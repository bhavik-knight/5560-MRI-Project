"""
Layout Module - Medical White Floor Plan with Sidebar
======================================================
Clean, high-contrast visualization with separated statistics panel.
"""

import pygame
from src.config import (
    ROOM_COORDINATES, ROOM_LABELS,
    MEDICAL_WHITE, CORRIDOR_GREY, WALL_BLACK, LABEL_BLACK, SEPARATOR_BLACK,
    SIDEBAR_X, WINDOW_WIDTH, WINDOW_HEIGHT,
    GREY_ARRIVING, BLUE_CHANGING, YELLOW_PREPPED, GREEN_SCANNING,
    ORANGE_PORTER, CYAN_BACKUP, PURPLE_SCAN, ZONE1_TOP_Y
)



def draw_room(surface, rect, label_text, font):
    """
    Draw a single room with medical white aesthetic.
    
    All rooms are WHITE with BLACK borders and BLACK centered text.
    
    Args:
        surface: pygame.Surface to draw on
        rect: pygame.Rect defining room boundaries
        label_text: Text to display (supports \\n for multi-line)
        font: pygame.Font object (or None)
    """
    # 1. Fill with medical white
    pygame.draw.rect(surface, MEDICAL_WHITE, rect)
    
    # 2. Draw black border (walls)
    pygame.draw.rect(surface, WALL_BLACK, rect, 2)
    
    # 3. Draw centered black text
    if font and label_text:
        lines = label_text.split('\n')
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        start_y = rect.centery - (total_height / 2)
        
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, LABEL_BLACK)
            text_rect = text_surf.get_rect(centerx=rect.centerx, top=start_y + (i * line_height))
            surface.blit(text_surf, text_rect)

def draw_coordinates(surface, font, building_rect):
    """
    Draw X and Y coordinate markers along the building border.
    """
    if not font:
        return
        
    x_start, y_start, width, height = building_rect
    x_end = x_start + width
    y_end = y_start + height
    
    # Draw X coordinates (Top and Bottom)
    for x in range(0, 1201, 100):
        # Top
        if x_start <= x <= x_end:
            text = font.render(str(x), True, (120, 120, 120))
            surface.blit(text, (x, y_start + 5))
        # Bottom
        if x_start <= x <= x_end:
            text = font.render(str(x), True, (120, 120, 120))
            surface.blit(text, (x, y_end - 15))
            
    # Draw Y coordinates (Left and Right)
    for y in range(0, 801, 100):
        # Left
        if y_start <= y <= y_end:
            text = font.render(str(y), True, (120, 120, 120))
            surface.blit(text, (x_start + 5, y + 2))
        # Right
        if y_start <= y <= y_end:
            text = font.render(str(y), True, (120, 120, 120))
            surface.blit(text, (x_end - 30, y + 2))

def draw_floor_plan(surface, font_room=None, font_zone=None):
    """
    Draw the complete MRI floor plan with medical white aesthetic.
    
    Args:
        surface: pygame.Surface to draw on
        font_room: pygame.Font for room labels (size 14)
        font_zone: pygame.Font for zone labels (larger)
    """
    # Fill background with corridor grey
    surface.fill(CORRIDOR_GREY)
    
    # Draw building border
    building_rect = pygame.Rect(*ROOM_COORDINATES['building'])
    pygame.draw.rect(surface, WALL_BLACK, building_rect, 5)
    
    # Draw coordinates
    draw_coordinates(surface, font_room, building_rect)
    
    # Draw all rooms in order (all WHITE with BLACK borders)
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
        ('waiting_room', font_room),
    ]

    
    for room_key, font in rooms_to_draw:
        rect = pygame.Rect(*ROOM_COORDINATES[room_key])
        label = ROOM_LABELS[room_key]
        draw_room(surface, rect, label, font)


