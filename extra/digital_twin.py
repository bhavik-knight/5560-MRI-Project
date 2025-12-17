
import pygame
import sys
import simpy
import random
import math

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
SIM_SPEED = 0.5  # 1 sim minute = 0.5 real seconds

# Colors
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
TEXT_COLOR = (0, 0, 0)

# Agent State Colors
GREY_ARRIVING = (180, 180, 180)
BLUE_CHANGING = (0, 128, 128)
YELLOW_PREPPED = (255, 215, 0)
GREEN_SCANNING = (0, 255, 0)

# Staff Colors
ORANGE_PORTER = (255, 140, 0)
CYAN_BACKUP = (0, 255, 255)
PURPLE_SCAN = (128, 0, 128)

# Room Coordinates
ZONE1_CENTER = (640, 650)
CHANGE_ROOM_1 = (80, 70)
CHANGE_ROOM_2 = (60, 155)
CHANGE_ROOM_3 = (60, 225)
PREP_ROOM_1 = (375, 80)
PREP_ROOM_2 = (535, 80)
GOWNED_WAITING = (275, 275)
MAGNET_3T = (1100, 175)
MAGNET_15T = (1100, 475)
EXIT_POS = (1260, 650)

# Global sprite group
all_sprites = pygame.sprite.Group()

def get_contrasting_text_color(bg_color):
    """Returns WHITE or BLACK text color based on background luminance."""
    r, g, b = bg_color
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return WHITE if luminance < 0.5 else BLACK

def draw_room(surface, rect, color, label_text, font):
    """Helper to draw a room with a border and centered text."""
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, BLACK, rect, 2)
    
    if font and label_text:
        text_color = get_contrasting_text_color(color)
        lines = label_text.split('\n')
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        start_y = rect.centery - (total_height / 2)
        
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, text_color)
            text_rect = text_surf.get_rect(centerx=rect.centerx, top=start_y + (i * line_height))
            surface.blit(text_surf, text_rect)

def draw_floor_plan(screen, font_room, font_zone):
    """Renders the MRI Department floor plan."""
    screen.fill(WHITE)
    pygame.draw.rect(screen, BLACK, (10, 10, 1260, 700), 5)
    
    draw_room(screen, pygame.Rect(20, 600, 1240, 100), GREY_LIGHT, "ZONE 1: PUBLIC CORRIDOR", font_zone)
    draw_room(screen, pygame.Rect(950, 50, 300, 250), CYAN_MAG, "3T MRI (Source 1)", font_room)
    draw_room(screen, pygame.Rect(950, 350, 300, 250), CYAN_MAG, "1.5T MRI", font_room)
    draw_room(screen, pygame.Rect(820, 50, 130, 550), GREY_DARK, "CONTROL", font_zone)
    
    draw_room(screen, pygame.Rect(20, 20, 120, 100), BLUE_TEAL, "Change 1", font_room)
    draw_room(screen, pygame.Rect(20, 120, 80, 70), BLUE_TEAL, "Change 2", font_room)
    draw_room(screen, pygame.Rect(20, 190, 80, 70), BLUE_TEAL, "Change 3", font_room)
    
    draw_room(screen, pygame.Rect(150, 20, 60, 60), PINK_WR, "WR 1", font_room)
    draw_room(screen, pygame.Rect(220, 20, 60, 60), PINK_WR, "WR 2", font_room)
    
    draw_room(screen, pygame.Rect(300, 20, 150, 120), ORANGE_PREP, "IV Prep 1", font_room)
    draw_room(screen, pygame.Rect(460, 20, 150, 120), ORANGE_PREP, "IV Prep 2", font_room)
    
    draw_room(screen, pygame.Rect(150, 200, 250, 150), YELLOW_ROOM, "GOWNED WAIT\n(Max 3)", font_room)
    draw_room(screen, pygame.Rect(350, 350, 200, 200), GREY_HOLDING, "Holding", font_room)

# ===== AGENT CLASSES =====

