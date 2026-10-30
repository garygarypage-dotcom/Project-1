import os
import json

def build_master_database():
    """
    Scans the dumped maps and mobs folders inside ms_ai to compile a comprehensive,
    fully mapped master navigation and spawn database.
    """
    # 1. Establish strict path locations relative to this script inside ms_ai
    base_dir = os.path.dirname(os.path.abspath(__file__))
    maps_folder = os.path.join(base_dir, "Map")
    mobs_folder = os.path.join(base_dir, "Mob")
    output_file = os.path.join(base_dir, "master_navigation_db.json")
    
    print("====================================================")
    print("   MAPLESTORY AI DATABASE COMPILATION ENGINE        ")
    print("====================================================")
    
    # 2. Build a local caching dictionary for monster metadata
    mob_metadata_cache = {}
    print("[INIT] Scanning local Mob directory for entity stats...")
    
    if os.path.exists(mobs_folder):
        for file in os.listdir(mobs_folder):
            if file.endswith(".json"):
                # Clean up ID formatting (e.g., '0100100.img.json' or '100100.json' -> '100100')
                mob_id = file.split(".")[0].lstrip("0")
                if not mob_id:
                    continue
                    
                try:
                    with open(os.path.join(mobs_folder, file), "r", encoding="utf-8") as f:
                        mob_data = json.load(f)
                        info_block = mob_data.get("info", {})
                        
                        # Cache the most important battle stats for pathfinding calculations
                        mob_metadata_cache[mob_id] = {
                            "level": info_block.get("level", 1),
                            "max_hp": info_block.get("maxHP", 1),
                            "exp": info_block.get("exp", 0),
                            "fly": "fly" in mob_data # Flying mobs ignore traditional platform footholds
                        }
                except Exception as e:
                    # Skip corrupt files safely
                    continue
        print(f"[SUCCESS] Indexed metadata properties for {len(mob_metadata_cache)} unique monsters.")
    else:
        print("[WARNING] 'Mob' data folder not detected in ms_ai. Skipping stats mapping.")

    # 3. Process the full Map directory tree
    master_registry = {}
    print("\n[PROCESSING] Scanning Map folders to compile navigation paths...")
    
    if not os.path.exists(maps_folder):
        print(f"[CRITICAL ERROR] Could not find 'Map' folder at: {maps_folder}")
        return

    # Walk through the map sub-packages (e.g., Map/Map/Map1/)
    for root, dirs, files in os.walk(maps_folder):
        for file in files:
            if file.endswith(".json"):
                map_id = file.split(".")[0].lstrip("0")
                full_map_path = os.path.join(root, file)
                
                try:
                    with open(full_map_path, "r", encoding="utf-8") as f:
                        map_data = json.load(f)
                except:
                    continue

                # Parse the localized metadata name block
                map_info = map_data.get("info", {})
                street_name = map_info.get("streetName", "Unknown Region")
                map_title = map_info.get("mapName", f"Map Node {map_id}")
                map_name_key = f"{street_name}: {map_title}".strip().lower()

                # Extract explicit Footholds (Platforms)
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

                # Process absolute Rope and Ladder coordinate nodes
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
                    
                    # Apply explicit visual color markers [R, G, B]
                    if is_ladder:
                        prop_color = [255, 255, 0] # Yellow
                        prop_type = "Ladder"
                    else:
                        prop_color = [0, 0, 255] # Blue
                        prop_type = "Rope"
                    
                    marker_key = f"rope_node_{idx}"
                    imported_markers[marker_key] = {
                        "rect": [max(10, min(screen_x, 1200)), max(10, min(screen_y, 900)), box_w, max(20, box_h)],
                        "color": prop_color, 
                        "label": f"{prop_type} Prop #{idx}"
                    }

                # Link structural monster spawn listings to their cached metadata blocks
                active_mobs_list = {}
                for life_node in map_data.get("life", {}).values():
                    if life_node.get("type") == "m":
                        m_id = str(life_node.get("id")).lstrip("0")
                        if m_id and m_id not in active_mobs_list:
                            # Pull active stats from our cache if it exists, otherwise provide placeholders
                            active_mobs_list[m_id] = mob_metadata_cache.get(m_id, {
                                "level": "Unknown",
                                "max_hp": "Unknown",
                                "exp": 0,
                                "fly": False
                            })

                # Final map object creation
                master_registry[map_name_key] = {
                    "map_id": map_id,
                    "mobs": active_mobs_list if active_mobs_list else {"None": {}},
                    "platforms": imported_platforms if imported_platforms else [{"name": "Ground Floor", "y_level": 85, "x_min": 5, "x_max": 95}],
                    "markers": imported_markers
                }

    # 4. Flush compiled database package out to the local workspace
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(master_registry, f, indent=2)
        
    print("\n====================================================")
    print(f"[COMPLETE] Database merged into: {output_file}")
    print(f"[SUMMARY] Successfully structured data fields for {len(master_registry)} maps!")
    print("====================================================")

if __name__ == "__main__":
    build_master_database()
