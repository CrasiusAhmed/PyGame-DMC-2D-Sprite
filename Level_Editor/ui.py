# ui.py
import pygame

class Button:
    def __init__(self, label, rect, font, color):
        self.label = label
        self.rect  = rect
        self.font  = font
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, 2)
        txt = self.font.render(self.label, True, self.color)
        x = self.rect.x + (self.rect.w - txt.get_width())//2
        y = self.rect.y + (self.rect.h - txt.get_height())//2
        surface.blit(txt, (x,y))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)




# What it does:

    # Wraps a rect + label + hit‐test into a neat class.

    # draw() renders border and text; is_clicked() checks mouse pos.