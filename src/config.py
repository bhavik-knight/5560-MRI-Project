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
WINDOW_HEIGHT = 800
SIMULATION_AREA_WIDTH = 1200  # Floor plan area
SIDEBAR_X = 1200              # Sidebar starts here
SIDEBAR_WIDTH = 400           # Sidebar width
FPS = 60

# Medical White Color Scheme
MEDICAL_WHITE = (255, 255, 255)      # All rooms
CORRIDOR_GREY = (230, 230, 230)      # Background
WALL_BLACK = (0, 0, 0)               # Room borders
LABEL_BLACK = (0, 0, 0)              # Text
SEPARATOR_BLACK = (0, 0, 0)          # Sidebar divider

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
    'zone1': (20, 680, 1160, 100),
    
    # Zone 2: The Hub (Left/Center)
    'change_1': (20, 20, 100, 90),       # Big/Accessible
    'change_2': (20, 110, 70, 60),       # Standard
    'change_3': (20, 170, 70, 60),       # Standard
    
    'washroom_1': (130, 20, 50, 50),     # Accessible
    'washroom_2': (190, 20, 50, 50),     # Standard
    
    'prep_1': (250, 20, 130, 100),       # IV Prep Room 308
    'prep_2': (390, 20, 130, 100),       # IV Prep Room 309
    
    'gowned_waiting': (130, 180, 220, 130),  # CRITICAL: The Buffer (Room 302)
    'holding': (300, 320, 180, 180),     # Holding/Transfer (Room 311)
    
    # Zone 3: Control (Vertical Strip)
    'control': (700, 50, 110, 480),
    
    # Zone 4: Magnets (Right Side)
    'magnet_3t': (820, 50, 260, 220),    # 3T MRI (Room 319)
    'magnet_15t': (820, 300, 260, 220),  # 1.5T MRI (Room 315)
    
    # Building Border
    'building': (10, 10, 1180, 770),
}

# Agent Spawn/Target Positions (x, y tuples)
AGENT_POSITIONS = {
    'zone1_center': (600, 730),
    'change_1_center': (70, 65),
    'change_2_center': (55, 140),
    'change_3_center': (55, 200),
    'prep_1_center': (315, 70),
    'prep_2_center': (455, 70),
    'gowned_waiting_center': (240, 245),
    'magnet_3t_center': (950, 160),
    'magnet_15t_center': (950, 410),
    'exit': (1180, 730),
    
    # Staff Staging Positions
    'porter_home': (550, 730),
    'backup_staging': (280, 245),
    'scan_staging_3t': (870, 160),
    'scan_staging_15t': (870, 410),
}

# Waiting Areas (Rectangles for spatial scatter: x_min, x_max, y_min, y_max)
ZONE1_SUBWAITING_AREA = (1000, 1150, 720, 780)  # Bottom-right edge of Zone 1
GOWNED_WAITING_AREA = (260, 360, 480, 560)      # Yellow box in Zone 2

# ============================================================================
# SIMULATION CONSTANTS
# ============================================================================

# Time-Based Simulation (Shift Duration Model)
DEFAULT_DURATION = 720      # 12 hours (standard MRI shift)
WARM_UP_DURATION = 60       # 1 hour (prime the system, remove empty-state bias)

# Time Scaling (Faster for video recording)
SIM_SPEED = 0.25  # 1 simulation minute = 0.25 real seconds (~3 min video for 12h shift)

# Staffing
STAFF_COUNT = {
    'porter': 1,
    'backup_tech': 2,
    'scan_tech': 2,
}

# Resource Capacities (Dual-Bay Model)
RESOURCE_CAPACITY = {
    'magnet': 2,           # 2 magnets total (3T + 1.5T)
    'prep_rooms': 2,       # 2 IV Prep rooms (308, 309)
    'change_rooms': 3,     # 3 Change rooms (303, 304, 305)
    'gowned_waiting': 3,   # Max 3 patients in buffer (Source: Floor Plan)
}

# Magnet Resources (Dual-Bay Configuration)
MAGNET_RESOURCES = {
    '3T': 1,      # One 3T magnet (priority)
    '1.5T': 1,    # One 1.5T magnet (backup)
}

# Magnet Locations
MAGNET_3T_LOC = (950, 160)   # Top scan room
MAGNET_15T_LOC = (950, 410)  # Bottom scan room (adjusted from original 550)

# Agent Movement
AGENT_SPEED = {
    'patient': 5.0,        # pixels per frame (increased for visibility)
    'staff': 6.0,          # pixels per frame (staff move faster)
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
    
    # Arrival Schedule (Poisson Process - Increased Demand)
    'mean_inter_arrival': 15,   # Mean time between arrivals (minutes)
    'arrival_noise': (-5, 0, 5),  # Random variation (for non-Poisson fallback)
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
