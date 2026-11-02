#!/usr/bin/env python3
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH = 1280
HEIGHT = 640

# Create base canvas with RGBA
img = Image.new("RGBA", (WIDTH, HEIGHT), (11, 17, 30, 255))
draw = ImageDraw.Draw(img)

# 1. Background Gradient & Ambient Glows
# Gradient from top-left (deep navy blue #0f1c3f) to bottom-right (deep abyss #060913)
for y in range(HEIGHT):
    factor = y / HEIGHT
    r = int(14 * (1 - factor) + 5 * factor)
    g = int(24 * (1 - factor) + 9 * factor)
    b = int(45 * (1 - factor) + 18 * factor)
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

# Draw ambient background radial glows
glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_layer)

# Cyan/Blue Aero glow top-center
cx, cy = 640, 260
for rad in range(320, 0, -8):
    alpha = int(45 * (1 - rad / 320))
    glow_draw.ellipse([cx - rad, cy - int(rad*0.7), cx + rad, cy + int(rad*0.7)], fill=(0, 168, 255, alpha))

# Purple/Teal corner glow
for rad in range(250, 0, -10):
    alpha = int(30 * (1 - rad / 250))
    glow_draw.ellipse([1100 - rad, 100 - rad, 1100 + rad, 100 + rad], fill=(147, 51, 234, alpha))
    glow_draw.ellipse([150 - rad, 520 - rad, 150 + rad, 520 + rad], fill=(20, 184, 166, alpha))

img = Image.alpha_composite(img, glow_layer)
draw = ImageDraw.Draw(img)

# Subtle background dot grid
for x in range(30, WIDTH, 32):
    for y in range(30, HEIGHT, 32):
        draw.ellipse([x, y, x + 2, y + 2], fill=(255, 255, 255, 18))

# 2. Fonts
font_dir = "/usr/share/fonts/truetype/liberation"
f_title = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 52)
f_subtitle = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 20)
f_tagline = ImageFont.truetype(f"{font_dir}/LiberationSans-Regular.ttf", 16)
f_chip = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 13)
f_mono = ImageFont.truetype(f"{font_dir}/LiberationMono-Bold.ttf", 13)
f_small = ImageFont.truetype(f"{font_dir}/LiberationSans-Regular.ttf", 13)

# 3. Main Glass Window Card
# Window coordinates
wx0, wy0, wx1, wy1 = 70, 45, WIDTH - 70, HEIGHT - 55

# Window drop shadow
shadow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
s_draw = ImageDraw.Draw(shadow_layer)
s_draw.rounded_rectangle([wx0 + 8, wy0 + 12, wx1 + 8, wy1 + 16], radius=18, fill=(0, 0, 0, 140))
shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(16))
img = Image.alpha_composite(img, shadow_layer)

# Window base
window_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
w_draw = ImageDraw.Draw(window_layer)

# Semi-translucent dark slate body with Aero tint
w_draw.rounded_rectangle([wx0, wy0, wx1, wy1], radius=16, fill=(13, 20, 36, 235), outline=(56, 189, 248, 120), width=2)

# Titlebar (Aero Glass header with specular reflection)
title_h = 54
# Draw titlebar gradient
for ty in range(title_h):
    frac = ty / title_h
    # Top half bright specular reflection
    if frac < 0.48:
        val = int(255 - frac * 120)
        c = (38, 86, 148, int(200 + (1 - frac) * 50))
    else:
        c = (18, 48, 92, 230)
    w_draw.line([(wx0 + 2, wy0 + 2 + ty), (wx1 - 2, wy0 + 2 + ty)], fill=c)

# Specular shine line
w_draw.line([(wx0 + 2, wy0 + int(title_h * 0.48)), (wx1 - 2, wy0 + int(title_h * 0.48))], fill=(255, 255, 255, 60))
w_draw.line([(wx0 + 16, wy0 + 3), (wx1 - 16, wy0 + 3)], fill=(255, 255, 255, 120))

# Titlebar buttons (Windows 7 Aero style window controls on right)
bx = wx1 - 32
by = wy0 + 16
# Close (red)
w_draw.rounded_rectangle([bx - 12, by - 6, bx + 16, by + 12], radius=3, fill=(225, 29, 72, 220), outline=(255, 255, 255, 100))
w_draw.line([(bx - 4, by - 1), (bx + 8, by + 7)], fill=(255, 255, 255, 240), width=2)
w_draw.line([(bx - 4, by + 7), (bx + 8, by - 1)], fill=(255, 255, 255, 240), width=2)

