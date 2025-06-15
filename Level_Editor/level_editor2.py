import pygame
import sys
import math
import font



# Initialize Pygame
pygame.init()
pygame.font.init()
font = pygame.font.SysFont(None, 24)

# Window size
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Level display area (70% width, 50% height)
LEVEL_WIDTH, LEVEL_HEIGHT = int(WINDOW_WIDTH * 0.7), int(WINDOW_HEIGHT * 0.8)
LEVEL_X, LEVEL_Y = 10, 10  # top-left of level area

# Tile size (pixels)
TILE_SIZE = 50

# Compute grid dimensions
COLS = LEVEL_WIDTH  // TILE_SIZE
ROWS = LEVEL_HEIGHT // TILE_SIZE

# Colors
WHITE = (255, 255, 255)
GRAY  = ( 40,  40,  40)
BLACK = (  0,   0,   0)
GREEN = (  0, 255,   0)

# Create window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Level Editor")

# Load & scale background
background_img = pygame.image.load("img/background-editor.png").convert_alpha()
background_img = pygame.transform.scale(background_img, (LEVEL_WIDTH, LEVEL_HEIGHT))

# ------------------------------------------------------------------------------
# NEW: Load multiple tile images into a list and scale them
tile_paths = [
    "img/tile/1.png",
    "img/tile/2.png",
    "img/tile/3.png",
    "img/tile/4.png",
    "img/tile/5.png",
    "img/tile/6.png",
    "img/tile/7.png",
    "img/tile/8.png",
    "img/tile/9.png",
    "img/tile/10.png",
    "img/tile/11.png",
    "img/tile/tile.png",
]
tiles = []
for path in tile_paths:
    img = pygame.image.load(path).convert_alpha()
    tiles.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))

# Track which tile is selected (index into `tiles`)
selected_tile = 0

# Prepare menu preview rects (one per tile), spaced vertically
menu_rect = pygame.Rect(
    LEVEL_X + LEVEL_WIDTH + 20,
    LEVEL_Y,
    WINDOW_WIDTH - (LEVEL_WIDTH + LEVEL_X + 30),
    WINDOW_HEIGHT - LEVEL_Y * 2
)


# Initialize empty map: -1 means no tile
map_data = [[-1 for _ in range(COLS)] for _ in range(ROWS)]

clock = pygame.time.Clock()
running = True




# After you build menu_tiles:
MENU_COLS = 3
spacing = 10         # you already had this

