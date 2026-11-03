#!/usr/bin/env python3
"""
FiestaPanel GitHub Banner Generator
Produces high-resolution (1280x640) OpenGraph and README hero banner
featuring authentic Windows 7 Aero Glass aesthetics and Minecraft asset showcase.
"""
import math
import os
import random
import urllib.request
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH = 1280
HEIGHT = 640

# 1. Base Canvas & Deep Space Background
img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 10, 20, 255))
draw = ImageDraw.Draw(img)

# Deep space cyber gradient
for y in range(HEIGHT):
    factor = y / HEIGHT
    r = int(12 * (1 - factor) + 5 * factor)
    g = int(22 * (1 - factor) + 8 * factor)
    b = int(45 * (1 - factor) + 18 * factor)
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

# Ambient radial glow backlights
glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
g_draw = ImageDraw.Draw(glow)

# Top-center Aero Blue glow
cx, cy = 560, 220
for rad in range(420, 0, -12):
    alpha = int(55 * (1 - rad / 420))
    g_draw.ellipse([cx - rad, cy - int(rad * 0.65), cx + rad, cy + int(rad * 0.65)], fill=(14, 165, 233, alpha))

# Top-right Violet glow
cx2, cy2 = 1100, 150
for rad in range(380, 0, -12):
    alpha = int(48 * (1 - rad / 380))
    g_draw.ellipse([cx2 - rad, cy2 - int(rad * 0.65), cx2 + rad, cy2 + int(rad * 0.65)], fill=(139, 92, 246, alpha))

# Bottom-left Emerald glow
cx3, cy3 = 180, 560
for rad in range(300, 0, -12):
    alpha = int(35 * (1 - rad / 300))
    g_draw.ellipse([cx3 - rad, cy3 - rad, cx3 + rad, cy3 + rad], fill=(16, 185, 129, alpha))

img = Image.alpha_composite(img, glow)
draw = ImageDraw.Draw(img)

# Soft starry particle points (clean, subtle ambient depth)
random.seed(42)
for _ in range(85):
    sx = random.randint(15, WIDTH - 15)
    sy = random.randint(15, HEIGHT - 15)
    s_alpha = random.randint(15, 65)
    s_rad = random.choice([1, 1, 1, 2])
    draw.ellipse([sx - s_rad, sy - s_rad, sx + s_rad, sy + s_rad], fill=(255, 255, 255, s_alpha))

# 2. Typography & Fonts
font_dir = "/usr/share/fonts/truetype/liberation"
f_hero = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 50)
f_tag = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 11)
f_sub = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 18)
f_desc = ImageFont.truetype(f"{font_dir}/LiberationSans-Regular.ttf", 14)
f_pill = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 12)
f_card_h = ImageFont.truetype(f"{font_dir}/LiberationSans-Bold.ttf", 13)
f_card_label = ImageFont.truetype(f"{font_dir}/LiberationSans-Regular.ttf", 12)
f_card_mono = ImageFont.truetype(f"{font_dir}/LiberationMono-Bold.ttf", 12)
f_cmd = ImageFont.truetype(f"{font_dir}/LiberationMono-Bold.ttf", 11.5)
f_cmd_sub = ImageFont.truetype(f"{font_dir}/LiberationMono-Regular.ttf", 10.5)
f_small = ImageFont.truetype(f"{font_dir}/LiberationSans-Regular.ttf", 11.5)
f_small_mono = ImageFont.truetype(f"{font_dir}/LiberationMono-Bold.ttf", 11.5)

# Dynamic Server Software Version Detection
def get_banner_version():
    try:
        req = urllib.request.Request("https://fill.papermc.io/v3/projects/paper", headers={"User-Agent": "FiestaPanel/2.1"})
        with urllib.request.urlopen(req, timeout=3) as r:
            d = json.loads(r.read())
            v_dict = d.get("versions", {})
            for group, vers in v_dict.items():
                for v in vers:
                    if "-" not in v:
                        return f"Paper {v}"
    except Exception:
        pass
    return "Paper 26.3"

banner_version = get_banner_version()

