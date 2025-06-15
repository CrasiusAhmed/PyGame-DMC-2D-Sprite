# rigidbody.py
import pygame
import math

class CircleCollider:
    """A circular collider for 2D physics"""
    def __init__(self, center_x, center_y, radius):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
    
    def update_position(self, center_x, center_y):
        """Update the collider's center position"""
        self.center_x = center_x
        self.center_y = center_y
    
    def get_center(self):
        """Get the center position as a tuple"""
        return (self.center_x, self.center_y)
    
    def collides_with_circle(self, other_collider):
        """Check collision with another circle collider"""
        dx = self.center_x - other_collider.center_x
        dy = self.center_y - other_collider.center_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance < (self.radius + other_collider.radius)
    
    def collides_with_point(self, point_x, point_y):
        """Check if a point is inside this circle"""
        dx = self.center_x - point_x
        dy = self.center_y - point_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.radius
    
    def collides_with_rect(self, rect):
        """Check collision with a pygame Rect (for tile collision)"""
        # Find the closest point on the rectangle to the circle center
        closest_x = max(rect.left, min(self.center_x, rect.right))
        closest_y = max(rect.top, min(self.center_y, rect.bottom))
        
        # Calculate distance from circle center to closest point
        dx = self.center_x - closest_x
        dy = self.center_y - closest_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        return distance <= self.radius
    
    def draw_debug(self, screen, cam_x, cam_y, color=(0, 255, 0), width=2):
        """Draw the circle collider for debugging"""
        screen_x = int(self.center_x - cam_x)
        screen_y = int(self.center_y - cam_y)
        pygame.draw.circle(screen, color, (screen_x, screen_y), int(self.radius), width)


class RigidBody:
    """A rigid body with physics properties and a circular collider"""
    def __init__(self, center_x, center_y, radius, mass=1.0):
        self.collider = CircleCollider(center_x, center_y, radius)
        self.mass = mass
        
        # Physics properties
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0
        
        # Physics constants
        self.gravity = 0.8
        self.friction = 0.9  # Ground friction (higher = less sliding)
        self.air_resistance = 0.99  # Air resistance (higher = less air drag)
        self.bounce = 0.1  # Bounce factor when hitting surfaces (lower = less bouncy)
        
        # Ground detection
        self.is_grounded = False
        self.ground_y = None
        
        # Collision response
        self.can_collide = True
        
    def apply_force(self, force_x, force_y):
        """Apply a force to the rigid body"""
        self.acceleration_x += force_x / self.mass
        self.acceleration_y += force_y / self.mass
    
    def apply_impulse(self, impulse_x, impulse_y):
        """Apply an instant impulse to the rigid body"""
        self.velocity_x += impulse_x / self.mass
        self.velocity_y += impulse_y / self.mass
    
    def set_position(self, center_x, center_y):
        """Set the rigid body position"""
        self.collider.update_position(center_x, center_y)
    
    def get_position(self):
        """Get the rigid body position"""
        return self.collider.get_center()
    
    def update_physics(self, dt=1.0):
        """Update physics simulation"""
        # Apply gravity if not grounded
        if not self.is_grounded:
            self.acceleration_y += self.gravity
        
        # Update velocity with acceleration
        self.velocity_x += self.acceleration_x * dt
        self.velocity_y += self.acceleration_y * dt
        
        # Apply air resistance
        if not self.is_grounded:
            self.velocity_x *= self.air_resistance
            self.velocity_y *= self.air_resistance
        else:
            # Apply ground friction
            self.velocity_x *= self.friction
        
        # Update position with velocity
        new_x = self.collider.center_x + self.velocity_x * dt
        new_y = self.collider.center_y + self.velocity_y * dt
        
        self.set_position(new_x, new_y)
        
        # Reset acceleration (forces are applied each frame)
        self.acceleration_x = 0.0
        self.acceleration_y = 0.0
    
    def check_ground_collision(self, ground_y):
        """Check and resolve collision with ground"""
        bottom_y = self.collider.center_y + self.collider.radius
        
        # Track ground state changes (without debug prints)
        was_grounded = self.is_grounded
        
        # Handle case where ground_y is None (no ground beneath)
        if ground_y is None:
            self.is_grounded = False
            self.ground_y = None
            return
            
        if bottom_y >= ground_y:
            # Collision with ground
            
            # Only set is_grounded true if coming down (not going up through ground)
            if self.velocity_y >= 0:
                self.is_grounded = True
                self.ground_y = ground_y
                
                # Adjust position to sit on ground
                new_center_y = ground_y - self.collider.radius
                self.set_position(self.collider.center_x, new_center_y)
                
                # Always stop vertical velocity when grounded
                self.velocity_y = 0
        else:
            # Not touching ground
            self.is_grounded = False
            self.ground_y = ground_y  # IMPORTANT: Keep track of ground_y even when not touching it
    
    def check_tile_collision(self, tile_rects):
        """Check and resolve collision with tile rectangles"""
        if not self.can_collide:
            return
        
        for tile_rect in tile_rects:
            if self.collider.collides_with_rect(tile_rect):
                self.resolve_tile_collision(tile_rect)
    
    def resolve_tile_collision(self, tile_rect):
        """Resolve collision with a tile rectangle"""
        # Calculate overlap and push the circle out
        center_x, center_y = self.collider.get_center()
        radius = self.collider.radius
        
        # Find the closest point on the rectangle
        closest_x = max(tile_rect.left, min(center_x, tile_rect.right))
        closest_y = max(tile_rect.top, min(center_y, tile_rect.bottom))
        
        # Calculate penetration
        dx = center_x - closest_x
        dy = center_y - closest_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < radius and distance > 0:
            # Normalize the collision vector
            nx = dx / distance
            ny = dy / distance
            
            # Calculate penetration depth
            penetration = radius - distance
            
            # Push the circle out
            new_x = center_x + nx * penetration
            new_y = center_y + ny * penetration
            self.set_position(new_x, new_y)
            
            # Reflect velocity based on collision normal
            dot_product = self.velocity_x * nx + self.velocity_y * ny
            self.velocity_x -= 2 * dot_product * nx * self.bounce
            self.velocity_y -= 2 * dot_product * ny * self.bounce
            
            # Check if this is a ground collision (collision normal points up)
            if ny < -0.7:  # Normal points mostly upward
                self.is_grounded = True
                self.ground_y = tile_rect.top
                if self.velocity_y > 0:
                    self.velocity_y = 0
                # Debug logging removed to prevent spam
    
    def draw_debug(self, screen, cam_x, cam_y, color=(0, 255, 0), width=2, show_velocity=False):
        """Draw debug information"""
        self.collider.draw_debug(screen, cam_x, cam_y, color, width)
        
        # Draw velocity vector (optional)
        if show_velocity:
            center_x, center_y = self.collider.get_center()
            screen_x = int(center_x - cam_x)
            screen_y = int(center_y - cam_y)
            
            vel_end_x = screen_x + int(self.velocity_x * 2)
            vel_end_y = screen_y + int(self.velocity_y * 2)
            
            if abs(self.velocity_x) > 0.1 or abs(self.velocity_y) > 0.1:
                pygame.draw.line(screen, (255, 0, 0), (screen_x, screen_y), (vel_end_x, vel_end_y), 2)