# Pagination state
page = 0
tiles_per_page = MENU_COLS * ((menu_rect.height - 150) // (TILE_SIZE + spacing))
max_page = max(0, math.ceil(len(tiles) / tiles_per_page) - 1)

# Prepare Prev/Next button rects (above the 4 action buttons)
nav_height = 30
nav_y = menu_rect.y + menu_rect.height - nav_height * 2 - 80
prev_rect = pygame.Rect(menu_rect.x + spacing, nav_y, 60, nav_height)
next_rect = pygame.Rect(menu_rect.x + menu_rect.width - spacing - 60, nav_y, 60, nav_height)

# Prepare bottom action buttons
button_names = ["Save", "Load", "Create", "Import"]
buttons = []
btn_w = (menu_rect.width - spacing * (len(button_names) + 1)) // len(button_names)
btn_h = 40
btn_y = menu_rect.y + menu_rect.height - btn_h - 20
bx = menu_rect.x + spacing
for name in button_names:
    buttons.append((name, pygame.Rect(bx, btn_y, btn_w, btn_h)))
    bx += btn_w + spacing

# Stub functions for your next step
def save_level():
    print("Save level here")

def load_level():
    print("Load level here")

def create_new_level():
    print("Create new level here")

def import_level():
    print("Import level here")







while running:
    screen.fill(GRAY)

    # 1) Draw level border
    level_rect = pygame.Rect(LEVEL_X, LEVEL_Y, LEVEL_WIDTH, LEVEL_HEIGHT)
    pygame.draw.rect(screen, WHITE, level_rect, 3)

    # 2) Draw background inside level area
    screen.blit(background_img, (LEVEL_X, LEVEL_Y))

    # 3) Draw grid lines
    for row in range(ROWS + 1):
        y = LEVEL_Y + row * TILE_SIZE
        pygame.draw.line(screen, BLACK, (LEVEL_X, y), (LEVEL_X + LEVEL_WIDTH, y), 1)
    for col in range(COLS + 1):
        x = LEVEL_X + col * TILE_SIZE
        pygame.draw.line(screen, BLACK, (x, LEVEL_Y), (x, LEVEL_Y + LEVEL_HEIGHT), 1)

    # 4) Draw any placed tiles from map_data
    for row in range(ROWS):
        for col in range(COLS):
            idx = map_data[row][col]
            if idx != -1:
                x = LEVEL_X + col * TILE_SIZE
                y = LEVEL_Y + row * TILE_SIZE
                screen.blit(tiles[idx], (x, y))






      # Draw menu border
    pygame.draw.rect(screen, WHITE, menu_rect, 3)

    # 2‑page tile grid
    start = page * tiles_per_page
    end   = start + tiles_per_page
    for idx, tile in enumerate(tiles[start:end]):
        i = start + idx
        row = idx // MENU_COLS
        col = idx %  MENU_COLS
        x = menu_rect.x + spacing + col * (TILE_SIZE + spacing)
        y = menu_rect.y + spacing + row * (TILE_SIZE + spacing)
        screen.blit(tile, (x, y))
        # highlight selected
        if i == selected_tile:
            pygame.draw.rect(screen, GREEN, (x, y, TILE_SIZE, TILE_SIZE), 3)

    # Prev / Next page buttons
    pygame.draw.rect(screen, WHITE, prev_rect, 2)
    pygame.draw.rect(screen, WHITE, next_rect, 2)
    screen.blit(font.render("Prev", True, WHITE), (prev_rect.x+5, prev_rect.y+5))
    screen.blit(font.render("Next", True, WHITE), (next_rect.x+5, next_rect.y+5))

    # Bottom action buttons
    for name, rect in buttons:
        pygame.draw.rect(screen, WHITE, rect, 2)
        txt = font.render(name, True, WHITE)
        tx = rect.x + (rect.w - txt.get_width()) // 2
        ty = rect.y + (rect.h - txt.get_height()) // 2
        screen.blit(txt, (tx, ty))




    # ------------------------------------------------------------------------------

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # ←–– menu prev/next
            if prev_rect.collidepoint(mx, my) and page > 0:
                page -= 1
            elif next_rect.collidepoint(mx, my) and page < max_page:
                page += 1

            # ←–– action buttons
            for name, rect in buttons:
                if rect.collidepoint(mx, my):
                    if name == "Save":   save_level()
                    elif name == "Load": load_level()
                    elif name == "Create": create_new_level()
                    elif name == "Import": import_level()

            # ←–– paginated tile‐selection
            if menu_rect.collidepoint(mx, my):
                local_x = mx - (menu_rect.x + spacing)
                local_y = my - (menu_rect.y + spacing)
                c = local_x // (TILE_SIZE + spacing)
                r = local_y // (TILE_SIZE + spacing)
                i = page * tiles_per_page + r * MENU_COLS + c
                if 0 <= i < len(tiles):
                    selected_tile = i

            # ←–– place/remove in the level area
            elif level_rect.collidepoint(mx, my):
                col = (mx - LEVEL_X) // TILE_SIZE
                row = (my - LEVEL_Y) // TILE_SIZE
                if 0 <= col < COLS and 0 <= row < ROWS:
                    if event.button == 1:
                        map_data[row][col] = selected_tile
                    elif event.button == 3:
                        map_data[row][col] = -1



    pygame.display.update()
    clock.tick(60)

pygame.quit()
sys.exit()
