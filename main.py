# main.py
import pygame
import os
import time
from player import Player
from enemy1 import Enemy, DETECT_RANGE
from Yori import Yori
from level_manager import LevelManager, AnimatedBackground
from ui_system import UISystem
from dialog_system import DialogSystem  # NEW

pygame.init()

# ── BACKGROUND MUSIC ──
MUSIC_PATH = os.path.join('Music', 'Main Theme - Shadows of the Ancients.mp3')
if os.path.isfile(MUSIC_PATH):
    try:
        # Load and start looping the main theme at 50% volume
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)  # -1 = loop forever
        print("Background music loaded and playing in loop (volume 50%). Use +/- to adjust.")
    except pygame.error as e:
        print(f"[MUSIC] Failed to load '{MUSIC_PATH}':", e)
else:
    print(f"[MUSIC] File not found: {MUSIC_PATH}")

# Helper to adjust music volume (0.0–1.0)
MUSIC_VOL_STEP = 0.05

# ── UI System ──
ui_system = UISystem()

# ── Window setup ──
W, H = 1280, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Devil Is Crying")
clock = pygame.time.Clock()

# ── Dialog System ──
dialog = DialogSystem((W, H))
# Opening dialog slides (edit text later)
dialog.start([
    {
        "image": os.path.join("img", "Player", "Player Image", "Hichigava.png"),
        "text": "Hichigava:\nAnother day, another destiny…"
    },
    {
        "image": os.path.join("img", "Player", "Player Image", "Hichigava.png"),
        "text": "Time to see what challenges await me ahead!"
    }
])

# ── 1) Load a single AnimatedBackground from "img/Background" ──
global_bg_folder = os.path.join("img", "Background")
if not os.path.isdir(global_bg_folder):
    raise FileNotFoundError(f"No folder at '{global_bg_folder}'")

jpg_files = [f for f in os.listdir(global_bg_folder) if f.lower().endswith(".jpg")]
frame_count = len(jpg_files)
if frame_count == 0:
    raise FileNotFoundError(f"No .jpg frames found in '{global_bg_folder}'")

global_bg = AnimatedBackground(global_bg_folder, frame_count, animation_speed=0.8)
bg_width, bg_height = global_bg.get_size()

# ── 2) Load all levels side-by-side ──
level_manager = LevelManager()
available = level_manager.get_available_levels()
if not available:
    raise RuntimeError("No levels found on disk!")

available_sorted = sorted(available)
print("All levels (in load order):", available_sorted)

levels_list = []
for name in available_sorted:
    if not level_manager.set_current_level(name):
        raise RuntimeError(f"Could not load level '{name}'")
    levels_list.append(level_manager.get_current_level())

# ── Compute each level’s pixel-width and cumulative start_x ──
tile_size = levels_list[0].tile_size
level_pixel_widths = []
for lvl in levels_list:
    if lvl.map_data and len(lvl.map_data[0]) > 0:
        cols = len(lvl.map_data[0])
        level_pixel_widths.append(cols * tile_size)
    else:
        level_pixel_widths.append(W)

level_start_x = []
acc = 0
for w in level_pixel_widths:
    level_start_x.append(acc)
    acc += w

num_levels = len(levels_list)
total_world_width = sum(level_pixel_widths)

# ── (Optional) Per-level tile offsets ──
level_offsets = {
    "level0": (0, 0),
    "level1": (0, 0),
    "level2": (0, 0),
    "level3": (0, 0),
    "level4": (0, 0),
    "level5": (0, 0)
}

# ── 3) Spawn Player + Enemies in specific levels ──
player = None
enemies = []
# Flag so Yori dialog only triggers once
yori_dialog_shown = False

# Create player in level0 and enemies in levels 2, 3, and 4
for i, lvl in enumerate(levels_list):
    level_name = available_sorted[i]
    
    # Create player only in level0 with manual position to ensure it's on a solid tile
    if i == 0:
        # Use helper to find first ground tile with air above so player starts on solid ground
        # This places the player directly on the first solid tile in level0
        spawn_local = lvl.get_spawn_position("top_tile")
        player_x = level_start_x[i] + spawn_local[0]
        # Place player so that the sprite bottom is 1 px inside the solid tile
        # This ensures the initial ground collision rectangle overlaps the tile
        # Align sprite so its feet (bottom) sit exactly on the tile top.
        # Sprite is 600 px tall, collider radius 30 px → need offset 600/2 - 30 = 270 px.
        player_y = spawn_local[1] + 270
        player = Player((player_x, player_y))
        # Ensure the player starts grounded on this tile
        player.ground_y = player_y  # sprite bottom already 1px into tile
        player.rigid_body.set_position(player.rect.centerx, player.rect.centery)
        player.rigid_body.is_grounded = True
        print(f"Player spawned in {level_name} at position ({player_x}, {player_y})")
    
    # Create enemies in levels 2, 3, and 4
    if i in [2, 3, 4]:  # Level indices 2, 3, and 4 correspond to level2, level3, level4
        spawn_local = lvl.get_spawn_position("top_tile")
        spawn_world = (spawn_local[0] + level_start_x[i], spawn_local[1])
        enemy_spawn_world = (spawn_world[0] + 200, spawn_world[1])
        # Position enemy so its feet rest exactly on the tile top.
        # Enemy sprite is 600px tall, collider radius 40 ⇒ offset 300-40 = 260.
        enemy_bottom_y = spawn_world[1] + 260
        en = Enemy((enemy_spawn_world[0], enemy_bottom_y))
        # Ensure enemy starts grounded on the tile top (spawn_world[1])
        en.ground_y = spawn_world[1]
        en.rigid_body.set_position(en.rect.centerx, en.rect.centery)
        en.rigid_body.is_grounded = True
        en.target = player  # Set player as the target for the enemy
        en.ui_system = ui_system  # Give enemy access to UI system
        enemies.append(en)
        print(f"Enemy spawned in {level_name} at position ({enemy_spawn_world[0]}, {enemy_bottom_y})")

