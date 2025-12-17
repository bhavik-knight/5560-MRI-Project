
import pygame
import sys

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY_LIGHT = (220, 220, 220)
GREY_DARK = (150, 150, 150)
GREY_HOLDING = (180, 180, 180)
BLUE_TEAL = (0, 128, 128)      # Teal
PINK_WR = (255, 182, 193)      # Pink
ORANGE_PREP = (255, 165, 0)    # Light Orange (using Orange)
CYAN_MAG = (224, 255, 255)     # Light Cyan
YELLOW_ROOM = (255, 215, 0)    # Gold
TEXT_COLOR = (0, 0, 0)

def draw_room(surface, rect, color, label_text, font):
    """
    Helper to draw a room with a border and centered text.
    Handles newline characters in label_text.
    """
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, BLACK, rect, 2) # Black border width 2
    
    if font and label_text:
        lines = label_text.split('\n')
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        
        # Center the block of text
        start_y = rect.centery - (total_height / 2)
        
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(centerx=rect.centerx, top=start_y + (i * line_height))
            surface.blit(text_surf, text_rect)

def draw_floor_plan(screen, font_room, font_zone):
    """
    Renders the MRI Department floor plan based on the precise coordinate map.
    """
    screen.fill(WHITE)
    
    # Draw 'Building' Border
    # Encapsulates Zones 1, 2, 3, 4 into a single 'Building'.
    # Width=5. Rect: (10, 10, 1260, 700)
    pygame.draw.rect(screen, BLACK, (10, 10, 1260, 700), 5)

    # --- Zone 1 (Public Corridor) ---
    draw_room(screen, pygame.Rect(20, 600, 1240, 100), GREY_LIGHT, "ZONE 1: PUBLIC CORRIDOR", font_zone)

    # --- Zone 4 (The Magnets - Right Side) ---
    # 3T Magnet (Room 319): (950, 50, 300, 250) [Top Right]
    draw_room(screen, pygame.Rect(950, 50, 300, 250), CYAN_MAG, "3T MRI (Source 1)", font_room)
    
    # 1.5T Magnet (Room 315): (950, 350, 300, 250) [Bottom Right]
    draw_room(screen, pygame.Rect(950, 350, 300, 250), CYAN_MAG, "1.5T MRI", font_room)

    # --- Zone 3 (Control Room - Strip) ---
    draw_room(screen, pygame.Rect(820, 50, 130, 550), GREY_DARK, "CONTROL", font_zone)

    # --- Zone 2 (The Hub - Left/Center) ---
    
    # Left Wall (Change Rooms)
    draw_room(screen, pygame.Rect(20, 20, 120, 100), BLUE_TEAL, "Change 1", font_room)
    draw_room(screen, pygame.Rect(20, 120, 80, 70), BLUE_TEAL, "Change 2", font_room)
    draw_room(screen, pygame.Rect(20, 190, 80, 70), BLUE_TEAL, "Change 3", font_room)

    # Top Wall (Sanitation & Prep) - UPDATED WITH TWO WASHROOMS
    # Washroom 306 (Accessible): Right of Change Rooms - STANDARDIZED
    draw_room(screen, pygame.Rect(150, 20, 60, 60), PINK_WR, "WR 1", font_room)
    
    # Washroom 307 (Standard): Right of WR 1 - STANDARDIZED
    draw_room(screen, pygame.Rect(220, 20, 60, 60), PINK_WR, "WR 2", font_room)
    
    # IV Prep 308: Shifted right to x=300 to accommodate washrooms
    draw_room(screen, pygame.Rect(300, 20, 150, 120), ORANGE_PREP, "IV Prep 1", font_room)
    
    # IV Prep 309: Shifted right
    draw_room(screen, pygame.Rect(460, 20, 150, 120), ORANGE_PREP, "IV Prep 2", font_room)

    # Center Buffer (The Critical Resource)
    draw_room(screen, pygame.Rect(150, 200, 250, 150), YELLOW_ROOM, "GOWNED WAIT\n(Max 3)", font_room)

    # Center Obstacle
    draw_room(screen, pygame.Rect(350, 350, 200, 200), GREY_HOLDING, "Holding", font_room)

def main():
    pygame.init()
    
    # Attempt to initialize fonts
    font_room = None
    font_zone = None
    try:
        if pygame.font:
            pygame.font.init()
            # "SysFont('Arial', 16, bold=True) for room labels"
            font_room = pygame.font.SysFont('Arial', 16, bold=True)
            # "larger font for Zone labels"
            font_zone = pygame.font.SysFont('Arial', 24, bold=True) 
    except (ImportError, TypeError, AttributeError, NotImplementedError) as e:
        print(f"Warning: Font initialization failed ({e}). Running without text labels.")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MRI Digital Twin - Layout")
    
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        draw_floor_plan(screen, font_room, font_zone)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
