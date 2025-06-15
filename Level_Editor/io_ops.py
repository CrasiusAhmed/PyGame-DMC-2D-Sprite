# io_ops.py
import json, shutil
import csv
import os
import tkinter as tk
from tkinter import filedialog

def save(map_data, background, filename="level.json"):
    """
    Save both:
      • map_data: 2D list of ints
      • backgrounds: list of background filenames (ordered front-to-back)
    into a single JSON file.
    """
    payload = {
        "map_data": map_data,
        "backgrounds": background
    }
    with open(filename, "w") as f:
        json.dump(payload, f)
    print(f"Saved level → {filename}")

def load(filename="level.json"):
    """
    Load and return (map_data, backgrounds).
    If the file is just a list (old format), treats it as map_data only.
    """
    with open(filename, "r") as f:
        payload = json.load(f)
    print(f"Loaded level ← {filename}")

    if isinstance(payload, list):
        # old format: just map_data
        return payload, []
    return payload.get("map_data", []), payload.get("backgrounds", [])

def export_all_levels(levels, backgrounds_list,
                      tile_folder="img/tile",
                      bg_folder="img/background",
                      out_root="exported_levels"):
    """
    For each level index i:
      • writes exported_levels/level{i}/map.csv
      • writes exported_levels/level{i}/backgrounds.json
      • copies each bg image into that folder
      • (optionally) copies all tile images so the game can run standalone
    """
    for i, (map_data, bg_paths) in enumerate(zip(levels, backgrounds_list)):
        folder = os.path.join(out_root, f"level{i}")
        os.makedirs(folder, exist_ok=True)

        # 1) map.csv - adjust tile indices for game (subtract 1 from non-empty tiles)
        with open(os.path.join(folder, "map.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            # Convert editor indices to game indices
            # Editor: 0=ADD_ICON, 1=first_tile, 2=second_tile, etc.
            # Game:   0=first_tile, 1=second_tile, etc., -1=empty
            adjusted_map = []
            print(f"Exporting level {i} - converting tile indices:")
            for row_idx, row in enumerate(map_data):
                adjusted_row = []
                for col_idx, cell in enumerate(row):
                    if cell == -1:  # Empty cell
                        adjusted_row.append(-1)
                    elif cell == 0:  # ADD_ICON (shouldn't be placed, but treat as empty)
                        adjusted_row.append(-1)
                        if cell != -1:  # Only print if there was actually a tile there
                            print(f"  Row {row_idx}, Col {col_idx}: Editor index {cell} -> Game index -1 (ADD_ICON treated as empty)")
                    else:  # Actual tile (subtract 1 to convert to game index)
                        game_index = cell - 1
                        adjusted_row.append(game_index)
                        print(f"  Row {row_idx}, Col {col_idx}: Editor index {cell} -> Game index {game_index}")
                adjusted_map.append(adjusted_row)
            writer.writerows(adjusted_map)

        # 2) backgrounds.json
        basenames = []
        for full in bg_paths:
            name = os.path.basename(full)
            basenames.append(name)
            dest = os.path.join(folder, name)
            if not os.path.exists(dest):
                shutil.copy(full, dest)
        with open(os.path.join(folder, "backgrounds.json"), "w") as f:
            json.dump(basenames, f)

        # 3) Copy tile images in the same order as the editor loads them
        tiles_out = os.path.join(folder, "tiles")
        os.makedirs(tiles_out, exist_ok=True)
        
        # Get tiles in the same order as editor (sorted numerically)
        tile_files = [
            f for f in os.listdir(tile_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        
        # Sort numerically by extracting numbers from filenames
        def numeric_sort_key(filename):
            import re
            numbers = re.findall(r'\d+', filename)
            if numbers:
                return int(numbers[0])
            return float('inf')
        
        tile_files.sort(key=numeric_sort_key)
        
        print(f"Exporting {len(tile_files)} tiles in correct numeric order:")
        for idx, filename in enumerate(tile_files):
            print(f"  Game index {idx}: {filename}")
            src = os.path.join(tile_folder, filename)
            dst = os.path.join(tiles_out, filename)
            if not os.path.exists(dst):
                shutil.copy(src, dst)

        print(f"Exported level {i} → {folder}")

def save_project(levels, backgrounds_list, filename="project.json"):
    """
    Save entire multi-level project:
    • levels: list of 2D map arrays
    • backgrounds_list: list of background file lists for each level
    """
    # Get the directory where we'll save the project
    project_dir = os.path.dirname(filename)
    os.makedirs(project_dir, exist_ok=True)
    
    # Copy all background files to project directory and get basenames
    project_backgrounds = []
    for level_idx, bg_paths in enumerate(backgrounds_list):
        level_basenames = []
        for bg_path in bg_paths:
            if bg_path and os.path.exists(bg_path):
                basename = os.path.basename(bg_path)
                dest_path = os.path.join(project_dir, basename)
                if not os.path.exists(dest_path):
                    shutil.copy(bg_path, dest_path)
                level_basenames.append(basename)
        project_backgrounds.append(level_basenames)
    
    # Create project payload
    payload = {
        "levels": levels,
        "backgrounds": project_backgrounds,
        "level_count": len(levels)
    }
    
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved project ({len(levels)} levels) → {filename}")

def load_project(filename="project.json"):
    """
    Load entire multi-level project.
    Returns (levels, backgrounds_list) or (None, None) if failed.
    """
    if not os.path.exists(filename):
        return None, None
        
    try:
        with open(filename, "r") as f:
            payload = json.load(f)
        
        project_dir = os.path.dirname(filename)
        levels = payload.get("levels", [])
        background_basenames = payload.get("backgrounds", [])
        
        # Rebuild full paths for backgrounds
        backgrounds_list = []
        for level_basenames in background_basenames:
            level_fullpaths = []
            for basename in level_basenames:
                if basename:
                    fullpath = os.path.join(project_dir, basename)
                    level_fullpaths.append(fullpath)
            backgrounds_list.append(level_fullpaths)
        
        print(f"Loaded project ({len(levels)} levels) ← {filename}")
        return levels, backgrounds_list
        
    except Exception as e:
        print(f"Failed to load project {filename}: {e}")
        return None, None

def import_level():
    """
    Pops up a folder dialog, reads map.csv & backgrounds.json
    Returns (map_data, backgrounds) or (None, None) if canceled.
    """
    root = tk.Tk(); root.withdraw()
    folder = filedialog.askdirectory(title="Select level folder to import (e.g., exported_levels/level0)")
    if not folder:
        return None, None

    # Read map.csv
    map_csv = os.path.join(folder, "map.csv")
    if not os.path.exists(map_csv):
        print(f"Error: map.csv not found in {folder}")
        print("Make sure you select a level folder (like exported_levels/level0) that contains map.csv")
        return None, None
        
    try:
        new_map = []
        with open(map_csv, newline="") as f:
            for row in csv.reader(f):
                new_map.append([int(x) for x in row])
    except Exception as e:
        print(f"Error reading map.csv: {e}")
        return None, None

    # Read backgrounds.json (if exists)
    bg_json = os.path.join(folder, "backgrounds.json")
    new_bgs = []
    if os.path.exists(bg_json):
        try:
            with open(bg_json) as f:
                basenames = json.load(f)
            # Convert basenames to full paths
            for basename in basenames:
                full_path = os.path.join(folder, basename)
                if os.path.exists(full_path):
                    new_bgs.append(full_path)
                else:
                    print(f"Warning: Background file {basename} not found in {folder}")
        except Exception as e:
            print(f"Error reading backgrounds.json: {e}")

    print(f"Imported level from {folder} (map: {len(new_map)}x{len(new_map[0]) if new_map else 0}, backgrounds: {len(new_bgs)})")
    return new_map, new_bgs



# What it does:

    # save_level/load_level: JSON‐backed persistence of your 2D array.

    # create_new_level: Quick factory for a blank ROWS×COLS map.

    # import_level: Placeholder—you’ll hook in your DB or other format here.