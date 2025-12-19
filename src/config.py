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

# Patient Type Colors
COLOR_INPATIENT = (233, 30, 99)         # Dark Pink / Fuschia (High Acuity)
COLOR_OUTPATIENT = (30, 144, 255)       # Dodger Blue (Standard)

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
    
    'waiting_room': (200, 250, 200, 250),  # Original Hub Buffer
    'holding_transfer': (420, 250, 250, 250), # holding transfer room
    
    # Zone 3: Control (Vertical Strip)
    'control': (750, 50, 100, 520),
    
    # Zone 4: Magnets (Right Side)
    'magnet_3t': (870, 50, 250, 250),    # 3T MRI (Room 319)
    'magnet_15t': (870, 320, 250, 250),  # 1.5T MRI (Room 315)
    
    # break room
    'break_room': (50, 400, 75, 75),

    # Building Border
    'building': (10, 10, 1180, 770),
}

# Agent Spawn/Target Positions (x, y tuples)
AGENT_POSITIONS = {
    'zone1_center': (1150, 675),
    'change_1_center': (100, 100),
    'change_2_center': (87, 192),
    'change_3_center': (87, 282),
    'washroom_1_center': (198, 88),
    'washroom_2_center': (283, 88),
    'prep_1_center': (425, 125),
    'prep_2_center': (595, 125),
    'waiting_room_center': (300, 375),
    'holding_transfer_center': (545, 375),
    'magnet_3t_center': (995, 175),
    'magnet_15t_center': (995, 445),
    'exit': (1180, 675),
    
    # Staff Staging Positions
    'porter_home': (350, 675),
    'backup_staging': (450, 125),
    'scan_staging_3t': (800, 175),
    'scan_staging_15t': (800, 445),
    'admin_home': (850, 675),

    # Staging Areas
    'change_staging': (150, 250), # Hallway outside change rooms
    'washroom_staging': (280, 100), # Near washrooms 306/307 (Zone 2 top)
    'break_room_center': (87, 437), # Center of the newly defined break room
    'room_311_slot_1': (450, 350),
    'room_311_slot_2': (450, 450),
    'control_room_center': (850, 320),
}

# Room Capacities
ROOM_311_CAPACITY = 2
ROOM_311_SLOTS = [(450, 350), (450, 450)]
CONTROL_ROOM_LOC = (850, 320)

# Priority Levels (Lower number = Higher priority in SimPy)
PRIORITY_INPATIENT = 0  # Highest priority for high-acuity cases
PRIORITY_OUTPATIENT = 1  # Standard priority

# Waiting Areas (Rectangles for spatial scatter: x_min, x_max, y_min, y_max)
ZONE1_TOP_Y = 600
ZONE1_SUBWAITING_AREA = (900, 1050, 620, 730)
WAITING_ROOM_AREA = (220, 430, 270, 430)
WAITING_ROOM_LOC = (325, 350)

# ============================================================================
# SIMULATION CONSTANTS
# ============================================================================

# Time-Based Simulation (Shift Duration Model)
DEFAULT_DURATION = 720      # 12 hours
WARM_UP_DURATION = 60       # 1 hour
HEADLESS = False            # Set to True for fast batch runs

# Time Scaling (Faster for video recording)
# Source 118: SIM_SPEED = 0.25 (Note: Adjust higher if running 720 hours, but keep 0.25 for demo)
SIM_SPEED = 0.25  # 1 simulation minute = 0.25 real seconds (~3 min video for 12h shift)
RECORD_INTERVAL = 2  # 1 = Record all, 2 = Record every 2nd frame (2x speed)

# Clinical Parameters
# EXAM_TYPES = ['Brain', 'Spine', 'Knee', 'Abdomen', 'Cardiac'] # Source 140

# Staffing
STAFF_COUNT = {
    'scan_tech': 2,
    'backup_tech': 2,
    'admin': 1,
    'porter': 1,
}