class Agent(pygame.sprite.Sprite):
    """Base class for all moving agents."""
    def __init__(self, x, y, color, speed=2.0):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(x)
        self.target_y = float(y)
        self.color = color
        self.speed = speed
        all_sprites.add(self)
    
    def move_to(self, target_x, target_y):
        """Set new target position."""
        self.target_x = float(target_x)
        self.target_y = float(target_y)
    
    def update(self):
        """Move smoothly toward target."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > self.speed:
            # Move toward target
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
        else:
            # Snap to target
            self.x = self.target_x
            self.y = self.target_y
    
    def is_at_target(self):
        """Check if agent has reached target."""
        return abs(self.x - self.target_x) < 1 and abs(self.y - self.target_y) < 1

class Patient(Agent):
    """Patient agent - drawn as a circle."""
    def __init__(self, p_id, x, y):
        super().__init__(x, y, GREY_ARRIVING, speed=3.0)
        self.p_id = p_id
        self.state = 'arriving'
    
    def set_state(self, state):
        """Update patient state and color."""
        self.state = state
        if state == 'arriving':
            self.color = GREY_ARRIVING
        elif state == 'changing':
            self.color = BLUE_CHANGING
        elif state == 'prepped':
            self.color = YELLOW_PREPPED
        elif state == 'scanning':
            self.color = GREEN_SCANNING
    
    def draw(self, screen):
        """Draw patient as a circle."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 8)
        pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), 8, 1)

class Staff(Agent):
    """Staff agent - shape depends on role."""
    def __init__(self, role, x, y):
        colors = {'porter': ORANGE_PORTER, 'backup': CYAN_BACKUP, 'scan': PURPLE_SCAN}
        super().__init__(x, y, colors.get(role, WHITE), speed=4.0)
        self.role = role
        self.busy = False
    
    def draw(self, screen):
        """Draw staff based on role."""
        x, y = int(self.x), int(self.y)
        
        if self.role == 'porter':
            # Triangle
            points = [(x, y-10), (x-8, y+8), (x+8, y+8)]
            pygame.draw.polygon(screen, self.color, points)
            pygame.draw.polygon(screen, BLACK, points, 2)
        else:
            # Square (backup or scan tech)
            rect = pygame.Rect(x-8, y-8, 16, 16)
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)

# ===== SIMULATION INTEGRATION =====

class SimulationState:
    """Holds simulation state accessible by both SimPy and PyGame."""
    def __init__(self):
        self.env = None
        self.screen = None
        self.clock = None
        self.font_room = None
        self.font_zone = None
        self.running = True
        self.sim_time = 0
        
        # Resources
        self.porter = None
        self.backup_techs = None
        self.scan_techs = None
        self.magnet = None
        
        # Staff agents
        self.porter_agent = None
        self.backup_agents = []
        self.scan_agents = []

def wait_with_animation(state, duration_minutes):
    """Wait for simulation time while animating."""
    target_time = state.env.now + duration_minutes
    
    while state.env.now < target_time and state.running:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state.running = False
                return
        
        # Update and draw
        draw_floor_plan(state.screen, state.font_room, state.font_zone)
        all_sprites.update()
        
        # Draw all agents
        for sprite in all_sprites:
            sprite.draw(state.screen)
        
        # Display sim time
        if state.font_room:
            time_text = state.font_room.render(f"Sim Time: {int(state.env.now)} min", True, BLACK)
            state.screen.blit(time_text, (20, 5))
        
        pygame.display.flip()
        state.clock.tick(FPS)
        
        # Advance simulation time (1 sim minute = 0.5 real seconds)
        state.env.run(until=state.env.now + (1.0 / (FPS * SIM_SPEED)))

