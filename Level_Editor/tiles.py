import pygame

def load_tiles(tile_paths, tile_size):
    """
    Loads each image in `tile_paths`, scales it to (tile_size × tile_size),
    and returns a list of the resulting Surfaces.
    """
    tiles = []
    for path in tile_paths:
        img = pygame.image.load(path).convert_alpha()
        tiles.append(pygame.transform.scale(img, (tile_size, tile_size)))
    return tiles



# What it does:

    # Iterates your list of file‐paths, loads each one with alpha.

    # Scales to your uniform TILE_SIZE and returns the list.