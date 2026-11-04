#!/usr/bin/env python3
"""
FiestaPanel Minimalist GitHub Banner Generator
Produces clean, official (1280x380) repository banner featuring the authentic
classic green portal theme, default interlocking rings logo, bold italic
FIESTAPANEL header, and centered 'The Reliable Choice' tagline.
"""
import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1280
HEIGHT = 380

SVG_BANNER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 380" width="1280" height="380">
  <defs>
    <!-- Classic Portal Green Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#2ea35b"/>
      <stop offset="36%" stop-color="#006622"/>
      <stop offset="100%" stop-color="#176a3b"/>
    </linearGradient>

    <!-- Top Specular Gloss Sheen -->
    <linearGradient id="sheenGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>

    <!-- Soft Ambient Center Backlight Glow -->
    <radialGradient id="centerGlow" cx="50%" cy="45%" r="42%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>

    <!-- Drop Shadows for Depth -->
    <filter id="logoShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.45"/>
    </filter>
    <filter id="textShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.5"/>
      <feDropShadow dx="0" dy="6" stdDeviation="12" flood-color="#000000" flood-opacity="0.3"/>
    </filter>
    <filter id="tagShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
  </defs>

  <!-- 1. Background Layers -->
  <rect width="1280" height="380" fill="url(#bgGrad)"/>
  <rect width="1280" height="175" fill="url(#sheenGrad)"/>
  <rect width="1280" height="380" fill="url(#centerGlow)"/>

  <!-- 2. Authentic Portal Borders -->
  <!-- Top Specular Highlight Edge -->
  <line x1="0" y1="1.5" x2="1280" y2="1.5" stroke="rgba(255,255,255,0.48)" stroke-width="3"/>
  <!-- Signature Bottom Lime Accent Border -->
  <rect x="0" y="373" width="1280" height="7" fill="#74b21d"/>

  <!-- 3. Default Portal Logo (Interlocking TP-Link Rings) Centered Horizontally -->
  <!-- ViewBox 0 0 36 28 scaled 3x (108x84), centered at x=640 => translate(586, 68) -->
  <g transform="translate(586, 68) scale(3)" filter="url(#logoShadow)">
    <!-- Left Ring (White) -->
    <path d="M4 14 C4 8 9 4 15 4 L20 4 C24 4 28 8 28 12 L22 12 C22 10 19 8 16 8 L14 8 C11 8 8 11 8 14 C8 17 11 20 14 20 L16 20 C19 20 22 18 22 16 L28 16 C28 20 24 24 20 24 L15 24 C9 24 4 20 4 14 Z" fill="#ffffff" opacity="0.95"/>
    <!-- Right Ring (Mint Green) -->
    <path d="M32 14 C32 20 27 24 21 24 L16 24 C12 24 8 20 8 16 L14 16 C14 18 17 20 20 20 L22 20 C25 20 28 17 28 14 C28 11 25 8 22 8 L20 8 C17 8 14 10 14 12 L8 12 C8 8 12 4 16 4 L21 4 C27 4 32 8 32 14 Z" fill="#bdf4c9" opacity="0.9"/>
  </g>

  <!-- 4. FIESTAPANEL Header (Bold Italic, Centered) -->
  <text x="640" y="246" 
        font-family="'Liberation Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif" 
        font-size="68" 
        font-weight="900" 
        font-style="italic" 
        letter-spacing="2" 
        fill="#ffffff" 
        text-anchor="middle" 
        filter="url(#textShadow)">FIESTAPANEL</text>

  <!-- 5. Tagline: The Reliable Choice (Centered, Subtitle Mint Tint) -->
  <text x="640" y="295" 
        font-family="'Liberation Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif" 
        font-size="20" 
        font-weight="700" 
        letter-spacing="3" 
        fill="#d6f7dc" 
        text-anchor="middle" 
        filter="url(#tagShadow)">The Reliable Choice</text>
