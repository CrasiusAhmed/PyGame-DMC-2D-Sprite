# main.py
# Purpose: Glue everything together; your actual game loop.
import pygame
import sys
from config       import *
from tiles        import load_tiles
from level_data   import create_empty
from io_ops       import save, load, export_all_levels, save_project, load_project
from ui           import Button
from renderer     import draw_grid
from menu         import TileMenu

import os
import shutil
import tkinter as tk
from tkinter import filedialog

TILE_FOLDER   = "img/tile"
ADD_ICON_PATH = "img/add.png"

pygame.init()
pygame.font.init()
font = pygame.font.SysFont(None, 24)

# database folder
SAVE_DIR   = "db"
os.makedirs(SAVE_DIR, exist_ok=True)

current_db = None   # path to the JSON we’re currently editing

# Load icon without convert:
icon_surf = pygame.image.load("img/Demon.png")
pygame.display.set_icon(icon_surf)

# Now create window:
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Level Editor")
clock = pygame.time.Clock()

# Level area - calculate grid first, then adjust level size to match exactly
LEVEL_W_CALC = int(WINDOW_WIDTH * LEVEL_W_FRAC)
LEVEL_H_CALC = int(WINDOW_HEIGHT * LEVEL_H_FRAC)
LEVEL_X, LEVEL_Y = 10, 10
COLS = LEVEL_W_CALC // TILE_SIZE
ROWS = LEVEL_H_CALC // TILE_SIZE

# Adjust level size to match grid exactly (no unused pixels)
LEVEL_W = COLS * TILE_SIZE
LEVEL_H = ROWS * TILE_SIZE

# Debug: Print level dimensions
print(f"Calculated level: {LEVEL_W_CALC}x{LEVEL_H_CALC}")
print(f"Adjusted level: {LEVEL_W}x{LEVEL_H}, Grid: {COLS}x{ROWS}, Tile size: {TILE_SIZE}")
print(f"Grid covers entire level area: {COLS * TILE_SIZE}x{ROWS * TILE_SIZE}")

# Load background
BG_FOLDER = "img/background"
default_bg = "img/background-editor.jpg"
backgrounds_paths = [default_bg]   # filepaths
backgrounds_surfs = []             # loaded & scaled Surfaces

def load_backgrounds():
    backgrounds_surfs.clear()
    for p in backgrounds_paths:
        surf = pygame.image.load(p).convert_alpha()
        surf = pygame.transform.scale(surf, (LEVEL_W, LEVEL_H))
        backgrounds_surfs.append(surf)

load_backgrounds()

