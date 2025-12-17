
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
    Renders the MRI Department floor plan based on the provided architectural diagram.
    Layout:
    - Zone 1 (Corridor): Bottom full width.
    - Left Column: Change Rooms (303-305).
    - Center-Left: Gowned Waiting (302).
    - Center-Top: IV Prep (308, 309).
    - Center-Mid: Holding (311).
    - Right-Center: Zone 3 Control Rooms.
    - Far Right: Zone 4 Magnets.
    """
    screen.fill(WHITE)
    
    # Helper to render text if font exists
    def draw_text(text, x, y, color=TEXT_COLOR, rotate=0, small=False):
        if font:
            # Simple scale hack: if small, just use same font but maybe render differently? 
            # Pygame font size is fixed at init. We'll just print.
            img = font.render(text, True, color)
            if rotate != 0:
                img = pygame.transform.rotate(img, rotate)
            screen.blit(img, (x, y))

    # --- Zone 1 (Public Corridor) ---
    # Bottom strip
    zone1_rect = pygame.Rect(0, 620, 1280, 100)
    pygame.draw.rect(screen, GREY_LIGHT, zone1_rect)
    pygame.draw.rect(screen, TEXT_COLOR, zone1_rect, 1)
    draw_text("ZONE 1: Public Corridor (3302)", 500, 660)

    # --- Zone 2 (The Hub) ---
    
    # 1. Change Rooms (Left Wall, Vertical Stack)
    # Rooms 305 (Top), 304, 303 (Bottom) roughly x=50
    change_rooms = [
        ("Change 305", pygame.Rect(50, 100, 120, 80)),
        ("Change 304", pygame.Rect(50, 180, 120, 60)),
        ("Change 303", pygame.Rect(50, 240, 120, 60))
    ]
    for label, rect in change_rooms:
        pygame.draw.rect(screen, BLUE_ROOM, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
        draw_text(label, rect.x + 5, rect.y + 20)

    # 2. Gowned Waiting (302)
    # Large area to the right of Change rooms
    gowned_rect = pygame.Rect(170, 100, 200, 200)
    pygame.draw.rect(screen, YELLOW_ROOM, gowned_rect)
    pygame.draw.rect(screen, TEXT_COLOR, gowned_rect, 1)
    draw_text("Gowned Waiting", gowned_rect.x + 20, gowned_rect.y + 80)
    draw_text("(302)", gowned_rect.x + 70, gowned_rect.y + 100)

    # 3. IV Prep (308, 309)
    # Top Center
    prep_rooms = [
        ("IV Prep 308", pygame.Rect(400, 50, 150, 120)),
        ("IV Prep 309", pygame.Rect(550, 50, 150, 120))
    ]
    for label, rect in prep_rooms:
        pygame.draw.rect(screen, BLUE_ROOM, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
        draw_text(label, rect.x + 20, rect.y + 50)

    # 4. Holding Transfer (311)
    # Center, below Prep
    holding_rect = pygame.Rect(400, 200, 300, 200)
    pygame.draw.rect(screen, GREY_LIGHT, holding_rect) # Maybe grey for holding?
    pygame.draw.rect(screen, TEXT_COLOR, holding_rect, 1)
    draw_text("Holding / Transfer", holding_rect.x + 60, holding_rect.y + 80)
    draw_text("(311)", holding_rect.x + 120, holding_rect.y + 100)

    # --- Zone 3 (Control) ---
    # Strip between holding and magnets
    # Control 320 (Top) and 314 (Bottom)
    c_rooms = [
        ("Control 320", pygame.Rect(800, 50, 100, 250)),
        ("Control 314", pygame.Rect(800, 350, 100, 250))
    ]
    for label, rect in c_rooms:
        pygame.draw.rect(screen, GREY_DARK, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
        # Vertical text?
        draw_text(label, rect.x + 10, rect.y + 100, color=WHITE, rotate=90)
    
    # Label Zone 3 generally
    # draw_text("ZONE 3", 830, 310, rotate=90)


    # --- Zone 4 (Magnets) ---
    # Top Right: 3T MRI (319)
    mag3t_rect = pygame.Rect(900, 50, 350, 250)
    pygame.draw.rect(screen, GREY_LIGHT, mag3t_rect)
    pygame.draw.rect(screen, TEXT_COLOR, mag3t_rect, 2)
    draw_text("3.0T MRI (319)", 920, 70)
    draw_text("ZONE 4", 920, 100)
    # Magnet Box
    pygame.draw.rect(screen, WHITE, (1050, 100, 100, 150), 1)
    draw_text("Magnet", 1070, 160)

    # Bottom Right: 1.5T MRI (315)
    mag15t_rect = pygame.Rect(900, 350, 350, 250)
    pygame.draw.rect(screen, GREY_LIGHT, mag15t_rect)
    pygame.draw.rect(screen, TEXT_COLOR, mag15t_rect, 2)
    draw_text("1.5T MRI (315)", 920, 370)
    draw_text("ZONE 4", 920, 400)
    # Magnet Box
    pygame.draw.rect(screen, WHITE, (1050, 400, 100, 150), 1)
    draw_text("Magnet", 1070, 460)

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