# Break Schedule Parameters
BREAK_CONFIG = {
    'long_break_min': 30,
    'short_break_min': 15,
    'total_break_min': 90,
    'schedule': [30, 15, 30, 15] # 2 long, 2 short
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
PROB_IV_NEEDED = 0.33      # Derived from Row 12 "Patient IV setup" (33%)
PROB_DIFFICULT_IV = 0.15   # Derived from Row 12b "Difficult IV" (15%)
PROB_WASHROOM_USAGE = 0.2  # Source 17
PROB_INPATIENT = 0.25      # Increased to 25% for Stress Test [User Request]
PROB_NO_SHOW = 0.05        # 5% Absent rate [Source 36]
PROB_LATE = 0.20           # 20% Lateness rate [Source 36]

# Dynamic Capacity Constants [Source 172]
MAX_SCAN_TIME = 70      # Max time for complex case
AVG_CYCLE_TIME = 45     # Avg throughput time per patient

# Scan Durations & Workload Mix (Source: class2-ppt.pdf)
# "Protocol Duration – HI Siemens Site"
SCAN_PROTOCOLS = {
    'Prostate': {'mean': 22.0, 'std': 5.0},
    'Cardiac': {'mean': 68.9},
    'Body': {'mean': 50.5},
    # Default fallbacks if needed
    'Brain': {'mean': 25.0},
    'Spine': {'mean': 35.0},
    'Knee': {'mean': 20.0},
}
# Keep EXAM_TYPES for random selection, but prefer SCAN_PROTOCOLS statistics
EXAM_TYPES = list(SCAN_PROTOCOLS.keys())

# All times in MINUTES
# Format: (min, mode, max) for triangular distribution
# UPDATED Source: 4 Tech Model- MRI Department Efficiency 2025-rev 1.sheet4.pdf
PROCESS_TIMES = {
    # Screening & Consent ("Pit Crew" Actions)
    # Task 4: Patient fills out safety screening form
    'registration': (2.08, 3.18, 5.15), 
    'screening': (2.08, 3.18, 5.15), # Mapped to registration
    
    # Change/Gown
    # Task 7: Patient changes
    'change': (1.53, 3.17, 5.78),
    'changing': (1.53, 3.17, 5.78),
    
    # IV Setup (if needed)
    'iv_prep': (1.5, 2.5, 4.0),
    'iv_setup': (1.5, 2.5, 4.0),
    'iv_difficult': (7.0, 7.8, 9.0), # Mean 7m 48s approx
    
    # Scanning Phase
    # Protocol Durations are now in SCAN_PROTOCOLS; these are overheads
    'scan_setup': (1.52, 3.96, 7.48),
    'scan_duration': (18.1, 22.0, 26.5), # Fallback/Legacy
    'scan_exit': (0.35, 2.56, 4.52),
    
    # Staff Task Itemization
    'handover': 2.0, # Fixed 2.0 min handover for Techs
    
    # Operation/Turnover Times
    # Task 17: Perform bed flip
    'bed_flip': (0.53, 1.18, 2.80),
    'bed_flip_fast': (0.53, 1.18, 2.80),
    'bed_flip_slow': (1.5, 2.5, 4.0),
    'settings_change': (1.0, 2.0, 3.0),
    
    # New Patient Needs
    'washroom': (0.8, 2.3, 5.2), # Source 17
    'change_back': (2.0, 3.5, 5.0),
    
    # Inpatient/High Acuity (Parallel Processing)
    'holding_prep': (10, 15, 25),  # Anesthesia setup outside magnet
    'bed_transfer': (3, 5, 8),     # Moving from Room 311 to Magnet
    
    # Arrival Schedule (Poisson Process) 
    'mean_inter_arrival': 30, # To be optimized via "Singles Line" strategy
    
    # Compliance Penalties
    'no_show_wait': 15,          # Magnet sits idle for 15 min
    'late_delay': (10, 15, 30),  # Late patients arrive 10-30 mins behind
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
    'holding_transfer': 'ROOM 311\nHolding/Transfer',
    'control': 'CONTROL',
    'break_room': 'Break\nRoom',
    'magnet_3t': '3T MRI',
    'magnet_15t': '1.5T MRI',
}