# 3. Main Windows 7 Aero Glass Window
wx0, wy0 = 48, 30
wx1, wy1 = WIDTH - 48, HEIGHT - 30

# Ambient Drop Shadow
shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
s_draw = ImageDraw.Draw(shadow)
s_draw.rounded_rectangle([wx0 + 8, wy0 + 12, wx1 + 8, wy1 + 16], radius=18, fill=(0, 0, 0, 210))
shadow = shadow.filter(ImageFilter.GaussianBlur(28))
img = Image.alpha_composite(img, shadow)

# Window Base Frame
win = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
w_draw = ImageDraw.Draw(win)
w_draw.rounded_rectangle([wx0, wy0, wx1, wy1], radius=16, fill=(10, 17, 32, 248), outline=(56, 189, 248, 180), width=2)

# Titlebar (Aero Glass header with specular reflection sheen)
th = 50
for ty in range(th):
    frac = ty / th
    if frac < 0.48:
        val = int(225 + (1 - frac) * 30)
        c = (35, 95, 172, val)
    else:
        c = (12, 45, 96, 245)
    w_draw.line([(wx0 + 2, wy0 + 2 + ty), (wx1 - 2, wy0 + 2 + ty)], fill=c)

# Specular shine highlights
w_draw.line([(wx0 + 2, wy0 + int(th * 0.48)), (wx1 - 2, wy0 + int(th * 0.48))], fill=(255, 255, 255, 80))
w_draw.line([(wx0 + 16, wy0 + 2), (wx1 - 16, wy0 + 2)], fill=(255, 255, 255, 150))

# Window Controls (Right side buttons)
bx = wx1 - 32
by = wy0 + 15
# Close button (Glowing ruby red 3D glass)
w_draw.rounded_rectangle([bx - 12, by - 6, bx + 16, by + 14], radius=3, fill=(225, 29, 72, 240), outline=(255, 255, 255, 140))
w_draw.line([(bx - 3, by), (bx + 7, by + 8)], fill=(255, 255, 255, 255), width=2)
w_draw.line([(bx - 3, by + 8), (bx + 7, by)], fill=(255, 255, 255, 255), width=2)

# Maximize button
bx -= 36
w_draw.rounded_rectangle([bx - 12, by - 6, bx + 16, by + 14], radius=3, fill=(30, 64, 175, 190), outline=(255, 255, 255, 90))
w_draw.rectangle([bx - 3, by + 1, bx + 7, by + 7], outline=(255, 255, 255, 255), width=1)

# Minimize button
bx -= 36
w_draw.rounded_rectangle([bx - 12, by - 6, bx + 16, by + 14], radius=3, fill=(30, 64, 175, 190), outline=(255, 255, 255, 90))
w_draw.line([(bx - 3, by + 7), (bx + 7, by + 7)], fill=(255, 255, 255, 255), width=2)

# Titlebar Left Icon (Glowing Aero Orb)
w_draw.ellipse([wx0 + 16, wy0 + 11, wx0 + 42, wy0 + 37], fill=(14, 165, 233, 255), outline=(255, 255, 255, 220), width=2)
w_draw.line([(wx0 + 23, wy0 + 31), (wx0 + 36, wy0 + 17)], fill=(255, 255, 255, 255), width=2)
w_draw.arc([wx0 + 26, wy0 + 15, wx0 + 38, wy0 + 27], start=180, end=270, fill=(255, 255, 255, 255), width=3)

# Titlebar Text
w_draw.text((wx0 + 52, wy0 + 16), "FiestaPanel • Next-Gen Minecraft Server Suite [Windows 7 Aero Edition]", font=f_card_h, fill=(240, 248, 255, 255))

img = Image.alpha_composite(img, win)
draw = ImageDraw.Draw(img)

# 4. Hero Content Header
hx = wx0 + 44
hy = wy0 + 72

# Category Tag
tag_text = "NEXT-GEN MINECRAFT SERVER MANAGEMENT CONSOLE"
tag_bbox = draw.textbbox((hx, hy), tag_text, font=f_tag)
tw = tag_bbox[2] - tag_bbox[0]
draw.rounded_rectangle([hx, hy, hx + tw + 22, hy + 22], radius=11, fill=(14, 165, 233, 40), outline=(56, 189, 248, 160), width=1)
draw.text((hx + 11, hy + 4), tag_text, font=f_tag, fill=(56, 189, 248, 255))

