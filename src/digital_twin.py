
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
BLUE_ROOM = (100, 149, 237) # Cornflower Blue
YELLOW_ROOM = (255, 215, 0) # Gold
TEXT_COLOR = (0, 0, 0)

def draw_floor_plan(screen, font):
    """
    Renders the MRI Department floor plan based on the specification.
    """
    screen.fill(WHITE)
    
    # Helper to render text if font exists
    def draw_text(text, x, y, color=TEXT_COLOR, rotate=0):
        if font:
            img = font.render(text, True, color)
            if rotate != 0:
                img = pygame.transform.rotate(img, rotate)
            screen.blit(img, (x, y))

    # --- Zone 1 (Public) ---
    # Grey strip at bottom (y=600 to 720)
    zone1_rect = pygame.Rect(0, 600, 1280, 120)
    pygame.draw.rect(screen, GREY_LIGHT, zone1_rect)
    
    draw_text("Zone 1: Waiting", 20, 620)

    # --- Zone 2 (The Hub) ---
    # Draw 3 small blue boxes left-center for 'Change Rooms' (Rooms 303-305)
    change_rooms = [
        ("303", pygame.Rect(50, 200, 80, 60)),
        ("304", pygame.Rect(50, 280, 80, 60)),
        ("305", pygame.Rect(50, 360, 80, 60))
    ]
    
    for label, rect in change_rooms:
        pygame.draw.rect(screen, BLUE_ROOM, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1) # Border
        draw_text(label, rect.x + 10, rect.y + 20)

    # Draw 2 small blue boxes top-center for 'Prep Rooms' (Rooms 308-309)
    prep_rooms = [
        ("308", pygame.Rect(300, 50, 80, 80)),
        ("309", pygame.Rect(400, 50, 80, 80))
    ]
    
    for label, rect in prep_rooms:
        pygame.draw.rect(screen, BLUE_ROOM, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
        draw_text(label, rect.x + 10, rect.y + 30)

    # CRITICAL: Yellow box 'Gowned Waiting' (Room 302) in center.
    gowned_rect = pygame.Rect(300, 300, 200, 150)
    pygame.draw.rect(screen, YELLOW_ROOM, gowned_rect)
    pygame.draw.rect(screen, TEXT_COLOR, gowned_rect, 1)
    
    draw_text("Gowned Waiting (302)", gowned_rect.x + 10, gowned_rect.y + 60)

    # --- Zone 3 (Control) ---
    # Vertical grey strip (x=800 to 950)
    zone3_rect = pygame.Rect(800, 0, 150, 720) 
    pygame.draw.rect(screen, GREY_DARK, zone3_rect)
    
    draw_text("Zone 3: Control", 860, 200, color=WHITE, rotate=90)

    # --- Zone 4 (Magnets) ---
    # 3T Magnet: Top-Right
    mag3t_rect = pygame.Rect(1000, 50, 250, 200)
    pygame.draw.rect(screen, GREY_LIGHT, mag3t_rect)
    pygame.draw.rect(screen, TEXT_COLOR, mag3t_rect, 2)
    draw_text("3T Magnet", 1050, 140)

    # 1.5T Magnet: Bottom-Right
    mag15t_rect = pygame.Rect(1000, 350, 250, 200)
    pygame.draw.rect(screen, GREY_LIGHT, mag15t_rect)
    pygame.draw.rect(screen, TEXT_COLOR, mag15t_rect, 2)
    draw_text("1.5T Magnet", 1050, 440)

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
    font = pygame.font.SysFont(None, 24)

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
