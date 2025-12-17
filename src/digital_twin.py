
import pygame
import sys

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60


# Colors
WHITE = (255, 255, 255)
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
    pygame.draw.rect(surface, (0, 0, 0), rect, 2) # Black border width 2
    
    if font:
        lines = label_text.split('\n')
        # Calculate total height for vertical centering
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        start_y = rect.centery - (total_height / 2)
        
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(centerx=rect.centerx, top=start_y + (i * line_height))
            surface.blit(text_surf, text_rect)

def draw_floor_plan(screen, font):
    """
    Renders the MRI Department floor plan based on the precise coordinate map.
    """
    screen.fill(WHITE)
    
    # --- Zone 1 (Public Corridor) ---
    # Rect: (0, 600, 1280, 120) [Bottom Strip]. Color: Light Grey.
    draw_room(screen, pygame.Rect(0, 600, 1280, 120), GREY_LIGHT, "ZONE 1: PUBLIC / SUB-WAITING", font)

    # --- Zone 4 (The Magnets - Right Side) ---
    # 3T Magnet (Room 319): (950, 50, 300, 250) [Top Right]
    draw_room(screen, pygame.Rect(950, 50, 300, 250), CYAN_MAG, "3T MRI\n(Room 319)", font)
    
    # 1.5T Magnet (Room 315): (950, 350, 300, 250) [Bottom Right]
    draw_room(screen, pygame.Rect(950, 350, 300, 250), CYAN_MAG, "1.5T MRI\n(Room 315)", font)

    # --- Zone 3 (Control Room - Strip) ---
    # Rect: (820, 50, 130, 550) [Vertical Strip]. Color: Dark Grey.
    # Note: Text centering might look odd on narrow vertical strip if text is wide, 
    # but specific requirement was label "ZONE 3\nCONTROL".
    draw_room(screen, pygame.Rect(820, 50, 130, 550), GREY_DARK, "ZONE 3\nCONTROL", font)

    # --- Zone 2 (The Hub - Left/Center) ---
    
    # Left Wall (Change Rooms)
    # Change 305 (Big): (20, 20, 120, 100)
    draw_room(screen, pygame.Rect(20, 20, 120, 100), BLUE_TEAL, "Change\n(Big)", font)
    
    # Change 304 (Standard): (20, 120, 80, 70)
    draw_room(screen, pygame.Rect(20, 120, 80, 70), BLUE_TEAL, "Chg 1", font)
    
    # Change 303 (Standard): (20, 190, 80, 70)
    draw_room(screen, pygame.Rect(20, 190, 80, 70), BLUE_TEAL, "Chg 2", font)

    # Top Wall (Sanitation & Prep)
    # Washrooms (306/307): (150, 20, 80, 100)
    draw_room(screen, pygame.Rect(150, 20, 80, 100), PINK_WR, "W/R", font)
    
    # IV Prep 308: (300, 20, 150, 120)
    draw_room(screen, pygame.Rect(300, 20, 150, 120), ORANGE_PREP, "Prep 1\n(308)", font)
    
    # IV Prep 309: (460, 20, 150, 120)
    draw_room(screen, pygame.Rect(460, 20, 150, 120), ORANGE_PREP, "Prep 2\n(309)", font)

    # Center Buffer (The Critical Resource)
    # Gowned Waiting (302): (150, 200, 250, 150)
    draw_room(screen, pygame.Rect(150, 200, 250, 150), YELLOW_ROOM, "GOWNED WAIT\n(Buffer 302)", font)

    # Center Obstacle
    # Holding Transfer (311): (350, 350, 200, 200)
    draw_room(screen, pygame.Rect(350, 350, 200, 200), GREY_HOLDING, "Holding\n(311)", font)

def main():
    pygame.init()
    
    # Attempt to initialize fonts, proceed without them if it fails
    font = None
    try:
        if pygame.font:
            pygame.font.init()
            font = pygame.font.SysFont(None, 24)
    except (ImportError, TypeError, AttributeError, NotImplementedError) as e:
        print(f"Warning: Font initialization failed ({e}). Running without text labels.")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MRI Digital Twin - Zone 1-4 Layout")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        draw_floor_plan(screen, font)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
