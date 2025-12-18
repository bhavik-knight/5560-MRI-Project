"""
Renderer Module - PyGame Window Manager
========================================
Manages the PyGame display window and orchestrates frame rendering.
"""

import pygame
import cv2
import numpy as np
import os
from src.config import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BLACK, RECORD_INTERVAL
from src.visuals.layout import draw_floor_plan, draw_dashboard

class RenderEngine:
    """
    Manages PyGame window and rendering pipeline.
    Separates visualization from simulation logic.
    """
    
    def __init__(self, title="MRI Digital Twin", record_video=False):
        """
        Initialize PyGame window and rendering resources.
        
        Args:
            title: Window title string
            record_video: If True, records simulation to video file
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
        
        # Video recording setup
        self.record_video = record_video
        self.video_writer = None
        if record_video:
            self._init_video_writer()
            
        # Frame counter for skipping frames (optimization)
        self.frame_count = 0
    
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
    
    def _init_video_writer(self):
        """Initialize OpenCV video writer for recording."""
        try:
            # Create results directory if it doesn't exist
            os.makedirs('results', exist_ok=True)
            
            # Video file path
            video_path = 'results/simulation_video.mkv'
            
            # Video codec (XVID for .mkv)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            
            # Video parameters
            fps = 30  # Record at 30 FPS for smoother playback
            size = (WINDOW_WIDTH, WINDOW_HEIGHT)
            
            # Initialize writer
            self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, size)
            
            if self.video_writer.isOpened():
                print(f"✓ Video recording initialized: {video_path}")
                print(f"  Resolution: {WINDOW_WIDTH}×{WINDOW_HEIGHT}")
                print(f"  FPS: {fps}")
                print(f"  Codec: XVID (.mkv)")
            else:
                print("✗ Failed to initialize video writer")
                self.video_writer = None
                self.record_video = False
                
        except Exception as e:
            print(f"✗ Video recording setup failed: {e}")
            self.video_writer = None
            self.record_video = False
    
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
    
    def save_screenshot(self, filename='results/layout_screenshot.png'):
        """
        Save a screenshot of the current PyGame window.
        """
        try:
            os.makedirs('results', exist_ok=True)
            pygame.image.save(self.screen, filename)
            print(f"✓ Screenshot saved to {filename}")
        except Exception as e:
            print(f"✗ Failed to save screenshot: {e}")
        
        return True
    
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
        
        # 6. Capture frame for video recording (if enabled)
        self.frame_count += 1
        if self.record_video and self.video_writer is not None:
             # Optimization: Only record every Nth frame based on RECORD_INTERVAL
             if self.frame_count % RECORD_INTERVAL == 0:
                try:
                    # Capture screen as numpy array
                    view = pygame.surfarray.array3d(self.screen)
                    
                    # Transpose from (width, height, 3) to (height, width, 3)
                    view = view.transpose([1, 0, 2])
                    
                    # Convert RGB to BGR for OpenCV
                    frame_bgr = cv2.cvtColor(view, cv2.COLOR_RGB2BGR)
                    
                    # Write frame
                    self.video_writer.write(frame_bgr)
                except Exception as e:
                    print(f"⚠ Frame capture error: {e}")
        
        # 7. Control frame rate
        self.clock.tick(self.fps)
        
        return True
    
    def cleanup(self):
        """Clean up PyGame and video resources."""
        # Release video writer if it exists
        if self.video_writer is not None:
            try:
                self.video_writer.release()
                print("✓ Video saved successfully")
            except Exception as e:
                print(f"⚠ Error releasing video writer: {e}")
        
        pygame.quit()
    
    def get_delta_time(self):
        """
        Get time elapsed since last frame in seconds.
        Useful for time-based simulation updates.
        
        Returns:
            float: Delta time in seconds
        """
        return self.clock.get_time() / 1000.0
