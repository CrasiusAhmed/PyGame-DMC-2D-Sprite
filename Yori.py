import pygame, os, random, time
from rigidbody import RigidBody

# ── constant paths & sizes ──
IMG_DIR = os.path.join(os.path.dirname(__file__), 'img')
YORI_SIZE = (600, 600)  # Larger size for boss

# ── Yori Boss gameplay values ──
# ═══════════════════════════════════════════════════════════════════
# 🚶 YORI WALKING SPEED: Change WALK_SPEED to make Yori walk faster/slower
# ⚔️ YORI ATTACK SPEED: Change speed=0.25 in attack animations (lines ~350, ~390, ~430)
# 💥 KNOCKBACK DISTANCE: Change knockback_force in start_block_animation()
# ⏱️ KNOCKBACK DURATION: Change knockback_duration in __init__()
# 💀 DEATH KNOCKBACK: Change death_knockback_force in __init__()
# ═══════════════════════════════════════════════════════════════════
DETECT_RANGE = 1000       # Boss detects player when in level 5 and within range
ATTACK_STOP_DIST = 200    # Bigger distance - stop approaching when within this distance
WALK_SPEED = 7            # 🚶 YORI WALKING SPEED - Change this to make Yori walk faster/slower
DASH_SPEED = 8            # Speed when dashing back
DASH_DISTANCE = 250       # How far to dash back (bigger distance)
ATTACK_DELAY = 0.0        # No delay between individual attacks in combo
DASH_BACK_DELAY = 1.5     # Delay after dashing back before starting new combo

# ── helper to load & scale all frames in a folder ──
def load_frames(folder):
    path = os.path.join(IMG_DIR, folder)
    if not os.path.exists(path):
        print(f"Warning: Folder {path} not found!")
        return []
    files = sorted([f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))], 
                   key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else 0)
    return [
        pygame.transform.scale(
            pygame.image.load(os.path.join(path, f)).convert_alpha(),
            YORI_SIZE
        )
        for f in files
    ]

