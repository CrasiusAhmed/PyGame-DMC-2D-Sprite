import pygame, os
from player import Player
from enemy1 import Enemy, DETECT_RANGE  # ★ need the same detection radius for drawing

import math

class AnimatedBackground:
    def __init__(self, image_folder, frame_count, animation_speed=0.1, easing_type="linear"):
        """
        Initialize animated background with easing
        
        Args:
            image_folder: Path to folder containing background frames
            frame_count: Number of frames (e.g., 13 for 0001-0013)
            animation_speed: Speed of animation (lower = slower, higher = faster)
            easing_type: Type of easing ("linear", "ease_in", "ease_out", "ease_in_out", "smooth")
        """
        self.frames = []
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = animation_speed
        self.easing_type = easing_type
        self.transition_progress = 0.0  # 0.0 to 1.0 for smooth transitions
        self.use_blending = True  # Enable frame blending for smoother animation
        
        # Load all background frames
        for i in range(1, frame_count + 1):
            frame_path = os.path.join(image_folder, f"{i:04d}.jpg")
            if os.path.exists(frame_path):
                frame = pygame.image.load(frame_path).convert()
                self.frames.append(frame)
                print(f"Loaded background frame: {frame_path}")
        
        if not self.frames:
            raise FileNotFoundError(f"No background frames found in {image_folder}")
        
        print(f"Loaded {len(self.frames)} background frames with {easing_type} easing")
    
    def ease_in(self, t):
        """Ease in (slow start, fast end)"""
        return t * t
    
    def ease_out(self, t):
        """Ease out (fast start, slow end)"""
        return 1 - (1 - t) * (1 - t)
    
    def ease_in_out(self, t):
        """Ease in-out (slow start and end, fast middle)"""
        if t < 0.5:
            return 2 * t * t
        return 1 - 2 * (1 - t) * (1 - t)
    
    def smooth_step(self, t):
        """Smooth step function for very smooth transitions"""
        return t * t * (3 - 2 * t)
    
    def apply_easing(self, t):
        """Apply the selected easing function"""
        if self.easing_type == "ease_in":
            return self.ease_in(t)
        elif self.easing_type == "ease_out":
            return self.ease_out(t)
        elif self.easing_type == "ease_in_out":
            return self.ease_in_out(t)
        elif self.easing_type == "smooth":
            return self.smooth_step(t)
        else:  # linear
            return t
    
    def update(self, dt):
        """Update animation frame with easing"""
        self.animation_timer += dt
        
        # Calculate progress through current frame transition
        if self.animation_speed > 0:
            self.transition_progress = min(1.0, self.animation_timer / self.animation_speed)
        
        # Apply easing to the transition progress
        eased_progress = self.apply_easing(self.transition_progress)
        
        # Move to next frame when transition is complete
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            self.transition_progress = 0.0
            self.current_frame = (self.current_frame + 1) % len(self.frames)
    
    def get_current_frame(self):
        """Get current background frame with optional blending"""
        if not self.use_blending or len(self.frames) <= 1:
            return self.frames[self.current_frame]
        
        # Get current and next frame for blending
        current_frame = self.frames[self.current_frame]
        next_frame_idx = (self.current_frame + 1) % len(self.frames)
        next_frame = self.frames[next_frame_idx]
        
        # Apply easing to transition progress
        eased_progress = self.apply_easing(self.transition_progress)
        
        # If transition is minimal, just return current frame (optimization)
        if eased_progress < 0.01:
            return current_frame
        elif eased_progress > 0.99:
            return next_frame
        
        # Create blended frame
        try:
            # Create a copy of current frame
            blended_frame = current_frame.copy()
            
            # Calculate alpha for blending
            alpha = int(255 * eased_progress)
            
            # Create a temporary surface for the next frame with alpha
            temp_surface = next_frame.copy()
            temp_surface.set_alpha(alpha)
            
            # Blend the frames
            blended_frame.blit(temp_surface, (0, 0))
            
            return blended_frame
        except:
            # Fallback to simple frame switching if blending fails
            return current_frame if eased_progress < 0.5 else next_frame
    
    def set_easing_type(self, easing_type):
        """Change easing type during runtime"""
        self.easing_type = easing_type
        print(f"Background easing changed to: {easing_type}")
    
    def toggle_blending(self):
        """Toggle frame blending on/off"""
        self.use_blending = not self.use_blending
        print(f"Background blending: {'ON' if self.use_blending else 'OFF'}")
    
    def get_size(self):
        """Get background dimensions"""
        if self.frames:
            return self.frames[0].get_size()
        return (0, 0)

