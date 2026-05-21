import pygame
import random
import math
import sys
import os

# --- CONFIGURATION ---
FPS = 60
BASE_WIDTH, BASE_HEIGHT = 1920, 1080
GRID_W, GRID_H = 10, 20

# Global font family – change here to apply everywhere
FONT_NAME = "Arial"

# Padding around each player board (used for layout calculations)
UI_WIDTH_PADDING = 80
UI_HEIGHT_PADDING = 70

SHAPES = [
    [[1, 1, 1, 1]], [[1, 0, 0], [1, 1, 1]], [[0, 0, 1], [1, 1, 1]],
    [[1, 1], [1, 1]], [[0, 1, 1], [1, 1, 0]], [[0, 1, 0], [1, 1, 1]], [[1, 1, 0], [0, 1, 1]]
]

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
        
        # Voting flags
        self.voted_quit = False
        self.voted_yes = False
        self.voted_no = False
        
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
        
        self.target_jid = None 
        self.incoming_garbage = 0
        self.outbound_garbage = 0

    def _generate_piece(self):
        shape_idx = random.randint(0, len(SHAPES) - 1)
        return SHAPES[shape_idx], shape_idx + 1

    def spawn_piece(self):
        self.current_piece, self.color_index = self.piece_queue.pop(0)
        self.piece_queue.append(self._generate_piece())
        self.piece_x = GRID_W // 2 - len(self.current_piece[0]) // 2
        self.piece_y = 0
        
        if self.check_collision(0, 0, self.current_piece):
            self.alive = False

    def check_collision(self, dx, dy, shape):
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    new_x = self.piece_x + x + dx
                    new_y = self.piece_y + y + dy
                    if new_x < 0 or new_x >= GRID_W or new_y >= GRID_H: return True
                    if new_y >= 0 and self.board[new_y][new_x] != 0: return True
        return False

    def rotate_piece(self):
        if not self.alive: return
        rotated = [list(row) for row in zip(*self.current_piece[::-1])]
        if not self.check_collision(0, 0, rotated): self.current_piece = rotated

    def hard_drop(self):
        if not self.alive: return
        while not self.check_collision(0, 1, self.current_piece): self.piece_y += 1
        self.lock_piece()
        self.fall_time = 0

    def lock_piece(self):
        for y, row in enumerate(self.current_piece):
            for x, cell in enumerate(row):
                if cell: self.board[self.piece_y + y][self.piece_x + x] = self.color_index
        
        self.clear_lines()
        self.apply_garbage()
        self.spawn_piece()

    def clear_lines(self):
        new_board = [row for row in self.board if any(cell == 0 for cell in row)]
        lines_cleared = GRID_H - len(new_board)
        for _ in range(lines_cleared): new_board.insert(0, [0 for _ in range(GRID_W)])
        self.board = new_board
        
        if lines_cleared == 2: self.outbound_garbage += 1
        elif lines_cleared == 3: self.outbound_garbage += 2
        elif lines_cleared == 4: self.outbound_garbage += 4
        
        if lines_cleared == 1: self.score += 100
        elif lines_cleared == 2: self.score += 300
        elif lines_cleared == 3: self.score += 500
        elif lines_cleared == 4: self.score += 800

    def apply_garbage(self):
        if self.incoming_garbage > 0:
            for _ in range(self.incoming_garbage):
                hole = random.randint(0, GRID_W - 1)
                garbage_row = [8 if i != hole else 0 for i in range(GRID_W)] 
                self.board.pop(0) 
                self.board.append(garbage_row) 
            self.incoming_garbage = 0

    def update(self, dt):
        if not self.alive: return
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.check_collision(0, 1, self.current_piece): self.piece_y += 1
            else: self.lock_piece()

        self.move_cooldown -= dt
        if self.move_cooldown <= 0:
            axis_x = self.joystick.get_axis(0)
            axis_y = self.joystick.get_axis(1)
            
            if axis_x < -0.5 and not self.check_collision(-1, 0, self.current_piece):
                self.piece_x -= 1
                self.move_cooldown = 120
            elif axis_x > 0.5 and not self.check_collision(1, 0, self.current_piece):
                self.piece_x += 1
                self.move_cooldown = 120
            if axis_y > 0.5 and not self.check_collision(0, 1, self.current_piece): 
                self.piece_y += 1
                self.move_cooldown = 60

    def draw(self, surface, x_offset, y_offset, cell_size, block_textures, font, small_font, players_dict, is_menu=False):
        board_rect = pygame.Rect(x_offset, y_offset, GRID_W * cell_size, GRID_H * cell_size)
        pygame.draw.rect(surface, (20, 20, 20), board_rect)
        pygame.draw.rect(surface, self.color, board_rect, 4)   # kolor gracza
        pygame.draw.rect(surface, (255, 255, 255), board_rect.inflate(8, 8), 2)  # biała ramka

        # Siatka na planszy (delikatne linie)
        grid_color = (255, 255, 255, 30)
        grid_surf = pygame.Surface((GRID_W * cell_size, GRID_H * cell_size), pygame.SRCALPHA)
        for x in range(1, GRID_W):
            pygame.draw.line(grid_surf, grid_color, (x * cell_size, 0), (x * cell_size, GRID_H * cell_size), 1)
        for y in range(1, GRID_H):
            pygame.draw.line(grid_surf, grid_color, (0, y * cell_size), (GRID_W * cell_size, y * cell_size), 1)
        surface.blit(grid_surf, (x_offset, y_offset))

        # Rysowanie bloków
        for y in range(GRID_H):
            for x in range(GRID_W):
                c_idx = self.board[y][x]
                if c_idx > 0:
                    tex = pygame.transform.scale(block_textures[c_idx-1], (cell_size, cell_size))
                    surface.blit(tex, (x_offset + x * cell_size, y_offset + y * cell_size))

        if self.alive and self.current_piece:
            for y, row in enumerate(self.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        tex = pygame.transform.scale(block_textures[self.color_index-1], (cell_size, cell_size))
                        surface.blit(tex, (x_offset + (self.piece_x + x) * cell_size, y_offset + (self.piece_y + y) * cell_size))

        # Nick i punkty
        name_text = font.render(self.nickname, True, self.color)
        score_text = small_font.render(f"Pkt: {self.score}", True, (255, 255, 255))
        surface.blit(name_text, (x_offset, y_offset - 40))
        surface.blit(score_text, (x_offset, y_offset - 20))

        if is_menu and self.voted_quit:
            vote_text = small_font.render("CHCE WYJŚĆ", True, (255, 50, 50))
            surface.blit(vote_text, (x_offset, y_offset - 60))

        # Kolejka klocków
        next_x = x_offset + (GRID_W * cell_size) + 10
        next_y = y_offset
        for shape, color_idx in self.piece_queue:
            for y, row in enumerate(shape):
                for x, cell in enumerate(row):
                    if cell:
                        tex = pygame.transform.scale(block_textures[color_idx-1], (cell_size//2, cell_size//2))
                        surface.blit(tex, (next_x + x*(cell_size//2), next_y + y*(cell_size//2)))
            next_y += 4 * (cell_size // 2)

        # Informacje o celu i śmieciach (tylko w grze)
        if self.alive and not is_menu:
            if self.target_jid and self.target_jid in players_dict:
                target = players_dict[self.target_jid]
                if target.alive:
                    target_label = small_font.render("CEL:", True, (150, 150, 150))
                    target_name = small_font.render(target.nickname, True, target.color)
                    surface.blit(target_label, (next_x, next_y + 10))
                    surface.blit(target_name, (next_x, next_y + 30))
            if self.incoming_garbage > 0:
                warn_text = font.render(f"! ŚMIECI: {self.incoming_garbage} !", True, (255, 50, 50))
                surface.blit(warn_text, (x_offset, y_offset + (GRID_H * cell_size) + 5))

        # Ekran śmierci
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
        pygame.display.set_caption("TETRIS TETRIS TETRIS")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(FONT_NAME, 24, bold=True)
        self.small_font = pygame.font.SysFont(FONT_NAME, 16)
        self.title_font = pygame.font.SysFont(FONT_NAME, 64, bold=True)
        
        self.players = {}
        self.block_textures = self.load_blocks("blocks.png")
        
        self.state = "MENU"
        self.previous_state = "MENU"
        self.player_counter = 0
        
        self.load_music()

    def load_music(self):
        self.playlist = []
        if not os.path.exists('music'):
            os.makedirs('music')
        else:
            for file in os.listdir('music'):
                if file.endswith(('.mp3', '.ogg', '.wav')):
                    self.playlist.append(os.path.join('music', file))
        if self.playlist: pygame.mixer.music.load(self.playlist[0])

    def load_blocks(self, filename):
        try:
            sheet = pygame.image.load(filename).convert_alpha()
            w, h = sheet.get_size()
            block_w = w // 8
            return [sheet.subsurface(pygame.Rect(i * block_w, 0, block_w, h)) for i in range(8)]
        except:
            return [pygame.Surface((32, 32)) for _ in range(8)]

    def reset_all_votes(self):
        for p in self.players.values():
            p.voted_quit = False
            p.voted_yes = False
            p.voted_no = False

    def start_game(self):
        self.reset_all_votes()
        for p in self.players.values(): 
            p.reset()
            self._assign_random_target(p) 
        if self.playlist: pygame.mixer.music.play(-1)
        self.state = "PLAYING"

    def _assign_random_target(self, player):
        alive_jids = [jid for jid, p in self.players.items() if p.alive and p != player]
        player.target_jid = random.choice(alive_jids) if alive_jids else None

    def cycle_target(self, player_jid):
        player = self.players.get(player_jid)
        if not player or not player.alive: return
        
        alive_jids = [jid for jid, p in self.players.items() if p.alive and jid != player_jid]
        if not alive_jids:
            player.target_jid = None
            return
            
        if player.target_jid not in alive_jids:
            player.target_jid = alive_jids[0]
        else:
            current_idx = alive_jids.index(player.target_jid)
            next_idx = (current_idx + 1) % len(alive_jids)
            player.target_jid = alive_jids[next_idx]

    def calculate_optimal_layout(self, num_players, sw, sh):
        best_score = -9999
        best_cols, best_rows, best_block = 1, 1, 1
        
        for c in range(1, num_players + 1):
            r = math.ceil(num_players / c)
            cell_w = sw // c
            cell_h = sh // r
            
            # --- NOWA LOGIKA: priorytet wysokości ---
            max_b_h = (cell_h - UI_HEIGHT_PADDING) // GRID_H
            needed_w = max_b_h * GRID_W + UI_WIDTH_PADDING
            
            if needed_w <= cell_w:
                block = max_b_h
            else:
                max_b_w = (cell_w - UI_WIDTH_PADDING) // GRID_W
                block = max(1, min(max_b_w, max_b_h))
            # ------------------------------------
            
            empty_cells = (c * r) - num_players
            score = (block * 10) - empty_cells
            
            if score > best_score:
                best_score = score
                best_cols = c
                best_rows = r
                best_block = block
                
        best_block = min(best_block, 40)
        return best_cols, best_rows, best_block

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                
                elif event.type == pygame.JOYDEVICEADDED:
                    joy = pygame.joystick.Joystick(event.device_index)
                    name = joy.get_name()
                    jid = joy.get_instance_id()
                    if name.startswith("Gamepad_") and jid not in self.players:
                        nick = name.replace("Gamepad_", "")
                        self.players[jid] = PlayerBoard(nick, joy, self.player_counter)
                        self.player_counter += 1
                        
                elif event.type == pygame.JOYDEVICEREMOVED:
                    jid = event.instance_id
                    if jid in self.players: del self.players[jid]

                elif event.type == pygame.JOYBUTTONDOWN:
                    player = self.players.get(event.instance_id)
                    if not player: continue
                    
                    if self.state == "QUIT_PROMPT":
                        if event.button == 2: # SELECT -> Potwierdź
                            player.voted_yes = True
                            player.voted_no = False
                        elif event.button == 3: # START -> Anuluj
                            player.voted_no = True
                            player.voted_yes = False
                            
                        yes_votes = sum(1 for p in self.players.values() if p.voted_yes)
                        no_votes = sum(1 for p in self.players.values() if p.voted_no)
                        majority = (len(self.players) // 2) + 1 
                        
                        if yes_votes >= majority:
                            running = False 
                        elif no_votes >= majority: 
                            self.state = self.previous_state 
                            self.reset_all_votes()
                            
                    else:
                        if self.state == "MENU":
                            if event.button == 2: # SELECT -> Głosowanie Quit
                                player.voted_quit = not player.voted_quit
                                majority = (len(self.players) // 2) + 1
                                if sum(1 for p in self.players.values() if p.voted_quit) >= majority:
                                    self.previous_state = self.state
                                    self.state = "QUIT_PROMPT"
                                    self.reset_all_votes()
                            elif event.button == 3: # START -> Gotowość
                                player.ready = not player.ready
                        
                        elif self.state == "PLAYING" and player.alive:
                            if event.button == 0: player.hard_drop() # A
                            elif event.button == 1: player.rotate_piece() # B
                            elif event.button == 2: # SELECT -> Celowanie
                                self.cycle_target(event.instance_id)
                                
                        elif self.state == "LEADERBOARD":
                            if event.button == 3: # START
                                self.state = "MENU"
                                for p in self.players.values(): p.ready = False

            # --- Automatyczne przypisywanie celu, jeśli stary cel nie żyje ---
            if self.state == "PLAYING":
                for p in self.players.values():
                    if p.alive:
                        target = self.players.get(p.target_jid)
                        if not target or not target.alive:
                            self._assign_random_target(p)

            # --- Logika śmieci ---
            if self.state == "PLAYING":
                for jid, p in self.players.items():
                    if p.outbound_garbage > 0:
                        target = self.players.get(p.target_jid)
                        if not target or not target.alive:
                            self._assign_random_target(p)
                            target = self.players.get(p.target_jid)
                        if target and target.alive:
                            target.incoming_garbage += p.outbound_garbage
                        p.outbound_garbage = 0

            # --- RENDEROWANIE ---
            self.screen.fill((10, 10, 15))   # szybkie jednolite tło
            bg_state = self.previous_state if self.state == "QUIT_PROMPT" else self.state

            if bg_state == "MENU":
                self.draw_menu()
            elif bg_state == "PLAYING":
                self.update_and_draw_playing(dt if self.state != "QUIT_PROMPT" else 0)
            elif bg_state == "LEADERBOARD":
                self.draw_leaderboard()

            if self.state == "MENU":
                total_quit_votes = sum(1 for p in self.players.values() if p.voted_quit)
                if total_quit_votes > 0:
                    majority = (len(self.players) // 2) + 1
                    vote_info = self.font.render(f"Głosy za wyłączeniem gry: {total_quit_votes} / {majority} (Wciśnij SELECT aby dołączyć)", True, (255, 100, 100))
                    self.screen.blit(vote_info, (BASE_WIDTH//2 - vote_info.get_width()//2, 20))

            if self.state == "QUIT_PROMPT":
                self.draw_quit_prompt()

            # Przejścia między stanami
            if self.state == "MENU":
                if len(self.players) > 0 and all(p.ready for p in self.players.values()):
                    self.start_game()
            elif self.state == "PLAYING":
                if len(self.players) > 0 and all(not p.alive for p in self.players.values()):
                    pygame.mixer.music.stop()
                    self.state = "LEADERBOARD"

            pygame.display.flip()
            
        pygame.quit()
        sys.exit()

    def draw_quit_prompt(self):
        s = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220)) 
        self.screen.blit(s, (0, 0))
        
        y_center = BASE_HEIGHT // 2
        t1 = self.title_font.render("CZY NA PEWNO CHCESZ WYŁĄCZYĆ GRĘ DO SYSTEMU?", True, (255, 50, 50))
        t2 = self.font.render("Wciśnij SELECT by potwierdzić. Wciśnij START by anulować.", True, (255, 255, 255))
        
        self.screen.blit(t1, (BASE_WIDTH//2 - t1.get_width()//2, y_center - 100))
        self.screen.blit(t2, (BASE_WIDTH//2 - t2.get_width()//2, y_center - 20))
        
        yes_votes = sum(1 for p in self.players.values() if p.voted_yes)
        no_votes = sum(1 for p in self.players.values() if p.voted_no)
        majority = (len(self.players) // 2) + 1
        
        v_text = self.font.render(f"WYJŚCIE: {yes_votes}/{majority} głosów   |   ANULOWANIE: {no_votes}/{majority} głosów", True, (255, 215, 0))
        self.screen.blit(v_text, (BASE_WIDTH//2 - v_text.get_width()//2, y_center + 50))

    def draw_menu(self):
        # Wielki tytuł
        title = self.title_font.render("TETRIS TETRIS TETRIS", True, (255, 215, 0))
        self.screen.blit(title, (BASE_WIDTH//2 - title.get_width()//2, 100))

        # Instrukcje
        instructions = [
            "Witaj w Tetris Battle!",
            "Aby dołączyć do gry, podłącz gamepad i naciśnij START.",
            "Gdy wszyscy gracze będą GOTOWI (nacisną START), gra wystartuje automatycznie.",
            "W grze: A = twardy drop, B = obrót, SELECT = zmiana celu.",
            "W menu: START = gotowość, SELECT = głosowanie za wyjściem do systemu.",
        ]
        y = 220
        for line in instructions:
            text = self.small_font.render(line, True, (200, 200, 200))
            self.screen.blit(text, (BASE_WIDTH//2 - text.get_width()//2, y))
            y += 30

        # Lista graczy
        y = 420
        square_w = 20
        gap = 10
        for p in self.players.values():
            status = "GOTOWY" if p.ready else "OCZEKUJE..."
            color = (50, 255, 50) if p.ready else (255, 50, 50)
            text = self.font.render(f"{p.nickname} - {status}", True, color)
            total_w = square_w + gap + text.get_width()
            start_x = BASE_WIDTH//2 - total_w//2
            pygame.draw.rect(self.screen, p.color, (start_x, y, square_w, square_w))
            self.screen.blit(text, (start_x + square_w + gap, y))
            y += 40

    def update_and_draw_playing(self, dt):
        num_players = max(1, len(self.players))
        sw, sh = self.screen.get_size()
        
        cols, rows, block_size = self.calculate_optimal_layout(num_players, sw, sh)
        cell_w = sw // cols
        cell_h = sh // rows
        
        for idx, player in enumerate(self.players.values()):
            player.update(dt)
            grid_x = idx % cols
            grid_y = idx // cols
            
            items_in_this_row = cols
            if grid_y == rows - 1:
                items_in_this_row = num_players - (rows - 1) * cols
            
            row_padding = (sw - (items_in_this_row * cell_w)) // 2
            
            total_player_w = (GRID_W * block_size) + UI_WIDTH_PADDING
            total_player_h = (GRID_H * block_size) + UI_HEIGHT_PADDING
            
            x_offset = row_padding + (grid_x * cell_w) + (cell_w - total_player_w) // 2 
            y_offset = (grid_y * cell_h) + (cell_h - total_player_h) // 2 + 50 
            
            player.draw(self.screen, x_offset, y_offset, block_size, self.block_textures, self.font, self.small_font, self.players, is_menu=False)

    def draw_leaderboard(self):
        title = self.title_font.render("TABELA WYNIKÓW", True, (255, 215, 0))
        self.screen.blit(title, (BASE_WIDTH//2 - title.get_width()//2, 100))
        info = self.font.render("Wciśnij START aby wrócić do Lobby", True, (150, 150, 150))
        self.screen.blit(info, (BASE_WIDTH//2 - info.get_width()//2, 180))
        y = 300
        for idx, p in enumerate(sorted(self.players.values(), key=lambda p: p.score, reverse=True)):
            color = (255, 215, 0) if idx == 0 else (200, 200, 200)
            text = self.font.render(f"{idx + 1}. {p.nickname} - Pkt: {p.score}", True, color)
            self.screen.blit(text, (BASE_WIDTH//2 - text.get_width()//2, y))
            y += 50


if __name__ == "__main__":
    game = Game()
    game.run()