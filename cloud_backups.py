"""
Cloud Offsite Backups Manager for FiestaPanel.
Supports S3-compatible cloud storage (Cloudflare R2, AWS S3, Backblaze B2, MinIO, Wasabi)
and WebDAV / Nextcloud / ownCloud offsite destinations with automated synchronization and retention.
"""

import os
import json
import time
import datetime
import threading
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Optional

import requests
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, BotoCoreError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = logging.getLogger("fiesta.cloud_backups")

DEFAULT_CLOUD_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "provider": "s3",  # "s3" or "webdav"
    "auto_sync": True,
    "retention_count": 5,  # 0 for unlimited
    "s3": {
        "endpoint_url": "",
        "bucket_name": "",
        "region_name": "auto",
        "access_key_id": "",
        "secret_access_key": "",
        "prefix": "backups/"
    },
    "webdav": {
        "url": "",
        "username": "",
        "password": "",
        "prefix": ""
    }
}


class CloudBackupManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "cloud_backups.json")
        self._lock = threading.Lock()
        self.status = {
            "active": False,
            "progress": 0,
            "current_file": "",
            "bytes_transferred": 0,
            "total_bytes": 0,
            "last_sync": None,
            "last_status": "Idle",
            "last_error": None
        }

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from cloud_backups.json or returns defaults."""
        if not os.path.exists(self.config_file):
            return json.loads(json.dumps(DEFAULT_CLOUD_CONFIG))
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                cfg = json.loads(json.dumps(DEFAULT_CLOUD_CONFIG))
                if isinstance(loaded, dict):
                    for k in ("enabled", "provider", "auto_sync", "retention_count"):
                        if k in loaded:
                            cfg[k] = loaded[k]
                    for sub in ("s3", "webdav"):
                        if isinstance(loaded.get(sub), dict):
                            cfg[sub].update(loaded[sub])
                return cfg
        except Exception as e:
            logger.error(f"Failed to read cloud config: {e}")
            return json.loads(json.dumps(DEFAULT_CLOUD_CONFIG))

    def save_config(self, new_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates and persists cloud backup configuration."""
        current = self.load_config()
        if not isinstance(new_data, dict):
            return False, "Invalid configuration format"

        if "enabled" in new_data:
            current["enabled"] = bool(new_data["enabled"])
        if "provider" in new_data and str(new_data["provider"]).lower() in ("s3", "webdav"):
            current["provider"] = str(new_data["provider"]).lower()
        if "auto_sync" in new_data:
            current["auto_sync"] = bool(new_data["auto_sync"])
        if "retention_count" in new_data:
            try:
                ret = int(new_data["retention_count"])
                current["retention_count"] = max(0, min(100, ret))
            except (ValueError, TypeError):
                pass

        # Update S3
        if "s3" in new_data and isinstance(new_data["s3"], dict):
            s = new_data["s3"]
            current["s3"]["endpoint_url"] = str(s.get("endpoint_url", current["s3"]["endpoint_url"])).strip()
            current["s3"]["bucket_name"] = str(s.get("bucket_name", current["s3"]["bucket_name"])).strip()
            current["s3"]["region_name"] = str(s.get("region_name", current["s3"]["region_name"])).strip() or "auto"
            current["s3"]["access_key_id"] = str(s.get("access_key_id", current["s3"]["access_key_id"])).strip()

            new_sec = str(s.get("secret_access_key", "")).strip()
            if new_sec and not new_sec.startswith("••"):
                current["s3"]["secret_access_key"] = new_sec

            prefix = str(s.get("prefix", current["s3"]["prefix"])).strip().lstrip("/")
            if prefix and not prefix.endswith("/"):
                prefix += "/"
            current["s3"]["prefix"] = prefix

        # Update WebDAV
        if "webdav" in new_data and isinstance(new_data["webdav"], dict):
            w = new_data["webdav"]
            current["webdav"]["url"] = str(w.get("url", current["webdav"]["url"])).strip().rstrip("/")
            current["webdav"]["username"] = str(w.get("username", current["webdav"]["username"])).strip()

            new_pw = str(w.get("password", "")).strip()
            if new_pw and not new_pw.startswith("••"):
                current["webdav"]["password"] = new_pw

            pfx = str(w.get("prefix", current["webdav"]["prefix"])).strip().strip("/")
            current["webdav"]["prefix"] = pfx

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            return True, "Cloud offsite backup configuration saved."
        except Exception as e:
            return False, f"Failed to save cloud config: {e}"

    def get_masked_config(self) -> Dict[str, Any]:
        """Returns safe configuration for UI rendering with secrets masked."""
        cfg = self.load_config()
        if cfg["s3"].get("secret_access_key"):
            cfg["s3"]["secret_access_key"] = "••••••••••••••••"
            cfg["s3"]["has_secret"] = True
        else:
            cfg["s3"]["has_secret"] = False

        if cfg["webdav"].get("password"):
            cfg["webdav"]["password"] = "••••••••••••••••"
            cfg["webdav"]["has_password"] = True
        else:
            cfg["webdav"]["has_password"] = False
        return cfg

    # ── S3 Helper Methods ────────────────────────────────────────────────────
    def _get_s3_client(self, cfg: Optional[Dict[str, Any]] = None):
        if not HAS_BOTO3:
            raise RuntimeError("boto3 is not installed on this system.")
        if cfg is None:
            cfg = self.load_config()
        s = cfg.get("s3", {})

        access_key = s.get("access_key_id", "").strip()
        secret_key = s.get("secret_access_key", "").strip()
        endpoint_url = s.get("endpoint_url", "").strip() or None
        region = s.get("region_name", "auto").strip() or "auto"

        if not access_key or not secret_key:
            raise ValueError("S3 Access Key ID or Secret Access Key is missing.")

        boto_cfg = Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=30,
            retries={"max_attempts": 3}
        )

        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region if region != "auto" else "us-east-1",
            config=boto_cfg
        )

    # ── Connection Test ──────────────────────────────────────────────────────
    def test_connection(self, override_cfg: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Tests offsite connection using current or overridden settings."""
        cfg = override_cfg or self.load_config()
        provider = cfg.get("provider", "s3").lower()

        if provider == "s3":
            try:
                s = cfg.get("s3", {})
                bucket = s.get("bucket_name", "").strip()
                if not bucket:
                    return False, "Bucket name is required for S3 testing."

                client = self._get_s3_client(cfg)
                # Attempt to head bucket or list first key
                try:
                    client.head_bucket(Bucket=bucket)
                except Exception:
                    # Fallback to listing 1 key
                    client.list_objects_v2(Bucket=bucket, MaxKeys=1)

                return True, f"Successfully connected to S3 bucket '{bucket}'!"
            except Exception as e:
                err_msg = str(e)
                if hasattr(e, "response") and isinstance(e.response, dict):
                    err_msg = e.response.get("Error", {}).get("Message", err_msg)
                return False, f"S3 Connection failed: {err_msg}"

        elif provider == "webdav":
            try:
                w = cfg.get("webdav", {})
                url = w.get("url", "").strip()
                user = w.get("username", "").strip()
                pw = w.get("password", "").strip()
                if not url:
                    return False, "WebDAV server URL is required."

                auth = (user, pw) if user and pw else None
                resp = requests.request("PROPFIND", url, auth=auth, headers={"Depth": "0"}, timeout=12)
                if resp.status_code in (200, 207):
                    return True, "Successfully connected to WebDAV server!"
                elif resp.status_code == 401:
                    return False, "WebDAV authentication failed: Invalid username or password."
                else:
                    return False, f"WebDAV server responded with HTTP status {resp.status_code}"
            except Exception as e:
                return False, f"WebDAV Connection failed: {str(e)}"

        return False, f"Unsupported provider: {provider}"

    # ── Upload Operations ────────────────────────────────────────────────────
    def upload_file(self, local_path: str, remote_name: Optional[str] = None) -> Tuple[bool, str]:
        """Uploads a local backup file to configured offsite destination."""
        if not os.path.isfile(local_path):
            return False, f"Local file not found: {local_path}"

        cfg = self.load_config()
        provider = cfg.get("provider", "s3").lower()
        fname = remote_name or os.path.basename(local_path)
        file_size = os.path.getsize(local_path)

        with self._lock:
            self.status["active"] = True
            self.status["current_file"] = fname
            self.status["total_bytes"] = file_size
            self.status["bytes_transferred"] = 0
            self.status["progress"] = 0
            self.status["last_status"] = f"Uploading {fname} to {provider.upper()}..."
            self.status["last_error"] = None

        def progress_cb(bytes_amount):
            with self._lock:
                self.status["bytes_transferred"] += bytes_amount
                if file_size > 0:
                    pct = int((self.status["bytes_transferred"] / file_size) * 100)
                    self.status["progress"] = min(100, pct)

        try:
            if provider == "s3":
                s = cfg.get("s3", {})
                bucket = s.get("bucket_name", "").strip()
                prefix = s.get("prefix", "backups/").strip().lstrip("/")
                if prefix and not prefix.endswith("/"):
                    prefix += "/"
                key = f"{prefix}{fname}"

                client = self._get_s3_client(cfg)
                client.upload_file(local_path, bucket, key, Callback=progress_cb)

            elif provider == "webdav":
                w = cfg.get("webdav", {})
                url = w.get("url", "").strip().rstrip("/")
                prefix = w.get("prefix", "").strip().strip("/")
                if prefix:
                    url = f"{url}/{prefix}"
                target_url = f"{url}/{fname}"
                user = w.get("username", "").strip()
                pw = w.get("password", "").strip()
                auth = (user, pw) if user and pw else None

                class ProgressFileWrapper:
                    def __init__(self, file_obj, callback):
                        self.file_obj = file_obj
                        self.callback = callback

                    def read(self, size=-1):
                        data = self.file_obj.read(size)
                        if data:
                            self.callback(len(data))
                        return data

                with open(local_path, "rb") as f:
                    wrapped = ProgressFileWrapper(f, progress_cb)
                    resp = requests.put(target_url, data=wrapped, auth=auth, timeout=600)
                    if resp.status_code not in (200, 201, 204):
                        raise RuntimeError(f"WebDAV upload failed with HTTP status {resp.status_code}")

            else:
                raise ValueError(f"Unknown provider: {provider}")

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self._lock:
                self.status["active"] = False
                self.status["progress"] = 100
                self.status["last_sync"] = now_str
                self.status["last_status"] = f"Successfully synced {fname} to {provider.upper()}."

            # Automatically prune retention
            self.prune_retention()

            return True, f"Successfully uploaded {fname} to offsite storage."

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Offsite upload error: {err_msg}")
            with self._lock:
                self.status["active"] = False
                self.status["last_status"] = "Upload failed"
                self.status["last_error"] = err_msg
            return False, f"Offsite upload failed: {err_msg}"

    def start_async_upload(self, local_path: str):
        """Dispatches upload in a background thread."""
        t = threading.Thread(target=self.upload_file, args=(local_path,), daemon=True)
        t.start()

    # ── Remote Backups Listing ───────────────────────────────────────────────
    def list_remote_backups(self) -> List[Dict[str, Any]]:
        """Lists backups currently stored in offsite cloud destination."""
        cfg = self.load_config()
        provider = cfg.get("provider", "s3").lower()
        results: List[Dict[str, Any]] = []

        if provider == "s3":
            try:
                s = cfg.get("s3", {})
                bucket = s.get("bucket_name", "").strip()
                prefix = s.get("prefix", "backups/").strip().lstrip("/")
                if prefix and not prefix.endswith("/"):
                    prefix += "/"

                client = self._get_s3_client(cfg)
                paginator = client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    for item in page.get("Contents", []):
                        key = item.get("Key", "")
                        if key == prefix or key.endswith("/"):
                            continue
                        filename = os.path.basename(key)
                        size_bytes = item.get("Size", 0)
                        mtime = item.get("LastModified")
                        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S") if mtime else "--"

                        results.append({
                            "filename": filename,
                            "key": key,
                            "size_bytes": size_bytes,
                            "size_mb": round(size_bytes / (1024 * 1024), 1),
                            "size_gb": round(size_bytes / (1024 * 1024 * 1024), 2),
                            "mtime": mtime_str,
                            "provider": "S3"
                        })
            except Exception as e:
                logger.error(f"Failed to list S3 remote backups: {e}")

        elif provider == "webdav":
            try:
                w = cfg.get("webdav", {})
                url = w.get("url", "").strip().rstrip("/")
                prefix = w.get("prefix", "").strip().strip("/")
                if prefix:
                    url = f"{url}/{prefix}"
                user = w.get("username", "").strip()
                pw = w.get("password", "").strip()
                auth = (user, pw) if user and pw else None

                resp = requests.request("PROPFIND", url, auth=auth, headers={"Depth": "1"}, timeout=15)
                if resp.status_code in (200, 207):
                    root = ET.fromstring(resp.content)
                    ns = {"D": "DAV:"}
                    for resp_el in root.findall("D:response", ns):
                        href = resp_el.findtext("D:href", namespaces=ns) or ""
                        filename = os.path.basename(urllib.parse.unquote(href.rstrip("/")))
                        if not filename or href.rstrip("/") == urllib.parse.urlparse(url).path.rstrip("/"):
                            continue

                        # Extract size & modified
                        size_bytes = 0
                        mtime_str = "--"
                        prop = resp_el.find("D:propstat/D:prop", ns)
                        if prop is not None:
                            len_text = prop.findtext("D:getcontentlength", namespaces=ns)
                            if len_text and len_text.isdigit():
                                size_bytes = int(len_text)
                            mtime_raw = prop.findtext("D:getlastmodified", namespaces=ns)
                            if mtime_raw:
                                mtime_str = mtime_raw

                        if filename.endswith((".tar.gz", ".zip", ".tar.zst")):
                            results.append({
                                "filename": filename,
                                "key": href,
                                "size_bytes": size_bytes,
                                "size_mb": round(size_bytes / (1024 * 1024), 1),
                                "size_gb": round(size_bytes / (1024 * 1024 * 1024), 2),
                                "mtime": mtime_str,
                                "provider": "WebDAV"
                            })
            except Exception as e:
                logger.error(f"Failed to list WebDAV remote backups: {e}")

        results.sort(key=lambda x: x.get("mtime", ""), reverse=True)
        return results

    # ── Download Remote Backup ───────────────────────────────────────────────
    def download_remote_backup(self, filename: str, local_dest_dir: str) -> Tuple[bool, str]:
        """Downloads an offsite backup archive back to the local backup directory."""
        cfg = self.load_config()
        provider = cfg.get("provider", "s3").lower()
        safe_fname = os.path.basename(filename)
        dest_path = os.path.join(local_dest_dir, safe_fname)
        os.makedirs(local_dest_dir, exist_ok=True)

        try:
            if provider == "s3":
                s = cfg.get("s3", {})
                bucket = s.get("bucket_name", "").strip()
                prefix = s.get("prefix", "backups/").strip().lstrip("/")
                if prefix and not prefix.endswith("/"):
                    prefix += "/"
                key = f"{prefix}{safe_fname}"

                client = self._get_s3_client(cfg)
                client.download_file(bucket, key, dest_path)

            elif provider == "webdav":
                w = cfg.get("webdav", {})
                url = w.get("url", "").strip().rstrip("/")
                prefix = w.get("prefix", "").strip().strip("/")
                if prefix:
                    url = f"{url}/{prefix}"
                target_url = f"{url}/{safe_fname}"
                user = w.get("username", "").strip()
                pw = w.get("password", "").strip()
                auth = (user, pw) if user and pw else None

                with requests.get(target_url, auth=auth, stream=True, timeout=600) as r:
                    r.raise_for_status()
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=16384):
                            f.write(chunk)

            return True, f"Successfully restored '{safe_fname}' from cloud storage to local disk."
        except Exception as e:
            logger.error(f"Failed to download remote backup: {e}")
            return False, f"Failed to download cloud backup: {e}"

    # ── Delete Remote Backup ─────────────────────────────────────────────────
    def delete_remote_backup(self, filename: str) -> Tuple[bool, str]:
        """Deletes a single backup from offsite cloud storage."""
        cfg = self.load_config()
        provider = cfg.get("provider", "s3").lower()
        safe_fname = os.path.basename(filename)

        try:
            if provider == "s3":
                s = cfg.get("s3", {})
                bucket = s.get("bucket_name", "").strip()
                prefix = s.get("prefix", "backups/").strip().lstrip("/")
                if prefix and not prefix.endswith("/"):
                    prefix += "/"
                key = f"{prefix}{safe_fname}"

                client = self._get_s3_client(cfg)
                client.delete_object(Bucket=bucket, Key=key)

            elif provider == "webdav":
                w = cfg.get("webdav", {})
                url = w.get("url", "").strip().rstrip("/")
                prefix = w.get("prefix", "").strip().strip("/")
                if prefix:
                    url = f"{url}/{prefix}"
                target_url = f"{url}/{safe_fname}"
                user = w.get("username", "").strip()
                pw = w.get("password", "").strip()
                auth = (user, pw) if user and pw else None

                resp = requests.delete(target_url, auth=auth, timeout=15)
                if resp.status_code not in (200, 204, 404):
                    raise RuntimeError(f"WebDAV returned status {resp.status_code}")

            return True, f"Remote backup '{safe_fname}' deleted from cloud."
        except Exception as e:
            return False, f"Failed to delete remote backup: {e}"

    # ── Retention Pruning ────────────────────────────────────────────────────
    def prune_retention(self) -> int:
        """Enforces retention policy by removing oldest cloud backups exceeding retention_count."""
        cfg = self.load_config()
        retention = cfg.get("retention_count", 5)
        if retention <= 0:
            return 0

        remote_files = self.list_remote_backups()
        if len(remote_files) <= retention:
            return 0

        to_delete = remote_files[retention:]
        deleted_count = 0
        for item in to_delete:
            ok, _ = self.delete_remote_backup(item["filename"])
            if ok:
                deleted_count += 1
        return deleted_count

    def get_status(self) -> Dict[str, Any]:
        """Returns live upload and synchronization status."""
        with self._lock:
            return dict(self.status)
