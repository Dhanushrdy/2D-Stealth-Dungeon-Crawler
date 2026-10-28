import pygame
import random
import heapq
import os
import math
import sys
import json

# --- 1. Configuration ---
GRID_SIZE = 33
TILE_SIZE = 20
SCREEN_RES = GRID_SIZE * TILE_SIZE
UI_HEIGHT = 45
WINDOW_HEIGHT = SCREEN_RES + UI_HEIGHT
FPS = 60 

# Colors
WHITE, GREY, GREEN, RED, YELLOW, BLACK, BLUE = (240,240,240), (120,120,120), (34,139,34), (255,50,50), (255,215,0), (0,0,0), (0,0,255)

# --- 2. Initialization & Asset Loading ---
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((SCREEN_RES, WINDOW_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
pygame.display.set_caption("Dungon Crawler")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Verdana", 20, bold=True)
title_font = pygame.font.SysFont("Verdana", 48, bold=True)
sub_font = pygame.font.SysFont("Verdana", 24, bold=False)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_save_path():
    appdata = os.getenv('APPDATA')
    if appdata:
        save_dir = os.path.join(appdata, "DungeonCrawler")
        if not os.path.exists(save_dir):
            try: os.makedirs(save_dir)
            except: pass
        return os.path.join(save_dir, "save.json")
    
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "save.json")
    return os.path.abspath("save.json")

def load_settings():
    path = get_save_path()
    defs = {
        "fps": 60, "shadows": True, "last_save": "",
        "slots": {}
    }
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                d = json.load(f)
                defs["fps"] = d.get("fps", defs["fps"])
                defs["shadows"] = d.get("shadows", defs["shadows"])
                
                if "last_save" in d: defs["last_save"] = str(d["last_save"])
                elif "last_slot" in d: defs["last_save"] = str(d["last_slot"])
                
                if "slots" in d:
                    for k, v in d["slots"].items():
                        if isinstance(v, int):
                            defs["slots"][str(k)] = {"level": v}
                        elif isinstance(v, dict) and "level" in v:
                            defs["slots"][str(k)] = v
        except: pass
    return defs

def save_settings(f, shd, l_save, slots):
    try:
        with open(get_save_path(), "w") as fw:
            json.dump({"fps": f, "shadows": shd, "last_save": l_save, "slots": slots}, fw)
    except: pass

def load_sprite(name, color_fallback):
    path = resource_path(name)
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
    return None

def load_snd(name):
    path = resource_path(name)
    if os.path.exists(path): return pygame.mixer.Sound(path)
    return None

# Load Assets
P_IMG, E_IMG = load_sprite("player.png", YELLOW), load_sprite("enemy.png", RED)
W_IMG, B_IMG = load_sprite("wall.png", GREY), load_sprite("bush.png", GREEN)
snd_walk, snd_run = load_snd("walk.wav"), load_snd("run.wav")
snd_spotted, snd_win, snd_lose = load_snd("alert.wav"), load_snd("win.wav"), load_snd("lose.wav")
snd_hide, snd_skelly = load_snd("hide.wav"), load_snd("skeleton.wav")

icon_path = resource_path("game_icon.png")
if os.path.exists(icon_path):
    pygame.display.set_icon(pygame.image.load(icon_path))

bg_music_path = resource_path("background_music.mp3")
if os.path.exists(bg_music_path):
    pygame.mixer.music.load(bg_music_path)
    pygame.mixer.music.set_volume(0.15)
    pygame.mixer.music.play(-1)

# Balance Volumes (Walk stays at max 1.0)
if snd_walk: snd_walk.set_volume(1.0)
if snd_run: snd_run.set_volume(0.5)
if snd_hide: snd_hide.set_volume(0.7)
if snd_skelly: snd_skelly.set_volume(0.4)
if snd_spotted: snd_spotted.set_volume(0.6)

walk_ch = pygame.mixer.Channel(0)
skelly_ch = pygame.mixer.Channel(1)
alert_ch = pygame.mixer.Channel(2)

# --- 3. Pathfinding & World Logic ---
def a_star(grid, start, goal):
    neighbors = [(0,1), (0,-1), (1,0), (-1,0)]
    oheap = []
    heapq.heappush(oheap, (0, start))
    came_from, gscore = {}, {start: 0}
    while oheap:
        current = heapq.heappop(oheap)[1]
        if current == goal:
            path = []
            while current in came_from:
                path.append(current); current = came_from[current]
            return path[::-1]
        for dx, dy in neighbors:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < GRID_SIZE and 0 <= neighbor[1] < GRID_SIZE:
                if grid[neighbor[0]][neighbor[1]] == 1: continue 
                cost = 5 if grid[neighbor[0]][neighbor[1]] == 2 else 1 
                temp_g = gscore[current] + cost
                if temp_g < gscore.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    gscore[neighbor] = temp_g
                    f = temp_g + abs(neighbor[0]-goal[0]) + abs(neighbor[1]-goal[1])
                    heapq.heappush(oheap, (f, neighbor))
    return []

def generate_maze(grid):
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE): grid[x][y] = 1
    stack = [(1, 1)]; grid[1][1] = 0
    while stack:
        curr = stack[-1]
        dirs = [(0, 2), (0, -2), (2, 0), (-2, 0)]
        random.shuffle(dirs)
        found = False
        for dx, dy in dirs:
            nx, ny = curr[0] + dx, curr[1] + dy
            if 0 < nx < GRID_SIZE-1 and 0 < ny < GRID_SIZE-1 and grid[nx][ny] == 1:
                grid[curr[0] + dx//2][curr[1] + dy//2] = 0
                grid[nx][ny] = 0
                stack.append((nx, ny)); found = True; break
        if not found: stack.pop()
        
    # Create alternate paths (braid the maze) by breaking random internal walls
    for _ in range(80):
        rx, ry = random.randint(2, GRID_SIZE-3), random.randint(2, GRID_SIZE-3)
        if grid[rx][ry] == 1: grid[rx][ry] = 0

    for _ in range(50):
        rx, ry = random.randint(1, GRID_SIZE-2), random.randint(1, GRID_SIZE-2)
        if grid[rx][ry] == 0: grid[rx][ry] = 2

# --- 4. Special Effects ---
def draw_fog(surf, p_pos):
    # Mask Surface
    fog_mask = pygame.Surface((SCREEN_RES, SCREEN_RES))
    fog_mask.fill((15, 15, 25)) # Very dark blue
    
    # Vision Circle (Radius of 6 tiles)
    radius = 120
    light_surf = pygame.Surface((radius * 2, radius * 2))
    light_surf.fill((0, 0, 0))
    
    # Soft Gradient Edge
    for r in range(radius, 0, -4):
        intensity = int(255 * (1 - r / radius))
        pygame.draw.circle(light_surf, (intensity, intensity, intensity), (radius, radius), r)
    
    # Center light on player
    fog_mask.blit(light_surf, (p_pos[0]*TILE_SIZE - radius + 10, p_pos[1]*TILE_SIZE - radius + 10), 
                  special_flags=pygame.BLEND_RGB_ADD)
    surf.blit(fog_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

class Enemy:
    def __init__(self, spawn_grid=None):
        if spawn_grid:
            while True:
                tx, ty = random.randint(1, GRID_SIZE-2), random.randint(1, GRID_SIZE-2)
                if spawn_grid[tx][ty] not in (1, 2) and (tx, ty) != (GRID_SIZE-2, GRID_SIZE-2) and (tx, ty) != (1, 1):
                    self.x, self.y = tx, ty
                    break
        else:
            self.x, self.y = 1, 1
        self.state, self.path, self.timer = "WANDER", [], 0
        self.move_delay, self.last_move = 170, 0
        self.angle = 0

    def update(self, p_pos, grid, now, all_enemies=None):
        dist = abs(self.x - p_pos[0]) + abs(self.y - p_pos[1])
        spotted = dist <= 5 and grid[p_pos[0]][p_pos[1]] != 2
        
        if spotted and self.state != "CHASE":
            if snd_spotted and not alert_ch.get_busy(): alert_ch.play(snd_spotted)

        if spotted:
            self.state = "CHASE"
            if not self.path or tuple(p_pos) != self.path[-1]:
                self.path = a_star(grid, (self.x, self.y), p_pos)
        elif self.state == "CHASE":
            self.state = "SEARCH"; self.timer = now
        
        if self.state == "SEARCH" and now - self.timer > 5000:
            self.state = "WANDER"; self.path = []

        if self.state == "WANDER" and not self.path:
            tx, ty = random.randint(1, GRID_SIZE-2), random.randint(1, GRID_SIZE-2)
            if grid[tx][ty] != 1: self.path = a_star(grid, (self.x, self.y), (tx, ty))

        if self.path and now - self.last_move > self.move_delay:
            nxt = self.path[0]
            blocked = False
            if all_enemies:
                for other in all_enemies:
                    if other is not self and (other.x, other.y) == nxt:
                        blocked = True; break
            if not blocked:
                nxt = self.path.pop(0)
                dx, dy = nxt[0] - self.x, nxt[1] - self.y
                self.angle = math.degrees(math.atan2(-dy, dx))
                self.x, self.y = nxt
                self.last_move = now
                if snd_skelly and not skelly_ch.get_busy(): skelly_ch.play(snd_skelly)
            else:
                self.last_move = now

    def draw_vision(self, surf):
        cone_surf = pygame.Surface((TILE_SIZE*10, TILE_SIZE*10), pygame.SRCALPHA)
        pygame.draw.arc(cone_surf, (255, 0, 0, 80), (0, 0, TILE_SIZE*10, TILE_SIZE*10), 
                        math.radians(-self.angle-30), math.radians(-self.angle+30), TILE_SIZE*5)
        surf.blit(cone_surf, (self.x*TILE_SIZE - TILE_SIZE*4.5, self.y*TILE_SIZE - TILE_SIZE*4.5))

# --- 5. Main Loop ---
grid = [[1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
generate_maze(grid)
player_pos = [GRID_SIZE-2, GRID_SIZE-2]
player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1))
settings = load_settings()
GAME_FPS = settings["fps"]
SHOW_SHADOWS = settings["shadows"]
current_save = settings["last_save"]
save_slots = settings["slots"]

level = save_slots[current_save]["level"] if current_save in save_slots and save_slots[current_save] else 1
enemies = [Enemy(grid) for _ in range(level)]
stamina, game_state = 100.0, "MENU"
save_list_mode = "LOAD"
target_slot_idx = 0
prev_state = "MENU"
player_last_move = 0

menu_idx, settings_idx, save_list_idx, modal_idx = 0, 0, 0, 0
input_text = ""
main_menu_opts = ["Continue", "Load Game", "New Game", "Settings", "Quit"]

while True:
    now = pygame.time.get_ticks()
    screen.fill(BLACK)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit(0)
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if game_state == "MENU":
                for i in range(len(main_menu_opts)):
                    if pygame.Rect(SCREEN_RES//2 - 150, 280 + i * 45, 300, 40).collidepoint(mx, my): menu_idx = i
            elif game_state == "SAVE_LIST":
                for i in range(5):
                    if pygame.Rect(SCREEN_RES//2 - 175, 160 + i * 60, 350, 45).collidepoint(mx, my): save_list_idx = i
            elif game_state == "WON":
                for i in range(4):
                    if pygame.Rect(SCREEN_RES//2 - 150, (SCREEN_RES//2 - 130) + 90 + i*40, 300, 30).collidepoint(mx, my): modal_idx = i
            elif game_state == "LOST":
                for i in range(3):
                    if pygame.Rect(SCREEN_RES//2 - 150, (SCREEN_RES//2 - 130) + 110 + i*40, 300, 30).collidepoint(mx, my): modal_idx = i
            elif game_state == "PAUSED":
                for i in range(5):
                    if pygame.Rect(SCREEN_RES//2 - 150, (SCREEN_RES//2 - 130) + 100 + i*35, 300, 30).collidepoint(mx, my): modal_idx = i
            elif game_state == "SETTINGS":
                if pygame.Rect(SCREEN_RES//2 - 210, SCREEN_RES//2 - 130 + 90, 420, 40).collidepoint(mx, my): settings_idx = 0
                elif pygame.Rect(SCREEN_RES//2 - 210, SCREEN_RES//2 - 130 + 140, 420, 40).collidepoint(mx, my): settings_idx = 1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if game_state == "MENU":
                for i in range(len(main_menu_opts)):
                    if pygame.Rect(SCREEN_RES//2 - 150, 280 + i * 45, 300, 40).collidepoint(mx, my):
                        menu_idx = i
                        sel = main_menu_opts[menu_idx]
                        if sel == "Continue":
                            if current_save in save_slots and save_slots[current_save]: 
                                level = save_slots[current_save]["level"]
                                generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]
                                player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); game_state = "PLAYING"
                        elif sel == "Load Game": 
                            game_state = "SAVE_LIST"; save_list_idx = 0; save_list_mode = "LOAD"
                            save_keys = [k for k, v in save_slots.items() if v is not None]
                        elif sel == "New Game": 
                            game_state = "SAVE_LIST"; save_list_idx = 0; save_list_mode = "NEW"
                            save_keys = [k for k, v in save_slots.items() if v is not None]
                        elif sel == "Settings": prev_state, game_state = "MENU", "SETTINGS"
                        elif sel == "Quit": pygame.quit(); sys.exit(0)
                        break
            elif game_state == "SAVE_LIST":
                display_slots = (save_keys + [None] * 5)[:5]
                for i, k in enumerate(display_slots):
                    rect_y = 160 + i * 60
                    if k is not None:
                        del_rect = pygame.Rect(SCREEN_RES//2 + 135, rect_y + 8, 30, 30)
                        if del_rect.collidepoint(mx, my):
                            del save_slots[k]
                            save_keys = [sk for sk in save_slots.keys() if save_slots[sk] is not None]
                            save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
                            continue
                            
                    if pygame.Rect(SCREEN_RES//2 - 175, rect_y, 350, 45).collidepoint(mx, my):
                        if save_list_mode == "LOAD" and k is not None:
                            current_save = k; level = save_slots[k]["level"]
                            save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
                            generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]
                            player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); game_state = "PLAYING"
                            break
                        elif save_list_mode == "NEW":
                            target_slot_idx = i
                            game_state = "NAME_INPUT"; input_text = ""
                            break
            elif game_state == "WON":
                opts = [("Continue", 0), ("Replay Level", 1), ("Main Menu", 2), ("Quit to Desktop", 3)]
                for i, (name, _id) in enumerate(opts):
                    if pygame.Rect(SCREEN_RES//2 - 150, (SCREEN_RES//2 - 130) + 90 + i*40, 300, 30).collidepoint(mx, my):
                        modal_idx = i
                        if modal_idx == 0: generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                        elif modal_idx == 1: level = max(1, level - 1); save_slots[current_save] = {"level": level}; save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots); generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                        elif modal_idx == 2: game_state = "MENU"
                        elif modal_idx == 3: pygame.quit(); sys.exit(0)
                        break
            elif game_state == "LOST":
                opts = [("Restart Level", pygame.K_r), ("Main Menu", pygame.K_m), ("Quit to Desktop", pygame.K_q)]
                for i, (name, key) in enumerate(opts):
                    if pygame.Rect(SCREEN_RES//2 - 150, (SCREEN_RES//2 - 130) + 110 + i*40, 300, 30).collidepoint(mx, my):
                        if key == pygame.K_q: pygame.quit(); sys.exit(0)
                        elif key == pygame.K_m: game_state = "MENU"
                        elif key == pygame.K_r:
                            generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"
                            player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1))
                            if os.path.exists(bg_music_path): pygame.mixer.music.play(-1)
                        break
            elif game_state == "PAUSED":
                opts = [("Resume", pygame.K_ESCAPE), ("Settings", pygame.K_s), ("Restart Level", pygame.K_r), ("Main Menu", pygame.K_m), ("Quit to Desktop", pygame.K_q)]
                for i, (name, key) in enumerate(opts):
                    if pygame.Rect(SCREEN_RES//2 - 150, SCREEN_RES//2 - 130 + 100 + i*35, 300, 30).collidepoint(mx, my):
                        if key == pygame.K_ESCAPE: game_state = "PLAYING"
                        elif key == pygame.K_q: pygame.quit(); sys.exit(0)
                        elif key == pygame.K_m: game_state = "MENU"
                        elif key == pygame.K_s: prev_state, game_state = "PAUSED", "SETTINGS"
                        elif key == pygame.K_r:
                            generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"
                            player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1))
                            if os.path.exists(bg_music_path): pygame.mixer.music.play(-1)
                        break
            elif game_state == "SETTINGS":
                if pygame.Rect(SCREEN_RES//2 - 210, SCREEN_RES//2 - 130 + 90, 420, 40).collidepoint(mx, my):
                    settings_idx = 0
                    opts = [30, 60, 144]
                    curr = opts.index(GAME_FPS) if GAME_FPS in opts else 1
                    GAME_FPS = opts[(curr + 1) % len(opts)]
                elif pygame.Rect(SCREEN_RES//2 - 210, SCREEN_RES//2 - 130 + 140, 420, 40).collidepoint(mx, my):
                    settings_idx = 1; SHOW_SHADOWS = not SHOW_SHADOWS
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE: 
                if game_state == "PLAYING": prev_state = "PLAYING"; game_state = "PAUSED"; modal_idx = 0; walk_ch.stop()
                elif game_state == "PAUSED": game_state = "PLAYING"
                elif game_state == "SETTINGS": 
                    save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
                    game_state = prev_state
                elif game_state in ("SAVE_LIST", "NAME_INPUT"): game_state = "MENU"
                else: pygame.quit(); sys.exit(0)
            elif game_state == "MENU":
                if event.key == pygame.K_UP: menu_idx = max(0, menu_idx - 1)
                elif event.key == pygame.K_DOWN: menu_idx = min(len(main_menu_opts)-1, menu_idx + 1)
                elif event.key == pygame.K_RETURN:
                    sel = main_menu_opts[menu_idx]
                    if sel == "Continue":
                        if current_save in save_slots and save_slots[current_save]: 
                            level = save_slots[current_save]["level"]
                            generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]
                            player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); game_state = "PLAYING"
                    elif sel == "Load Game":
                        game_state = "SAVE_LIST"; save_list_idx = 0; save_list_mode = "LOAD"
                        save_keys = [k for k, v in save_slots.items() if v is not None]
                    elif sel == "New Game":
                        game_state = "SAVE_LIST"; save_list_idx = 0; save_list_mode = "NEW"
                        save_keys = [k for k, v in save_slots.items() if v is not None]
                    elif sel == "Settings": prev_state, game_state = "MENU", "SETTINGS"
                    elif sel == "Quit": pygame.quit(); sys.exit(0)
            elif game_state == "SAVE_LIST":
                if event.key == pygame.K_UP: save_list_idx = max(0, save_list_idx - 1)
                elif event.key == pygame.K_DOWN: save_list_idx = min(4, save_list_idx + 1)
                elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    display_slots = (save_keys + [None] * 5)[:5]
                    k = display_slots[save_list_idx]
                    if k is not None:
                        del save_slots[k]
                        save_keys = [sk for sk in save_slots.keys() if save_slots[sk] is not None]
                        save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
                elif event.key == pygame.K_RETURN:
                    display_slots = (save_keys + [None] * 5)[:5]
                    k = display_slots[save_list_idx]
                    if save_list_mode == "LOAD" and k is not None:
                        current_save = k
                        level = save_slots[current_save]["level"]
                        save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
                        generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]
                        player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); game_state = "PLAYING"
                    elif save_list_mode == "NEW":
                        target_slot_idx = save_list_idx
                        game_state = "NAME_INPUT"; input_text = ""
            elif game_state == "NAME_INPUT":
                if event.key == pygame.K_RETURN and input_text.strip():
                    current_save = input_text.strip()
                    level = 1
                    display_slots = (save_keys + [None] * 5)[:5]
                    new_slots = {}
                    for j in range(5):
                        if j == target_slot_idx:
                            new_slots[current_save] = {"level": level}
                        else:
                            old_k = display_slots[j]
                            if old_k is not None and old_k != current_save:
                                new_slots[old_k] = save_slots[old_k]
                    save_slots = new_slots
                    save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
                    generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]
                    player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); game_state = "PLAYING"
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isprintable() and len(input_text) < 15:
                    input_text += event.unicode
            elif game_state in ("WON", "LOST", "PAUSED"):
                if game_state == "WON": opts_len = 4
                elif game_state == "LOST": opts_len = 3
                else: opts_len = 5
                
                if event.key == pygame.K_UP: modal_idx = max(0, modal_idx - 1)
                elif event.key == pygame.K_DOWN: modal_idx = min(opts_len - 1, modal_idx + 1)
                elif event.key == pygame.K_RETURN:
                    if game_state == "WON":
                        if modal_idx == 0: generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                        elif modal_idx == 1: level = max(1, level - 1); save_slots[current_save] = {"level": level}; save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots); generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                        elif modal_idx == 2: game_state = "MENU"
                        elif modal_idx == 3: pygame.quit(); sys.exit(0)
                    elif game_state == "LOST":
                        if modal_idx == 0: generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                        elif modal_idx == 1: game_state = "MENU"
                        elif modal_idx == 2: pygame.quit(); sys.exit(0)
                    elif game_state == "PAUSED":
                        if modal_idx == 0: game_state = "PLAYING"
                        elif modal_idx == 1: prev_state, game_state = "PAUSED", "SETTINGS"
                        elif modal_idx == 2: generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                        elif modal_idx == 3: game_state = "MENU"
                        elif modal_idx == 4: pygame.quit(); sys.exit(0)
                elif event.key == pygame.K_ESCAPE and game_state == "PAUSED": game_state = "PLAYING"
                elif event.key == pygame.K_r and game_state in ("LOST", "PAUSED"): generate_maze(grid); player_pos = [GRID_SIZE-2, GRID_SIZE-2]; enemies = [Enemy(grid) for _ in range(level)]; stamina = 100.0; game_state = "PLAYING"; player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1)); (pygame.mixer.music.play(-1) if os.path.exists(bg_music_path) else None)
                elif event.key == pygame.K_m and game_state in ("LOST", "PAUSED"): game_state = "MENU"
                elif event.key == pygame.K_q and game_state in ("LOST", "PAUSED", "WON"): pygame.quit(); sys.exit(0)
                elif event.key == pygame.K_s and game_state == "PAUSED": prev_state, game_state = "PAUSED", "SETTINGS"
            elif game_state == "SETTINGS":
                if event.key == pygame.K_UP: settings_idx = max(0, settings_idx - 1)
                elif event.key == pygame.K_DOWN: settings_idx = min(1, settings_idx + 1)
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    if settings_idx == 0:
                        opts = [30, 60, 144]
                        curr = opts.index(GAME_FPS) if GAME_FPS in opts else 1
                        GAME_FPS = opts[(curr + (1 if event.key == pygame.K_RIGHT else -1)) % len(opts)]
                    elif settings_idx == 1: SHOW_SHADOWS = not SHOW_SHADOWS

    if game_state == "PLAYING":
        keys = pygame.key.get_pressed()
        sprinting = keys[pygame.K_LSHIFT] and stamina >= 7
        cooldown = 85 if sprinting else 155 
        
        # Audio State Management
        is_moving_input = keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        if not is_moving_input or (now - player_last_move > cooldown + 50):
            if walk_ch.get_busy():
                walk_ch.stop()
        else:
            expected_snd = snd_hide if grid[player_pos[0]][player_pos[1]] == 2 else (snd_run if sprinting else snd_walk)
            if expected_snd and (walk_ch.get_sound() != expected_snd or not walk_ch.get_busy()):
                walk_ch.play(expected_snd, loops=-1)

        if now - player_last_move > cooldown:
            moved = False
            if keys[pygame.K_UP] and player_pos[1] > 0 and grid[player_pos[0]][player_pos[1]-1] != 1:
                player_pos[1] -= 1; moved = True
            elif keys[pygame.K_DOWN] and player_pos[1] < GRID_SIZE-1 and grid[player_pos[0]][player_pos[1]+1] != 1:
                player_pos[1] += 1; moved = True
            elif keys[pygame.K_LEFT] and player_pos[0] > 0 and grid[player_pos[0]-1][player_pos[1]] != 1:
                player_pos[0] -= 1; moved = True
            elif keys[pygame.K_RIGHT] and player_pos[0] < GRID_SIZE-1 and grid[player_pos[0]+1][player_pos[1]] != 1:
                player_pos[0] += 1; moved = True
            
            if moved:
                player_last_move = now
                if sprinting: stamina -= 7
                player_path_to_goal = a_star(grid, tuple(player_pos), (1, 1))
        
        if not keys[pygame.K_LSHIFT] and stamina < 100: stamina += 0.5
        
        for e in enemies:
            e.update(tuple(player_pos), grid, now, enemies)
            if player_pos == [e.x, e.y]: 
                game_state = "LOST"; modal_idx = 0; pygame.mixer.music.stop(); walk_ch.stop(); (snd_lose.play() if snd_lose else None)
        
        if game_state == "PLAYING" and player_pos == [1, 1]: 
            level += 1
            if current_save not in save_slots: save_slots[current_save] = {}
            save_slots[current_save]["level"] = level
            save_settings(GAME_FPS, SHOW_SHADOWS, current_save, save_slots)
            game_state = "WON"; modal_idx = 0; pygame.mixer.music.stop(); walk_ch.stop(); (snd_win.play() if snd_win else None)

    # Rendering
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            p = (x*TILE_SIZE, y*TILE_SIZE)
            
            # Draw floor pattern everywhere first (Wooden Floor)
            floor_color = (120, 75, 45) if (x + y) % 2 == 0 else (105, 60, 35)
            pygame.draw.rect(screen, floor_color, (p[0], p[1], TILE_SIZE, TILE_SIZE))
            
            if grid[x][y] == 1: 
                if W_IMG: screen.blit(W_IMG, p)
                else: pygame.draw.rect(screen, GREY, (p[0],p[1],TILE_SIZE,TILE_SIZE))
            elif grid[x][y] == 2:
                if B_IMG: screen.blit(B_IMG, p)
                else: pygame.draw.rect(screen, GREEN, (p[0],p[1],TILE_SIZE,TILE_SIZE))

    pygame.draw.rect(screen, YELLOW, (1*TILE_SIZE, 1*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    
    # Draw path to goal
    if player_path_to_goal:
        points = [(player_pos[0]*TILE_SIZE + TILE_SIZE//2, player_pos[1]*TILE_SIZE + TILE_SIZE//2)]
        for nx, ny in player_path_to_goal:
            points.append((nx*TILE_SIZE + TILE_SIZE//2, ny*TILE_SIZE + TILE_SIZE//2))
        if len(points) > 1:
            pygame.draw.lines(screen, BLUE, False, points, 3)

    for e in enemies:
        e.draw_vision(screen)
    
    for e in enemies:
        if E_IMG: screen.blit(E_IMG, (e.x*TILE_SIZE, e.y*TILE_SIZE))
        else: pygame.draw.rect(screen, RED, (e.x*TILE_SIZE, e.y*TILE_SIZE, TILE_SIZE, TILE_SIZE))
    
    if P_IMG: screen.blit(P_IMG, (player_pos[0]*TILE_SIZE, player_pos[1]*TILE_SIZE))
    else: pygame.draw.rect(screen, YELLOW, (player_pos[0]*TILE_SIZE, player_pos[1]*TILE_SIZE, TILE_SIZE, TILE_SIZE))

    # Apply Shadow Fog
    if game_state == "PLAYING" and SHOW_SHADOWS:
        draw_fog(screen, player_pos)

    # UI (Always above fog)
    if game_state == "PLAYING" or game_state in ("WON", "LOST"):
        # HUD Panel (Bottom)
        hud_bg = pygame.Surface((SCREEN_RES, UI_HEIGHT), pygame.SRCALPHA)
        hud_bg.fill((20, 20, 20, 230))
        pygame.draw.line(hud_bg, (100, 100, 100), (0, 0), (SCREEN_RES, 0), 2)
        screen.blit(hud_bg, (0, SCREEN_RES))
        
        # Level text
        lvl_text = font.render(f"LEVEL {level}", True, (220, 220, 220))
        screen.blit(lvl_text, (20, SCREEN_RES + 10))
        
        # Stamina Bar
        bar_w, bar_h = 160, 14
        bar_x, bar_y = SCREEN_RES - 180, SCREEN_RES + 15
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h)) # Background
        pygame.draw.rect(screen, (0, 220, 80), (bar_x, bar_y, int((stamina/100) * bar_w), bar_h)) # Fill
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h), 2) # Border
        stam_txt = font.render("STAMINA", True, (200, 200, 200))
        stam_txt = pygame.transform.scale(stam_txt, (80, 14))
        screen.blit(stam_txt, (bar_x - 90, SCREEN_RES + 15))

        # Alert System
        if any(e.state == "CHASE" for e in enemies):
            alert_bg = pygame.Surface((180, 36), pygame.SRCALPHA)
            alert_bg.fill((200, 0, 0, math.floor(abs(math.sin(now/150)) * 180) + 50))
            pygame.draw.rect(alert_bg, (255, 50, 50), (0, 0, 180, 36), 2)
            screen.blit(alert_bg, (SCREEN_RES//2 - 90, SCREEN_RES + 4))
            alert_txt = font.render("! SPOTTED !", True, (255, 255, 255))
            screen.blit(alert_txt, (SCREEN_RES//2 - alert_txt.get_width()//2, SCREEN_RES + 8))

    if game_state == "MENU":
        screen.fill((10, 10, 15))
        for i in range(0, SCREEN_RES, TILE_SIZE*2):
            pygame.draw.line(screen, (30, 30, 40), (i, 0), (i, SCREEN_RES))
            pygame.draw.line(screen, (30, 30, 40), (0, i), (SCREEN_RES, i))
        
        title = title_font.render("DUNGEON", True, (200, 200, 200))
        title2 = title_font.render("CRAWLER", True, (200, 0, 0))
        screen.blit(title, (SCREEN_RES//2 - title.get_width()//2, 80))
        screen.blit(title2, (SCREEN_RES//2 - title2.get_width()//2, 140))
        
        for i, opt in enumerate(main_menu_opts):
            can_continue = current_save and current_save in save_slots and save_slots[current_save] is not None
            c = (100, 100, 100) if (opt == "Continue" and not can_continue) else ((255, 255, 0) if i == menu_idx else (200, 200, 200))
            surf = font.render(opt, True, c)
            screen.blit(surf, (SCREEN_RES//2 - surf.get_width()//2, 280 + i * 45))

    elif game_state == "SAVE_LIST":
        screen.fill((10, 10, 15))
        for i in range(0, SCREEN_RES, TILE_SIZE*2):
            pygame.draw.line(screen, (30, 30, 40), (i, 0), (i, SCREEN_RES))
            pygame.draw.line(screen, (30, 30, 40), (0, i), (SCREEN_RES, i))
            
        title_surf = title_font.render("LOAD GAME" if save_list_mode == "LOAD" else "SELECT SLOT", True, (255, 255, 255))
        screen.blit(title_surf, (SCREEN_RES//2 - title_surf.get_width()//2, 60))
        
        display_slots = (save_keys + [None] * 5)[:5]
        for i, k in enumerate(display_slots):
            is_sel = (i == save_list_idx)
            bg_c = (60, 60, 60) if is_sel else (30, 30, 30)
            txt_c = (255, 255, 0) if is_sel else (200, 200, 200)
            
            rect_y = 160 + i * 60
            pygame.draw.rect(screen, bg_c, (SCREEN_RES//2 - 175, rect_y, 350, 45))
            pygame.draw.rect(screen, txt_c, (SCREEN_RES//2 - 175, rect_y, 350, 45), 2)
            
            if k is not None:
                s_data = save_slots[k]
                disp_txt = f"{k} - Level {s_data['level']}"
                surf = font.render(disp_txt, True, txt_c)
                screen.blit(surf, (SCREEN_RES//2 - surf.get_width()//2, rect_y + 8))
                
                del_rect = pygame.Rect(SCREEN_RES//2 + 135, rect_y + 8, 30, 30)
                mx, my = pygame.mouse.get_pos()
                del_c = (255, 50, 50) if del_rect.collidepoint(mx, my) else (150, 0, 0)
                pygame.draw.rect(screen, del_c, del_rect)
                pygame.draw.rect(screen, (200, 200, 200), del_rect, 1)
                x_txt = sub_font.render("X", True, (255, 255, 255))
                screen.blit(x_txt, (del_rect.centerx - x_txt.get_width()//2, del_rect.centery - x_txt.get_height()//2 - 2))
            else:
                disp_txt = "Empty"
                surf = font.render(disp_txt, True, (150, 150, 150))
                screen.blit(surf, (SCREEN_RES//2 - surf.get_width()//2, rect_y + 8))
            


    elif game_state == "NAME_INPUT":
        screen.fill((10, 10, 15))
        for i in range(0, SCREEN_RES, TILE_SIZE*2):
            pygame.draw.line(screen, (30, 30, 40), (i, 0), (i, SCREEN_RES))
            pygame.draw.line(screen, (30, 30, 40), (0, i), (SCREEN_RES, i))
            
        title_surf = title_font.render("NEW GAME", True, (255, 255, 255))
        screen.blit(title_surf, (SCREEN_RES//2 - title_surf.get_width()//2, 80))
        
        prompt_txt = font.render("Enter Save Name:", True, (200, 200, 200))
        screen.blit(prompt_txt, (SCREEN_RES//2 - prompt_txt.get_width()//2, 220))
        
        input_rect = pygame.Rect(SCREEN_RES//2 - 200, 260, 400, 50)
        pygame.draw.rect(screen, (30, 30, 40), input_rect)
        pygame.draw.rect(screen, (255, 255, 0), input_rect, 3)
        
        disp_text = input_text + ("_" if now % 1000 < 500 else "")
        txt_surf = font.render(disp_text, True, (255, 255, 255))
        screen.blit(txt_surf, (input_rect.x + 15, input_rect.y + 12))        


    elif game_state in ("WON", "LOST", "PAUSED", "SETTINGS"):
        overlay = pygame.Surface((SCREEN_RES, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        
        modal_w, modal_h = 420, 320
        modal_rect = pygame.Rect(SCREEN_RES//2 - modal_w//2, (SCREEN_RES//2 - 130) - 20, modal_w, modal_h)
        pygame.draw.rect(screen, (30, 30, 30), modal_rect)
        if game_state == "WON": border_c = (200, 180, 0)
        elif game_state == "LOST": border_c = (150, 0, 0)
        else: border_c = (100, 150, 200)
        pygame.draw.rect(screen, border_c, modal_rect, 4)
        
        if game_state == "WON":
            title_surf = title_font.render(f"LEVEL {max(1, level - 1)} COMPLETE!", True, (255, 255, 255))
            title_surf = pygame.transform.scale(title_surf, (int(title_surf.get_width()*0.7), int(title_surf.get_height()*0.7)))
            screen.blit(title_surf, (SCREEN_RES//2 - title_surf.get_width()//2, modal_rect.y + 30))
            opts = ["Continue", "Replay Level", "Main Menu", "Quit to Desktop"]
            mx, my = pygame.mouse.get_pos()
            for i, o in enumerate(opts):
                c = (255, 255, 0) if i == modal_idx or pygame.Rect(SCREEN_RES//2 - 150, modal_rect.y + 90 + i*40, 300, 30).collidepoint(mx, my) else (200, 200, 200)
                o_surf = sub_font.render(o, True, c)
                screen.blit(o_surf, (SCREEN_RES//2 - o_surf.get_width()//2, modal_rect.y + 90 + i*40))
            
        elif game_state == "LOST":
            title_surf = title_font.render("YOU DIED", True, (255, 50, 50))
            title_surf = pygame.transform.scale(title_surf, (int(title_surf.get_width()*0.7), int(title_surf.get_height()*0.7)))
            screen.blit(title_surf, (SCREEN_RES//2 - title_surf.get_width()//2, modal_rect.y + 30))
            opts = ["Restart Level", "Main Menu", "Quit to Desktop"]
            mx, my = pygame.mouse.get_pos()
            for i, o in enumerate(opts):
                c = (255, 255, 0) if i == modal_idx or pygame.Rect(SCREEN_RES//2 - 150, modal_rect.y + 110 + i*40, 300, 30).collidepoint(mx, my) else (200, 200, 200)
                o_surf = sub_font.render(o, True, c)
                screen.blit(o_surf, (SCREEN_RES//2 - o_surf.get_width()//2, modal_rect.y + 110 + i*40))
            
        elif game_state == "PAUSED":
            title_surf = title_font.render("PAUSED", True, (255, 255, 255))
            screen.blit(title_surf, (SCREEN_RES//2 - title_surf.get_width()//2, modal_rect.y + 30))
            opts = ["Resume", "Settings", "Restart Level", "Main Menu", "Quit to Desktop"]
            mx, my = pygame.mouse.get_pos()
            for i, o in enumerate(opts):
                c = (255, 255, 0) if i == modal_idx or pygame.Rect(SCREEN_RES//2 - 150, modal_rect.y + 100 + i*35, 300, 30).collidepoint(mx, my) else (200, 200, 200)
                o_surf = sub_font.render(o, True, c)
                screen.blit(o_surf, (SCREEN_RES//2 - o_surf.get_width()//2, modal_rect.y + 100 + i*35))
                
        elif game_state == "SETTINGS":
            title_surf = title_font.render("SETTINGS", True, (255, 255, 255))
            screen.blit(title_surf, (SCREEN_RES//2 - title_surf.get_width()//2, modal_rect.y + 20))
            fps_txt = f"< {GAME_FPS} FPS >"
            shd_txt = "< " + ("ON" if SHOW_SHADOWS else "OFF") + " >"
            
            c0 = (255, 255, 0) if settings_idx == 0 else (200, 200, 200)
            c1 = (255, 255, 0) if settings_idx == 1 else (200, 200, 200)
            
            s1 = sub_font.render(f"Max Framerate:", True, c0)
            v1 = sub_font.render(fps_txt, True, c0)
            s2 = sub_font.render(f"Video Shadows:", True, c1)
            v2 = sub_font.render(shd_txt, True, c1)
            
            screen.blit(s1, (modal_rect.x + 40, modal_rect.y + 100))
            screen.blit(v1, (modal_rect.x + 240, modal_rect.y + 100))
            screen.blit(s2, (modal_rect.x + 40, modal_rect.y + 150))
            screen.blit(v2, (modal_rect.x + 240, modal_rect.y + 150))
            
            esc_txt = font.render("Press ESC to return", True, (120, 120, 120))
            screen.blit(esc_txt, (SCREEN_RES//2 - esc_txt.get_width()//2, modal_rect.bottom - 40))

    pygame.display.flip()
    clock.tick(GAME_FPS)