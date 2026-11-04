#!/usr/bin/env python3
import os
import sys
import json
import re
import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "static", "mcassets")
MAPPING_FILE = os.path.join(BASE_DIR, "items_textures.json")
CATALOG_FILE = os.path.join(ASSET_DIR, "catalog.json")

os.makedirs(ASSET_DIR, exist_ok=True)

# Special aliases and entity/block texture mappings
aliases = {
    "shield": "entity/shield_base_nopattern",
    "chest": "entity/chest/normal",
    "trapped_chest": "entity/chest/trapped",
    "ender_chest": "entity/chest/ender",
    "crafting_table": "block/crafting_table_top",
    "furnace": "block/furnace_front",
    "blast_furnace": "block/blast_furnace_front",
    "smoker": "block/smoker_front",
    "grass_block": "block/grass_block_side",
    "enchanted_golden_apple": "item/golden_apple",
    "crossbow": "item/crossbow_standby",
    "bow": "item/bow",
    "tnt": "block/tnt_side",
    "bookshelf": "block/bookshelf",
    "barrel": "block/barrel_side",
    "dispenser": "block/dispenser_front",
    "dropper": "block/dropper_front",
    "observer": "block/observer_front",
    "piston": "block/piston_top",
    "sticky_piston": "block/piston_top_sticky",
    "red_bed": "item/red_bed",
    "white_bed": "item/white_bed",
    "black_bed": "item/black_bed",
    "blue_bed": "item/blue_bed",
    "yellow_bed": "item/yellow_bed",
    "green_bed": "item/green_bed",
    "purple_bed": "item/purple_bed",
    "pink_bed": "item/pink_bed",
    "bed": "item/red_bed",
}

extra_items = [
    "diamond_sword", "iron_sword", "golden_sword", "netherite_sword", "stone_sword", "wooden_sword",
    "diamond_pickaxe", "iron_pickaxe", "golden_pickaxe", "netherite_pickaxe", "stone_pickaxe", "wooden_pickaxe",
    "diamond_axe", "iron_axe", "golden_axe", "netherite_axe", "stone_axe", "wooden_axe",
    "diamond_shovel", "iron_shovel", "golden_shovel", "netherite_shovel", "stone_shovel", "wooden_shovel",
    "diamond_hoe", "iron_hoe", "golden_hoe", "netherite_hoe", "stone_hoe", "wooden_hoe",
    "diamond_helmet", "iron_helmet", "golden_helmet", "netherite_helmet", "chainmail_helmet", "leather_helmet", "turtle_helmet",
    "diamond_chestplate", "iron_chestplate", "golden_chestplate", "netherite_chestplate", "chainmail_chestplate", "leather_chestplate", "elytra",
    "diamond_leggings", "iron_leggings", "golden_leggings", "netherite_leggings", "chainmail_leggings", "leather_leggings",
    "diamond_boots", "iron_boots", "golden_boots", "netherite_boots", "chainmail_boots", "leather_boots",
    "shield", "totem_of_undying", "bow", "crossbow", "arrow", "spectral_arrow", "tipped_arrow",
    "bread", "cooked_beef", "cooked_porkchop", "cooked_mutton", "cooked_chicken", "cooked_cod", "cooked_salmon",
    "apple", "golden_apple", "enchanted_golden_apple", "potion", "splash_potion", "lingering_potion",
    "ender_pearl", "eye_of_ender", "blaze_rod", "blaze_powder", "firework_rocket",
    "iron_ingot", "gold_ingot", "diamond", "emerald", "netherite_ingot", "copper_ingot", "coal", "charcoal",
    "stick", "flint", "string", "feather", "gunpowder", "redstone", "glowstone_dust",
    "water_bucket", "lava_bucket", "milk_bucket", "bucket", "powder_snow_bucket",
    "stone", "cobblestone", "smooth_stone", "dirt", "grass_block", "oak_planks", "spruce_planks", "birch_planks",
    "crafting_table", "furnace", "chest", "ender_chest", "barrel", "anvil", "torch", "lantern",
    "mace", "wind_charge", "breeze_rod", "trial_key", "ominous_trial_key", "ominous_bottle", "heavy_core",
    "crafter", "copper_bulb", "copper_grate", "chiseled_copper", "chiseled_tuff", "tuff_bricks", "flow_armor_trim_smithing_template",
    "bolt_armor_trim_smithing_template", "flow_pottery_sherd", "guster_pottery_sherd", "scrape_pottery_sherd"
]

_name_to_tex_cache = None

def load_name_to_tex():
    global _name_to_tex_cache
    if _name_to_tex_cache is not None:
        return _name_to_tex_cache
    name_to_tex = {}
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                for entry in json.load(f):
                    n = entry.get("name")
                    t = entry.get("texture")
                    if n and t:
                        name_to_tex[n] = t
        except Exception as e:
            logging.warning(f"Failed to read {MAPPING_FILE}: {e}")
    _name_to_tex_cache = name_to_tex
    return _name_to_tex_cache