def draw_sidebar(surface, stats_dict, font):
    """
    Draw statistics sidebar on the right side of the screen.
    
    Args:
        surface: pygame.Surface to draw on
        stats_dict: Dictionary with keys like 'Sim Time', 'Patients', etc.
        font: pygame.Font for text
    """
    if not font:
        return
    
    # Draw vertical separator line
    pygame.draw.line(surface, SEPARATOR_BLACK, 
                     (SIDEBAR_X, 0), (SIDEBAR_X, WINDOW_HEIGHT), 3)
    
    # Sidebar background (already corridor grey from fill)
    
    # Title
    y_offset = 20
    title = font.render("SIMULATION STATS", True, LABEL_BLACK)
    surface.blit(title, (SIDEBAR_X + 20, y_offset))
    y_offset += 40
    
    # Draw horizontal line
    pygame.draw.line(surface, SEPARATOR_BLACK,
                     (SIDEBAR_X + 10, y_offset), (WINDOW_WIDTH - 10, y_offset), 1)
    y_offset += 20
    
    # Stats
    if stats_dict:
        for key, value in stats_dict.items():
            text = font.render(f"{key}: {value}", True, LABEL_BLACK)
            surface.blit(text, (SIDEBAR_X + 20, y_offset))
            y_offset += 30
    
    # Add spacing
    y_offset += 20
    
    # Legend section
    pygame.draw.line(surface, SEPARATOR_BLACK,
                     (SIDEBAR_X + 10, y_offset), (WINDOW_WIDTH - 10, y_offset), 1)
    y_offset += 20
    
    legend_title = font.render("PATIENT STATES", True, LABEL_BLACK)
    surface.blit(legend_title, (SIDEBAR_X + 20, y_offset))
    y_offset += 35
    
    # Patient state legend
    patient_states = [
        (GREY_ARRIVING, "Arriving (Zone 1)"),
        (BLUE_CHANGING, "Changing"),
        (YELLOW_PREPPED, "Prepped (Waiting)"),
        (GREEN_SCANNING, "Scanning"),
    ]
    
    for color, label in patient_states:
        # Draw circle
        pygame.draw.circle(surface, color, (SIDEBAR_X + 30, y_offset), 6)
        pygame.draw.circle(surface, WALL_BLACK, (SIDEBAR_X + 30, y_offset), 6, 1)
        
        # Draw label
        text = font.render(label, True, LABEL_BLACK)
        surface.blit(text, (SIDEBAR_X + 50, y_offset - 8))
        y_offset += 30
    
    # Staff legend
    y_offset += 20
    pygame.draw.line(surface, SEPARATOR_BLACK,
                     (SIDEBAR_X + 10, y_offset), (WINDOW_WIDTH - 10, y_offset), 1)
    y_offset += 20
    
    staff_title = font.render("STAFF ROLES", True, LABEL_BLACK)
    surface.blit(staff_title, (SIDEBAR_X + 20, y_offset))
    y_offset += 35
    
    # Porter (triangle)
    triangle_points = [
        (SIDEBAR_X + 30, y_offset - 8),
        (SIDEBAR_X + 22, y_offset + 8),
        (SIDEBAR_X + 38, y_offset + 8)
    ]
    pygame.draw.polygon(surface, ORANGE_PORTER, triangle_points)
    pygame.draw.polygon(surface, WALL_BLACK, triangle_points, 2)
    text = font.render("Porter", True, LABEL_BLACK)
    surface.blit(text, (SIDEBAR_X + 50, y_offset - 8))
    y_offset += 30
    
    # Backup Tech (square)
    rect = pygame.Rect(SIDEBAR_X + 22, y_offset - 8, 16, 16)
    pygame.draw.rect(surface, CYAN_BACKUP, rect)
    pygame.draw.rect(surface, WALL_BLACK, rect, 2)
    text = font.render("Backup Tech", True, LABEL_BLACK)
    surface.blit(text, (SIDEBAR_X + 50, y_offset - 8))
    y_offset += 30
    
    # Scan Tech (square)
    rect = pygame.Rect(SIDEBAR_X + 22, y_offset - 8, 16, 16)
    pygame.draw.rect(surface, PURPLE_SCAN, rect)
    pygame.draw.rect(surface, WALL_BLACK, rect, 2)
    text = font.render("Scan Tech", True, LABEL_BLACK)
    surface.blit(text, (SIDEBAR_X + 50, y_offset - 8))

def draw_dashboard(surface, stats_dict, font):
    """
    Legacy function - now redirects to draw_sidebar.
    Kept for backwards compatibility.
    """
    draw_sidebar(surface, stats_dict, font)
