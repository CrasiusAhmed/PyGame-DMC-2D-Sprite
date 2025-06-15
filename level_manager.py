import pygame
import os
import csv

class AnimatedBackground:
    def __init__(self, image_folder, frame_count, animation_speed=0.8):
        """
        Initialize animated background with smooth linear blending between frames.
        
        Args:
            image_folder: Path to folder containing background frames (0001.jpg, 0002.jpg, …)
            frame_count: Number of frames in that folder
            animation_speed: Seconds it takes to fade from one frame to the next
        """
        # ── LAZY FRAME LOADING OPTIMIZATION ──
        # Instead of loading *all* frames up-front (very slow on large JPG sets),
        # we only remember the file-paths and load frames on-demand the first time
        # they are required for display.  This reduces start-up time massively.
        self.frame_paths = []           # holds absolute paths to each frame file
        self.frames = []                # same length as frame_paths; holds Surfaces or None
        self.current_frame = 0
        self.animation_timer = 0.0
        self.animation_speed = animation_speed
        self.transition_progress = 0.0  # 0.0 → just current frame, 1.0 → just next frame

        # Populate the path list (0001.jpg, 0002.jpg, …)
        for i in range(1, frame_count + 1):
            frame_path = os.path.join(image_folder, f"{i:04d}.jpg")
            if os.path.exists(frame_path):
                self.frame_paths.append(frame_path)
                self.frames.append(None)  # placeholder – not yet loaded

        if not self.frame_paths:
            raise FileNotFoundError(f"No background frames found in {image_folder}")

        # Immediately load the very first frame so that get_size() works and the
        # screen isn’t blank on the first draw.
        self._ensure_frame_loaded(0)
        print(f"[AnimatedBackground] Prepared {len(self.frame_paths)} frames from '{image_folder}' (lazy loading)")

    # ── INTERNAL: load frame *idx* if it has not been loaded yet ──
    def _ensure_frame_loaded(self, idx):
        if 0 <= idx < len(self.frame_paths) and self.frames[idx] is None:
            try:
                surf = pygame.image.load(self.frame_paths[idx]).convert()
                self.frames[idx] = surf
            except Exception as e:
                # If load fails, keep None so we don’t crash; will fallback later
                print(f"[AnimatedBackground] Failed to load frame {idx}: {e}")
                self.frames[idx] = pygame.Surface((1, 1))  # tiny placeholder
    
    def update(self, dt):
        """Advance the animation timer by dt (seconds), then update frames with linear blending."""
        self.animation_timer += dt
        if self.animation_speed > 0:
            self.transition_progress = min(1.0, self.animation_timer / self.animation_speed)
        
        # When we've fully reached transition_progress == 1.0, move to the next frame
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.transition_progress = 0.0
            self.current_frame = (self.current_frame + 1) % len(self.frames)
    
    def get_current_frame(self):
        """
        Return the Surface for the current animation step, loading frames lazily and
        blending with the next frame if transition_progress > 0.  Always guarantees
        a Surface is returned (never None) so callers can blit it without checks.
        """
        # Ensure the two frames we might need are actually loaded
        self._ensure_frame_loaded(self.current_frame)
        if len(self.frames) > 1:
            nxt_idx = (self.current_frame + 1) % len(self.frames)
            self._ensure_frame_loaded(nxt_idx)
        
        if len(self.frames) <= 1:
            return self.frames[self.current_frame]
        
        cur = self.frames[self.current_frame]
        nxt_idx = (self.current_frame + 1) % len(self.frames)
        nxt = self.frames[nxt_idx]
        
        # If we're almost at the start or end of a transition, just return one cleanly:
        if self.transition_progress < 0.01:
            return cur
        elif self.transition_progress > 0.99:
            return nxt
        
        # Otherwise, blend linearly
        try:
            blended = cur.copy()
            alpha = int(255 * self.transition_progress)
            temp = nxt.copy()
            temp.set_alpha(alpha)
            blended.blit(temp, (0, 0))
            return blended
        except Exception:
            # Fallback: pick whichever is closer
            return cur if self.transition_progress < 0.5 else nxt
    
    def get_size(self):
        """Return (width, height) of a single frame (all frames assumed identical size)."""
        if self.frames:
            return self.frames[0].get_size()
        return (0, 0)

class Tile:
    def __init__(self, tile_id, image_path, solid=False):
        self.tile_id = tile_id
        self.image = pygame.image.load(image_path).convert_alpha() if image_path else None
        self.solid = solid

