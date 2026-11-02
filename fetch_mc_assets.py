#!/usr/bin/env python3
import os
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ASSET_DIR = "/home/ubuntu/fiesta-portal/static/mcassets"
os.makedirs(ASSET_DIR, exist_ok=True)

MAPPING_FILE = "/home/ubuntu/fiesta-portal/items_textures.json"

name_to_tex = {}
if os.path.exists(MAPPING_FILE):
    with open(MAPPING_FILE, "r") as f:
        for entry in json.load(f):
            n = entry.get("name")
            t = entry.get("texture")
            if n and t:
                name_to_tex[n] = t

# Special aliases and entity textures
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
    "mace", "wind_charge", "breeze_rod", "trial_key", "ominous_trial_key", "ominous_bottle"
]

all_items = set(name_to_tex.keys()).union(set(aliases.keys())).union(set(extra_items))

def fetch_single(item_name):
    dest = os.path.join(ASSET_DIR, f"{item_name}.png")
    if os.path.exists(dest) and os.path.getsize(dest) > 50:
        return True

    clean_name = item_name.lower().replace("minecraft:", "").strip()
    tex = aliases.get(clean_name) or name_to_tex.get(clean_name)

    candidates = []
    if tex:
        c1 = tex.replace("minecraft:", "").replace("items/", "item/")
        candidates.append(f"https://assets.mcasset.cloud/1.21.1/assets/minecraft/textures/{c1}.png")
        c2 = tex.replace("minecraft:", "")
        candidates.append(f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.21.1/{c2}.png")
        candidates.append(f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/1.21/assets/minecraft/textures/{c1}.png")

    candidates.extend([
        f"https://assets.mcasset.cloud/1.21.1/assets/minecraft/textures/item/{clean_name}.png",
        f"https://assets.mcasset.cloud/1.21.1/assets/minecraft/textures/block/{clean_name}.png",
        f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.21.1/items/{clean_name}.png",
        f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.21.1/blocks/{clean_name}.png",
        f"https://assets.mcasset.cloud/1.21.1/assets/minecraft/textures/entity/{clean_name}.png",
        f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/1.21/assets/minecraft/textures/item/{clean_name}.png",
        f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/1.21/assets/minecraft/textures/block/{clean_name}.png"
    ])

    for url in candidates:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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

print(f"Fetching textures for {len(all_items)} Minecraft items/blocks...")
with ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(fetch_single, list(all_items)))

success_count = sum(1 for r in results if r)
print(f"Finished! Successfully cached {success_count} / {len(all_items)} textures in {ASSET_DIR}")
