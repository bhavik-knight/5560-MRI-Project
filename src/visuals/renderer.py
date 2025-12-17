"""
Renderer Module - PyGame Window Manager
========================================
Manages the PyGame display window and orchestrates frame rendering.
"""

import pygame
from src.config import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BLACK
from src.visuals.layout import draw_floor_plan, draw_dashboard

class RenderEngine:
    """
    Manages PyGame window and rendering pipeline.
    Separates visualization from simulation logic.
    """
    
    def __init__(self, title="MRI Digital Twin"):
        """
        Initialize PyGame window and rendering resources.
        
        Args:
            title: Window title string
        """
        pygame.init()
        
        # Create window
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(title)
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
        self.fps = FPS
        
        # Initialize fonts
        self.font_room = None
        self.font_zone = None
        self._init_fonts()
        
        # Sprite group for agents
        self.all_sprites = pygame.sprite.Group()
    
    def _init_fonts(self):
        """Initialize fonts with fallback handling."""
        try:
            pygame.font.init()
            # Medical aesthetic: crisp, small fonts (size 14)
            self.font_room = pygame.font.SysFont('Arial', 14, bold=False)
            self.font_zone = pygame.font.SysFont('Arial', 18, bold=True)
            print("✓ Fonts loaded successfully (Arial)")
        except Exception as e:
            print(f"⚠ Font loading failed: {e}")
            try:
                # Fallback to default pygame font
                self.font_room = pygame.font.Font(None, 16)
                self.font_zone = pygame.font.Font(None, 22)
                print("✓ Fonts loaded successfully (Default)")
            except Exception as e2:
                print(f"✗ All font initialization failed: {e2}")
    
    def add_sprite(self, sprite):
        """
        Add an agent sprite to the rendering group.
        
        Args:
            sprite: Agent object (Patient or Staff)
        """
        self.all_sprites.add(sprite)
    
    def remove_sprite(self, sprite):
        """
        Remove an agent sprite from the rendering group.
        
        Args:
            sprite: Agent object to remove
        """
        self.all_sprites.remove(sprite)
        sprite.kill()
    
    def render_frame(self, stats_dict=None):
        """
        Render a single frame.
        
        Args:
            stats_dict: Optional dictionary of statistics to display
                       e.g., {'Sim Time': 45, 'Patients': 3}
        
        Returns:
            bool: False if user closed window, True otherwise
        """
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        
        # 1. Draw static floor plan (fills background with corridor grey)
        draw_floor_plan(self.screen, self.font_room, self.font_zone)
        
        # 2. Update agent positions
        self.all_sprites.update()
        
        # 3. Draw all agents
        for sprite in self.all_sprites:
            sprite.draw(self.screen)
        
        # 4. Draw sidebar with stats and legend
        if self.font_room:
            from src.visuals.layout import draw_sidebar
            draw_sidebar(self.screen, stats_dict, self.font_room)
        
        # 5. Flip display
        pygame.display.flip()
        
        # 6. Control frame rate
        self.clock.tick(self.fps)
        
        return True
    
    def cleanup(self):
        """Clean up PyGame resources."""
        pygame.quit()
    
    def get_delta_time(self):
        """
        Get time elapsed since last frame in seconds.
        Useful for time-based simulation updates.
        
        Returns:
            float: Delta time in seconds
        """
        return self.clock.get_time() / 1000.0