</svg>
"""


def render_with_chrome(svg_path: str, png_path: str) -> bool:
    """Renders the SVG to PNG using headless Google Chrome if available."""
    chrome_bin = (
        shutil.which("google-chrome")
        or shutil.which("chromium-browser")
        or shutil.which("chromium")
    )
    if not chrome_bin:
        return False
    try:
        cmd = [
            chrome_bin,
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            f"--window-size={WIDTH},{HEIGHT}",
            f"--screenshot={png_path}",
            f"file://{os.path.abspath(svg_path)}",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(png_path) and os.path.getsize(png_path) > 1000
    except Exception as e:
        print(f"Notice: Headless Chrome render failed ({e}), using Pillow fallback.")
        return False


def render_with_pillow(png_path: str):
    """Fallback high-resolution renderer using Pillow."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (23, 106, 59, 255))
    draw = ImageDraw.Draw(img)

    # 3-stop vertical gradient: #2ea35b (0%) -> #006622 (36%) -> #176a3b (100%)
    for y in range(HEIGHT):
        factor = y / HEIGHT
        if factor <= 0.36:
            sub = factor / 0.36
            r = int(0x2E * (1 - sub) + 0x00 * sub)
            g = int(0xA3 * (1 - sub) + 0x66 * sub)
            b = int(0x5B * (1 - sub) + 0x22 * sub)
        else:
            sub = (factor - 0.36) / 0.64
            r = int(0x00 * (1 - sub) + 0x17 * sub)
            g = int(0x66 * (1 - sub) + 0x6A * sub)
            b = int(0x22 * (1 - sub) + 0x3B * sub)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Ambient radial backlight glow in center
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    cx, cy = WIDTH // 2, int(HEIGHT * 0.45)
    for rad in range(360, 0, -12):
        alpha = int(35 * (1 - rad / 360))
        g_draw.ellipse([cx - rad, cy - int(rad * 0.45), cx + rad, cy + int(rad * 0.45)], fill=(255, 255, 255, alpha))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # Top specular line
    draw.line([(0, 1), (WIDTH, 1)], fill=(255, 255, 255, 120), width=3)
    # Bottom lime border (#74b21d)
    draw.rectangle([0, HEIGHT - 7, WIDTH, HEIGHT], fill=(0x74, 0xB2, 0x1D, 255))

    # Typography
    font_dir = "/usr/share/fonts/truetype/liberation"
    try:
        f_header = ImageFont.truetype(f"{font_dir}/LiberationSans-BoldItalic.ttf", 64)
        f_tag = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 19)
    except Exception:
        f_header = ImageFont.load_default()
        f_tag = ImageFont.load_default()

    # Draw Text
    header_text = "FIESTAPANEL"
    tag_text = "The Reliable Choice"

    # Header with shadow
    bbox_h = draw.textbbox((0, 0), header_text, font=f_header)
    w_h = bbox_h[2] - bbox_h[0]
    hx = (WIDTH - w_h) // 2
    hy = 195
    draw.text((hx, hy + 3), header_text, font=f_header, fill=(0, 0, 0, 100))
    draw.text((hx, hy), header_text, font=f_header, fill=(255, 255, 255, 255))

    # Tagline with shadow
    bbox_t = draw.textbbox((0, 0), tag_text, font=f_tag)
    w_t = bbox_t[2] - bbox_t[0]
    tx = (WIDTH - w_t) // 2
    ty = 275
    draw.text((tx, ty + 2), tag_text, font=f_tag, fill=(0, 0, 0, 120))
    draw.text((tx, ty), tag_text, font=f_tag, fill=(0xD6, 0xF7, 0xDC, 255))

    img.save(png_path, "PNG")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    static_dir = os.path.join(base_dir, "static")
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)

    svg_path = os.path.join(assets_dir, "banner.svg")
    png_path = os.path.join(assets_dir, "banner.png")
    static_png_path = os.path.join(static_dir, "banner.png")

    # 1. Write the clean vector SVG
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_BANNER.strip())
    print(f"Generated vector banner: {svg_path} ({os.path.getsize(svg_path)} bytes)")

    # 2. Render to PNG (Chrome preferred for perfect SVG paths/drop-shadows, Pillow fallback)
    rendered = render_with_chrome(svg_path, png_path)
    if not rendered:
        render_with_pillow(png_path)
    print(f"Generated raster banner: {png_path} ({os.path.getsize(png_path)} bytes)")

    # 3. Mirror to static/ for web server assets
    shutil.copy2(png_path, static_png_path)
    print(f"Mirrored banner to: {static_png_path}")


if __name__ == "__main__":
    main()