# initialize all pygame modules
pygame.init()

# set window dimensions
W, H = 1280, 720  
# → W//2 = 1280//2 = 640, H-50 = 720-50 = 670

# create the main display surface (game window)
screen = pygame.display.set_mode((W, H))

# create a clock to manage frame rate
clock = pygame.time.Clock()

# initialize font for UI text
pygame.font.init()
font = pygame.font.Font(None, 24)


# ── load animated background ──
# get path to 'img' directory next to this script
IMG = os.path.join(os.path.dirname(__file__), 'img')

# create animated background from Background folder
background_folder = os.path.join(IMG, 'Background')
animation_speed = 0.8  # Adjust this value to control animation speed (0.1 = slow, 0.5 = fast)
easing_type = "ease_out"  # Options: "linear", "ease_in", "ease_out", "ease_in_out", "smooth"

try:
    animated_bg = AnimatedBackground(background_folder, 13, animation_speed, easing_type)
    BG_W, BG_H = animated_bg.get_size()
    print(f"Animated background loaded! Size: {BG_W}x{BG_H}")
    print("Controls:")
    print("  +/- : Adjust animation speed")
    print("  0   : Reset speed to default")
    print("  1-5 : Change easing type")
    print("  B   : Toggle frame blending")
except FileNotFoundError as e:
    print(f"Error loading animated background: {e}")
    # Fallback to static background if animated fails
    try:
        bg_full = pygame.image.load(os.path.join(IMG, 'Forest.jpg')).convert()
        BG_W, BG_H = bg_full.get_width(), bg_full.get_height()
    except:
        # Create a simple colored background as last resort
        bg_full = pygame.Surface((1280, 720))
        bg_full.fill((50, 100, 150))  # Blue-ish color
        BG_W, BG_H = 1280, 720
    animated_bg = None


# ── create our sprites ──

