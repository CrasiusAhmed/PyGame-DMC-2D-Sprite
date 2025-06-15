# Purpose: Manage your 2D map array.

def create_empty(cols, rows):
    """Return a new rows×cols grid filled with −1."""
    return [[-1]*cols for _ in range(rows)]
