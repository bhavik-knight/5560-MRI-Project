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
FPS = 60                      # Smooth 60 FPS animation

# Medical White Color Scheme
# Source 85: "background_color is Corridor Grey... Room Interiors are Medical White"
MEDICAL_WHITE = (255, 255, 255)      # All rooms
CORRIDOR_GREY = (230, 230, 230)      # Background
WALL_BLACK = (0, 0, 0)               # Room borders
LABEL_BLACK = (0, 0, 0)              # Text
SEPARATOR_BLACK = (0, 0, 0)          # Sidebar divider
GREY_OCCUPIED = (225, 225, 235)      # Slightly grey/blueish for occupied rooms

# ============================================================================
# RGB COLORS - Agent States
# ============================================================================

# Patient State Colors
GREY_ARRIVING = (180, 180, 180)      # Arriving in Zone 1
PURPLE_REGISTERED = (160, 32, 240)   # Registered (Purple)
BLUE_CHANGING = (0, 128, 128)        # Changing (Teal)
YELLOW_PREPPED = (255, 215, 0)       # Prepped/Waiting (Gold)
GREEN_SCANNING = (0, 255, 0)         # Scanning (Bright Green)
NEON_YELLOW = (255, 255, 0)          # High-visibility yellow

# Staff Colors
ORANGE_PORTER = (255, 140, 0)        # Porter (Dark Orange)
CYAN_BACKUP = (0, 255, 255)          # Backup Tech (Cyan)
PURPLE_SCAN = (128, 0, 128)          # Scan Tech (Purple)
BLUE_ADMIN = (48, 92, 222)           # Admin TA (Royal Blue #305CDE)

# Room/Zone Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN_OCCUPIED = (230, 255, 230)     # Light green for occupied rooms
GREY_OCCUPIED = (225, 225, 235)      # Kept for compatibility or alternative
GREY_LIGHT = (220, 220, 220)
GREY_DARK = (150, 150, 150)
GREY_HOLDING = (180, 180, 180)
BLUE_TEAL = (0, 128, 128)

# Visual Logic Colors [Source 81]
COLOR_MAGNET_CLEAN = (255, 255, 255)    # White
COLOR_MAGNET_BUSY = (230, 255, 230)     # Light Green
COLOR_MAGNET_DIRTY = (210, 180, 140)    # Tan/Light Brown

# ============================================================================
# LAYOUT COORDINATES (pygame.Rect format: x, y, width, height)
# ============================================================================

ROOM_COORDINATES = {
    # Zone 1: Public Corridor (Bottom)
    'zone1': (50, 600, 1070, 150),
    
    # Zone 2: The Hub (Left/Center)
    'change_1': (50, 50, 100, 100),       # Big/Accessible
    'change_2': (50, 160, 75, 75),       # Standard
    'change_3': (50, 245, 75, 75),       # Standard
    
    'washroom_1': (160, 50, 75, 75),     # Accessible
    'washroom_2': (245, 50, 75, 75),     # Standard
    
    'prep_1': (350, 50, 150, 150),       # IV Prep Room 308
    'prep_2': (520, 50, 150, 150),       # IV Prep Room 309
    
    'waiting_room': (200, 250, 250, 200),  # Original Hub Buffer
    
    # Zone 3: Control (Vertical Strip)
    'control': (750, 50, 100, 520),
    
    # Zone 4: Magnets (Right Side)
    'magnet_3t': (870, 50, 250, 250),    # 3T MRI (Room 319)
    'magnet_15t': (870, 320, 250, 250),  # 1.5T MRI (Room 315)
    
    # Building Border
    'building': (10, 10, 1180, 770),
}

# Agent Spawn/Target Positions (x, y tuples)
AGENT_POSITIONS = {
    'zone1_center': (1150, 675),
    'change_1_center': (100, 100),
    'change_2_center': (87, 197),
    'change_3_center': (87, 282),
    'prep_1_center': (425, 125),
    'prep_2_center': (595, 125),
    'waiting_room_center': (325, 350),
    'magnet_3t_center': (995, 175),
    'magnet_15t_center': (995, 445),
    'exit': (1180, 675),
    
    # Staff Staging Positions
    'porter_home': (350, 675),
    'backup_staging': (450, 125),
    'scan_staging_3t': (800, 175),
    'scan_staging_15t': (800, 445),
    'admin_home': (850, 675),
}

# Waiting Areas (Rectangles for spatial scatter: x_min, x_max, y_min, y_max)
ZONE1_TOP_Y = 600
ZONE1_SUBWAITING_AREA = (900, 1050, 620, 730)
WAITING_ROOM_AREA = (220, 430, 270, 430)
WAITING_ROOM_LOC = (325, 350)

