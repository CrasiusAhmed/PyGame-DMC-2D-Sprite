def calculate_dynamic_camera(player, enemies, screen_width, screen_height, total_world_width, bg_height, footer_margin):
    """Calculate camera position based on player and nearby enemies"""
    
    # For simplicity, focus on player in level 0
    if current_level_idx == 0:
        # In level 0, focus only on player
        cam_x = player.world_x - (screen_width // 2)
        cam_y = player.rect.bottom - (screen_height - footer_margin)
        
        # Clamp camera to world bounds
        cam_x = max(0, min(cam_x, total_world_width - screen_width))
        cam_y = max(0, min(cam_y, bg_height - screen_height))
        return cam_x, cam_y
    
    # Check for dying Yori (for cinematic camera)
    dying_yori = None
    if hasattr(yori, 'state') and yori.state == 'die':
        dying_yori = yori
    
    # Handle cinematic death camera first
    if dying_yori and hasattr(dying_yori, 'death_time'):
        time_since_death = time.time() - dying_yori.death_time
        if time_since_death < 5.0:
            # Cinematic camera for Yori's death
            cam_x = dying_yori.rect.centerx - (screen_width // 2)
            cam_y = dying_yori.rect.centery - 100 - (screen_height // 2)
            
            # Clamp camera to world bounds
            cam_x = max(0, min(cam_x, total_world_width - screen_width))
            cam_y = max(0, min(cam_y, bg_height - screen_height))
            return cam_x, cam_y
    
    # If in level 2, 3, or 4 with enemies, focus on player and target
    if current_level_idx in [2, 3, 4]:
        # Find enemies in the current level
        current_enemies = []
        for enemy in enemies:
            # Check if enemy is in the current level's bounds
            if level_start_x[current_level_idx] <= enemy.rect.centerx < level_start_x[current_level_idx] + level_pixel_widths[current_level_idx]:
                current_enemies.append(enemy)
        
        if current_enemies:
            # Focus on player and enemy in current level
            enemy = current_enemies[0]  # Take the first enemy in this level
            mid_x = (player.rect.centerx + enemy.rect.centerx) // 2
            mid_y = (player.rect.centery + enemy.rect.centery) // 2
            
            cam_x = mid_x - (screen_width // 2)
            cam_y = mid_y - (screen_height // 2)
            
            # Clamp camera to world bounds
            cam_x = max(0, min(cam_x, total_world_width - screen_width))
            cam_y = max(0, min(cam_y, bg_height - screen_height))
            return cam_x, cam_y
    
    # If in level 5 with Yori, focus on player and Yori
    if current_level_idx == 5 and yori.alive():
        mid_x = (player.rect.centerx + yori.rect.centerx) // 2
        mid_y = (player.rect.centery + yori.rect.centery) // 2
        
        cam_x = mid_x - (screen_width // 2)
        cam_y = mid_y - (screen_height // 2)
    else:
        # Default to player-focused camera
        cam_x = player.world_x - (screen_width // 2)
        cam_y = player.rect.bottom - (screen_height - footer_margin)
    
    # Clamp camera to world bounds
    cam_x = max(0, min(cam_x, total_world_width - screen_width))
    cam_y = max(0, min(cam_y, bg_height - screen_height))
    
    return cam_x, cam_y