class Yori(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        
        # Load Yori animations
        self.idle = load_frames('Yori/Idle')
        self.walking = load_frames('Yori/Walking')  # Added walking animation
        self.attack1 = load_frames('Yori/Attack 1')
        self.attack2 = load_frames('Yori/Attack 2')
        self.attack3 = load_frames('Yori/Attack 3')
        self.dash = load_frames('Yori/Dash')
        self.hurt_counter = load_frames('Yori/Hurt Counter')  # Counter animation
        self.block = load_frames('Yori/Block')  # Block animation
        self.death = load_frames('Yori/Death')  # Death animation
        # Load counter related animations
        self.counter_wait = load_frames('Yori/Counter')          # Waiting (parry) stance
        self.counter = load_frames('Yori/Counter Attack')        # Actual counter attack animation
        self.skill = load_frames('Yori/Skill')  # Skill animation
        
        # Debug: Check if death animation loaded
        if self.death:
            print(f"Death animation loaded successfully! {len(self.death)} frames")
        else:
            print("WARNING: Death animation failed to load!")
        
        # Boss health - much higher than regular enemies
        self.max_health = 500
        self.current_health = self.max_health
        
        # Animation state
        self.state = 'idle'
        self.frame = 0.0
        
        # Counter and block states
        self.hurt_counter_time = 0
        self.block_time = 0
        self.counter_delay = 1.5  # Time to show hurt counter before allowing counter attack
        self.block_duration = 1.0  # Duration of block animation
        
        # New AI states for health below 55%
        self.low_health_threshold = 0.55  # 55% health threshold
        self.low_health_dialog_shown = False  # Track if low health dialog was shown
        self.should_trigger_low_health_dialog = False  # Flag for main.py to check
        self.can_counter_attack = False  # Can Yori counter attack player?
        self.counter_attack_chance = 0.3  # 30% chance to counter when health < 55%
        self.counter_attack_time = 0  # Time when counter attack started
        self.counter_attack_duration = 2.0  # Duration of counter attack animation
        # New counter wait (parry) mechanic
        self.counter_wait_duration = 3.0   # How long Yori holds counter stance
        self.counter_wait_start_time = 0
        # Lunge configuration for counter-attack
        self.counter_attack_lunge = 200   # pixels to move forward during counter
        self._counter_start_x = 0         # recorded start X for lunge easing
        self.skill_cooldown = 0  # Skill cooldown timer
        self.skill_cooldown_duration = 10.0  # 10 seconds between skill uses
        self.skill_time = 0  # Time when skill started
        self.skill_duration = 3.0  # Duration of skill animation
        self.skill_damage = 100  # Higher damage for skill attack
        self.should_use_skill = False  # Flag to use skill after dialog
        
        # Knockback animation system
        self.knockback_start_velocity = 0
        self.knockback_duration = 0.8  # How long the knockback lasts
        self.is_in_knockback = False
        
        # Death animation system
        self.death_time = 0
        self.death_knockback_force = 10.0  # 💀 DEATH KNOCKBACK DISTANCE - Change this value
        self.death_knockback_duration = 1.2  # How long death knockback lasts
        self.is_death_knockback = False
        self.cinematic_death = False      # Flag for cinematic death camera
        self.death_animation_done = False # Flag to indicate when death animation is complete
        self.death_animation_speed = 0.08 # Slow animation speed for dramatic effect (lower = slower)
        self.cinematic_death_duration = 6.0 # Extended time to maintain cinematic camera (in seconds)
        
        # Direction and facing
        self.dir = 1  # 1 = right, -1 = left
        self.flip = False
        
        # Set starting image & position
        if self.idle:
            self.image = self.idle[0]
        else:
            # Fallback if no idle frames
            self.image = pygame.Surface(YORI_SIZE, pygame.SRCALPHA)
            self.image.fill((255, 0, 0, 128))  # Red placeholder
        
        self.rect = self.image.get_rect(midbottom=pos)
        
        # Target (player) - will be set by main.py
        self.target = None
        
        # Attack system - 3-attack combo
        self.attack_combo_count = 0  # Track which attack in combo (0, 1, 2 for attacks 1, 2, 3)
        self.attack_damage = 75  # Higher damage for boss
        self.attack_point = (self.rect.centerx, self.rect.centery)
        self.attack_radius = 120  # Larger attack radius
        self.damage_dealt = False
        self.damage_frame = 0.6  # Deal damage at 60% of animation
        
        # Boss AI timing
        self.next_action_time = 0
        self.dash_target_x = 0
        self.is_dashing = False
        self.in_combo = False  # Track if currently in attack combo
        
        # UI system reference
        self.ui_system = None

        # ── load SFX ──
        self.sfx_walk = None
        self.sfx_dash = None
        self.sfx_attack = {}
        self.sfx_skill = None
        self.sfx_counter = None
        try:
            pw = os.path.join('Music', 'Walking.mp3')
            if os.path.isfile(pw):
                self.sfx_walk = pygame.mixer.Sound(pw)
                self.sfx_walk.set_volume(0.7)
            pd = os.path.join('Music', 'Dashing.mp3')
            if os.path.isfile(pd):
                self.sfx_dash = pygame.mixer.Sound(pd)
            ps = os.path.join('Music', 'Yori Skill.mp3')
            if os.path.isfile(ps):
                self.sfx_skill = pygame.mixer.Sound(ps)
            else:
                # Use a fallback sound if skill sound is missing
                ps = os.path.join('Music', 'Hiichigava Skill.mp3')
                if os.path.isfile(ps):
                    self.sfx_skill = pygame.mixer.Sound(ps)
            # Load counter sound
            pc = os.path.join('Music', 'Yori Counter.mp3')
            if os.path.isfile(pc):
                self.sfx_counter = pygame.mixer.Sound(pc)
                print("Yori Counter sound loaded successfully!")
            else:
                print("Warning: Yori Counter.mp3 not found!")
            # Load attack sounds with better error handling
            for i in (1,2,3):
                # Support both "Yori Attack {i}.mp3" and "Yori Attack{i}.mp3" (no space) filenames
                pa_space = os.path.join('Music', f'Yori Attack {i}.mp3')
                pa_nospace = os.path.join('Music', f'Yori Attack{i}.mp3')
                chosen_path = None
                if os.path.isfile(pa_space):
                    chosen_path = pa_space
                elif os.path.isfile(pa_nospace):
                    chosen_path = pa_nospace
                if chosen_path:
                    self.sfx_attack[i] = pygame.mixer.Sound(chosen_path)
                    print(f"Yori Attack {i} sound loaded successfully! (" + os.path.basename(chosen_path) + ")")
                else:
                    print(f"Warning: Yori Attack {i}.mp3 (space or no-space) not found!")
        except pygame.error as e:
            print('[Yori SFX] load error', e)
        self._walk_sound_playing = False
        
        # ── RIGID BODY SYSTEM ──
        collider_radius = 50  # Larger collider for boss
        center_x = self.rect.centerx
        center_y = self.rect.centery
        self.rigid_body = RigidBody(center_x, center_y, collider_radius, mass=2.0)
        
        # Boss physics settings
        self.rigid_body.gravity = 0.8
        self.rigid_body.friction = 0.9
        self.rigid_body.air_resistance = 0.98
        self.rigid_body.bounce = 0.02
        
        # Set ground level
        self.ground_y = self.rect.bottom
        
        # Add world_x position tracking (important for level transitions)
        self.world_x = self.rect.centerx
        
        print(f"Yori boss created at {pos} with {self.max_health} health!")

    def update_attack_point(self):
        """Update the attack point position based on Yori's direction during attack"""
        if self.state.startswith('attack'):
            # Position attack point in front of Yori based on facing direction
            offset_x = 150 if self.dir == 1 else -150
            offset_y = -20
            self.attack_point = (self.rect.centerx + offset_x, self.rect.centery + offset_y)
        else:
            # Default position when not attacking
            self.attack_point = (self.rect.centerx, self.rect.centery)

    def face_player(self):
        """Make Yori face the player"""
        if self.target:
            if self.target.rect.centerx > self.rect.centerx:
                self.dir = 1
                self.flip = False
            else:
                self.dir = -1
                self.flip = True

    def attack_player(self):
        """Attack the player if in range"""
        if self.target:
            player_center = (self.target.rect.centerx, self.target.rect.centery)
            distance = ((self.attack_point[0] - player_center[0])**2 + 
                       (self.attack_point[1] - player_center[1])**2)**0.5
            
            if distance <= self.attack_radius:
                print(f"Yori attacks player for {self.attack_damage} damage! Distance: {distance:.1f}")
                self.target.take_damage(self.attack_damage, self.ui_system)
            else:
                print(f"Yori attack missed! Player too far away. Distance: {distance:.1f}")

    def take_damage(self, damage, ui_system=None):
        """Take damage and show damage text"""
        if self.state == 'counter_wait':
            # Parry successful ��� immediately launch counter attack, ignore damage
            print("Yori parries the attack and counterattacks!")
            self.start_counter_attack()
            return

        if self.state != 'die':
            # Check if Yori can counter attack when health is low
            health_percentage = self.current_health / self.max_health
            if (health_percentage < self.low_health_threshold and 
                self.state in ['attack1', 'attack2', 'attack3'] and 
                random.random() < self.counter_attack_chance):
                # Yori counters the player's attack!
                print("Yori counters the player's attack!")
                self.start_counter_attack()
                return  # Don't take damage when countering
            
            self.current_health -= damage
            print(f"Yori took {damage} damage! Health: {self.current_health}/{self.max_health}")
            
            # Create damage text if UI system is provided
            if ui_system:
                ui_system.add_damage_text(self.rect.centerx, self.rect.centery - 200, damage, (255, 100, 100))
            
            # Check if health dropped below 55% for the first time
            if (health_percentage >= self.low_health_threshold and 
                self.current_health / self.max_health < self.low_health_threshold and 
                not self.low_health_dialog_shown):
                self.trigger_low_health_dialog()
            
            if self.current_health <= 0:
                self.current_health = 0
                self.state = 'die'
                self.frame = 0.0
                self.death_time = time.time()
                
                # Always face the player when dying
                if self.target:
                    # Update flip to face the player during death animation
                    self.flip = self.target.rect.centerx < self.rect.centerx
                    
                    # Signal that a cinematic death is happening
                    self.cinematic_death = True
                    print("CINEMATIC DEATH ACTIVATED - Camera should focus on Yori now!")
                    
                # Start death knockback animation
                self.is_death_knockback = True
                self.knockback_start_velocity = self.death_knockback_force
                # Knockback away from player
                if self.target:
                    knockback_dir = -1 if self.target.rect.centerx > self.rect.centerx else 1
                else:
                    knockback_dir = -self.dir
                self.rigid_body.velocity_x = knockback_dir * self.death_knockback_force
                
                print("Yori has been defeated with dramatic death knockback!")
    
    def stun(self):
        """Stun Yori boss - show hurt counter animation with delay"""
        if self.state != 'die':
            print("Yori has been countered! Showing hurt counter animation...")
            self.in_combo = False
            self.state = 'hurt_counter'
            self.frame = 0.0
            self.hurt_counter_time = time.time()
            self.next_action_time = time.time() + self.counter_delay + 2.0  # Counter delay + 2 second pause
            self.damage_dealt = True  # Prevent damage from current attack
            
            # Stop all movement
            self.rigid_body.velocity_x = 0
    
    def trigger_low_health_dialog(self):
        """Trigger dialog when Yori's health drops below 55%"""
        self.low_health_dialog_shown = True
        self.can_counter_attack = True  # Enable counter attacks
        print("Yori's health is below 55%! Triggering low health dialog and enabling advanced AI!")
        
        # Set a flag that main.py can check to trigger the dialog
        self.should_trigger_low_health_dialog = True
    
    def start_counter_wait(self):
        """Enter counter waiting stance (parry)"""
        if self.state != 'die':
            print("Yori enters counter stance!")
            self.state = 'counter_wait'
            self.frame = 0.0
            self.counter_wait_start_time = time.time()
            self.damage_dealt = True   # Prevent damage from interrupted attack
            # Stop all movement while waiting
            self.rigid_body.velocity_x = 0

    def start_counter_attack(self):
        """Start Yori's counter attack when health is below 55%"""
        if self.state != 'die':
            print("Yori performs a counter attack!")
            self.state = 'counter'
            self.frame = 0.0
            self.counter_attack_time = time.time()
            # record starting X for lunge motion
            self._counter_start_x = self.rect.centerx
            self.next_action_time = time.time() + self.counter_attack_duration
            self.damage_dealt = False
            # Play counter sound effect
            if self.sfx_counter:
                self.sfx_counter.play()
            
            # Stop all movement during counter attack
            self.rigid_body.velocity_x = 0
            
            # Face the player for counter attack
            if self.target:
                if self.target.rect.centerx > self.rect.centerx:
                    self.dir = 1
                    self.flip = False
                else:
                    self.dir = -1
                    self.flip = True
    
    def start_skill_attack(self):
        """Start Yori's skill attack when health is below 55%"""
        if self.state != 'die' and self.skill_cooldown <= 0:
            print("Yori uses his special skill attack!")
            self.state = 'skill'
            self.frame = 0.0
            self.skill_time = time.time()
            self.next_action_time = time.time() + self.skill_duration
            self.damage_dealt = False
            self.skill_cooldown = self.skill_cooldown_duration  # Start cooldown
            
            # Play skill sound effect
            if self.sfx_skill:
                self.sfx_skill.play()
            
            # Stop walking sound if playing
            if self._walk_sound_playing and self.sfx_walk:
                self.sfx_walk.stop()
                self._walk_sound_playing = False
                
            # Stop all movement during skill
            self.rigid_body.velocity_x = 0
            
            # Face the player for skill attack
            if self.target:
                if self.target.rect.centerx > self.rect.centerx:
                    self.dir = 1
                    self.flip = False
                else:
                    self.dir = -1
                    self.flip = True

    def start_block_animation(self):
        """Start the cinematic block animation when counter-attacked"""
        if self.state != 'die':
            print("Yori blocks the counter attack with cinematic animation!")
            self.state = 'block'
            self.frame = 0.0
            self.block_time = time.time()
            # Reduced pause time so Yori gets back to action faster
            self.next_action_time = time.time() + self.block_duration + 0.3  # Block duration + short pause
            
            # Set up smooth knockback animation
            knockback_force = 20.0  # Change this value to increase/decrease knockback distance
            self.knockback_start_velocity = knockback_force
            self.is_in_knockback = True
            self.rigid_body.velocity_x = -self.dir * knockback_force

    def start_dash_back(self):
        """Start dashing back from the player"""
        if self.target:
            # Calculate dash direction (away from player)
            if self.target.rect.centerx > self.rect.centerx:
                # Player is to the right, dash left
                self.dash_target_x = self.rect.centerx - DASH_DISTANCE
                self.dir = -1
            else:
                # Player is to the left, dash right
                self.dash_target_x = self.rect.centerx + DASH_DISTANCE
                self.dir = 1
            
            self.state = 'dash'
            if self.sfx_dash:
                self.sfx_dash.play()
            self.frame = 0.0
            self.is_dashing = True
            self.flip = (self.dir < 0)
            
    def start_dash_to_player(self):
        """Start dashing toward the player - used when player gets behind Yori"""
        if self.target:
            # Calculate dash direction (toward player)
            if self.target.rect.centerx > self.rect.centerx:
                # Player is to the right, dash right
                self.dash_target_x = self.target.rect.centerx - 100  # Stop 100px before player
                self.dir = 1
            else:
                # Player is to the left, dash left
                self.dash_target_x = self.target.rect.centerx + 100  # Stop 100px before player
                self.dir = -1
            
            self.state = 'dash'
            self.frame = 0.0
            self.is_dashing = True
            self.flip = (self.dir < 0)
            print("Yori is dashing toward player!")

    def ease_in_out(self, t):
        """Smooth easing function for animations"""
        return t * t * (3.0 - 2.0 * t)
    
    def animate(self, seq, speed=0.2):
        """Advance through the given animation sequence"""
        if not seq:  # Safety check for empty sequences
            return
            
        self.frame = (self.frame + speed) % len(seq)
        img = seq[int(self.frame)]
        if self.flip:
            img = pygame.transform.flip(img, True, False)
        
        # Update image & keep bottom alignment
        self.image = img
        self.rect = img.get_rect(midbottom=self.rect.midbottom)

    def alive(self):
        """Check if Yori is still alive"""
        return self.current_health > 0

    def update(self):
        now = time.time()
        
        # Check if Yori is active (only in level 5)
        is_active = hasattr(self, 'is_active') and self.is_active
        
        # Update skill cooldown
        if self.skill_cooldown > 0:
            self.skill_cooldown -= 1/60.0  # Assuming 60 FPS
            
        # Check if Yori should use skill after dialog
        if self.should_use_skill and self.skill_cooldown <= 0:
            self.should_use_skill = False
            self.start_skill_attack()
        
        # ── PHYSICS UPDATE ──
        self.rigid_body.update_physics(dt=1.0)
        
        # Check ground collision with rigid body only if ground_y is set
        if self.ground_y is not None:
            self.rigid_body.check_ground_collision(self.ground_y)
            
            # IMPORTANT: Fix for level transitions - ensure Yori stays on the ground
            # If we're supposed to be on the ground, force the position
            if self.rigid_body.is_grounded:
                # Ensure Yori's bottom position matches ground_y exactly
                self.rect.bottom = self.ground_y
                # Update rigid body position to match sprite position
                self.rigid_body.set_position(self.rect.centerx, self.rect.centery)
                # Reset vertical velocity to prevent accumulating falling momentum
                self.rigid_body.velocity_y = 0
                
            # Track ground_y changes
            if not hasattr(self, '_prev_ground_y'):
                self._prev_ground_y = self.ground_y
            self._prev_ground_y = self.ground_y
        else:
            # If no ground is detected, make sure is_grounded is False to allow falling
            self.rigid_body.is_grounded = False
            
        # Debug output for monitoring Yori's ground state (once per second)
        if hasattr(self, '_last_debug_time') and now - self._last_debug_time < 1.0:
            pass  # Skip debug if less than 1 second has passed
        else:
            self._last_debug_time = now
            """ print(f"DEBUG - Yori update: pos: ({self.rect.centerx}, {self.rect.bottom}), grounded: {self.rigid_body.is_grounded}, ground_y: {self.ground_y}") """
            if hasattr(self, '_prev_ground_y'):
                self._prev_ground_y = None
        
        # Get the new position from rigid body and update sprite
        new_center_x, new_center_y = self.rigid_body.get_position()
        self.rect.centerx = int(new_center_x)
        self.rect.centery = int(new_center_y)  # Adjust visual position
        
        # Keep world_x synced to rect.centerx for level transitions
        self.world_x = self.rect.centerx
        
        # Update attack point position
        self.update_attack_point()
        
        # Don't do anything if dead, except handle death animation
        if not self.alive() and self.state != 'die':
            return
            
        # *** IMPORTANT: If Yori is not active, don't process AI logic ***
        if not is_active:
            # Stay in idle state but don't move
            self.state = 'idle'
            self.animate(self.idle, speed=0.15)
            return
        
        # Calculate distance to player (only when active)
        if self.target:
            dist = abs(self.target.rect.centerx - self.rect.centerx)
        else:
            dist = 1e6
        
        # ── YORI BOSS AI STATE MACHINE ──
        
        if self.state == 'idle':
            # Always face the player when idle
            self.face_player()
            
            # Animate idle
            self.animate(self.idle, speed=0.15)
            
            # If enough time has passed, decide next action
            if now >= self.next_action_time:
                # Check health percentage for skill priority
                health_percentage = self.current_health / self.max_health
                
                # When health is below 55%, prioritize skill attack if cooldown is ready
                if (health_percentage < self.low_health_threshold and 
                    self.skill_cooldown <= 0 and 
                    dist <= ATTACK_STOP_DIST):  # Must be near player to hit with skill
                    print("Yori uses skill attack as priority (health < 55%)")
                    self.start_skill_attack()
                elif dist <= ATTACK_STOP_DIST:
                    # Stop walk loop if still playing
                    if self._walk_sound_playing and self.sfx_walk:
                        self.sfx_walk.stop(); self._walk_sound_playing = False
                    # Close enough to attack – start 3-attack combo
                    self.attack_combo_count = 0  # Reset combo
                    self.in_combo = True
                    self.state = 'attack1'
                    if self.sfx_attack.get(1):
                        self.sfx_attack[1].play()
                    self.frame = 0.0
                    self.damage_dealt = False
                    print("Yori starts 3-attack combo!")
                else:
                    # Too far – walk towards player
                    self.state = 'walking'
                    self.frame = 0.0
                    print("Yori walks towards player!")
        
        elif self.state == 'walking':
            # Always face the player when walking
            self.face_player()
            
            # Animate walking at same speed as player
            self.animate(self.walking, speed=0.8)
            
            # Move towards player
            self.rigid_body.velocity_x = self.dir * WALK_SPEED
            # play walk loop
            if self.sfx_walk and not self._walk_sound_playing:
                self.sfx_walk.play(loops=-1)
                self._walk_sound_playing = True
            
            # Check health percentage for skill priority while walking
            health_percentage = self.current_health / self.max_health
            if (health_percentage < self.low_health_threshold and 
                self.skill_cooldown <= 0 and 
                dist <= ATTACK_STOP_DIST):
                # Stop walking and use skill immediately
                self.rigid_body.velocity_x = 0
                if self._walk_sound_playing and self.sfx_walk:
                    self.sfx_walk.stop()
                    self._walk_sound_playing = False
                print("Yori stops walking to use skill attack (health < 55%)")
                self.start_skill_attack()
            elif dist <= ATTACK_STOP_DIST:
                # Close enough - start attack combo
                self.rigid_body.velocity_x = 0  # Stop moving

                # Stop walking sound if it's still playing so attack SFX is audible
                if self._walk_sound_playing and self.sfx_walk:
                    self.sfx_walk.stop()
                    self._walk_sound_playing = False

                self.attack_combo_count = 0  # Reset combo
                self.in_combo = True
                self.state = 'attack1'
                if self.sfx_attack.get(1):
                    self.sfx_attack[1].play()
                self.frame = 0.0
                self.damage_dealt = False
                print("Yori reached player - starting attack combo!")
        
        elif self.state == 'attack1':
            # Stop moving during attack
            self.rigid_body.velocity_x = 0

            # Check if player is attacking – attempt perfect counter
            if (self.target and isinstance(self.target.state, int)):
                # Player attack detected – switch to counter stance
                self.start_counter_wait()
                return
            
            # Check if player moved too far away - reset combo
            if dist > ATTACK_STOP_DIST:
                print("Player moved away - resetting Yori combo!")
                self.in_combo = False
                self.state = 'idle'
                self.frame = 0.0
                self.next_action_time = now + 0.5  # Brief pause before next action
                return
            
            # Play attack1 animation
            self.animate(self.attack1, speed=0.4)  # ⚔️ ATTACK 1 SPEED - Change 0.25 to make faster/slower
            
            # Deal damage at specific frame
            if not self.damage_dealt and self.frame >= len(self.attack1) * self.damage_frame:
                self.attack_player()
                self.damage_dealt = True
            
            # When attack animation finishes
            if self.frame >= len(self.attack1) - 1:
                # Check if player is behind Yori
                is_player_behind = (self.target.rect.centerx > self.rect.centerx and self.flip) or \
                                   (self.target.rect.centerx < self.rect.centerx and not self.flip)
                
                if is_player_behind:
                    # Player moved behind Yori during attack - dash to reposition
                    self.start_dash_to_player()
                    self.frame = 0.0
                    self.damage_dealt = False
                    self.in_combo = False  # Reset combo after repositioning
                    print("Player behind Yori! Repositioning...")
                else:
                    # Continue with normal combo
                    self.attack_combo_count = 1
                    self.state = 'attack2'
                    if self.sfx_attack.get(2):
                        self.sfx_attack[2].play()
                    self.frame = 0.0
                    self.damage_dealt = False
                    self.next_action_time = now + ATTACK_DELAY
                    print("Yori combo: Attack 1 → Attack 2")
        
        elif self.state == 'attack2':
            # Stop moving during attack
            self.rigid_body.velocity_x = 0

            # Check if player is attacking – attempt perfect counter
            if (self.target and isinstance(self.target.state, int)):
                self.start_counter_wait()
                return
            
            # Check if player moved too far away - reset combo
            if dist > ATTACK_STOP_DIST:
                print("Player moved away - resetting Yori combo!")
                self.in_combo = False
                self.state = 'idle'
                self.frame = 0.0
                self.next_action_time = now + 0.5  # Brief pause before next action
                return
            
            # Small delay between attacks
            if now < self.next_action_time:
                self.animate(self.idle, speed=0.1)  # Brief idle between attacks
                return
            
            # Play attack2 animation
            self.animate(self.attack2, speed=0.4)  # ⚔️ ATTACK 2 SPEED - Change 0.25 to make faster/slower
            
            # Deal damage at specific frame
            if not self.damage_dealt and self.frame >= len(self.attack2) * self.damage_frame:
                self.attack_player()
                self.damage_dealt = True
            
            # When attack animation finishes
            if self.frame >= len(self.attack2) - 1:
                # Check if player is behind Yori
                is_player_behind = (self.target.rect.centerx > self.rect.centerx and self.flip) or \
                                   (self.target.rect.centerx < self.rect.centerx and not self.flip)
                
                if is_player_behind:
                    # Player moved behind Yori during attack - dash to reposition
                    self.start_dash_to_player()
                    self.frame = 0.0
                    self.damage_dealt = False
                    self.in_combo = False  # Reset combo after repositioning
                    print("Player behind Yori! Repositioning...")
                else:
                    # Continue with normal combo
                    self.attack_combo_count = 2
                    self.state = 'attack3'
                    if self.sfx_attack.get(3):
                        self.sfx_attack[3].play()
                    self.frame = 0.0
                    self.damage_dealt = False
                    self.next_action_time = now + ATTACK_DELAY
                    print("Yori combo: Attack 2 → Attack 3")
        
        elif self.state == 'attack3':
            # Stop moving during attack
            self.rigid_body.velocity_x = 0

            # Check if player is attacking – attempt perfect counter
            if (self.target and isinstance(self.target.state, int)):
                self.start_counter_wait()
                return
            
            # Check if player moved too far away - reset combo
            if dist > ATTACK_STOP_DIST:
                print("Player moved away - resetting Yori combo!")
                self.in_combo = False
                self.state = 'idle'
                self.frame = 0.0
                self.next_action_time = now + 0.5  # Brief pause before next action
                return
            
            # Small delay between attacks
            if now < self.next_action_time:
                self.animate(self.idle, speed=0.1)  # Brief idle between attacks
                return
            
            # Play attack3 animation
            self.animate(self.attack3, speed=0.4)  # ⚔️ ATTACK 3 SPEED - Change 0.25 to make faster/slower
            
            # Deal damage at specific frame
            if not self.damage_dealt and self.frame >= len(self.attack3) * self.damage_frame:
                self.attack_player()
                self.damage_dealt = True
            
            # When attack animation finishes
            if self.frame >= len(self.attack3) - 1:
                # Check if player is behind Yori
                is_player_behind = (self.target.rect.centerx > self.rect.centerx and self.flip) or \
                                   (self.target.rect.centerx < self.rect.centerx and not self.flip)
                
                if is_player_behind:
                    # Player moved behind Yori during attack - dash to reposition
                    self.start_dash_to_player()
                    self.frame = 0.0
                    self.damage_dealt = False
                    self.in_combo = False  # Reset combo after repositioning
                    print("Player behind Yori! Repositioning...")
                else:
                    # Combo finished normally - dash back
                    self.in_combo = False
                    self.start_dash_back()
                    print("Yori combo finished - dashing back!")
        
        elif self.state == 'dash':
            # Play dash animation
            self.animate(self.dash, speed=0.3)
            if self._walk_sound_playing and self.sfx_walk:
                self.sfx_walk.stop(); self._walk_sound_playing=False
            
            # Move towards dash target
            if self.is_dashing:
                current_x = self.rect.centerx
                distance_to_target = abs(self.dash_target_x - current_x)
                
                if distance_to_target > 10:  # Still dashing
                    # Move towards dash target
                    dash_direction = 1 if self.dash_target_x > current_x else -1
                    self.rigid_body.velocity_x = dash_direction * DASH_SPEED
                else:
                    # Reached dash target
                    self.rigid_body.velocity_x = 0
                    self.is_dashing = False
                    # NO DELAY - go straight back to action
                    self.next_action_time = now  # Ready immediately
                    
                    # Check distance and go straight to appropriate action
                    if dist <= ATTACK_STOP_DIST:
                        # Close enough - start new attack combo immediately
                        self.attack_combo_count = 0
                        self.in_combo = True
                        self.state = 'attack1'
                        self.frame = 0.0
                        self.damage_dealt = False
                        print("Yori finished dash - starting new combo immediately!")
                    else:
                        # Too far - start walking immediately
                        self.state = 'walking'
                        self.frame = 0.0
                        print("Yori finished dash - walking to player immediately!")
        
        elif self.state == 'counter_wait':
            # Hold parry stance
            self.rigid_body.velocity_x = 0
            # Play counter_wait once then hold on final frame (no looping)
            if self.frame < len(self.counter_wait) - 1:
                self.frame += 0.25  # animation speed
                if self.frame >= len(self.counter_wait):
                    self.frame = len(self.counter_wait) - 1
            img = self.counter_wait[int(self.frame)]
            if self.flip:
                img = pygame.transform.flip(img, True, False)
            self.image = img
            self.rect = img.get_rect(midbottom=self.rect.midbottom)
            # If player hasn't attacked in time, resume combat
            if now >= self.counter_wait_start_time + self.counter_wait_duration:
                print("Counter window expired - Yori resumes attack!")
                self.state = 'idle'
                self.frame = 0.0
                self.next_action_time = now + 0.5

        elif self.state == 'hurt_counter':
            # Stop all movement during hurt counter
            self.rigid_body.velocity_x = 0
            
            # Play hurt counter animation
            self.animate(self.hurt_counter, speed=0.15)
            
            # Check if counter delay has passed
            if now >= self.hurt_counter_time + self.counter_delay:
                print("Hurt counter delay finished - player can now counter attack!")
                # Stay in hurt_counter state until player attacks or timeout
                if now >= self.next_action_time:
                    # Timeout - return to idle
                    print("Counter window expired - Yori returns to combat!")
                    self.state = 'idle'
                    self.frame = 0.0
                    self.next_action_time = now + 0.5
        
        elif self.state == 'block':
            # Handle smooth knockback animation
            if self.is_in_knockback:
                # Calculate knockback progress (0 to 1)
                knockback_progress = (now - self.block_time) / self.knockback_duration
                
                if knockback_progress >= 1.0:
                    # Knockback finished
                    self.is_in_knockback = False
                    self.rigid_body.velocity_x = 0
                else:
                    # Linear ease out - gradually reduce velocity
                    remaining_force = self.knockback_start_velocity * (1.0 - knockback_progress)
                    self.rigid_body.velocity_x = -self.dir * remaining_force
            
            # Play block animation with cinematic feel
            self.animate(self.block, speed=0.12)  # Slower for cinematic effect
            
            # Check if block animation should end
            if now >= self.block_time + self.block_duration:
                print("Block animation finished - Yori returns to combat!")
                self.is_in_knockback = False
                self.rigid_body.velocity_x = 0
                
                # Instead of going to idle, immediately decide next action based on distance
                if dist <= ATTACK_STOP_DIST:
                    # Close enough - start attacking immediately
                    self.attack_combo_count = 0
                    self.in_combo = True
                    self.state = 'attack1'
                    self.frame = 0.0
                    self.damage_dealt = False
                    self.next_action_time = now  # No delay
                    print("Block finished - Yori immediately starts attacking!")
                else:
                    # Too far - start walking immediately
                    self.state = 'walking'
                    self.frame = 0.0
                    self.next_action_time = now  # No delay
                    print("Block finished - Yori immediately starts walking to player!")
        
        elif self.state == 'counter':
            # Stop all movement during counter attack
            self.rigid_body.velocity_x = 0

            # ── Counter-attack animation (no looping) ──
            if self.frame < len(self.counter) - 1:
                self.frame += 0.35  # animation speed
            if self.frame >= len(self.counter):
                self.frame = len(self.counter) - 1  # clamp to last frame

            # Forward lunge begins from frame index 3 (4th image)
            frame_idx = int(self.frame)
            if frame_idx >= 3:
                # t from 0->1 across remaining frames
                t = (self.frame - 3) / max(1, (len(self.counter) - 4))
                t = max(0.0, min(1.0, t))
                eased = self.ease_in_out(t)
                offset = eased * self.counter_attack_lunge * self.dir
                new_x = self._counter_start_x + offset
                dx = new_x - self.rect.centerx
                # move sprite & physics body
                self.rect.centerx = int(new_x)
                rb_x, rb_y = self.rigid_body.get_position()
                self.rigid_body.set_position(rb_x + dx, rb_y)

            # Draw current frame
            img = self.counter[int(self.frame)]
            if self.flip:
                img = pygame.transform.flip(img, True, False)
            self.image = img
            self.rect = img.get_rect(midbottom=self.rect.midbottom)

            # Deal damage & knockback when 60% of animation reached
            if (not self.damage_dealt) and self.frame >= len(self.counter) * 0.6:
                self.attack_player()
                self.damage_dealt = True
                print("Yori's counter attack hits!")
                # Apply knockback to player
                if self.target and hasattr(self.target, 'rigid_body'):
                    knock_dir = 1 if self.target.rect.centerx > self.rect.centerx else -1
                    # horizontal knockback only (no vertical)
                    # Keep knock-back speed moderate (20) but increase duration so the
                    # player travels farther without feeling unnaturally fast.
                    self.target.rigid_body.velocity_x = knock_dir * 50
                    # Notify player script of knockback duration (0.6s)
                    try:
                        # Longer knock-back window ⇒ more distance at same speed
                        self.target.knockback_end_time = pygame.time.get_ticks() + 1000
                    except Exception:
                        pass
                    # force player into block pose during knockback
                    try:
                        # Switch player into block pose for knockback ONLY if still alive
                        if self.target.current_health > 0:
                            self.target.blocking = True
                            # Play full block-enter animation for better transition
                            self.target.block_animation_state = 'entering'
                            self.target.state = 'block'
                            self.target.frame = 0.0
                            import time as _t
                            self.target.auto_unblock_time = _t.time() + 0.5
                    except Exception:
                        pass

            # Finish when animation ends – immediately resume combat (no long delay)
            if self.frame >= len(self.counter) - 1:
                print("Counter attack finished - Yori returns to combat!")
                # Return to appropriate state based on distance
                if dist <= ATTACK_STOP_DIST:
                    self.state = 'idle'
                    self.next_action_time = now + 0.2  # very short pause
                else:
                    self.state = 'walking'
                    self.frame = 0.0
                # Reset any hold timer that might exist
                if hasattr(self, '_counter_hold_start'):
                    delattr(self, '_counter_hold_start')
        
        elif self.state == 'skill':
            # Stop all movement during skill
            self.rigid_body.velocity_x = 0
            
            # Play skill animation ONCE (no looping)
            if self.frame < len(self.skill) - 1:
                self.frame += 0.25  # Animation speed
            if self.frame >= len(self.skill):
                self.frame = len(self.skill) - 1  # Clamp to last frame
            img = self.skill[int(self.frame)]
            if self.flip:
                img = pygame.transform.flip(img, True, False)
            self.image = img
            self.rect = img.get_rect(midbottom=self.rect.midbottom)
            
            # Deal damage once at ~70% of the animation using an enlarged radius
            if (not self.damage_dealt and 
                self.frame >= len(self.skill) * 0.7):
                # Temporarily boost damage & radius for skill
                original_damage = self.attack_damage
                original_radius = self.attack_radius
                self.attack_damage = self.skill_damage
                self.attack_radius = getattr(self, 'skill_attack_radius', 250)
                self.attack_player()
                # Restore original values
                self.attack_damage = original_damage
                self.attack_radius = original_radius
                self.damage_dealt = True
                print("Yori's skill attack hits with devastating power!")
            
            # Check if skill animation finished
            if now >= self.skill_time + self.skill_duration:
                print("Skill attack finished - Yori returns to combat!")
                # Return to appropriate state based on distance
                if dist <= ATTACK_STOP_DIST:
                    self.state = 'idle'
                    self.next_action_time = now + 0.5  # Brief pause
                else:
                    self.state = 'walking'
                    self.frame = 0.0

        elif self.state == 'die':
            # Handle death knockback animation
            if self.is_death_knockback:
                # Calculate death knockback progress (0 to 1)
                death_progress = (now - self.death_time) / self.death_knockback_duration
                
                if death_progress >= 1.0:
                    # Death knockback finished
                    self.is_death_knockback = False
                    self.rigid_body.velocity_x = 0
                else:
                    # Linear ease out - gradually reduce death knockback velocity
                    remaining_force = self.knockback_start_velocity * (1.0 - death_progress)
                    knockback_dir = 1 if self.rigid_body.velocity_x > 0 else -1
                    self.rigid_body.velocity_x = knockback_dir * remaining_force
            
            # Play death animation (don't loop it) with slow-motion effect
            if self.death:
                # Calculate how much time has passed since death
                current_time = time.time()
                time_since_death = current_time - self.death_time
                
                # Super slow animation progression - map all frames to 6 seconds duration
                total_frames = len(self.death)
                cinematic_duration = 1.0  # Fixed 6 second duration for death animation
                
                if time_since_death < cinematic_duration:
                    # Calculate which frame to show based on elapsed time
                    progress_ratio = time_since_death / cinematic_duration
                    self.frame = progress_ratio * (total_frames - 1)
                    
                    # Debug info commented out
                    # print(f"DEATH ANIMATION: Frame {self.frame:.1f}/{total_frames-1} - Time: {time_since_death:.1f}s/{cinematic_duration}s")
                else:
                    # Stay on last frame after animation completes
                    self.frame = len(self.death) - 1
                    # print(f"DEATH ANIMATION COMPLETE - Holding on last frame")
                
                img = self.death[int(self.frame)]
                if self.flip:
                    img = pygame.transform.flip(img, True, False)
                self.image = img
                self.rect = img.get_rect(midbottom=self.rect.midbottom)
            else:
                print("ERROR: No death animation available! Using hurt_counter as fallback")
                # Fallback to hurt_counter if death animation not available
                self.animate(self.hurt_counter, speed=0.1)

    def draw_health_bar(self, screen, camera_x, camera_y):
        """Draw Yori's health bar at the bottom center of the screen (Dark Souls style)"""
        # ALWAYS show health bar, even when dead
        
        # Health bar dimensions and position (bigger and at bottom)
        bar_width = 600  # Bigger width
        bar_height = 30  # Bigger height
        bar_x = (screen.get_width() - bar_width) // 2
        bar_y = screen.get_height() - 80  # Near bottom of screen
        
        # Background bar (very dark red)
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (30, 0, 0), bg_rect)  # Even darker red background
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 3)  # Thicker white border
        
        # Health bar (red or very dark red if dead)
        if self.alive():
            # Alive - show normal health
            health_percentage = self.current_health / self.max_health
            health_width = int(bar_width * health_percentage)
            if health_width > 0:
                health_rect = pygame.Rect(bar_x, bar_y, health_width, bar_height)
                pygame.draw.rect(screen, (180, 0, 0), health_rect)  # Normal red for health
        else:
            # Dead - show full bar in very dark red to indicate death
            health_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            pygame.draw.rect(screen, (60, 0, 0), health_rect)  # Very dark red for death
            
    def check_tile_collision_below(self, tile_rects):
        """Check if there's a solid tile below Yori for ground detection"""
        # Create a wider rectangle below Yori's feet - much wider to prevent falling at level transitions
        check_rect = pygame.Rect(
            self.rect.centerx - 60,  # Much wider rectangle centered on Yori
            self.rect.bottom,        # Start at Yori's feet
            120,                     # Extra wide to handle level transitions
            32                       # Check for ground up to 32px below (half tile)
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
                self.rect.centerx - 150,  # Very wide check for better level transitions
                self.rect.bottom,         # Start at Yori's feet
                300,                      # Extra wide to ensure level transitions work
                64                        # Check a full tile height down
            )
            
            for tile_rect in tile_rects:
                if transition_check_rect.colliderect(tile_rect):
                    # Use the highest ground found
                    if found_ground is None or tile_rect.top < found_ground:
                        found_ground = tile_rect.top
        
        # Store previous ground for reference
        if not hasattr(self, '_prev_found_ground'):
            self._prev_found_ground = found_ground
        self._prev_found_ground = found_ground
        
        # Return the highest ground found or None
        return found_ground