# Hero Title: Fiesta (White) + Panel (Cyan)
y_title = hy + 28
draw.text((hx, y_title), "Fiesta", font=f_hero, fill=(255, 255, 255, 255))
bbox_fiesta = draw.textbbox((hx, y_title), "Fiesta", font=f_hero)
draw.text((bbox_fiesta[2] + 4, y_title), "Panel", font=f_hero, fill=(56, 189, 248, 255))

# Subtitle
y_sub = y_title + 58
draw.text((hx, y_sub), "The High-Performance Modern & Retro Web Console for Minecraft Communities", font=f_sub, fill=(147, 197, 253, 255))

# Tagline
y_tag = y_sub + 27
draw.text((hx, y_tag), "Windows 7 Aero Glass & Retro TP-Link UI   •   1-Click Multi-Engine 26.3   •   Turnkey Docker & CLI", font=f_desc, fill=(148, 163, 184, 255))

# High-contrast Feature Badges (solid dark translucent backgrounds + crisp vibrant borders)
pills = [
    ("● Windows 7 Aero", (56, 189, 248), (224, 242, 254)),
    ("● Retro TP-Link", (34, 197, 94), (220, 252, 231)),
    ("● Visual Inventory", (249, 115, 22), (255, 237, 213)),
    ("● Modrinth Engine", (20, 184, 166), (204, 251, 241)),
    ("● Docker & Turnkey", (168, 85, 247), (243, 232, 255)),
]

px = hx
py = y_tag + 28
for text, border_col, text_col in pills:
    bbox = draw.textbbox((px, py), text, font=f_pill)
    pw = bbox[2] - bbox[0]
    draw.rounded_rectangle([px, py, px + pw + 18, py + 26], radius=6, fill=(12, 22, 40, 240), outline=border_col, width=1)
    draw.text((px + 9, py + 5), text, font=f_pill, fill=text_col)
    px += pw + 28

# 5. Bottom Showcase Cards (Card 1: Telemetry & Install, Card 2: Visual Inventory & Assets)
card_y0 = 368
card_y1 = wy1 - 24

# Left Card: Telemetry & Turnkey Install Box
c1_x0 = wx0 + 40
c1_x1 = c1_x0 + 530
draw.rounded_rectangle([c1_x0, card_y0, c1_x1, card_y1], radius=10, fill=(13, 21, 38, 240), outline=(51, 65, 85, 240), width=1)

# Card 1 Status Pill
draw.ellipse([c1_x0 + 18, card_y0 + 16, c1_x0 + 28, card_y0 + 26], fill=(34, 197, 94, 255))
draw.text((c1_x0 + 36, card_y0 + 14), f"SERVER ONLINE   •   {banner_version}   •   TPS: 20.0 (Optimal)", font=f_card_h, fill=(248, 250, 252, 255))

# CPU Progress Bar
draw.text((c1_x0 + 18, card_y0 + 44), "CPU Usage", font=f_card_label, fill=(148, 163, 184, 255))
draw.rounded_rectangle([c1_x0 + 98, card_y0 + 48, c1_x0 + 395, card_y0 + 56], radius=4, fill=(24, 34, 53, 255))
draw.rounded_rectangle([c1_x0 + 98, card_y0 + 48, c1_x0 + 170, card_y0 + 56], radius=4, fill=(56, 189, 248, 255))
draw.text((c1_x0 + 410, card_y0 + 44), "24%", font=f_card_mono, fill=(224, 242, 254, 255))

# Memory Progress Bar
draw.text((c1_x0 + 18, card_y0 + 70), "Memory", font=f_card_label, fill=(148, 163, 184, 255))
draw.rounded_rectangle([c1_x0 + 98, card_y0 + 74, c1_x0 + 395, card_y0 + 82], radius=4, fill=(24, 34, 53, 255))
draw.rounded_rectangle([c1_x0 + 98, card_y0 + 74, c1_x0 + 252, card_y0 + 82], radius=4, fill=(192, 132, 252, 255))
draw.text((c1_x0 + 410, card_y0 + 70), "4.2 / 8.0 GB (52%)", font=f_card_mono, fill=(243, 232, 255, 255))

