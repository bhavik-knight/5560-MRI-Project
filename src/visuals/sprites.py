"""
Sprites Module - Dynamic Agent Classes
=======================================
Defines Patient and Staff agents with smooth movement and state-based rendering.
"""

import pygame
import math
from src.config import (
    GREY_ARRIVING, BLUE_CHANGING, YELLOW_PREPPED, GREEN_SCANNING,
    ORANGE_PORTER, CYAN_BACKUP, PURPLE_SCAN,
    BLACK, AGENT_SPEED
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
        self.speed = speed if speed is not None else AGENT_SPEED['patient']
    
    def move_to(self, target_x, target_y):
        """Set new target position for smooth movement."""
        self.target_x = float(target_x)
        self.target_y = float(target_y)
    
    def update(self):
        """
        Update agent position - moves smoothly toward target.
        Called every frame by pygame sprite group.
        """
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > self.speed:
            # Move toward target at constant speed
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
        super().__init__(x, y, GREY_ARRIVING, speed=AGENT_SPEED['patient'])
        self.p_id = p_id
        self.state = 'arriving'
    
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
            'changing': BLUE_CHANGING,
            'prepped': YELLOW_PREPPED,
            'scanning': GREEN_SCANNING,
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
        }
        color = role_colors.get(role, CYAN_BACKUP)
        
        super().__init__(x, y, color, speed=AGENT_SPEED['staff'])
        self.role = role
        self.busy = False  # Track if staff is currently assisting a patient
        self.home_x = x
        self.home_y = y
    
    def return_home(self):
        """Move staff back to their assigned home position."""
        self.move_to(self.home_x, self.home_y)
    
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
