"""
Sprites Module - Dynamic Agent Classes
=======================================
Defines Patient and Staff agents with smooth movement and state-based rendering.
"""

import pygame
import math
import src.config as config
from src.config import (
    GREY_ARRIVING, BLUE_CHANGING, YELLOW_PREPPED, GREEN_SCANNING,
    ORANGE_PORTER, CYAN_BACKUP, PURPLE_SCAN, BLUE_ADMIN,
    BLACK, AGENT_SPEED, GREY_DARK,
    PURPLE_REGISTERED
)

class Agent(pygame.sprite.Sprite):
    """
    Base class for all moving agents (patients and staff).
    Handles smooth interpolated movement between positions.
    """
    
    def __init__(self, x, y, color, speed=None):
        """
        Initialize agent.
        
        Args:
            x, y: Starting position
            color: RGB tuple
            speed: Movement speed in pixels/frame (uses config default if None)
        """
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(x)
        self.target_y = float(y)
        self.color = color
        # Ensure speed is taken from config if not provided
        self.speed = speed if speed is not None else AGENT_SPEED['patient']
    
    def move_to(self, target_x, target_y):
        """Set new target position for smooth movement."""
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        
        # In headless mode, movement is instantaneous
        if config.HEADLESS:
            self.x = self.target_x
            self.y = self.target_y
    
    def update(self):
        """
        Update agent position - moves smoothly toward target.
        Called every frame by pygame sprite group.
        
        Physics: (target - current) * speed (normalized)
        """
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > self.speed:
            # Move toward target at constant speed
            # Calculate position increments based on: (target - current).normalized() * speed
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
        else:
            # Snap to target when close enough
            self.x = self.target_x
            self.y = self.target_y
    
    def is_at_target(self):
        """Check if agent has reached target position."""
        return abs(self.x - self.target_x) < 1 and abs(self.y - self.target_y) < 1
    
    def draw(self, surface):
        """Override in subclasses to define visual appearance."""
        if config.HEADLESS:
            return
        pass


class Patient(Agent):
    """
    Patient agent - rendered as a circle.
    Color changes based on state (arriving, changing, prepped, scanning).
    """
    
    def __init__(self, p_id, x, y):
        """
        Initialize patient.
        
        Args:
            p_id: Unique patient identifier
            x, y: Starting position
        """
        # Pass speed from config explicitly
        super().__init__(x, y, GREY_ARRIVING, speed=AGENT_SPEED['patient'])
        self.p_id = p_id
        self.state = 'arriving'
        
        # Comprehensive Data Collection (User Request - Step 3)
        self.patient_type = 'outpatient' # Default
        self.has_iv = False
        self.is_difficult = False
        self.arrival_time = 0.0
        
        # Metrics Storage
        self.metrics = {}      # Stage -> Duration
        self.timestamps = {}   # Stage -> Start Time
    
    def start_timer(self, stage, now):
        """Record start time for a simulation stage."""
        self.timestamps[stage] = now
        
    def stop_timer(self, stage, now):
        """Calculate and store duration for a simulation stage."""
        if stage in self.timestamps:
            start_time = self.timestamps.pop(stage)
            duration = now - start_time
            self.metrics[stage] = self.metrics.get(stage, 0.0) + duration
            return duration
        return 0.0
    
    def set_state(self, state):
        """
        Update patient state and color.
        
        Args:
            state: One of 'arriving', 'changing', 'prepped', 'scanning'
        """
        self.state = state
        
        # Update color based on state
        state_colors = {
            'arriving': GREY_ARRIVING,
            'registered': PURPLE_REGISTERED,
            'changing': BLUE_CHANGING,
            'prepped': YELLOW_PREPPED,
            'scanning': GREEN_SCANNING,
            'exited': GREY_DARK,
        }
        self.color = state_colors.get(state, GREY_ARRIVING)
    
    def draw(self, surface):
        """Draw patient as a filled circle with black outline."""
        center = (int(self.x), int(self.y))
        radius = 8
        
        # Fill
        pygame.draw.circle(surface, self.color, center, radius)
        
        # Outline
        pygame.draw.circle(surface, BLACK, center, radius, 1)


class Staff(Agent):
    """
    Staff agent - shape depends on role.
    - Porter: Triangle (orange)
    - Backup Tech: Square (cyan)
    - Scan Tech: Square (purple)
    """
    
    def __init__(self, role, x, y):
        """
        Initialize staff member.
        
        Args:
            role: One of 'porter', 'backup', 'scan'
            x, y: Starting position
        """
        # Set color based on role
        role_colors = {
            'porter': ORANGE_PORTER,
            'backup': CYAN_BACKUP,
            'scan': PURPLE_SCAN,
            'admin': BLUE_ADMIN,
        }
        color = role_colors.get(role, CYAN_BACKUP)
        
        # Pass speed from config explicitly
        super().__init__(x, y, color, speed=AGENT_SPEED['staff'])
        self.role = role
        self.busy = False  # Track if staff is currently assisting a patient
        
        # Home position for returning when idle (e.g., Backup Techs stay near IV Prep)
        self.home_x = x
        self.home_y = y
    
    def return_home(self):
        """Move staff back to their assigned home position."""
        self.move_to(self.home_x, self.home_y)
        
    def return_to_base(self):
        """Alias for return_home to satisfy verification requirements."""
        self.return_home()

    def go_to_break(self):
        """Move sprite to BREAK_ROOM_LOC."""
        from src.config import AGENT_POSITIONS
        self.move_to(*AGENT_POSITIONS['break_room_center'])

    def cover_position(self, target_pos_or_x, target_y=None):
        """Move sprite to the station they are covering."""
        if target_y is not None:
            self.move_to(target_pos_or_x, target_y)
        else:
            self.move_to(*target_pos_or_x)
    
    def draw(self, surface):
        """Draw staff member - shape depends on role. Apply offset when busy to avoid Z-fighting."""
        # Apply visual offset when busy (co-located with patient)
        offset_x = 15 if self.busy else 0
        offset_y = 15 if self.busy else 0
        
        x, y = int(self.x + offset_x), int(self.y + offset_y)
        
        if self.role == 'porter':
            # Triangle pointing up
            points = [
                (x, y - 10),      # Top point
                (x - 8, y + 8),   # Bottom left
                (x + 8, y + 8)    # Bottom right
            ]
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, BLACK, points, 2)
        
        else:
            # Square (for backup and scan techs)
            size = 16
            rect = pygame.Rect(x - size//2, y - size//2, size, size)
            pygame.draw.rect(surface, self.color, rect)
            pygame.draw.rect(surface, BLACK, rect, 2)