# 1-Line Turnkey Box
cmd_y0 = card_y0 + 104
draw.rounded_rectangle([c1_x0 + 14, cmd_y0, c1_x1 - 14, cmd_y0 + 58], radius=6, fill=(2, 6, 23, 245), outline=(14, 165, 233, 190), width=1)
draw.text((c1_x0 + 22, cmd_y0 + 10), "$ curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash", font=f_cmd, fill=(56, 189, 248, 255))
draw.text((c1_x0 + 22, cmd_y0 + 32), "Windows: irm https://fiesta.debarkak.xyz/install.ps1 | iex   •   Docker Ready", font=f_cmd_sub, fill=(148, 163, 184, 255))

# Right Card: Visual Inventory & Texture Engine
c2_x0 = c1_x1 + 24
c2_x1 = wx1 - 40
draw.rounded_rectangle([c2_x0, card_y0, c2_x1, card_y1], radius=10, fill=(13, 21, 38, 240), outline=(51, 65, 85, 240), width=1)

# Card 2 Header
draw.text((c2_x0 + 20, card_y0 + 14), "Visual Inventory Inspector (1,300+ Textures)", font=f_card_h, fill=(248, 250, 252, 255))

# Minecraft slot shelf background
slot_sx = c2_x0 + 42
slot_sy = card_y0 + 44
slot_size = 46
shelf_w = 7 * slot_size + 6 * 14 + 16
draw.rounded_rectangle([slot_sx - 8, slot_sy - 6, slot_sx - 8 + shelf_w, slot_sy + slot_size + 6], radius=6, fill=(7, 12, 22, 240), outline=(30, 41, 59, 200))

# Minecraft slot grid with genuine textures
mc_assets = [
    "netherite_sword.png",
    "totem_of_undying.png",
    "enchanted_golden_apple.png",
    "enchanted_book.png",
    "diamond_sword.png",
    "netherite_chestplate.png",
    "ender_eye.png"
]
asset_dir = "/home/ubuntu/fiesta-portal/static/mcassets"

for idx, asset_file in enumerate(mc_assets):
    cur_x = slot_sx + idx * (slot_size + 14)
    # Beveled authentic Minecraft inventory slot
    draw.rectangle([cur_x, slot_sy, cur_x + slot_size, slot_sy + slot_size], fill=(139, 139, 139, 255), outline=(55, 55, 55, 255), width=2)
    draw.rectangle([cur_x + 2, slot_sy + 2, cur_x + slot_size - 2, slot_sy + slot_size - 2], fill=(68, 68, 68, 255))

    path = os.path.join(asset_dir, asset_file)
    if os.path.exists(path):
        item_img = Image.open(path).convert("RGBA")
        item_img = item_img.resize((34, 34), Image.Resampling.NEAREST)
        img.paste(item_img, (cur_x + 6, slot_sy + 6), item_img)

# Card 2 Attribution and Repository Info
draw.text((c2_x0 + 20, card_y0 + 112), "MIT License   •   Maintained by cbladeOfficial & debarkak", font=f_small, fill=(148, 163, 184, 255))
draw.text((c2_x0 + 20, card_y0 + 134), "github.com/open-fiestasmp/FiestaPanel   •   Turnkey Deployment", font=f_small_mono, fill=(56, 189, 248, 255))

# 6. Save Banner to assets/ and static/
out_dir = "/home/ubuntu/fiesta-portal/assets"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "banner.png")
img.save(out_path, "PNG", optimize=True)
print(f"Generated hero banner at {out_path} ({os.path.getsize(out_path)} bytes)")

static_dir = "/home/ubuntu/fiesta-portal/static"
os.makedirs(static_dir, exist_ok=True)
static_path = os.path.join(static_dir, "banner.png")
img.save(static_path, "PNG", optimize=True)
print(f"Synced hero banner to {static_path} ({os.path.getsize(static_path)} bytes)")
