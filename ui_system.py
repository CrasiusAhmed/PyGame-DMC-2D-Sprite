# ui_system.py
import pygame
import time
import os

class DamageText:
    def __init__(self, x, y, damage, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.start_y = y
        self.damage = damage
        self.color = color
        self.start_time = time.time()
        self.duration = 1.0  # 1 second
        self.font = pygame.font.Font(None, 40)  # Bigger font for better visibility
        
    def update(self):
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        if elapsed >= self.duration:
            return False  # Remove this damage text
            
        # Move text upward and fade out
        progress = elapsed / self.duration
        self.y = self.start_y - (progress * 80)  # Move up 80 pixels over duration
        
        return True  # Keep this damage text
        
    def draw(self, screen, cam_x, cam_y):
        # Calculate alpha for fade out
        elapsed = time.time() - self.start_time
        progress = elapsed / self.duration
        alpha = int(255 * (1 - progress))
        
        # Create text surface with outline for better visibility
        # Handle both numeric damage and text like "Blocked"
        if isinstance(self.damage, (int, float)):
            text_str = str(int(self.damage))
        else:
            text_str = str(self.damage)
        
        # Draw outline (black)
        outline_color = (0, 0, 0)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    outline_surface = self.font.render(text_str, True, outline_color)
                    outline_surface.set_alpha(alpha)
                    screen_x = self.x - cam_x + dx
                    screen_y = self.y - cam_y + dy
                    screen.blit(outline_surface, (screen_x, screen_y))
        
        # Draw main text
        text_surface = self.font.render(text_str, True, self.color)
        text_surface.set_alpha(alpha)
        screen_x = self.x - cam_x
        screen_y = self.y - cam_y
        screen.blit(text_surface, (screen_x, screen_y))

class HealthBar:
    def __init__(self, width=80, height=8):
        self.width = width
        self.height = height
        self.font = pygame.font.Font(None, 24)
        
    def draw(self, screen, x, y, current_health, max_health, cam_x, cam_y):
        # Calculate screen position
        screen_x = x - cam_x - self.width // 2
        screen_y = y - cam_y - 40  # Position above the entity
        
        # Calculate health percentage
        health_percent = max(0, current_health / max_health) if max_health > 0 else 0
        
        # Background (red)
        bg_rect = pygame.Rect(screen_x, screen_y, self.width, self.height)
        pygame.draw.rect(screen, (100, 0, 0), bg_rect)
        
        # Health bar (green to red gradient based on health)
        if health_percent > 0:
            health_width = int(self.width * health_percent)
            health_rect = pygame.Rect(screen_x, screen_y, health_width, self.height)
            
            # Color gradient: green when full, yellow at 50%, red when low
            if health_percent > 0.6:
                color = (0, 255, 0)  # Green
            elif health_percent > 0.3:
                color = (255, 255, 0)  # Yellow
            else:
                color = (255, 0, 0)  # Red
                
            pygame.draw.rect(screen, color, health_rect)
        
        # Border
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1)
        
        # Health text
        health_text = f"{int(current_health)}/{int(max_health)}"
        text_surface = self.font.render(health_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(screen_x + self.width // 2, screen_y - 15))
        
        # Draw text background for better visibility
        text_bg = pygame.Rect(text_rect.x - 2, text_rect.y - 1, text_rect.width + 4, text_rect.height + 2)
        pygame.draw.rect(screen, (0, 0, 0, 128), text_bg)
        
        screen.blit(text_surface, text_rect)

class UISystem:
    def __init__(self):
        self.damage_texts = []
        self.health_bar = HealthBar()
        # Player health tracking for damage overlay effect
        self._prev_player_health = None
        self._damage_prev_percent = 1.0  # percent right before damage
        self._damage_flash_end = 0       # timestamp when yellow flash ends

        # Skill icon (load safely before video mode is set)
        icon_path = os.path.join("img", "Player", "Player Skill Icon", "1.png")
        self.skill_icon = None
        if os.path.isfile(icon_path):
            raw_icon = pygame.image.load(icon_path)
            # convert_alpha requires a display mode; only call if already set
            if pygame.display.get_surface():
                raw_icon = raw_icon.convert_alpha()
            self.skill_icon = pygame.transform.smoothscale(raw_icon, (80, 80))
                    
    def add_damage_text(self, x, y, damage, color=(255, 50, 50)):
        """Add a new damage text at the specified world coordinates"""
        self.damage_texts.append(DamageText(x, y, damage, color))
        
    def update(self):
        """Update all UI elements and remove expired ones"""
        self.damage_texts = [dt for dt in self.damage_texts if dt.update()]
        
    def draw_damage_texts(self, screen, cam_x, cam_y):
        """Draw all active damage texts"""
        for dt in self.damage_texts:
            dt.draw(screen, cam_x, cam_y)
            
    def draw_entity_health(self, screen, entity, cam_x, cam_y):
        """Draw health bar above an entity"""
        if hasattr(entity, 'current_health') and hasattr(entity, 'max_health'):
            # Use rigid body position if available, otherwise use rect
            if hasattr(entity, 'rigid_body'):
                x, y = entity.rigid_body.get_position()
                y -= 50  # Position above the rigid body
            else:
                x = entity.rect.centerx
                y = entity.rect.top
                
            self.health_bar.draw(screen, x, y, entity.current_health, entity.max_health, cam_x, cam_y)
            
    def draw_player_health_ui(self, screen, player, x=20, y=20):
        """Draw player health bar (Souls-style) in top-left corner with red base,
        yellow damage flash, then dark-red missing portion."""
        if not (hasattr(player, 'current_health') and hasattr(player, 'max_health')):
            return

        # Track damage events to create yellow flash overlay
        now_t = time.time()
        if self._prev_player_health is None:
            self._prev_player_health = player.current_health
        if player.current_health < self._prev_player_health:
            # Damage happened → remember previous percent for flash region
            self._damage_prev_percent = max(0, self._prev_player_health / player.max_health)
            self._damage_flash_end = now_t + 1.0  # 1 second yellow flash
        self._prev_player_health = player.current_health

        font = pygame.font.Font(None, 36)

        # ------ lazy-load icon and dimensions ------
        if not hasattr(self, "_player_icon"):
            # Search common locations for player icon
            search_paths = []
            # 1) explicit file path provided in message
            search_paths.append(os.path.join("img", "Player", "Player Image", "Hichigava.png"))
            # 2) any file inside 'img/Player/Player Image' folder
            img_subdir = os.path.join("img", "Player", "Player Image")
            if os.path.isdir(img_subdir):
                for fname in os.listdir(img_subdir):
                    if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                        search_paths.append(os.path.join(img_subdir, fname))
            # 3) fall back to previous guesses inside img/Player root
            icon_dir = os.path.join("img", "Player")
            for fname in ["Player Image.png", "Player Image.jpg", "Player Image.jpeg", "Player.png", "icon.png"]:
                search_paths.append(os.path.join(icon_dir, fname))

            icon_path = next((p for p in search_paths if os.path.isfile(p)), None)
            if icon_path:
                try:
                    img_raw = pygame.image.load(icon_path).convert_alpha()
                    self._player_icon = pygame.transform.smoothscale(img_raw, (100, 100))
                except Exception:
                    self._player_icon = None
            else:
                self._player_icon = None

        icon_w = self._player_icon.get_width() if getattr(self, "_player_icon", None) else 0
        icon_pad = 8 if icon_w else 0

        bar_width = 260  # wider than before
        bar_height = 24
        bar_x = x + icon_w + icon_pad
        bar_y = y + 8  # align with icon

        # ------ background and border ------
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (40, 0, 0), bg_rect)  # very dark background
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)

        # ------ health bar pieces ------
        health_percent = max(0, player.current_health / player.max_health) if player.max_health else 0

        # 1) Red current health
        if health_percent > 0:
            red_rect = pygame.Rect(bar_x, bar_y, int(bar_width * health_percent), bar_height)
            pygame.draw.rect(screen, (180, 0, 0), red_rect)  # solid red

        # 2) Yellow flash overlay for recently lost health
        if now_t < self._damage_flash_end and self._damage_prev_percent > health_percent:
            flash_start_px = int(bar_width * health_percent)
            flash_end_px = int(bar_width * self._damage_prev_percent)
            flash_rect = pygame.Rect(bar_x + flash_start_px, bar_y, flash_end_px - flash_start_px, bar_height)
            pygame.draw.rect(screen, (255, 200, 0), flash_rect)

        # 3) Dark-red missing health area (drawn after flash to appear behind it later)
        missing_start_px = int(bar_width * health_percent)
        if missing_start_px < bar_width:
            missing_rect = pygame.Rect(bar_x + missing_start_px, bar_y, bar_width - missing_start_px, bar_height)
            pygame.draw.rect(screen, (80, 0, 0), missing_rect)

        # ------ draw icon ------
        if getattr(self, "_player_icon", None):
            screen.blit(self._player_icon, (x, y))

    # ─────────────────────────────────────────────
    # Skill cooldown UI (bottom-center icon + overlay)
    # ─────────────────────────────────────────────
    def draw_skill_cooldown(self, screen, player, scr_w, scr_h, bottom_margin=20):
        """Draw the player's skill icon at the bottom-centre of the screen and
        overlay a grey fill that rises from bottom-to-top while the skill is on
        cooldown.  The icon is loaded in __init__; if unavailable, skip."""
        if self.skill_icon is None:
            return
        # Location of the icon (centre horizontally)
        icon_w, icon_h = self.skill_icon.get_size()
        x = (scr_w - icon_w) // 2
        y = scr_h - icon_h - bottom_margin

        # Cool-down progress 0→1 (1 = ready, 0 = just used)
        cd_ms = getattr(player, "skill_cooldown", 0)
        last_ms = getattr(player, "last_skill_time_ms", -cd_ms)
        now_ms = pygame.time.get_ticks()
        elapsed = now_ms - last_ms
        t = max(0, min(1, elapsed / cd_ms)) if cd_ms > 0 else 1  # clamp

        # Draw base icon
        screen.blit(self.skill_icon, (x, y))

        if t < 1.0:
            # Skill still recharging – draw grey overlay covering (1-t) of height.
            overlay_h = int(icon_h * (1 - t))
            if overlay_h > 0:
                overlay = pygame.Surface((icon_w, overlay_h), pygame.SRCALPHA)
                overlay.fill((30, 30, 30, 180))  # semi-transparent grey
                screen.blit(overlay, (x, y + (icon_h - overlay_h)))

        # Optional outline circle for clarity
        pygame.draw.circle(screen, (255, 255, 255), (x + icon_w // 2, y + icon_h // 2), icon_w // 2, 2)