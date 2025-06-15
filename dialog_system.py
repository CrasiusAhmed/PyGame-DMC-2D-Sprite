import pygame, os

class DialogSystem:
    """Very simple blocking dialog / cut-scene overlay.

    Provide a list of dicts with keys:
        - image: pygame.Surface (portrait) or path string
        - text: str (single or multi-line)  (\n for line break)
    """

    def __init__(self, screen_size):
        self.active = False
        self.dialogs = []
        self.index = 0
        self.font = pygame.font.Font(None, 40)
        self.screen_w, self.screen_h = screen_size
        self.skip_surface = self.font.render("[SKIP]", True, (255, 255, 255))
        self.skip_rect = self.skip_surface.get_rect()
        self.skip_rect.bottomright = (self.screen_w - 20, self.screen_h - 20)

    def start(self, dialogs):
        """Start a dialog sequence (list of dicts). Freezes game until finished."""
        self.dialogs = []
        for d in dialogs:
            img = d.get("image")
            if isinstance(img, str):
                if os.path.isfile(img):
                    img_surf = pygame.image.load(img).convert_alpha()
                else:
                    img_surf = None
            else:
                img_surf = img
            if img_surf:
                # scale portrait height to ~70% of screen
                scale_h = int(self.screen_h * 0.7)
                scale_factor = scale_h / img_surf.get_height()
                scale_w = int(img_surf.get_width() * scale_factor)
                img_surf = pygame.transform.smoothscale(img_surf, (scale_w, scale_h))
            self.dialogs.append({"image": img_surf, "text": d.get("text", "")})
        self.index = 0
        self.active = True

    def handle_event(self, e):
        if not self.active:
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.next()
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.next()

    def next(self):
        self.index += 1
        if self.index >= len(self.dialogs):
            self.active = False

    def draw(self, screen):
        if not self.active:
            return
        # semi-transparent black overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        dlg = self.dialogs[self.index]
        portrait = dlg["image"]
        text = dlg["text"]

        if portrait:
            screen.blit(portrait, (40, self.screen_h - portrait.get_height() - 40))
        # draw text box on right side
        text_x = 40 + (portrait.get_width() + 40 if portrait else 0)
        lines = text.split("\n")
        y = self.screen_h - 200
        for line in lines:
            ts = self.font.render(line, True, (255, 255, 255))
            screen.blit(ts, (text_x, y))
            y += ts.get_height() + 5
        # draw skip
        screen.blit(self.skip_surface, self.skip_rect)
