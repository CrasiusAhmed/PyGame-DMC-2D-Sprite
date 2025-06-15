import pygame, os, random, time
from rigidbody import RigidBody

# ── constant paths & sizes ──
IMG_DIR      = os.path.join(os.path.dirname(__file__), 'img')
ENEMY_SIZE   = (600, 600)  # scale all enemy frames to 600×600 px

# ── tweakable gameplay values ──
WALK_SPEED       = 2          # enemy moves 2 px per frame when walking/approaching
IDLE_MIN_SEC     = 2          # after idle, wait at least 2 seconds
IDLE_MAX_SEC     = 5          # at most 5 seconds
WALK_DIST        = 100        # patrol distance in px, e.g. walk 100 px before idling
DETECT_RANGE     = 500        # if player is within 800 px, enemy spots them
ATTACK_STOP_DIST = 130        # stop approaching when within 130 px of player
RECOVER_MIN_SEC  = 2          # back-off pause at least 2 seconds after attack
RECOVER_MAX_SEC  = 3          # at most 3 seconds back-off

# ── helper to load & scale all frames in a folder ──
def load_frames(folder):
    path = os.path.join(IMG_DIR, folder)
    files = sorted(os.listdir(path), key=lambda x: int(x.split('.')[0]))
    return [
        pygame.transform.scale(
            pygame.image.load(os.path.join(path, f)).convert_alpha(),
            ENEMY_SIZE
        )
        for f in files
    ]

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        # load animations: idle, walk, attack
        self.idle   = load_frames('Enemy 1/Idle')
        self.walk   = load_frames('Enemy 1/Walking')
        self.attack = load_frames('Enemy 1/Attack')
        self.hurt   = load_frames('Enemy 1/Hurt')
        self.die    = load_frames('Enemy 1/Death')
        self.stun_frames = load_frames('Enemy 1/Stun')

        # initial animation state
        self.state = 'idle'
        self.frame = 0.0

        # health attributes
        self.max_health = 100
        self.current_health = self.max_health

        # choose random initial patrol direction
        self.dir  = random.choice([-1, 1])   # -1 = left, +1 = right
        self.flip = (self.dir < 0)           # flip image if facing left

        # set starting image & position
        self.image = self.idle[0]
        self.rect  = self.image.get_rect(midbottom=pos)
        # e.g. if pos=(426,670), rect.midbottom=(426,670)

        # timers & trackers for idle/patrol
        self.next_idle   = time.time() + random.uniform(IDLE_MIN_SEC, IDLE_MAX_SEC)
        # e.g. now=1000.0 → next_idle=1000+3.5=1003.5
        self.patrol_dist = 0     # how far we've patrolled so far
        self.patrol_tgt  = 0     # how far we want to patrol this cycle

        # stun timer for counter mechanic
        self.stun_timer = 0      # How long to remain stunned

        # recovery (back-off) timer
        self.recover_end = 0     # timestamp when back-off ends

        # will be set by main.py so enemy knows who the player is
        self.target = None

        # attack attributes
        self.attack_damage = 50
        
        # attack point attributes (similar to player)
        self.attack_point = (self.rect.centerx, self.rect.centery)
        self.attack_radius = 80  # Enemy has larger attack radius

        # attack timing control
        self.damage_dealt = False  # Track if damage was dealt in current attack
        self.damage_frame = 0.7  # Deal damage when animation is 70% complete
        # Add a property to help with debugging
                
        # stun system
        self.stunned = False
        self.stun_end_time = 0
        
        # UI system reference (will be set by main.py)
        self.ui_system = None
        
        # ── RIGID BODY SYSTEM ──
        # Create a circular rigid body collider for the enemy
        # Position it at the enemy's center, with a radius appropriate for the enemy size
        collider_radius = 40  # Slightly larger than player since enemy is bigger
        center_x = self.rect.centerx + 0   # +10 = move right, -10 = move left
        center_y = self.rect.centery + 0   # +10 = move down, -10 = move up
        self.rigid_body = RigidBody(center_x, center_y, collider_radius, mass=1.5)
        
        # Enemy physics settings (can be different from player)
        self.rigid_body.gravity = 0.8
        self.rigid_body.friction = 0.85  # Slightly less friction for different feel
        self.rigid_body.air_resistance = 0.98
        self.rigid_body.bounce = 0.05  # Less bouncy than player
        
        # Set ground level for enemy (same as sprite bottom initially)
        self.ground_y = self.rect.bottom
        
        # Add world_x position tracking (important for level transitions)
        self.world_x = self.rect.centerx


    def update_attack_point(self):
        """Update the attack point position based on enemy direction during attack"""
        if self.state == 'attack':
            # Position attack point in front of enemy based on facing direction
            offset_x = 120 if self.dir == 1 else -120  # Adjust distance as needed
            offset_y = -10  # Slightly above center
            self.attack_point = (self.rect.centerx + offset_x, self.rect.centery + offset_y)
        else:
            # Default position when not attacking
            self.attack_point = (self.rect.centerx, self.rect.centery)

    def attack_player(self, ui_system=None):
        if self.target:
            print(f"Enemy attacks player for {self.attack_damage} damage!")
            # Calculate distance between enemy attack point and player center
            player_center = (self.target.rect.centerx, self.target.rect.centery)
            distance = ((self.attack_point[0] - player_center[0])**2 + 
                       (self.attack_point[1] - player_center[1])**2)**0.5
            
            # Only deal damage if player is within attack radius
            if distance <= self.attack_radius:
                print(f"Enemy attacks player for {self.attack_damage} damage! Distance: {distance:.1f}")
                self.target.take_damage(self.attack_damage, ui_system)
            else:
                print(f"Enemy attack missed! Player too far away. Distance: {distance:.1f}")
            


    def take_damage(self, damage, ui_system=None):
        if self.state not in ('hurt', 'die', 'stun', 'stun'):
            self.current_health -= damage
            print(f"Enemy took {damage} damage! Health: {self.current_health}/{self.max_health}")
            
            # Create damage text if UI system is provided
            if ui_system:
                ui_system.add_damage_text(self.rect.centerx, self.rect.centery - 150, damage, (255, 255, 50))
            
            if self.current_health <= 0:
                self.state = 'die'
                self.frame = 0.0
            else:
                self.state = 'hurt'
                self.frame = 0.0
    
    def stun(self):
        """Stun the enemy for 1 second"""
        if self.state not in ('die',):  # Can't stun if dead
            print("Enemy stunned!")
            self.stunned = True
            self.state = 'stun'
            self.frame = 0.0
            self.stun_end_time = time.time() + 1.0  # Stun for 1 second
            
            # Stop all movement
            self.rigid_body.velocity_x = 0
            
            # Reset damage dealt flag to prevent damage during stun
            self.damage_dealt = True

    def animate(self, seq, speed=0.2):
        """
        Advance through the given animation sequence `seq` at `speed` frames per update.
        """
        self.frame = (self.frame + speed) % len(seq)
        img = seq[int(self.frame)]
        if self.flip:
            img = pygame.transform.flip(img, True, False)
        # update image & keep bottom alignment
        self.image = img
        self.rect  = img.get_rect(midbottom=self.rect.midbottom)

    def update(self):
        now = time.time()
        
        # ── PHYSICS UPDATE ──
        # Update physics simulation first
        self.rigid_body.update_physics(dt=1.0)
        
        # Check ground collision with rigid body only if ground_y is set
        if self.ground_y is not None:
            self.rigid_body.check_ground_collision(self.ground_y)
            # Track ground_y changes
            if not hasattr(self, '_prev_ground_y'):
                self._prev_ground_y = self.ground_y
            self._prev_ground_y = self.ground_y
        else:
            # If no ground is detected, make sure is_grounded is False to allow falling
            self.rigid_body.is_grounded = False
            if hasattr(self, '_prev_ground_y'):
                self._prev_ground_y = None
        
        # Get the new position from rigid body and update sprite
        new_center_x, new_center_y = self.rigid_body.get_position()
        self.rect.centerx = int(new_center_x)
        self.rect.centery = int(new_center_y - 30)  # Move visual sprite UP by 30px
        
        # Update attack point position
        self.update_attack_point()

        if self.state == 'hurt':
            self.animate(self.hurt, speed=0.3)
            if self.frame >= len(self.hurt) - 1:
                self.state = 'idle'
                self.frame = 0.0
            return
        
        if self.state == 'stun':
            # Play stun animation and check if stun time is over
            self.animate(self.stun_frames, speed=0.2)
            
            # Update stun timer
            self.stun_timer -= 1/60.0  # Assuming 60 FPS
            
            # Check if stun is over
            if self.stun_timer <= 0:
                print("Enemy stun ended")
                self.state = 'idle'
                self.frame = 0.0
                self.damage_dealt = False  # Reset damage dealt flag
            
            # No movement during stun
            self.rigid_body.velocity_x = 0
            return

        if self.state == 'die':
            self.animate(self.die, speed=0.3)
            if self.frame >= len(self.die) - 1:
                self.kill()  # Remove the enemy from the game
            return
        elif self.state == 'attack':
            # Stop moving during attack
            self.rigid_body.velocity_x = 0
            # play attack animation once
            self.animate(self.attack, speed=0.3)

            # Deal damage when animation reaches the damage frame
            if not self.damage_dealt and self.frame >= len(self.attack) * self.damage_frame:
                                
                self.attack_player(self.ui_system)
                self.damage_dealt = True

            # when last frame reached:
            if self.frame >= len(self.attack) - 1:
                # self.attack_player()  # Attack the player
                # start recovery/back-off
                self.state = 'recover'
                self.frame = 0.0
                self.recover_end = now + random.uniform(RECOVER_MIN_SEC, RECOVER_MAX_SEC)
                # reverse direction to back away
                self.dir = -self.dir
                self.damage_dealt = False  # Reset for next attack
            return  # skip default animate so attack plays cleanly




        # calculate horizontal distance to player (if set), else a large number
        if self.target:
            dist = abs(self.target.rect.centerx - self.rect.centerx)
            # e.g. player at x=640, enemy at 426 → dist=214 px
        else:
            dist = 1e6

        # ── 1) Detection: if idle/walking and player is close, start approach ──
        if self.state in ('idle','walk') and dist < DETECT_RANGE:
            self.state = 'approach'
            self.frame = 0.0
            # face the player
            self.dir  = 1 if self.target.rect.centerx > self.rect.centerx else -1
            self.flip = (self.dir < 0)

        # ── 2) State machine ──
        if self.state == 'idle':
            # Stop moving when idle
            self.rigid_body.velocity_x *= 0.8  # Apply friction to slow down
            # wait until `next_idle` time, then pick a patrol
            if now >= self.next_idle:
                self.state       = 'walk'
                self.frame       = 0.0
                self.patrol_dist = 0
                self.patrol_tgt  = WALK_DIST  # e.g. 100 px
                # choose random patrol direction
                self.dir   = random.choice([-1, 1])
                self.flip  = (self.dir < 0)

        elif self.state == 'walk':
            # patrol in one direction using physics
            # Set velocity directly instead of applying force for more predictable movement
            self.rigid_body.velocity_x = self.dir * WALK_SPEED
            self.patrol_dist += abs(WALK_SPEED)  # Track distance moved
            # if we've walked far enough, go back to idle
            if self.patrol_dist >= self.patrol_tgt:
                self.state     = 'idle'
                self.frame     = 0.0
                # schedule next idle duration
                self.next_idle = now + random.uniform(IDLE_MIN_SEC, IDLE_MAX_SEC)

        elif self.state == 'approach':
            # move toward player until within ATTACK_STOP_DIST using physics
            if dist > ATTACK_STOP_DIST:
                # Set velocity directly for more predictable movement
                self.rigid_body.velocity_x = self.dir * WALK_SPEED
            else:
                # Stop moving when close enough to attack
                self.rigid_body.velocity_x = 0
                # close enough to attack:
                self.dir   = 1 if self.target.rect.centerx > self.rect.centerx else -1
                self.flip  = (self.dir < 0)
                self.state = 'attack'
                self.frame = 0.0

        
        elif self.state == 'recover':
            # move backwards using physics
            # Set velocity directly for more predictable movement
            self.rigid_body.velocity_x = self.dir * WALK_SPEED
            # once back-off time is up:
            if now >= self.recover_end:
                if dist < DETECT_RANGE:
                    # if player still close, re-approach
                    self.state = 'approach'
                    self.frame = 0.0
                    self.dir   = 1 if self.target.rect.centerx > self.rect.centerx else -1
                    self.flip  = (self.dir < 0)
                else:
                    # otherwise go idle/patrol again
                    self.state     = 'idle'
                    self.frame     = 0.0
                    self.next_idle = now + random.uniform(IDLE_MIN_SEC, IDLE_MAX_SEC)

        # ── 3) default animation for idle/walk/approach/recover ──
        if self.state == 'idle':
            self.animate(self.idle)
        elif self.state in ('walk', 'approach', 'recover'):
            self.animate(self.walk)





    def draw_attack_point(self, screen, cam_x, cam_y):
        # Use the dynamic attack point position and radius
        # Adjust the attack point position by the camera offset
        adjusted_attack_point = (self.attack_point[0] - cam_x, self.attack_point[1] - cam_y)
        # Draw the attack point as a circle (blue for enemy, red for player)
        pygame.draw.circle(screen, (0, 0, 255), adjusted_attack_point, self.attack_radius, 2)
    
    def draw_rigid_body_debug(self, screen, cam_x, cam_y, color=(255, 0, 0), show_velocity=False):
        """Draw the enemy's rigid body collider for debugging"""
        if hasattr(self, 'rigid_body'):
            # Draw with specified color (default red to distinguish from player)
            self.rigid_body.draw_debug(screen, cam_x, cam_y, color=color, width=2, show_velocity=show_velocity)
            
    def check_tile_collision_below(self, tile_rects):
        """Check if there's a solid tile below the enemy for ground detection"""
        # Create a wider rectangle below the enemy's feet - much wider to prevent falling at level transitions
        # Start 1 pixel above feet so ground tile that aligns exactly with bottom is detected
        check_rect = pygame.Rect(
            self.rect.centerx - 50,
            self.rect.bottom - 1,
            100,
            33
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
                self.rect.bottom,         # Start at enemy's feet
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
