import pygame
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

# Force dummy video driver for headless environments if needed,
# but we want to try recording a frame correctly.
# os.environ['SDL_VIDEODRIVER'] = 'dummy'

from src.visuals.renderer import RenderEngine
from src.config import WINDOW_WIDTH, WINDOW_HEIGHT

def capture_layout():
    """Captures a snapshot of the current MRI Digital Twin layout."""
    print("Initializing RenderEngine for layout capture...")
    
    try:
        # Initialize PyGame and create a surface
        pygame.init()
        # We need a display to render correctly with the current RenderEngine
        # If this fails because of no X server, we'll see it.
        
        # Use a hidden window if possible or just standard
        renderer = RenderEngine(title="MRI Layout Snapshot")
        
        # Prepare dummy stats for display
        stats = {
            'Sim Time': 0,
            'Patients': 0,
            'In System': 0,
            'Status': 'LAYOUT SNAPSHOT',
            'Est Clear': '0m'
        }
        
        # Render one frame
        # render_frame handles events, drawing floor plan, sprites, and sidebar
        renderer.render_frame(stats_dict=stats)
        
        # Save the screenshot
        os.makedirs('results', exist_ok=True)
        output_path = 'results/current_layout.png'
        renderer.save_screenshot(output_path)
        
        renderer.cleanup()
        print(f"Successfully captured layout to {output_path}")
        
    except Exception as e:
        print(f"Error capturing layout: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    capture_layout()
