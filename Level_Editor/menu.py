# menu.py
import pygame
import math
from config import WHITE, GREEN

class TileMenu:
    def __init__(self, rect, tiles, cols, gap, font, padding = 50):
        """
        A paginated tile selector.
        - rect: pygame.Rect defining menu area
        - tiles: list of tile Surfaces
        - cols: number of columns (e.g. 3 for left/center/right)
        - gap: pixels between tiles
        - font: Pygame Font for labels
        - padding: inset from rect edges (like CSS padding)
        """
        self.rect    = rect
        self.tiles   = tiles
        self.cols    = cols
        self.gap     = gap
        self.font    = font
        self.padding = padding

        # How many tiles fit per page?
        tile_h = tiles[0].get_height()
        # Calculate available height for tiles (total height - top padding - bottom padding - nav button height - extra spacing)
        btn_h = 30
        available_height = rect.height - (2 * self.padding) - btn_h - 20  # 20 for extra spacing above nav buttons
        rows_per_page = available_height // (tile_h + gap)
        self.per_page = cols * rows_per_page
        self.max_page = max(0, math.ceil(len(tiles) / self.per_page) - 1)
        self.page     = 0

        # NEW: Prev/Next rectangles with padding
        btn_w = 60
        nav_y = rect.y + rect.height - self.padding - btn_h
        prev_x  = rect.x + self.padding
        next_x  = rect.x + rect.width - self.padding - btn_w
        self.prev = pygame.Rect(prev_x,  nav_y, btn_w, btn_h)
        self.next = pygame.Rect(next_x,  nav_y, btn_w, btn_h)


    def draw(self, surface, selected_index):
        # 1) Outline the menu
        pygame.draw.rect(surface, WHITE, self.rect, 3)

        # 2) Compute X positions: left, center, right within padded area
        w = self.tiles[0].get_width()
        left_x   = self.rect.x + self.padding
        center_x = self.rect.x + (self.rect.width - w)//2
        right_x  = self.rect.x + self.rect.width - self.padding - w
        xs = [left_x, center_x, right_x]

        # 3) Y start position
        base_y = self.rect.y + self.padding

        # 4) Blit each tile for the current page
        start = self.page * self.per_page
        tile_h = self.tiles[0].get_height()
        for idx, tile in enumerate(self.tiles[start:start + self.per_page]):
            row, col = divmod(idx, self.cols)
            x = xs[col]
            y = base_y + row * (tile_h + self.gap)
            surface.blit(tile, (x, y))

            # 5) Highlight the selected one
            if start + idx == selected_index:
                pygame.draw.rect(surface, GREEN,
                                 (x, y, w, tile_h), 3)

        # 6) Draw Prev / Next controls
        pygame.draw.rect(surface, WHITE, self.prev, 2)
        surface.blit(self.font.render("Prev", True, WHITE),
                     (self.prev.x + 5, self.prev.y + 5))
        pygame.draw.rect(surface, WHITE, self.next, 2)
        surface.blit(self.font.render("Next", True, WHITE),
                     (self.next.x + 5, self.next.y + 5))

    def handle_event(self, pos, mouse_button):
        mx, my = pos

        # 1) Page back / forward
        if self.prev.collidepoint(mx, my) and self.page > 0:
            self.page -= 1
        elif self.next.collidepoint(mx, my) and self.page < self.max_page:
            self.page += 1

        # 2) Tile selection within the menu box
        if self.rect.collidepoint(mx, my):
            # Don't process clicks on navigation buttons
            if self.prev.collidepoint(mx, my) or self.next.collidepoint(mx, my):
                return None
                
            # reuse the same xs + base_y logic as draw()
            w = self.tiles[0].get_width()
            h = self.tiles[0].get_height()
            xs = [
                self.rect.x + self.padding,
                self.rect.x + (self.rect.width - w)//2,
                self.rect.x + self.rect.width - self.padding - w
            ]
            base_y = self.rect.y + self.padding

            start = self.page * self.per_page
            for idx, tile in enumerate(self.tiles[start:start + self.per_page]):
                row, col = divmod(idx, self.cols)
                x = xs[col]
                y = base_y + row * (h + self.gap)
                tile_rect = pygame.Rect(x, y, w, h)
                if tile_rect.collidepoint(mx, my):
                    return start + idx  # selected tile index

        return None