# Maximize (blue)
bx -= 36
w_draw.rounded_rectangle([bx - 12, by - 6, bx + 16, by + 12], radius=3, fill=(30, 64, 175, 180), outline=(255, 255, 255, 80))
w_draw.rectangle([bx - 3, by, bx + 7, by + 6], outline=(255, 255, 255, 240), width=1)

# Minimize
bx -= 36
w_draw.rounded_rectangle([bx - 12, by - 6, bx + 16, by + 12], radius=3, fill=(30, 64, 175, 180), outline=(255, 255, 255, 80))
w_draw.line([(bx - 3, by + 6), (bx + 7, by + 6)], fill=(255, 255, 255, 240), width=2)

# Window Icon (Aero Orb / Gateway Icon)
w_draw.ellipse([wx0 + 18, wy0 + 12, wx0 + 44, wy0 + 38], fill=(14, 165, 233, 240), outline=(255, 255, 255, 180), width=2)
# Pickaxe / Cross in icon
w_draw.line([(wx0 + 24, wy0 + 32), (wx0 + 38, wy0 + 18)], fill=(255, 255, 255, 255), width=2)
w_draw.arc([wx0 + 28, wy0 + 16, wx0 + 40, wy0 + 28], start=180, end=270, fill=(255, 255, 255, 255), width=3)

# Titlebar Title text
w_draw.text((wx0 + 54, wy0 + 17), "FiestaPanel Gateway Console • v2.0.0 [Win7 Aero Engine]", font=f_chip, fill=(224, 242, 254, 240))

img = Image.alpha_composite(img, window_layer)
draw = ImageDraw.Draw(img)

# 4. Window Content Area
# Top Left: Big Brand Header
hx = wx0 + 45
hy = wy0 + 78

# Subtle glow behind FiestaPanel title
glow_t = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
gt_draw = ImageDraw.Draw(glow_t)
gt_draw.text((hx + 2, hy + 2), "FiestaPanel", font=f_title, fill=(56, 189, 248, 120))
glow_t = glow_t.filter(ImageFilter.GaussianBlur(8))
img = Image.alpha_composite(img, glow_t)
draw = ImageDraw.Draw(img)

draw.text((hx, hy), "FiestaPanel", font=f_title, fill=(255, 255, 255, 255))

# Subtitle
draw.text((hx + 3, hy + 64), "The Modern & Retro Minecraft Server Management Suite", font=f_subtitle, fill=(56, 189, 248, 255))

# Description line
draw.text((hx + 4, hy + 98), "Nostalgic TP-Link & Windows 7 Aero UI  •  Real-Time Telemetry  •  Jailed File Manager", font=f_tagline, fill=(148, 163, 184, 255))

# Feature Pills / Badges
pills = [
    ("🪟 Windows 7 Aero Glass", (38, 86, 148), (186, 230, 253)),
    ("📟 Retro TP-Link", (20, 83, 45), (187, 247, 208)),
    ("🎒 Visual Inventory", (124, 45, 18), (254, 215, 170)),
    ("🔌 Modrinth v2 Store", (19, 78, 74), (204, 251, 241)),
    ("⚡ 1-Line Turnkey", (88, 28, 135), (243, 232, 255)),
]

px = hx + 4
py = hy + 130
for text, bg_col, text_col in pills:
    # Measure text
    bbox = draw.textbbox((px, py), text, font=f_chip)
    tw = bbox[2] - bbox[0]
    draw.rounded_rectangle([px, py, px + tw + 18, py + 26], radius=6, fill=(*bg_col, 200), outline=(*text_col, 100), width=1)
    draw.text((px + 9, py + 5), text, font=f_chip, fill=text_col)
    px += tw + 28

# 5. Bottom Showcase Cards (Two cards: Left = Live Status & Install, Right = Inventory & Textures)
# Left Card: Live Server Telemetry + Install Command
c1_x0, c1_y0, c1_x1, c1_y1 = hx + 4, hy + 175, hx + 480, wy1 - 32
draw.rounded_rectangle([c1_x0, c1_y0, c1_x1, c1_y1], radius=10, fill=(15, 23, 42, 220), outline=(51, 65, 85, 200), width=1)

# Card 1 Header: Server Status pill
draw.ellipse([c1_x0 + 16, c1_y0 + 16, c1_x0 + 26, c1_y0 + 26], fill=(34, 197, 94, 255))
draw.text((c1_x0 + 34, c1_y0 + 14), "SERVER ONLINE  •  Purpur 1.21.11  •  TPS: 20.0", font=f_chip, fill=(241, 245, 249, 255))

