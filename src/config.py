"""
Shared Configuration Module for MRI Digital Twin
================================================
This module contains all constants, colors, and coordinates used across
the simulation, visualization, and analysis modules.

NO DEPENDENCIES - This file should not import any other modules.
"""

# ============================================================================
# VISUAL CONSTANTS
# ============================================================================

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 720
FPS = 60

# ============================================================================
# RGB COLORS - Agent States
# ============================================================================

# Patient State Colors
GREY_ARRIVING = (180, 180, 180)      # Arriving in Zone 1
BLUE_CHANGING = (0, 128, 128)        # Changing (Teal)
YELLOW_PREPPED = (255, 215, 0)       # Prepped/Waiting (Gold)
GREEN_SCANNING = (0, 255, 0)         # Scanning (Bright Green)
NEON_YELLOW = (255, 255, 0)          # High-visibility yellow

# Staff Colors
ORANGE_PORTER = (255, 140, 0)        # Porter (Dark Orange)
CYAN_BACKUP = (0, 255, 255)          # Backup Tech (Cyan)
PURPLE_SCAN = (128, 0, 128)          # Scan Tech (Purple)

# Room/Zone Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY_LIGHT = (220, 220, 220)
GREY_DARK = (150, 150, 150)
GREY_HOLDING = (180, 180, 180)
BLUE_TEAL = (0, 128, 128)
PINK_WR = (255, 182, 193)
ORANGE_PREP = (255, 165, 0)
CYAN_MAG = (224, 255, 255)
YELLOW_ROOM = (255, 215, 0)

# ============================================================================
# LAYOUT COORDINATES (pygame.Rect format: x, y, width, height)
# ============================================================================

ROOM_COORDINATES = {
    # Zone 1: Public Corridor (Bottom)
    'zone1': (20, 600, 1560, 100),
    
    # Zone 2: The Hub (Left/Center)
    'change_1': (20, 20, 120, 100),      # Big/Accessible
    'change_2': (20, 120, 80, 70),       # Standard
    'change_3': (20, 190, 80, 70),       # Standard
    
    'washroom_1': (150, 20, 60, 60),     # Accessible
    'washroom_2': (220, 20, 60, 60),     # Standard
    
    'prep_1': (300, 20, 150, 120),       # IV Prep Room 308
    'prep_2': (460, 20, 150, 120),       # IV Prep Room 309
    
    'gowned_waiting': (150, 200, 250, 150),  # CRITICAL: The Buffer (Room 302)
    'holding': (350, 350, 200, 200),     # Holding/Transfer (Room 311)
    
    # Zone 3: Control (Vertical Strip)
    'control': (820, 50, 130, 550),
    
    # Zone 4: Magnets (Right Side)
    'magnet_3t': (950, 50, 300, 250),    # 3T MRI (Room 319)
    'magnet_15t': (950, 350, 300, 250),  # 1.5T MRI (Room 315)
    
    # Building Border
    'building': (10, 10, 1580, 700),
}

# Agent Spawn/Target Positions (x, y tuples)
AGENT_POSITIONS = {
    'zone1_center': (800, 650),
    'change_1_center': (80, 70),
    'change_2_center': (60, 155),
    'change_3_center': (60, 225),
    'prep_1_center': (375, 80),
    'prep_2_center': (535, 80),
    'gowned_waiting_center': (275, 275),
    'magnet_3t_center': (1100, 175),
    'magnet_15t_center': (1100, 475),
    'exit': (1580, 650),
    
    # Staff Staging Positions
    'porter_home': (750, 650),
    'backup_staging': (325, 275),
    'scan_staging_3t': (1020, 175),
    'scan_staging_15t': (1020, 475),
}

# ============================================================================
# SIMULATION CONSTANTS
# ============================================================================

# Time Scaling
SIM_SPEED = 0.5  # 1 simulation minute = 0.5 real seconds

# Staffing
STAFF_COUNT = {
    'porter': 1,
    'backup_tech': 2,
    'scan_tech': 2,
}

# Resource Capacities
RESOURCE_CAPACITY = {
    'magnet': 1,           # Only 1 patient can scan at a time (per magnet)
    'prep_rooms': 2,       # 2 IV Prep rooms (308, 309)
    'change_rooms': 3,     # 3 Change rooms (303, 304, 305)
    'gowned_waiting': 3,   # Max 3 patients in buffer (Source: Floor Plan)
}

# Agent Movement
AGENT_SPEED = {
    'patient': 3.0,        # pixels per frame
    'staff': 4.0,          # pixels per frame (staff move faster)
}

# ============================================================================
# DISTRIBUTION PARAMETERS (From Sheet 4 - Source 41)
# ============================================================================

# All times in MINUTES
# Format: (min, mode, max) for triangular distribution

PROCESS_TIMES = {
    # Screening & Consent
    'screening': (2, 3, 5),
    
    # Change/Gown
    'change': (2, 3.5, 5),
    
    # IV Setup (if needed)
    'iv_setup': (1, 2.5, 4),
    'iv_difficult': (3, 5, 8),  # If difficult IV
    
    # Scan Duration
    'scan': (18, 22, 26),
    
    # Bed Flip Time
    'bed_flip_current': 5,      # Current state (constant)
    'bed_flip_future': 1,       # Future state goal (constant)
    
    # Arrival Schedule
    'inter_arrival': 30,        # New patient every 30 minutes
    'arrival_noise': (-5, 0, 5),  # Random variation
}

# Probabilities
PROBABILITIES = {
    'needs_iv': 0.70,           # 70% of patients need IV
    'difficult_iv': 0.15,       # 15% of IVs are difficult
}

# ============================================================================
# ROOM LABELS (For Visualization)
# ============================================================================

ROOM_LABELS = {
    'zone1': 'ZONE 1: PUBLIC CORRIDOR',
    'change_1': 'Change 1',
    'change_2': 'Change 2',
    'change_3': 'Change 3',
    'washroom_1': 'WR 1',
    'washroom_2': 'WR 2',
    'prep_1': 'IV Prep 1',
    'prep_2': 'IV Prep 2',
    'gowned_waiting': 'GOWNED WAIT\n(Max 3)',
    'holding': 'Holding',
    'control': 'CONTROL',
    'magnet_3t': '3T MRI (Source 1)',
    'magnet_15t': '1.5T MRI',
}

# ============================================================================
# ROOM COLORS (For Visualization)
# ============================================================================

ROOM_COLORS = {
    'zone1': GREY_LIGHT,
    'change_1': BLUE_TEAL,
    'change_2': BLUE_TEAL,
    'change_3': BLUE_TEAL,
    'washroom_1': PINK_WR,
    'washroom_2': PINK_WR,
    'prep_1': ORANGE_PREP,
    'prep_2': ORANGE_PREP,
    'gowned_waiting': YELLOW_ROOM,
    'holding': GREY_HOLDING,
    'control': GREY_DARK,
    'magnet_3t': CYAN_MAG,
    'magnet_15t': CYAN_MAG,
}
