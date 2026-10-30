import os
import json
import xml.etree.ElementTree as ET

def parse_wz_xml(file_path):
    """Recursively parses a WZ XML dump into a native Python dictionary structure."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # WZ XML exports typically store values under an 'imgdir' root node
        imgdir = root.find("imgdir")
        if imgdir is not None:
            return parse_xml_node(imgdir)
        return parse_xml_node(root)
    except Exception as e:
        return {}

def parse_xml_node(element):
    """Helper method to convert XML nodes into typed key-value pairs."""
    node_data = {}
    for child in element:
        name = child.attrib.get("name")
        if not name:
            continue
            
        if child.tag == "imgdir":
            node_data[name] = parse_xml_node(child)
        else:
            value = child.attrib.get("value")
            if child.tag in ["int", "short", "long"]:
                try:
                    node_data[name] = int(value)
                except:
                    node_data[name] = 0
            elif child.tag in ["float", "double"]:
                try:
                    node_data[name] = float(value)
                except:
                    node_data[name] = 0.0
            elif child.tag in ["vector", "canvas"]:
                # Vectors handle geometric coordinates like x/y values
                node_data[name] = {
                    "x": int(child.attrib.get("x", 0)),
                    "y": int(child.attrib.get("y", 0))
                }
            else:
                node_data[name] = value
    return node_data

def build_master_database_from_xml():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    maps_folder = os.path.join(base_dir, "Map", "Map.wz")
    mobs_folder = os.path.join(base_dir, "Mob", "Mob.wz")
    output_file = os.path.join(base_dir, "master_navigation_db.json")
    
    print("====================================================")
    print("   MAPLESTORY AI XML COMPILATION ENGINE             ")
    print("====================================================")
    
    # 1. Map Monster Stats out of XML dumps
    mob_metadata_cache = {}
    print("[INIT] Scanning Mob.wz folder for XML property trees...")
    
    if os.path.exists(mobs_folder):
        for root, dirs, files in os.walk(mobs_folder):
            for file in files:
                if file.endswith(".xml"):
                    mob_id = file.replace(".img.xml", "").replace(".xml", "").lstrip("0")
                    if not mob_id:
                        continue
                        
                    data = parse_wz_xml(os.path.join(root, file))
                    info_block = data.get("info", {})
                    
                    mob_metadata_cache[mob_id] = {
                        "level": info_block.get("level", 1),
                        "max_hp": info_block.get("maxHP", 1),
                        "exp": info_block.get("exp", 0),
                        "fly": "fly" in data
                    }
        print(f"[SUCCESS] Indexed metadata properties for {len(mob_metadata_cache)} unique monsters.")
    
    # 2. Process Map Folder Tree
    master_registry = {}
    print("\n[PROCESSING] Scanning Map.wz folder for structural nodes...")
    
    if not os.path.exists(maps_folder):
        print(f"[CRITICAL ERROR] Could not find Map.wz folder at: {maps_folder}")
        return

    for root, dirs, files in os.walk(maps_folder):
        for file in files:
            # We target structural map data frames while ignoring generic configuration fragments
            if file.endswith(".xml") and file.split(".")[0].isdigit():
                map_id = file.replace(".img.xml", "").replace(".xml", "").lstrip("0")
                map_data = parse_wz_xml(os.path.join(root, file))
                
                map_info = map_data.get("info", {})
                street_name = map_info.get("streetName", "Unknown Region")
                map_title = map_info.get("mapName", f"Map Node {map_id}")
                map_name_key = f"{street_name}: {map_title}".strip().lower()

                # Extract Footholds
                imported_platforms = []
                for layer_id, layer in map_data.get("foothold", {}).items():
                    if isinstance(layer, dict):
                        for group_id, group in layer.items():
                            if isinstance(group, dict):
                                for fh_id, fh in group.items():
                                    if isinstance(fh, dict):
                                        x1 = fh.get("x1", 0)
                                        x2 = fh.get("x2", 0)
                                        y1 = fh.get("y1", 0)
                                        imported_platforms.append({
                                            "name": f"Platform Node {fh_id}",
                                            "y_level": abs(y1) % 100,
                                            "x_min": min(abs(x1) % 100, abs(x2) % 100),
                                            "x_max": max(abs(x1) % 100, abs(x2) % 100)
                                        })

                # Calculate layout scaling bounds
                if imported_platforms:
                    all_x = [p["x_min"] for p in imported_platforms] + [p["x_max"] for p in imported_platforms]
                    min_x, max_x = min(all_x), max(all_x)
                else:
                    min_x, max_x = -2000, 2000
                map_width = max(1, max_x - min_x)

                # Extract Ladders / Ropes
                imported_markers = {}
                for idx, (node_key, rope) in enumerate(map_data.get("ladderRope", {}).items()):
                    if isinstance(rope, dict):
                        rx = rope.get("x", 0)
                        y1 = rope.get("y1", 0)
                        y2 = rope.get("y2", 0)
                        is_ladder = rope.get("l", 0) == 1
                        
                        screen_x = int(((rx - min_x) / map_width) * 1280)
                        screen_y = int(((y1 + 1000) / 2000) * 960)
                        box_w = 20  
                        box_h = int(abs(y2 - y1) / 2000 * 960)
                        
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

                # Link Monster Spawn Nodes
                active_mobs_list = {}
                for life_node in map_data.get("life", {}).values():
                    if isinstance(life_node, dict) and life_node.get("type") == "m":
                        m_id = str(life_node.get("id")).lstrip("0")
                        if m_id and m_id not in active_mobs_list:
                            active_mobs_list[m_id] = mob_metadata_cache.get(m_id, {
                                "level": "Unknown", "max_hp": "Unknown", "exp": 0, "fly": False
                            })

                master_registry[map_name_key] = {
                    "map_id": map_id,
                    "mobs": active_mobs_list if active_mobs_list else {"None": {}},
                    "platforms": imported_platforms if imported_platforms else [{"name": "Ground Floor", "y_level": 85, "x_min": 5, "x_max": 95}],
                    "markers": imported_markers
                }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(master_registry, f, indent=2)
        
    print("\n====================================================")
    print(f"[COMPLETE] Database merged into: {output_file}")
    print(f"[SUMMARY] Successfully structured data fields for {len(master_registry)} maps!")
    print("====================================================")

if __name__ == "__main__":
    build_master_database_from_xml()