# Load tiles
def get_tile_paths():
    # Always put ADD_ICON first, then every file in TILE_FOLDER
    files = [
        f for f in os.listdir(TILE_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    
    # Sort numerically by extracting numbers from filenames
    def numeric_sort_key(filename):
        import re
        # Extract numbers from filename, pad with zeros for proper sorting
        numbers = re.findall(r'\d+', filename)
        if numbers:
            return int(numbers[0])
        return float('inf')  # Put non-numeric files at the end
    
    files.sort(key=numeric_sort_key)
    return [ADD_ICON_PATH] + [os.path.join(TILE_FOLDER, f) for f in files]

paths = get_tile_paths()
tiles = load_tiles(paths, TILE_SIZE)
selected = 1

# Debug: Print tile information
print(f"Loaded {len(tiles)} tiles:")
for i, path in enumerate(paths):
    print(f"  Index {i}: {path}")
print(f"Selected tile index: {selected}")

# Map data
map_data = create_empty(COLS, ROWS)

# Menu
menu_rect = pygame.Rect(
    LEVEL_X + LEVEL_W + 20,
    LEVEL_Y,
    WINDOW_WIDTH - (LEVEL_X + LEVEL_W + 30),
    WINDOW_HEIGHT - 2 * LEVEL_Y
)
menu = TileMenu(menu_rect, tiles, 3, 10, font)

# Action buttons under level area (2x3 grid)
spacing = 10
btn_w = (LEVEL_W - spacing * 3) // 2
btn_h = 40
base_x = LEVEL_X + spacing
base_y = LEVEL_Y + LEVEL_H + spacing
button_names = [
    "Save", "Load",
    "Create", "New Editor",
    "Background", "BG-sec"
]
action_buttons = []
for i, name in enumerate(button_names):
    row = i // 2
    col = i % 2
    rect = pygame.Rect(
        base_x + col * (btn_w + spacing),
        base_y + row * (btn_h + spacing),
        btn_w,
        btn_h
    )
    action_buttons.append(Button(name, rect, font, WHITE))

# Multi‐level support: keep each level’s map & bg‐list
levels            = [map_data]
backgrounds_list  = [backgrounds_paths.copy()]
current_level     = 0

# Auto-save system for level switching
def auto_save_level(level_index):
    """Auto-save a level when switching away from it."""
    if level_index < len(levels):
        auto_file = os.path.join(SAVE_DIR, f"auto_level{level_index}.json")
        level_data = levels[level_index]
        level_backgrounds = (
            backgrounds_list[level_index]
            if level_index < len(backgrounds_list)
            else [default_bg]
        )
        # Save full paths instead of just basenames for auto-save
        save(level_data, level_backgrounds, filename=auto_file)

def auto_load_level(level_index):
    """Auto-load a level when switching to it."""
    auto_file = os.path.join(SAVE_DIR, f"auto_level{level_index}.json")
    if os.path.exists(auto_file):
        try:
            loaded_map, loaded_backgrounds = load(filename=auto_file)
            # For auto-save files, backgrounds should already be full paths
            # But check if they exist, if not, fall back to default
            valid_backgrounds = []
            for bg_path in loaded_backgrounds:
                if os.path.exists(bg_path):
                    valid_backgrounds.append(bg_path)
                else:
                    basename = os.path.basename(bg_path)
                    fallback_path = os.path.join("img", basename)
                    if os.path.exists(fallback_path):
                        valid_backgrounds.append(fallback_path)
                    else:
                        print(f"Warning: Background {bg_path} not found, using default")
                        valid_backgrounds.append(default_bg)
            return loaded_map, valid_backgrounds if valid_backgrounds else [default_bg]
        except Exception as e:
            print(f"Error auto-loading level {level_index}: {e}")
    return None, None

# Try to auto-load level 0 on startup
startup_map, startup_bgs = auto_load_level(0)
if startup_map is not None:
    map_data = startup_map
    backgrounds_paths = startup_bgs
    levels[0] = map_data
    backgrounds_list[0] = backgrounds_paths.copy()
    load_backgrounds()
    print("Auto-loaded level 0 from previous session")

# Main loop
while True:
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            # Auto-save current level before exiting
            levels[current_level] = map_data
            backgrounds_list[current_level] = backgrounds_paths.copy()
            auto_save_level(current_level)
            pygame.quit()
            sys.exit()

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RIGHT:
                # Auto-save current level
                levels[current_level] = map_data
                backgrounds_list[current_level] = backgrounds_paths.copy()
                auto_save_level(current_level)

                # Move to next level
                if current_level == len(levels) - 1:
                    levels.append(create_empty(COLS, ROWS))
                    backgrounds_list.append([default_bg])
                current_level += 1
                current_db = None

                # Try to auto-load the level, or use in-memory data
                loaded_map, loaded_bgs = auto_load_level(current_level)
                if loaded_map is not None:
                    map_data = loaded_map
                    backgrounds_paths = loaded_bgs
                    levels[current_level] = map_data
                    backgrounds_list[current_level] = backgrounds_paths.copy()
                else:
                    map_data = levels[current_level]
                    backgrounds_paths = backgrounds_list[current_level].copy()

                load_backgrounds()
                selected = 1
                print(f"[KEY] Right → now at level {current_level}")

            elif ev.key == pygame.K_LEFT:
                if current_level > 0:
                    # Auto-save current level
                    levels[current_level] = map_data
                    backgrounds_list[current_level] = backgrounds_paths.copy()
                    auto_save_level(current_level)

                    # Move to previous level
                    current_level -= 1

                    # Try to auto-load the level, or use in-memory data
                    loaded_map, loaded_bgs = auto_load_level(current_level)
                    if loaded_map is not None:
                        map_data = loaded_map
                        backgrounds_paths = loaded_bgs
                        levels[current_level] = map_data
                        backgrounds_list[current_level] = backgrounds_paths.copy()
                    else:
                        map_data = levels[current_level]
                        backgrounds_paths = backgrounds_list[current_level].copy()

                    load_backgrounds()
                    selected = 1
                    print(f"[KEY] Left  ← now at level {current_level}")
                else:
                    print("[KEY] Left at level 0 (no change)")

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            pos, btn = ev.pos, ev.button
            handled = False  # Track if we've used the click

            # Menu pagination & tile select
            new_sel = menu.handle_event(pos, btn)
            if new_sel is not None:
                handled = True
                # If you clicked the ADD_ICON slot (index 0):
                if new_sel == 0:
                    root = tk.Tk()
                    root.withdraw()
                    file_path = filedialog.askopenfilename(
                        title="Select image to add as tile",
                        filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
                    )
                    if file_path:
                        dest = os.path.join(TILE_FOLDER, os.path.basename(file_path))
                        shutil.copy(file_path, dest)
                        # Re-scan & reload tiles
                        paths = get_tile_paths()
                        tiles = load_tiles(paths, TILE_SIZE)
                        menu.tiles = tiles
                        # Select the new tile (the last one)
                        selected = len(tiles) - 1
                else:
                    # You clicked a normal tile
                    selected = new_sel

            # Action buttons
            for button in action_buttons:
                if button.clicked(pos):
                    handled = True
                    label = button.label

                    if label == "Save":
                        # 1) Let user choose a project‐filename
                        root = tk.Tk()
                        root.withdraw()
                        project_file = filedialog.asksaveasfilename(
                            title="Save project (all levels) as...",
                            initialdir=SAVE_DIR,
                            defaultextension=".json",
                            filetypes=[("Project JSON", "*.json")]
                        )
                        if not project_file:
                            break

                        # 2) Sync current in-memory level
                        levels[current_level] = map_data
                        backgrounds_list[current_level] = backgrounds_paths.copy()

                        # 3) Save entire project
                        save_project(levels, backgrounds_list, project_file)
                        print(f"Saved entire project ({len(levels)} levels) → {project_file}")

                    elif label == "Load":
                        # 1) Sync current in-memory level
                        levels[current_level] = map_data
                        backgrounds_list[current_level] = backgrounds_paths.copy()

                        # 2) Ask for project JSON to load
                        root = tk.Tk()
                        root.withdraw()
                        project_file = filedialog.askopenfilename(
                            title="Load entire project…",
                            initialdir=SAVE_DIR,
                            filetypes=[("Project JSON", "*.json")]
                        )
                        if not project_file:
                            break

                        # 3) Load all levels and backgrounds_list
                        loaded_levels, loaded_backgrounds = load_project(project_file)
                        if loaded_levels is None or len(loaded_levels) == 0:
                            print(f"Failed to load project or project was empty: {project_file}")
                            break

                        # 4) Replace in-memory data
                        levels = loaded_levels
                        backgrounds_list = loaded_backgrounds
                        current_level = 0
                        map_data = levels[0]
                        backgrounds_paths = (
                            backgrounds_list[0].copy()
                            if backgrounds_list and backgrounds_list[0]
                            else [default_bg]
                        )

                        # 5) Validate backgrounds exist on disk
                        valid_bgs = []
                        for bg in backgrounds_paths:
                            if isinstance(bg, str) and os.path.exists(bg):
                                valid_bgs.append(bg)
                            else:
                                print(f"Warning: background '{bg}' not found → using default")
                                valid_bgs.append(default_bg)
                        backgrounds_paths = valid_bgs
                        backgrounds_list[0] = backgrounds_paths.copy()

                        load_backgrounds()
                        print(f"Loaded entire project ({len(levels)} levels) ← {project_file}")

                    elif label == "Create":
                        # EXPORT your current level out as CSV + JSON
                        export_all_levels(levels, backgrounds_list)

                    elif label == "New Editor":
                        # 1) Delete all auto-save files in SAVE_DIR
                        for fname in os.listdir(SAVE_DIR):
                            if fname.startswith("auto_level") and fname.endswith(".json"):
                                try:
                                    os.remove(os.path.join(SAVE_DIR, fname))
                                except OSError:
                                    pass

                        # 2) Reset in-memory data to a single blank level
                        levels = [create_empty(COLS, ROWS)]
                        backgrounds_list = [[default_bg]]
                        current_level = 0
                        map_data = levels[0]
                        backgrounds_paths = [default_bg]
                        load_backgrounds()

                        print("New Editor: cleared all auto-saves and reset to level 0")

                    elif label == "Background":
                        # Replace primary background for CURRENT level
                        root = tk.Tk()
                        root.withdraw()
                        fp = filedialog.askopenfilename(
                            title="Select new primary background for level",
                            filetypes=[("Images", "*.png;*.jpg;*.jpeg")]
                        )
                        if fp:
                            dest = os.path.join(BG_FOLDER, os.path.basename(fp))
                            shutil.copy(fp, dest)
                            # Update the 0-index background in the current level’s list:
                            backgrounds_list[current_level][0] = dest
                            # Sync it into backgrounds_paths and reload Surfs:
                            backgrounds_paths = backgrounds_list[current_level].copy()
                            load_backgrounds()

                    elif label == "BG-sec":
                        # Add a new background layer *to this* level
                        root = tk.Tk()
                        root.withdraw()
                        fp = filedialog.askopenfilename(
                            title="Select additional background for level",
                            filetypes=[("Images", "*.png;*.jpg;*.jpeg")]
                        )
                        if fp:
                            dest = os.path.join(BG_FOLDER, os.path.basename(fp))
                            shutil.copy(fp, dest)
                            # Append to this level’s list:
                            backgrounds_list[current_level].append(dest)
                            # Sync & reload:
                            backgrounds_paths = backgrounds_list[current_level].copy()
                            load_backgrounds()

            # Place/remove in level
            if not handled:
                lx, ly = pos[0] - LEVEL_X, pos[1] - LEVEL_Y
                # Calculate grid coordinates
                c = lx // TILE_SIZE
                r = ly // TILE_SIZE
                # Debug output for edge cases
                if lx >= 0 and ly >= 0:
                    print(f"Click: pos=({pos[0]}, {pos[1]}), local=({lx}, {ly}), grid=({r}, {c}), bounds=({ROWS}, {COLS})")
                    if c >= COLS or r >= ROWS:
                        print(f"  -> Out of bounds!")
                    elif c < 0 or r < 0:
                        print(f"  -> Negative coordinates!")
                    else:
                        print(f"  -> Valid click!")
                
                # Check if the grid coordinates are valid and within bounds
                if 0 <= r < ROWS and 0 <= c < COLS and lx >= 0 and ly >= 0:
                    if btn == 1:
                        map_data[r][c] = selected
                        print(f"Placed tile {selected} at ({r}, {c})")
                    if btn == 3:
                        map_data[r][c] = -1
                        print(f"Removed tile at ({r}, {c})")

    # Draw everything
    screen.fill(GRAY)

    # 1) Blit all background layers for the current level
    for bg_surf in backgrounds_surfs:
        screen.blit(bg_surf, (LEVEL_X, LEVEL_Y))

    draw_grid(
        screen,
        LEVEL_X, LEVEL_Y,
        LEVEL_W, LEVEL_H,
        backgrounds_surfs[0],   # now a single Surface
        ROWS, COLS,
        TILE_SIZE
    )
    for r in range(ROWS):
        for c in range(COLS):
            idx = map_data[r][c]
            if idx != -1 and idx < len(tiles):
                screen.blit(
                    tiles[idx],
                    (LEVEL_X + c * TILE_SIZE, LEVEL_Y + r * TILE_SIZE)
                )

    menu.draw(screen, selected)
    for button in action_buttons:
        button.draw(screen)

    pygame.display.update()
    clock.tick(60)





# 1. config.py — just constants

# 2. tiles.py — tile loading

# 3. level_data.py — map creation

# 4. io_ops.py — save/load stubs (JSON or DB)

# 5. ui.py — generic Button

# 6. renderer.py — level drawing only

# 7. menu.py — paginated tile menu + action buttons

# 8. main.py — Pygame init & loop, wires everything