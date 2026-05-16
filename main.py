import pygame
import random
import math
import sys
import os

# --- KONFIGURACJA ---
FPS = 60
BASE_WIDTH, BASE_HEIGHT = 1920, 1080
GRID_W, GRID_H = 10, 20

# Klocki (Tetromino)
SHAPES = [
    [[1, 1, 1, 1]], # I 
    [[1, 0, 0], [1, 1, 1]], # J
    [[0, 0, 1], [1, 1, 1]], # L 
    [[1, 1], [1, 1]], # O 
    [[0, 1, 1], [1, 1, 0]], # S 
    [[0, 1, 0], [1, 1, 1]], # T 
    [[1, 1, 0], [0, 1, 1]]  # Z 
]

# Kolory ramek dla graczy
PLAYER_COLORS = [
    (255, 50, 50), (50, 255, 50), (50, 50, 255), (255, 255, 50),
    (255, 50, 255), (50, 255, 255), (255, 150, 50), (150, 50, 255),
    (255, 255, 255), (150, 150, 150), (255, 100, 100), (100, 255, 100),
    (100, 100, 255), (255, 200, 100), (200, 100, 255), (100, 255, 200)
]

class PlayerBoard:
    def __init__(self, nickname, joystick, player_id):
        self.nickname = nickname
        self.joystick = joystick
        self.color = PLAYER_COLORS[player_id % len(PLAYER_COLORS)]
        self.ready = False
        self.reset()

    def reset(self):
        self.board = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.score = 0
        self.alive = True
        self.piece_queue = [self._generate_piece() for _ in range(3)]
        self.current_piece, self.color_index = self._generate_piece()
        self.piece_x = GRID_W // 2 - len(self.current_piece[0]) // 2
        self.piece_y = 0
        self.fall_time = 0
        self.fall_speed = 500
        self.move_cooldown = 0

    def _generate_piece(self):
        shape_idx = random.randint(0, len(SHAPES) - 1)
        return SHAPES[shape_idx], shape_idx + 1

    def spawn_piece(self):
        self.current_piece, self.color_index = self.piece_queue.pop(0)
        self.piece_queue.append(self._generate_piece())
        
        self.piece_x = GRID_W // 2 - len(self.current_piece[0]) // 2
        self.piece_y = 0
        
        if self.check_collision(0, 0, self.current_piece):
            self.alive = False # Game Over dla tego gracza

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
        if not self.alive: return
        rotated = [list(row) for row in zip(*self.current_piece[::-1])]
        if not self.check_collision(0, 0, rotated):
            self.current_piece = rotated

    def hard_drop(self):
        if not self.alive: return
        while not self.check_collision(0, 1, self.current_piece):
            self.piece_y += 1
        self.lock_piece()
        self.fall_time = 0

    def lock_piece(self):
        for y, row in enumerate(self.current_piece):
            for x, cell in enumerate(row):
                if cell:
                    self.board[self.piece_y + y][self.piece_x + x] = self.color_index
        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        new_board = [row for row in self.board if any(cell == 0 for cell in row)]
        lines_cleared = GRID_H - len(new_board)
        for _ in range(lines_cleared):
            new_board.insert(0, [0 for _ in range(GRID_W)])
        self.board = new_board
        
        # System punktacji
        if lines_cleared == 1: self.score += 100
        elif lines_cleared == 2: self.score += 300
        elif lines_cleared == 3: self.score += 500
        elif lines_cleared == 4: self.score += 800

    def update(self, dt):
        if not self.alive: return

        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.check_collision(0, 1, self.current_piece):
                self.piece_y += 1
            else:
                self.lock_piece()

        self.move_cooldown -= dt
        if self.move_cooldown <= 0:
            dx, dy = 0, 0
            # Sprawdzenie D-Pada (jako Hat lub Axis - dla bezpieczeństwa obu)
            if self.joystick.get_numhats() > 0:
                dx, dy = self.joystick.get_hat(0)
            else:
                axis_x = self.joystick.get_axis(0)
                axis_y = self.joystick.get_axis(1)
                if axis_x < -0.5: dx = -1
                elif axis_x > 0.5: dx = 1
                if axis_y > 0.5: dy = -1 # w dół to często ujemne na d-padach uinput, zależy od kalibracji
                elif axis_y < -0.5: dy = 1

            if dx == -1 and not self.check_collision(-1, 0, self.current_piece):
                self.piece_x -= 1
                self.move_cooldown = 120
            elif dx == 1 and not self.check_collision(1, 0, self.current_piece):
                self.piece_x += 1
                self.move_cooldown = 120
                
            if dy == -1 and not self.check_collision(0, 1, self.current_piece): # w dół (w zależności od mapowania evdev, dy może być 1 lub -1)
                self.piece_y += 1
                self.move_cooldown = 60
                
            if dy == 1 and not self.check_collision(0, 1, self.current_piece):
                self.piece_y += 1
                self.move_cooldown = 60

    def draw(self, surface, x_offset, y_offset, cell_size, block_textures, font, small_font):
        # Rysowanie tła planszy
        board_rect = pygame.Rect(x_offset, y_offset, GRID_W * cell_size, GRID_H * cell_size)
        pygame.draw.rect(surface, (20, 20, 20), board_rect)
        
        # Osobista kolorowa otoczka gracza (Border)
        pygame.draw.rect(surface, self.color, board_rect, 4) 

        # Zablokowane klocki
        for y in range(GRID_H):
            for x in range(GRID_W):
                c_idx = self.board[y][x]
                if c_idx > 0:
                    tex = pygame.transform.scale(block_textures[c_idx-1], (cell_size, cell_size))
                    surface.blit(tex, (x_offset + x * cell_size, y_offset + y * cell_size))

        # Aktualny klocek
        if self.alive and self.current_piece:
            for y, row in enumerate(self.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        tex = pygame.transform.scale(block_textures[self.color_index-1], (cell_size, cell_size))
                        surface.blit(tex, (x_offset + (self.piece_x + x) * cell_size, y_offset + (self.piece_y + y) * cell_size))

        # Nazwa i Punkty
        name_text = font.render(self.nickname, True, self.color)
        score_text = small_font.render(f"Pkt: {self.score}", True, (255, 255, 255))
        surface.blit(name_text, (x_offset, y_offset - 40))
        surface.blit(score_text, (x_offset, y_offset - 20))

        # Kolejka 3 następnych klocków (Next)
        next_x = x_offset + (GRID_W * cell_size) + 10
        next_y = y_offset
        for shape, color_idx in self.piece_queue:
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        tex = pygame.transform.scale(block_textures[color_idx-1], (cell_size//2, cell_size//2))
                        surface.blit(tex, (next_x + x*(cell_size//2), next_y + y*(cell_size//2)))
            next_y += 4 * (cell_size // 2)

        if not self.alive:
            s = pygame.Surface((GRID_W * cell_size, GRID_H * cell_size), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            surface.blit(s, (x_offset, y_offset))
            over_text = font.render("KO", True, (255, 50, 50))
            surface.blit(over_text, (x_offset + (GRID_W*cell_size)//2 - over_text.get_width()//2, y_offset + (GRID_H*cell_size)//2))

class Game:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("Tetris 16-Player Battle")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 16)
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        
        self.players = {}
        self.block_textures = self.load_blocks("blocks.png")
        self.state = "MENU" # MENU, PLAYING, LEADERBOARD
        self.player_counter = 0
        
        self.load_music()

    def load_music(self):
        self.playlist = []
        if not os.path.exists('music'):
            os.makedirs('music')
            print("Utworzono folder 'music'. Wrzuć tam pliki MP3/OGG!")
        else:
            for file in os.listdir('music'):
                if file.endswith(('.mp3', '.ogg', '.wav')):
                    self.playlist.append(os.path.join('music', file))
        
        if self.playlist:
            pygame.mixer.music.load(self.playlist[0]) # Ładuje pierwszy utwór, później można dodać shuffle

    def load_blocks(self, filename):
        try:
            sheet = pygame.image.load(filename).convert_alpha()
            w, h = sheet.get_size()
            block_w = w // 8
            return [sheet.subsurface(pygame.Rect(i * block_w, 0, block_w, h)) for i in range(8)]
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return [pygame.Surface((32, 32)) for _ in range(8)]

    def handle_joysticks(self):
        count = pygame.joystick.get_count()
        for i in range(count):
            joy = pygame.joystick.Joystick(i)
            if not joy.get_init(): joy.init()
            name = joy.get_name()
            jid = joy.get_instance_id()
            
            if name.startswith("Gamepad_") and jid not in self.players:
                nick = name.replace("Gamepad_", "")
                self.players[jid] = PlayerBoard(nick, joy, self.player_counter)
                self.player_counter += 1

        # Usuwanie odłączonych graczy
        connected_ids = [pygame.joystick.Joystick(i).get_instance_id() for i in range(count)]
        disconnected = [jid for jid in self.players if jid not in connected_ids]
        for jid in disconnected:
            del self.players[jid]

    def start_game(self):
        for p in self.players.values():
            p.reset()
        if self.playlist:
            pygame.mixer.music.play(-1) # -1 oznacza zapętlenie
        self.state = "PLAYING"

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            self.handle_joysticks()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                
                elif event.type == pygame.JOYBUTTONDOWN:
                    player = self.players.get(event.instance_id)
                    if player:
                        # Mapowanie przycisków: 
                        # 0: A (Insta drop), 1: B (Obrót), 7: Start (Gotowość/Start)
                        # UWAGA: Numery przycisków mogą się różnić zależnie od mapowania evdev na twoim serwerze.
                        
                        if self.state == "MENU":
                            if event.button == 7: # Przycisk START
                                player.ready = not player.ready
                        
                        elif self.state == "PLAYING" and player.alive:
                            if event.button == 0: # Przycisk A -> Insta Drop
                                player.hard_drop()
                            elif event.button == 1: # Przycisk B -> Rotate
                                player.rotate_piece()
                                
                        elif self.state == "LEADERBOARD":
                            if event.button == 7: # START żeby wrócić do menu
                                self.state = "MENU"
                                for p in self.players.values(): p.ready = False

            self.screen.fill((10, 10, 15))

            if self.state == "MENU":
                self.draw_menu()
                # Start gry, gdy przynajmniej 1 gracz jest gotowy i wszyscy podłączeni są gotowi
                if len(self.players) > 0 and all(p.ready for p in self.players.values()):
                    self.start_game()
                    
            elif self.state == "PLAYING":
                self.update_and_draw_playing(dt)
                # Sprawdzenie końca gry
                if len(self.players) > 0 and all(not p.alive for p in self.players.values()):
                    pygame.mixer.music.stop()
                    self.state = "LEADERBOARD"
                    
            elif self.state == "LEADERBOARD":
                self.draw_leaderboard()

            pygame.display.flip()
            
        pygame.quit()
        sys.exit()

    def draw_menu(self):
        title = self.title_font.render("TETRIS LOBBY", True, (255, 255, 255))
        self.screen.blit(title, (BASE_WIDTH//2 - title.get_width()//2, 100))
        
        info = self.font.render("Wciśnij START (na padzie), aby zgłosić gotowość", True, (150, 150, 150))
        self.screen.blit(info, (BASE_WIDTH//2 - info.get_width()//2, 180))

        y = 300
        for p in self.players.values():
            status = "GOTOWY" if p.ready else "OCZEKUJE..."
            color = (50, 255, 50) if p.ready else (255, 50, 50)
            text = self.font.render(f"{p.nickname} - {status}", True, color)
            self.screen.blit(text, (BASE_WIDTH//2 - text.get_width()//2, y))
            y += 40

    def update_and_draw_playing(self, dt):
        num_players = max(1, len(self.players))
        cols = math.ceil(math.sqrt(num_players))
        rows = math.ceil(num_players / cols)
        
        sw, sh = self.screen.get_size()
        cell_w, cell_h = sw // cols, sh // rows
        
        # Marginesy dla Next Piece i etykiet
        max_block_w = (cell_w - 100) // GRID_W 
        max_block_h = (cell_h - 60) // GRID_H
        block_size = min(max_block_w, max_block_h)
        
        for idx, player in enumerate(self.players.values()):
            player.update(dt)
            
            grid_x, grid_y = idx % cols, idx // cols
            board_w = GRID_W * block_size
            board_h = GRID_H * block_size
            
            # Wyrównanie planszy do lewej w jej slocie, by zrobić miejsce po prawej na "Next pieces"
            x_offset = (grid_x * cell_w) + (cell_w - board_w - 60) // 2 
            y_offset = (grid_y * cell_h) + (cell_h - board_h) // 2 + 20
            
            player.draw(self.screen, x_offset, y_offset, block_size, self.block_textures, self.font, self.small_font)

    def draw_leaderboard(self):
        title = self.title_font.render("TABELA WYNIKÓW", True, (255, 215, 0))
        self.screen.blit(title, (BASE_WIDTH//2 - title.get_width()//2, 100))
        
        info = self.font.render("Wciśnij START, aby wrócić do menu", True, (150, 150, 150))
        self.screen.blit(info, (BASE_WIDTH//2 - info.get_width()//2, 180))

        # Sortowanie graczy po wyniku
        sorted_players = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
        
        y = 300
        for idx, p in enumerate(sorted_players):
            color = (255, 215, 0) if idx == 0 else (200, 200, 200) # Złoty dla wygranego
            text = self.font.render(f"{idx + 1}. {p.nickname} - Pkt: {p.score}", True, color)
            self.screen.blit(text, (BASE_WIDTH//2 - text.get_width()//2, y))
            y += 50

if __name__ == "__main__":
    game = Game()
    game.run()