import os
import json

def import_map_from_local_dump(map_id, custom_map_name=None):
    """
    Reads a local map JSON dump, extracts footholds, ropes/ladders,
    AND automatically extracts the exact monster IDs spawning on this map.
    """
    file_name = "map_spawns.json"
    base_game_dir = r"E:\SteamLibrary\steamapps\common\MapleStory"
    
    first_digit = map_id[0] if len(map_id) > 0 else "0"
    local_dump_path = os.path.join(base_game_dir, "wz_dump", "Map", "Map", f"Map{first_digit}", f"{map_id}.img.json")

    print(f"[DATA] Reading local game data dump for Map ID: {map_id}...")
    
    if not os.path.exists(local_dump_path):
        print(f"[ERROR] Missing decoded map file at: {local_dump_path}")
        return False
        
    try:
        with open(local_dump_path, "r", encoding="utf-8") as f:
            map_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read structural JSON properties: {e}")
        return False

    # 1. Dynamically extract monster IDs from the 'life' block
    extracted_mob_ids = []
    for life_node in map_data.get("life", {}).values():
        if life_node.get("type") == "m":
            mob_id = life_node.get("id")
            if mob_id and mob_id not in extracted_mob_ids:
                extracted_mob_ids.append(str(int(mob_id)))

    if not extracted_mob_ids:
        extracted_mob_ids = ["None Found"]

    # 2. Extract map metadata names
    map_info = map_data.get("info", {})
    map_name = custom_map_name
    if not map_name:
        street_name = map_info.get("streetName", "Unknown Region")
        map_title = map_info.get("mapName", f"Map Node {map_id}")
        map_name = f"{street_name} {map_title}".strip().lower()
        
    print(f"[PROCESSING] Structural layout found: '{map_name.upper()}'")
    print(f"[MOBS FOUND] Automatically targeted monster IDs: {extracted_mob_ids}")

    # 3. Extract footholds
    imported_platforms = []
    for layer in map_data.get("foothold", {}).values():
        for group in layer.values():
            for fh_id, fh in group.items():
                x1, x2, y1 = fh.get("x1", 0), fh.get("x2", 0), fh.get("y1", 0)
                imported_platforms.append({
                    "name": f"Platform Node {fh_id}",
                    "y_level": abs(y1) % 100,
                    "x_min": min(abs(x1) % 100, abs(x2) % 100),
                    "x_max": max(abs(x1) % 100, abs(x2) % 100)
                })

    # 4. Extract ladders/ropes 
    imported_markers = {}
    if imported_platforms:
        all_x = [p["x_min"] for p in imported_platforms] + [p["x_max"] for p in imported_platforms]
        min_x, max_x = min(all_x), max(all_x)
    else:
        min_x, max_x = -2000, 2000
    map_width = max(1, max_x - min_x)
    
    for idx, (node_key, rope) in enumerate(map_data.get("ladderRope", {}).items()):
        rx = rope.get("x", 0)
        y1 = rope.get("y1", 0)
        y2 = rope.get("y2", 0)
        is_ladder = rope.get("l", 0) == 1
        
        screen_x = int(((rx - min_x) / map_width) * 1280)
        screen_y = int(((y1 + 1000) / 2000) * 960)
        box_w = 20  
        box_h = int(abs(y2 - y1) / 2000 * 960)
        
        # Fixed explicit color definitions
        if is_ladder:
            prop_color = Yellow [R, G, B]
            prop_type = "Ladder"
        else:
            prop_color = Blue [R, G, B]
            prop_type = "Rope"
        
        marker_key = f"rope_node_{idx}"
        imported_markers[marker_key] = {
            "rect": [max(10, min(screen_x, 1200)), max(10, min(screen_y, 900)), box_w, max(20, box_h)],
            "color": prop_color, 
            "label": f"{prop_type} Prop #{idx}"
        }

    # 5. Merge into local map_spawns.json database
    existing_database = {}
    if os.path.exists(file_name) and os.path.getsize(file_name) > 10:
        try:
            with open(file_name, "r") as f:
                existing_database = json.load(f)
        except:
            pass

    existing_database[map_name] = {
        "mobs": extracted_mob_ids,
        "platforms": imported_platforms if imported_platforms else [{"name": "Ground Floor", "y_level": 85, "x_min": 5, "x_max": 95}],
        "markers": imported_markers
    }

    with open(file_name, "w") as f:
        json.dump(existing_database, f, indent=2)
        
    print(f"[SUCCESS] Merged '{map_name}' into {file_name}. Logged {len(extracted_mob_ids)} unique monster types.")
    return True

if __name__ == "__main__":
    print("====================================================")
    print("   MAPLESTORY STEAM WZ AUTO-LIFE IMPORT SYSTEM")
    print("====================================================")
    user_map_id = input("Enter target Map ID (e.g., 10004080): ").strip()
    user_map_name = input("Enter clean OCR-matching name (Leave blank for automatic): ").strip()
    
    if user_map_id.isdigit():
        custom_name = user_map_name if user_map_name else None
        import_map_from_local_dump(user_map_id, custom_map_name=custom_name)
    else:
        print("[!] Invalid input. Map ID must be numbers.")
    print("====================================================\n")
