import pygame, os
# Ensure mixer is initialised for sound playback
if not pygame.mixer.get_init():
    pygame.mixer.init()
from rigidbody import RigidBody

# ── constants & configuration ──
IMG_DIR     = os.path.join(os.path.dirname(__file__), 'img')
PLAYER_SIZE = (600, 600)   # all frames will be scaled to 600×600 px

# tweak these values to adjust gameplay feel:
MOVE_SPEED    = 7          # walking speed: 5 px per frame
DASH_SPEED    = 15         # dash speed: 15 px per frame
DASH_DURATION = 400        # dash lasts 400 milliseconds
ATTACK_DIST   = 70         # lunge forward distance on attack, in pixels
ATTACK_TIME   = 100        # (unused) ms for attack lunge
JUMP_V        = -20        # initial jump velocity: move upward 20 px/frame
GRAVITY       = 0.8        # downward acceleration per frame

# ── easing helper functions ──

def ease_out_quad(t):
    # ease-out: fast start, slow end
    # e.g. ease_out_quad(0.5) → 1 - (0.5)^2 = 0.75
    return 1 - (1 - t)**2


# ── frame loading utility ──
def load_frames(folder):
    """
    Load and scale all image files in IMG_DIR/folder.
    Expects filenames like '0.png', '1.png', ... sorted by integer index.
    Returns a list of scaled Surface objects.
    """
    path = os.path.join(IMG_DIR, folder)
    files = sorted(os.listdir(path), key=lambda s: int(s.split('.')[0]))
    # example: files = ['0.png','1.png','2.png']
    return [
        pygame.transform.scale(
            pygame.image.load(os.path.join(path, f)).convert_alpha(),
            PLAYER_SIZE
        )
        for f in files
    ]

