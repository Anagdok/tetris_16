import pygame
import random
import math
import sys

# --- CONFIGURATION ---
FPS = 60
BASE_WIDTH, BASE_HEIGHT = 1920, 1080 # We will scale this dynamically
GRID_W, GRID_H = 10, 20
BLOCK_SIZE_VIRTUAL = 30 # Base size for calculation

# Tetromino shapes
SHAPES = [
    [[1, 1, 1, 1]], # I (Cyan)
    [[1, 0, 0], [1, 1, 1]], # J (Blue/Purple)
    [[0, 0, 1], [1, 1, 1]], # L (Orange)
    [[1, 1], [1, 1]], # O (Yellow)
    [[0, 1, 1], [1, 1, 0]], # S (Green)
    [[0, 1, 0], [1, 1, 1]], # T (Pink/Magenta)
    [[1, 1, 0], [0, 1, 1]]  # Z (Red)
]

class PlayerBoard:
    def __init__(self, nickname, joystick):
        self.nickname = nickname
        self.joystick = joystick
        self.board = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.score = 0
        self.alive = True
        
        self.current_piece = None
        self.piece_x = 0
        self.piece_y = 0
        self.color_index = 0
        
        self.fall_time = 0
        self.fall_speed = 500 # ms per drop
        self.move_cooldown = 0
        
        self.spawn_piece()

    def spawn_piece(self):
        shape_idx = random.randint(0, len(SHAPES) - 1)
        self.current_piece = SHAPES[shape_idx]
        self.color_index = shape_idx + 1 # 1-7 matching our blocks.png slices
        self.piece_x = GRID_W // 2 - len(self.current_piece[0]) // 2
        self.piece_y = 0
        
        if self.check_collision(0, 0, self.current_piece):
            self.alive = False # Game Over for this player

    def check_collision(self, dx, dy, shape):
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    new_x = self.piece_x + x + dx
                    new_y = self.piece_y + y + dy
                    if new_x < 0 or new_x >= GRID_W or new_y >= GRID_H:
                        return True
                    if new_y >= 0 and self.board[new_y][new_x] != 0:
                        return True
        return False

    def rotate_piece(self):
        # Transpose and reverse rows
        rotated = [list(row) for row in zip(*self.current_piece[::-1])]
        if not self.check_collision(0, 0, rotated):
            self.current_piece = rotated

    def lock_piece(self):
        for y, row in enumerate(self.current_piece):
            for x, cell in enumerate(row):
                if cell:
                    self.board[self.piece_y + y][self.piece_x + x] = self.color_index
        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        lines_cleared = 0
        new_board = [row for row in self.board if any(cell == 0 for cell in row)]
        lines_cleared = GRID_H - len(new_board)
        
        # Add empty lines at top
        for _ in range(lines_cleared):
            new_board.insert(0, [0 for _ in range(GRID_W)])
            
        self.board = new_board
        self.score += lines_cleared * 100
        # In a full Tetris 99, this is where you'd send 'garbage' to other boards

    def update(self, dt):
        if not self.alive: return

        # Gravity
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.check_collision(0, 1, self.current_piece):
                self.piece_y += 1
            else:
                self.lock_piece()

        # Handle Inputs
        self.move_cooldown -= dt
        if self.move_cooldown <= 0:
            axis_x = self.joystick.get_axis(0) # e.ABS_X
            axis_y = self.joystick.get_axis(1) # e.ABS_Y
            
            # Deadzones applied here. Pygame normalizes axes to -1.0 to 1.0. 
            if axis_x < -0.5 and not self.check_collision(-1, 0, self.current_piece):
                self.piece_x -= 1
                self.move_cooldown = 100
            elif axis_x > 0.5 and not self.check_collision(1, 0, self.current_piece):
                self.piece_x += 1
                self.move_cooldown = 100
                
            if axis_y > 0.5 and not self.check_collision(0, 1, self.current_piece):
                self.piece_y += 1
                self.move_cooldown = 50 # Faster drop

    def draw(self, surface, x_offset, y_offset, cell_size, block_textures, font):
        # Draw Board Background
        board_rect = pygame.Rect(x_offset, y_offset, GRID_W * cell_size, GRID_H * cell_size)
        pygame.draw.rect(surface, (20, 20, 20), board_rect)
        pygame.draw.rect(surface, (100, 100, 100), board_rect, 2) # Border

        # Draw Locked Blocks
        for y in range(GRID_H):
            for x in range(GRID_W):
                color_idx = self.board[y][x]
                if color_idx > 0:
                    tex = pygame.transform.scale(block_textures[color_idx-1], (cell_size, cell_size))
                    surface.blit(tex, (x_offset + x * cell_size, y_offset + y * cell_size))

        # Draw Current Piece
        if self.alive and self.current_piece:
            for y, row in enumerate(self.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        tex = pygame.transform.scale(block_textures[self.color_index-1], (cell_size, cell_size))
                        surface.blit(tex, (x_offset + (self.piece_x + x) * cell_size, y_offset + (self.piece_y + y) * cell_size))

        # Draw Player Name and Status
        name_text = font.render(self.nickname, True, (255, 255, 255))
        surface.blit(name_text, (x_offset, y_offset - 25))
        
        if not self.alive:
            over_text = font.render("KO", True, (255, 0, 0))
            surface.blit(over_text, (x_offset + (GRID_W*cell_size)//2 - 10, y_offset + (GRID_H*cell_size)//2))

class Game:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        # Set to fullscreen for optimal display management
        self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("Tetris 16-Player Battle")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18, bold=True)
        
        self.players = {}
        self.block_textures = self.load_blocks("blocks.png")

    def load_blocks(self, filename):
        """Slices the blocks.png into individual textures."""
        try:
            sheet = pygame.image.load(filename).convert_alpha()
            w, h = sheet.get_size()
            # The image is 8 blocks wide.
            block_w = w // 8
            textures = []
            for i in range(8):
                rect = pygame.Rect(i * block_w, 0, block_w, h)
                textures.append(sheet.subsurface(rect))
            return textures
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            # Fallback to solid colored surfaces if file is missing
            colors = [(255,0,0), (255,255,0), (128,0,128), (0,255,0), (0,255,255), (255,165,0), (255,0,255), (128,128,128)]
            textures = []
            for c in colors:
                s = pygame.Surface((32, 32))
                s.fill(c)
                pygame.draw.rect(s, (255,255,255), s.get_rect(), 1)
                textures.append(s)
            return textures

    def handle_joystick_connection(self):
        """Scans for new Gamepad-server OS devices."""
        current_joy_count = pygame.joystick.get_count()
        for i in range(current_joy_count):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            name = joy.get_name()
            
            if name.startswith("Gamepad_") and joy.get_instance_id() not in self.players:
                nickname = name.replace("Gamepad_", "")
                print(f"Player Connected: {nickname}")
                self.players[joy.get_instance_id()] = PlayerBoard(nickname, joy)

    def calculate_layout(self):
        """Dynamic Screen Management - Calculates optimal grid layout without black squares."""
        num_players = max(1, len(self.players))
        
        # Calculate optimal columns and rows
        cols = math.ceil(math.sqrt(num_players))
        rows = math.ceil(num_players / cols)
        
        # Screen dimensions
        sw, sh = self.screen.get_size()
        
        # How much space each player gets
        cell_w = sw // cols
        cell_h = sh // rows
        
        # Calculate block size inside that space to maintain Tetris aspect ratio (10x20)
        # We leave some padding for the name tags
        padding = 40
        max_block_w = (cell_w - padding) // GRID_W
        max_block_h = (cell_h - padding) // GRID_H
        
        block_size = min(max_block_w, max_block_h)
        
        return cols, rows, cell_w, cell_h, block_size

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            self.handle_joystick_connection()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                # Handle Button Presses (Rotation)
                elif event.type == pygame.JOYBUTTONDOWN:
                    player = self.players.get(event.instance_id)
                    if player and player.alive:
                        # BTN_SOUTH (A) or BTN_EAST (B)
                        if event.button == 0 or event.button == 1: 
                            player.rotate_piece()

            # Update Logic
            for player in self.players.values():
                player.update(dt)

            # Draw Logic
            self.screen.fill((5, 5, 10)) # Dark background
            
            cols, rows, cell_w, cell_h, block_size = self.calculate_layout()
            
            for idx, player in enumerate(self.players.values()):
                grid_x = idx % cols
                grid_y = idx // cols
                
                # Center the board in its allocated cell
                board_pixel_w = GRID_W * block_size
                board_pixel_h = GRID_H * block_size
                
                x_offset = (grid_x * cell_w) + (cell_w - board_pixel_w) // 2
                y_offset = (grid_y * cell_h) + (cell_h - board_pixel_h) // 2 + 10 # +10 to leave room for name
                
                player.draw(self.screen, x_offset, y_offset, block_size, self.block_textures, self.font)

            pygame.display.flip()
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