# Resource stats row
draw.text((c1_x0 + 16, c1_y0 + 44), "CPU Usage", font=f_small, fill=(148, 163, 184, 255))
draw.rounded_rectangle([c1_x0 + 90, c1_y0 + 48, c1_x0 + 240, c1_y0 + 56], radius=4, fill=(30, 41, 59, 255))
draw.rounded_rectangle([c1_x0 + 90, c1_y0 + 48, c1_x0 + 125, c1_y0 + 56], radius=4, fill=(56, 189, 248, 255))
draw.text((c1_x0 + 250, c1_y0 + 44), "24%", font=f_mono, fill=(224, 242, 254, 255))

draw.text((c1_x0 + 16, c1_y0 + 68), "Memory", font=f_small, fill=(148, 163, 184, 255))
draw.rounded_rectangle([c1_x0 + 90, c1_y0 + 72, c1_x0 + 240, c1_y0 + 80], radius=4, fill=(30, 41, 59, 255))
draw.rounded_rectangle([c1_x0 + 90, c1_y0 + 72, c1_x0 + 165, c1_y0 + 80], radius=4, fill=(168, 85, 247, 255))
draw.text((c1_x0 + 250, c1_y0 + 68), "4.2 / 8.0 GB", font=f_mono, fill=(224, 242, 254, 255))

# 1-Line Install Box inside Card 1
cmd_y0 = c1_y0 + 98
draw.rounded_rectangle([c1_x0 + 12, cmd_y0, c1_x1 - 12, cmd_y0 + 36], radius=6, fill=(2, 6, 23, 240), outline=(56, 189, 248, 140))
draw.text((c1_x0 + 22, cmd_y0 + 9), "$ curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash", font=f_mono, fill=(56, 189, 248, 255))

# Card 2: Visual Inventory & Minecraft Asset Showcase
c2_x0, c2_y0, c2_x1, c2_y1 = c1_x1 + 24, hy + 175, wx1 - 45, wy1 - 32
draw.rounded_rectangle([c2_x0, c2_y0, c2_x1, c2_y1], radius=10, fill=(15, 23, 42, 220), outline=(51, 65, 85, 200), width=1)

# Card 2 Header
draw.text((c2_x0 + 16, c2_y0 + 14), "Visual Inventory Inspector (1,300+ Textures)", font=f_chip, fill=(241, 245, 249, 255))

# Minecraft slot grid with genuine textures
mc_assets = [
    ("netherite_sword.png", "Netherite Sword"),
    ("totem_of_undying.png", "Totem of Undying"),
    ("golden_apple.png", "Golden Apple"),
    ("enchanted_book.png", "Enchanted Book"),
    ("diamond_sword.png", "Diamond Sword"),
    ("beacon.png", "Beacon"),
    ("ender_eye.png", "Eye of Ender")
]

slot_sx = c2_x0 + 16
slot_sy = c2_y0 + 42
slot_size = 46

asset_dir = "/home/ubuntu/fiesta-portal/static/mcassets"

for idx, (asset_file, label) in enumerate(mc_assets):
    cur_x = slot_sx + idx * (slot_size + 14)
    if cur_x + slot_size > c2_x1 - 10:
        break
    # Authentic retro Minecraft slot frame (dark bevel top/left, light bevel bottom/right)
    draw.rectangle([cur_x, slot_sy, cur_x + slot_size, slot_sy + slot_size], fill=(139, 139, 139, 255), outline=(55, 55, 55, 255), width=2)
    draw.rectangle([cur_x + 2, slot_sy + 2, cur_x + slot_size - 2, slot_sy + slot_size - 2], fill=(70, 70, 70, 255))

    # Paste item texture with nearest-neighbor scaling
    path = os.path.join(asset_dir, asset_file)
    if os.path.exists(path):
        item_img = Image.open(path).convert("RGBA")
        # Upscale to 36x36
        item_img = item_img.resize((36, 36), Image.Resampling.NEAREST)
        img.paste(item_img, (cur_x + 5, slot_sy + 5), item_img)

# Card 2 Subtitle / Attribution
draw.text((c2_x0 + 16, c2_y0 + 104), "Open Source • MIT License • Built by cbladeOfficial & debarkak", font=f_small, fill=(148, 163, 184, 255))
draw.text((c2_x1 - 165, c2_y0 + 104), "open-fiestasmp/FiestaPanel", font=f_mono, fill=(56, 189, 248, 255))

# Save image
out_dir = "/home/ubuntu/fiesta-portal/assets"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "banner.png")
img.save(out_path, "PNG", optimize=True)
print(f"Generated banner at {out_path} ({os.path.getsize(out_path)} bytes)")