def patient_journey(state, p_id):
    """SimPy process for a single patient."""
    # 1. Arrival in Zone 1
    patient = Patient(p_id, ZONE1_CENTER[0], ZONE1_CENTER[1])
    patient.set_state('arriving')
    yield state.env.timeout(1)  # Brief pause
    
    # 2. Transport to Change Room
    with state.porter.request() as req:
        yield req
        state.porter_agent.busy = True
        state.porter_agent.move_to(patient.x, patient.y)
        
        # Wait for porter to reach patient
        while not state.porter_agent.is_at_target():
            yield state.env.timeout(0.1)
        
        # Move together to change room
        target = random.choice([CHANGE_ROOM_1, CHANGE_ROOM_2, CHANGE_ROOM_3])
        patient.move_to(target[0], target[1])
        state.porter_agent.move_to(target[0], target[1])
        
        while not patient.is_at_target():
            yield state.env.timeout(0.1)
        
        state.porter_agent.busy = False
        state.porter_agent.move_to(ZONE1_CENTER[0], ZONE1_CENTER[1])  # Return
    
    # 3. Changing
    patient.set_state('changing')
    yield state.env.timeout(3.5)
    
    # 4. Prep with Backup Tech
    with state.backup_techs.request() as req:
        yield req
        # Find available backup tech
        tech = next((t for t in state.backup_agents if not t.busy), state.backup_agents[0])
        tech.busy = True
        tech.move_to(patient.x, patient.y)
        
        while not tech.is_at_target():
            yield state.env.timeout(0.1)
        
        # Move to prep room
        prep_target = random.choice([PREP_ROOM_1, PREP_ROOM_2])
        patient.move_to(prep_target[0], prep_target[1])
        tech.move_to(prep_target[0], prep_target[1])
        
        while not patient.is_at_target():
            yield state.env.timeout(0.1)
        
        patient.set_state('prepped')
        yield state.env.timeout(2.5)  # IV setup
        
        tech.busy = False
        tech.move_to(GOWNED_WAITING[0] + 50, GOWNED_WAITING[1])  # Return to staging
    
    # 5. Gowned Waiting (if magnet busy)
    patient.move_to(GOWNED_WAITING[0], GOWNED_WAITING[1])
    while not patient.is_at_target():
        yield state.env.timeout(0.1)
    
    # 6. Scan
    with state.magnet.request() as req:
        yield req
        # Find available scan tech
        scan_tech = next((t for t in state.scan_agents if not t.busy), state.scan_agents[0])
        scan_tech.busy = True
        
        # Move to magnet
        patient.move_to(MAGNET_3T[0], MAGNET_3T[1])
        scan_tech.move_to(MAGNET_3T[0] - 30, MAGNET_3T[1])
        
        while not patient.is_at_target():
            yield state.env.timeout(0.1)
        
        patient.set_state('scanning')
        yield state.env.timeout(22)  # Scan duration
        
        scan_tech.busy = False
        scan_tech.move_to(MAGNET_3T[0] - 80, MAGNET_3T[1])  # Return to control
    
    # 7. Exit
    patient.move_to(EXIT_POS[0], EXIT_POS[1])
    while not patient.is_at_target():
        yield state.env.timeout(0.1)
    
    patient.kill()  # Remove from sprites

def patient_generator(state):
    """Generate patients at intervals."""
    p_id = 0
    while state.running:
        p_id += 1
        state.env.process(patient_journey(state, p_id))
        yield state.env.timeout(30)  # New patient every 30 minutes

def main():
    pygame.init()
    
    # Initialize fonts
    font_room = None
    font_zone = None
    try:
        pygame.font.init()
        font_room = pygame.font.SysFont('Arial', 16, bold=True)
        font_zone = pygame.font.SysFont('Arial', 24, bold=True)
        print("Fonts loaded successfully")
    except Exception as e:
        print(f"Font loading failed: {e}")
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MRI Digital Twin - Agent Simulation")
    clock = pygame.time.Clock()
    
    # Create simulation state
    state = SimulationState()
    state.env = simpy.Environment()
    state.screen = screen
    state.clock = clock
    state.font_room = font_room
    state.font_zone = font_zone
    
    # Create resources
    state.porter = simpy.Resource(state.env, capacity=1)
    state.backup_techs = simpy.Resource(state.env, capacity=2)
    state.scan_techs = simpy.Resource(state.env, capacity=2)
    state.magnet = simpy.Resource(state.env, capacity=1)
    
    # Create staff agents
    state.porter_agent = Staff('porter', ZONE1_CENTER[0] - 50, ZONE1_CENTER[1])
    state.backup_agents = [
        Staff('backup', GOWNED_WAITING[0] + 50, GOWNED_WAITING[1]),
        Staff('backup', GOWNED_WAITING[0] + 70, GOWNED_WAITING[1])
    ]
    state.scan_agents = [
        Staff('scan', MAGNET_3T[0] - 80, MAGNET_3T[1]),
        Staff('scan', MAGNET_15T[0] - 80, MAGNET_15T[1])
    ]
    
    # Start patient generator
    state.env.process(patient_generator(state))
    
    # Main loop
    while state.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state.running = False
        
        # Draw floor plan
        draw_floor_plan(screen, font_room, font_zone)
        
        # Update and draw agents
        all_sprites.update()
        for sprite in all_sprites:
            sprite.draw(screen)
        
        # Display sim time
        if font_room:
            time_text = font_room.render(f"Sim Time: {int(state.env.now)} min", True, BLACK)
            screen.blit(time_text, (20, 5))
        
        pygame.display.flip()
        clock.tick(FPS)
        
        # Advance simulation
        state.env.run(until=state.env.now + (1.0 / (FPS * SIM_SPEED)))
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