class Level:
    def __init__(self, level_path):
        """
        Load one level from disk. Expects:
        
        level_path/
          ├─ map.csv
          ├─ tiles/        (PNG files named “0.png”, “1.png”, … → tile_id = int(filename))
          │   └─ …
          └─ Background/   (JPG frames “0001.jpg, 0002.jpg, …”)
              └─ …
        """
        self.level_path = level_path
        self.map_data = []
        self.tiles = {}
        self.animated_background = None
        self.background_speed = 0.8
        self.tile_size = 64
        
        self.load_level()
    
    def load_level(self):
        # ── 1) Load map.csv ──
        map_path = os.path.join(self.level_path, "map.csv")
        if os.path.exists(map_path):
            with open(map_path, 'r') as f:
                reader = csv.reader(f)
                self.map_data = [[int(cell) for cell in row] for row in reader]
            print(f"[Level] Loaded map.csv ({len(self.map_data)} rows).")
        else:
            print(f"[Level] Warning: '{map_path}' not found.")
        
        # ── 2) Load tile images from “tiles” folder ──
        tiles_dir = os.path.join(self.level_path, "tiles")
        if os.path.exists(tiles_dir) and os.path.isdir(tiles_dir):
            for fname in os.listdir(tiles_dir):
                if fname.endswith(".png"):
                    try:
                        tid = int(fname.split('.')[0])
                        path = os.path.join(tiles_dir, fname)
                        self.tiles[tid] = Tile(tid, path, solid=True)
                        print(f"[Level] Loaded tile ID {tid} from '{fname}'.")
                    except ValueError:
                        print(f"[Level] Warning: cannot parse tile ID from '{fname}'.")
        else:
            print(f"[Level] Warning: tiles folder not found in '{self.level_path}'.")
        
        # ── 3) Load animated background (if “Background” folder exists) ──
        self.load_animated_background()
    
    def load_animated_background(self):
        bg_folder = os.path.join(self.level_path, "Background")
        if os.path.exists(bg_folder) and os.path.isdir(bg_folder):
            frame_files = [f for f in os.listdir(bg_folder) if f.endswith(".jpg")]
            if frame_files:
                frame_count = len(frame_files)
                try:
                    self.animated_background = AnimatedBackground(
                        bg_folder,
                        frame_count,
                        animation_speed=self.background_speed
                    )
                except FileNotFoundError as e:
                    print(f"[Level] Warning: {e}")
            else:
                print(f"[Level] No .jpg files found in '{bg_folder}', skipping animated background.")
        else:
            # No Background folder → no animated background
            self.animated_background = None


    def get_solid_tile_rects(self):
        """
        Return a list of pygame.Rect for every solid tile in this level.
        A tile is “solid” if its tile-ID ≠ -1 AND the corresponding Tile object has a non‐None .image.
        """
        solid_rects = []
        ts = self.tile_size
        for row_idx, row in enumerate(self.map_data):
            for col_idx, tid in enumerate(row):
                if tid != -1 and tid in self.tiles:
                    tile = self.tiles[tid]
                    # If tile.image is not None, assume solid. Adjust if you have non‐solid image tiles.
                    if tile.image:
                        world_x = col_idx * ts
                        world_y = row_idx * ts
                        solid_rects.append(pygame.Rect(world_x, world_y, ts, ts))
        return solid_rects
    
    def update(self, dt):
        """Update the background animation (if any) each frame."""
        if self.animated_background:
            self.animated_background.update(dt)
    
    def get_background(self):
        """Return the current background Surface or None if not animated."""
        if self.animated_background:
            return self.animated_background.get_current_frame()
        return None
    
    def get_background_size(self):
        """Return (width, height) of the animated background, or default (1280,720)."""
        if self.animated_background:
            return self.animated_background.get_size()
        return (1280, 720)
    
    def get_ground_y_at(self, x_pixel):
        """Return the y (top) of the highest solid tile directly beneath a given x-coordinate.
        The *x_pixel* value is interpreted in the level's local coordinate system (not
        world-space).  If no ground is found this returns *None*."""
        col = int(x_pixel // self.tile_size)
        if col < 0 or col >= (len(self.map_data[0]) if self.map_data else 0):
            return None
        # Search from bottom row upwards so we get the uppermost ground tile
        for r in range(len(self.map_data) - 1, -1, -1):
            tid = self.map_data[r][col]
            if tid != -1 and tid in self.tiles:
                return r * self.tile_size
        return None

    def get_spawn_position(self, spawn_type="top_tile"):
        """
        Return (x, y) on top of the first solid tile in map_data.
        Currently only supports “top_tile” mode.
        """
        if spawn_type == "top_tile":
            # Look for a solid tile that has empty space above it (good ground spawn)
            # Search from bottom row upwards so we favour lower ground tiles
            for r in range(len(self.map_data) - 1, 0, -1):
                for c, tid in enumerate(self.map_data[r]):
                    if tid != -1 and tid in self.tiles:
                        # Check if there's empty space above this tile – good spawn location
                        above_tid = self.map_data[r-1][c] if r > 0 else -1
                        if above_tid == -1:  # Empty cell above means free head-room
                            world_x = c * self.tile_size + self.tile_size // 2
                            world_y = r * self.tile_size  # y of tile top (sprite bottom)
                            return (world_x, world_y)
            
            # If no good ground spawn found, use the bottom row with solid tiles
            for r in range(len(self.map_data) - 1, -1, -1):  # Search from bottom up
                for c, tid in enumerate(self.map_data[r]):
                    if tid != -1 and tid in self.tiles:
                        world_x = c * self.tile_size + self.tile_size // 2
                        world_y = r * self.tile_size  # Spawn on top of the tile (bottom of sprite)
                        return (world_x, world_y)
        
        elif spawn_type == "first_tile":
            # Original behavior - find first solid tile
            for r, row in enumerate(self.map_data):
                for c, tid in enumerate(row):
                    if tid != -1 and tid in self.tiles:
                        world_x = c * self.tile_size + self.tile_size // 2
                        world_y = r * self.tile_size  # Spawn on top of the tile (bottom of sprite)
                        return (world_x, world_y)
        
        # fallback
        return (self.tile_size // 2, self.tile_size // 2)
    
    def draw_tiles(self, screen, cam_x, cam_y):
        """
        Draw each tile at (col*tile_size, row*tile_size) minus camera offset.
        Only blit if on-screen (plus a margin of one tile).
        """
        for r, row in enumerate(self.map_data):
            for c, tid in enumerate(row):
                if tid != -1 and tid in self.tiles:
                    tile = self.tiles[tid]
                    if tile.image:
                        world_x = c * self.tile_size
                        world_y = r * self.tile_size
                        screen_x = world_x - cam_x
                        screen_y = world_y - cam_y
                        if -self.tile_size <= screen_x <= screen.get_width() and \
                           -self.tile_size <= screen_y <= screen.get_height():
                            screen.blit(tile.image, (screen_x, screen_y))

class LevelManager:
    def __init__(self):
        self.levels = {}
        self.current_level = None
        self.current_level_name = None
        self.load_levels()
    
    def load_levels(self):
        """
        Scan the “Level/” directory (sibling to this script) for subfolders.
        Each subfolder (e.g. “level0”, “level1”) is loaded as a Level.
        """
        base = os.path.join(os.path.dirname(__file__), "Level")
        if os.path.exists(base) and os.path.isdir(base):
            for name in os.listdir(base):
                full = os.path.join(base, name)
                if os.path.isdir(full):
                    try:
                        lvl = Level(full)
                        self.levels[name] = lvl
                        print(f"[LevelManager] Loaded '{name}'.")
                    except Exception as e:
                        print(f"[LevelManager] Failed loading '{name}': {e}")
        else:
            print(f"[LevelManager] No Level folder found at '{base}'.")
    
    def get_available_levels(self):
        """Return a list of all loaded level names."""
        return list(self.levels.keys())
    
    def set_current_level(self, level_name):
        """
        If level_name exists, switch current_level to it and return True.
        Otherwise return False.
        """
        if level_name in self.levels:
            self.current_level = self.levels[level_name]
            self.current_level_name = level_name
            print(f"[LevelManager] Current level set to '{level_name}'.")
            return True
        return False
    
    def get_current_level(self):
        """Return the Level instance for whatever is active (or None)."""
        return self.current_level
    
    def next_level(self):
        """Advance to the next level (alphabetical), wrapping around."""
        names = sorted(self.get_available_levels())
        if self.current_level_name in names:
            idx = names.index(self.current_level_name)
            nxt = names[(idx + 1) % len(names)]
            return self.set_current_level(nxt)
        return False
    
    def previous_level(self):
        """Go to the previous level (alphabetical), wrapping around."""
        names = sorted(self.get_available_levels())
        if self.current_level_name in names:
            idx = names.index(self.current_level_name)
            prv = names[(idx - 1) % len(names)]
            return self.set_current_level(prv)
        return False