# ============================================================================
# SIMULATION CONSTANTS
# ============================================================================

# Time-Based Simulation (Shift Duration Model)
DEFAULT_DURATION = 120      # 2 hours (standard test shift)
WARM_UP_DURATION = 60       # 1 hour (prime the system, remove empty-state bias)

# Time Scaling (Faster for video recording)
# Source 118: SIM_SPEED = 0.25 (Note: Adjust higher if running 720 hours, but keep 0.25 for demo)
SIM_SPEED = 0.25  # 1 simulation minute = 0.25 real seconds (~3 min video for 12h shift)
RECORD_INTERVAL = 2  # 1 = Record all, 2 = Record every 2nd frame (2x speed)

# Clinical Parameters
EXAM_TYPES = ['Brain', 'Spine', 'Knee', 'Abdomen', 'Cardiac'] # Source 140

# Staffing
STAFF_COUNT = {
    'porter': 1,
    'backup_tech': 2,
    'scan_tech': 2,
    'admin': 1,
}

# Resource Capacities (Dual-Bay Model)
RESOURCE_CAPACITY = {
    'magnet': 2,           # 2 magnets total (3T + 1.5T)
    'prep_rooms': 2,       # 2 IV Prep rooms (308, 309)
    'change_rooms': 3,     # 3 Change rooms (303, 304, 305)
    'waiting_room': 3,   # Max 3 patients in buffer (Source: Floor Plan)
}

# Magnet Resources (Dual-Bay Configuration)
MAGNET_RESOURCES = {
    '3T': 1,      # One 3T magnet (priority)
    '1.5T': 1,    # One 1.5T magnet (backup)
}

# Magnet Locations
MAGNET_3T_LOC = (995, 175)   # Top scan room
MAGNET_15T_LOC = (995, 445)  # Bottom scan room

# Agent Movement
# Source 118: Define Speeds
AGENT_SPEED = {
    'patient': 5.0,        # pixels per frame (increased for visibility)
    'staff': 6.0,          # pixels per frame (staff move faster)
}

# PROBABILITIES (Source 33)
PROB_IV_NEEDED = 0.33
PROB_DIFFICULT_IV = 0.01
PROB_WASHROOM_USAGE = 0.2 # Source 17
# Dynamic Capacity Constants [Source 172]
MAX_SCAN_TIME = 70      # Max time for complex case
AVG_CYCLE_TIME = 45     # Avg throughput time per patient

# All times in MINUTES
# Format: (min, mode, max) for triangular distribution
# UPDATED Source: Sheet 3 Distributions
PROCESS_TIMES = {
    # Screening & Consent
    'registration': (2.1, 3.2, 5.1), # Source 14
    'screening': (2.08, 3.20, 5.15), # Kept for backup/legacy
    
    # Change/Gown
    'change': (1.53, 3.17, 5.78), # Kept for legacy
    'changing': (1.5, 3.1, 5.7), # Source 16
    
    # IV Setup (if needed)
    'iv_prep': (1.5, 2.5, 4.0), # Source 22
    'iv_setup': (1.53, 2.56, 4.08), # Legacy
    'iv_difficult': (7.0, 7.8, 9.0),
    
    # Scanning Phase (Empirical breakdown)
    'scan_setup': (1.52, 3.96, 7.48),
    'scan_duration': (18.1, 22.0, 26.5),
    'scan_exit': (0.35, 2.56, 4.52),
    
    # Operation/Turnover Times
    'bed_flip_fast': (0.5, 0.8, 1.0), # Tech Assisted
    'bed_flip_slow': (1.5, 2.5, 4.0), # Porter Solo
    'bed_flip': (0.58, 1.0, 1.33), # Legacy
    'settings_change': (1.0, 2.0, 3.0), # Tech in control room
    
    # New Patient Needs
    'washroom': (0.8, 2.3, 5.2), # Source 17
    'change_back': (2.0, 3.5, 5.0),
    
    # Arrival Schedule (Poisson Process)
    'mean_inter_arrival': 30,
}


# ============================================================================
# ROOM LABELS (For Visualization)
# ============================================================================

ROOM_LABELS = {
    'zone1': 'PUBLIC CORRIDOR',
    'change_1': 'Change 1',
    'change_2': 'Change 2',
    'change_3': 'Change 3',
    'washroom_1': 'WR 1',
    'washroom_2': 'WR 2',
    'prep_1': 'IV Prep 1',
    'prep_2': 'IV Prep 2',
    'waiting_room': 'WAITING ROOM',
    'control': 'CONTROL',
    'magnet_3t': '3T MRI',
    'magnet_15t': '1.5T MRI',
}