# Create Yori boss in level5 with manual position to ensure it's on a solid tile
level5_idx = available_sorted.index("level5")
# Use row 8 (index) where solid tiles are located in level5/map.csv
tile_row = 8  # Row 9 (0-indexed is 8) is where solid tiles start
tile_col = 8  # Middle of the level

# Calculate world position based on tile position
yori_x = level_start_x[level5_idx] + (tile_col * tile_size) + (tile_size // 2)
yori_y = tile_row * tile_size  # Position on top of the tile
yori = Yori((yori_x, yori_y))
print(f"Yori spawned in level5 at position ({yori_x}, {yori_y})")

# Set up Yori
yori.target = player
yori.ui_system = ui_system
yori.is_active = False  # Start inactive - will be activated in level 5
player.target = yori
player.ui_system = ui_system

# Give player access to all enemies for attacks (including Yori)
player.all_enemies = enemies + [yori]

# Create sprite group with player, regular enemies, and Yori
all_sprites = pygame.sprite.Group(player, yori, *enemies)

# ── Helper function to find closest enemy ──
def find_closest_enemy(player, enemies):
    """Find the closest enemy to the player"""
    if not enemies:
        return None
    
    closest_enemy = None
    closest_distance = float('inf')
    
    for enemy in enemies:
        # Calculate distance between player and enemy
        dx = enemy.rect.centerx - player.rect.centerx
        dy = enemy.rect.centery - player.rect.centery
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance < closest_distance:
            closest_distance = distance
            closest_enemy = enemy
    
    return closest_enemy

# ── Helper function to find nearby living enemies ──

# ── Dynamic camera function ──
def calculate_dynamic_camera(player, enemies, screen_width, screen_height, total_world_width, bg_height, footer_margin):
    """Calculate camera position based on player and nearby enemies"""
    
    # For simplicity, focus on player in level 0
    if current_level_idx == 0:
        # In level 0, focus only on player
        cam_x = player.world_x - (screen_width // 2)
        cam_y = player.rect.bottom - (screen_height - footer_margin)
        
        # Clamp camera to world bounds
        cam_x = max(0, min(cam_x, total_world_width - screen_width))
        cam_y = max(0, min(cam_y, bg_height - screen_height))
        return cam_x, cam_y
    
    # Check for dying Yori (for cinematic camera)
    dying_yori = None
    if hasattr(yori, 'state') and yori.state == 'die':
        dying_yori = yori
    
    # Handle cinematic death camera first
    if dying_yori and hasattr(dying_yori, 'death_time'):
        time_since_death = time.time() - dying_yori.death_time
        if time_since_death < 5.0:
            # Cinematic camera for Yori's death
            cam_x = dying_yori.rect.centerx - (screen_width // 2)
            cam_y = dying_yori.rect.centery - 100 - (screen_height // 2)
            
            # Clamp camera to world bounds
            cam_x = max(0, min(cam_x, total_world_width - screen_width))
            cam_y = max(0, min(cam_y, bg_height - screen_height))
            return cam_x, cam_y
    

    
    # If in level 2, 3, or 4 with enemies, focus on player and target
    if current_level_idx in [2, 3, 4]:
        # Find living enemies in the current level
        current_enemies = []
        for enemy in enemies:
            # Check if enemy is in the current level's bounds and alive
            if (level_start_x[current_level_idx] <= enemy.rect.centerx < level_start_x[current_level_idx] + level_pixel_widths[current_level_idx] 
                and hasattr(enemy, 'health') and enemy.health > 0):  # Only include living enemies
                current_enemies.append(enemy)
        
        if current_enemies:
            # Focus on player and enemy in current level
            enemy = current_enemies[0]  # Take the first enemy in this level
            mid_x = (player.rect.centerx + enemy.rect.centerx) // 2
            mid_y = (player.rect.centery + enemy.rect.centery) // 2
            
            cam_x = mid_x - (screen_width // 2)
            cam_y = mid_y - (screen_height // 2)
            
            # Clamp camera to world bounds
            cam_x = max(0, min(cam_x, total_world_width - screen_width))
            cam_y = max(0, min(cam_y, bg_height - screen_height))
            return cam_x, cam_y
            
    # If in level 5 with Yori, focus on player and Yori
    if current_level_idx == 5 and yori.alive():
        mid_x = (player.rect.centerx + yori.rect.centerx) // 2
        mid_y = (player.rect.centery + yori.rect.centery) // 2
        
        cam_x = mid_x - (screen_width // 2)
        cam_y = mid_y - (screen_height // 2)
    else:
        # Default to player-focused camera
        cam_x = player.world_x - (screen_width // 2)
        cam_y = player.rect.bottom - (screen_height - footer_margin)
    
    # Clamp camera to world bounds
    cam_x = max(0, min(cam_x, total_world_width - screen_width))
    cam_y = max(0, min(cam_y, bg_height - screen_height))
    
    return cam_x, cam_y

# ── 4) State tracking ──
current_level_idx = 0
current_level = levels_list[0]
running = True
FOOTER_MARGIN = 0

# ── Camera smoothing ──

while running:
    dt = clock.get_time() / 1000.0

    # ── A) HANDLE EVENTS ──
    for e in pygame.event.get():
        # Feed dialog system first
        dialog.handle_event(e)
        if dialog.active and e.type != pygame.QUIT:
            # Ensure walking sound stops when dialog is active
            if hasattr(player, '_walk_sound_playing') and player._walk_sound_playing and player.sfx_walk:
                player.sfx_walk.stop()
                player._walk_sound_playing = False
            continue  # skip other input while dialog visible
        if e.type == pygame.QUIT:
            running = False

        player.handle_event(e)

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            player.click()

        if e.type == pygame.KEYDOWN:
            # Adjust music volume with +/- keys
            if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                vol = max(0.0, pygame.mixer.music.get_volume() - MUSIC_VOL_STEP)
                pygame.mixer.music.set_volume(vol)
                print(f"Music volume: {int(vol*100)}%")
            if e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                vol = min(1.0, pygame.mixer.music.get_volume() + MUSIC_VOL_STEP)
                pygame.mixer.music.set_volume(vol)
                print(f"Music volume: {int(vol*100)}%")

            if e.key == pygame.K_r and player.is_dead:
                spawn0 = levels_list[0].get_spawn_position("top_tile")
                player.reset()
                player.rect.topleft = (spawn0[0], spawn0[1])
                player.world_x = spawn0[0]
                current_level_idx = 0
                current_level = levels_list[0]
                # Target Yori
                if yori.alive():
                    player.target = yori
                print("Game reset → back to level0.")

    # ── B) UPDATE LOGIC ──
    # Frame counter for periodic events
    if 'frame_counter' not in globals():
        global frame_counter
        frame_counter = 0
    frame_counter += 1
    # If a dialog is active, halt world updates except animated background.
    if dialog.active:
        global_bg.update(dt)
        # Stop any sounds that might be playing during dialog
        if hasattr(player, '_walk_sound_playing') and player._walk_sound_playing and player.sfx_walk:
            player.sfx_walk.stop()
            player._walk_sound_playing = False
    else:
        global_bg.update(dt)
        for lvl in levels_list:
            lvl.update(dt)
        all_sprites.update()
    
    # Update UI system
    ui_system.update()
    
    # Check if Yori should trigger low health dialog
    if hasattr(yori, 'should_trigger_low_health_dialog') and yori.should_trigger_low_health_dialog:
        yori.should_trigger_low_health_dialog = False  # Reset flag
        dialog.start([
            {"image": os.path.join("img", "Yori", "Yori Image", "yori.png"),
             "text": "Yori:\nYou think you've won?\nThis is where the real fight begins!"},
            {"image": os.path.join("img", "Yori", "Yori Image", "yori.png"),
             "text": "Yori:\nWitness my true power!\nI will show you despair!"},
            {"image": os.path.join("img", "Player", "Player Image", "Hichigava.png"),
             "text": "Hichigava:\nYour power means nothing!\nJustice will prevail!"}
        ])
        # After dialog, make Yori use skill
        if hasattr(yori, 'start_skill_animation'):
            # Schedule skill animation to start after dialog ends
            yori.should_use_skill = True

    # ── TILE COLLISION DETECTION ──
    # Get tile collision rects for the current level (adjusted for world coordinates)
    current_level_tiles = current_level.get_solid_tile_rects()
    current_level_start = level_start_x[current_level_idx]
    
    # Adjust tile rects to world coordinates
    world_tile_rects = []
    for tile_rect in current_level_tiles:
        world_rect = pygame.Rect(
            tile_rect.x + current_level_start,
            tile_rect.y,
            tile_rect.width,
            tile_rect.height
        )
        world_tile_rects.append(world_rect)
    
    # Apply tile collision to player and ALL enemies
    if hasattr(player, 'rigid_body'):
        # First check if player is standing on tiles
        player.rigid_body.check_tile_collision(world_tile_rects)

        # Check for ground tile directly below the player
        ground_level = player.check_tile_collision_below(world_tile_rects)
        
        # Only set ground_y if there's a tile directly below the player
        # This ensures the player falls when moving off a tile
        if ground_level is not None:
            # Debug removed to prevent spam
            player.ground_y = ground_level
        else:
            # No ground detected below player
            player.ground_y = None
    
    # ------------------------------------------------------------------
    # Apply tile collision + ground detection to **all regular enemies**
    # Each enemy may be in a different level, so build a tile list based on
    # its own X-position (similar to the logic used for Yori).
    # ------------------------------------------------------------------
    for enemy in enemies:
        if not hasattr(enemy, "rigid_body"):
            continue
            
        # Check if player is countering and stun nearby enemies
        # Only successful counters (player.counter_success == True) should stun
        # nearby enemies.  A failed counter (MISS) must not apply stun.
        if (hasattr(player, 'state') and player.state == 'counter' and 
            getattr(player, 'counter_success', False) and not dialog.active):
            # If player is in counter state, stun enemies that are close enough
            dist = pygame.math.Vector2(player.rect.center).distance_to(enemy.rect.center)
            if dist <= 200:  # Stun nearby enemies when countering
                if hasattr(enemy, 'state') and enemy.state != 'die' and enemy.state != 'stun':
                    # Set enemy to stun state
                    enemy.state = 'stun'
                    enemy.frame = 0.0
                    enemy.stun_timer = 2.0  # Stun for 2 seconds
                    print(f"Enemy stunned by counter!")
        # Determine which level the enemy is currently over
        enemy_level_idx = None
        for i in range(num_levels):
            if level_start_x[i] <= enemy.rect.centerx < level_start_x[i] + level_pixel_widths[i]:
                enemy_level_idx = i
                break
        if enemy_level_idx is None:
            enemy_level_idx = current_level_idx  # Fallback

        # Gather tiles from the enemy’s level and its neighbours (±1) so edge
        # cases at boundaries are handled gracefully.
        enemy_world_tile_rects = []
        for idx in [enemy_level_idx - 1, enemy_level_idx, enemy_level_idx + 1]:
            if 0 <= idx < num_levels:
                lvl = levels_list[idx]
                start_x = level_start_x[idx]
                for tile_rect in lvl.get_solid_tile_rects():
                    enemy_world_tile_rects.append(pygame.Rect(
                        tile_rect.x + start_x,
                        tile_rect.y,
                        tile_rect.width,
                        tile_rect.height,
                    ))

        # Physics collision & ground detection
        enemy.rigid_body.check_tile_collision(enemy_world_tile_rects)
        enemy_ground_level = enemy.check_tile_collision_below(enemy_world_tile_rects)
        enemy.ground_y = enemy_ground_level
    
    # Apply tile collision to Yori – need to include tiles from the level Yori is actually in
    if hasattr(yori, 'rigid_body'):
        # ------------------------------------------------------------------
        # Build a tile list that covers the level Yori currently occupies.
        # This prevents Yori from falling through gaps during cross-level
        # transitions where the current level (used for the player) may not
        # contain the ground tiles underneath Yori.
        # ------------------------------------------------------------------
        # Identify the level index under Yori’s centre-x
        yori_level_idx = None
        for i in range(num_levels):
            if level_start_x[i] <= yori.rect.centerx < level_start_x[i] + level_pixel_widths[i]:
                yori_level_idx = i
                break
        # Fallback to current_level_idx if detection fails (shouldn’t happen)
        if yori_level_idx is None:
            yori_level_idx = current_level_idx

        # Gather tiles from Yori’s level and its immediate neighbours (±1) so
        # wide checks at boundaries still find ground.
        yori_world_tile_rects = []
        for idx in [yori_level_idx - 1, yori_level_idx, yori_level_idx + 1]:
            if 0 <= idx < num_levels:
                lvl = levels_list[idx]
                start_x = level_start_x[idx]
                for tile_rect in lvl.get_solid_tile_rects():
                    world_rect = pygame.Rect(
                        tile_rect.x + start_x,
                        tile_rect.y,
                        tile_rect.width,
                        tile_rect.height
                    )
                    yori_world_tile_rects.append(world_rect)
        # ------------------------------------------------------------------
        # Use this expanded tile list for physics & ground detection
        # ------------------------------------------------------------------
        yori.rigid_body.check_tile_collision(yori_world_tile_rects)

        # Check for ground tile directly below Yori using the new tile list
        yori_ground_level = yori.check_tile_collision_below(yori_world_tile_rects)
                
        # Set ground_y to the detected ground level (or None if no ground)
        yori.ground_y = yori_ground_level
        
        # FAILSAFE: If player is grounded but Yori isn't, force Yori to be at the same level
        # This prevents Yori from falling during transitions or other edge cases
        if player.rigid_body.is_grounded and not yori.rigid_body.is_grounded:
            # If player has ground, use that as a reference
            if player.ground_y is not None:
                # Set Yori's ground to player's ground
                yori.ground_y = player.ground_y
                # Set Yori's bottom position to match ground
                yori.rect.bottom = player.ground_y
                # Update rigid body position
                yori.rigid_body.set_position(yori.rect.centerx, yori.rect.centery)
                # Force grounded state
                yori.rigid_body.is_grounded = True
                # Stop any vertical movement
                yori.rigid_body.velocity_y = 0
                
        # EMERGENCY FIX: If Yori falls too far, reset position
        if yori.rect.bottom > 5000:  # Arbitrary threshold to catch excessive falls
            print("DEBUG - Emergency fix: Yori fell too far, searching for ground below")
            # Attempt to find the nearest ground tile directly underneath Yori’s current X
            new_ground = yori.check_tile_collision_below(yori_world_tile_rects)
            if new_ground is not None:
                # Snap Yori to that ground level
                yori.rect.bottom = new_ground
                yori.ground_y = new_ground
            else:
                # As a last resort, move Yori back to his original spawn height instead of
                # teleporting him to the player. This prevents sudden “rubber-band” effects.
                if hasattr(yori, "spawn_initial_bottom"):
                    yori.rect.bottom = yori.spawn_initial_bottom
                    yori.ground_y = yori.spawn_initial_bottom
            # Reset physics state so he stands still on the ground
            yori.rigid_body.is_grounded = True
            yori.rigid_body.velocity_y = 0
            yori.rigid_body.set_position(yori.rect.centerx, yori.rect.centery)
                
            # Debug output (only occasionally to avoid spam)
            if frame_counter % 60 == 0:  # Once per second
                print(f"DEBUG - FAILSAFE: Forcing Yori to ground at {player.ground_y}")
    
    # ── PLAYER-ENEMY COLLISION (COMMENTED OUT) ──
    # Check collision between player and ALL enemies
    # for enemy in enemies:
    #     if (hasattr(player, 'rigid_body') and hasattr(enemy, 'rigid_body') and 
    #         player.rigid_body.collider.collides_with_circle(enemy.rigid_body.collider)):
    #         
    #         # Calculate collision response
    #         player_pos = player.rigid_body.get_position()
    #         enemy_pos = enemy.rigid_body.get_position()
    #         
    #         # Calculate direction from enemy to player
    #         dx = player_pos[0] - enemy_pos[0]
    #         dy = player_pos[1] - enemy_pos[1]
    #         distance = (dx * dx + dy * dy) ** 0.5
    #         
    #         if distance > 0:
    #             # Normalize direction
    #             nx = dx / distance
    #             ny = dy / distance
    #             
    #             # Calculate overlap
    #             total_radius = player.rigid_body.collider.radius + enemy.rigid_body.collider.radius
    #             overlap = total_radius - distance
    #             
    #             if overlap > 0:
    #                 # Separate the objects
    #                 separation = overlap * 0.5
    #                 
    #                 # Move player away from enemy
    #                 new_player_x = player_pos[0] + nx * separation
    #                 new_player_y = player_pos[1] + ny * separation
    #                 player.rigid_body.set_position(new_player_x, new_player_y)
    #                 player.rect.centerx = int(new_player_x)
    #                 player.rect.centery = int(new_player_y)
    #                 
    #                 # Move enemy away from player
    #                 new_enemy_x = enemy_pos[0] - nx * separation
    #                 new_enemy_y = enemy_pos[1] - ny * separation
    #                 enemy.rigid_body.set_position(new_enemy_x, new_enemy_y)
    #                 enemy.rect.centerx = int(new_enemy_x)
    #                 enemy.rect.centery = int(new_enemy_y)
    #                 
    #                 # Apply collision impulse (optional - for bouncing effect)
    #                 impulse_strength = 2.0
    #                 player.rigid_body.apply_impulse(nx * impulse_strength, 0)
    #                 enemy.rigid_body.apply_impulse(-nx * impulse_strength, 0)
    
    # ── PLAYER-YORI COLLISION ──
    # Check collision between player and Yori
    if (hasattr(player, 'rigid_body') and hasattr(yori, 'rigid_body') and 
        player.rigid_body.collider.collides_with_circle(yori.rigid_body.collider)):
        
        # Commenting out the entire collision response so player can walk and dash through Yori
        # Yori still has a rigid body for other purposes (attacks, effects, etc.)
        # but doesn't block player movement
        
        """
        # Calculate collision response
        player_pos = player.rigid_body.get_position()
        yori_pos = yori.rigid_body.get_position()
        
        # Calculate direction from yori to player
        dx = player_pos[0] - yori_pos[0]
        dy = player_pos[1] - yori_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance > 0:
            # Normalize direction
            nx = dx / distance
            ny = dy / distance
            
            # Calculate overlap
            total_radius = player.rigid_body.collider.radius + yori.rigid_body.collider.radius
            overlap = total_radius - distance
            
            if overlap > 0:
                # Separate the objects
                separation = overlap * 0.5
                
                # Move player away from yori
                new_player_x = player_pos[0] + nx * separation
                new_player_y = player_pos[1] + ny * separation
                player.rigid_body.set_position(new_player_x, new_player_y)
                player.rect.centerx = int(new_player_x)
                player.rect.centery = int(new_player_y)
                
                # Move yori away from player
                new_yori_x = yori_pos[0] - nx * separation
                new_yori_y = yori_pos[1] - ny * separation
                yori.rigid_body.set_position(new_yori_x, new_yori_y)
                yori.rect.centerx = int(new_yori_x)
                yori.rect.centery = int(new_yori_y)
                
                # Apply collision impulse (optional - for bouncing effect)
                impulse_strength = 2.0
                player.rigid_body.apply_impulse(nx * impulse_strength, 0)
                yori.rigid_body.apply_impulse(-nx * impulse_strength, 0)
        """
        # Player now passes through Yori when walking OR dashing

    # Prevent player from going left of world
    if player.rect.left < 0:
        player.rect.left = 0
        player.world_x = 0

    # Keep world_x synced to rect.x (centerx for more stable transitions)
    player.world_x = player.rect.centerx

    # Remember player's grounded state before level transition
    player_was_grounded = player.rigid_body.is_grounded
    player_previous_ground_y = player.ground_y
    
    # Remember Yori's grounded state before level transition
    yori_was_grounded = yori.rigid_body.is_grounded
    yori_previous_ground_y = yori.ground_y
    
    # Debug print for level transition
    # print(f"DEBUG - Before transition: Player pos: ({player.rect.centerx}, {player.rect.bottom}), grounded: {player_was_grounded}")
    # print(f"DEBUG - Before transition: Yori pos: ({yori.rect.centerx}, {yori.rect.bottom}), grounded: {yori_was_grounded}")
    
    # Check if we moved into next/previous level
    right_edge = level_start_x[current_level_idx] + level_pixel_widths[current_level_idx]
    if player.world_x >= right_edge and current_level_idx < (num_levels - 1):
        # Save player's position relative to right edge before transition
        edge_offset = player.world_x - right_edge
        
        # Save Yori's relative position to player before transition
        yori_player_offset = yori.rect.centerx - player.rect.centerx
        
        # Check if we're entering level 5 - activate Yori boss fight
        if current_level_idx == 4:  # If we're in level 4, we'll enter level 5
            print("ENTERING LEVEL 5! ACTIVATING YORI BOSS FIGHT!")
            yori.is_active = True  # Activate Yori for boss fight
            if not yori_dialog_shown:
                dialog.start([
                    {"image": os.path.join("img", "Yori", "Yori Image", "yori.png"),
                     "text": "Yori:\nYou have come far, warrior…\nBut this is where you fall!"},
                    {"image": os.path.join("img", "Yori", "Yori Image", "yori.png"),
                     "text": "Yori:\nKneel, and I may yet spare you."},
                    {"image": os.path.join("img", "Player", "Player Image", "Hichigava.png"),
                     "text": "Hichigava:\nSpare your breath, tyrant."},
                    {"image": os.path.join("img", "Player", "Player Image", "Hichigava.png"),
                     "text": "Hichigava:\nJustice answers with steel!"}
                ])
                yori_dialog_shown = True
        
        current_level_idx += 1
        current_level = levels_list[current_level_idx]
        print(f"→ Entered {available_sorted[current_level_idx]}")
        
        # Set new position: left edge of new level + offset
        current_level_start = level_start_x[current_level_idx]
        player.rect.centerx = current_level_start + edge_offset
        player.world_x = player.rect.centerx
        player.rigid_body.set_position(player.rect.centerx, player.rect.centery)
        
        # Update Yori's position **only** if the boss fight has not been activated yet.
        # Once yori.is_active is True (player has entered level5), we stop forcibly
        # repositioning him during further level transitions so that throwing him
        # off a platform doesn’t cause an unwanted teleport back to the player.
        if not getattr(yori, "is_active", False):
            yori.rect.centerx = player.rect.centerx + yori_player_offset
            yori.world_x = yori.rect.centerx
            
            # Force Yori to stay at same vertical position initially to prevent falling
            # Will be properly adjusted to ground level later in the code
            if player_was_grounded:
                yori.rect.bottom = player.rect.bottom
                # Set Yori as grounded immediately to prevent any falling
                yori.rigid_body.is_grounded = True
                # Set Yori's ground_y to match its current bottom position
                yori.ground_y = yori.rect.bottom
                """ print(f"DEBUG - Right transition: Initial sync - Setting Yori bottom to player: {player.rect.bottom}, setting grounded=True") """
            
            # Update rigid body position to match sprite position
            yori.rigid_body.set_position(yori.rect.centerx, yori.rect.centery)
        
        # Immediately update the world tile rects for the new level
        current_level_tiles = current_level.get_solid_tile_rects()
        current_level_start = level_start_x[current_level_idx]
        world_tile_rects = []
        for tile_rect in current_level_tiles:
            world_rect = pygame.Rect(
                tile_rect.x + current_level_start,
                tile_rect.y,
                tile_rect.width,
                tile_rect.height
            )
            world_tile_rects.append(world_rect)
        
        # Immediately check for ground level in the new level
        ground_level = player.check_tile_collision_below(world_tile_rects)
        
        # Keep player grounded if they were grounded before transition
        if player_was_grounded:
            # If there's ground in the new level, use it
            if ground_level is not None:
                player.ground_y = ground_level
            # If no ground found but player was grounded, maintain the previous ground_y
            # This ensures the player stays at the same height during transition
            elif player_previous_ground_y is not None:
                player.ground_y = player_previous_ground_y
                player.rigid_body.is_grounded = True
                
            # Ensure velocity is zeroed to prevent falling
            player.rigid_body.velocity_y = 0
        
        # Keep Yori grounded as well during level transition
        yori_ground_level = yori.check_tile_collision_below(world_tile_rects)
        
        # Keep Yori grounded if it was grounded before transition
        if yori_was_grounded:
            # If there's ground in the new level, use it
            if yori_ground_level is not None:
                yori.ground_y = yori_ground_level
            # If no ground found but was grounded, maintain the previous ground_y
            elif yori_previous_ground_y is not None:
                yori.ground_y = yori_previous_ground_y
                yori.rigid_body.is_grounded = True
            
            # Ensure velocity is zeroed to prevent falling
            yori.rigid_body.velocity_y = 0
        
        # Yori position is already updated earlier when player position changes

    left_edge = level_start_x[current_level_idx]
    if player.world_x < left_edge and current_level_idx > 0:
        # Save player's position relative to left edge before transition
        edge_offset = player.world_x - left_edge
        
        # Save Yori's relative position to player before transition
        yori_player_offset = yori.rect.centerx - player.rect.centerx
        
        current_level_idx -= 1
        current_level = levels_list[current_level_idx]
        print(f"← Returned to {available_sorted[current_level_idx]}")
        
        # Set new position: right edge of previous level + offset
        current_level_start = level_start_x[current_level_idx]
        right_edge_prev = current_level_start + level_pixel_widths[current_level_idx]
        player.rect.centerx = right_edge_prev + edge_offset
        player.world_x = player.rect.centerx
        player.rigid_body.set_position(player.rect.centerx, player.rect.centery)
        
        # Update Yori's position to maintain relative position to player - IMPORTANT: Do this right after player position update
        yori.rect.centerx = player.rect.centerx + yori_player_offset
        yori.world_x = yori.rect.centerx
        # Update rigid body position to match sprite position
        yori.rigid_body.set_position(yori.rect.centerx, yori.rect.centery)
        
        # Immediately update the world tile rects for the new level
        current_level_tiles = current_level.get_solid_tile_rects()
        current_level_start = level_start_x[current_level_idx]
        world_tile_rects = []
        for tile_rect in current_level_tiles:
            world_rect = pygame.Rect(
                tile_rect.x + current_level_start,
                tile_rect.y,
                tile_rect.width,
                tile_rect.height
            )
            world_tile_rects.append(world_rect)
        
        # Immediately check for ground level in the new level
        ground_level = player.check_tile_collision_below(world_tile_rects)
        
        # Keep player grounded if they were grounded before transition
        if player_was_grounded:
            # If there's ground in the new level, use it
            if ground_level is not None:
                player.ground_y = ground_level
            # If no ground found but player was grounded, maintain the previous ground_y
            # This ensures the player stays at the same height during transition
            elif player_previous_ground_y is not None:
                player.ground_y = player_previous_ground_y
                player.rigid_body.is_grounded = True
                
            # Ensure velocity is zeroed to prevent falling
            player.rigid_body.velocity_y = 0
        
        # Keep Yori grounded as well during level transition
        yori_ground_level = yori.check_tile_collision_below(world_tile_rects)
        
        # Keep Yori grounded if it was grounded before transition
        if yori_was_grounded:
            # If there's ground in the new level, use it
            if yori_ground_level is not None:
                yori.ground_y = yori_ground_level
            # If no ground found but was grounded, maintain the previous ground_y
            elif yori_previous_ground_y is not None:
                yori.ground_y = yori_previous_ground_y
                yori.rigid_body.is_grounded = True
            
            # Ensure velocity is zeroed to prevent falling
            yori.rigid_body.velocity_y = 0
        
        # Yori position is already updated earlier when player position changes
    
    # ── DYNAMIC TARGETING ──
    # First, find the closest enemy that's in attack state (prioritize enemies who are attacking)
    attacking_enemies = [e for e in enemies if e.state == 'attack' and e.current_health > 0]
    
    if attacking_enemies:
        # Target the closest attacking enemy
        closest_attacking = find_closest_enemy(player, attacking_enemies)
        if closest_attacking:
            player.target = closest_attacking
            print(f"DEBUG - Targeting attacking enemy at distance {pygame.math.Vector2(player.rect.center).distance_to(closest_attacking.rect.center):.1f}")
    else:
        # If no enemies are attacking, target the closest enemy
        closest_enemy = find_closest_enemy(player, [e for e in enemies if e.current_health > 0])
        if closest_enemy:
            player.target = closest_enemy
    
    # ── YORI TARGETING (LEVEL 5 ONLY) ──
    # Only target Yori if in level 5 and Yori is alive
    if current_level_idx == 5 and yori.alive():
        player.target = yori

    # ── C) DYNAMIC CAMERA SYSTEM ──
    # Use our calculate_dynamic_camera function for all camera logic
    cam_x, cam_y = calculate_dynamic_camera(
        player, 
        enemies, 
        W, 
        H, 
        total_world_width, 
        bg_height, 
        FOOTER_MARGIN
    )
    
    # Clamp camera to world bounds
    cam_x = max(0, min(cam_x, total_world_width - W))
    cam_y = max(0, min(cam_y, bg_height - H))

    # ── D) DRAW ──
    screen.fill((0, 0, 0))

    # ──── At the very top of main.py ────
    bg_x_offset = -100   # ← change to +10 or -10 to nudge the animated BG left/right

    # ───▶ Draw the fixed (non-scrolling) background at (0, 0) ◀───
    bg_frame = global_bg.get_current_frame()
    screen.blit(bg_frame, (bg_x_offset, 0))   # always draw at Y=0


    # ────────────────────────────────────────────────────────────────

    # 2) Draw all levels’ tiles (shifted by level_start_x[i])
    for i, lvl in enumerate(levels_list):
        base_x = level_start_x[i]
        offs_x, offs_y = level_offsets.get(available_sorted[i], (0, 0))

        for row_idx, row in enumerate(lvl.map_data):
            for col_idx, tid in enumerate(row):
                if tid != -1 and tid in lvl.tiles:
                    tile = lvl.tiles[tid]
                    if tile.image:
                        world_x = base_x + (col_idx * tile_size)
                        world_y = row_idx * tile_size
                        screen_x = world_x - cam_x + offs_x
                        screen_y = world_y - cam_y + offs_y
                        if -tile_size <= screen_x <= W and -tile_size <= screen_y <= H:
                            screen.blit(tile.image, (screen_x, screen_y))

    # 3) Draw all sprites (player + all enemies)
    # Skip world draw if dialog active? we still draw but overlay on top.
    for spr in all_sprites:
        screen.blit(spr.image, (spr.rect.x - cam_x, spr.rect.y - cam_y))

    # 3.5) Draw UI elements
    # Draw enemy health bars
    for enemy in enemies:
        ui_system.draw_entity_health(screen, enemy, cam_x, cam_y)
    
    # Draw Yori's boss health bar only when in level5 and combat is active
    # Show boss bar once fight started (yori.is_active) until boss is dead, no
    # matter which level the camera is currently in.
    if yori.is_active and (yori.alive() or yori.state == 'die'):
        yori.draw_health_bar(screen, cam_x, cam_y)
    
    # Draw damage texts
    ui_system.draw_damage_texts(screen, cam_x, cam_y)
    
    # Draw player health in UI corner
    ui_system.draw_player_health_ui(screen, player)
    # Draw skill icon/cool-down bar bottom-centre
    ui_system.draw_skill_cooldown(screen, player, W, H)

    # Draw dialog overlay last
    dialog.draw(screen)

    # 4) Draw attack points (player + current enemy)
    ## player.draw_attack_point(screen, cam_x, cam_y)  # disabled: hide red/blue debug circles
    ## enemies[current_level_idx].draw_attack_point(screen, cam_x, cam_y)
    
    # 4.5) Draw rigid body debug circles for player and Yori
    ## player.draw_rigid_body_debug(screen, cam_x, cam_y)  # disabled: hide green collider circle
    
    # Draw debug circles for Yori
    if yori.alive() and hasattr(yori, 'rigid_body'):
        color = (255, 0, 255)  # Purple for Yori
        # Highlight Yori as the target with thicker line
        width = 4 if yori == player.target else 2
        ## yori.rigid_body.draw_debug(screen, cam_x, cam_y, color=color, width=width)  # disabled
        # Draw a small center dot
        center_x, center_y = yori.rigid_body.get_position()
        screen_x = int(center_x - cam_x)
        screen_y = int(center_y - cam_y)
        pygame.draw.circle(screen, color, (screen_x, screen_y), 5)  # Larger circle for boss
        
        # Draw Yori label
        font = pygame.font.Font(None, 24)
        label = "YORI*" if yori == player.target else "YORI"
        text = font.render(label, True, color)
        screen.blit(text, (screen_x - 20, screen_y - 40))

    # Draw debug circles for all enemies with different colors
    enemy_colors = [(255, 0, 0), (255, 100, 0), (255, 0, 100), (100, 255, 0), (0, 100, 255)]
    for i, enemy in enumerate(enemies):
        color = enemy_colors[i % len(enemy_colors)]  # Cycle through colors
        if hasattr(enemy, 'rigid_body'):
            # Highlight the current target with thicker line
            width = 4 if enemy == player.target else 2
            ## enemy.rigid_body.draw_debug(screen, cam_x, cam_y, color=color, width=width)  # disabled
            # Draw a small center dot to make each enemy more distinguishable
            center_x, center_y = enemy.rigid_body.get_position()
            screen_x = int(center_x - cam_x)
            screen_y = int(center_y - cam_y)
            pygame.draw.circle(screen, color, (screen_x, screen_y), 3)  # Small filled circle
            
            # Draw enemy number label with special marking for target
            font = pygame.font.Font(None, 24)
            label = f"E{i}*" if enemy == player.target else f"E{i}"
            text = font.render(label, True, color)
            screen.blit(text, (screen_x - 10, screen_y - 30))
    #         screen.blit(text, (screen_x - 10, screen_y - 30))

    # Debug: draw detection circle around enemies
    for enemy in enemies:
        if current_level_idx in [2, 3, 4]:  # Only draw in levels 2, 3, 4
            ex = enemy.rect.centerx - cam_x
            ey = enemy.rect.centery - cam_y
            ## pygame.draw.circle(screen, (0, 255, 0), (int(ex), int(ey)), DETECT_RANGE, 2)  # disabled
    
    # 6) Debug: show camera mode (OLD SIMPLE CAMERA)
    font = pygame.font.Font(None, 36)

    pygame.display.flip()
    clock.tick(60)
    
    # Periodic debug output to monitor Yori's position
    # if frame_counter % 120 == 0:  # Every 2 seconds
        #print(f"DEBUG - Status: Player pos: ({player.rect.centerx}, {player.rect.bottom}), grounded: {player.rigid_body.is_grounded}")
        # print(f"DEBUG - Status: Yori pos: ({yori.rect.centerx}, {yori.rect.bottom}), grounded: {yori.rigid_body.is_grounded}, ground_y: {yori.ground_y}")

pygame.quit()





















# ═══════════════════════════════════════════════════════════════════════════════
# ── NEW DYNAMIC CAMERA SYSTEM (DARK SOULS STYLE) ──
# ═══════════════════════════════════════════════════════════════════════════════
# 
# To use this new camera system, replace the "CAMERA (OLD SIMPLE VERSION)" section
# around line 309-314 with the code below:
#
# FEATURES:
# - Player-centered camera when no enemies nearby (EXPLORE MODE)
# - Dark Souls style camera focusing on player + enemy when in combat (COMBAT MODE)
# - Smooth transitions between modes
# - Automatic return to player focus when enemies die
#
# ═══════════════════════════════════════════════════════════════════════════════

"""
# ── REPLACE THE OLD CAMERA SECTION (lines ~309-314) WITH THIS: ──

    # ── C) DYNAMIC CAMERA (NEW SYSTEM) ──
    target_cam_x, target_cam_y = calculate_dynamic_camera(
        player, enemies, W, H, total_world_width, bg_height, FOOTER_MARGIN
    )
    
    # Smooth camera movement
    current_cam_x += (target_cam_x - current_cam_x) * CAMERA_SMOOTH_SPEED
    current_cam_y += (target_cam_y - current_cam_y) * CAMERA_SMOOTH_SPEED
    
    # Use the smoothed camera position
    cam_x = int(current_cam_x)
    cam_y = int(current_cam_y)
    
    # Check if we're in combat mode (for debug display)
    nearby_enemies = find_nearby_enemies(player, enemies, max_distance=400)
    combat_mode = len(nearby_enemies) > 0

# ── AND REPLACE THE DEBUG TEXT (line ~385) WITH THIS: ──

    # 6) Debug: show camera mode (DYNAMIC CAMERA)
    font = pygame.font.Font(None, 36)
    mode_text = "COMBAT CAM" if combat_mode else "EXPLORE CAM"
    mode_color = (255, 100, 100) if combat_mode else (100, 255, 100)
    text_surface = font.render(mode_text, True, mode_color)
    screen.blit(text_surface, (10, 10))
"""

# ═══════════════════════════════════════════════════════════════════════════════
# ── CAMERA SYSTEM EXPLANATION ──
# ═══════════════════════════════════════════════════════════════════════════════
#
# CURRENT SYSTEM (Simple Camera):
# - Always follows the player
# - Camera position: player.world_x - (screen_width // 2)
# - Simple and predictable
#
# NEW SYSTEM (Dynamic Camera):
# - EXPLORE MODE: Follows player (same as current)
# - COMBAT MODE: Focuses on midpoint between player and closest enemy
# - Smooth transitions between modes
# - Combat mode triggers when enemies are within 400 pixels
# - Returns to explore mode when all nearby enemies are dead
#
# BENEFITS:
# - More cinematic combat experience
# - Better view of both player and enemy during fights
# - Automatic adaptation to combat situations
# - Smooth camera movements (no jarring jumps)
#
# ═══════════════════════════════════════════════════════════════════════════════