# place player at the horizontal center (W//2 = 640) and 50 px up from bottom (H-50 = 670)
player = Player((W // 2, H - 50))

# place enemy at one-third across (1280//3 = 426) and same vertical position
enemy = Enemy((W // 3, H - 50))

# Set the enemy as the target for the player
player.target = enemy

# Set the player as the target for the enemy
enemy.target = player


# put both sprites into a single group for easy update/draw calls
all_sprites = pygame.sprite.Group(player, enemy)


# leave some space at the bottom so the camera doesn't center the player at the very screen edge
FOOTER_MARGIN = 80


# ── main game loop ──
running = True
while running:
    # handle all pending events
    for e in pygame.event.get():
        # if window close button clicked, exit loop
        if e.type == pygame.QUIT:
            running = False

        # let the player respond to keyboard/mouse events
        player.handle_event(e)

        # on left-mouse click, call the player's click handler
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            player.click()

        # reset game with R key
        if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
            if player.is_dead:
                player.reset()
                print("Game reset! Press R to reset when dead.")
        
        # background animation controls
        if e.type == pygame.KEYDOWN and animated_bg:
            if e.key == pygame.K_EQUALS or e.key == pygame.K_PLUS:  # + key to speed up
                animated_bg.animation_speed = max(0.05, animated_bg.animation_speed - 0.05)
                print(f"Background animation speed: {animated_bg.animation_speed:.2f}")
            elif e.key == pygame.K_MINUS:  # - key to slow down
                animated_bg.animation_speed = min(2.0, animated_bg.animation_speed + 0.05)
                print(f"Background animation speed: {animated_bg.animation_speed:.2f}")
            elif e.key == pygame.K_0:  # 0 key to reset speed
                animated_bg.animation_speed = 0.3
                print(f"Background animation speed reset to: {animated_bg.animation_speed:.2f}")
            
            # Easing type controls
            elif e.key == pygame.K_1:  # Linear easing
                animated_bg.set_easing_type("linear")
            elif e.key == pygame.K_2:  # Ease in
                animated_bg.set_easing_type("ease_in")
            elif e.key == pygame.K_3:  # Ease out
                animated_bg.set_easing_type("ease_out")
            elif e.key == pygame.K_4:  # Ease in-out
                animated_bg.set_easing_type("ease_in_out")
            elif e.key == pygame.K_5:  # Smooth step
                animated_bg.set_easing_type("smooth")
            elif e.key == pygame.K_b:  # Toggle blending
                animated_bg.toggle_blending()

    # get delta time for smooth animation
    dt = clock.get_time() / 1000.0  # convert milliseconds to seconds
    
    # update animated background
    if animated_bg:
        animated_bg.update(dt)
    
    # update all sprites (calls each .update() method)
    all_sprites.update()

    # ── prevent moving off the left edge of the world ──
    # player.rect.left is clamped to at least 0
    player.rect.left = max(player.rect.left, 0)
    enemy.rect.left  = max(enemy.rect.left,  0)

    # ── camera follows the player ──
    # center camera x on player's center: cam_x = player_x - (W/2)
    cam_x = player.rect.centerx - W // 2

    # position camera y so player's feet sit just above FOOTER_MARGIN
    #      cam_y = player_bottom - (screen_height - FOOTER_MARGIN)
    cam_y = player.rect.bottom - (H - FOOTER_MARGIN)

    # clamp camera so it never shows beyond the background edges
    cam_x = max(0, min(cam_x, BG_W - W))
    cam_y = max(0, min(cam_y, BG_H - H))

    # ── draw the world ──

    # draw the animated background shifted by the camera offset
    if animated_bg:
        current_bg = animated_bg.get_current_frame()
        screen.blit(current_bg, (-cam_x, -cam_y))
    else:
        # fallback to static background
        screen.blit(bg_full, (-cam_x, -cam_y))

    # draw each sprite at (world_pos - camera_pos)
    for spr in all_sprites:
        screen.blit(spr.image, (spr.rect.x - cam_x, spr.rect.y - cam_y))

    # Draw the player's attack point with camera adjustment
    player.draw_attack_point(screen, cam_x, cam_y)

    # Draw the enemy's attack point with camera adjustment
    enemy.draw_attack_point(screen, cam_x, cam_y)
    
    # ── debug: draw the enemy's detection range ──
    # calculate on-screen center of the enemy
    ex = enemy.rect.centerx - cam_x
    ey = enemy.rect.centery  - cam_y

    # draw a green circle of radius DETECT_RANGE around the enemy
    pygame.draw.circle(screen, (0, 255, 0), (int(ex), int(ey)), DETECT_RANGE, 2)
    
    # ── draw UI information ──
    if animated_bg:
        # Background info
        info_texts = [
            f"Background: {animated_bg.easing_type} easing",
            f"Speed: {animated_bg.animation_speed:.2f}",
            f"Blending: {'ON' if animated_bg.use_blending else 'OFF'}",
            f"Frame: {animated_bg.current_frame + 1}/{len(animated_bg.frames)}"
        ]
        
        # Draw semi-transparent background for text
        info_bg = pygame.Surface((250, 100))
        info_bg.set_alpha(128)
        info_bg.fill((0, 0, 0))
        screen.blit(info_bg, (10, 10))
        
        # Draw text
        for i, text in enumerate(info_texts):
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (15, 15 + i * 20))

    # update the full display
    pygame.display.flip()

    # cap the frame rate at 60 frames per second
    clock.tick(60)

# clean up pygame on exit
pygame.quit()
