
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
    
    # --- Zone 1 (Public) ---
    # Grey strip at bottom (y=600 to 720)
    zone1_rect = pygame.Rect(0, 600, 1280, 120)
    pygame.draw.rect(screen, GREY_LIGHT, zone1_rect)
    
    text_z1 = font.render("Zone 1: Waiting", True, TEXT_COLOR)
    screen.blit(text_z1, (20, 620))

    # --- Zone 2 (The Hub) ---
    # Main central area (x=0 to 800, y=0 to 600)
    # Background already White from fill.
    # Optional border or label?
    # text_z2 = font.render("Zone 2: The Hub", True, (200, 200, 200))
    # screen.blit(text_z2, (10, 10))

    # Draw 3 small blue boxes left-center for 'Change Rooms' (Rooms 303-305)
    # Approx coords: x ~ 50-150, centered vertically in Zone 2 (y ~ 300)
    change_rooms = [
        ("303", pygame.Rect(50, 200, 80, 60)),
        ("304", pygame.Rect(50, 280, 80, 60)),
        ("305", pygame.Rect(50, 360, 80, 60))
    ]
    
    for label, rect in change_rooms:
        pygame.draw.rect(screen, BLUE_ROOM, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1) # Border
        # Label
        lbl = font.render(label, True, TEXT_COLOR)
        screen.blit(lbl, (rect.x + 10, rect.y + 20))

    # Draw 2 small blue boxes top-center for 'Prep Rooms' (Rooms 308-309)
    # Approx coords: x ~ 300-400, y ~ 50
    prep_rooms = [
        ("308", pygame.Rect(300, 50, 80, 80)),
        ("309", pygame.Rect(400, 50, 80, 80))
    ]
    
    for label, rect in prep_rooms:
        pygame.draw.rect(screen, BLUE_ROOM, rect)
        pygame.draw.rect(screen, TEXT_COLOR, rect, 1)
        lbl = font.render(label, True, TEXT_COLOR)
        screen.blit(lbl, (rect.x + 10, rect.y + 30))

    # CRITICAL: Yellow box 'Gowned Waiting' (Room 302) in center.
    # Center of Zone 2 (800x600) is 400, 300.
    gowned_rect = pygame.Rect(300, 300, 200, 150)
    pygame.draw.rect(screen, YELLOW_ROOM, gowned_rect)
    pygame.draw.rect(screen, TEXT_COLOR, gowned_rect, 1)
    
    lbl_gw = font.render("Gowned Waiting (302)", True, TEXT_COLOR)
    screen.blit(lbl_gw, (gowned_rect.x + 10, gowned_rect.y + 60))

    # --- Zone 3 (Control) ---
    # Vertical grey strip (x=800 to 950)
    zone3_rect = pygame.Rect(800, 0, 150, 720) # Extends full height? Or stop at Zone 1? 
    # Prompt says "x=800 to 950", implies full height, but usually Control is next to Magnet.
    # Let's draw it full height but overlay Zone 1 if needed.
    # Actually Zone 1 is y=600+. Control usually looks into Magnet.
    pygame.draw.rect(screen, GREY_DARK, zone3_rect)
    
    text_z3 = font.render("Zone 3: Control", True, WHITE)
    # Rotate text for vertical strip?
    text_z3 = pygame.transform.rotate(text_z3, 90)
    screen.blit(text_z3, (860, 200))

    # --- Zone 4 (Magnets) ---
    # Right side (x=950 to 1280)
    # Background White (or distinctive?)
    
    # 3T Magnet: Top-Right
    mag3t_rect = pygame.Rect(1000, 50, 250, 200)
    pygame.draw.rect(screen, GREY_LIGHT, mag3t_rect)
    pygame.draw.rect(screen, TEXT_COLOR, mag3t_rect, 2)
    lbl_3t = font.render("3T Magnet", True, TEXT_COLOR)
    screen.blit(lbl_3t, (1050, 140))

    # 1.5T Magnet: Bottom-Right
    mag15t_rect = pygame.Rect(1000, 350, 250, 200)
    pygame.draw.rect(screen, GREY_LIGHT, mag15t_rect)
    pygame.draw.rect(screen, TEXT_COLOR, mag15t_rect, 2)
    lbl_15t = font.render("1.5T Magnet", True, TEXT_COLOR)
    screen.blit(lbl_15t, (1050, 440))

def main():
    pygame.init()
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