class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # load all animation sequences into a dict
        self.anims = {
            'idle': load_frames('Player/Player idle'),
            'walk_start': load_frames('Player/Player Walk Start'),  # New start frame
            'walk': load_frames('Player/Player walking'),
            'walk_stop': load_frames('Player/Player Walk Stop'),  # New stop frame
            1     : load_frames('Player/Player Attack 1'),
            2     : load_frames('Player/Player Attack 2'),
            3     : load_frames('Player/Player Attack 3'),
            'jump': load_frames('Player/Player Jump 1'),
            'jump2':load_frames('Player/Player Jump 2'),
            'dash': load_frames('Player/Player Dash'),
            'hurt': load_frames('Player/Player Hurt'),
            'death': load_frames('Player/Player Death'),
            'block': load_frames('Player/Player Block'),
            'counter': load_frames('Player/Player Counter'),
            'counter_attack': load_frames('Player/Player Counter Attack'),
            'skill': load_frames('Player/Player Skill'),  # new skill animation
        }

        # initial state - ensure player always starts in idle
        self.state    = 'idle'    # current action or attack number
        self.frame    = 0.0       # floating-point frame index
        self.dir      = 0         # movement direction: -1 (left), 0, +1 (right)
        self.flip     = False     # whether to horizontally flip the sprite
        self.image    = self.anims['idle'][0]  # starting image
        self.rect     = self.image.get_rect(midbottom=pos)
        # e.g. if pos=(640,670), rect.midbottom=(640,670)

        # physics attributes
        self.vel_y    = 0         # vertical velocity in px/frame
        self.jumps    = 0         # how many jumps used (max 2)
        self.ground_y = self.rect.bottom  # y-coordinate of “ground level”

        # dash state
        self.dashing     = False
        self.dash_start  = 0      # timestamp(ms) when dash began
        self.is_dead = False
        
        # blocking state
        self.blocking = False
        self.block_animation_state = 'none'  # 'none', 'entering', 'holding', 'exiting'
        self.block_animation_speed = 0.25  # Faster base speed for better feel
        self.block_queued = False  # right-click during attack queues block
        
        # counter system (works while blocking)
        self.countering = False
        self.counter_success = False
        self.counter_attacking = False
        self.counter_attack_damage = 75  # Higher damage for counter attacks
        self.counter_ready = False  # True when counter succeeded and waiting for click
        self.last_counter_time = 0  # Anti-spam for counter attempts
        self._counter_damage_dealt = False  # Track if counter attack damage has been dealt

        # facing & attack tracking
        self.facing      = 1      # last non-zero dir: +1=right, -1=left
        self._atk_covered = 0.0   # how many px we've lunged so far

        # attack point attributes
        self.attack_point = (self.rect.centerx + 50, self.rect.centery)  # Example position
        self.attack_radius = 50  # Example radius
        # Skill attributes (continued)
        self.skill_damage = 200
        self.skill_cooldown = 15000  # ms
        self.last_skill_time_ms = -15000  # allow immediately
        self._skill_damage_dealt = False
        # Skill AOE radius (for visual debug and hit detection)
        self.skill_radius = 250  # customize this value for AOE size
        # Queued skill flag (allows buffering during other actions)
        self.skill_queued = False

        # ── load SFX (if present) ──
        self.sfx_counter = None
        self.sfx_counter_attack = None
        self.sfx_skill = None
        self.sfx_walk = None
        self.sfx_dash = None
        self.sfx_attack = {}
        try:
            p1 = os.path.join('Music', 'Counter.mp3')
            if os.path.isfile(p1):
                self.sfx_counter = pygame.mixer.Sound(p1)
            p2 = os.path.join('Music', 'Counter Attack.mp3')
            if os.path.isfile(p2):
                self.sfx_counter_attack = pygame.mixer.Sound(p2)
            p3 = os.path.join('Music', 'Hiichigava Skill.mp3')
            if os.path.isfile(p3):
                self.sfx_skill = pygame.mixer.Sound(p3)
            p_walk = os.path.join('Music', 'Walking.mp3')
            if os.path.isfile(p_walk):
                self.sfx_walk = pygame.mixer.Sound(p_walk)
                self.sfx_walk.set_volume(0.7)
            p_dash = os.path.join('Music', 'Dashing.mp3')
            if os.path.isfile(p_dash):
                self.sfx_dash = pygame.mixer.Sound(p_dash)
            # attack sounds
            for i in (1,2,3):
                pa = os.path.join('Music', f'Player Attack {i}.mp3')
                if os.path.isfile(pa):
                    self.sfx_attack[i] = pygame.mixer.Sound(pa)
        except pygame.error as e:
            print('[SFX] load error', e)

        # Track walking sound state
        self._walk_sound_playing = False

        # Add a timer to track the last attack time
        self.last_attack_time = 0
        self.attack_cooldown = 400  # 0.4 seconds (400ms) cooldown between any attacks
        self.attack_delays = {1: 1000, 2: 5000, 3: 1000}  # Delays between combo attacks
        
        # Add jump-related tracking variables
        self.last_jump_time = 0
        self._prev_grounded = True


        # Add a target attribute to reference the enemy
        self.target = None

        self.max_health = 1000
        self.current_health = self.max_health
        
        # ── RIGID BODY SYSTEM ──
        # Create a circular rigid body collider
        # Position it at the player's center, with a smaller radius than the sprite
        collider_radius = 30  # Adjust this to fit your player size
        center_x = self.rect.centerx
        center_y = self.rect.centery
        self.rigid_body = RigidBody(center_x, center_y, collider_radius, mass=1.0)
        
        # Sync the rigid body position with sprite position
        self.world_x = self.rect.x  # Track world position for camera

    def take_damage(self, damage, ui_system=None):
        if self.is_dead or self.state in ('hurt', 'death'):
            return  # Don't take damage if already dead or hurt
        
        # Check if player is using skill (invincible during skill)
        if self.state == 'skill':
            print(f"Player is invincible during skill! {damage} damage missed!")
            # Create "Miss" text if UI system is provided
            if ui_system:
                ui_system.add_damage_text(self.rect.centerx, self.rect.centery - 150, "Miss", (255, 255, 0))
            return  # No damage taken when using skill
        
        # Check if player is blocking
        if self.blocking:
            print(f"Player blocked {damage} damage!")
            # Create "Blocked" text if UI system is provided
            if ui_system:
                ui_system.add_damage_text(self.rect.centerx, self.rect.centery - 150, "Blocked", (60, 80, 120))
            return  # No damage taken when blocking
        
        self.current_health -= damage
        print(f"Player took {damage} damage! Health: {self.current_health}/{self.max_health}")
        
        # Create damage text if UI system is provided
        if ui_system:
            ui_system.add_damage_text(self.rect.centerx, self.rect.centery - 150, damage, (255, 50, 50))
        
        if self.current_health <= 0:
            self.current_health = 0
            self.is_dead = True
            self.state = 'death'
            self.frame = 0.0
            print("PLAYER DIED!")
            # Handle player death (e.g., reset game, show game over screen)
        else:
            # Reset all special states when taking damage
            self.reset_counter_state()
            self.blocking = False
            self.block_animation_state = 'none'
            self.dashing = False
            
            self.state = 'hurt'
            self.frame = 0.0


    def draw_attack_point(self, screen, cam_x, cam_y):
        # Adjust the attack point position by the camera offset
        adjusted_attack_point = (self.attack_point[0] - cam_x, self.attack_point[1] - cam_y)
        # Draw the attack point as a circle
        pygame.draw.circle(screen, (255, 0, 0), adjusted_attack_point, self.attack_radius, 1)
        # Draw skill AOE radius (semi-transparent fill + outline) so it's easier to
        # see and tweak.  The colour & alpha make it clearly visible over most
        # backgrounds.
        skill_center = (self.rect.centerx - cam_x, self.rect.centery - cam_y)
        # Create a temporary surface with per-pixel alpha for the filled circle
        radius = self.skill_radius
        tmp_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        # Semi-transparent blue fill (alpha 60/255)
        pygame.draw.circle(tmp_surf, (0, 120, 255, 60), (radius, radius), radius)
        # Solid outline (width 3)
        pygame.draw.circle(tmp_surf, (0, 180, 255), (radius, radius), radius, 3)
        # Blit centred on player
        screen.blit(tmp_surf, (skill_center[0]-radius, skill_center[1]-radius))
    
    def draw_rigid_body_debug(self, screen, cam_x, cam_y, show_velocity=False):
        """Draw the rigid body collider for debugging"""
        self.rigid_body.draw_debug(screen, cam_x, cam_y, color=(0, 255, 0), width=2, show_velocity=show_velocity)
    
    # Debug method removed after fixing jump animation issue
    
    def check_tile_collision_below(self, tile_rects):
        """Check if there's a solid tile below the player for ground detection"""
        # Create a wider rectangle below the player's feet - much wider to prevent falling at level transitions
        # Start 1 pixel above feet so a tile whose top equals rect.bottom is detected
        check_rect = pygame.Rect(
            self.rect.centerx - 40,
            self.rect.bottom - 1,
            80,
            33  # cover same depth plus the extra pixel
        )
        
        # Check collision with any tile
        found_ground = None
        for tile_rect in tile_rects:
            if check_rect.colliderect(tile_rect):
                # If we find multiple ground tiles, use the highest one
                if found_ground is None or tile_rect.top < found_ground:
                    found_ground = tile_rect.top
        
        # If no ground found with initial check, try an even wider check for level transitions
        if found_ground is None and len(tile_rects) > 0:
            transition_check_rect = pygame.Rect(
                self.rect.centerx - 100,  # Very wide check (nearly 2 tiles wide)
                self.rect.bottom,         # Start at player's feet
                200,                      # Extra wide for seamless level transitions
                64                        # Check a full tile height down
            )
            
            for tile_rect in tile_rects:
                if transition_check_rect.colliderect(tile_rect):
                    # Use the highest ground found
                    if found_ground is None or tile_rect.top < found_ground:
                        found_ground = tile_rect.top
        
        # Store previous ground for reference (debug prints removed)
        if not hasattr(self, '_prev_found_ground'):
            self._prev_found_ground = found_ground
        self._prev_found_ground = found_ground
        
        # Return the highest ground found or None
        return found_ground

    def update_attack_point(self):
        # Update the attack point position based on player direction during attacks and counter attacks
        if isinstance(self.state, int) or self.state == 'counter_attack':  # Attack states (1, 2, 3) or counter attack
            offset_x = 200 if self.facing == 1 else -200  # Adjust this value as needed
            offset_y = -50  # Adjust this if you need to change the vertical position
            self.attack_point = (self.rect.centerx + offset_x, self.rect.centery + offset_y)
        else:
            # Keep the attack point at a default position when not attacking
            self.attack_point = (self.rect.centerx, self.rect.centery)

    def check_attack_hit(self, enemy):
        # Check if the attack point hits the enemy
        distance = pygame.math.Vector2(self.attack_point).distance_to(enemy.rect.center)
        # Ensure the enemy is in the direction the player is facing
        enemy_direction = 1 if enemy.rect.centerx > self.rect.centerx else -1
        return distance <= self.attack_radius + enemy.rect.width / 2 and enemy_direction == self.facing
    
    def check_counter_timing(self):
        """Check if enemy is in the counter window (50%-70% of attack animation)"""
        if not self.target:
            return False
        
        # Handle different enemy types
        if hasattr(self.target, '__class__') and self.target.__class__.__name__ == 'Yori':
            # Yori boss - check for any of the 3 attack states
            if self.target.state not in ('attack1', 'attack2', 'attack3'):
                return False
            
            # Get the appropriate attack animation based on current state
            if self.target.state == 'attack1':
                attack_frames = self.target.attack1
            elif self.target.state == 'attack2':
                attack_frames = self.target.attack2
            elif self.target.state == 'attack3':
                attack_frames = self.target.attack3
            else:
                return False
            
            # Counter window: between 30% and 70% of Yori's current attack animation
            counter_frame_start = len(attack_frames) * 0.3
            counter_frame_end = len(attack_frames) * 0.7
            
            return (counter_frame_start <= self.target.frame <= counter_frame_end and 
                    not self.target.damage_dealt)
        
        else:
            # Regular enemy (enemy1)
            if self.target.state != 'attack':
                return False
            
            # Use a tighter counter window (30%-70%) to prevent very early counters
            counter_frame_start = len(self.target.attack) * 0.3
            counter_frame_end = len(self.target.attack) * 0.7
            
            # Check if we're strictly inside the window (exclude the exact edges) –
            # this avoids accidental counters on the very first animation frame.
            in_counter_window = (counter_frame_start < self.target.frame < counter_frame_end)
            damage_not_dealt = not self.target.damage_dealt
            counter_possible = in_counter_window and damage_not_dealt
            
            # Print debug info only on counter attempt
            """ print(f"DEBUG - Enemy counter check: Frame {self.target.frame:.1f}/{len(self.target.attack)}, " + 
                  f"Window: {counter_frame_start:.1f}-{counter_frame_end:.1f}, " + 
                  f"Damage dealt: {self.target.damage_dealt}, Counter possible: {counter_possible}") """
            
            return counter_possible
    
    def perform_counter(self):
        """Successfully counter the enemy attack"""
        print("PERFECT COUNTER!")
        if self.sfx_counter:
            self.sfx_counter.play()
        self.countering = True
        self.counter_success = True
        self.counter_ready = True  # Make counter attack available immediately!
        self.state = 'counter'
        self.frame = 0.0
        self.dir = 0  # Stop movement
        
        # Stop blocking - player must right-click again to block
        self.blocking = False
        self.block_animation_state = 'none'
        
        # Face the enemy
        if self.target:
            self.facing = 1 if self.target.rect.centerx > self.rect.centerx else -1
            self.flip = (self.facing == -1)
            
            # Prevent enemy from dealing damage
            self.target.damage_dealt = True
            print("Enemy damage blocked by perfect counter!")
            
            # Stun the enemy for 2 seconds
            if hasattr(self.target, 'stun'):
                self.target.stun_end_time = __import__('time').time() + 2.0  # 2 seconds stun
                self.target.stun()
                print("Enemy stunned for 2 seconds!")
            elif hasattr(self.target, '__class__') and self.target.__class__.__name__ == 'Yori':
                # For Yori boss, interrupt the attack combo and reset to idle
                print("Yori attack countered! Combo interrupted!")
                self.target.in_combo = False
                self.target.state = 'idle'
                self.target.frame = 0.0
                self.target.next_action_time = __import__('time').time() + 2.0  # 2 second pause
                self.target.damage_dealt = True  # Prevent damage from current attack
        
        print("Counter attack ready! Left-click NOW to perform counter attack!")
    
    def counter_failed(self):
        """Failed to counter - show miss text, stop blocking, and allow damage"""
        print("COUNTER FAILED - MISS!")
        if self.sfx_counter:
            self.sfx_counter.play()
        
        # Show miss text if UI system is available
        if hasattr(self, 'ui_system') and self.ui_system:
            self.ui_system.add_damage_text(self.rect.centerx, self.rect.centery - 100, "MISS", (255, 100, 100))
        
        # Stop blocking immediately - player will take damage
        self.blocking = False
        self.block_animation_state = 'none'
        
        # Play counter animation anyway to prevent spamming
        self.countering = True
        self.counter_success = False  # Mark as failed counter
        self.state = 'counter'
        self.frame = 0.0
        self.dir = 0  # Stop movement
        
        # Face the enemy
        if self.target:
            self.facing = 1 if self.target.rect.centerx > self.rect.centerx else -1
            self.flip = (self.facing == -1)
        
        # Don't prevent enemy damage - player will get hit
        print("Player is vulnerable to enemy attack!")
    
    def start_counter_attack(self):
        """Start the counter attack after successful counter"""
        print("Starting counter attack!")
        if self.sfx_counter_attack:
            self.sfx_counter_attack.play()
        self.counter_attacking = True
        self.countering = False  # Stop counter animation
        self.state = 'counter_attack'
        self.frame = 0.0
        
        # Ensure the damage dealt flag is properly initialized for counter attack
        self._counter_damage_dealt = False
        
        # Face the enemy for counter attack
        if self.target:
            self.facing = 1 if self.target.rect.centerx > self.rect.centerx else -1
            self.flip = (self.facing == -1)
            
        # Immediately update attack point to ensure proper positioning
        self.update_attack_point()
    
    def perform_counter_attack_damage(self):
        """Deal damage during counter attack and stun enemy"""
        print(f"DEBUG: Attempting counter attack damage - target exists: {self.target is not None}")
        if self.target:
            print(f"DEBUG: Player attack point: {self.attack_point}, facing: {self.facing}")
            print(f"DEBUG: Enemy position: {self.target.rect.center}")
            distance = pygame.math.Vector2(self.attack_point).distance_to(self.target.rect.center)
            enemy_direction = 1 if self.target.rect.centerx > self.rect.centerx else -1
            print(f"DEBUG: Distance: {distance}, Attack radius: {self.attack_radius}, Enemy direction: {enemy_direction}")
            
            if self.check_attack_hit(self.target):
                print(f"Counter attack hits for {self.counter_attack_damage} damage!")
                
                # Temporarily allow damage to stunned enemy for counter attack
                was_stunned = (self.target.state == 'stun')
                if was_stunned:
                    # Temporarily change state to allow damage
                    original_state = self.target.state
                    self.target.state = 'idle'
                
                # Deal damage normally first
                self.target.take_damage(self.counter_attack_damage, getattr(self, 'ui_system', None))
                
                # If target is Yori, also trigger block animation
                if hasattr(self.target, '__class__') and self.target.__class__.__name__ == 'Yori':
                    if self.target.current_health > 0:  # Only if Yori is still alive
                        self.target.start_block_animation()
                
                # Remove stun after successful counter-attack so the enemy can continue fighting
                if was_stunned and self.target.current_health > 0:
                    # Clear stun flags/state
                    self.target.state = 'hurt'
                    if hasattr(self.target, 'stunned'):
                        self.target.stunned = False
                    if hasattr(self.target, 'stun_timer'):
                        self.target.stun_timer = 0
                
                print("Counter attack damage dealt!")
            else:
                print("Counter attack missed!")
        else:
            print("Counter attack missed - no target!")
    
    def reset_counter_state(self):
        """Reset all counter-related states and return to idle"""
        self.countering = False
        self.counter_success = False
        self.counter_attacking = False
        self.counter_ready = False
        
        # Reset damage flag for next counter attack
        self._counter_damage_dealt = False
        
        # Always return to idle - player must right-click again to block
        self.state = 'idle'
        self.frame = 0.0

    def handle_event(self, e):
        # Don't handle events if dead or hurt
        if self.is_dead or self.state in ('hurt', 'death'):
            return

        # ── handle blocking input (right mouse button) ──
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:  # Right mouse button
            if (not self.blocking and not isinstance(self.state, int) and not self.dashing and 
                not self.countering and not self.counter_attacking and 
                self.state not in ('counter', 'counter_attack', 'skill')):
                self.blocking = True
                self.block_animation_state = 'entering'
                self.state = 'block'
                self.frame = 0.0
                self.dir = 0  # Stop movement when blocking starts
                print("Player started blocking")
        
        if e.type == pygame.MOUSEBUTTONUP and e.button == 3:  # Right mouse button released
            if self.blocking and self.block_animation_state in ('entering', 'holding'):
                self.block_animation_state = 'exiting'
                print("Player releasing block")

        # ── handle jump input ──
        if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
            # allow up to double jump if not dashing, not blocking, not countering, and not counter attacking
            if (self.jumps < 2 and not self.dashing and not self.blocking and 
                not self.countering and not self.counter_attacking and 
                self.state not in ('counter', 'counter_attack')):
                
                # Remove debounce check to ensure jump always registers
                # Track the jump
                self.last_jump_time = pygame.time.get_ticks()
                self.jumps += 1
                
                # Force grounded state to false immediately when jumping
                self.rigid_body.is_grounded = False
                
                # choose animation: first jump vs second jump
                self.state = 'jump' if self.jumps == 1 else 'jump2'
                self.frame = 0.0
                
                # Apply stronger jump impulse for the second jump to ensure height
                jump_power = JUMP_V * (1.2 if self.jumps == 2 else 1.0)
                
                # Apply jump impulse to rigid body instead of setting vel_y directly
                # Cancel any existing vertical velocity first to prevent additive effect
                self.rigid_body.velocity_y = 0 
                self.rigid_body.apply_impulse(0, jump_power)

        # ── handle skill input (Q) ──
        if e.type == pygame.KEYDOWN and e.key == pygame.K_q:
            now_ms = pygame.time.get_ticks()
            # Check cooldown and ensure player is not already performing skill or dead/hurt
            if (now_ms - self.last_skill_time_ms >= self.skill_cooldown and
                not self.is_dead and self.state not in ('hurt', 'death', 'skill')):
                # ── Cancel any current action immediately ──
                self.dashing = False
                self.blocking = False
                self.block_animation_state = 'none'
                self.countering = False
                self.counter_attacking = False
                # If attacking, reset attack variables
                if isinstance(self.state, int):
                    self._atk_covered = 0.0
                # Stop movement completely
                self.rigid_body.velocity_x = 0
                # Activate skill instantly
                self.state = 'skill'
                self.frame = 0.0
                self.dir = 0
                self._skill_damage_dealt = False
                self.last_skill_time_ms = now_ms
                if self.sfx_skill:
                    self.sfx_skill.play()
                print("Skill activated!")

        # ── handle dash input ──
        if e.type == pygame.KEYDOWN and e.key == pygame.K_LSHIFT:
            # Check if blocking and can counter
            if self.blocking and not self.countering:
                # Anti-spam: prevent counter attempts too frequently
                now = pygame.time.get_ticks()
                if now - self.last_counter_time < 500:  # 500ms cooldown between counter attempts
                    return
                
                self.last_counter_time = now
                # Attempt to counter - check if enemy is in damage frame
                counter_possible = self.check_counter_timing()
                """ print(f"DEBUG - Counter attempt! Target: {self.target.__class__.__name__ if self.target else 'None'}, " +
                      f"Counter possible: {counter_possible}") """
                
                if self.target and counter_possible:
                    self.perform_counter()
                else:
                    self.counter_failed()
            # only dash when not already dashing, not attacking, not blocking, and not countering
            elif not self.dashing and not isinstance(self.state, int) and not self.blocking and not self.countering and not self.counter_attacking:
                # Check if right mouse button is currently pressed
                mouse_buttons = pygame.mouse.get_pressed()
                if not mouse_buttons[2]:  # Right mouse button (index 2) is not pressed
                    self.dashing    = True
                    self.dash_start = pygame.time.get_ticks()  # e.g. 123456 ms
                    self.state      = 'dash'
                    self.frame      = 0.0
                    if self.sfx_dash:
                        self.sfx_dash.play()

    def handle_input(self):
        # Don't handle input if dead, hurt, blocking, countering, counter attacking, or using skill
        # Allow input when counter_ready is true, even if countering
        if (self.is_dead or self.state in ('hurt', 'death', 'skill') or 
            (self.blocking and not self.counter_ready) or 
            self.countering or self.counter_attacking or 
            self.state in ('counter', 'counter_attack')):
            return
        
        keys = pygame.key.get_pressed()
        
        # Check held right mouse button to initiate block once available
        mouse_buttons = pygame.mouse.get_pressed()
        if (mouse_buttons[2] and not self.blocking and not isinstance(self.state, int)
        and not self.dashing and not self.countering and not self.counter_attacking
        and self.state not in ('counter', 'counter_attack', 'skill')):
            self.blocking = True
            self.block_animation_state = 'entering'
            self.state = 'block'
            self.frame = 0.0
            self.dir = 0
            print("Block auto-started from held RMB")
            return  # prevent walk/dir logic in same frame

        # Only update direction and facing if not attacking
        if not isinstance(self.state, int):
            if keys[pygame.K_d]:
                self.dir = 1
                self.facing = 1
                if self.state not in ('jump', 'jump2', 'dash'):
                    if self.state != 'walk_start' and self.state != 'walk':
                        self.state = 'walk_start'
            elif keys[pygame.K_a]:
                self.dir = -1
                self.facing = -1
                if self.state not in ('jump', 'jump2', 'dash'):
                    if self.state != 'walk_start' and self.state != 'walk':
                        self.state = 'walk_start'
            else:
                self.dir = 0
                if self.state == 'walk':
                    self.state = 'walk_stop'
                    self.frame = 0.0
                elif self.state == 'walk_stop' and int(self.frame) == len(self.anims['walk_stop']) - 1:
                    self.state = 'idle'

        # Only update flip when not attacking, not blocking, and not countering
        if not isinstance(self.state, int) and not self.blocking and not self.countering and not self.counter_attacking:
            self.flip = (self.facing == -1)


    def animate(self):
        # pick the right sequence based on current state
        seq = self.anims[self.state]

        # Special handling for blocking animation
        if self.state == 'block':
            if self.block_animation_state == 'entering':
                # Play forward animation with ease-out
                progress = self.frame / (len(seq) - 1) if len(seq) > 1 else 1
                # Simple ease-out: start fast, end slow
                speed_multiplier = 1.5 - (progress * 0.8)  # 1.5 to 0.7
                
                self.frame += self.block_animation_speed * speed_multiplier
                if self.frame >= len(seq) - 1:
                    self.frame = len(seq) - 1  # Clamp to last frame
                    self.block_animation_state = 'holding'
                    print("Block animation complete - holding")
            
            elif self.block_animation_state == 'holding':
                # Stay on last frame
                self.frame = len(seq) - 1
            
            elif self.block_animation_state == 'exiting':
                # Play reverse animation with ease-in
                progress = (len(seq) - 1 - self.frame) / (len(seq) - 1) if len(seq) > 1 else 1
                # Simple ease-in: start slow, end fast
                speed_multiplier = 0.8 + (progress * 0.7)  # 0.8 to 1.5
                
                self.frame -= self.block_animation_speed * speed_multiplier
                if self.frame <= 0:
                    self.frame = 0.0
                    self.blocking = False
                    self.block_animation_state = 'none'
                    self.state = 'idle'
                    print("Block animation finished - back to idle")
            
            img = seq[int(self.frame)]
        
        # Special handling for counter animations
        elif self.state == 'counter':
            # Play counter animation once
            self.frame += 0.4  # Fast counter animation
            
            if self.frame >= len(seq) - 1:
                # Counter animation finished
                if self.counter_success:
                    # Successful counter - stay in idle, waiting for click
                    self.state = 'idle'  # Return to idle, waiting for click
                    self.frame = 0.0
                    self.countering = False  # Allow input handling
                else:
                    # Failed counter - return to blocking
                    self.reset_counter_state()
            img = seq[int(self.frame)]
        
        elif self.state == 'counter_attack':
            seq = self.anims['counter_attack']
            self.frame += 0.3
            if not self._counter_damage_dealt and self.frame >= len(seq)*0.7:
                self.perform_counter_attack_damage()
                self._counter_damage_dealt = True
            if self.frame >= len(seq)-1:
                self.reset_counter_state()
                self.last_attack_time = 0
            img = seq[int(self.frame)]

            
        elif self.state == 'skill':
            # play once
            self.frame += 0.35
            seq = self.anims['skill']
            # damage at 50%
            if not self._skill_damage_dealt and self.frame >= len(seq)*0.5:
                self._skill_damage_dealt = True
                damage = self.skill_damage
                ui_system = getattr(self, 'ui_system', None)
                if hasattr(self, 'all_enemies'):
                    for enemy in self.all_enemies:
                        # Use distance to center point for circular AOE
                        dist = pygame.math.Vector2(self.rect.center).distance_to(enemy.rect.center)
                        if dist <= self.skill_radius + enemy.rect.width/2:
                            enemy.take_damage(damage, ui_system)
                print("Skill dealt damage")
            if self.frame >= len(seq)-1:
                self.state = 'idle'
                self.frame = 0.0
            img = seq[int(self.frame)]
            
            # Deal damage at 70% of animation
            if not hasattr(self, '_counter_damage_dealt'):
                self._counter_damage_dealt = False
            
            if not self._counter_damage_dealt and self.frame >= len(seq) * 0.7:
                self.perform_counter_attack_damage()
                self._counter_damage_dealt = True
            
            if self.frame >= len(seq) - 1:
                # Counter attack finished, reset counter state and attack sequence
                self.reset_counter_state()  # This will handle state transition properly
                # Reset attack sequence back to 1, 2, 3
                self.last_attack_time = 0  # Reset attack timing to allow fresh sequence
                print("Counter attack finished! Attack sequence reset to 1, 2, 3")
            
            img = seq[int(self.frame)]
        
        else:
            # Normal animation logic for all other states
            # choose frame-advance speed
            if isinstance(self.state, int):
                if self.state == 2:
                    speed = 0.1  # slower speed for attack 2
                else:
                    speed = 0.3  # default speed for other attacks
            elif self.state == 'walk_start':
                speed = 0.9  # speed for walk start animation
                if int(self.frame) == len(seq) - 1:
                    self.state = 'walk'
                    self.frame = 0.0
            elif self.state == 'walk_stop':
                speed = 0.9  # speed for walk stop animation
            elif self.state == 'walk':
                speed = 0.6  # speed for walking animation
            elif self.state == 'dash':
                speed = 0.3
            elif self.state in ('jump','jump2'):
                speed = 0.25
            elif self.state == 'hurt':
                speed = 0.2  # hurt animation speed
            elif self.state == 'death':
                speed = 0.3  # death animation speed
            else:
                speed = 0.2         # idle, default

            # Advance the frame
            self.frame = self.frame + speed
            
            # For jump animations, freeze on the last frame instead of looping
            if self.state in ('jump', 'jump2') and self.frame >= len(seq):
                self.frame = len(seq) - 1
                # Check if we're grounded but still showing jump animation
                if self.rigid_body.is_grounded:
                    # Force transition to idle if we're on the ground but still in jump animation
                    self.state = 'idle'
                    self.frame = 0.0
            else:
                # For other animations, wrap around
                self.frame = self.frame % len(seq)
                
            img = seq[int(self.frame)]

        # apply flip if facing left
        if self.flip:
            img = pygame.transform.flip(img, True, False)

        # set the sprite image & update rect to keep bottom alignment
        self.image = img
        self.rect  = img.get_rect(midbottom=self.rect.midbottom)

        # ── walking sound loop management ──
        if self.state == 'walk' and self.sfx_walk:
            if not self._walk_sound_playing:
                self.sfx_walk.play(loops=-1)
                self._walk_sound_playing = True
        else:
            if self._walk_sound_playing and self.sfx_walk:
                self.sfx_walk.stop()
                self._walk_sound_playing = False

    def update(self):
        now = pygame.time.get_ticks()  # current time in ms
        # ── external knockback management (set by enemies) ──
        if hasattr(self, 'knockback_end_time'):
            # If player died during knock-back, abort knock-back handling and let death anim run
            if self.is_dead:
                delattr(self, 'knockback_end_time')
            elif now < self.knockback_end_time:
                # During knockback: keep block pose, no input or other actions
                self.blocking = True
                self.block_animation_state = 'holding'
                self.state = 'block'

                # Make sure physics treats the player as airborne during knock-back
                # This avoids the stronger ground friction that would otherwise
                # shorten the push-back distance on subsequent hits.
                self.rigid_body.is_grounded = False

                # Apply a consistent horizontal slow-down (air drag style)
                self.rigid_body.velocity_x *= 0.95

                # ── update physics & sync sprite ──
                self.rigid_body.update_physics()
                rb_x, rb_y = self.rigid_body.get_position()
                self.rect.centerx = int(rb_x)
                self.rect.centery = int(rb_y)
                self.world_x = self.rect.centerx

                # Ensure correct block frame is shown during knock-back
                self.animate()
                return  # skip the rest until knockback finishes
            else:
                # Knockback finished – clean up once
                delattr(self, 'knockback_end_time')
                self.blocking = False
                self.block_animation_state = 'none'
                self.state = 'idle'
                # stop residual velocity completely
                self.rigid_body.velocity_x = 0
                self.rigid_body.velocity_y = 0
        
        # Always check if we're on ground but still showing jump animation
        # This needs to run EVERY frame, before any other logic
        if self.rigid_body.is_grounded and self.state in ('jump', 'jump2'):
            # Transition from jump to idle/walk when on ground
            if self.dir != 0:
                self.state = 'walk'
            else:
                self.state = 'idle'
            self.frame = 0.0
            self.jumps = 0
            
        self.handle_input()


        # Handle hurt state
        if self.state == 'hurt':
            self.animate()
            # When hurt animation ends, return to idle
            if int(self.frame) >= len(self.anims['hurt']) - 1:
                self.state = 'idle'
                self.frame = 0.0
            return  # Skip other updates while hurt
        
        # Handle death state
        if self.state == 'death':
            self.animate()
            # Death animation plays once and stays on last frame
            if int(self.frame) >= len(self.anims['death']) - 1:
                self.frame = len(self.anims['death']) - 1  # Stay on last frame
            return  # Skip all other updates when dead

        # Update attack point position
        self.update_attack_point()


         # Check if the attack state should reset
        if isinstance(self.state, int) and (now - self.last_attack_time > self.attack_delays.get(self.state, 0)):
            if self.state < 3:
                self.state += 1
                self.last_attack_time = now  # Reset the attack timer for the next attack
            else:
                self.state = 'idle'
                self.frame = 0.0

        # ── DASH LOGIC ──
        if self.dashing:
            finished = (now - self.dash_start) > DASH_DURATION
            # Move by dash distance directly (like original code)
            dx = DASH_SPEED * ( -1 if self.flip else 1 )
            self.rect.x += dx  # Move sprite directly like original
            # Keep rigid body synced with sprite
            self.rigid_body.set_position(self.rect.centerx, self.rect.centery)
            self.animate()
            if finished:
                self.dashing = False
                # Clear any accumulated velocity from dash
                self.rigid_body.velocity_x = 0
                # Go to idle after dash
                self.state = 'idle'
                self.frame = 0.0
                # Reset jump counters on dash-landing so jumping works again
                self.jumps = 0
                self.last_jump_time = 0
            return  # skip the rest while dashing

        # ── ATTACK LUNGE (ease-out) ──
        if isinstance(self.state, int):
            seq   = self.anims[self.state]
            speed = 0.3
            # advance until last frame
            self.frame = min(self.frame + speed, len(seq) - 1)
            img = seq[int(self.frame)]
            if self.flip:
                img = pygame.transform.flip(img, True, False)
            self.image = img
            self.rect  = img.get_rect(midbottom=self.rect.midbottom)

            # compute progress 0→1 then eased distance
            prog  = self.frame / (len(seq) - 1)
            eased = ease_out_quad(prog)      # e.g. at prog=0.5, eased≈0.75
            target = ATTACK_DIST * eased     # e.g. 70 * 0.75 = 52.5 px
            delta  = target - self._atk_covered
            # Apply attack lunge by moving sprite directly (like original code)
            if delta > 0:
                self.rect.x += self.facing * delta
                # Keep rigid body synced with sprite
                self.rigid_body.set_position(self.rect.centerx, self.rect.centery)
            self._atk_covered = target

            # when animation ends, reset to idle (or trigger queued skill)
            if self.frame >= len(seq) - 1:
                # End of attack – revert to idle state
                self.state        = 'idle'
                self.frame        = 0.0
                self._atk_covered = 0.0
                # Clear any accumulated velocity from attack and sync positions
                self.rigid_body.velocity_x = 0
                self.rigid_body.set_position(self.rect.centerx, self.rect.centery)

            return  # skip movement & gravity during attack

        # ── RIGID BODY PHYSICS ──
        # Set horizontal velocity directly for walking (instead of applying forces)
        if not self.dashing:
            # Lock movement during counter states and skill
            if (self.countering or self.counter_attacking or 
                self.state in ('counter', 'counter_attack', 'skill')):
                self.rigid_body.velocity_x = 0  # Completely stop horizontal movement
                self.dir = 0  # Ensure direction is also locked
            elif self.dir != 0:
                # Set horizontal velocity directly to match original movement speed
                self.rigid_body.velocity_x = self.dir * MOVE_SPEED
            else:
                # Apply friction when not moving
                self.rigid_body.velocity_x *= 0.8
            self.animate()

        # Update rigid body physics
        self.rigid_body.update_physics()
        
          # Check ground collision with rigid body only if ground_y is set
        if self.ground_y is not None:
             self.rigid_body.check_ground_collision(self.ground_y)
             # Track ground_y changes (without debug prints)
             if not hasattr(self, '_prev_ground_y'):
                 self._prev_ground_y = self.ground_y
             self._prev_ground_y = self.ground_y
        else:
            # If no ground is detected, make sure is_grounded is False to allow falling
            self.rigid_body.is_grounded = False
            if hasattr(self, '_prev_ground_y'):
                self._prev_ground_y = None
         
        
        # Sync sprite position with rigid body (only for normal movement)
        # During dash and attack, we move the sprite directly and sync rigid body to sprite
        if not self.dashing and not isinstance(self.state, int):
            rb_center_x, rb_center_y = self.rigid_body.get_position()
            self.rect.centerx = int(rb_center_x)
            self.rect.centery = int(rb_center_y)
        
        # Update world position (use centerx for more stable transitions)
        self.world_x = self.rect.centerx

        # Handle ground and air states
        # STEP 1: Determine if player just landed this frame
        was_in_air = not hasattr(self, '_prev_grounded') or not self._prev_grounded
        just_landed = was_in_air and self.rigid_body.is_grounded
        
        # STEP 2: Handle landing
        if just_landed:
            # Player just landed - reset to idle
            if self.state in ('jump', 'jump2'):
                # Reset state
                self.state = 'idle'
                self.frame = 0.0
                # Reset jumps counter for next jump
                self.jumps = 0
                # Reset jump timer
                self.last_jump_time = 0
                # Explicitly set Y-velocity to zero
                self.rigid_body.velocity_y = 0
                # Player landed (debug print removed)
        
        # STEP 3: Handle air state
        elif not self.rigid_body.is_grounded:
            # Only use falling animation if player fell off a ledge (not after jumping)
            # Check if we're falling but not in a jump state already and not coming from a jump
            if (self.rigid_body.velocity_y > 1 and 
                self.state not in ('jump', 'jump2') and 
                not self.dashing and 
                not isinstance(self.state, int) and 
                not self.blocking and
                self.jumps == 0):  # Only apply if we haven't jumped (fell off a ledge)
                
                # Set falling animation if fell off a ledge
                self.state = 'jump'
                # Use the last frame of jump animation for falling
                self.frame = len(self.anims['jump']) - 1
            
            # If we're in jump state, make sure we're using the right frame
            elif self.state in ('jump', 'jump2'):
                # Check velocity - if going down, show last frame
                if self.rigid_body.velocity_y > 0:
                    # Going down - show last frame of jump animation
                    target_frame = len(self.anims[self.state]) - 1
                    if int(self.frame) != target_frame:
                        self.frame = target_frame
        
        # STEP 4: Handle transitions from jump to walk/idle while on ground
        elif self.rigid_body.is_grounded:
            # Already on ground - make sure jump state is cleared
            if self.state in ('jump', 'jump2'):
                if self.dir != 0:
                    # Moving - transition to walk
                    self.state = 'walk'
                else:
                    # Not moving - transition to idle
                    self.state = 'idle'
                self.frame = 0.0
                self.jumps = 0
                # Ensure velocity is properly set
                self.rigid_body.velocity_y = 0
        
        # Store current grounded state for next frame comparison
        self._prev_grounded = self.rigid_body.is_grounded

    def click(self):
        # Check if counter attack is ready first (highest priority)
        if self.counter_ready:
            # Execute counter attack
            self.start_counter_attack()
            self.counter_ready = False
            return

        # Don't allow normal attacks if dead, hurt, blocking, countering, or counter attacking
        if (self.is_dead or self.state in ('hurt', 'death') or 
            self.blocking or self.countering or self.counter_attacking or 
            self.state in ('counter', 'counter_attack')):
            return

        now = pygame.time.get_ticks()  # current time in ms

        # ignore clicks mid-air
        if self.state in ('jump', 'jump2'):
            return
            
        # Check if we're still in the attack cooldown period
        if now - self.last_attack_time < self.attack_cooldown:
            return  # Ignore clicks during cooldown
            
        # Check if the click is within the allowed delay for combo transitions
        if isinstance(self.state, int) and (now - self.last_attack_time <= self.attack_delays.get(self.state, 0)):
            # cycle through attack states 1→2→3, then back to 1
            if self.state < 3:
                self.state += 1
            else:
                self.state = 1
        else:
            # Start from attack 1 if the delay has passed
            self.state = 1

        # Update the last attack time
        self.last_attack_time = now

        # Determine damage based on attack type
        if self.sfx_attack.get(self.state):
            self.sfx_attack[self.state].play()
        damage = {1: 20, 2: 40, 3: 60}.get(self.state, 0)

        # Check if the attack hits any enemies within range (AOE attack)
        hit_count = 0
        ui_system = getattr(self, 'ui_system', None)
        if hasattr(self, 'all_enemies') and self.all_enemies:
            for enemy in self.all_enemies:
                if self.check_attack_hit(enemy):
                    enemy.take_damage(damage, ui_system)
                    hit_count += 1
            if hit_count > 0:
                print(f"Player hit {hit_count} enemy(ies) for {damage} damage each!")
        elif self.target and self.check_attack_hit(self.target):
            # Fallback to single target if all_enemies is not available
            self.target.take_damage(damage, ui_system)
            print(f"Player hit target for {damage} damage!")


        # reset animation & lunge tracker
        self.frame        = 0.0
        self._atk_covered = 0.0

    def reset(self):
        """Reset player to initial state"""
        self.current_health = self.max_health
        self.is_dead = False
        self.state = 'idle'
        self.frame = 0.0
        self.vel_y = 0
        self.jumps = 0
        self.dashing = False
        self.blocking = False
        self.block_animation_state = 'none'
        # Reset counter system
        self.reset_counter_state()
        # Reset rigid body physics
        self.rigid_body.velocity_x = 0
        self.rigid_body.velocity_y = 0
        self.rigid_body.acceleration_x = 0
        self.rigid_body.acceleration_y = 0
        # Ensure player is properly grounded on reset
        self.rigid_body.is_grounded = True
        self._prev_grounded = True
        # Reset jump timer
        self.last_jump_time = 0
        print("Player reset!")
