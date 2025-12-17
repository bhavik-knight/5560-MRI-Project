"""
Layout Module - Static Floor Plan Drawing
==========================================
Handles all static room rendering for the MRI Digital Twin.
"""

import pygame
from src.config import (
    ROOM_COORDINATES, ROOM_LABELS, ROOM_COLORS,
    BLACK, WHITE
)

def get_contrasting_text_color(bg_color):
    """
    Returns WHITE or BLACK text color based on background luminance.
    Uses relative luminance formula for better contrast.
    """
    r, g, b = bg_color
    # Calculate relative luminance (perceived brightness)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    # Return white text for dark backgrounds, black for light backgrounds
    return WHITE if luminance < 0.5 else BLACK

def draw_room(surface, rect, color, label_text, font):
    """
    Draw a single room with border and centered text.
    
    Args:
        surface: pygame.Surface to draw on
        rect: pygame.Rect defining room boundaries
        color: RGB tuple for room fill color
        label_text: Text to display (supports \\n for multi-line)
        font: pygame.Font object (or None)
    """
    # 1. Draw filled rectangle
    pygame.draw.rect(surface, color, rect)
    
    # 2. Draw black border
    pygame.draw.rect(surface, BLACK, rect, 2)
    
    # 3. Draw centered text
    if font and label_text:
        text_color = get_contrasting_text_color(color)
        lines = label_text.split('\n')
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        start_y = rect.centery - (total_height / 2)
        
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, text_color)
            text_rect = text_surf.get_rect(centerx=rect.centerx, top=start_y + (i * line_height))
            surface.blit(text_surf, text_rect)

def draw_floor_plan(surface, font_room=None, font_zone=None):
    """
    Draw the complete MRI department floor plan.
    
    Args:
        surface: pygame.Surface to draw on
        font_room: pygame.Font for room labels
        font_zone: pygame.Font for zone labels (larger)
    """
    # Fill background
    surface.fill(WHITE)
    
    # Draw building border
    building_rect = pygame.Rect(*ROOM_COORDINATES['building'])
    pygame.draw.rect(surface, BLACK, building_rect, 5)
    
    # Draw all rooms in order (back to front for proper layering)
    rooms_to_draw = [
        # Zone 1 (bottom)
        ('zone1', font_zone),
        
        # Zone 4 (magnets - right side)
        ('magnet_3t', font_room),
        ('magnet_15t', font_room),
        
        # Zone 3 (control strip)
        ('control', font_zone),
        
        # Zone 2 (the hub - left/center)
        ('change_1', font_room),
        ('change_2', font_room),
        ('change_3', font_room),
        ('washroom_1', font_room),
        ('washroom_2', font_room),
        ('prep_1', font_room),
        ('prep_2', font_room),
        ('gowned_waiting', font_room),
        ('holding', font_room),
    ]
    
    for room_key, font in rooms_to_draw:
        rect = pygame.Rect(*ROOM_COORDINATES[room_key])
        color = ROOM_COLORS[room_key]
        label = ROOM_LABELS[room_key]
        draw_room(surface, rect, color, label, font)

def draw_dashboard(surface, stats_dict, font):
    """
    Draw statistics dashboard overlay.
    
    Args:
        surface: pygame.Surface to draw on
        stats_dict: Dictionary with keys like 'sim_time', 'patients_total', etc.
        font: pygame.Font for stats text
    """
    if not font:
        return
    
    # Dashboard background (top-left corner)
    dashboard_rect = pygame.Rect(10, 10, 300, 100)
    pygame.draw.rect(surface, WHITE, dashboard_rect)
    pygame.draw.rect(surface, BLACK, dashboard_rect, 2)
    
    # Draw stats
    y_offset = 20
    for key, value in stats_dict.items():
        text = f"{key}: {value}"
        text_surf = font.render(text, True, BLACK)
        surface.blit(text_surf, (20, y_offset))
        y_offset += 25