def get_version_candidates(version=None):
    candidates = []
    if version:
        clean = version.strip()
        candidates.append(clean)
        parts = clean.split(".")
        if len(parts) >= 2:
            base = f"{parts[0]}.{parts[1]}"
            if base != clean and base not in candidates:
                candidates.append(base)
    for fb in ["1.21.4", "1.21.3", "1.21.1", "1.21", "1.20.6"]:
        if fb not in candidates:
            candidates.append(fb)
    return candidates

def format_item_name(item_id):
    clean = (item_id or "").replace("minecraft:", "").strip()
    return " ".join(w.capitalize() for w in clean.split("_"))

def fetch_single(item_name, versions=None):
    dest = os.path.join(ASSET_DIR, f"{item_name}.png")
    if os.path.exists(dest) and os.path.getsize(dest) > 50:
        return True

    clean_name = item_name.lower().replace("minecraft:", "").strip()
    name_to_tex = load_name_to_tex()
    tex = aliases.get(clean_name) or name_to_tex.get(clean_name)

    version_list = versions or ["1.21.4", "1.21.1", "1.21"]

    candidates = []
    if tex:
        c1 = tex.replace("minecraft:", "").replace("items/", "item/")
        c2 = tex.replace("minecraft:", "")
        for v in version_list:
            candidates.append(f"https://assets.mcasset.cloud/{v}/assets/minecraft/textures/{c1}.png")
            candidates.append(f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/{v}/{c2}.png")
            candidates.append(f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/{v}/assets/minecraft/textures/{c1}.png")

    for v in version_list:
        candidates.extend([
            f"https://assets.mcasset.cloud/{v}/assets/minecraft/textures/item/{clean_name}.png",
            f"https://assets.mcasset.cloud/{v}/assets/minecraft/textures/block/{clean_name}.png",
            f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/{v}/items/{clean_name}.png",
            f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/{v}/blocks/{clean_name}.png",
            f"https://assets.mcasset.cloud/{v}/assets/minecraft/textures/entity/{clean_name}.png"
        ])

    for url in candidates:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 50:
                        with open(dest, "wb") as f_out:
                            f_out.write(data)
                        return True
        except Exception:
            continue
    return False

def update_catalog():
    try:
        entries = []
        if os.path.isdir(ASSET_DIR):
            for fname in sorted(os.listdir(ASSET_DIR)):
                if fname.endswith(".png") and not fname.startswith("empty_"):
                    item_id = fname[:-4]
                    entries.append({
                        "id": item_id,
                        "name": format_item_name(item_id),
                        "icon": f"/static/mcassets/{fname}"
                    })
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f)
        return len(entries)
    except Exception as e:
        logging.warning(f"Failed to update catalog.json: {e}")
        return 0

def sync_mc_assets(version=None, max_workers=15):
    versions = get_version_candidates(version)
    name_to_tex = load_name_to_tex()
    all_items = set(name_to_tex.keys()).union(set(aliases.keys())).union(set(extra_items))

    # Identify items not yet cached locally
    missing_items = [
        item for item in all_items
        if not (os.path.exists(os.path.join(ASSET_DIR, f"{item}.png")) and os.path.getsize(os.path.join(ASSET_DIR, f"{item}.png")) > 50)
    ]

    newly_fetched = 0
    if missing_items:
        logging.info(f"Syncing MC assets: {len(missing_items)} missing items to fetch for version candidate(s) {versions}...")
        priority_items = [i for i in extra_items if i in missing_items]
        other_items = [i for i in missing_items if i not in priority_items]

        # Fetch essential/priority items first
        if priority_items:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(fetch_single, item, versions) for item in priority_items]
                for f in futures:
                    try:
                        if f.result():
                            newly_fetched += 1
                    except Exception:
                        pass
            update_catalog()

        # Fetch remaining items
        if other_items:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(fetch_single, item, versions) for item in other_items]
                for f in futures:
                    try:
                        if f.result():
                            newly_fetched += 1
                    except Exception:
                        pass

    total_catalog = update_catalog()
    logging.info(f"MC asset sync complete: {newly_fetched} newly fetched, {total_catalog} items in catalog.")
    return {
        "success": True,
        "version_candidates": versions,
        "missing_checked": len(missing_items),
        "newly_fetched": newly_fetched,
        "total_catalog": total_catalog
    }

if __name__ == "__main__":
    target_version = sys.argv[1] if len(sys.argv) > 1 else "1.21.4"
    print(f"Syncing Minecraft assets for target version: {target_version}...")
    res = sync_mc_assets(target_version, max_workers=15)
    print(f"Done! Checked {res['missing_checked']} missing items, fetched {res['newly_fetched']} new icons. Total catalog: {res['total_catalog']}")
