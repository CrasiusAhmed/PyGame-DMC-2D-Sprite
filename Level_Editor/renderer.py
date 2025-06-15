# Purpose: All your Pygame drawing routines.
import pygame
from config import BLACK

def draw_backgrounds(surface, x, y, backgrounds):
    """
    Blit each background Surface in order (front-to-back).
    """
    for bg in backgrounds:
        surface.blit(bg, (x, y))


def draw_grid(surface, x, y, width, height, background, rows, cols, tile_size):
    """
    Draws your level area:
      1) Black border
      2) Background image
      3) Grid lines
    
    - surface: the Pygame display or a Surface
    - x, y: top-left corner of the grid
    - width, height: pixel dimensions of the grid area
    - background: a Surface to blit under the grid
    - rows, cols: number of grid cells vertically/horizontally
    - tile_size: size in pixels of each cell
    """
    # 1) Thick black border
    pygame.draw.rect(surface, BLACK, (x, y, width, height), 3)

    # 2) Draw the background (e.g. your sky/ground image)
    surface.blit(background, (x, y))

    # 2a) Horizontal grid lines
    for row in range(rows + 1):
        yy = y + row * tile_size
        pygame.draw.line(surface, BLACK, (x, yy), (x + width, yy), 1)

    # 2b) Vertical grid lines
    for col in range(cols + 1):
        xx = x + col * tile_size
        pygame.draw.line(surface, BLACK, (xx, y), (xx, y + height), 1)