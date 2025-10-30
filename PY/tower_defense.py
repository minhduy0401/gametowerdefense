import os, time, random, math, hashlib, secrets, json, sys
import io

# Fix UTF-8 encoding cho Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dataclasses import dataclass
from typing import List, Tuple, Optional, Set, Dict
import pygame

from config import (
    TILE, GRID_W, GRID_H, WIDTH, HEIGHT, GAME_WIDTH, GAME_HEIGHT, FPS,
    WHITE, BLACK, DARK, GREEN, RED, BLUE, YELLOW, ORANGE, SAND, GRASS, PURPLE, CYAN, PINK, BROWN, GRAY,
    ASSETS_DIR, MUSIC_MENU_DIR, MUSIC_GAME_DIR, SAVE_FILE, ACCOUNTS_FILE,
    BASE_START_MONEY, BASE_START_LIVES, SELL_REFUND_RATE, PROJECTILE_SPEED,
    RANGE_TILES, RANGE_PX, H_RANGE_TILES, H_RANGE_PX,
    TOWER_DEFS, TOWER_KEYS, TOWER_UPGRADE, ENEMY_TYPES, ALL_TOWER_KEYS, DEFAULT_LOADOUT,
    SPAWN_GAP, WAVE_COOLDOWN, TOTAL_LEVELS, MAX_LEVELS, waves_in_level, MODE_PARAMS, MODES,
    BOSS_LEVELS, BOSS_HP_MULTIPLIER, BOSS_REWARD_MULTIPLIER,
    POWERUPS,
    PERMANENT_MAP_LEVEL,
    SCENE_MENU, SCENE_GAME, SCENE_ALL_CLEAR, SCENE_LEVEL_SELECT, SCENE_SHOP, SCENE_STATS,
    SCENE_LEADER, SCENE_NAME, SCENE_AUTH, SCENE_MAP_PREVIEW, SCENE_SETTINGS,
)
pygame.init()
from utils import (
    grid_to_px, px_to_grid, clamp,
    load_img, load_sprite, try_tileset,
    load_shoot_sound, list_music, play_random_music,
    DEFAULT_SAVE, SAVE_KEYS_ORDER, load_save, save_save, load_accounts, save_accounts,
)

# Helpers (load/save, audio, music listing) are provided by utils.py

# ------------------- PARTICLES -------------------
class Particle:
    def __init__(self, x, y, vx, vy, color, life):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0
        
    def draw(self, screen):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        size = max(1, int(4 * (self.life / self.max_life)))
        if alpha > 0:
            color_with_alpha = (*self.color[:3], alpha)
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_with_alpha, (size, size), size)
            screen.blit(surf, (int(self.x-size), int(self.y-size)))

# ------------------- ANIMATED GATES -------------------
class AnimatedGate:
    def __init__(self, x, y, gate_type="entrance"):
        self.x = x
        self.y = y
        self.gate_type = gate_type  # "entrance" hoặc "exit"
        self.animation_time = 0
        self.pulse_speed = 2.0  # Tốc độ animation
        self.particles = []
        self.particle_timer = 0
        
    def update(self, dt):
        self.animation_time += dt * self.pulse_speed
        self.particle_timer += dt
        
        # Tạo particles mới
        if self.particle_timer > 0.1:  # Tạo particle mỗi 0.1 giây
            self.particle_timer = 0
            center_x = self.x * TILE + TILE // 2
            center_y = self.y * TILE + TILE // 2
            
            if self.gate_type == "entrance":
                # Particles đỏ xoáy quanh cổng vào (nguy hiểm)
                for i in range(3):
                    angle = random.uniform(0, math.pi * 2)
                    radius = random.uniform(20, 40)
                    px = center_x + math.cos(angle) * radius
                    py = center_y + math.sin(angle) * radius
                    vx = math.cos(angle + math.pi/2) * 40
                    vy = math.sin(angle + math.pi/2) * 40
                    color = (255, random.randint(80, 120), random.randint(80, 120))  # Đỏ đậm
                    self.particles.append(Particle(px, py, vx, vy, color, 2.5))
            else:
                # Particles xanh bay ra từ cổng ra (an toàn)
                for i in range(2):
                    px = center_x + random.uniform(-15, 15)
                    py = center_y + random.uniform(-10, 10)
                    vx = random.uniform(30, 50)  # Bay sang phải (hướng ra)
                    vy = random.uniform(-30, 30)
                    color = (random.randint(80, 120), 255, random.randint(120, 180))  # Xanh sáng
                    self.particles.append(Particle(px, py, vx, vy, color, 2.0))
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
    def draw(self, screen, tiles):
        # Vẽ particles trước (ở phía sau)
        for particle in self.particles:
            particle.draw(screen)
            
        # Hiệu ứng pulse và glow
        pulse = abs(math.sin(self.animation_time)) * 0.3 + 0.7  # 0.7 -> 1.0
        
        if self.gate_type == "entrance":
            # Cổng vào - màu đỏ với hiệu ứng nguy hiểm (địch xuất hiện)
            base_color = (255, 80, 80)      # Đỏ sáng
            glow_color = (255, 120, 120)    # Đỏ glow
            
            # Vẽ glow effect đỏ
            glow_radius = int(TILE * 0.8 * pulse)
            for i in range(3):
                alpha = int(80 * (1 - i/3) * pulse)  # Alpha cao hơn cho hiệu ứng mạnh
                glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*glow_color, alpha), (glow_radius, glow_radius), glow_radius - i*8)
                screen.blit(glow_surf, (self.x*TILE + TILE//2 - glow_radius, self.y*TILE + TILE//2 - glow_radius))
            
            # Vẽ cổng chính đỏ
            gate_size = int(TILE * 0.9 * pulse)
            gate_surf = pygame.Surface((gate_size, gate_size), pygame.SRCALPHA)
            pygame.draw.rect(gate_surf, (*base_color, 220), (0, 0, gate_size, gate_size), border_radius=12)
            pygame.draw.rect(gate_surf, (255, 200, 200), (0, 0, gate_size, gate_size), width=3, border_radius=12)
            
            # Vẽ ký hiệu cảnh báo thay vì portal xoay
            center_x, center_y = gate_size//2, gate_size//2
            warning_size = int(gate_size//3 * pulse)
            
            # Vẽ tam giác cảnh báo với animation nhấp nháy
            warning_alpha = int(200 + 55 * math.sin(self.animation_time * 6))  # Nhấp nháy
            triangle_points = [
                (center_x, center_y - warning_size),
                (center_x - warning_size, center_y + warning_size//2),
                (center_x + warning_size, center_y + warning_size//2)
            ]
            pygame.draw.polygon(gate_surf, (255, 255, 100, warning_alpha), triangle_points)
            pygame.draw.polygon(gate_surf, (200, 0, 0), triangle_points, 2)
            
            # Dấu chấm than trong tam giác
            pygame.draw.circle(gate_surf, (200, 0, 0), (center_x, center_y - warning_size//4), 3)
            pygame.draw.circle(gate_surf, (200, 0, 0), (center_x, center_y + warning_size//4), 2)
            
            screen.blit(gate_surf, (self.x*TILE + (TILE-gate_size)//2, self.y*TILE + (TILE-gate_size)//2))
            
        else:  # exit gate
            # Cổng ra - màu xanh với hiệu ứng an toàn (địch thoát ra)
            base_color = (80, 200, 120)     # Xanh lá sáng
            glow_color = (120, 240, 160)    # Xanh glow
            
            # Vẽ glow effect xanh
            glow_radius = int(TILE * 0.8 * pulse)
            for i in range(3):
                alpha = int(70 * (1 - i/3) * pulse)  # Alpha vừa phải cho hiệu ứng êm
                glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*glow_color, alpha), (glow_radius, glow_radius), glow_radius - i*10)
                screen.blit(glow_surf, (self.x*TILE + TILE//2 - glow_radius, self.y*TILE + TILE//2 - glow_radius))
            
            # Vẽ base chính xanh
            base_size = int(TILE * 1.0 * pulse)
            base_surf = pygame.Surface((base_size, base_size), pygame.SRCALPHA)
            pygame.draw.rect(base_surf, (*base_color, 200), (0, 0, base_size, base_size), border_radius=15)
            pygame.draw.rect(base_surf, (150, 255, 180), (0, 0, base_size, base_size), width=3, border_radius=15)
            
            # Vẽ ký hiệu mũi tên hướng ra thay vì lửa
            center_x, center_y = base_size//2, base_size//2
            arrow_size = int(base_size//3 * pulse)
            arrow_breath = math.sin(self.animation_time * 4) * 0.15 + 0.85  # Hiệu ứng thở nhẹ
            
            # Vẽ 3 mũi tên chồng lên nhau để tạo hiệu ứng chuyển động
            for i in range(3):
                offset = i * 8 - 8  # Tạo khoảng cách giữa các mũi tên
                arrow_alpha = int(255 * arrow_breath * (1 - i * 0.3))
                arrow_color = (100, 255, 150, arrow_alpha)
                
                # Mũi tên hướng phải (→)
                arrow_points = [
                    (center_x - arrow_size + offset, center_y - arrow_size//2),
                    (center_x + arrow_size//2 + offset, center_y),
                    (center_x - arrow_size + offset, center_y + arrow_size//2),
                    (center_x - arrow_size//3 + offset, center_y)
                ]
                if arrow_alpha > 50:  # Chỉ vẽ nếu đủ sáng
                    pygame.draw.polygon(base_surf, arrow_color[:3], arrow_points)
            
            # Viền mũi tên chính
            main_arrow_points = [
                (center_x - arrow_size, center_y - arrow_size//2),
                (center_x + arrow_size//2, center_y),
                (center_x - arrow_size, center_y + arrow_size//2),
                (center_x - arrow_size//3, center_y)
            ]
            pygame.draw.polygon(base_surf, (0, 150, 80), main_arrow_points, 2)
            
            screen.blit(base_surf, (self.x*TILE + (TILE-base_size)//2, self.y*TILE + (TILE-base_size)//2))

# ------------------- ACCOUNTS (đăng nhập/đăng ký) -------------------
def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def _new_account_record(username: str, password: str):
    salt = secrets.token_hex(8)
    return {
        "salt": salt,
        "pw": _hash_password(password, salt),
        "level_unlocked": 1,  # Giữ lại để tương thích
        "level_unlocked_by_mode": {"Easy": 1, "Normal": 1, "Hard": 1},  # Tiến độ riêng theo chế độ
        "unlocked_towers": DEFAULT_LOADOUT.copy(),  # Súng đã sở hữu (bắt đầu với chỉ súng máy)
        "available_for_purchase": DEFAULT_LOADOUT.copy(),  # Súng có thể mua (bắt đầu với súng máy đã có)
        "current_loadout": DEFAULT_LOADOUT.copy(),  # Loadout hiện tại (chỉ súng máy)
        "stars": 0,  # Star dựa trên performance
        "coins": 0,  # Coin để mua súng
        "achievements": {},
        "leaderboard": [],
        "player_name": username,  # Mặc định player_name = username, có thể đổi sau
    }

def load_accounts():
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}  # username -> record

def save_accounts(db: dict):
    try:
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save accounts failed:", e)






# ------------------- MAPS -------------------
def make_map(level: int):
    """
    Trả về 1 map theo LEVEL với số đường vào tăng dần.
    - Level 1-3: 2 đường vào (cải thiện từ 1)
    - Level 4-6: 3 đường vào (cải thiện từ 2)
    - Level 7-9: 4 đường vào (cải thiện từ 3)
    - Level 10+: 4+ đường vào
    
    Mỗi map là list các path; mỗi path là list node (x,y) đi ngang/dọc theo lưới.
    - Lối vào đặt ở x = -1 (bên trái), lối ra ở x = GRID_W (bên phải) để quái vào/ra mượt.
    - Các node còn lại nằm trong 0..GRID_W-1 (x) và 0..GRID_H-1 (y).
    - Địch sẽ spawn ngẫu nhiên từ các path khác nhau tạo thêm thử thách.
    """
    
    # Định nghĩa map theo số đường vào
    LEVEL_MAPS = {}
    
    # Level 1-3: Network paths - có điểm giao để địch có thể phân nhánh ra nhiều exit
    LEVEL_MAPS[1] = [
        [(-1, 2), (6, 2), (6, 5), (GRID_W, 5)],     # Path 1: vào trên, có thể ra giữa
        [(-1, 7), (6, 7), (6, 5), (GRID_W, 5)],     # Path 2: vào dưới, gặp path 1 tại (6,5)
        [(6, 5), (10, 5), (10, 2), (GRID_W, 2)],    # Path 3: từ junction ra trên
        [(6, 5), (10, 5), (10, 8), (GRID_W, 8)]     # Path 4: từ junction ra dưới
    ]
    LEVEL_MAPS[2] = [
        [(-1, 1), (5, 1), (5, 4), (GRID_W, 4)],     # Path 1: vào trên, ra giữa
        [(-1, 8), (5, 8), (5, 4), (GRID_W, 4)],     # Path 2: vào dưới, gặp tại (5,4)
        [(5, 4), (9, 4), (9, 1), (GRID_W, 1)],      # Path 3: từ junction ra trên
        [(5, 4), (9, 4), (9, 7), (GRID_W, 7)]       # Path 4: từ junction ra dưới
    ]  
    LEVEL_MAPS[3] = [
        [(-1, 3), (4, 3), (7, 3), (7, 5), (GRID_W, 5)],     # Path chính ngang
        [(-1, 6), (4, 6), (7, 6), (7, 5), (GRID_W, 5)],     # Path gặp nhau tại (7,5)
        [(7, 5), (11, 5), (11, 2), (GRID_W, 2)],            # Nhánh ra trên
        [(7, 5), (11, 5), (11, 8), (GRID_W, 8)]             # Nhánh ra dưới
    ]
    
    # Level 4-6: Network paths với nhiều junction
    LEVEL_MAPS[4] = [
        [(-1, 1), (5, 1), (8, 1), (8, 4), (GRID_W, 4)],     # Entrance path 1
        [(-1, 5), (5, 5), (8, 5), (8, 4), (GRID_W, 4)],     # Entrance path 2 - gặp nhau tại (8,4)
        [(-1, 9), (5, 9), (8, 9), (8, 4), (GRID_W, 4)],     # Entrance path 3 - gặp nhau tại (8,4)
        [(8, 4), (11, 4), (11, 1), (GRID_W, 1)],            # Junction - ra trên
        [(8, 4), (11, 4), (11, 7), (GRID_W, 7)],            # Junction - ra dưới
        [(8, 4), (13, 4), (13, 5), (GRID_W, 5)]             # Junction - ra giữa
    ]
    LEVEL_MAPS[5] = [
        [(-1, 2), (4, 2), (7, 2), (7, 5), (GRID_W, 5)],     # Entrance path 1
        [(-1, 6), (4, 6), (7, 6), (7, 5), (GRID_W, 5)],     # Entrance path 2 - gặp tại (7,5)
        [(-1, 8), (4, 8), (7, 8), (7, 5), (GRID_W, 5)],     # Entrance path 3 - gặp tại (7,5)
        [(7, 5), (10, 5), (10, 2), (GRID_W, 2)],            # Junction - ra trên
        [(7, 5), (10, 5), (10, 8), (GRID_W, 8)],            # Junction - ra dưới
        [(7, 5), (12, 5), (12, 6), (GRID_W, 6)]             # Junction - ra giữa
    ]
    LEVEL_MAPS[6] = [
        [(-1, 1), (3, 1), (6, 1), (6, 4), (9, 4), (GRID_W, 4)],    # Main path ngang
        [(-1, 7), (3, 7), (6, 7), (6, 4), (9, 4), (GRID_W, 4)],    # Path gặp tại (6,4) và (9,4)
        [(6, 4), (6, 8), (10, 8), (GRID_W, 8)],                    # Junction từ (6,4) ra dưới
        [(9, 4), (12, 4), (12, 1), (GRID_W, 1)],                   # Junction từ (9,4) ra trên
        [(9, 4), (12, 4), (12, 7), (GRID_W, 7)]                    # Junction từ (9,4) ra dưới
    ]
    
    # Level 7-9: 4 đường vào (tăng từ 3 lên 4)
    LEVEL_MAPS[7] = [
        [(-1, 1), (4, 1), (4, 5), (8, 5), (8, 8), (GRID_W, 8)],
        [(-1, 3), (6, 3), (6, 7), (11, 7), (11, 2), (GRID_W, 2)],
        [(-1, 6), (3, 6), (3, 9), (12, 9), (12, 4), (GRID_W, 4)],
        [(-1, 9), (9, 9), (9, 6), (GRID_W, 6)]
    ]
    LEVEL_MAPS[8] = [
        [(-1, 1), (5, 1), (5, 6), (9, 6), (9, 3), (GRID_W, 3)],
        [(-1, 4), (7, 4), (7, 8), (12, 8), (12, 1), (GRID_W, 1)],
        [(-1, 7), (2, 7), (2, 2), (14, 2), (14, 9), (GRID_W, 9)],
        [(-1, 9), (10, 9), (10, 5), (GRID_W, 5)]
    ]
    LEVEL_MAPS[9] = [
        [(-1, 1), (3, 1), (3, 4), (8, 4), (8, 8), (GRID_W, 8)],
        [(-1, 3), (6, 3), (6, 7), (11, 7), (11, 2), (GRID_W, 2)],
        [(-1, 6), (4, 6), (4, 9), (13, 9), (13, 5), (GRID_W, 5)],
        [(-1, 8), (9, 8), (9, 1), (GRID_W, 1)]
    ]
    
    # Level 10+: 4 đường vào
    LEVEL_MAPS[10] = [
        [(-1, 1), (4, 1), (4, 4), (8, 4), (8, 7), (GRID_W, 7)],
        [(-1, 3), (6, 3), (6, 8), (11, 8), (11, 2), (GRID_W, 2)],
        [(-1, 6), (2, 6), (2, 9), (9, 9), (9, 5), (GRID_W, 5)],
        [(-1, 9), (13, 9), (13, 6), (GRID_W, 6)]
    ]
    LEVEL_MAPS[11] = [
        [(-1, 2), (3, 2), (3, 7), (7, 7), (7, 1), (11, 1), (11, 8), (GRID_W, 8)],
        [(-1, 5), (5, 5), (5, 3), (9, 3), (9, 6), (13, 6), (13, 4), (GRID_W, 4)],
        [(-1, 8), (8, 8), (8, 5), (12, 5), (12, 9), (GRID_W, 9)],
        [(-1, 1), (6, 1), (6, 4), (10, 4), (10, 2), (GRID_W, 2)]
    ]
    LEVEL_MAPS[12] = [
        [(-1, 3), (4, 3), (4, 6), (8, 6), (8, 2), (GRID_W, 2)],
        [(-1, 1), (7, 1), (7, 8), (12, 8), (12, 5), (GRID_W, 5)],
        [(-1, 7), (2, 7), (2, 4), (10, 4), (10, 9), (GRID_W, 9)],
        [(-1, 9), (5, 9), (5, 1), (GRID_W, 1)]
    ]
    LEVEL_MAPS[13] = [
        [(-1, 2), (6, 2), (6, 5), (9, 5), (9, 8), (GRID_W, 8)],
        [(-1, 4), (3, 4), (3, 1), (11, 1), (11, 7), (GRID_W, 7)],
        [(-1, 6), (8, 6), (8, 3), (13, 3), (13, 9), (GRID_W, 9)],
        [(-1, 8), (4, 8), (4, 6), (GRID_W, 6)]
    ]
    LEVEL_MAPS[14] = [
        [(-1, 1), (5, 1), (5, 7), (9, 7), (9, 3), (GRID_W, 3)],
        [(-1, 4), (7, 4), (7, 9), (12, 9), (12, 2), (GRID_W, 2)],
        [(-1, 6), (2, 6), (2, 2), (10, 2), (10, 8), (GRID_W, 8)],
        [(-1, 9), (6, 9), (6, 5), (14, 5), (14, 4), (GRID_W, 4)]
    ]
    LEVEL_MAPS[15] = [
        [(-1, 2), (4, 2), (4, 8), (8, 8), (8, 1), (12, 1), (12, 6), (GRID_W, 6)],
        [(-1, 5), (6, 5), (6, 3), (10, 3), (10, 9), (14, 9), (14, 7), (GRID_W, 7)],
        [(-1, 7), (3, 7), (3, 4), (11, 4), (11, 2), (GRID_W, 2)],
        [(-1, 9), (7, 9), (7, 6), (13, 6), (13, 8), (GRID_W, 8)]
    ]
    
    # Cho level > 15: Tạo map tự động với 4 đường vào
    if level > 15:
        return generate_procedural_map(level)
    
    # Trả về map cho level, nếu không có thì dùng map level 1
    return LEVEL_MAPS.get(level, LEVEL_MAPS[1])


def generate_procedural_map(level: int):
    """
    Tạo map tự động cho level > 15 với 4 đường vào.
    Độ khó tăng dần theo level.
    """
    import random
    
    # Sử dụng level làm seed để tạo map nhất quán
    random.seed(level * 42)
    
    # Level > 15 luôn có 4 đường vào để duy trì độ khó cao
    num_paths = 4
    
    paths = []
    
    # Định nghĩa các vị trí y cố định cho 4 đường để tránh trùng lặp
    y_positions = [1, 3, 6, 8]  # Phân bố đều trên map
    
    for i in range(num_paths):
        start_y = y_positions[i]
        
        # Tạo path với độ phức tạp tăng theo level
        complexity = min((level - 15) // 3 + 2, 6)  # 2-6 turns, tăng dần
        path = generate_single_path(start_y, complexity, random)
        paths.append(path)
    
    return paths


def generate_single_path(start_y: int, complexity: int, rng):
    """
    Tạo một đường đi với số lượng rẽ được chỉ định.
    """
    path = [(-1, start_y)]  # Điểm bắt đầu
    
    current_x = 0
    current_y = start_y
    
    for turn in range(complexity):
        # Di chuyển một đoạn theo x
        next_x = current_x + rng.randint(2, 5)
        next_x = min(next_x, GRID_W - 2)
        path.append((next_x, current_y))
        
        # Rẽ theo y
        direction = rng.choice([-1, 1])
        next_y = current_y + direction * rng.randint(2, 4)
        next_y = max(1, min(next_y, GRID_H - 2))
        path.append((next_x, next_y))
        
        current_x = next_x
        current_y = next_y
    
    # Đến cuối màn hình
    if current_x < GRID_W - 1:
        path.append((GRID_W - 1, current_y))
    
    # Điểm kết thúc
    path.append((GRID_W, current_y))
    
    return path


def make_maps():
    """Trả về list map cho tất cả level (không còn giới hạn 15 map)."""
    # Không cần tạo list cố định nữa vì mỗi level có map riêng
    # Hàm này giữ lại để tương thích nhưng không dùng nhiều
    return [make_map(i) for i in range(1, 16)]


# Dữ liệu map dùng cho game - giờ sẽ load động theo level
MAPS = make_maps()  # Giữ lại để tương thích với code cũ


def make_permanent_map() -> List[List[Tuple[int,int]]]:
    """Tạo 1 map chơi vĩnh viễn (special) với theme snow và nhiều ô đặt trụ.
    Map này có ít đường đi để tối đa hóa không gian cho tower.
    Trả về list các path (mỗi path là list of nodes).
    """
    # Thiết kế map Snow: 3 đường chính đơn giản để tối đa hóa tower slots
    paths = []

    # Đường 1: Trên cùng - đường thẳng đơn giản
    paths.append([(-1, 2), (2, 2), (6, 2), (10, 2), (14, 2), (GRID_W, 2)])
    
    # Đường 2: Giữa - có một curve nhẹ
    paths.append([(-1, 5), (3, 5), (6, 5), (6, 7), (9, 7), (12, 7), (GRID_W, 7)])
    
    # Đường 3: Dưới cùng - đường zigzag nhẹ  
    paths.append([(-1, 9), (4, 9), (7, 9), (7, 6), (10, 6), (13, 6), (GRID_W, 6)])

    return paths

def grid_nodes_to_px(nodes: List[Tuple[int, int]]) -> List[Tuple[float, float]]:
    return [grid_to_px(x, y) for x, y in nodes]

def expand_path_cells(multipath_nodes: List[List[Tuple[int,int]]]) -> Set[Tuple[int,int]]:
    cells: Set[Tuple[int, int]] = set()
    for nodes in multipath_nodes:
        for (x1, y1), (x2, y2) in zip(nodes[:-1], nodes[1:]):
            if x1 == x2:
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    if 0 <= x1 < GRID_W and 0 <= y < GRID_H:
                        cells.add((x1, y))
            elif y1 == y2:
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if 0 <= x < GRID_W and 0 <= y1 < GRID_H:
                        cells.add((x, y1))
    return cells

# Core entity classes and UI moved to modules for clarity
from entities import Enemy, Projectile, Tower, DeathEffect, DamageText
from wave_manager import WaveManager
from ui import Button, draw_level_badge


class Game:

    def _init_runtime(self, mode_name: str, level: int, new_game=False):
        """Thiết lập lại trạng thái 1 ván chơi (tiền, mạng, map, wave...)."""
        # 1) Mode & tham số
        self.mode_name = mode_name
        mp = MODE_PARAMS[self.mode_name]
        self.level = level
        # Default waves per level
        self.max_waves = waves_in_level(self.level)
        # Special permanent map handling
        try:
            from config import PERMANENT_MAP_LEVEL
        except Exception:
            PERMANENT_MAP_LEVEL = None
        self.is_permanent_map = (PERMANENT_MAP_LEVEL is not None and self.level == PERMANENT_MAP_LEVEL)
        if self.is_permanent_map:
            # Permanent map: fixed 5 waves as requested
            self.max_waves = 5

        # 2) Trạng thái người chơi / trận
        self.money = mp["money"]
        self.lives = mp["lives"]
        self.paused = False
        self.speed_scale = 1.0
        self.win_level = False
        self.game_over_reason = None  # Lý do thua game ("boss_escaped" hoặc "no_lives")
        self.show_placement_grid = False  # Tắt grid placement để tránh nhầm lẫn

        # 3) World rỗng
        self.towers = []
        self.projectiles = []
        self.enemies = []
        self.death_effects = []  # Hiệu ứng khi địch chết
        self.damage_texts = []   # Text sát thương bay lên
        self.occupied = set()

        # 4) Đường đi theo level hiện tại (thay vì dùng index cố định)
        if getattr(self, 'is_permanent_map', False):
            multipath_grid = make_permanent_map()
        else:
            multipath_grid = make_map(self.level)  # Load map theo level, không phải index
        self.paths_grid = multipath_grid
        self.paths_px = [ [grid_to_px(x,y) for (x,y) in path] for path in multipath_grid ]

        # Tập ô thuộc đường đi (để chặn đặt trụ)
        self.path_cells = expand_path_cells(multipath_grid)
        self.exit_cells = [p[-1] for p in multipath_grid]

        # Tạo grid placement system với khoảng cách bắt buộc
        self.tower_slots = self._generate_tower_slots()
        self.decorative_objects = self._generate_decorative_objects()
        
        # Tạo animated gates chỉ cho entrance và exit thật (không phải junction)
        self.animated_gates = []
        
        # Tạo entrance gates - chỉ cho paths bắt đầu từ ngoài map (-1)
        for path in self.paths_grid:
            start_x, start_y = path[0]
            if start_x == -1:  # Chỉ tạo gate cho paths từ bên trái thật
                gate_x = 0
                gate_y = max(0, min(GRID_H-1, start_y))
                self.animated_gates.append(AnimatedGate(gate_x, gate_y, "entrance"))
        
        # Tạo exit gates - chỉ cho paths kết thúc ở ngoài map (GRID_W)
        exit_positions = set()  # Tránh tạo gate trùng lặp
        for path in self.paths_grid:
            end_x, end_y = path[-1]
            if end_x == GRID_W:  # Chỉ tạo gate cho paths ra bên phải thật
                gate_x = GRID_W - 1
                gate_y = max(0, min(GRID_H-1, end_y))
                gate_pos = (gate_x, gate_y)
                if gate_pos not in exit_positions:  # Tránh trùng lặp
                    exit_positions.add(gate_pos)
                    self.animated_gates.append(AnimatedGate(gate_x, gate_y, "exit"))

        # 5) Âm thanh, thông số thống kê
        self.snd_shoot = load_shoot_sound()
        self._shoot_snd_cooldown = 0.0
        self.kills = 0
        self.towers_built = 0
        self.money_spent = 0
        self.powerups_used = 0
        self.start_time = time.time()
        self.notice_msg = ""
        self.notice_timer = 0.0
        # Mouse hover state cho powerup buttons
        self.hovered_powerup = None
        
        # Thời gian setup đầu game
        self.setup_time = 15.0  # 15 giây để setup
        self.in_setup_phase = True
        
        # Thông báo bắt đầu setup phase (chỉ khi new_game)
        if new_game:
            self.notice("[TOOL] SETUP PHASE STARTED! Place your defenses! [TOOL]", 4.0)
        
        # Hiển thị tầm bắn
        self.selected_tower_for_range = None  # Tower được chọn để hiện tầm bắn
        self.show_all_ranges = False          # Hiển thị tất cả tầm bắn

        # 6) Tower sprites (nếu có asset) - Load tất cả 12 tháp
        self.tower_sprites = {}
        for tower_key in ALL_TOWER_KEYS:
            sprite_file = TOWER_DEFS[tower_key]["sprite"]
            # Kích thước khác nhau theo loại tháp
            if tower_key == "sniper":
                size = 52
            elif tower_key in ["splash", "mortar", "rocket"]:
                size = 56
            elif tower_key == "slow":
                size = 50
            else:
                size = 48
            self.tower_sprites[tower_key] = load_sprite(sprite_file, size)
            
        # Enemy sprites - Load tất cả 4 loại địch  
        self.enemy_sprites = {}
        base_size = 36
        for enemy_key in ["normal", "fast", "tank", "boss"]:
            sprite_file = f"enemy_{enemy_key}.png"
            # Kích thước theo size_mul từ config
            size_mul = ENEMY_TYPES[enemy_key].get("size_mul", 1.0)
            actual_size = int(base_size * size_mul)
            self.enemy_sprites[enemy_key] = load_sprite(sprite_file, actual_size)
            
        # Fallback enemy sprite
        self.enemy_sprite = load_sprite("enemy.png", base_size)

        # 7) Tạo wave manager (không tự động start, chờ setup phase)
        paths_for_wave_mgr = [ [grid_to_px(x,y) for (x,y) in path] for path in multipath_grid ]
        print(f"[LEVEL] {self.level}: Tạo {len(paths_for_wave_mgr)} paths cho WaveManager")
        self.wave_mgr = WaveManager(
            paths_for_wave_mgr,
            MODE_PARAMS[self.mode_name]["hp_mul"],
            MODE_PARAMS[self.mode_name]["spd_mul"],
            level=self.level,
            special_mode=('permanent' if getattr(self, 'is_permanent_map', False) else None)
        )
        # Không start wave ngay, chờ setup phase kết thúc

        # 8) Mặc định trụ đã mở & lựa chọn từ loadout
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            self.unlocked_towers = list(account.get("current_loadout", DEFAULT_LOADOUT.copy()))
        else:
            self.unlocked_towers = list(DEFAULT_LOADOUT)
        self.selected_tower = self.unlocked_towers[0] if self.unlocked_towers else None

        # Load decoration sprites
        self.decoration_sprites = self._load_decoration_sprites()

        self._ensure_tiles_loaded()
        self._load_map_background(self.level)  # Load background theo level hiện tại
        self._compute_decor_once()
        
    def _generate_tower_slots(self):
        """
        Tạo các ô có thể đặt tower với khoảng cách bắt buộc 2-4 ô.
        Đảm bảo vẫn có đủ slot để thắng game.
        """
        import random
        random.seed(self.level * 567)  # Seed cố định cho level
        
        available_cells = []
        # Tìm tất cả ô không phải đường đi
        for x in range(GRID_W):
            for y in range(GRID_H):
                if (x, y) not in self.path_cells:
                    available_cells.append((x, y))
        
        tower_slots = set()
        min_distance = random.choice([2, 3, 4])  # Khoảng cách ngẫu nhiên cho level này
        
        # Thuật toán Poisson disk sampling để đặt tower slots
        attempts = 0
        while len(tower_slots) < min(20, len(available_cells) // 3) and attempts < 1000:
            attempts += 1
            
            # Chọn ô ngẫu nhiên
            candidate = random.choice(available_cells)
            
            # Kiểm tra khoảng cách với các tower slot đã có
            valid = True
            for existing in tower_slots:
                distance = abs(candidate[0] - existing[0]) + abs(candidate[1] - existing[1])  # Manhattan distance
                if distance < min_distance:
                    valid = False
                    break
            
            if valid:
                tower_slots.add(candidate)
        
        # Đảm bảo có ít nhất 8 slot để game có thể thắng được
        if len(tower_slots) < 8:
            # Thêm một số slot gần đường đi để đảm bảo chiến thuật
            for path in self.paths_grid:
                for i in range(1, len(path)-1):
                    px, py = path[i]
                    # Tìm ô gần đường đi
                    for dx in [-2, -1, 1, 2]:
                        for dy in [-2, -1, 1, 2]:
                            nx, ny = px + dx, py + dy
                            if (0 <= nx < GRID_W and 0 <= ny < GRID_H and 
                                (nx, ny) not in self.path_cells and
                                (nx, ny) not in tower_slots):
                                tower_slots.add((nx, ny))
                                if len(tower_slots) >= 12:
                                    break
                        if len(tower_slots) >= 12:
                            break
                    if len(tower_slots) >= 12:
                        break
        
        return tower_slots
    
    def _load_decoration_sprites(self):
        """Load tất cả decoration sprites từ thư mục chính và custom."""
        decoration_sprites = {}
        decoration_files = {
            "broken_tower": "broken_tower.png",
            "dead_tree": "dead_tree.png", 
            "rocks": "rocks.png",
            "thorns": "thorns.png",
            "ruins": "ruins.png",
            "crystal": "crystal.png",
            "bones": "bones.png"
        }
        
        # Thử load từ thư mục custom trước, sau đó mới đến thư mục chính
        for dec_type, filename in decoration_files.items():
            # Thử custom folder trước
            custom_path = os.path.join(ASSETS_DIR, "decor", "custom", filename)
            main_path = os.path.join(ASSETS_DIR, "decorations", filename)  # Sửa lại đúng thư mục
            
            loaded = False
            for path_to_try in [custom_path, main_path]:
                try:
                    if os.path.exists(path_to_try):
                        img = pygame.image.load(path_to_try).convert_alpha()
                        # Scale thông minh dựa trên kích thước gốc
                        original_size = max(img.get_width(), img.get_height())
                        if original_size <= 24:
                            target_size = 32  
                        elif original_size <= 48:
                            target_size = 42  
                        else:
                            target_size = 56  
                        
                        scaled_img = pygame.transform.smoothscale(img, (target_size, target_size))
                        decoration_sprites[dec_type] = scaled_img
                        folder_name = "custom" if "custom" in path_to_try else "main"
                        print(f"[OK] Loaded decoration: {filename} ({folder_name})")
                        loaded = True
                        break
                except Exception as e:
                    continue
            
            if not loaded:
                print(f"[FAIL] Could not load decoration {filename}")
                decoration_sprites[dec_type] = None
                
        return decoration_sprites
    
    def _generate_decorative_objects(self):
        """
        Tạo các vật trang trí cho những ô không thể đặt tower.
        Bao gồm: cành khô, tháp vỡ, đá, cây nhỏ...
        """
        import random
        random.seed(self.level * 789)  # Seed khác để độc lập
        
        decorations = []
        decoration_types = [
            {"name": "broken_tower", "weight": 15, "color": (100, 80, 70), "size": "large"},
            {"name": "dead_tree", "weight": 20, "color": (80, 60, 40), "size": "medium"},
            {"name": "rocks", "weight": 25, "color": (120, 110, 100), "size": "small"},
            {"name": "thorns", "weight": 20, "color": (60, 80, 40), "size": "small"},
            {"name": "ruins", "weight": 10, "color": (90, 85, 75), "size": "large"},
            {"name": "crystal", "weight": 5, "color": (150, 100, 200), "size": "medium"},
            {"name": "bones", "weight": 5, "color": (200, 190, 180), "size": "small"},
        ]
        
        # Tạo trọng số dựa trên theme level
        if self.level <= 3:  # Cỏ xanh - ít decoration đáng sợ
            for dec in decoration_types:
                if dec["name"] in ["bones", "ruins"]:
                    dec["weight"] = 2
        elif self.level >= 10:  # Lava - nhiều decoration đáng sợ
            for dec in decoration_types:
                if dec["name"] in ["bones", "ruins", "thorns"]:
                    dec["weight"] *= 2
        
        # Đặt decoration vào các ô trống (không phải đường đi, không phải tower slot)
        for x in range(GRID_W):
            for y in range(GRID_H):
                cell = (x, y)
                if (cell not in self.path_cells and 
                    cell not in self.tower_slots and
                    random.random() < 0.4):  # 40% chance có decoration
                    
                    # Chọn loại decoration theo trọng số
                    total_weight = sum(d["weight"] for d in decoration_types)
                    rand_val = random.randint(1, total_weight)
                    current_weight = 0
                    
                    for dec_type in decoration_types:
                        current_weight += dec_type["weight"]
                        if rand_val <= current_weight:
                            decorations.append({
                                "pos": cell,
                                "type": dec_type["name"], 
                                "color": dec_type["color"],
                                "size": dec_type["size"],
                                "offset": (random.randint(-8, 8), random.randint(-8, 8))
                            })
                            break
        
        print(f"Tao {len(decorations)} decorations cho level {self.level}")
        return decorations
        
    def _generate_decorative_objects_preview(self, temp_game):
        """Tạo decorations cho preview map (tương tự như game thật)."""
        import random
        random.seed(temp_game.level * 789)
        
        available_cells = []
        for x in range(GRID_W):
            for y in range(GRID_H):
                if (x, y) not in temp_game.path_cells:
                    available_cells.append((x, y))
        
        decorations = []
        placed_positions = set()
        min_distance = random.choice([2, 3])
        target_count = min(15, len(available_cells) // 4)
        
        attempts = 0
        while len(decorations) < target_count and attempts < 1000:
            attempts += 1
            
            if not available_cells:
                break
            candidate = random.choice(available_cells)
            
            valid = True
            for existing_pos in placed_positions:
                distance = abs(candidate[0] - existing_pos[0]) + abs(candidate[1] - existing_pos[1])
                if distance < min_distance:
                    valid = False
                    break
            
            if valid:
                decorations.append(candidate)
                placed_positions.add(candidate)
        
        # Đảm bảo có ít nhất 8 decoration
        if len(decorations) < 8:
            for path in temp_game.paths_grid:
                for i in range(1, len(path)-1):
                    px, py = path[i]
                    for dx in [-2, -1, 1, 2]:
                        for dy in [-2, -1, 1, 2]:
                            nx, ny = px + dx, py + dy
                            if (0 <= nx < GRID_W and 0 <= ny < GRID_H and 
                                (nx, ny) not in temp_game.path_cells and
                                (nx, ny) not in placed_positions):
                                decorations.append((nx, ny))
                                placed_positions.add((nx, ny))
                                if len(decorations) >= 12:
                                    break
                        if len(decorations) >= 12:
                            break
                    if len(decorations) >= 12:
                        break
        
        return decorations
        
    def _generate_tower_slots_preview(self, temp_game):
        """Tạo tower slots cho preview map."""
        import random
        random.seed(temp_game.level * 567)
        
        available_cells = []
        for x in range(GRID_W):
            for y in range(GRID_H):
                if (x, y) not in temp_game.path_cells:
                    available_cells.append((x, y))
        
        tower_slots = set()
        min_distance = random.choice([2, 3, 4])
        
        attempts = 0
        while len(tower_slots) < min(20, len(available_cells) // 3) and attempts < 1000:
            attempts += 1
            candidate = random.choice(available_cells)
            
            valid = True
            for existing in tower_slots:
                distance = abs(candidate[0] - existing[0]) + abs(candidate[1] - existing[1])
                if distance < min_distance:
                    valid = False
                    break
            
            if valid:
                tower_slots.add(candidate)
        
        # Đảm bảo có ít nhất 8 slot
        if len(tower_slots) < 8:
            for path in temp_game.paths_grid:
                for i in range(1, len(path)-1):
                    px, py = path[i]
                    for dx in [-2, -1, 1, 2]:
                        for dy in [-2, -1, 1, 2]:
                            nx, ny = px + dx, py + dy
                            if (0 <= nx < GRID_W and 0 <= ny < GRID_H and 
                                (nx, ny) not in temp_game.path_cells and
                                (nx, ny) not in tower_slots):
                                tower_slots.add((nx, ny))
                                if len(tower_slots) >= 12:
                                    break
                        if len(tower_slots) >= 12:
                            break
                    if len(tower_slots) >= 12:
                        break
        
        return tower_slots
        

    def back_to_menu(self):
        # Cập nhật thống kê tích lũy nếu đang trong game và có tài khoản
        if self.scene == SCENE_GAME and self.current_user and self.current_user in self.accounts:
            acc = self.accounts[self.current_user]
            # Cập nhật thống kê tích lũy cho tài khoản
            acc["total_kills"] = acc.get("total_kills", 0) + self.kills
            acc["total_towers_built"] = acc.get("total_towers_built", 0) + self.towers_built
            acc["total_money_spent"] = acc.get("total_money_spent", 0) + self.money_spent  
            acc["total_powerups_used"] = acc.get("total_powerups_used", 0) + self.powerups_used
            
            # Lưu leaderboard nếu game đã chơi đủ lâu (tránh spam)
            if hasattr(self, 'start_time') and time.time() - self.start_time > 30:
                duration = max(1, int(time.time() - self.start_time))
                # Công thức tính điểm Permanent Map: chỉ kills và wave
                if getattr(self, 'is_permanent_map', False):
                    wave_no = getattr(self, 'wave_mgr', None).wave_no if hasattr(self, 'wave_mgr') else 0
                    score = self.kills * 10 + wave_no * 500
                else:
                    # Công thức cũ cho level thường (không lưu leaderboard)
                    score = self.kills*10 + self.lives*100 + self.money + self.level*500 - duration//2
                
                # Chỉ lưu điểm từ Permanent Map vào leaderboard
                if getattr(self, 'is_permanent_map', False):
                    acc["leaderboard"] = acc.get("leaderboard", [])
                    acc["leaderboard"].append({
                        "name": self.current_user, 
                        "level": self.level, 
                        "wave": getattr(self, 'wave_mgr', None).wave_no if hasattr(self, 'wave_mgr') else 0,
                        "score": int(score), 
                        "ts": int(time.time()),
                        "is_permanent": True
                    })
                    acc["leaderboard"] = sorted(acc["leaderboard"], key=lambda x: -x["score"])[:20]
            
            save_accounts(self.accounts)
            
        self.scene = SCENE_MENU
        self._build_menu_buttons()
        # nhạc: chuyển về nhạc menu (nếu bật)
        if self.save["settings"]["music"]:
            play_random_music(self.menu_tracks, self.save["settings"]["volume"])

    def menu_shop(self):
        """Mở cửa hàng mở khoá trụ."""
        self.scene = SCENE_SHOP
        self._shop_rects = {}  # sẽ được điền khi draw_shop

    def menu_stats(self):
        """Mở thống kê / thành tựu."""
        self.scene = SCENE_STATS

    def menu_name(self):
        """Đổi tên người chơi."""
        self.scene = SCENE_NAME
        # ô nhập tên - logic thông minh
        if self.current_user and self.current_user in self.accounts:
            # Lấy player_name hiện tại từ account
            current_player_name = self.accounts[self.current_user].get("player_name", self.current_user)
            
            # Nếu player_name khác username (đã đổi tên) → hiển thị tên đã đổi
            # Nếu player_name = username (chưa đổi) → hiển thị username
            self.name_input = current_player_name
        else:
            current_player_name = self.save.get("player_name", "Player")
            self.name_input = current_player_name

    def menu_map_preview(self):
        """Xem trước map của level hiện tại."""
        self.scene = SCENE_MAP_PREVIEW

    def menu_settings(self):
        """Mở cài đặt âm thanh."""
        self.scene = SCENE_SETTINGS
        # Khởi tạo buttons cho settings screen
        self._build_settings_buttons()

    def _build_settings_buttons(self):
        """Tạo các nút cho màn hình cài đặt."""
        self.settings_buttons = []
        
        x = WIDTH // 2 - 150
        w, h = 300, 45
        gap = 60
        y_start = 200
        
        # Nút bật/tắt nhạc
        music_text = "Nhạc nền: BẬT" if self.save["settings"]["music"] else "Nhạc nền: TẮT"
        self.settings_buttons.append(Button((x, y_start, w, h), music_text, self.toggle_music))
        
        # Nút bật/tắt âm thanh hiệu ứng
        sfx_text = "Âm thanh súng: BẬT" if self.save["settings"]["sfx"] else "Âm thanh súng: TẮT"
        self.settings_buttons.append(Button((x, y_start + gap, w, h), sfx_text, self.toggle_sfx))
        
        # Nút trở về menu
        self.settings_buttons.append(Button((x, y_start + gap * 3, w, h), "Trở về Menu", self.back_to_menu))

    def toggle_music(self):
        """Bật/tắt nhạc nền."""
        self.save["settings"]["music"] = not self.save["settings"]["music"]
        
        if self.save["settings"]["music"]:
            # Bật nhạc
            if self.scene == SCENE_GAME:
                play_random_music(self.game_tracks, self.save["settings"]["volume"])
            else:
                play_random_music(self.menu_tracks, self.save["settings"]["volume"])
        else:
            # Tắt nhạc
            import pygame
            pygame.mixer.music.stop()
        
        # Cập nhật buttons và lưu settings
        if self.scene == SCENE_SETTINGS:
            self._build_settings_buttons()
        elif self.scene == SCENE_MENU:
            self._build_menu_buttons()
        save_save(self.save)

    def toggle_sfx(self):
        """Bật/tắt âm thanh hiệu ứng."""
        self.save["settings"]["sfx"] = not self.save["settings"]["sfx"]
        
        # Cập nhật buttons và lưu settings
        if self.scene == SCENE_SETTINGS:
            self._build_settings_buttons()
        elif self.scene == SCENE_MENU:
            self._build_menu_buttons()
        save_save(self.save)
    
    def _migrate_old_save_data(self):
        """Chuyển đổi dữ liệu save cũ sang cấu trúc mới với tiến độ theo chế độ."""
        if "level_unlocked_by_mode" not in self.save:
            # Chuyển đổi: tiến độ cũ chỉ áp dụng cho Easy, Normal/Hard reset về 1
            old_level = self.save.get("level_unlocked", 1)
            self.save["level_unlocked_by_mode"] = {
                "Easy": old_level,    # Giữ tiến độ cũ cho Easy
                "Normal": 1,          # Reset Normal về 1
                "Hard": 1             # Reset Hard về 1
            }
            
        # Migration cho progression system
        if "available_for_purchase" not in self.save:
            # Cho người chơi cũ, làm cho tất cả súng đã có thể mua
            unlocked = self.save.get("unlocked_towers", DEFAULT_LOADOUT.copy())
            self.save["available_for_purchase"] = unlocked.copy()
            print(f"[MIGRATE] Added available_for_purchase: {len(unlocked)} towers")
            
        if "coins" not in self.save:
            # Cho người chơi cũ coin để mua súng
            self.save["coins"] = 5  # Cho 5 coin để bắt đầu
            print("[MIGRATE] Added coins: 5")
            
        if "level_unlocked_by_mode" in self.save:
            old_level = self.save.get("level_unlocked", 1)
            print(f"[MIGRATE] Converted save data: Easy={old_level}, Normal=1, Hard=1")
            # Sanitize/clamp progression values to avoid corrupted large numbers
            try:
                from config import TOTAL_LEVELS
            except Exception:
                TOTAL_LEVELS = 15

            for mode_k, v in list(self.save.get("level_unlocked_by_mode", {}).items()):
                try:
                    clamped = max(1, min(int(v), TOTAL_LEVELS))
                except Exception:
                    clamped = 1
                if self.save["level_unlocked_by_mode"].get(mode_k) != clamped:
                    print(f"[MIGRATE] Clamping save.level_unlocked_by_mode[{mode_k}] from {v} to {clamped}")
                    self.save["level_unlocked_by_mode"][mode_k] = clamped

            # Also clamp legacy single value
            if "level_unlocked" in self.save:
                try:
                    self.save["level_unlocked"] = max(1, min(int(self.save["level_unlocked"]), TOTAL_LEVELS))
                except Exception:
                    self.save["level_unlocked"] = 1

        save_save(self.save)
        
    def _migrate_old_accounts_data(self):
        """Chuyển đổi dữ liệu accounts cũ sang cấu trúc mới với tiến độ theo chế độ."""
        changed = False
        for username, account_data in self.accounts.items():
            if "level_unlocked_by_mode" not in account_data:
                # Chuyển đổi: tiến độ cũ chỉ áp dụng cho Easy, Normal/Hard reset về 1  
                old_level = account_data.get("level_unlocked", 1)
                account_data["level_unlocked_by_mode"] = {
                    "Easy": old_level,    # Giữ tiến độ cũ cho Easy
                    "Normal": 1,          # Reset Normal về 1
                    "Hard": 1             # Reset Hard về 1
                }
                changed = True
                print(f"[MIGRATE] Converted account {username}: Easy={old_level}, Normal=1, Hard=1")
            
            # Migration cho progression system
            if "available_for_purchase" not in account_data:
                # Cho tài khoản cũ, làm cho tất cả súng đã có thể mua
                unlocked = account_data.get("unlocked_towers", DEFAULT_LOADOUT.copy())
                account_data["available_for_purchase"] = unlocked.copy()
                changed = True
                print(f"[MIGRATE] Added available_for_purchase for {username}: {len(unlocked)} towers")
                
            if "coins" not in account_data:
                # Cho tài khoản cũ coin để mua súng
                account_data["coins"] = 5  # Cho 5 coin để bắt đầu
                changed = True
                print(f"[MIGRATE] Added coins for {username}: 5")
            # Sanitize/clamp progression values to avoid corrupted large numbers
            try:
                from config import TOTAL_LEVELS
            except Exception:
                TOTAL_LEVELS = 15

            if "level_unlocked_by_mode" in account_data:
                for mode_k, v in list(account_data.get("level_unlocked_by_mode", {}).items()):
                    try:
                        clamped = max(1, min(int(v), TOTAL_LEVELS))
                    except Exception:
                        clamped = 1
                    if account_data["level_unlocked_by_mode"].get(mode_k) != clamped:
                        print(f"[MIGRATE] Clamping account {username}.level_unlocked_by_mode[{mode_k}] from {v} to {clamped}")
                        account_data["level_unlocked_by_mode"][mode_k] = clamped

            if "level_unlocked" in account_data:
                try:
                    account_data["level_unlocked"] = max(1, min(int(account_data["level_unlocked"]), TOTAL_LEVELS))
                except Exception:
                    account_data["level_unlocked"] = 1
        
        if changed:
            save_accounts(self.accounts)

    def menu_level_select(self):
        """Mở màn hình chọn level."""
        if not self.current_user:
            self.menu_auth()
            return
        self.scene = SCENE_LEVEL_SELECT

    def menu_logout(self):
        """Đăng xuất và chuyển về màn hình đăng nhập."""
        self.current_user = None
        self.scene = SCENE_AUTH
        self.auth_msg = "Đã đăng xuất thành công!"

    def draw_map_preview(self):
        """Vẽ preview map cho level hiện tại."""
        self.screen.fill((30, 40, 50))
        
        # Lấy level tiếp theo theo chế độ hiện tại
        current_mode = MODES[self.menu_mode_idx]
        
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            level_by_mode = account.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            level_unlocked = level_by_mode.get(current_mode, 1)
        else:
            level_by_mode = self.save.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            level_unlocked = level_by_mode.get(current_mode, 1)
        
        # Level tiếp theo = level_unlocked (vì level_unlocked là level cao nhất có thể chơi)
        next_level = level_unlocked
        
        # Tiêu đề với chế độ
        title = f"Preview Map Level {next_level} - Mode: {current_mode}"
        self.screen.blit(self.bigfont.render(title, True, ORANGE), (40, 40))
        
        # Vẽ mini map - sử dụng permanent map nếu level = 999
        if next_level == 999:
            map_data = make_permanent_map()
        else:
            map_data = make_map(next_level)
        preview_scale = 0.4  # Thu nhỏ map để vừa màn hình
        preview_tile = int(TILE * preview_scale)
        
        # Offset để căn giữa
        map_width = GRID_W * preview_tile
        map_height = GRID_H * preview_tile
        offset_x = (WIDTH - map_width) // 2
        offset_y = 150
        
        # Vẽ nền cỏ
        for gx in range(GRID_W):
            for gy in range(GRID_H):
                rect = pygame.Rect(
                    offset_x + gx * preview_tile,
                    offset_y + gy * preview_tile,
                    preview_tile, preview_tile
                )
                pygame.draw.rect(self.screen, (70, 140, 80), rect)
                pygame.draw.rect(self.screen, (50, 100, 60), rect, 1)
        
        # Vẽ đường đi
        path_cells = expand_path_cells(map_data)
        for (gx, gy) in path_cells:
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                rect = pygame.Rect(
                    offset_x + gx * preview_tile,
                    offset_y + gy * preview_tile,
                    preview_tile, preview_tile
                )
                pygame.draw.rect(self.screen, (200, 160, 100), rect)
        
        # Vẽ tower slots (tạo temporary để preview)
        class TempGame:
            def __init__(self):
                self.level = next_level
                self.path_cells = path_cells
                self.paths_grid = map_data
        
        temp_game = TempGame()
        tower_slots = self._generate_decorative_objects_preview(temp_game)
        
        for (gx, gy) in tower_slots:
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                rect = pygame.Rect(
                    offset_x + gx * preview_tile + 2,
                    offset_y + gy * preview_tile + 2,
                    preview_tile - 4, preview_tile - 4
                )
                pygame.draw.rect(self.screen, (100, 255, 150), rect)  # Xanh lá sáng
        
        # Thông tin level
        info_y = offset_y + map_height + 30
        
        # Tính toán số đường vào theo quy luật
        if next_level <= 3:
            paths_rule = "1 đường vào (Dễ)"
        elif next_level <= 6:
            paths_rule = "2 đường vào (Trung bình)"
        elif next_level <= 9:
            paths_rule = "3 đường vào (Khó)"
        else:
            paths_rule = "4 đường vào (Rất khó)"
        
        # Tính toán độ phức tạp map
        total_cells = sum(len(expand_path_cells([path])) for path in map_data)
        complexity = "Dễ" if next_level <= 3 else "Trung bình" if next_level <= 6 else "Khó" if next_level <= 9 else "Rất khó"
        
        info_lines = [
            f"Level tiếp theo: {next_level}/{TOTAL_LEVELS if next_level <= TOTAL_LEVELS else '∞'}",
            f"Số đường thực tế: {len(map_data)} ({paths_rule})",
            f"Số ô đặt trụ: {len(tower_slots)} (cách nhau 2-4 ô)",
            f"Độ phức tạp: {complexity}",
            f"Tổng ô đường đi: {total_cells}",
        ]
        
        # Thêm thông tin theme nếu level > 15
        if next_level > 15:
            info_lines.append(f"Theme: Lava/Rất khó (Map tự động)")
        
        for i, line in enumerate(info_lines):
            self.screen.blit(self.font.render(line, True, WHITE), (40, info_y + i * 25))
        
        # Chú thích và Quy luật - Ẩn khi xem permanent map (level 999)
        if next_level != 999:  # Ẩn khi là permanent map
            legend_x = WIDTH - 200
            legend_y = offset_y
            legend_items = [
                ("Cỏ", (70, 140, 80)),
                ("Đường đi", (200, 160, 100)),
                ("Ô đặt trụ", (100, 255, 150)),
            ]
            
            self.screen.blit(self.font.render("Chú thích:", True, WHITE), (legend_x, legend_y))
            for i, (label, color) in enumerate(legend_items):
                y = legend_y + 30 + i * 25
                pygame.draw.rect(self.screen, color, (legend_x, y, 20, 15))
                self.screen.blit(self.font.render(label, True, WHITE), (legend_x + 30, y))
            
            # Quy luật số đường vào và placement
            rule_y = legend_y + 150
            self.screen.blit(self.font.render("Quy luật:", True, ORANGE), (legend_x, rule_y))
            rules = [
                "Lv 1-3: 1 đường",
                "Lv 4-6: 2 đường", 
                "Lv 7-9: 3 đường",
                "Lv 10+: 4 đường",
                "---",
                "Trụ cách nhau 2-4 ô",
                "Chỉ đặt ở ô xanh"
            ]
            for i, rule in enumerate(rules):
                color = WHITE if rule != "---" else GRAY
                self.screen.blit(self.font.render(rule, True, color), (legend_x, rule_y + 25 + i * 18))
        
        # Hướng dẫn
        self.screen.blit(self.font.render("ESC: về menu", True, WHITE), (20, HEIGHT - 30))

        # ===== Auto-tiler & trang trí =====
    def _ensure_tiles_loaded(self):
        if not hasattr(self, "tiles") or self.tiles is None:
            self.tiles = try_tileset()

    def _is_path(self, x, y):
        return (x, y) in self.path_cells

    def _neighbors_mask(self, x, y):
        # bitmask NESW: N=1, E=2, S=4, W=8 (1 nếu là đường)
        n = 0
        if self._is_path(x, y-1): n |= 1
        if self._is_path(x+1, y): n |= 2
        if self._is_path(x, y+1): n |= 4
        if self._is_path(x-1, y): n |= 8
        return n

    def _neighbors_mask_tuple(self, gx, gy):
        """Trả về tuple (n, s, w, e) cho việc vẽ đường"""
        n = (gx, gy-1) in self.path_cells
        s = (gx, gy+1) in self.path_cells
        w = (gx-1, gy) in self.path_cells
        e = (gx+1, gy) in self.path_cells
        return n, s, w, e

    def _compute_decor_once(self):
        # tạo danh sách vật trang trí, gọi 1 lần mỗi khi khởi tạo level
        if getattr(self, "_decor_built", False):
            return
        self._decor_built = True
        self.decorations = []
        if not self.tiles: 
            return
        import random
        random.seed(42 + self.level)

        # rải bush/rock tại ô không phải đường & chưa bị chiếm
        for _ in range(18):
            x = random.randrange(0, GRID_W)
            y = random.randrange(0, GRID_H)
            if (x, y) in self.path_cells or (x, y) in getattr(self, "occupied", set()):
                continue
            kind = random.choice(["bush", "rock"])
            self.decorations.append((kind, x, y, random.uniform(-6, 6), random.uniform(-6, 6)))

    def _draw_tiles_autotile(self):
        """Vẽ nền cỏ + đường cát có viền/corner tự động, dùng assets/tiles/*."""
        self._ensure_tiles_loaded()
        if not self.tiles:
            return  # thiếu tiles → bỏ qua, fallback màu trơn ở draw_game

        # 1) nền cỏ - chỉ vẽ ở các vị trí tower slots
        grass = self.tiles.get("grass")
        tower_slot_positions = getattr(self, 'tower_slots', set())
            
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                if grass and (gx, gy) in tower_slot_positions:
                    self.screen.blit(grass, (gx * TILE, gy * TILE))

        # 2) trung tâm cát
        sand_center = self.tiles.get("sand_center")
        for (gx, gy) in self.path_cells:
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H and sand_center:
                self.screen.blit(sand_center, (gx * TILE, gy * TILE))

        # 3) cạnh & góc
        t = self.tiles
        eN, eE, eS, eW = t.get("sand_edge_n"), t.get("sand_edge_e"), t.get("sand_edge_s"), t.get("sand_edge_w")
        cNE, cNW, cSE, cSW = t.get("sand_corner_ne"), t.get("sand_corner_nw"), t.get("sand_corner_se"), t.get("sand_corner_sw")

        for (gx, gy) in self.path_cells:
            m = self._neighbors_mask(gx, gy)

            # Edges: nếu cạnh giáp cỏ
            if not self._is_path(gx, gy-1) and eN: self.screen.blit(eN, (gx*TILE, gy*TILE))
            if not self._is_path(gx+1, gy) and eE: self.screen.blit(eE, (gx*TILE, gy*TILE))
            if not self._is_path(gx, gy+1) and eS: self.screen.blit(eS, (gx*TILE, gy*TILE))
            if not self._is_path(gx-1, gy) and eW: self.screen.blit(eW, (gx*TILE, gy*TILE))

            # Corners: nếu là góc lồi ra cỏ
            if self._is_path(gx, gy-1) and self._is_path(gx+1, gy) and not self._is_path(gx+1, gy-1) and cNE:
                self.screen.blit(cNE, (gx*TILE, gy*TILE))
            if self._is_path(gx, gy-1) and self._is_path(gx-1, gy) and not self._is_path(gx-1, gy-1) and cNW:
                self.screen.blit(cNW, (gx*TILE, gy*TILE))
            if self._is_path(gx, gy+1) and self._is_path(gx+1, gy) and not self._is_path(gx+1, gy+1) and cSE:
                self.screen.blit(cSE, (gx*TILE, gy*TILE))
            if self._is_path(gx, gy+1) and self._is_path(gx-1, gy) and not self._is_path(gx-1, gy+1) and cSW:
                self.screen.blit(cSW, (gx*TILE, gy*TILE))

        # Vẽ decorative objects trước
        if hasattr(self, 'decorative_objects'):
            for decoration in self.decorative_objects:
                self._draw_decoration(decoration)

        # Hiển thị grid placement indicators (vẽ sau decorations để không bị che)
        if getattr(self, 'show_placement_grid', True):
            decoration_positions = set()
            if hasattr(self, 'decorative_objects'):
                decoration_positions = {decoration["pos"] for decoration in self.decorative_objects}
                
            # Vẽ indicators cho tất cả các ô
            for gx in range(GRID_W):
                for gy in range(GRID_H):
                    cell = (gx, gy)
                    
                    # Kiểm tra trạng thái của ô
                    if cell in self.path_cells:
                        # Ô đường đi - không vẽ gì (đã có sand tiles)
                        continue
                    elif cell in decoration_positions:
                        # Ô có decoration - không vẽ indicator
                        continue
                    elif hasattr(self, 'tower_slots') and cell in self.tower_slots:
                        if cell in self.occupied:
                            # Ô có tower - viền xanh đậm mạnh
                            rect = pygame.Rect(gx*TILE + 1, gy*TILE + 1, TILE-2, TILE-2)
                            pygame.draw.rect(self.screen, (0, 200, 0), rect, width=4, border_radius=8)
                        else:
                            # Ô có thể đặt tower - nền xanh sáng + viền đậm + dấu "+"
                            rect = pygame.Rect(gx*TILE + 3, gy*TILE + 3, TILE-6, TILE-6)
                            # pygame.draw.rect(self.screen, (120, 255, 120, 120), rect, border_radius=8)  # T?t n?n xanh
                            # pygame.draw.rect(self.screen, (0, 180, 0), rect, width=3, border_radius=8)  # T?t vi?n xanh
                            
                            # Dấu "+" lớn hơn và rõ hơn
                            center_x = gx*TILE + TILE//2
                            center_y = gy*TILE + TILE//2
                            # Dấu + trắng với viền đen để nổi bật
                            for offset in [(0,0), (-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
                                x_off, y_off = offset
                                pygame.draw.line(self.screen, (0, 0, 0), 
                                               (center_x - 12 + x_off, center_y + y_off), 
                                               (center_x + 12 + x_off, center_y + y_off), 3)
                                pygame.draw.line(self.screen, (0, 0, 0), 
                                               (center_x + x_off, center_y - 12 + y_off), 
                                               (center_x + x_off, center_y + 12 + y_off), 3)
                            # Dấu + trắng chính
                            pygame.draw.line(self.screen, (255, 255, 255), 
                                           (center_x - 12, center_y), (center_x + 12, center_y), 3)
                            pygame.draw.line(self.screen, (255, 255, 255), 
                                           (center_x, center_y - 12), (center_x, center_y + 12), 3)
                    # else: Ô không thể đặt tower - để trống cho decorations tùy chỉnh

    def _draw_decor_and_markers(self):
        """Rải bụi cây/đá + cổng/nhà căn cứ."""
        if not self.tiles:
            return
        # vật trang trí
        for kind, gx, gy, dx, dy in getattr(self, "decorations", []):
            img = self.tiles.get(kind)
            if not img: 
                continue
            x = gx * TILE + int(dx)
            y = gy * TILE + int(dy)
            # vẽ bóng mềm
            pygame.draw.ellipse(self.screen, (0,0,0,35), (x+8, y+TILE-14, TILE-16, 10))
            self.screen.blit(img, (x, y))

        # Vẽ animated gates thay cho cổng tĩnh
        for gate in self.animated_gates:
            gate.draw(self.screen, self.tiles)

    def _load_map_background(self, level: int):
        """Load background image cho level cụ thể."""
        self.map_bg = None
        # Tìm background theo level
        candidates = [
            os.path.join(ASSETS_DIR, "backgrounds", f"level_{level}.png"),
            os.path.join(ASSETS_DIR, "backgrounds", f"map_{level}.png"),
            os.path.join(ASSETS_DIR, f"background_level_{level}.png"),
            os.path.join(ASSETS_DIR, f"background_{level}.png"),
        ]
        
        for p in candidates:
            try:
                img = pygame.image.load(p).convert()
                self.map_bg = pygame.transform.scale(img, (WIDTH, HEIGHT))
                break
            except Exception:
                pass
        
        # Nếu không tìm thấy background cụ thể cho level, không tạo map_bg
        # Để draw_game() sử dụng _draw_enhanced_background() làm fallback
        if self.map_bg is None:
            pass  # Không tạo map_bg, để sử dụng texture background
            
    def _generate_level_background(self, level: int):
        """Tạo background tự động cho level dựa trên theme."""
        bg = pygame.Surface((WIDTH, HEIGHT))
        
        # Chọn theme dựa trên số đường vào theo quy luật mới
        if level <= 3:
            # Level 1-3: 1 đường vào - Theme cỏ xanh (dễ)
            bg.fill((45, 120, 60))  # Xanh cỏ đậm
        elif level <= 6:
            # Level 4-6: 2 đường vào - Theme sa mạc (trung bình)
            bg.fill((160, 130, 80))  # Vàng cát
        elif level <= 9:
            # Level 7-9: 3 đường vào - Theme tuyết (khó)
            bg.fill((200, 220, 240))  # Xanh trắng
        else:
            # Level 10+: 4 đường vào - Theme lava (rất khó)
            bg.fill((80, 30, 20))  # Đỏ đen
        
        # Thêm texture đơn giản
        import random
        random.seed(level * 123)  # Seed cố định cho level
        
        for _ in range(50):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            size = random.randint(20, 80)
            alpha = random.randint(10, 30)
            
            if level <= 3:
                color = (30, 100, 40, alpha)  # Cỏ đậm hơn
            elif level <= 6:
                color = (140, 110, 60, alpha)  # Cát đậm hơn
            elif level <= 9:
                color = (180, 200, 220, alpha)  # Tuyết
            else:
                color = (120, 60, 40, alpha)  # Đá lava
            
            # Vẽ các chấm texture
            temp_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, color, (size//2, size//2), size//2)
            bg.blit(temp_surf, (x-size//2, y-size//2), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        return bg        
    def _load_bg_cached(self, filename):
        try:
            img = pygame.image.load(os.path.join(ASSETS_DIR, filename)).convert()
            return pygame.transform.scale(img, (WIDTH, HEIGHT))
        except Exception:
            return None



    def menu_leader(self):
        self.scene = SCENE_LEADER
    def menu_auth(self):
        self.scene = SCENE_AUTH
        self.auth_msg = ""
    def _get_font(self, size, bold=False):
        """Tạo font hỗ trợ tiếng Việt với fallback"""
        font_names = ["tahoma", "segoe ui", "arial", "calibri"]
        
        for font_name in font_names:
            try:
                return pygame.font.SysFont(font_name, size, bold=bold)
            except:
                continue
        
        # Fallback to default font
        return pygame.font.Font(None, int(size * 1.2))
    
    def _draw_text_with_outline(self, text, font, text_color, outline_color, x, y, outline_width=2):
        """Vẽ text với viền để dễ đọc hơn"""
        # Vẽ viền bằng cách vẽ text ở các vị trí xung quanh
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:  # Không vẽ ở vị trí chính giữa
                    outline_surface = font.render(text, True, outline_color)
                    self.screen.blit(outline_surface, (x + dx, y + dy))
        
        # Vẽ text chính ở giữa
        main_surface = font.render(text, True, text_color)
        self.screen.blit(main_surface, (x, y))
        return main_surface.get_rect(x=x, y=y)

    def __init__(self):
        # ...existing code...
        self.auth_pass2 = ""  # Thêm biến xác nhận mật khẩu
        # ...existing code...
        # Khởi tạo mixer trước để tránh trễ tải âm thanh
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.init(); pygame.mixer.set_num_channels(24)
        except Exception as e:
            print("Mixer init failed:", e)
        pygame.init()
        pygame.display.set_caption("Tower Defense")

        # Bật DOUBLEBUF + thử vsync
        flags = pygame.SCALED | pygame.DOUBLEBUF
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1)
        except TypeError:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)

        self.clock = pygame.time.Clock()
        # Sử dụng font mặc định của pygame hoặc tahoma để hỗ trợ tiếng Việt tốt
        self.font = self._get_font(20)
        self.bigfont = self._get_font(40, bold=True)
        self.medfont = self._get_font(24, bold=False)

        # ✅ KHỞI TẠO ẢNH NỀN MENU 1 LẦN (tránh AttributeError)
        self.bg_menu = self._load_bg_cached("background.png")  # trả về Surface hoặc None


        # --- Save & mặc định ---
        self.save = load_save()
        self._migrate_old_save_data()  # Chuyển đổi dữ liệu cũ
        self.player_name = self.save.get("player_name", "Player")

    # --- Accounts / Auth state ---
        self.accounts = load_accounts()
        self._migrate_old_accounts_data()  # Chuyển đổi dữ liệu accounts cũ
        self.current_user = None
        self.auth_msg = ""
        self.auth_mode = "login"
        self.auth_user = ""
        self.auth_pass = ""
        self._auth_focus = "user"
        self._auth_rects = {}

# -> BẮT ĐẦU Ở MÀN ĐĂNG NHẬP
        self.scene = SCENE_AUTH

# Nút menu (dùng sau khi quay về menu) - mặc định Easy mode
        self.menu_mode_idx = 0  # 0=Easy, 1=Normal, 2=Hard
        self.menu_buttons = []
        self.settings_buttons = []  # Buttons cho màn hình settings
        
        # Preview map state
        self.selected_level_preview = None
        self.selected_mode_preview = None
        
        # Khởi tạo pause_buttons trước để tránh lỗi AttributeError
        self.pause_buttons = []
        
        self._build_menu_buttons()

# Nhạc menu…
        self.menu_tracks = list_music(MUSIC_MENU_DIR)
        self.game_tracks = list_music(MUSIC_GAME_DIR)
        if self.save["settings"]["music"]:
            play_random_music(self.menu_tracks, self.save["settings"]["volume"])

# Chuẩn bị runtime nhưng KHÔNG vào game (scene vẫn là AUTH)
        self.selected_map_idx = 0
        self._init_runtime("Normal", level=1, new_game=True)

        # build menu
        self.menu_buttons: List[Button] = []
        self._build_menu_buttons()


        # ==== Helpers lưu tiến độ theo user đang đăng nhập ====
    def get_unlocked_towers(self):
        """Lấy danh sách trụ đã mở theo user hiện tại (hoặc save mặc định)."""
        if self.current_user:
            return self.accounts.get(self.current_user, {}).get("unlocked_towers", [])
        return self.save.get("unlocked_towers", [])

    def set_unlocked_towers(self, towers_list):
        """Ghi danh sách trụ đã mở cho user hiện tại (hoặc save mặc định)."""
        if self.current_user:
            acc = self.accounts.setdefault(self.current_user, {})
            acc["unlocked_towers"] = list(towers_list)
            save_accounts(self.accounts)
        else:
            self.save["unlocked_towers"] = list(towers_list)
            save_save(self.save)

    def get_stars(self):
        if self.current_user:
            return self.accounts.get(self.current_user, {}).get("stars", 0)
        return self.save.get("stars", 0)

    def set_stars(self, n):
        if self.current_user:
            acc = self.accounts.setdefault(self.current_user, {})
            acc["stars"] = int(n)
            save_accounts(self.accounts)
        else:
            self.save["stars"] = int(n)
            save_save(self.save)

        # Thống kê vòng chơi
        self.kills = 0
        self.towers_built = 0
        self.money_spent = 0
        self.start_time = time.time()
        self.powerups_used = 0
        self.notice_msg = ""    # thông báo nhỏ
        self.notice_timer = 0.0

        # Âm bắn
        self.snd_shoot = load_shoot_sound()
        self._shoot_snd_cooldown = 0.0

        # Sprite - Load tất cả 12 tháp
        self.tower_sprites = {}
        for tower_key in ALL_TOWER_KEYS:
            sprite_file = TOWER_DEFS[tower_key]["sprite"]
            # Kích thước khác nhau theo loại tháp
            if tower_key == "sniper":
                size = 52
            elif tower_key in ["splash", "mortar", "rocket"]:
                size = 56
            elif tower_key == "slow":
                size = 50
            else:
                size = 48
            self.tower_sprites[tower_key] = load_sprite(sprite_file, size)
            
        # Enemy sprites - Load tất cả 4 loại địch
        self.enemy_sprites = {}
        base_size = 36
        for enemy_key in ["normal", "fast", "tank", "boss"]:
            sprite_file = f"enemy_{enemy_key}.png"
            # Kích thước theo size_mul từ config
            size_mul = ENEMY_TYPES[enemy_key].get("size_mul", 1.0)
            actual_size = int(base_size * size_mul)
            self.enemy_sprites[enemy_key] = load_sprite(sprite_file, actual_size)
        
        # Fallback enemy sprite
        self.enemy_sprite = load_sprite("enemy.png", base_size)

        # World
        self.towers: List[Tower] = []
        self.projectiles: List[Projectile] = []
        self.enemies: List[Enemy] = []
        # ✅ mảng ô đã chiếm chỗ bởi tháp
        self.occupied = set()

        # Đường đi
        multipath_grid = MAPS[(self.level - 1) % len(MAPS)]
        self.paths_grid = multipath_grid
        self.paths_px = [grid_nodes_to_px(p) for p in multipath_grid]
        self.path_cells = expand_path_cells(multipath_grid)
        self.exit_cells = [p[-1] for p in multipath_grid]

        # Wave
        self.wave_mgr = WaveManager(self.paths_px, MODE_PARAMS[self.mode_name]["hp_mul"], MODE_PARAMS[self.mode_name]["spd_mul"], level=self.level)
        self.wave_mgr.start_next_wave()

        # Tiles
        self.tiles = try_tileset()
        self.decorations = []

        # Trụ đã mở khoá từ loadout & trụ đang chọn
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            self.unlocked_towers = list(account.get("current_loadout", DEFAULT_LOADOUT.copy()))
        else:
            self.unlocked_towers = list(DEFAULT_LOADOUT)
        self.selected_tower  = self.unlocked_towers[0] if self.unlocked_towers else None


        # Global slow (không dùng, để sẵn nếu muốn mở rộng)
        self.global_slow_timer = 0.0
        self.global_slow_mul = 1.0

        # Nút tạm dừng
        self.pause_buttons = [
            Button((WIDTH//2-120, HEIGHT//2-120, 240, 40), "Tiếp tục (C)", self.toggle_pause),
            Button((WIDTH//2-120, HEIGHT//2-70, 240, 40), "Cài đặt", self.menu_settings),
            Button((WIDTH//2-120, HEIGHT//2-20, 240, 40), "Chơi lại (R)", lambda: self._init_runtime(self.mode_name, self.level)),
            Button((WIDTH//2-120, HEIGHT//2+30, 240, 40), "Trang chính", self.back_to_menu),
            Button((WIDTH//2-120, HEIGHT//2+80, 240, 40), "Kết thúc",
                    lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)))
        ]

        if self.scene == SCENE_GAME and self.save["settings"]["music"]:
            play_random_music(self.game_tracks, self.save["settings"]["volume"])

    # --------- Button menu chính ---------
    def _build_menu_buttons(self):
        self.menu_buttons.clear()
        
        if self.current_user:
            # Layout 2 cột cho menu đầy đủ - đẩy ra xa hơn để không che logo
            col1_x = 260      # Cột trái: cách lề trái 50px
            col2_x = WIDTH - 460   # Cột phải: cách lề phải 50px (230 = width + margin)
            w, h = 180, 38
            gap = 50
            y_start = 180
            
            # Cột trái - 4 nút chính
            main_items = [
                ("Chọn màn chơi", self.menu_level_select),
                ("Cửa hàng", self.menu_shop),
                ("Thành tựu", self.menu_stats),
                ("Bảng xếp hạng", self.menu_leader),
            ]
            
            # Cột phải - 4 nút phụ
            sub_items = [
                ("Cài đặt", self.menu_settings),
                ("Đổi tên người chơi", self.menu_name),
                ("Đăng xuất", self.menu_logout),
                ("Thoát", self.quit_game),
            ]
            
            # Thêm buttons cột trái
            for i, (text, cb) in enumerate(main_items):
                y = y_start + i * gap
                self.menu_buttons.append(Button((col1_x, y, w, h), text, cb))
                
            # Thêm buttons cột phải
            for i, (text, cb) in enumerate(sub_items):
                y = y_start + i * gap
                self.menu_buttons.append(Button((col2_x, y, w, h), text, cb))
                
        else:
            # Chưa đăng nhập → menu đơn giản ở giữa
            x = WIDTH // 2 - 140
            w, h = 280, 38
            gap = 50
            y_start = 220
            
            items = [
                ("Đăng nhập / Đăng ký", self.menu_auth),
                ("Xem Bảng xếp hạng", self.menu_leader),
                ("Thoát", self.quit_game),
            ]

            for i, (text, cb) in enumerate(items):
                y = y_start + i * gap
                self.menu_buttons.append(Button((x, y, w, h), text, cb))
        
        # Thêm nút âm thanh ở góc dưới trái cho mọi trường hợp
        self._add_audio_buttons()

    def _add_audio_buttons(self):
        """Thêm nút bật/tắt âm thanh ở góc dưới trái menu."""
        # Vị trí góc dưới trái - tối ưu hóa
        x = 25
        # Đã xóa 2 nút nhạc nền và âm thanh - sử dụng menu Cài đặt thay thế

    def quit_game(self):
        """Thoát game an toàn khi bấm nút Thoát (menu/pause)."""
        pygame.quit()
        sys.exit(0)


    # --------- Save helpers ---------
    def add_achievement(self, key):
        self.save["achievements"][key]=True; save_save(self.save)

    # record_leaderboard removed - chỉ lưu điểm từ Permanent Map

    # --------- Callback menu ---------
    def menu_continue(self):
        if not self.current_user:
            self.menu_auth();  # ép mở form đăng nhập
            return
        
        # Chuyển đến màn hình chọn level thay vì vào game trực tiếp
        self.menu_level_select()



    def menu_newgame(self):
        # Reset tất cả chế độ về level 1 để người chơi bắt đầu lại hoàn toàn
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            if "level_unlocked_by_mode" not in account:
                account["level_unlocked_by_mode"] = {"Easy": 1, "Normal": 1, "Hard": 1}
            # Reset tất cả chế độ về 1
            account["level_unlocked_by_mode"] = {"Easy": 1, "Normal": 1, "Hard": 1}
            account["level_unlocked"] = 1
            save_accounts(self.accounts)
        else:
            if "level_unlocked_by_mode" not in self.save:
                self.save["level_unlocked_by_mode"] = {"Easy": 1, "Normal": 1, "Hard": 1}
            self.save["level_unlocked_by_mode"] = {"Easy": 1, "Normal": 1, "Hard": 1}
            self.save["level_unlocked"] = 1
            save_save(self.save)

        # Chuyển đến màn hình chọn level
        self.menu_level_select()

    # ------------------- VÒNG LẶP CHÍNH -------------------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
        pygame.quit()

    # ------------------- XỬ LÝ INPUT -------------------
    def handle_event(self, event):
        if self.scene == SCENE_MENU:
            self.handle_menu_event(event)
        elif self.scene == SCENE_GAME:
            self.handle_game_event(event)
        elif self.scene == SCENE_AUTH:
            self.handle_auth_event(event)
        elif self.scene == SCENE_LEVEL_SELECT:
            self.handle_level_select_event(event)
        elif self.scene == SCENE_SETTINGS:
            self.handle_settings_event(event)
        elif self.scene == SCENE_LEADER:
            self.handle_leader_event(event)
        elif self.scene == SCENE_STATS:
            self.handle_stats_event(event)
        elif self.scene == SCENE_MAP_PREVIEW:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.back_to_menu()
        else:
            self.handle_submenu_event(event)

    def handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: self.menu_continue()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for b in self.menu_buttons: b.handle(event)

    def handle_settings_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back_to_menu()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for b in self.settings_buttons: b.handle(event)

    def handle_submenu_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back_to_menu(); return

        elif self.scene == SCENE_SHOP and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            if "_back" in self._shop_rects and self._shop_rects["_back"].collidepoint((mx, my)):
                self.back_to_menu()
                return
                
            # Xử lý click vào tower cards
            for tower_key in ALL_TOWER_KEYS:
                # Nút mua tower
                buy_key = f"buy_{tower_key}"
                if buy_key in self._shop_rects and self._shop_rects[buy_key].collidepoint((mx, my)):
                    self._handle_buy_tower(tower_key)
                    break
                    
                # Nút chọn tower cho loadout  
                select_key = f"select_{tower_key}"
                if select_key in self._shop_rects and self._shop_rects[select_key].collidepoint((mx, my)):
                    self._handle_select_tower(tower_key)
                    break
    
        elif self.scene == SCENE_NAME:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    new_name = self.name_input.strip() or "Player"
                    
                    # Kiểm tra trùng tên với người chơi khác
                    name_exists = False
                    current_user_name = None
                    
                    # Lấy tên hiện tại của user (nếu có)
                    if self.current_user and self.current_user in self.accounts:
                        current_user_name = self.accounts[self.current_user].get("player_name", self.current_user)
                    else:
                        current_user_name = self.save.get("player_name", "Player")
                    
                    # Nếu tên mới giống tên hiện tại thì cho phép (không thay đổi gì)
                    if new_name != current_user_name:
                        # Kiểm tra trùng với tên trong accounts
                        for username, account_data in self.accounts.items():
                            if username != self.current_user:  # Bỏ qua chính mình
                                existing_name = account_data.get("player_name", username)
                                if new_name.lower() == existing_name.lower():  # So sánh không phân biệt hoa thường
                                    name_exists = True
                                    break
                        
                        # Kiểm tra trùng với tên trong save cũ (người chưa đăng nhập)
                        if not name_exists:
                            old_leaderboard = self.save.get("leaderboard", [])
                            for entry in old_leaderboard:
                                existing_name = entry.get("name", "")
                                if new_name.lower() == existing_name.lower():
                                    name_exists = True
                                    break
                    
                    if name_exists:
                        # Hiển thị thông báo lỗi thay vì đổi tên
                        self.auth_msg = f"Tên '{new_name}' đã được sử dụng bởi người chơi khác!"
                        return
                    
                    # Tên hợp lệ - thực hiện đổi tên
                    self.player_name = new_name
                    
                    # Lưu vào đúng nơi tùy theo trạng thái đăng nhập
                    if self.current_user and self.current_user in self.accounts:
                        # Lưu vào account hiện tại
                        self.accounts[self.current_user]["player_name"] = new_name
                        save_accounts(self.accounts)
                    else:
                        # Lưu vào save file (người chưa đăng nhập)
                        self.save["player_name"] = self.player_name
                        save_save(self.save)
                    
                    # Cập nhật player_name vào account nếu đã đăng nhập
                    if self.current_user and self.current_user in self.accounts:
                        self.accounts[self.current_user]["player_name"] = self.player_name
                        save_accounts(self.accounts)
                    
                    # Reset thông báo lỗi và quay về menu
                    self.auth_msg = ""
                    self.back_to_menu()
                elif event.key == pygame.K_ESCAPE:
                    # Hủy và reset thông báo lỗi
                    self.auth_msg = ""
                    self.back_to_menu()
                elif event.key == pygame.K_BACKSPACE: 
                    self.name_input = self.name_input[:-1]
                    # Clear thông báo lỗi khi người dùng chỉnh sửa
                    self.auth_msg = ""
                else:
                    ch = event.unicode
                    if ch.isprintable() and len(self.name_input)<16: 
                        self.name_input += ch
                        # Clear thông báo lỗi khi người dùng nhập
                        self.auth_msg = ""

    def handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.back_to_menu()
            elif event.key == pygame.K_p: self.toggle_pause()
            elif event.key == pygame.K_c: self.toggle_pause(False)
            # Bắt đầu trận đấu sớm - PHẢI ĐẶT TRƯỚC speed toggle
            elif event.key == pygame.K_SPACE and self.in_setup_phase:
                self.in_setup_phase = False
                self.setup_time = 0
                self.wave_mgr.start_next_wave()
                self.notice("⚔️ BẮT ĐẦU SỚM! ⚔️", 3.0)
            elif event.key == pygame.K_SPACE: self.speed_scale = 1.0 if self.speed_scale > 1.0 else 2.0
            elif event.key == pygame.K_r: self._init_runtime(self.mode_name, self.level)
            elif event.key == pygame.K_n and self.win_level: self.go_next_or_clear()
            elif event.key == pygame.K_g: self.show_placement_grid = not self.show_placement_grid  # Toggle placement grid
            # chọn trụ bằng số
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = int(event.unicode)-1 if event.unicode.isdigit() else 0
                if 0<=idx<4:
                    # Lấy loadout hiện tại từ account
                    if self.current_user and self.current_user in self.accounts:
                        account = self.accounts[self.current_user]
                        current_loadout = account.get("current_loadout", DEFAULT_LOADOUT)
                    else:
                        current_loadout = DEFAULT_LOADOUT
                    
                    if idx < len(current_loadout):
                        key = current_loadout[idx]
                        self.selected_tower = key
                        self.notice("Chọn trụ: " + TOWER_DEFS[key]["name"])
            # powerups
            elif event.key == pygame.K_f: self.buy_freeze()
            elif event.key == pygame.K_a: self.buy_airstrike()
            # Toggle hiển thị tầm bắn
            elif event.key == pygame.K_r: 
                self.show_all_ranges = not self.show_all_ranges
                self.notice(f"Hiển thị tầm bắn: {'BẬT' if self.show_all_ranges else 'TẮT'}", 2.0)

        elif event.type == pygame.MOUSEBUTTONDOWN and self.lives > 0 and not self.win_level and not self.paused:
            mx, my = pygame.mouse.get_pos()
            # click Audio controls
            if self._audio_control_click(mx,my): return
            # click Powerup
            if self._powerup_click(mx,my): return
            # click chọn trụ ở hotbar
            if self._hotbar_click(mx,my): return
            # đặt / nâng cấp / gỡ
            gx, gy = px_to_grid(mx, my)
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                cell = (gx, gy)
                if event.button == 1:
                    tower = self._find_tower_at(cell)
                    if tower: 
                        # Chọn tower để hiện tầm bắn hoặc nâng cấp
                        if self.selected_tower_for_range == tower:
                            # Nếu đã chọn rồi thì nâng cấp
                            self.try_upgrade_tower(tower)
                        else:
                            # Chọn tower để hiện tầm bắn
                            self.selected_tower_for_range = tower
                            self.notice(f"Chọn {TOWER_DEFS[tower.ttype]['name']} - Tầm bắn: {int(tower.range)}px")
                    elif self.selected_tower: 
                        self.try_place_tower(gx, gy, self.selected_tower)
                    else:
                        # Click vào chỗ trống thì bỏ chọn tower
                        self.selected_tower_for_range = None
                elif event.button == 3: 
                    self.try_remove_tower(gx, gy)
            else:
                # Click ra ngoài map thì bỏ chọn tower
                if event.button == 1:
                    self.selected_tower_for_range = None
                    
        elif event.type == pygame.MOUSEMOTION:
            # Xử lý mouse hover cho powerup buttons
            self._handle_powerup_hover(event.pos)

        elif self.paused and event.type == pygame.MOUSEBUTTONDOWN:
            # Kiểm tra xem pause_buttons có tồn tại không trước khi sử dụng
            if hasattr(self, 'pause_buttons') and self.pause_buttons:
                for b in self.pause_buttons: b.handle(event)
    def handle_auth_event(self, event):
    # Xử lý phím/chuột cho màn Đăng nhập / Đăng ký
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_to_menu()
                return
            if event.key == pygame.K_RETURN:
                self._auth_submit()
                return
            if event.key == pygame.K_BACKSPACE:
                if self._auth_focus == "user":
                    self.auth_user = self.auth_user[:-1]
                elif self._auth_focus == "pass":
                    self.auth_pass = self.auth_pass[:-1]
                elif self._auth_focus == "pass2":
                    self.auth_pass2 = self.auth_pass2[:-1]
                return

            ch = event.unicode
            if ch and ch.isprintable():
                if self._auth_focus == "user" and len(self.auth_user) < 16:
                    self.auth_user += ch
                elif self._auth_focus == "pass" and len(self.auth_pass) < 24:
                    self.auth_pass += ch
                elif self._auth_focus == "pass2" and len(self.auth_pass2) < 24:
                    self.auth_pass2 += ch

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            r = self._auth_rects or {}
            if r.get("tab_login") and r["tab_login"].collidepoint((mx, my)):
                self.auth_mode = "login"; self.auth_msg = ""
            elif r.get("tab_reg") and r["tab_reg"].collidepoint((mx, my)):
                self.auth_mode = "register"; self.auth_msg = ""
            elif r.get("user") and r["user"].collidepoint((mx, my)):
                self._auth_focus = "user"
            elif r.get("pass") and r["pass"].collidepoint((mx, my)):
                self._auth_focus = "pass"
            elif r.get("pass2") and r["pass2"] and r["pass2"].collidepoint((mx, my)):
                self._auth_focus = "pass2"
            elif r.get("ok") and r["ok"].collidepoint((mx, my)):
                self._auth_submit()
            elif r.get("back") and r["back"].collidepoint((mx, my)):
                self.back_to_menu()

    def _auth_submit(self):
        u = self.auth_user.strip()
        p = self.auth_pass.strip()
        p2 = self.auth_pass2.strip()
        if not u or not p or (self.auth_mode == "register" and not p2):
            self.auth_msg = "Tên, mật khẩu và xác nhận không được để trống!"
            return

        if self.auth_mode == "login":
            if u not in self.accounts:
                self.auth_msg = "Tài khoản không tồn tại!"
                return
            
            account = self.accounts[u]
            
            # Kiểm tra hệ thống cũ (plain text password với key "pass")
            if "pass" in account and "pw" not in account:
                # Tài khoản cũ - so sánh trực tiếp
                if account["pass"] != p:
                    self.auth_msg = "Sai tên hoặc mật khẩu!"
                    return
                    
                # Upgrade tài khoản cũ lên hệ thống mới
                salt = secrets.token_hex(8)
                account["salt"] = salt
                account["pw"] = _hash_password(p, salt)
                del account["pass"]  # Xóa mật khẩu cũ
                
                # Thêm các trường mới nếu chưa có
                if "player_name" not in account:
                    account["player_name"] = u
                if "leaderboard" not in account:
                    account["leaderboard"] = []
                    
                save_accounts(self.accounts)
                
            # Kiểm tra hệ thống mới (hash password với key "pw")
            elif "pw" in account and "salt" in account:
                salt = account["salt"]
                hashed_input = _hash_password(p, salt)
                if account["pw"] != hashed_input:
                    self.auth_msg = "Sai tên hoặc mật khẩu!"
                    return
            else:
                # Tài khoản bị hỏng
                self.auth_msg = "Tài khoản bị lỗi, vui lòng liên hệ admin!"
                return
        elif self.auth_mode == "register":
            if u in self.accounts:
                self.auth_msg = "Tên đã tồn tại!"
                return
            if p != p2:
                self.auth_msg = "Mật khẩu xác nhận không khớp!"
                return
            # Tạo account mới với function chuẩn
            self.accounts[u] = _new_account_record(u, p)
            save_accounts(self.accounts)

        # Đăng nhập thành công
        self.current_user = u
        self.auth_msg = "Đăng nhập thành công!"
        
        # Đồng bộ player_name từ save hiện tại vào account nếu chưa có
        if "player_name" not in self.accounts[u]:
            self.accounts[u]["player_name"] = u  # Dùng tên tài khoản làm tên hiển thị mặc định
            save_accounts(self.accounts)
        
        # Cập nhật player_name hiện tại từ account
        self.player_name = self.accounts[u]["player_name"]
        
        self._build_menu_buttons()
        self.back_to_menu()

    def handle_leader_event(self, event):
        """Xử lý sự kiện trong bảng xếp hạng."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_to_menu()
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            
            # Kiểm tra click vào nút "Trở về Menu"
            back_button_rect = pygame.Rect(WIDTH//2 - 75, HEIGHT - 80, 150, 50)
            if back_button_rect.collidepoint((mx, my)):
                self.back_to_menu()
                return

    def handle_stats_event(self, event):
        """Xử lý sự kiện trong bảng thành tựu."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_to_menu()
                return
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            
            # Kiểm tra click vào nút "Trở về Menu" - giống bảng xếp hạng
            back_button_rect = pygame.Rect(WIDTH//2 - 75, HEIGHT - 80, 150, 50)
            if back_button_rect.collidepoint((mx, my)):
                self.back_to_menu()
                return

    def handle_level_select_event(self, event):
        """Xử lý sự kiện trong màn hình chọn level."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_to_menu()
                return
            # Keyboard shortcuts for mode switching in level select
            elif event.key == pygame.K_LEFT:
                self.menu_mode_idx = (self.menu_mode_idx - 1) % len(MODES)
                self.notice(f"Chế độ: {MODES[self.menu_mode_idx]} (← →)")
                return
            elif event.key == pygame.K_RIGHT:
                self.menu_mode_idx = (self.menu_mode_idx + 1) % len(MODES)
                self.notice(f"Chế độ: {MODES[self.menu_mode_idx]} (← →)")
                return
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            
            # Kiểm tra click vào preview panel trước
            if hasattr(self, '_preview_rects') and self._preview_rects:
                # Nút CHƠI
                if 'play' in self._preview_rects and self._preview_rects['play'].collidepoint((mx, my)):
                    if hasattr(self, 'selected_level_preview') and self.selected_level_preview:
                        # Bắt đầu chơi level đã chọn
                        self._init_runtime(self.selected_mode_preview, self.selected_level_preview, new_game=False)
                        self.scene = SCENE_GAME
                        if self.save["settings"]["music"]:
                            play_random_music(self.game_tracks, self.save["settings"]["volume"])
                        # Reset preview
                        self.selected_level_preview = None
                        self.selected_mode_preview = None
                        return
                
                # Nút HỦY
                if 'cancel' in self._preview_rects and self._preview_rects['cancel'].collidepoint((mx, my)):
                    # Đóng preview
                    self.selected_level_preview = None
                    self.selected_mode_preview = None
                    return
            
            # Lấy số level đã mở theo chế độ hiện tại
            current_mode = MODES[self.menu_mode_idx]
            
            if self.current_user and self.current_user in self.accounts:
                account = self.accounts[self.current_user]
                level_by_mode = account.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
                max_level = level_by_mode.get(current_mode, 1)
            else:
                level_by_mode = self.save.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
                max_level = level_by_mode.get(current_mode, 1)
            
            # First check mode selector with hardcoded positions (direct approach)
            # Mode selector coordinates should match draw_level_select
            mode_selector_y = 120
            mode_button_w = 100
            mode_button_h = 40
            mode_gap = 15
            total_mode_width = len(MODES) * mode_button_w + (len(MODES) - 1) * mode_gap
            mode_start_x = (WIDTH - total_mode_width) // 2
            
            for i, mode in enumerate(MODES):
                mode_x = mode_start_x + i * (mode_button_w + mode_gap)
                mode_rect = pygame.Rect(mode_x, mode_selector_y, mode_button_w, mode_button_h)
                if mode_rect.collidepoint((mx, my)):
                    self.menu_mode_idx = i
                    self.notice(f"Chế độ: {MODES[i]}")
                    return  # Mode changed, redraw will happen
            
            # Prefer using the rects computed during drawing (ensures click area matches visuals).
            # Fallback: if rects not available, compute layout using the same constants as draw_level_select.
            if hasattr(self, '_level_rects') and self._level_rects:
                
                # Back button
                back_rect = self._level_rects.get("_back")
                if back_rect and back_rect.collidepoint((mx, my)):
                    self.back_to_menu(); return

                # Check each stored level rect
                for k, rect in list(self._level_rects.items()):
                    if k == "_back" or k.startswith("mode_"):
                        continue
                    try:
                        lvl = int(k)
                    except Exception:
                        continue
                    if rect.collidepoint((mx, my)):
                        # Hiển thị preview map thay vì chơi ngay
                        self.selected_level_preview = lvl
                        self.selected_mode_preview = MODES[self.menu_mode_idx]
                        return

            # Fallback layout (should rarely be used) - match draw_level_select constants
            cols = 4
            level_per_page = 20  # Hiển thị 20 level mỗi trang
            button_size = 90
            gap = 25
            start_x = (WIDTH - cols * (button_size + gap)) // 2
            start_y = 290  # match draw - updated for mode selector
            
            # Kiểm tra click nút "Trở về" (fallback size matching draw)
            back_button_rect = pygame.Rect(50, HEIGHT - 100, 150, 55)
            if back_button_rect.collidepoint((mx, my)):
                self.back_to_menu()
                return

            for level in range(1, min(max_level + 1, level_per_page + 1)):
                row = (level - 1) // cols
                col = (level - 1) % cols
                
                x = start_x + col * (button_size + gap)
                y = start_y + row * (button_size + gap)
                
                level_rect = pygame.Rect(x, y, button_size, button_size)
                
                if level_rect.collidepoint((mx, my)):
                    # Hiển thị preview map thay vì chơi ngay
                    self.selected_level_preview = level
                    self.selected_mode_preview = MODES[self.menu_mode_idx]
                    return




    # -------- Helpers chung --------
    def go_next_or_clear(self):
        if self.level >= MAX_LEVELS: 
            self.scene = SCENE_ALL_CLEAR
        else: 
            self._init_runtime(self.mode_name, self.level + 1)

    def toggle_pause(self, value=None): self.paused = (not self.paused) if value is None else value
    def _find_tower_at(self, cell:Tuple[int,int]) -> Optional[Tower]:
        for t in self.towers:
            if (t.gx, t.gy) == cell: return t
        return None

    def try_place_tower(self, gx: int, gy: int, ttype: str):
        """Đặt tower, chỉ cho phép tại các tower slots được định sẵn."""
        # Lấy loadout hiện tại từ account
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            current_loadout = account.get("current_loadout", DEFAULT_LOADOUT)
        else:
            current_loadout = DEFAULT_LOADOUT
            
        # ✅ chặn thiếu/không có trong loadout
        if not ttype or ttype not in current_loadout:
            self.notice("Trụ này không có trong loadout của bạn.")
            return
        
        cell = (gx, gy)
        
        # Kiểm tra cell có phải tower slot hợp lệ không
        if cell not in self.tower_slots:
            self.notice("Không thể đặt trụ ở đây! Chỉ đặt được ở ô xanh.")
            return
            
        # đảm bảo self.occupied đã có (xem mục 4)
        if cell in self.path_cells or cell in self.occupied:
            return
            
        cost = TOWER_DEFS[ttype]["cost"]
        if self.money < cost:
            self.notice("Không đủ tiền!")
            return
            
        self.money -= cost; self.money_spent += cost
        spec = TOWER_DEFS[ttype]
        t = Tower(gx, gy, ttype=ttype,
                range=spec["range"], fire_rate=spec["firerate"], damage=spec.get("damage",20),
                splash=spec.get("splash",0.0), slow_mul=spec.get("slow",1.0), slow_time=spec.get("slow_time",0.0),
                poison_damage=spec.get("poison_damage",0.0), poison_time=spec.get("poison_time",0.0))  # Poison support
        self.towers.append(t); self.occupied.add(cell); self.towers_built += 1
        self.notice(f"Đã đặt {TOWER_DEFS[ttype]['name']}!")


    def try_remove_tower(self, gx: int, gy: int):
        cell = (gx, gy)
        for i, t in enumerate(self.towers):
            if (t.gx, t.gy) == cell:
                del self.towers[i]; self.occupied.discard(cell)
                back = int(TOWER_DEFS[t.ttype]["cost"] * SELL_REFUND_RATE)
                self.money += back; return

    def try_upgrade_tower(self, tower: Tower):
        if not tower.can_upgrade(): return
        cost = tower.upgrade_cost()
        if self.money >= cost:
            self.money -= cost; self.money_spent += cost; tower.apply_upgrade()

    # Powerups
    def buy_freeze(self):
        pu = POWERUPS["freeze"]
        if self.money < pu["cost"]:
            self.notice("Không đủ tiền cho Freeze"); return
        self.money -= pu["cost"]; self.powerups_used += 1
        for e in self.enemies:
            if e.alive: e.apply_slow(pu["slow"], pu["time"])
        self.notice("Đã kích hoạt Freeze!")

    def buy_airstrike(self):
        pu = POWERUPS["air"]
        if self.money < pu["cost"]:
            self.notice("Không đủ tiền cho Airstrike"); return
        self.money -= pu["cost"]; self.powerups_used += 1
        for e in self.enemies:
            if e.alive: e.hit(pu["damage"])
        self.notice("Airstrike!!!")

    def _handle_powerup_hover(self, mouse_pos):
        """Xử lý mouse hover cho powerup buttons"""
        mx, my = mouse_pos
        self.hovered_powerup = None  # Reset hover state
        
        for key, rect in self._powerup_rects().items():
            if rect.collidepoint((mx, my)):
                self.hovered_powerup = key
                break

    def _audio_control_click(self, mx, my):
        """Xử lý click vào nút điều khiển âm thanh."""
        panel_x = GAME_WIDTH + 5
        # Tính toán vị trí tương tự như trong _draw_audio_controls
        info_y = 25 + 160
        guide_y = info_y + 95
        audio_y = guide_y + 195
        
        rects = self._audio_control_rects(panel_x, audio_y)
        
        if rects["music"].collidepoint((mx, my)):
            self.toggle_music()
            return True
        elif rects["sfx"].collidepoint((mx, my)):
            self.toggle_sfx()
            return True
        return False
    
    def _powerup_click(self, mx,my):
        # Vô hiệu hóa powerup trong setup phase
        if self.in_setup_phase:
            for key, rect in self._powerup_rects().items():
                if rect.collidepoint((mx,my)):
                    self.notice("Powerup chỉ sử dụng được trong combat!", 2.0)
                    return True
            return False
            
        for key, rect in self._powerup_rects().items():
            if rect.collidepoint((mx,my)):
                # Phát âm thanh khi click powerup
                if hasattr(self, 'snd_shoot') and self.snd_shoot and self.save["settings"]["sfx"]:
                    self.snd_shoot.play()
                if key=="freeze": self.buy_freeze()
                else: self.buy_airstrike()
                return True
        return False

    def _hotbar_click(self, mx, my):
        # Lấy loadout hiện tại từ account
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            current_loadout = account.get("current_loadout", DEFAULT_LOADOUT)
        else:
            current_loadout = DEFAULT_LOADOUT
        
        for key, rect in self._hotbar_rects().items():
            if rect.collidepoint((mx, my)):
                self.selected_tower = key
                self.notice("Chọn trụ: " + TOWER_DEFS[key]["name"])
                return True
        return False


    def notice(self, text, time_sec=2.0):
        # hiển thị thông báo nhỏ góc phải
        self.notice_msg = text; self.notice_timer = time_sec

    # ------------------- UPDATE -------------------
    def update(self, dt: float):
        if self.scene != SCENE_GAME: return
        if self.notice_timer>0: self.notice_timer -= dt
        
        # Update animated gates (luôn chạy, kể cả khi pause)
        for gate in self.animated_gates:
            gate.update(dt)
            
        if self.paused or self.lives <= 0 or self.win_level: return

        self._shoot_snd_cooldown = max(0.0, self._shoot_snd_cooldown - dt)
        sdt = dt * self.speed_scale

        # Xử lý setup phase
        if self.in_setup_phase:
            old_time = self.setup_time
            self.setup_time -= dt
            
            # Đếm ngược âm thanh cho 3 giây cuối
            if self.setup_time <= 3 and old_time > 3:
                self.notice("! 3 seconds remaining! !", 1.5)
                # Phát âm thanh cảnh báo
                if self.snd_shoot and self.save["settings"]["sfx"]:
                    try: 
                        self.snd_shoot.set_volume(0.3)
                        self.snd_shoot.play()
                    except: pass
            elif self.setup_time <= 2 and old_time > 2:
                self.notice("! 2... !", 1.0)
                if self.snd_shoot and self.save["settings"]["sfx"]:
                    try: 
                        self.snd_shoot.set_volume(0.4)
                        self.snd_shoot.play()
                    except: pass
            elif self.setup_time <= 1 and old_time > 1:
                self.notice("! 1... !", 1.0)
                if self.snd_shoot and self.save["settings"]["sfx"]:
                    try: 
                        self.snd_shoot.set_volume(0.5)
                        self.snd_shoot.play()
                    except: pass
            
            if self.setup_time <= 0:
                self.in_setup_phase = False
                self.wave_mgr.start_next_wave()
                self.notice("⚔️ BATTLE BEGINS! ⚔️", 3.0)
            return  # Không spawn địch và không xử lý combat trong setup phase

        spawned = self.wave_mgr.update(sdt)
        self.enemies.extend(spawned)

        for e in self.enemies: e.update(sdt)

        for e in self.enemies:
            if e.alive and e.reached_end:
                e.alive = False
                
                # Nếu boss thoát thì thua ngay lập tức
                if e.etype == "boss":
                    self.lives = 0  # Game over ngay lập tức
                    self.game_over_reason = "boss_escaped"  # Lý do thua
                    self.notice(" BOSS ESCAPED! GAME OVER! ", 5.0)
                    print(" BOSS ESCAPED - IMMEDIATE GAME OVER!")
                else:
                    self.lives -= 1  # Enemy thường chỉ trừ 1 mạng
                    if self.lives <= 0:
                        self.game_over_reason = "no_lives"  # Lý do thua do hết mạng

        for t in self.towers:
            t.update(sdt); t.aim(self.enemies)
            prj = t.try_fire(self.enemies)
            if prj:
                self.projectiles.append(prj)
                if self.snd_shoot and self._shoot_snd_cooldown <= 0.0 and self.save["settings"]["sfx"]:
                    try: self.snd_shoot.play()
                    except Exception: pass
                    self._shoot_snd_cooldown = 0.06

        # Update projectiles và tạo damage text
        for p in self.projectiles:
            # Lưu target trước khi update
            old_target_alive = p.target and p.target.alive
            old_target_hp = p.target.hp if p.target else 0
            
            p.update(sdt, self.enemies)
            
            # Nếu projectile vừa hit target (không còn alive và target bị damage)
            if not p.alive and old_target_alive and p.target and p.target.hp < old_target_hp:
                # Tạo damage text tại vị trí target
                tx, ty = p.target.pos()
                actual_damage = int(old_target_hp - p.target.hp)
                damage_text = DamageText(tx, ty, actual_damage)
                self.damage_texts.append(damage_text)

        # Xử lý địch chết và tạo hiệu ứng
        for e in self.enemies:
            if not e.alive and e.hp <= 0 and e.reward > 0:
                self.money += e.reward; self.kills += 1; e.reward = 0
                # Tạo hiệu ứng chết tại vị trí địch
                ex, ey = e.pos()
                death_effect = DeathEffect(ex, ey, e.etype)
                self.death_effects.append(death_effect)
                
                # Boss tạo thêm nhiều hiệu ứng hơn
                if e.etype == "boss":
                    # Tạo thêm 2 hiệu ứng phụ xung quanh boss
                    for i in range(2):
                        offset_x = ex + random.uniform(-30, 30)
                        offset_y = ey + random.uniform(-30, 30)
                        extra_effect = DeathEffect(offset_x, offset_y, "boss")
                        extra_effect.max_duration = 1.2  # Ngắn hơn một chút
                        extra_effect.time_left = 1.2
                        self.death_effects.append(extra_effect)
                    
                    # Thông báo đặc biệt khi boss chết
                    self.notice("*** BOSS DEFEATED! ***", 3.0)
                
                # Phát âm thanh địch chết (với volume khác nhau theo loại)
                if self.snd_shoot and self.save["settings"]["sfx"]:
                    try:
                        # Tạo hiệu ứng âm thanh khác nhau cho từng loại địch
                        volume = 0.3  # Volume mặc định
                        if e.etype == "boss":
                            volume = 0.8  # Boss to hơn
                        elif e.etype == "tank":
                            volume = 0.6  # Tank trung bình
                        elif e.etype == "fast":
                            volume = 0.3  # Fast nhỏ hơn
                        
                        # Clone âm thanh và chỉnh volume
                        if self.save["settings"]["sfx"]:
                            original_vol = self.snd_shoot.get_volume()
                            self.snd_shoot.set_volume(volume)
                            self.snd_shoot.play()
                            self.snd_shoot.set_volume(original_vol)  # Khôi phục volume gốc
                    except Exception:
                        pass

        # Update hiệu ứng chết và damage text
        for effect in self.death_effects:
            effect.update(sdt)
            
        for damage_text in self.damage_texts:
            damage_text.update(sdt)

        # Loại bỏ các đối tượng đã chết/hết hạn
        self.enemies = [e for e in self.enemies if e.alive]
        self.projectiles = [p for p in self.projectiles if p.alive]
        self.death_effects = [effect for effect in self.death_effects if effect.alive]
        self.damage_texts = [text for text in self.damage_texts if text.alive]

        if (not self.wave_mgr.active) and self.wave_mgr.cooldown <= 0.0 and len(self.enemies) == 0:
            # For permanent map, never call handle_level_clear — waves are infinite
            if not getattr(self, 'is_permanent_map', False) and self.wave_mgr.wave_no >= self.max_waves:
                self.handle_level_clear(); return
            else:
                self.wave_mgr.start_next_wave()
                # Hiển thị boss warning
                if hasattr(self.wave_mgr, 'just_started_boss_wave') and self.wave_mgr.just_started_boss_wave:
                    self.notice("! BOSS WAVE! COMMANDER INCOMING! !", 4.0)
                    self.wave_mgr.just_started_boss_wave = False

    def handle_level_clear(self):
        self.win_level = True

        # STAR SYSTEM: Chấm sao theo performance (như cũ)
        max_lives = MODE_PARAMS[self.mode_name]["lives"]
        lives_lost = max_lives - self.lives
        
        # Công thức chấm sao: 3 sao nếu không mất mạng, giảm 1 sao mỗi mạng mất, tối thiểu 1 sao
        if self.lives <= 0:
            stars_earned = 1  # Nếu game over, chỉ được 1 sao
        else:
            stars_earned = max(1, 3 - lives_lost)
        
        # COIN SYSTEM: Mỗi màn hoàn thành được coin để mua súng
        coins_earned = 1  # Mỗi màn = 1 coin để mua súng
        
        # Lưu thông tin sao cho level này
        level_key = f"{self.mode_name}_L{self.level}"
        
        # cập nhật level_unlocked theo chế độ + sao theo nơi lưu tương ứng
        if self.current_user and self.current_user in self.accounts:
            acc = self.accounts[self.current_user]
            
            # Đảm bảo có cấu trúc mới
            if "level_unlocked_by_mode" not in acc:
                acc["level_unlocked_by_mode"] = {"Easy": 1, "Normal": 1, "Hard": 1}
            if "level_stars" not in acc:
                acc["level_stars"] = {}
            
            # Cập nhật theo chế độ hiện tại (skip nếu đang chơi permanent map)
            if not getattr(self, 'is_permanent_map', False):
                current_mode_level = acc["level_unlocked_by_mode"].get(self.mode_name, 1)
                is_new_level = self.level >= current_mode_level  # Kiểm tra có phải màn mới không
                if is_new_level:
                    acc["level_unlocked_by_mode"][self.mode_name] = self.level + 1
            else:
                # Khi chơi permanent map, không thay đổi progression
                current_mode_level = acc["level_unlocked_by_mode"].get(self.mode_name, 1)
                is_new_level = False
            
            # Cập nhật sao: mỗi lần hoàn thành màn được +1 star
            if level_key not in acc["level_stars"]:
                acc["level_stars"][level_key] = 0  # Đảm bảo key tồn tại
            
            # Cập nhật star: chỉ lưu star cao nhất cho level này
            current_stars = acc["level_stars"].get(level_key, 0)
            if stars_earned > current_stars:
                acc["level_stars"][level_key] = stars_earned
                # Cập nhật tổng sao
                total_stars = sum(acc["level_stars"].values())
                acc["stars"] = total_stars
                
            # Cộng coin: mỗi lần hoàn thành màn (kể cả replay) được coin
            acc["coins"] = acc.get("coins", 0) + coins_earned
                
            # Cập nhật level_unlocked chung để tương thích (lấy max của tất cả chế độ)
            if not getattr(self, 'is_permanent_map', False):
                max_level = max(acc["level_unlocked_by_mode"].values())
                acc["level_unlocked"] = max_level
            # Chỉ lưu leaderboard từ Permanent Map
            if getattr(self, 'is_permanent_map', False):
                wave_no = getattr(self, 'wave_mgr', None).wave_no if hasattr(self, 'wave_mgr') else 0
                # Công thức mới: chỉ kills và wave
                score = self.kills * 10 + wave_no * 500
                acc["leaderboard"] = acc.get("leaderboard", [])
                acc["leaderboard"].append({
                    "name": self.current_user, 
                    "level": self.level, 
                    "wave": getattr(self, 'wave_mgr', None).wave_no if hasattr(self, 'wave_mgr') else 0,
                    "score": int(score), 
                    "ts": int(time.time()),
                    "is_permanent": True
                })
                acc["leaderboard"] = sorted(acc["leaderboard"], key=lambda x: -x["score"])[:20]
            
            # Cập nhật thống kê tích lũy cho tài khoản
            acc["total_kills"] = acc.get("total_kills", 0) + self.kills
            acc["total_towers_built"] = acc.get("total_towers_built", 0) + self.towers_built
            acc["total_money_spent"] = acc.get("total_money_spent", 0) + self.money_spent
            acc["total_powerups_used"] = acc.get("total_powerups_used", 0) + self.powerups_used
            
            # ===== PROGRESSION SYSTEM: Chỉ unlock súng khi qua màn MỚI =====
            if is_new_level:
                self._unlock_next_tower(acc)
            
            save_accounts(self.accounts)
        else:
            # Đảm bảo có cấu trúc mới cho save
            if "level_unlocked_by_mode" not in self.save:
                self.save["level_unlocked_by_mode"] = {"Easy": 1, "Normal": 1, "Hard": 1}
            if "level_stars" not in self.save:
                self.save["level_stars"] = {}
            
            # Cập nhật theo chế độ hiện tại (skip nếu đang chơi permanent map)
            if not getattr(self, 'is_permanent_map', False):
                current_mode_level = self.save["level_unlocked_by_mode"].get(self.mode_name, 1)
                is_new_level = self.level >= current_mode_level  # Kiểm tra có phải màn mới không
                if is_new_level:
                    self.save["level_unlocked_by_mode"][self.mode_name] = self.level + 1
            else:
                current_mode_level = self.save["level_unlocked_by_mode"].get(self.mode_name, 1)
                is_new_level = False
            
            # Cập nhật sao: mỗi lần hoàn thành màn được +1 star
            if level_key not in self.save["level_stars"]:
                self.save["level_stars"][level_key] = 0  # Đảm bảo key tồn tại
            
            # Cập nhật star: chỉ lưu star cao nhất cho level này
            current_stars = self.save["level_stars"].get(level_key, 0)
            if stars_earned > current_stars:
                self.save["level_stars"][level_key] = stars_earned
                # Cập nhật tổng sao
                total_stars = sum(self.save["level_stars"].values())
                self.save["stars"] = total_stars
                
            # Cộng coin: mỗi lần hoàn thành màn (kể cả replay) được coin
            self.save["coins"] = self.save.get("coins", 0) + coins_earned
                
            # Cập nhật level_unlocked chung để tương thích
            if not getattr(self, 'is_permanent_map', False):
                max_level = max(self.save["level_unlocked_by_mode"].values())
                self.save["level_unlocked"] = max_level
            
            duration = max(1, int(time.time() - self.start_time))
            # Công thức tính điểm mới cho Permanent Map
            if getattr(self, 'is_permanent_map', False):
                wave_no = getattr(self, 'wave_mgr', None).wave_no if hasattr(self, 'wave_mgr') else 0
                score = self.kills * 10 + wave_no * 500
            else:
                score = self.kills*10 + self.lives*100 + self.money + self.level*500 - duration//2
            self.record_leaderboard(score)
            
            # ===== PROGRESSION SYSTEM: Chỉ unlock súng khi qua màn MỚI =====
            if is_new_level:
                self._unlock_next_tower(self.save)
            
            save_save(self.save)

    def _unlock_next_tower(self, data_storage):
        """
        Progression system: Mỗi lần hoàn thành màn sẽ unlock thêm 1 súng mới để có thể mua.
        Súng được unlock theo thứ tự giá từ thấp đến cao, nhưng phải dùng star để mua.
        """
        # Danh sách tất cả súng sắp xếp theo giá
        towers_by_price = sorted(ALL_TOWER_KEYS, key=lambda x: TOWER_DEFS[x]["cost"])
        
        # Lấy danh sách súng đã unlock để mua (không phải owned)
        available_for_purchase = set(data_storage.get("available_for_purchase", []))
        
        # Tìm súng tiếp theo chưa unlock để mua
        for tower_key in towers_by_price:
            if tower_key not in available_for_purchase:
                # Unlock súng mới này để có thể mua
                available_for_purchase.add(tower_key)
                data_storage["available_for_purchase"] = list(available_for_purchase)
                
                # Thông báo cho người chọi
                tower_name = TOWER_DEFS[tower_key]["name"]
                tower_cost = TOWER_DEFS[tower_key]["cost"]
                self.notice(f"CÓ THỂ MUA: {tower_name} - Cần 1 coin!", 4.0)
                break

    # ------------------- VẼ -------------------
    def draw(self):
        if self.scene == SCENE_MENU: self.draw_menu()
        elif self.scene == SCENE_GAME: self.draw_game()
        elif self.scene == SCENE_ALL_CLEAR: self.draw_all_clear()
        elif self.scene == SCENE_AUTH: self.draw_auth()
        elif self.scene == SCENE_LEVEL_SELECT: self.draw_level_select()
        elif self.scene == SCENE_STATS: self.draw_stats()
        elif self.scene == SCENE_SHOP: self.draw_shop()
        elif self.scene == SCENE_SETTINGS: self.draw_settings()
        elif self.scene == SCENE_MAP_PREVIEW: self.draw_map_preview()
        elif self.scene == SCENE_LEADER: self.draw_leader()
        elif self.scene == SCENE_NAME: self.draw_name()
        pygame.display.flip()

    def draw_menu(self):
        if self.bg_menu:
            self.screen.blit(self.bg_menu, (0, 0))
        else:
            self.screen.fill((25,25,30))
        
        # Thêm background cho menu
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            self.screen.blit(bg_img, (0, 0))
        except Exception:
            self.screen.fill((25,25,30))
        
        # Bỏ title để không che logo trong background
        
        for b in self.menu_buttons: b.draw(self.screen, self.font)
        
        # Thông tin gọn gàng ở góc dưới
        if self.current_user:
            account = self.accounts.get(self.current_user, {})
            stars = account.get("stars", 0)
            
            # Hiển thị stars
            stars_text = f"{stars} Stars"
            stars_surf = self._get_font(18).render(stars_text, True, (255, 215, 0))
            self.screen.blit(stars_surf, (WIDTH - 100, HEIGHT - 30))
        else:
            # Khi chưa đăng nhập, hiển thị tip
            tip_text = "Đăng nhập để lưu tiến độ"
            tip_surf = self._get_font(16).render(tip_text, True, (180, 180, 180))
            tip_rect = tip_surf.get_rect(center=(WIDTH//2, HEIGHT - 30))
            self.screen.blit(tip_surf, tip_rect)


    def draw_maps(self):
        self.screen.fill((20,24,28))
        self.screen.blit(self.bigfont.render("Chọn bản đồ (nhấp)", True, ORANGE), (40, 40))
        for i in range(len(MAPS)):
            col=i%2; row=i//2
            rx = 160 + col*300; ry = 180 + row*160
            rect = pygame.Rect(rx, ry, 220, 120)
            pygame.draw.rect(self.screen, (60,60,90), rect, border_radius=10)
            txt = f"Map {i+1}" + ("  (đang chọn)" if i==self.selected_map_idx else "")
            self.screen.blit(self.medfont.render(txt, True, WHITE), (rx+20, ry+45))
        self.screen.blit(self.font.render("ESC: về menu", True, WHITE), (20, HEIGHT-30))

    def draw_shop(self):
        """Cửa hàng mở khóa trụ và chọn loadout."""
        self.screen.fill((25, 35, 45))
        
        # Background với overlay
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(bg_img, (0, 0))
            self.screen.blit(overlay, (0, 0))
        except Exception:
            pass

        # Tiêu đề
        title = self.bigfont.render(" CỬA HÀNG THÁP", True, ORANGE)
        title_rect = title.get_rect(center=(WIDTH//2, 40))
        shadow = self.bigfont.render(" CỬA HÀNG THÁP", True, BLACK)
        self.screen.blit(shadow, title_rect.move(2, 2))
        self.screen.blit(title, title_rect)

        # Lấy dữ liệu người chơi
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            owned = set(account.get("unlocked_towers", DEFAULT_LOADOUT.copy()))  # Súng đã sở hữu
            available = set(account.get("available_for_purchase", DEFAULT_LOADOUT.copy()))  # Súng có thể mua
            current_loadout = account.get("current_loadout", DEFAULT_LOADOUT.copy())
            stars = account.get("stars", 0)
            coins = account.get("coins", 0)
        else:
            owned = set(self.save.get("unlocked_towers", DEFAULT_LOADOUT.copy()))
            available = set(self.save.get("available_for_purchase", DEFAULT_LOADOUT.copy()))
            current_loadout = self.save.get("current_loadout", DEFAULT_LOADOUT.copy())
            stars = self.save.get("stars", 0)
            coins = self.save.get("coins", 0)

        # Panel thông tin - dời sang phải và điều chỉnh width vừa đủ
        info_bg = pygame.Rect(200, 80, 800, 60)  # Width cố định 800px thay vì WIDTH-250 để vừa với text
        pygame.draw.rect(self.screen, (40, 50, 60), info_bg, border_radius=10)
        pygame.draw.rect(self.screen, (80, 100, 120), info_bg, width=2, border_radius=10)
        
        # Text gọn hơn với font nhỏ hơn để vừa khung
        compact_font = self._get_font(18)
        info_text = f"Sao: {stars}  |  Coin: {coins}  |  Trang bị: {len(current_loadout)}/4  |  Sở hữu: {len(owned)}/{len(ALL_TOWER_KEYS)}"
        info_surf = compact_font.render(info_text, True, WHITE)
        self.screen.blit(info_surf, (210, 90))
        
        guide_font = self._get_font(16)
        guide_text = "Nhấn 'MUA' để mở khóa (1 Coin) | Nhấn tháp để thêm/bớt trang bị | ESC: Quay lại"
        guide_surf = guide_font.render(guide_text, True, (180, 180, 180))
        self.screen.blit(guide_surf, (210, 110))

        # Hiển thị current loadout - dời sang phải để cân đối
        loadout_y = 140  # Giảm từ 160 xuống 140 để tạo thêm không gian
        loadout_title = self._get_font(24, bold=True).render("TRANG BỊ HIỆN TẠI (mang vào trận):", True, YELLOW)
        self.screen.blit(loadout_title, (200, loadout_y))
        
        # Vẽ 4 slot loadout với kích thước rộng hơn để dễ nhìn
        slot_size = 120
        slot_spacing = 140
        start_x = 180  # Điều chỉnh vị trí để fit 4 slots rộng hơn
        for i in range(4):
            slot_x = start_x + i * slot_spacing
            slot_y = loadout_y + 30
            slot_rect = pygame.Rect(slot_x, slot_y, slot_size, slot_size)
            
            if i < len(current_loadout):
                tower_key = current_loadout[i]
                tower_info = TOWER_DEFS[tower_key]
                
                # Background cho slot có tháp
                pygame.draw.rect(self.screen, (60, 120, 80), slot_rect, border_radius=8)
                pygame.draw.rect(self.screen, (100, 200, 120), slot_rect, width=3, border_radius=8)
                
                # Hiển thị ảnh tháp
                if tower_key in self.tower_sprites:
                    sprite = self.tower_sprites[tower_key]
                    # Scale sprite lớn hơn cho slot rộng (khoảng 90x90)
                    sprite_size = 90
                    scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                    sprite_rect = scaled_sprite.get_rect(center=(slot_rect.centerx, slot_rect.centery - 10))
                    self.screen.blit(scaled_sprite, sprite_rect)
                
                # Tên tháp (ở dưới ảnh, font lớn hơn cho dễ đọc)
                name_font = self._get_font(18)
                name_surf = name_font.render(tower_info["name"], True, WHITE)
                name_rect = name_surf.get_rect(center=(slot_rect.centerx, slot_rect.bottom - 15))
                self.screen.blit(name_surf, name_rect)
            else:
                # Slot trống
                pygame.draw.rect(self.screen, (40, 40, 50), slot_rect, border_radius=8)
                pygame.draw.rect(self.screen, (80, 80, 90), slot_rect, width=2, border_radius=8)
                
                empty_font = self._get_font(20)
                empty_text = empty_font.render("Trống", True, (120, 120, 120))
                empty_rect = empty_text.get_rect(center=slot_rect.center)
                self.screen.blit(empty_text, empty_rect)

        # Hiển thị tất cả tháp có thể mua/chọn - kéo lên cao để không bị khuất
        towers_y = loadout_y + 170  # Tăng thêm từ 140 lên 170 để tạo khoảng cách lớn hơn
        towers_title = self._get_font(24, bold=True).render("CỬA HÀNG THÁP (sắp xếp theo giá):", True, YELLOW)
        self.screen.blit(towers_title, (200, towers_y))
        
        # Sắp xếp tower theo giá tiền từ thấp đến cao
        sorted_towers = sorted(ALL_TOWER_KEYS, key=lambda x: TOWER_DEFS[x]["cost"])
        
        # Grid layout cho tháp (4 cột) - dời sang phải để tránh nút "Về Menu"
        cols = 4
        rows = (len(sorted_towers) + cols - 1) // cols
        card_width = 220
        card_height = 100  # Giảm thêm từ 110 xuống 100 để tiết kiệm không gian
        grid_start_x = 200  # Dời từ 50 sang 200 (thêm 150px)
        grid_start_y = towers_y + 40  # Tăng từ 25 lên 40 để tạo khoảng cách với title
        
        self._shop_rects = {}  # Reset click areas
        
        for i, tower_key in enumerate(sorted_towers):
            row = i // cols
            col = i % cols
            x = grid_start_x + col * (card_width + 20)
            y = grid_start_y + row * (card_height + 15)
            
            tower_info = TOWER_DEFS[tower_key]
            is_owned = tower_key in owned  # Đã sở hữu
            is_available = tower_key in available  # Có thể mua
            is_in_loadout = tower_key in current_loadout
            
            # Card background với logic mới
            card_rect = pygame.Rect(x, y, card_width, card_height)
            if is_in_loadout:
                bg_color = (60, 120, 60)  # Xanh lá nếu trong loadout
                border_color = (100, 200, 100)
            elif is_owned:
                bg_color = (60, 80, 120)  # Xanh dương nếu đã sở hữu
                border_color = (100, 140, 200)
            elif is_available:
                bg_color = (100, 80, 20)  # Vàng nâu nếu có thể mua
                border_color = (160, 130, 40)
            else:
                bg_color = (50, 50, 60)   # Xám nếu chưa unlock
                border_color = (80, 80, 100)
                
            pygame.draw.rect(self.screen, bg_color, card_rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, card_rect, width=2, border_radius=10)
            
            # Tên tháp với font đẹp hơn
            title_font = self._get_font(18, bold=True)
            name_surf = title_font.render(tower_info["name"], True, YELLOW if is_in_loadout else WHITE)
            self.screen.blit(name_surf, (x + 8, y + 8))
            
            # Ảnh tháp (nếu có)
            tower_img = self._load_tower_image(tower_key)
            if tower_img:
                # Scale ảnh xuống 48x48px để vừa với card
                img_size = 48
                tower_img = pygame.transform.smoothscale(tower_img, (img_size, img_size))
                
                # Vị trí ảnh (góc phải trên của card)
                img_x = x + card_width - img_size - 8
                img_y = y + 8
                
                # Làm mờ nếu chưa mở khóa
                if not is_owned:
                    gray_overlay = pygame.Surface((img_size, img_size), pygame.SRCALPHA)
                    gray_overlay.fill((0, 0, 0, 120))
                    tower_img.blit(gray_overlay, (0, 0))
                
                # Vẽ ảnh tháp
                self.screen.blit(tower_img, (img_x, img_y))
                
                # Border cho ảnh
                border_rect = pygame.Rect(img_x - 1, img_y - 1, img_size + 2, img_size + 2)
                img_border_color = border_color
                pygame.draw.rect(self.screen, img_border_color, border_rect, width=1, border_radius=4)
            
            # Stats với font gọn và màu sắc đẹp
            stats_font = self._get_font(16)
            cost_color = (255, 215, 0)  # Gold cho giá
            damage_color = (255, 100, 100)  # Đỏ cho damage  
            range_color = (100, 200, 255)   # Xanh cho range
            
            stats_lines = [
                (f"${tower_info['cost']}", cost_color),
                (f"Sát thương: {tower_info['damage']}", damage_color),
                (f"Tầm bắn: {tower_info['range']//TILE} ô", range_color)
            ]
            
            for j, (line_text, line_color) in enumerate(stats_lines):
                line_surf = stats_font.render(line_text, True, line_color if is_owned else (120, 120, 120))
                self.screen.blit(line_surf, (x + 8, y + 35 + j * 16))
            
            # Nút hành động với font đẹp hơn
            action_font = self._get_font(14, bold=True)
            
            if not is_owned and is_available:
                # Nút MUA (chỉ hiện khi có thể mua)
                buy_rect = pygame.Rect(x + card_width - 85, y + card_height - 28, 75, 22)
                if coins >= 1:
                    pygame.draw.rect(self.screen, (220, 80, 80), buy_rect, border_radius=6)
                    pygame.draw.rect(self.screen, (255, 120, 120), buy_rect, width=1, border_radius=6)
                    buy_text = action_font.render("MUA (1 Coin)", True, WHITE)
                else:
                    pygame.draw.rect(self.screen, (80, 80, 80), buy_rect, border_radius=6)
                    pygame.draw.rect(self.screen, (120, 120, 120), buy_rect, width=1, border_radius=6)
                    buy_text = action_font.render("Thiếu Coin", True, (160, 160, 160))
                    
                buy_rect_center = buy_text.get_rect(center=buy_rect.center)
                self.screen.blit(buy_text, buy_rect_center)
                self._shop_rects[f"buy_{tower_key}"] = buy_rect
            elif not is_owned and not is_available:
                # Chưa unlock để mua
                status_font = self._get_font(14)
                status_text = "Chưa mở khóa"
                status_surf = status_font.render(status_text, True, (120, 120, 120))
                self.screen.blit(status_surf, (x + 8, y + card_height - 22))
            else:
                # Hiển thị trạng thái với màu sắc đẹp
                status_font = self._get_font(15, bold=True)
                if is_in_loadout:
                    status_text = "ĐANG DÙNG"
                    status_color = (80, 220, 80)
                else:
                    status_text = "Nhấn để thêm"
                    status_color = (200, 200, 100)
                    
                status_surf = status_font.render(status_text, True, status_color)
                self.screen.blit(status_surf, (x + 8, y + card_height - 22))
                
            # Click area cho toàn bộ card (nếu đã mở)
            if is_owned:
                self._shop_rects[f"select_{tower_key}"] = card_rect
        
        # Nút quay lại
        back_btn = pygame.Rect(50, HEIGHT - 70, 120, 40)
        back_hover = back_btn.collidepoint(pygame.mouse.get_pos())
        back_color = (150, 100, 100) if back_hover else (120, 80, 80)
        
        pygame.draw.rect(self.screen, back_color, back_btn, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, back_btn, width=2, border_radius=10)
        
        back_font = self._get_font(20, bold=True)
        back_text = back_font.render("VỀ MENU", True, WHITE)
        back_text_rect = back_text.get_rect(center=back_btn.center)
        self.screen.blit(back_text, back_text_rect)
        
        self._shop_rects["_back"] = back_btn
    
    def _handle_buy_tower(self, tower_key):
        """Xử lý mua tower bằng coin"""
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            coins = account.get("coins", 0)
            owned = set(account.get("unlocked_towers", DEFAULT_LOADOUT.copy()))  # Súng đã sở hữu
            available = set(account.get("available_for_purchase", DEFAULT_LOADOUT.copy()))  # Có thể mua
            
            if tower_key not in owned and tower_key in available and coins >= 1:
                # Mua tower thành công
                owned.add(tower_key)
                account["unlocked_towers"] = list(owned)
                account["coins"] = coins - 1
                save_accounts(self.accounts)
                tower_name = TOWER_DEFS[tower_key]['name']
                self.notice(f"✅ Đã mua {tower_name}! Còn lại {coins-1} coin")
            elif tower_key in owned:
                self.notice("Bạn đã sở hữu tháp này rồi!")
            elif tower_key not in available:
                self.notice("❌ Tháp này chưa mở khóa để mua!")
            else:
                self.notice("❌ Không đủ coin để mua! (Cần 1 coin)")
        else:
            # Xử lý cho save file (không đăng nhập)
            coins = self.save.get("coins", 0) 
            owned = set(self.save.get("unlocked_towers", DEFAULT_LOADOUT.copy()))
            available = set(self.save.get("available_for_purchase", DEFAULT_LOADOUT.copy()))
            
            if tower_key not in owned and tower_key in available and coins >= 1:
                owned.add(tower_key)
                self.save["unlocked_towers"] = list(owned)
                self.save["coins"] = coins - 1
                save_save(self.save)
                tower_name = TOWER_DEFS[tower_key]['name']
                self.notice(f"✅ Đã mua {tower_name}! Còn lại {coins-1} coin")
            elif tower_key in owned:
                self.notice("Bạn đã sở hữu tháp này rồi!")
            elif tower_key not in available:
                self.notice("❌ Tháp này chưa mở khóa để mua!")
            else:
                self.notice("❌ Không đủ coin để mua! (Cần 1 coin)")
    
    def _handle_select_tower(self, tower_key):
        """Xử lý chọn tower cho loadout"""
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            owned = set(account.get("unlocked_towers", DEFAULT_LOADOUT.copy()))  # Súng đã sở hữu
            current_loadout = account.get("current_loadout", DEFAULT_LOADOUT.copy())
            
            if tower_key not in owned:
                self.notice("❌ Chưa sở hữu tháp này! Hãy mua bằng sao trước.")
                return
                
            if tower_key in current_loadout:
                # Bỏ tower khỏi loadout
                current_loadout.remove(tower_key)
                self.notice(f"➖ Đã bỏ {TOWER_DEFS[tower_key]['name']} khỏi loadout")
            else:
                # Thêm tower vào loadout
                if len(current_loadout) < 4:
                    current_loadout.append(tower_key)
                    self.notice(f"➕ Đã thêm {TOWER_DEFS[tower_key]['name']} vào loadout")
                else:
                    self.notice("! Loadout đã đầy! Bỏ tháp khác trước.")
                    return
                    
            account["current_loadout"] = current_loadout
            save_accounts(self.accounts)
        else:
            self.notice("❌ Cần đăng nhập để chọn loadout!")
    
    def _load_tower_image(self, tower_key):
        """Load ảnh tháp theo thứ tự ưu tiên"""
        # Mapping tên file ảnh cho từng tháp
        tower_image_files = {
            "gun": "tower_lv1.png",
            "sniper": "tower_lv2.png", 
            "splash": "tower_lv3.png",
            "slow": "tower_lv4.png",
            "laser": "tower_laser.png",
            "rocket": "tower_rocket.png",
            "electric": "tower_electric.png",
            "poison": "tower_poison.png",
            "minigun": "tower_minigun.png",
            "mortar": "tower_mortar.png",
            "ice": "tower_ice.png",
            "flame": "tower_flame.png"
        }
        
        # Thứ tự tìm ảnh:
        # 1. Ảnh chuyên dụng cho tháp
        # 2. Ảnh từ thư mục towers/ (nếu có)
        # 3. Ảnh fallback
        
        tower_file = tower_image_files.get(tower_key, "tower_lv1.png")
        
        # Thử load ảnh chính từ assets/
        try:
            tower_path = os.path.join(ASSETS_DIR, tower_file)
            if os.path.exists(tower_path):
                return pygame.image.load(tower_path).convert_alpha()
        except Exception:
            pass
            
        # Thử load từ thư mục towers/ (nếu có)
        try:
            # Xác định category của tháp
            categories = {
                "gun": "basic", "sniper": "basic", "splash": "basic", "slow": "basic",
                "laser": "energy", "electric": "energy",
                "rocket": "explosive", "mortar": "explosive", 
                "minigun": "special", "poison": "special", "ice": "special", "flame": "special"
            }
            category = categories.get(tower_key, "basic")
            tower_path = os.path.join(ASSETS_DIR, "towers", category, f"{tower_key}.png")
            if os.path.exists(tower_path):
                return pygame.image.load(tower_path).convert_alpha()
        except Exception:
            pass
            
        # Fallback - thử load từ assets/tiles/
        try:
            tower_path = os.path.join(ASSETS_DIR, "tiles", tower_file)
            if os.path.exists(tower_path):
                return pygame.image.load(tower_path).convert_alpha()
        except Exception:
            pass
            
        return None

    def draw_settings(self):
        """Vẽ màn hình cài đặt âm thanh."""
        # Background
        if hasattr(self, "bg_menu") and self.bg_menu:
            self.screen.blit(self.bg_menu, (0, 0))
        else:
            self.screen.fill((25, 25, 35))
        
        # Overlay tối để text dễ đọc
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # Tiêu đề chính
        title = self.bigfont.render("CÀI ĐẶT ÂM THANH", True, YELLOW)
        title_x = (WIDTH - title.get_width()) // 2
        self.screen.blit(title, (title_x, 100))
        
        # Vẽ các nút settings
        button_font = self._get_font(18, bold=True)
        for button in self.settings_buttons:
            button.draw(self.screen, button_font)
        
        # Hướng dẫn
        hint_text = "ESC: Trở về menu"
        hint = self.font.render(hint_text, True, WHITE)
        hint_x = (WIDTH - hint.get_width()) // 2
        self.screen.blit(hint, (hint_x, HEIGHT - 50))

    def draw_stats(self):
        """Vẽ bảng thành tựu với thiết kế đẹp như bảng xếp hạng."""
        # [ART] GRADIENT BACKGROUND SIÊU ĐẸP
        self._draw_gradient_background((15, 25, 45), (45, 65, 85), vertical=True)
        
        # Background image với hiệu ứng blur (nếu có)
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert_alpha()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            
            # Tạo hiệu ứng blur bằng alpha blending
            blur_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            blur_surf.fill((20, 30, 50, 180))  # Overlay màu xanh đậm với alpha
            
            self.screen.blit(bg_img, (0, 0))
            self.screen.blit(blur_surf, (0, 0))
        except:
            # Nếu không có background image, dùng gradient
            pass
        
        # TITLE với gradient text effect - KHÔNG CÓ NỀN
        title_text = "BẢNG THÀNH TỰU"
        title_surf = self.bigfont.render(title_text, True, (255, 215, 0))  # Gold color
        title_rect = title_surf.get_rect()
        title_rect.centerx = WIDTH // 2
        title_rect.y = 55
        
        # Title glow effect
        glow_surf = self.bigfont.render(title_text, True, (255, 255, 200))
        for glow_offset in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            glow_rect = title_rect.move(glow_offset[0], glow_offset[1])
            self.screen.blit(glow_surf, glow_rect)
        
        self.screen.blit(title_surf, title_rect)
        
        # # Subtitle với hiệu ứng
        # subtitle_text = "Theo dõi tiến trình và thành tích của bạn"
        # subtitle_surf = self.font.render(subtitle_text, True, (200, 200, 255))
        # subtitle_rect = subtitle_surf.get_rect()
        # subtitle_rect.centerx = WIDTH // 2
        # subtitle_rect.y = 100
        # self.screen.blit(subtitle_surf, subtitle_rect)
        
        # Tính toán các thống kê tổng hợp theo tài khoản hiện tại
        current_mode = MODES[self.menu_mode_idx]
        
        if self.current_user and self.current_user in self.accounts:
            # Lấy dữ liệu từ tài khoản đang đăng nhập
            user_data = self.accounts[self.current_user]
            level_by_mode = user_data.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            max_level_unlocked = level_by_mode.get(current_mode, 1)
            user_leaderboard = user_data.get("leaderboard", [])
            total_score = sum(entry.get("score", 0) for entry in user_leaderboard)
            total_games = len(user_leaderboard)
            avg_score = total_score // max(1, total_games)
            
            # Thống kê tích lũy từ tài khoản
            total_kills = user_data.get("total_kills", 0)
            total_towers_built = user_data.get("total_towers_built", 0)
            total_money_spent = user_data.get("total_money_spent", 0)
            total_powerups_used = user_data.get("total_powerups_used", 0)
        else:
            # Fallback nếu chưa đăng nhập - dùng save cũ
            level_by_mode = self.save.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            max_level_unlocked = level_by_mode.get(current_mode, 1)
            total_score = sum(entry.get("score", 0) for entry in self.save.get("leaderboard", []))
            total_games = len(self.save.get("leaderboard", []))
            avg_score = total_score // max(1, total_games)
            total_kills = 0
            total_towers_built = 0
            total_money_spent = 0
            total_powerups_used = 0
        
        # Tính toán số tháp sở hữu - kết hợp từ unlocked_towers và current_loadout
        if self.current_user and self.current_user in self.accounts:
            user_data = self.accounts[self.current_user]
            unlocked_towers = user_data.get("unlocked_towers", [])
            current_loadout = user_data.get("current_loadout", [])
            
            # Kết hợp tất cả tháp từ cả hai nguồn
            all_towers = set(unlocked_towers) | set(current_loadout)
            # Chỉ đếm các tháp hợp lệ có trong ALL_TOWER_KEYS
            valid_towers = [t for t in all_towers if t in ALL_TOWER_KEYS]
            towers_owned = len(valid_towers)
            towers_in_loadout = len([t for t in current_loadout if t in ALL_TOWER_KEYS])
        else:
            unlocked_towers = self.save.get("unlocked_towers", [])
            # Chỉ đếm các tháp hợp lệ có trong ALL_TOWER_KEYS  
            valid_towers = [t for t in set(unlocked_towers) if t in ALL_TOWER_KEYS]
            towers_owned = len(valid_towers)
            towers_in_loadout = len(getattr(self, 'unlocked_towers', DEFAULT_LOADOUT))
            
        # COMPACT STATS LAYOUT với card-style entries
        stats_start_y = 160
        card_height = 35  # Giảm từ 45 xuống 35
        card_margin = 6   # Giảm từ 8 xuống 6
        card_width = 580  # Giảm từ 650 xuống 580
        card_start_x = (WIDTH - card_width) // 2
        
        # Tạo danh sách thống kê chính
        main_stats = [
            ("Số địch đã hạ", f"{total_kills:,}", (255, 100, 100)),
            ("Số tháp sở hữu", f"{towers_owned}/12", (100, 255, 100)),
            ("Điểm tích lũy", f"{total_score:,}", (255, 215, 0)),
            ("Số màn vượt qua", f"{max_level_unlocked - 1}", (100, 200, 255)),
            ("Số lần chơi", f"{total_games}", (255, 150, 255))
        ]
        
        # Vẽ từng stat card
        for i, (label, value, accent_color) in enumerate(main_stats):
            y_pos = stats_start_y + i * (card_height + card_margin)
            
            # [CARD] Tạo card cho mỗi stat - căn giữa
            card_rect = pygame.Rect(card_start_x, y_pos, card_width, card_height)
            
            # Card background với gradient
            self._draw_gradient_rect(card_rect, (255, 255, 255, 40), (255, 255, 255, 20))
            
            # Accent border trái
            accent_rect = pygame.Rect(card_start_x, y_pos, 4, card_height)
            pygame.draw.rect(self.screen, accent_color, accent_rect)
            
            # Label (trái) - MÀU ĐEN
            label_surf = self.font.render(label, True, (0, 0, 0))  # Đổi thành màu đen
            label_rect = label_surf.get_rect()
            label_rect.x = card_start_x + 20
            label_rect.centery = y_pos + card_height // 2
            self.screen.blit(label_surf, label_rect)
            
            # Value (phải) 
            value_surf = self.medfont.render(value, True, accent_color)
            value_rect = value_surf.get_rect()
            value_rect.right = card_start_x + card_width - 20
            value_rect.centery = y_pos + card_height // 2
            self.screen.blit(value_surf, value_rect)
        
        # ACHIEVEMENTS SECTION - nhỏ gọn hơn
        achievements_start_y = stats_start_y + len(main_stats) * (card_height + card_margin) + 25
        
        # Section title - FONT TIẾNG VIỆT CHUẨN
        achieve_title = "THÀNH TỰU ĐẶC BIỆT"
        
        # Dùng font tiếng Việt tốt cho title
        try:
            title_font = pygame.font.SysFont('tahoma', 24, bold=True)  # Tahoma hỗ trợ tiếng Việt tốt
        except:
            try:
                title_font = pygame.font.SysFont('arial', 24, bold=True)
            except:
                title_font = self.medfont
        
        achieve_title_surf = title_font.render(achieve_title, True, (255, 215, 0))
        achieve_title_rect = achieve_title_surf.get_rect()
        achieve_title_rect.centerx = WIDTH // 2
        achieve_title_rect.y = achievements_start_y
        
        # Title glow nhẹ với CÙNG FONT để không bị đè
        glow_surf = title_font.render(achieve_title, True, (255, 255, 200))
        for glow_offset in [(-1, -1), (1, 1), (-1, 1), (1, -1)]:  # Glow chéo để đẹp hơn
            glow_rect = achieve_title_rect.move(glow_offset[0], glow_offset[1])
            self.screen.blit(glow_surf, glow_rect)
        
        self.screen.blit(achieve_title_surf, achieve_title_rect)
        
        # Achievement cards - GỌN GÀNG để không đè nút
        achievements = self._get_achievements()[:4]  # Giới hạn 4 thành tựu
        achieve_card_start_y = achievements_start_y + 35
        achieve_card_height = 40  # Giảm từ 55 xuống 40 để gọn hơn
        achieve_card_width = 650  # Giảm từ 750 xuống 650 để nhỏ hơn
        achieve_card_start_x = (WIDTH - achieve_card_width) // 2
        
        for i, achievement in enumerate(achievements):
            y_pos = achieve_card_start_y + i * (achieve_card_height + 8)  # Giảm spacing từ 15 xuống 8 để gọn
            
            # Achievement card
            card_rect = pygame.Rect(achieve_card_start_x, y_pos, achieve_card_width, achieve_card_height)
            
            # Xác định màu và icon dựa trên trạng thái thành tựu
            if "Master" in achievement:
                accent_color = (255, 215, 0)  # Gold
                bg_color = (255, 215, 0, 60)
                icon = "★"
                icon_color = (255, 255, 100)
            elif "Expert" in achievement:
                accent_color = (192, 192, 192)  # Silver  
                bg_color = (192, 192, 192, 50)
                icon = "◆"
                icon_color = (220, 220, 255)
            elif "Advanced" in achievement:
                accent_color = (205, 127, 50)  # Bronze
                bg_color = (205, 127, 50, 45)
                icon = "●"
                icon_color = (255, 180, 120)
            elif "Beginner" in achievement:
                accent_color = (100, 200, 100)  # Green
                bg_color = (100, 200, 100, 40)
                icon = "▲"
                icon_color = (150, 255, 150)
            else:
                accent_color = (150, 150, 150)  # Gray
                bg_color = (150, 150, 150, 30)
                icon = "○"
                icon_color = (180, 180, 180)
            
            # Card background đặc - đẹp như trong ảnh
            if "Master" in achievement:
                card_bg_color = (255, 215, 0)  # Vàng đặc cho Master
            elif "Expert" in achievement:
                card_bg_color = (192, 192, 192)  # Xám bạc cho Expert
            elif "Advanced" in achievement:
                card_bg_color = (205, 127, 50)  # Nâu đồng cho Advanced  
            elif "Beginner" in achievement:
                card_bg_color = (100, 200, 100)  # Xanh lá cho Beginner
            else:
                card_bg_color = (150, 150, 150)  # Xám cho chưa đạt
            
            # Vẽ background đặc
            pygame.draw.rect(self.screen, card_bg_color, card_rect, border_radius=8)
            
            # Border màu đậm hơn
            border_color = tuple(int(c * 0.7) for c in card_bg_color)
            pygame.draw.rect(self.screen, border_color, card_rect, width=2, border_radius=8)
            
            # Achievement text màu đen, dễ đọc - KHÔNG CÓ ICON
            try:
                achieve_font = pygame.font.SysFont('tahoma', 16, bold=True)  # Tăng từ 14 lên 16 vì không có icon
            except:
                try:
                    achieve_font = pygame.font.SysFont('arial', 16, bold=True)  # Arial fallback
                except:
                    achieve_font = pygame.font.Font(None, 20)
                
            achieve_surf = achieve_font.render(achievement, True, (0, 0, 0))  # Màu đen
            achieve_rect = achieve_surf.get_rect()
            achieve_rect.x = achieve_card_start_x + 20  # Giảm từ 45 xuống 20 vì không có icon
            achieve_rect.centery = y_pos + achieve_card_height // 2
            self.screen.blit(achieve_surf, achieve_rect)
        
        # COMPACT BACK BUTTON - giống như bảng xếp hạng
        back_button_rect = pygame.Rect(WIDTH//2 - 75, HEIGHT - 80, 150, 50)
        mx, my = pygame.mouse.get_pos()
        is_back_hovered = back_button_rect.collidepoint((mx, my))
        
        # Back button animation giống bảng xếp hạng
        if is_back_hovered:
            button_scale = 1.05
            back_colors = [(180, 60, 60), (220, 100, 100)]
            border_color = (255, 150, 100)
        else:
            button_scale = 1.0
            back_colors = [(120, 40, 40), (160, 70, 70)]
            border_color = (200, 100, 100)
        
        # Scaled button
        scaled_back_size = (int(back_button_rect.width * button_scale), int(back_button_rect.height * button_scale))
        scaled_back_rect = pygame.Rect(
            back_button_rect.x + (back_button_rect.width - scaled_back_size[0]) // 2,
            back_button_rect.y + (back_button_rect.height - scaled_back_size[1]) // 2,
            *scaled_back_size
        )
        
        # Button shadow
        shadow_rect = scaled_back_rect.move(2, 2)
        shadow_surf = pygame.Surface(scaled_back_size, pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 100))
        self.screen.blit(shadow_surf, shadow_rect)
        
        # Gradient button
        self._draw_gradient_rect(scaled_back_rect, back_colors[0], back_colors[1], 10)
        
        # Button border
        pygame.draw.rect(self.screen, border_color, scaled_back_rect, width=2, border_radius=10)
        
        # Button text với shadow
        back_font = self._get_font(16, bold=True)
        back_text = "Trở về Menu"
        text_shadow = back_font.render(back_text, True, (0, 0, 0))
        text_main = back_font.render(back_text, True, WHITE)
        
        text_rect = text_main.get_rect(center=scaled_back_rect.center)
        shadow_rect = text_rect.move(1, 1)
        
        self.screen.blit(text_shadow, shadow_rect)
        self.screen.blit(text_main, text_rect)
        

            
    def _get_achievements(self):
        """Tính toán và trả về danh sách thành tựu."""
        achievements = []
        
        # Lấy thống kê từ tài khoản
        if self.current_user and self.current_user in self.accounts:
            user_data = self.accounts[self.current_user]
            total_kills = user_data.get("total_kills", 0)
            total_towers_built = user_data.get("total_towers_built", 0)
            total_games = len(user_data.get("leaderboard", []))
            max_level = max(user_data.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1}).values())
        else:
            total_kills = 0
            total_towers_built = 0
            total_games = len(self.save.get("leaderboard", []))
            max_level = max(self.save.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1}).values())
        
        # Thành tựu tiêu diệt địch
        if total_kills >= 2500:
            achievements.append("Diệt địch: Master (2500+)")
        elif total_kills >= 1000:
            achievements.append("Diệt địch: Expert (1000+)")
        elif total_kills >= 500:
            achievements.append("Diệt địch: Advanced (500+)")
        elif total_kills >= 100:
            achievements.append("Diệt địch: Beginner (100+)")
        else:
            achievements.append(f"Diệt địch: {total_kills}/100")
            
        # Thành tựu xây tháp
        if total_towers_built >= 500:
            achievements.append("Xây tháp: Master (500+)")
        elif total_towers_built >= 200:
            achievements.append("Xây tháp: Expert (200+)")
        elif total_towers_built >= 50:
            achievements.append("Xây tháp: Advanced (50+)")
        elif total_towers_built >= 10:
            achievements.append("Xây tháp: Beginner (10+)")
        else:
            achievements.append(f"Xây tháp: {total_towers_built}/10")
            
        # Thành tựu tiến độ level
        if max_level >= 15:
            achievements.append("Tiến độ: Master (Lv15+)")
        elif max_level >= 10:
            achievements.append("Tiến độ: Expert (Lv10+)")
        elif max_level >= 5:
            achievements.append("Tiến độ: Advanced (Lv5+)")
        else:
            achievements.append(f"Tiến độ: Lv{max_level}/15")
            
        # Thành tựu số lần chơi
        if total_games >= 50:
            achievements.append("Kinh nghiệm: Master (50+ games)")
        elif total_games >= 20:
            achievements.append("Kinh nghiệm: Expert (20+ games)")
        elif total_games >= 10:
            achievements.append("Kinh nghiệm: Advanced (10+ games)")
        else:
            achievements.append(f"Kinh nghiệm: {total_games}/10 games")
            
        # Thành tựu đặc biệt
        current_mode = MODES[self.menu_mode_idx]
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            level_by_mode = account.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            max_unlocked = level_by_mode.get(current_mode, 1)
        else:
            level_by_mode = self.save.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            max_unlocked = level_by_mode.get(current_mode, 1)
            
        if max_unlocked >= TOTAL_LEVELS:
            achievements.append("Hoàn thành tất cả màn!")
            
        # Đảm bảo có ít nhất 5 dòng
        while len(achievements) < 5:
            achievements.append("Thành tựu sắp mở khóa...")
            
        return achievements[:5]  # Chỉ hiển thị tối đa 5 thành tựu

    def draw_leader(self):
        """Vẽ bảng xếp hạng với thiết kế đẹp như giao diện chọn level."""
        # [ART] GRADIENT BACKGROUND SIÊU ĐẸP
        self._draw_gradient_background((15, 25, 45), (45, 65, 85), vertical=True)
        
        # Background image với hiệu ứng blur (nếu có)
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert_alpha()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            
            # Tạo hiệu ứng blur/overlay sang trọng
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for y in range(HEIGHT):
                alpha = int(80 + (y / HEIGHT) * 40)
                pygame.draw.line(overlay, (0, 0, 50, alpha), (0, y), (WIDTH, y))
            
            self.screen.blit(bg_img, (0, 0))
            self.screen.blit(overlay, (0, 0))
        except Exception:
            pass
        
        # * ANIMATED TITLE với multiple shadows và glow effect
        current_time = pygame.time.get_ticks()
        pulse = math.sin(current_time * 0.003) * 0.1 + 1.0  # Pulse animation
        
        title_font_size = int(42 * pulse)
        title_font = self._get_font(title_font_size, bold=True)
        title_text = "BẢNG XẾP HẠNG"
        title_surf = title_font.render(title_text, True, (255, 220, 100))
        title_rect = title_surf.get_rect(center=(WIDTH//2, 70))
        
        # Multiple shadow layers for depth
        shadow_colors = [(0, 0, 0, 180), (50, 30, 0, 120), (100, 60, 0, 80)]
        shadow_offsets = [(4, 4), (2, 2), (1, 1)]
        
        for (shadow_color, offset) in zip(shadow_colors, shadow_offsets):
            shadow_surf = title_font.render(title_text, True, shadow_color[:3])
            shadow_rect = title_rect.move(offset[0], offset[1])
            self.screen.blit(shadow_surf, shadow_rect)
        
        # Glow effect
        glow_surf = title_font.render(title_text, True, (255, 255, 150))
        for glow_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            glow_rect = title_rect.move(glow_offset[0], glow_offset[1])
            self.screen.blit(glow_surf, glow_rect)
        
        # Main title
        self.screen.blit(title_surf, title_rect)
        
        # ✨ COMPACT INFO PANEL với glassmorphism effect  
        info_panel_rect = pygame.Rect(WIDTH//2 - 250, 100, 500, 50)
        
        # Glassmorphism background
        glass_surf = pygame.Surface((info_panel_rect.width, info_panel_rect.height), pygame.SRCALPHA)
        glass_surf.fill((255, 255, 255, 20))
        
        # Gradient overlay
        for y in range(info_panel_rect.height):
            alpha = int(10 + (y / info_panel_rect.height) * 15)
            color = (50, 100, 150, alpha)
            pygame.draw.line(glass_surf, color, (0, y), (info_panel_rect.width, y))
        
        self.screen.blit(glass_surf, info_panel_rect)
        
        # Border với gradient
        pygame.draw.rect(self.screen, (100, 150, 200, 150), info_panel_rect, width=2, border_radius=12)
        
        # Subtitle với styling đẹp
        subtitle_font = self._get_font(16, bold=True)
        subtitle_text = "Top điểm số cao nhất từ Permanent Map"
        subtitle_surf = subtitle_font.render(subtitle_text, True, (150, 200, 255))
        subtitle_rect = subtitle_surf.get_rect(center=(WIDTH//2, info_panel_rect.centery))
        self.screen.blit(subtitle_surf, subtitle_rect)
        
        # Thu thập chỉ điểm số từ Permanent Map
        all_scores = []
        
        # Từ các tài khoản đã đăng nhập
        for username, account_data in self.accounts.items():
            account_leaderboard = account_data.get("leaderboard", [])
            # Lấy player_name từ account, fallback về username nếu không có
            player_name = account_data.get("player_name", username)
            for entry in account_leaderboard:
                # Chỉ lấy entry từ permanent map
                if entry.get("is_permanent", False):
                    all_scores.append({
                        "name": player_name,
                        "level": entry.get("level", 0),
                        "wave": entry.get("wave", 0),
                        "score": entry.get("score", 0),
                        "ts": entry.get("ts", 0),
                        "is_permanent": True
                    })
        
        # Bỏ save cũ vì không có thông tin permanent map
        
        # Sắp xếp theo điểm số giảm dần
        all_scores.sort(key=lambda x: -x["score"])
        
        # Loại bỏ trùng lặp - chỉ giữ điểm cao nhất cho mỗi người chơi
        unique_scores = {}
        for entry in all_scores:
            player_name = entry["name"]
            if player_name not in unique_scores:
                # Chưa có người chơi này, thêm vào
                unique_scores[player_name] = entry
            else:
                # Đã có người chơi này, so sánh điểm số
                if entry["score"] > unique_scores[player_name]["score"]:
                    # Điểm mới cao hơn, thay thế
                    unique_scores[player_name] = entry
        
        # Chuyển dict thành list và sắp xếp lại theo điểm
        top_scores = list(unique_scores.values())
        top_scores.sort(key=lambda x: -x["score"])
        top_scores = top_scores[:15]  # Lấy top 15
        
        # COMPACT LEADERBOARD với card-style entries
        leaderboard_start_y = 170
        card_height = 38
        card_margin = 4
        card_width = 700  # Thu gọn lại từ WIDTH-200 xuống 700px
        card_start_x = (WIDTH - card_width) // 2
        
        for i, row in enumerate(top_scores, start=1):
            y_pos = leaderboard_start_y + (i - 1) * (card_height + card_margin)
            
            # [CARD] Tạo card cho mỗi entry - căn giữa
            card_rect = pygame.Rect(card_start_x, y_pos, card_width, card_height)
            
            # Màu sắc và hiệu ứng cho top 3
            if i == 1:
                # GOLD - Gradient vàng lấp lánh
                card_colors = [(180, 140, 30), (255, 215, 0)]
                border_color = (255, 255, 150)
                text_color = (255, 255, 255)
                rank_emoji = "#1"
                glow_color = (255, 215, 0, 100)
            elif i == 2:
                # SILVER - Gradient bạc sang trọng
                card_colors = [(120, 120, 120), (192, 192, 192)]
                border_color = (220, 220, 220)
                text_color = (255, 255, 255)
                rank_emoji = "#2"
                glow_color = (192, 192, 192, 80)
            elif i == 3:
                # BRONZE - Gradient đồng ấm áp
                card_colors = [(140, 90, 50), (205, 127, 50)]
                border_color = (255, 180, 100)
                text_color = (255, 255, 255)
                rank_emoji = "#3"
                glow_color = (205, 127, 50, 60)
            else:
                # NORMAL - Gradient xanh hiện đại
                card_colors = [(40, 60, 80), (70, 90, 120)]
                border_color = (100, 140, 180)
                text_color = (220, 230, 240)
                rank_emoji = f"{i:2d}"
                glow_color = (70, 90, 120, 40)
            
            # Glow effect cho top 3
            if i <= 3:
                glow_rect = card_rect.inflate(8, 8)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                glow_surf.fill(glow_color)
                self.screen.blit(glow_surf, glow_rect)
            
            # Card shadow
            shadow_rect = card_rect.move(3, 3)
            shadow_surf = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 100))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Card gradient background
            self._draw_gradient_rect(card_rect, card_colors[0], card_colors[1], 12)
            
            # Card border
            pygame.draw.rect(self.screen, border_color, card_rect, width=2, border_radius=12)
            
            # 📊 Nội dung card với layout compact
            rank_font = self._get_font(14, bold=True)
            name_font = self._get_font(16, bold=True) if i <= 3 else self._get_font(14, bold=True)
            score_font = self._get_font(14, bold=True)
            wave_font = self._get_font(12)
            
            # Rank number/emoji - REMOVED (không hiển thị ô vuông nữa)
            # rank_surf = rank_font.render(rank_emoji, True, text_color)
            # rank_pos = (card_rect.x + 12, card_rect.y + (card_height - rank_surf.get_height()) // 2)
            # self.screen.blit(rank_surf, rank_pos)
            
            # Player name - single line compact - dời sang trái vì không có rank
            name_text = row['name'][:15] + ("..." if len(row['name']) > 15 else "")
            name_shadow = name_font.render(name_text, True, (0, 0, 0))
            name_main = name_font.render(name_text, True, text_color)
            
            name_x = card_rect.x + 15  # Dời từ 50 sang 15 vì không có rank
            name_y = card_rect.y + (card_height - name_main.get_height()) // 2
            self.screen.blit(name_shadow, (name_x + 1, name_y + 1))
            self.screen.blit(name_main, (name_x, name_y))
            
            # Wave info - inline với name
            wave_display = row.get('wave', row.get('level', 0))
            wave_text = f"Wave {wave_display}"
            wave_surf = wave_font.render(wave_text, True, (180, 200, 220))
            wave_x = card_rect.x + 180  # Điều chỉnh để phù hợp với card nhỏ hơn
            wave_y = card_rect.y + (card_height - wave_surf.get_height()) // 2
            self.screen.blit(wave_surf, (wave_x, wave_y))
            
            # Score với highlight - align right
            score_text = f"{row['score']:,}"
            score_shadow = score_font.render(score_text, True, (0, 0, 0))
            score_main = score_font.render(score_text, True, text_color)
            
            score_x = card_rect.right - 90  # Điều chỉnh để vừa với card nhỏ hơn
            score_y = card_rect.y + (card_height - score_main.get_height()) // 2
            self.screen.blit(score_shadow, (score_x + 1, score_y + 1))
            self.screen.blit(score_main, (score_x, score_y))
            
            # Star icon cho top 3 - REMOVED (không hiển thị ô vuông nữa)
            # if i <= 3:
            #     medal_surf = self._get_font(16).render("★", True, (255, 215, 0))
            #     medal_pos = (card_rect.right - 25, card_rect.y + (card_height - medal_surf.get_height()) // 2)
            #     self.screen.blit(medal_surf, medal_pos)
        
        # 📋 Thông báo nếu không có điểm - compact và căn giữa
        if not top_scores:
            empty_panel_rect = pygame.Rect(WIDTH//2 - 200, 200, 400, 80)
            
            # Empty state background
            empty_surf = pygame.Surface((empty_panel_rect.width, empty_panel_rect.height), pygame.SRCALPHA)
            empty_surf.fill((40, 60, 80, 100))
            self.screen.blit(empty_surf, empty_panel_rect)
            pygame.draw.rect(self.screen, (100, 140, 180), empty_panel_rect, width=2, border_radius=12)
            
            # Empty state content
            empty_font = self._get_font(18, bold=True)
            tip_font = self._get_font(14)
            
            empty_text = "Chưa có điểm số từ Permanent Map"
            empty_surf = empty_font.render(empty_text, True, (150, 200, 255))
            empty_rect = empty_surf.get_rect(center=(empty_panel_rect.centerx, empty_panel_rect.y + 25))
            self.screen.blit(empty_surf, empty_rect)
            
            tip_text = "Chơi Permanent Map để xuất hiện trong bảng xếp hạng!"
            tip_surf = tip_font.render(tip_text, True, (200, 220, 240))
            tip_rect = tip_surf.get_rect(center=(empty_panel_rect.centerx, empty_panel_rect.y + 50))
            self.screen.blit(tip_surf, tip_rect)
            
        # 📊 COMPACT STATS PANEL - căn giữa
        stats_y = leaderboard_start_y + len(top_scores) * (card_height + card_margin) + 20 if top_scores else 300
        stats_panel_rect = pygame.Rect(WIDTH//2 - 175, stats_y, 350, 60)
        
        # Stats background với glassmorphism
        stats_surf = pygame.Surface((stats_panel_rect.width, stats_panel_rect.height), pygame.SRCALPHA)
        stats_surf.fill((255, 255, 255, 15))
        
        # Gradient overlay cho stats
        for y in range(stats_panel_rect.height):
            alpha = int(5 + (y / stats_panel_rect.height) * 20)
            color = (30, 50, 70, alpha)
            pygame.draw.line(stats_surf, color, (0, y), (stats_panel_rect.width, y))
        
        self.screen.blit(stats_surf, stats_panel_rect)
        pygame.draw.rect(self.screen, (80, 120, 160), stats_panel_rect, width=2, border_radius=10)
        
        # Stats content - compact
        stats_font = self._get_font(14, bold=True)
        unique_players = len(unique_scores) if top_scores else 0
        total_games = len(all_scores)
        
        stats_title = "THỐNG KÊ TỔNG QUAN"
        stats_text = f"{total_games} lượt chơi từ {unique_players} người chơi"
        
        title_surf = stats_font.render(stats_title, True, (150, 200, 255))
        text_surf = self._get_font(12).render(stats_text, True, (180, 200, 220))
        
        title_rect = title_surf.get_rect(center=(stats_panel_rect.centerx, stats_panel_rect.y + 18))
        text_rect = text_surf.get_rect(center=(stats_panel_rect.centerx, stats_panel_rect.y + 38))
        
        self.screen.blit(title_surf, title_rect)
        self.screen.blit(text_surf, text_rect)
        
        # COMPACT BACK BUTTON - căn giữa dưới cùng
        back_button_rect = pygame.Rect(WIDTH//2 - 75, HEIGHT - 80, 150, 50)
        mx, my = pygame.mouse.get_pos()
        is_back_hovered = back_button_rect.collidepoint((mx, my))
        
        # Back button animation
        if is_back_hovered:
            button_scale = 1.05
            back_colors = [(180, 60, 60), (220, 100, 100)]
            border_color = (255, 150, 100)
        else:
            button_scale = 1.0
            back_colors = [(120, 40, 40), (160, 70, 70)]
            border_color = (200, 100, 100)
        
        # Scaled button
        scaled_back_size = (int(back_button_rect.width * button_scale), int(back_button_rect.height * button_scale))
        scaled_back_rect = pygame.Rect(
            back_button_rect.x + (back_button_rect.width - scaled_back_size[0]) // 2,
            back_button_rect.y + (back_button_rect.height - scaled_back_size[1]) // 2,
            *scaled_back_size
        )
        
        # Button shadow
        shadow_rect = scaled_back_rect.move(2, 2)
        shadow_surf = pygame.Surface(scaled_back_size, pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 100))
        self.screen.blit(shadow_surf, shadow_rect)
        
        # Gradient button
        self._draw_gradient_rect(scaled_back_rect, back_colors[0], back_colors[1], 10)
        
        # Button border
        pygame.draw.rect(self.screen, border_color, scaled_back_rect, width=2, border_radius=10)
        
        # Button text với shadow - smaller
        back_font = self._get_font(16, bold=True)
        back_text = "Trở về Menu"
        text_shadow = back_font.render(back_text, True, (0, 0, 0))
        text_main = back_font.render(back_text, True, WHITE)
        
        text_rect = text_main.get_rect(center=scaled_back_rect.center)
        shadow_rect = text_rect.move(1, 1)
        
        self.screen.blit(text_shadow, shadow_rect)
        self.screen.blit(text_main, text_rect)

    def draw_name(self):
        """Vẽ màn hình đổi tên người chơi với thiết kế đẹp như bảng xếp hạng."""
        # [ART] GRADIENT BACKGROUND SIÊU ĐẸP
        self._draw_gradient_background((15, 25, 45), (45, 65, 85), vertical=True)
        
        # Background image với hiệu ứng blur (nếu có)
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert_alpha()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            
            # Tạo hiệu ứng blur/overlay sang trọng
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for y in range(HEIGHT):
                alpha = int(120 + (y / HEIGHT) * 60)
                color = (20, 30, 50, alpha)
                pygame.draw.line(overlay, color, (0, y), (WIDTH, y))
            
            self.screen.blit(bg_img, (0, 0))
            self.screen.blit(overlay, (0, 0))
        except Exception:
            pass
        
        # * ANIMATED TITLE với multiple shadows và glow effect
        current_time = pygame.time.get_ticks()
        pulse = math.sin(current_time * 0.003) * 0.1 + 1.0  # Pulse animation
        
        title_font_size = int(38 * pulse)
        title_font = self._get_font(title_font_size, bold=True)
        title_text = "NHẬP TÊN NGƯỜI CHƠI"
        title_surf = title_font.render(title_text, True, (255, 220, 100))
        title_rect = title_surf.get_rect(center=(WIDTH//2, 100))
        
        # Multiple shadow layers for depth
        shadow_colors = [(0, 0, 0, 180), (50, 30, 0, 120), (100, 60, 0, 80)]
        shadow_offsets = [(4, 4), (2, 2), (1, 1)]
        
        for (shadow_color, offset) in zip(shadow_colors, shadow_offsets):
            shadow_surf = title_font.render(title_text, True, shadow_color[:3])
            shadow_rect = title_rect.move(offset[0], offset[1])
            self.screen.blit(shadow_surf, shadow_rect)
        
        # Glow effect
        glow_surf = title_font.render(title_text, True, (255, 255, 150))
        for glow_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            glow_rect = title_rect.move(glow_offset[0], glow_offset[1])
            self.screen.blit(glow_surf, glow_rect)
        
        # Main title
        self.screen.blit(title_surf, title_rect)
        
        # ✨ COMPACT INFO PANEL với glassmorphism effect  
        info_panel_rect = pygame.Rect(WIDTH//2 - 250, 130, 500, 40)
        
        # Glassmorphism background
        glass_surf = pygame.Surface((info_panel_rect.width, info_panel_rect.height), pygame.SRCALPHA)
        glass_surf.fill((255, 255, 255, 20))
        
        # Gradient overlay
        for y in range(info_panel_rect.height):
            alpha = int(10 + (y / info_panel_rect.height) * 15)
            color = (50, 100, 150, alpha)
            pygame.draw.line(glass_surf, color, (0, y), (info_panel_rect.width, y))
        
        self.screen.blit(glass_surf, info_panel_rect)
        
        # Border với gradient
        pygame.draw.rect(self.screen, (100, 150, 200, 150), info_panel_rect, width=2, border_radius=12)
        
        # Subtitle với styling đẹp
        subtitle_font = self._get_font(16, bold=True)
        subtitle_text = "Tên hiển thị sẽ xuất hiện trong bảng xếp hạng"
        subtitle_surf = subtitle_font.render(subtitle_text, True, (150, 200, 255))
        subtitle_rect = subtitle_surf.get_rect(center=(WIDTH//2, info_panel_rect.centery))
        self.screen.blit(subtitle_surf, subtitle_rect)
        
        # INPUT BOX với thiết kế đẹp
        input_box_rect = pygame.Rect(WIDTH//2 - 200, 200, 400, 50)
        
        # Input background với glassmorphism
        input_surf = pygame.Surface((input_box_rect.width, input_box_rect.height), pygame.SRCALPHA)
        input_surf.fill((255, 255, 255, 30))
        
        # Gradient overlay cho input
        for y in range(input_box_rect.height):
            alpha = int(20 + (y / input_box_rect.height) * 20)
            color = (255, 255, 255, alpha)
            pygame.draw.line(input_surf, color, (0, y), (input_box_rect.width, y))
        
        self.screen.blit(input_surf, input_box_rect)
        pygame.draw.rect(self.screen, (100, 150, 200), input_box_rect, width=3, border_radius=15)
        
        # Input text với font đẹp
        input_font = self._get_font(20, bold=True)
        input_text = getattr(self, 'name_input', '')
        if input_text:
            input_text_surf = input_font.render(input_text, True, (0, 0, 0))
        else:
            # Placeholder text
            input_text_surf = input_font.render("Nhập tên của bạn...", True, (120, 120, 120))
        
        input_text_rect = input_text_surf.get_rect()
        input_text_rect.x = input_box_rect.x + 15
        input_text_rect.centery = input_box_rect.centery
        self.screen.blit(input_text_surf, input_text_rect)
        
        # Hiển thị thông báo lỗi nếu có với styling đẹp
        if hasattr(self, 'auth_msg') and self.auth_msg:
            error_color = (255, 100, 100) if "đã được sử dụng" in self.auth_msg else (150, 255, 150)
            error_font = self._get_font(16, bold=True)
            error_surf = error_font.render(self.auth_msg, True, error_color)
            error_rect = error_surf.get_rect(center=(WIDTH//2, 270))
            self.screen.blit(error_surf, error_rect)
            instruction_y = 300
        else:
            instruction_y = 280
        
        # Instructions với styling đẹp
        instruction_font = self._get_font(18, bold=True)
        instruction_text = "Enter: lưu   |   ESC: huỷ"
        instruction_surf = instruction_font.render(instruction_text, True, (200, 200, 255))
        instruction_rect = instruction_surf.get_rect(center=(WIDTH//2, instruction_y))
        self.screen.blit(instruction_surf, instruction_rect)

    def draw_all_clear(self):
        self.screen.fill((10,10,20))
        if self.level >= MAX_LEVELS:
            msg = self.bigfont.render("HOÀN THÀNH TẤT CẢ LEVEL! [TROPHY]", True, ORANGE)
            submsg = self.font.render(f"Bạn đã vượt qua {MAX_LEVELS} level - Chúc mừng Siêu Cao Thủ!", True, WHITE)
        else:
            msg = self.bigfont.render(f"HOÀN THÀNH {TOTAL_LEVELS} LEVEL CỐ ĐỊNH! [PARTY]", True, ORANGE)  
            submsg = self.font.render("Bây giờ bạn có thể chơi với map tự động vô hạn!", True, WHITE)
        
        self.screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
        self.screen.blit(submsg, submsg.get_rect(center=(WIDTH//2, HEIGHT//2)))
        tip = self.font.render("Nhấn ESC để về menu", True, WHITE)
        self.screen.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))

    def draw_auth(self):
        if self.bg_menu is not None:
            self.screen.blit(self.bg_menu, (0, 0))
        else:
            self.screen.fill((30, 34, 45))
        # Vẽ background khi đăng nhập
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            self.screen.blit(bg_img, (0, 0))
            
            # Thêm overlay để che chữ "TOWER DEFENSE" nếu có trong background
            overlay = pygame.Surface((WIDTH, 200), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))  # Màu đen trong suốt ở phần trên
            self.screen.blit(overlay, (0, 0))
        except Exception:
            self.screen.fill((30, 34, 45))

        # Tiêu đề chính cho màn hình đăng nhập
        title_font = self._get_font(42, bold=True)
        title_text = "ĐĂNG NHẬP"
        title_surf = title_font.render(title_text, True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(WIDTH//2, 150))
        # Shadow effect
        shadow_surf = title_font.render(title_text, True, (0, 0, 0))
        shadow_rect = title_rect.move(2, 2)
        self.screen.blit(shadow_surf, shadow_rect)
        self.screen.blit(title_surf, title_rect)
        
        # Tiêu đề phụ và vị trí form
        form_offset = 250
        subtitle = self.font.render("Vui lòng đăng nhập hoặc đăng ký để tiếp tục", True, (200,200,200))
        subtitle_rect = subtitle.get_rect(center=(WIDTH//2, form_offset))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                self.screen.blit(self.font.render("Vui lòng đăng nhập hoặc đăng ký để tiếp tục", True, BLACK), subtitle_rect.move(dx, dy))
        self.screen.blit(subtitle, subtitle_rect)

        # Tabs (login / register)
        tab_w, tab_h = 130, 42
        tab_x = WIDTH//2 - tab_w - 10
        tab_y = form_offset + 40
        tab_login = pygame.Rect(tab_x, tab_y, tab_w, tab_h)
        tab_reg   = pygame.Rect(tab_x+tab_w+20, tab_y, tab_w, tab_h)

        def draw_tab(rect, text, active):
            color = (90,140,240) if active else (70,70,90)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            label = self.font.render(text, True, WHITE)
            label_rect = label.get_rect(center=rect.center)
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    if dx == 0 and dy == 0: continue
                    self.screen.blit(self.font.render(text, True, BLACK), label_rect.move(dx, dy))
            self.screen.blit(label, label_rect)

        draw_tab(tab_login, "Đăng nhập", self.auth_mode=="login")
        draw_tab(tab_reg,   "Đăng ký",   self.auth_mode=="register")

        # Ô nhập user/pass
        box_w, box_h = 250, 44
        box_x = WIDTH//2 - box_w//2
        box_gap = 24
        box_user = pygame.Rect(box_x, tab_y + tab_h + 30, box_w, box_h)
        box_pass = pygame.Rect(box_x, box_user.bottom + box_gap, box_w, box_h)
        box_pass2 = pygame.Rect(box_x, box_pass.bottom + box_gap, box_w, box_h)

        def draw_input(rect, label, value, focus=False, secret=False):
            pygame.draw.rect(self.screen, (250,250,250) if focus else (200,200,200), rect, border_radius=8)
            pygame.draw.rect(self.screen, (100,100,120), rect, width=2, border_radius=8)
            lbl = self.font.render(label, True, WHITE)
            lbl_rect = lbl.get_rect(topleft=(rect.x, rect.y-26))
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    if dx == 0 and dy == 0: continue
                    self.screen.blit(self.font.render(label, True, BLACK), lbl_rect.move(dx, dy))
            self.screen.blit(lbl, lbl_rect)
            txt = value if not secret else "*"*len(value)
            val = self.medfont.render(txt, True, (20,20,20))
            self.screen.blit(val, (rect.x+10, rect.y+10))

        draw_input(box_user, "Tài khoản", self.auth_user, self._auth_focus=="user", secret=False)
        draw_input(box_pass, "Mật khẩu",  self.auth_pass, self._auth_focus=="pass", secret=True)
        if self.auth_mode == "register":
            draw_input(box_pass2, "Xác nhận mật khẩu", self.auth_pass2, self._auth_focus=="pass2", secret=True)

        # Nút xác nhận / back
        btn_w, btn_h = 120, 42
        btn_gap = 20
        btn_y = (box_pass2.bottom + box_gap) if self.auth_mode == "register" else (box_pass.bottom + box_gap)
        btn_ok   = pygame.Rect(WIDTH//2 - btn_w - btn_gap//2, btn_y, btn_w, btn_h)
        btn_back = pygame.Rect(WIDTH//2 + btn_gap//2, btn_y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (90,160,90), btn_ok, border_radius=10)
        pygame.draw.rect(self.screen, (160,90,90), btn_back, border_radius=10)
        self.screen.blit(self.font.render("Xác nhận", True, WHITE), btn_ok.move(15,10))
        self.screen.blit(self.font.render("Hủy", True, WHITE), btn_back.move(40,10))

        # Thông báo trạng thái
        msg_y = btn_y + btn_h + 20
        if self.auth_msg:
            msg = self.font.render(self.auth_msg, True, RED)
            msg_rect = msg.get_rect(center=(WIDTH//2, msg_y))
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    if dx == 0 and dy == 0: continue
                    self.screen.blit(self.font.render(self.auth_msg, True, BLACK), msg_rect.move(dx, dy))
            self.screen.blit(msg, msg_rect)

        # Lưu rect để handle click
        self._auth_rects = {"tab_login":tab_login,"tab_reg":tab_reg,"user":box_user,"pass":box_pass,"pass2":box_pass2 if self.auth_mode=="register" else None,"ok":btn_ok,"back":btn_back}

    def draw_level_select(self):
        """Vẽ màn hình chọn level siêu đẹp và chuyên nghiệp."""
        # [ART] GRADIENT BACKGROUND SIÊU ĐẸP
        self._draw_gradient_background((15, 25, 45), (45, 65, 85), vertical=True)
        
        # Background image với hiệu ứng blur
        try:
            bg_img = pygame.image.load(os.path.join(ASSETS_DIR, "background.png")).convert_alpha()
            bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
            
            # Tạo hiệu ứng blur/overlay sang trọng
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            # Gradient overlay từ trong suốt đến đen
            for y in range(HEIGHT):
                alpha = int(80 + (y / HEIGHT) * 40)  # Alpha tăng dần từ trên xuống
                pygame.draw.line(overlay, (0, 0, 50, alpha), (0, y), (WIDTH, y))
            
            self.screen.blit(bg_img, (0, 0))
            self.screen.blit(overlay, (0, 0))
        except Exception:
            pass
        
        # * ANIMATED TITLE với multiple shadows và glow effect
        current_time = pygame.time.get_ticks()
        pulse = math.sin(current_time * 0.003) * 0.1 + 1.0  # Pulse animation
        
        title_font_size = int(48 * pulse)
        title_font = self._get_font(title_font_size, bold=True)
        title_text = "CHỌN LEVEL"
        title_surf = title_font.render(title_text, True, (255, 220, 100))
        title_rect = title_surf.get_rect(center=(WIDTH//2, 70))
        
        # Multiple shadow layers for depth
        shadow_colors = [(0, 0, 0, 180), (50, 30, 0, 120), (100, 60, 0, 80)]
        shadow_offsets = [(4, 4), (2, 2), (1, 1)]
        
        for (shadow_color, offset) in zip(shadow_colors, shadow_offsets):
            shadow_surf = title_font.render(title_text, True, shadow_color[:3])
            shadow_rect = title_rect.move(offset[0], offset[1])
            self.screen.blit(shadow_surf, shadow_rect)
        
        # Glow effect
        glow_surf = title_font.render(title_text, True, (255, 255, 150))
        for glow_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            glow_rect = title_rect.move(glow_offset[0], glow_offset[1])
            self.screen.blit(glow_surf, glow_rect)
        
        # Main title
        self.screen.blit(title_surf, title_rect)
        
        # [MODERN] MODE SELECTOR với siêu đẹp styling
        mode_selector_y = 120
        mode_button_w = 100
        mode_button_h = 40
        mode_gap = 15
        total_mode_width = len(MODES) * mode_button_w + (len(MODES) - 1) * mode_gap
        mode_start_x = (WIDTH - total_mode_width) // 2
        
        mx, my = pygame.mouse.get_pos()
        
        # Vẽ các nút chế độ với animation
        for i, mode in enumerate(MODES):
            mode_x = mode_start_x + i * (mode_button_w + mode_gap)
            mode_rect = pygame.Rect(mode_x, mode_selector_y, mode_button_w, mode_button_h)
            
            is_selected = (i == self.menu_mode_idx)
            is_hovered = mode_rect.collidepoint((mx, my))
            
            # Color scheme cho từng chế độ
            if mode == "Easy":
                base_color = (60, 140, 60) if is_selected else (40, 100, 40)
                hover_color = (80, 180, 80)
                text_color = (200, 255, 200)
            elif mode == "Normal":
                base_color = (120, 120, 60) if is_selected else (80, 80, 40)
                hover_color = (160, 160, 80)
                text_color = (255, 255, 200)
            else:  # Hard
                base_color = (140, 60, 60) if is_selected else (100, 40, 40)
                hover_color = (180, 80, 80)
                text_color = (255, 200, 200)
            
            # Hover effect
            if is_hovered:
                draw_color = hover_color
                button_scale = 1.05
            else:
                draw_color = base_color
                button_scale = 1.0
                
            # Selected glow effect
            if is_selected:
                glow_rect = mode_rect.inflate(6, 6)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                glow_surf.fill((*draw_color, 100))
                self.screen.blit(glow_surf, glow_rect)
            
            # Scale effect cho hover
            if button_scale != 1.0:
                scaled_w = int(mode_button_w * button_scale)
                scaled_h = int(mode_button_h * button_scale)
                scaled_rect = pygame.Rect(
                    mode_x + (mode_button_w - scaled_w) // 2,
                    mode_selector_y + (mode_button_h - scaled_h) // 2,
                    scaled_w, scaled_h
                )
            else:
                scaled_rect = mode_rect
            
            # Vẽ nút với gradient
            self._draw_gradient_rect(scaled_rect, draw_color, 
                                   (min(255, draw_color[0] + 30), 
                                    min(255, draw_color[1] + 30), 
                                    min(255, draw_color[2] + 30)), 8)
            
            # Border cho selected
            if is_selected:
                pygame.draw.rect(self.screen, (255, 255, 255), scaled_rect, width=3, border_radius=8)
            else:
                pygame.draw.rect(self.screen, (200, 200, 200), scaled_rect, width=1, border_radius=8)
            
            # Text với shadow
            mode_font = self._get_font(14, bold=True)
            text_shadow = mode_font.render(mode, True, (0, 0, 0))
            text_main = mode_font.render(mode, True, text_color)
            
            text_rect = text_main.get_rect(center=scaled_rect.center)
            shadow_rect = text_rect.move(1, 1)
            
            self.screen.blit(text_shadow, shadow_rect)
            self.screen.blit(text_main, text_rect)
            
            # Lưu rect để xử lý click (backup method, chủ yếu dùng hardcoded check ở trên)
            if not hasattr(self, '_level_rects') or self._level_rects is None:
                self._level_rects = {}
            self._level_rects[f"mode_{i}"] = mode_rect
        
        # Lấy số level đã mở theo chế độ hiện tại
        current_mode = MODES[self.menu_mode_idx]
        
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            level_by_mode = account.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            max_level = level_by_mode.get(current_mode, 1)
            stars = account.get("stars", 0)
        else:
            level_by_mode = self.save.get("level_unlocked_by_mode", {"Easy": 1, "Normal": 1, "Hard": 1})
            max_level = level_by_mode.get(current_mode, 1)
            stars = self.save.get("stars", 0)
        
        # � SIÊU ĐẸP INFO PANEL với glassmorphism effect  
        info_panel_rect = pygame.Rect(40, 180, WIDTH - 80, 80)
        
        # Glassmorphism background
        glass_surf = pygame.Surface((info_panel_rect.width, info_panel_rect.height), pygame.SRCALPHA)
        glass_surf.fill((255, 255, 255, 20))  # Semi-transparent white
        
        # Gradient overlay
        for y in range(info_panel_rect.height):
            alpha = int(10 + (y / info_panel_rect.height) * 15)
            color = (50, 100, 150, alpha)
            pygame.draw.line(glass_surf, color, (0, y), (info_panel_rect.width, y))
        
        self.screen.blit(glass_surf, info_panel_rect)
        
        # Border với gradient
        pygame.draw.rect(self.screen, (100, 150, 200, 150), info_panel_rect, width=2, border_radius=15)
        
        # [CHART] Thông tin người chơi với icons và styling
        info_font = self._get_font(16, bold=True)
        small_font = self._get_font(14)
        
        # Line 1: Mode và Progress
        mode_text = f"Mode: {current_mode}"
        stars_text = f"Stars: {stars}"
        # Clamp display value to TOTAL_LEVELS to avoid showing corrupted save numbers
        try:
            from config import TOTAL_LEVELS
        except Exception:
            TOTAL_LEVELS = 15

        display_max = max(1, min(int(max_level), TOTAL_LEVELS))
        progress_text = f"Số màn đã mở: {display_max}/{TOTAL_LEVELS}"
        
        mode_surf = info_font.render(mode_text, True, (150, 200, 255))
        stars_surf = info_font.render(stars_text, True, (255, 215, 0))
        progress_surf = info_font.render(progress_text, True, (100, 255, 150))
        
        y_line1 = info_panel_rect.y + 15
        self.screen.blit(mode_surf, (info_panel_rect.x + 20, y_line1))
        self.screen.blit(stars_surf, (info_panel_rect.x + 200, y_line1))
        self.screen.blit(progress_surf, (info_panel_rect.x + 350, y_line1))
        
        # Line 2: Game rules với warning colors
        lives_mode = MODE_PARAMS[current_mode]["lives"]
        lives_text = f"{lives_mode} Mạng"
        warning_text = "BOSS Thoát = GAME OVER!"
        
        lives_surf = small_font.render(lives_text, True, (255, 100, 100))
        warning_surf = small_font.render(warning_text, True, (255, 50, 50))
        
        y_line2 = info_panel_rect.y + 45
        self.screen.blit(lives_surf, (info_panel_rect.x + 20, y_line2))
        
        # Flashing warning effect
        warning_alpha = int(200 + math.sin(current_time * 0.008) * 55)
        warning_color = (255, 50, 50, warning_alpha)
        warning_surf = small_font.render(warning_text, True, warning_color[:3])
        self.screen.blit(warning_surf, (info_panel_rect.x + 150, y_line2))
        
        # [TARGET] MODERN LEVEL BUTTONS LAYOUT 
        cols = 4
        rows = 5
        level_per_page = cols * rows
        button_size = 90  # Tăng size để đẹp hơn
        gap = 25  # Tăng gap cho thoáng hơn
        start_x = (WIDTH - cols * (button_size + gap)) // 2
        start_y = 290  # Điều chỉnh vị trí để không đè lên mode selector
        
        # [WAVE] ANIMATED FLOATING PARTICLES BACKGROUND
        particle_time = pygame.time.get_ticks() * 0.001
        for i in range(15):
            px = (i * 80 + math.sin(particle_time + i) * 30) % WIDTH
            py = (200 + i * 40 + math.cos(particle_time * 0.8 + i) * 20) % (HEIGHT - 200)
            particle_alpha = int(20 + math.sin(particle_time * 2 + i) * 10)
            particle_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            particle_surf.fill((100, 150, 255, particle_alpha))
            self.screen.blit(particle_surf, (px, py))

        # Reset stored rects so event handler can use exact on-screen hitboxes
        self._level_rects = {}

        # [ART] Vẽ các level buttons với hiệu ứng SIÊU ĐẸP
        current_time = pygame.time.get_ticks()
        for level in range(1, min(max_level + 1, level_per_page + 1)):
            row = (level - 1) // cols
            col = (level - 1) % cols
            
            x = start_x + col * (button_size + gap)
            y = start_y + row * (button_size + gap)
            
            level_rect = pygame.Rect(x, y, button_size, button_size)
            
            # [MASK] ADVANCED STYLING dựa trên trạng thái
            is_boss_level = level in BOSS_LEVELS
            mx, my = pygame.mouse.get_pos()
            is_hovered = level_rect.collidepoint((mx, my)) and level <= max_level
            
            # [ART] Color schemes siêu đẹp
            if level <= max_level:
                if is_boss_level:
                    # [CROWN] BOSS LEVEL - Gradient vàng tím hoành tráng
                    base_colors = [(80, 40, 120), (140, 80, 180)]  # Tím gradient
                    border_colors = [(200, 150, 50), (255, 200, 100)]  # Vàng gradient
                    text_color = (255, 255, 150)
                    glow_color = (255, 200, 100, 100)
                else:
                    # ✅ NORMAL LEVEL - Gradient xanh hiện đại  
                    base_colors = [(30, 100, 60), (50, 140, 80)]  # Xanh gradient
                    border_colors = [(60, 180, 100), (80, 220, 120)]  # Xanh sáng
                    text_color = WHITE
                    glow_color = (100, 255, 150, 80)
            else:
                # [LOCKED] LOCKED LEVEL - Gradient xám sang trọng
                base_colors = [(40, 40, 45), (60, 60, 65)]
                border_colors = [(80, 80, 85), (100, 100, 105)]
                text_color = (120, 120, 120)
                glow_color = (150, 150, 150, 50)
            
            # [MASK] HOVER ANIMATION
            hover_scale = 1.0
            if is_hovered:
                hover_pulse = math.sin(current_time * 0.008) * 0.05 + 0.95
                hover_scale = 1.1 * hover_pulse
                # Làm sáng màu khi hover
                base_colors = [(min(255, c[0] + 30), min(255, c[1] + 30), min(255, c[2] + 30)) for c in base_colors]
                border_colors = [(min(255, c[0] + 40), min(255, c[1] + 40), min(255, c[2] + 40)) for c in border_colors]
            
            # [RULER] Tính toán kích thước với scale
            scaled_size = int(button_size * hover_scale)
            scaled_rect = pygame.Rect(
                x + (button_size - scaled_size) // 2,
                y + (button_size - scaled_size) // 2,
                scaled_size, scaled_size
            )
            
            # * GLOW EFFECT phía sau
            if level <= max_level:
                glow_size = scaled_size + 8
                glow_rect = pygame.Rect(
                    scaled_rect.x - 4, scaled_rect.y - 4,
                    glow_size, glow_size
                )
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                glow_surf.fill(glow_color)
                self.screen.blit(glow_surf, glow_rect)
            
            # [ART] GRADIENT BUTTON với shadow
            shadow_rect = scaled_rect.move(3, 3)
            shadow_surf = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 100))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Vẽ gradient background
            self._draw_gradient_rect(scaled_rect, base_colors[0], base_colors[1], 12)
            
            # [DIAMOND] PREMIUM BORDER với gradient
            for border_width in range(3, 0, -1):
                border_alpha = 255 - (3 - border_width) * 60
                border_color = border_colors[border_width - 1] if border_width <= len(border_colors) else border_colors[-1]
                pygame.draw.rect(self.screen, (*border_color, border_alpha)[:3], scaled_rect, width=border_width, border_radius=12)
            
            # [CROWN] BOSS CROWN ICON với animation
            if is_boss_level and level <= max_level:
                crown_pulse = math.sin(current_time * 0.005) * 0.2 + 0.8
                crown_font_size = int(24 * crown_pulse)
                crown_font = self._get_font(crown_font_size, bold=True)
                crown_text = "BOSS"
                crown_surf = crown_font.render(crown_text, True, (255, 215, 0))
                crown_rect = crown_surf.get_rect()
                crown_rect.topright = (scaled_rect.right - 3, scaled_rect.top + 3)
                
                # Crown glow effect
                glow_crown = crown_font.render(crown_text, True, (255, 255, 150))
                for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    glow_rect = crown_rect.move(offset[0], offset[1])
                    self.screen.blit(glow_crown, glow_rect)
                
                self.screen.blit(crown_surf, crown_rect)
            
            # [UNLOCKED] LOCK ICON cho levels chưa mở
            if level > max_level:
                lock_font = self._get_font(16, bold=True)
                lock_text = "LOCKED"
                lock_surf = lock_font.render(lock_text, True, (100, 100, 100))
                lock_rect = lock_surf.get_rect(center=(scaled_rect.centerx, scaled_rect.centery - 5))
                self.screen.blit(lock_surf, lock_rect)
            
            # [NUMBER] LEVEL NUMBER với typography siêu đẹp
            if level <= max_level:
                # Multiple text layers for depth
                number_font = self._get_font(int(36 * hover_scale), bold=True)
                level_text = str(level)
                
                # Text shadow
                shadow_surf = number_font.render(level_text, True, (0, 0, 0))
                shadow_rect = shadow_surf.get_rect(center=(scaled_rect.centerx + 2, scaled_rect.centery + 2))
                self.screen.blit(shadow_surf, shadow_rect)
                
                # Main text
                text_surf = number_font.render(level_text, True, text_color)
                text_rect = text_surf.get_rect(center=scaled_rect.center)
                self.screen.blit(text_surf, text_rect)
                
                # Text glow for boss levels
                if is_boss_level:
                    glow_surf = number_font.render(level_text, True, (255, 255, 200))
                    for glow_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        glow_rect = text_rect.move(glow_offset[0], glow_offset[1])
                        self.screen.blit(glow_surf, glow_rect)
            
            # SIÊU ĐẸP STARS SYSTEM với animation
            if level <= max_level and level < max_level:  # Chỉ show stars cho completed levels
                # Lấy số sao của level này
                level_key = f"{current_mode}_L{level}"
                if self.current_user and self.current_user in self.accounts:
                    account = self.accounts[self.current_user]
                    level_stars_data = account.get("level_stars", {})
                else:
                    level_stars_data = self.save.get("level_stars", {})
                
                earned_stars = level_stars_data.get(level_key, 0)
                
                # Vẽ 3 sao siêu đẹp với animation
                star_base_y = scaled_rect.bottom - 15
                star_spacing = 16
                star_start_x = scaled_rect.centerx - star_spacing
                
                for i in range(3):
                    star_x = star_start_x + i * star_spacing
                    star_y = star_base_y
                    
                    if i < earned_stars:
                        # EARNED STAR với pulse animation
                        star_pulse = math.sin(current_time * 0.008 + i * 0.5) * 0.15 + 0.85
                        star_size = int(7 * star_pulse)
                        
                        # Star glow
                        glow_surf = pygame.Surface((star_size * 3, star_size * 3), pygame.SRCALPHA)
                        glow_color = (255, 215, 0, 100)
                        pygame.draw.circle(glow_surf, glow_color, (star_size * 3 // 2, star_size * 3 // 2), star_size * 3 // 2)
                        self.screen.blit(glow_surf, (star_x - star_size, star_y - star_size))
                        
                        # Main star
                        self._draw_star(star_x, star_y, star_size, (255, 215, 0))
                        
                        # Star sparkle
                        sparkle_alpha = int(100 + math.sin(current_time * 0.01 + i) * 50)
                        sparkle_surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                        sparkle_surf.fill((255, 255, 255, sparkle_alpha))
                        self.screen.blit(sparkle_surf, (star_x + random.randint(-3, 3), star_y + random.randint(-3, 3)))
                    else:
                        # ☆ UNEARNED STAR - mờ và nhỏ hơn
                        self._draw_star(star_x, star_y, 5, (80, 80, 80))
                # Store the rect used for this level (use scaled_rect so click area matches hover visuals)
                try:
                    self._level_rects[str(level)] = scaled_rect.copy()
                except Exception:
                    self._level_rects[str(level)] = pygame.Rect(scaled_rect.x, scaled_rect.y, scaled_rect.w, scaled_rect.h)
        
    # [TARGET] SIÊU ĐẸP BACK BUTTON với animation
        back_button_rect = pygame.Rect(50, HEIGHT - 100, 150, 55)
        mx, my = pygame.mouse.get_pos()
        is_back_hovered = back_button_rect.collidepoint((mx, my))
        
        # Back button animation
        if is_back_hovered:
            button_scale = 1.05
            back_colors = [(180, 60, 60), (220, 100, 100)]
            border_color = (255, 150, 100)
        else:
            button_scale = 1.0
            back_colors = [(120, 40, 40), (160, 70, 70)]
            border_color = (200, 100, 100)
        
        # Scaled button
        scaled_back_size = (int(back_button_rect.width * button_scale), int(back_button_rect.height * button_scale))
        scaled_back_rect = pygame.Rect(
            back_button_rect.x + (back_button_rect.width - scaled_back_size[0]) // 2,
            back_button_rect.y + (back_button_rect.height - scaled_back_size[1]) // 2,
            *scaled_back_size
        )
        
        # Button shadow
        shadow_rect = scaled_back_rect.move(3, 3)
        shadow_surf = pygame.Surface(scaled_back_size, pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 120))
        self.screen.blit(shadow_surf, shadow_rect)
        
        # Gradient button
        self._draw_gradient_rect(scaled_back_rect, back_colors[0], back_colors[1], 12)
        
        # Button border
        pygame.draw.rect(self.screen, border_color, scaled_back_rect, width=3, border_radius=12)
        
        # Button text với shadow
        back_font = self._get_font(18, bold=True)
        back_text = "← Trở về"
        text_shadow = back_font.render(back_text, True, (0, 0, 0))
        text_main = back_font.render(back_text, True, WHITE)
        
        text_rect = text_main.get_rect(center=scaled_back_rect.center)
        shadow_rect = text_rect.move(1, 1)
        
        self.screen.blit(text_shadow, shadow_rect)
        self.screen.blit(text_main, text_rect)
        # Store back button rect for event handling
        try:
            self._level_rects["_back"] = scaled_back_rect.copy()
        except Exception:
            self._level_rects["_back"] = pygame.Rect(scaled_back_rect.x, scaled_back_rect.y, scaled_back_rect.w, scaled_back_rect.h)
        
        # [TARGET] ELEGANT HELP SECTION
        help_y = start_y + rows * (button_size + gap) + 40
        help_panel_rect = pygame.Rect(50, help_y - 10, WIDTH - 100, 70)
        
        # Subtle help background
        help_surf = pygame.Surface((help_panel_rect.width, help_panel_rect.height), pygame.SRCALPHA)
        help_surf.fill((0, 0, 0, 30))
        self.screen.blit(help_surf, help_panel_rect)
        
        # Help text với modern styling
        help_font = self._get_font(16)
        help_texts = [
            ("Click level để chơi", (100, 200, 255)),
            ("ESC hoặc nút Trở về: Quay về menu", (200, 200, 200))
        ]
        
        for i, (text, color) in enumerate(help_texts):
            text_surf = help_font.render(text, True, color)
            
            y_pos = help_y + i * 25
            self.screen.blit(text_surf, (60, y_pos))
        
        # Permanent map button (nổi bật)
        try:
            perm_level = PERMANENT_MAP_LEVEL
        except Exception:
            perm_level = None

        if perm_level is not None:
            perm_btn_w, perm_btn_h = 180, 46
            perm_btn_x = WIDTH - perm_btn_w - 50
            perm_btn_y = 140
            perm_rect = pygame.Rect(perm_btn_x, perm_btn_y, perm_btn_w, perm_btn_h)

            # Highlight style
            pygame.draw.rect(self.screen, (40, 90, 160), perm_rect, border_radius=12)
            pygame.draw.rect(self.screen, (100, 170, 255), perm_rect, width=3, border_radius=12)
            perm_font = self._get_font(16, bold=True)
            perm_text = f"PERMANENT MAP"
            t = perm_font.render(perm_text, True, WHITE)
            self.screen.blit(t, t.get_rect(center=perm_rect.center))

            # Store rect so click handler can start it
            if not hasattr(self, '_level_rects') or self._level_rects is None:
                self._level_rects = {}
            # use key equal to the special level number string so handler picks it up
            self._level_rects[str(perm_level)] = perm_rect
        
        # ✨ PREVIEW MAP PANEL - Hiển thị khi đã chọn level
        if hasattr(self, 'selected_level_preview') and self.selected_level_preview:
            self._draw_map_preview_panel()
    
    def _draw_map_preview_panel(self):
        """Vẽ panel preview map ở giữa màn hình."""
        # Panel background - ở giữa màn hình, kéo xuống một chút
        panel_width = 650
        panel_height = 500
        panel_rect = pygame.Rect(
            (WIDTH - panel_width) // 2,
            (HEIGHT - panel_height) // 2 + 120,  # Kéo xuống 50px
            panel_width,
            panel_height
        )
        
        # Background đen đặc để che hoàn toàn phía sau
        panel_surf = pygame.Surface((panel_rect.width, panel_rect.height))
        panel_surf.fill((15, 20, 30))  # Màu đen xanh đậm
        self.screen.blit(panel_surf, panel_rect)
        
        # Border
        pygame.draw.rect(self.screen, (100, 150, 200), panel_rect, width=3, border_radius=15)
        
        # Title
        title_font = self._get_font(20, bold=True)
        title_text = f"LEVEL {self.selected_level_preview} - {self.selected_mode_preview}"
        title_surf = title_font.render(title_text, True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(panel_rect.centerx, panel_rect.y + 25))
        self.screen.blit(title_surf, title_rect)
        
        # Tính toán để căn giữa toàn bộ nội dung (map + legend)
        preview_size = 320
        legend_width = 200
        total_content_width = preview_size + 20 + legend_width  # map + gap + legend
        
        # Bắt đầu từ giữa panel
        content_start_x = panel_rect.centerx - total_content_width // 2
        
        # Map preview - vẽ map nhỏ
        preview_y = panel_rect.y + 60
        preview_x = content_start_x
        preview_rect = pygame.Rect(preview_x, preview_y, preview_size, preview_size)
        
        # Vẽ map preview đơn giản
        self._draw_mini_map_preview(preview_rect, self.selected_level_preview)
        
        # ❌ ẨN Chú thích và Quy luật khi xem PERMANENT MAP (level 999)
        if self.selected_level_preview != 999:
            # Vẽ chú thích bên cạnh map
            legend_x = preview_rect.right + 20
            legend_y = preview_rect.y
            legend_font = self._get_font(14)
            legend_title_font = self._get_font(16, bold=True)
            
            # Title chú thích
            legend_title = legend_title_font.render("Chú thích:", True, (255, 255, 255))
            self.screen.blit(legend_title, (legend_x, legend_y))
            legend_y += 35
            
            # Các mục chú thích với ô màu
            legends = [
                ((60, 130, 70), "Cỏ"),
                ((200, 170, 120), "Đường đi"),
                ((100, 200, 120), "Ô đặt trụ")
            ]
            
            for color, text in legends:
                # Vẽ ô màu
                color_rect = pygame.Rect(legend_x, legend_y, 25, 25)
                pygame.draw.rect(self.screen, color, color_rect)
                pygame.draw.rect(self.screen, (200, 200, 200), color_rect, 1)
                
                # Vẽ text
                text_surf = legend_font.render(text, True, WHITE)
                self.screen.blit(text_surf, (legend_x + 35, legend_y + 3))
                legend_y += 35
            
            # Quy luật về số đường
            legend_y += 20
            rule_title = legend_title_font.render("Quy luật:", True, (255, 200, 100))
            self.screen.blit(rule_title, (legend_x, legend_y))
            legend_y += 30
            
            rules = [
                "Lv 1-3: 1 đường",
                "Lv 4-6: 2 đường",
                "Lv 7-9: 3 đường",
                "Lv 10+: 4 đường"
            ]
            
            rule_font = self._get_font(12)
            for rule in rules:
                rule_surf = rule_font.render(rule, True, (220, 220, 220))
                self.screen.blit(rule_surf, (legend_x, legend_y))
                legend_y += 24
            
            # Ghi chú nhỏ
            legend_y += 10
            note_font = self._get_font(11)
            note1 = note_font.render("---", True, (150, 150, 150))
            self.screen.blit(note1, (legend_x, legend_y))
            legend_y += 20
            note2 = note_font.render("Trụ cách nhau 2-4 ô", True, (150, 150, 150))
            self.screen.blit(note2, (legend_x, legend_y))
            legend_y += 18
            note3 = note_font.render("Chỉ đặt ở ô xanh", True, (150, 150, 150))
            self.screen.blit(note3, (legend_x, legend_y))
        
        # Buttons - Chơi và Hủy
        button_y = preview_rect.bottom + 30
        button_width = 120
        button_height = 45
        button_gap = 20
        
        # Nút "CHƠI"
        play_button_rect = pygame.Rect(
            panel_rect.centerx - button_width - button_gap // 2,
            button_y,
            button_width,
            button_height
        )
        
        mx, my = pygame.mouse.get_pos()
        is_play_hovered = play_button_rect.collidepoint((mx, my))
        
        play_color = (60, 180, 100) if is_play_hovered else (40, 140, 80)
        pygame.draw.rect(self.screen, play_color, play_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, (100, 255, 150), play_button_rect, width=2, border_radius=10)
        
        play_font = self._get_font(18, bold=True)
        play_text = play_font.render("CHƠI", True, WHITE)
        play_text_rect = play_text.get_rect(center=play_button_rect.center)
        self.screen.blit(play_text, play_text_rect)
        
        # Nút "HỦY"
        cancel_button_rect = pygame.Rect(
            panel_rect.centerx + button_gap // 2,
            button_y,
            button_width,
            button_height
        )
        
        is_cancel_hovered = cancel_button_rect.collidepoint((mx, my))
        
        cancel_color = (180, 60, 60) if is_cancel_hovered else (140, 40, 40)
        pygame.draw.rect(self.screen, cancel_color, cancel_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 100, 100), cancel_button_rect, width=2, border_radius=10)
        
        cancel_text = play_font.render("HỦY", True, WHITE)
        cancel_text_rect = cancel_text.get_rect(center=cancel_button_rect.center)
        self.screen.blit(cancel_text, cancel_text_rect)
        
        # Lưu rects để xử lý click
        if not hasattr(self, '_preview_rects'):
            self._preview_rects = {}
        self._preview_rects['play'] = play_button_rect
        self._preview_rects['cancel'] = cancel_button_rect
    
    def _draw_mini_map_preview(self, rect, level):
        """Vẽ preview map nhỏ trong rect với style giống game thật, bao gồm decorations."""
        # Lấy map data cho level này
        try:
            # Load đúng map cho permanent map (level 999)
            if level == 999:
                map_data = make_permanent_map()
            else:
                map_data = make_map(level)
            if not map_data:
                map_data = [[(0, 0), (GRID_W-1, GRID_H-1)]]
            
            tile_w = rect.width / GRID_W
            tile_h = rect.height / GRID_H
            
            # Tạo set các ô là path
            path_tiles = expand_path_cells(map_data)
            
            # Tạo temporary game object để generate tower slots và decorations
            class TempGame:
                def __init__(self):
                    self.level = level
                    self.path_cells = path_tiles
                    self.paths_grid = map_data
            
            temp_game = TempGame()
            
            # Tạo tower slots và decorations giống game thật
            tower_slots = self._generate_tower_slots_preview(temp_game)
            decorations = self._generate_decorative_objects_preview(temp_game)
            
            # Tạo set decorations để dễ kiểm tra
            decoration_set = set(decorations)
            
            # Vẽ từng ô
            for gy in range(GRID_H):
                for gx in range(GRID_W):
                    px = rect.x + int(gx * tile_w)
                    py = rect.y + int(gy * tile_h)
                    tile_rect = pygame.Rect(px, py, int(tile_w)+1, int(tile_h)+1)
                    
                    if (gx, gy) in path_tiles:
                        # Đường đi - màu vàng cát
                        color = (200, 170, 120)
                    elif (gx, gy) in tower_slots:
                        # Ô đặt trụ - màu xanh lá sáng
                        color = (100, 200, 120)
                    else:
                        # Cỏ thường - màu xanh (bỏ decoration, chỉ giữ cỏ đồng nhất)
                        color = (60, 130, 70)
                    
                    pygame.draw.rect(self.screen, color, tile_rect)
                    
                    # Vẽ border nhẹ cho mỗi ô
                    pygame.draw.rect(self.screen, (50, 110, 60), tile_rect, 1)
            
            # Vẽ exit gates (các ô xanh lục ở bên phải)
            exit_positions = set()
            for path in map_data:
                end_x, end_y = path[-1]
                if end_x == GRID_W:  # Exit ở bên phải
                    gate_x = GRID_W - 1
                    gate_y = max(0, min(GRID_H-1, end_y))
                    exit_positions.add((gate_x, gate_y))
            
            for (ex, ey) in exit_positions:
                px = rect.x + int(ex * tile_w)
                py = rect.y + int(ey * tile_h)
                tile_rect = pygame.Rect(px, py, int(tile_w)+1, int(tile_h)+1)
                # Vẽ gate màu xanh lục sáng
                pygame.draw.rect(self.screen, (50, 255, 150), tile_rect)
                pygame.draw.rect(self.screen, (30, 200, 120), tile_rect, 1)
            
        except Exception as e:
            # Fallback - chỉ hiển thị text
            pygame.draw.rect(self.screen, (60, 120, 60), rect)
            font = self._get_font(14)
            text = font.render(f"Level {level}", True, WHITE)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
        
        # Border ngoài
        pygame.draw.rect(self.screen, (40, 40, 50), rect, width=2)
    
    def _draw_star(self, x, y, size, color):
        """Vẽ ngôi sao 5 cánh."""
        import math
        points = []
        for i in range(10):
            angle = math.pi * i / 5
            if i % 2 == 0:
                # Điểm ngoài
                px = x + size * math.cos(angle - math.pi/2)
                py = y + size * math.sin(angle - math.pi/2)
            else:
                # Điểm trong
                px = x + size * 0.5 * math.cos(angle - math.pi/2)
                py = y + size * 0.5 * math.sin(angle - math.pi/2)
            points.append((px, py))
        
        pygame.draw.polygon(self.screen, color, points)

    def _draw_enhanced_background(self):
        """Vẽ nền đẹp cho game area với texture rõ ràng."""
        # Chọn màu nền dựa trên level
        level = self.level
        
        # Permanent Map sử dụng Snow theme
        if getattr(self, 'is_permanent_map', False):
            # Snow theme cho Permanent Map
            base_color = (240, 245, 255)    # Trắng tuyết sáng
            dark_color = (220, 225, 235)    # Xám nhạt 
            light_color = (255, 255, 255)   # Trắng tinh khiết
        elif level <= 3:
            # Theme cỏ xanh với pattern rõ ràng hơn
            base_color = (45, 120, 60)
            dark_color = (35, 90, 45)
            light_color = (60, 140, 80)
        elif level <= 6:
            # Theme sa mạc
            base_color = (140, 115, 80)
            dark_color = (120, 95, 65)
            light_color = (160, 135, 95)
        elif level <= 9:
            # Theme tuyết
            base_color = (180, 190, 200)
            dark_color = (160, 170, 180)
            light_color = (200, 210, 220)
        else:
            # Theme lava
            base_color = (90, 45, 35)
            dark_color = (70, 30, 20)
            light_color = (110, 60, 45)
        
        # Tạo nền cho game area
        game_area = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)
        pygame.draw.rect(self.screen, base_color, game_area)
        
        # Thêm pattern kẻ ô để tạo texture rõ ràng
        for gx in range(GRID_W):
            for gy in range(GRID_H):
                x, y = gx * TILE, gy * TILE
                # Tạo pattern checkerboard nhẹ
                if (gx + gy) % 2 == 0:
                    # Ô sáng hơn một chút
                    overlay = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                    overlay.fill((*light_color, 30))  # Alpha 30 để tạo hiệu ứng nhẹ
                    self.screen.blit(overlay, (x, y))
                else:
                    # Ô tối hơn một chút
                    overlay = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                    overlay.fill((*dark_color, 30))  # Alpha 30 để tạo hiệu ứng nhẹ
                    self.screen.blit(overlay, (x, y))
        
        # Thêm một số điểm nhấn random để tăng tính tự nhiên
        import random
        random.seed(level * 42)  # Seed cố định cho level
        
        for _ in range(20):
            x = random.randint(0, GAME_WIDTH - 32)
            y = random.randint(0, GAME_HEIGHT - 32)
            size = random.randint(12, 24)
            
            # Vẽ các vòng tròn với alpha rõ ràng hơn
            dot_surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            color_with_alpha = (*dark_color, 80)  # Alpha cao hơn để rõ ràng
            pygame.draw.circle(dot_surf, color_with_alpha, (size, size), size)
            self.screen.blit(dot_surf, (x, y))

    # ---- Trong game ----
    def draw_game(self):
        # 1) Ưu tiên sử dụng ảnh nền, fallback về texture nền
        if hasattr(self, "map_bg") and self.map_bg:
            # Có ảnh nền → sử dụng ảnh
            self.screen.blit(self.map_bg, (0, 0))
        else:
            # Không có ảnh → sử dụng nền texture đẹp
            self._draw_enhanced_background()
        
        # Nền cho khu vực UI - màu đẹp hơn, ít đen hơn
        ui_bg_color = (40, 45, 55)  # Xanh xám nhẹ thay vì đen
        pygame.draw.rect(self.screen, ui_bg_color, (GAME_WIDTH, 0, WIDTH-GAME_WIDTH, HEIGHT))  # Panel phải
        pygame.draw.rect(self.screen, ui_bg_color, (0, GAME_HEIGHT, GAME_WIDTH, HEIGHT-GAME_HEIGHT))  # Panel dưới
        
        # Thêm gradient subtile cho UI area
        for i in range(5):
            alpha = 10 - i * 2
            gradient_color = (ui_bg_color[0] + i, ui_bg_color[1] + i, ui_bg_color[2] + i)
            pygame.draw.rect(self.screen, gradient_color, (GAME_WIDTH + i, i, WIDTH-GAME_WIDTH - 2*i, HEIGHT - 2*i))
        # 2) Vẽ tiles/đường/decor...
        if hasattr(self, "_draw_tiles_autotile"):
            self._draw_tiles_autotile()
        else:
            self.draw_grid()
        if hasattr(self, "_draw_decor_and_markers"):
            self._draw_decor_and_markers()

        # 3) Objects & UI
        self.draw_projectiles()
        self.draw_enemies()
        self.draw_death_effects()  # Vẽ hiệu ứng chết
        self.draw_damage_texts()   # Vẽ text sát thương
        self.draw_range_circles()  # Vẽ tầm bắn tower
        self.draw_placement_preview()  # Vẽ preview khi đặt tower
        self.draw_towers()
        
        # Vẽ thanh đếm ngược setup phase
        if self.in_setup_phase:
            self.draw_setup_countdown()
        
        # 4) Vẽ đường viền tách game area và UI area
        pygame.draw.line(self.screen, WHITE, (GAME_WIDTH, 0), (GAME_WIDTH, HEIGHT), 2)  # Đường dọc
        pygame.draw.line(self.screen, WHITE, (0, GAME_HEIGHT), (WIDTH, GAME_HEIGHT), 2)  # Đường ngang
        
        self.draw_hud()

        if self.paused or self.lives <= 0 or self.win_level:
            self.draw_overlay()



    def draw_grid(self):
        # nền cỏ - chỉ vẽ ở các vị trí tower slots
        tower_slot_positions = getattr(self, 'tower_slots', set())
            
        if hasattr(self, "tiles") and self.tiles and self.tiles.get("grass"):
            grass = self.tiles["grass"]
            if grass:  # Kiểm tra grass không None
                for gx in range(GRID_W):
                    for gy in range(GRID_H):
                        if (gx, gy) in tower_slot_positions:
                            self.screen.blit(grass, (gx*TILE, gy*TILE))
            # Nếu không có grass tile, không cần fill màu nền vì chỉ vẽ ở tower slots
        # Không fill toàn bộ màn hình nữa
            
        # đường cát (nếu có tiles)
        if hasattr(self, "tiles") and self.tiles and self.tiles.get("sand_center"):
            center = self.tiles["sand_center"]
            edge = {"n": self.tiles.get("sand_edge_n"),"s": self.tiles.get("sand_edge_s"),
                    "w": self.tiles.get("sand_edge_w"),"e": self.tiles.get("sand_edge_e")}
            corner = {"ne": self.tiles.get("sand_corner_ne"),"nw": self.tiles.get("sand_corner_nw"),
                      "se": self.tiles.get("sand_corner_se"),"sw": self.tiles.get("sand_corner_sw")}
            for (gx, gy) in self.path_cells:
                x, y = gx*TILE, gy*TILE
                if center:  # Kiểm tra center không None
                    self.screen.blit(center, (x, y))
                n, s, w, e = self._neighbors_mask_tuple(gx, gy)
                if not n and edge["n"]: self.screen.blit(edge["n"], (x, y))
                if not s and edge["s"]: self.screen.blit(edge["s"], (x, y))
                if not w and edge["w"]: self.screen.blit(edge["w"], (x, y))
                if not e and edge["e"]: self.screen.blit(edge["e"], (x, y))
                if not n and not e and corner["ne"]: self.screen.blit(corner["ne"], (x, y))
                if not n and not w and corner["nw"]: self.screen.blit(corner["nw"], (x, y))
                if not s and not e and corner["se"]: self.screen.blit(corner["se"], (x, y))
                if not s and not w and corner["sw"]: self.screen.blit(corner["sw"], (x, y))
        else:
            for (gx, gy) in self.path_cells:
                rect = pygame.Rect(gx*TILE, gy*TILE, TILE, TILE); pygame.draw.rect(self.screen, SAND, rect)
        
        # Vẽ decorative objects trước
        if hasattr(self, 'decorative_objects'):
            for decoration in self.decorative_objects:
                self._draw_decoration(decoration)

        # Hiển thị grid placement indicators (vẽ sau decorations để không bị che)
        if getattr(self, 'show_placement_grid', True):
            decoration_positions = set()
            if hasattr(self, 'decorative_objects'):
                decoration_positions = {decoration["pos"] for decoration in self.decorative_objects}
                
            # Vẽ indicators cho tất cả các ô
            for gx in range(GRID_W):
                for gy in range(GRID_H):
                    cell = (gx, gy)
                    
                    # Kiểm tra trạng thái của ô
                    if cell in self.path_cells:
                        # Ô đường đi - không vẽ gì (đã có sand tiles)
                        continue
                    elif cell in decoration_positions:
                        # Ô có decoration - không vẽ indicator
                        continue
                    elif hasattr(self, 'tower_slots') and cell in self.tower_slots:
                        if cell in self.occupied:
                            # Ô có tower - viền xanh đậm mạnh
                            rect = pygame.Rect(gx*TILE + 1, gy*TILE + 1, TILE-2, TILE-2)
                            pygame.draw.rect(self.screen, (0, 200, 0), rect, width=4, border_radius=8)
                        else:
                            # Ô có thể đặt tower - nền xanh sáng + viền đậm + dấu "+"
                            rect = pygame.Rect(gx*TILE + 3, gy*TILE + 3, TILE-6, TILE-6)
                            # pygame.draw.rect(self.screen, (120, 255, 120, 120), rect, border_radius=8)  # T?t n?n xanh
                            # pygame.draw.rect(self.screen, (0, 180, 0), rect, width=3, border_radius=8)  # T?t vi?n xanh
                            
                            # Dấu "+" lớn hơn và rõ hơn
                            center_x = gx*TILE + TILE//2
                            center_y = gy*TILE + TILE//2
                            # Dấu + trắng với viền đen để nổi bật
                            for offset in [(0,0), (-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
                                x_off, y_off = offset
                                pygame.draw.line(self.screen, (0, 0, 0), 
                                               (center_x - 12 + x_off, center_y + y_off), 
                                               (center_x + 12 + x_off, center_y + y_off), 3)
                                pygame.draw.line(self.screen, (0, 0, 0), 
                                               (center_x + x_off, center_y - 12 + y_off), 
                                               (center_x + x_off, center_y + 12 + y_off), 3)
                            # Dấu + trắng chính
                            pygame.draw.line(self.screen, (255, 255, 255), 
                                           (center_x - 12, center_y), (center_x + 12, center_y), 3)
                            pygame.draw.line(self.screen, (255, 255, 255), 
                                           (center_x, center_y - 12), (center_x, center_y + 12), 3)
                    # else: Ô không thể đặt tower - để trống cho decorations tùy chỉnh
        
        # lưới
        grid_color = (35,65,35) if (hasattr(self,"tiles") and self.tiles) else DARK
        for x in range(GRID_W + 1): pygame.draw.line(self.screen, grid_color, (x*TILE, 0), (x*TILE, HEIGHT))
        for y in range(GRID_H + 1): pygame.draw.line(self.screen, grid_color, (0, y*TILE), (WIDTH, y*TILE))
    
    def _draw_decoration(self, decoration):
        """Vẽ một decoration object - ưu tiên sử dụng ảnh, fallback về vẽ hình học."""
        gx, gy = decoration["pos"]
        dec_type = decoration["type"]
        color = decoration["color"]
        size_type = decoration["size"]
        offset_x, offset_y = decoration["offset"]
        
        # Tính toán vị trí và kích thước
        base_x = gx * TILE + TILE // 2 + offset_x
        base_y = gy * TILE + TILE // 2 + offset_y
        
        # Vẽ shadow rất nhẹ (chỉ cho decorations lớn)
        if decoration["size"] in ["medium", "large"]:
            shadow_color = (0, 0, 0, 25)  # Shadow nhẹ hơn
            shadow_surf = pygame.Surface((24, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, shadow_color, (0, 0, 24, 6))
            self.screen.blit(shadow_surf, (base_x - 12, base_y + 8))
        
        # Kiểm tra có ảnh decoration không
        sprite = self.decoration_sprites.get(dec_type) if hasattr(self, 'decoration_sprites') else None
        
        if sprite:
            # Sử dụng ảnh decoration
            sprite_rect = sprite.get_rect(center=(base_x, base_y))
            self.screen.blit(sprite, sprite_rect)
        else:
            # Fallback: Vẽ hình học như cũ
            if size_type == "small":
                size = 16
            elif size_type == "medium":
                size = 24
            else:  # large
                size = 32
                
            # Vẽ decoration dựa trên type (code cũ)
            if dec_type == "broken_tower":
                # Tháp vỡ - hình chữ nhật với crack
                rect = pygame.Rect(base_x - size//2, base_y - size//2, size, size)
                pygame.draw.rect(self.screen, color, rect, border_radius=4)
                pygame.draw.rect(self.screen, (color[0]-20, color[1]-20, color[2]-20), rect, width=2, border_radius=4)
                # Crack
                pygame.draw.line(self.screen, (60, 40, 30), (base_x - size//4, base_y - size//2), 
                               (base_x + size//4, base_y + size//2), 2)
                
            elif dec_type == "dead_tree":
                # Cây chết - thân + cành
                pygame.draw.circle(self.screen, color, (base_x, base_y), size//3)
                pygame.draw.line(self.screen, color, (base_x, base_y - size//2), (base_x, base_y + size//2), 3)
                pygame.draw.line(self.screen, color, (base_x, base_y - size//4), (base_x - size//3, base_y - size//2), 2)
                pygame.draw.line(self.screen, color, (base_x, base_y - size//4), (base_x + size//3, base_y - size//2), 2)
                
            elif dec_type == "rocks":
                # Đá - nhiều hình tròn chồng lên nhau
                for i in range(3):
                    offset = (i-1) * size//6
                    rock_size = size//2 + (i % 2) * 4
                    pygame.draw.circle(self.screen, (color[0] + offset, color[1] + offset, color[2] + offset), 
                                     (base_x + offset, base_y + offset), rock_size//2)
                                     
            elif dec_type == "thorns":
                # Gai - tam giác nhọn
                points = [
                    (base_x, base_y - size//2),
                    (base_x - size//3, base_y + size//2),
                    (base_x + size//3, base_y + size//2)
                ]
                pygame.draw.polygon(self.screen, color, points)
                pygame.draw.polygon(self.screen, (color[0]-20, color[1]-20, color[2]-20), points, 2)
                
            elif dec_type == "ruins":
                # Tàn tích - hình vuông với hole
                outer_rect = pygame.Rect(base_x - size//2, base_y - size//2, size, size)
                inner_rect = pygame.Rect(base_x - size//4, base_y - size//4, size//2, size//2)
                pygame.draw.rect(self.screen, color, outer_rect, border_radius=2)
                pygame.draw.rect(self.screen, (20, 20, 20), inner_rect, border_radius=2)
                
            elif dec_type == "crystal":
                # Pha lê - kim cương
                points = [
                    (base_x, base_y - size//2),
                    (base_x - size//3, base_y),
                    (base_x, base_y + size//2),
                    (base_x + size//3, base_y)
                ]
                pygame.draw.polygon(self.screen, color, points)
                pygame.draw.polygon(self.screen, (255, 255, 255), points, 1)
                
            elif dec_type == "bones":
                # Xương - chữ X
                pygame.draw.line(self.screen, color, (base_x - size//2, base_y - size//2), 
                               (base_x + size//2, base_y + size//2), 3)
                pygame.draw.line(self.screen, color, (base_x + size//2, base_y - size//2), 
                               (base_x - size//2, base_y + size//2), 3)

    def draw_enemies(self):
        # Enhanced enemy rendering với sprites và tên
        for e in self.enemies:
            x, y = e.pos()
            
            # Tính alpha để fade out khi enemy thoát khỏi map
            alpha = 1.0
            if x > GAME_WIDTH:  # Nếu enemy đã ra ngoài map
                fade_distance = x - GAME_WIDTH
                max_fade = 64  # Fade trong 64px
                alpha = max(0.0, 1.0 - (fade_distance / max_fade))
                if alpha <= 0:
                    continue  # Không vẽ nếu hoàn toàn trong suốt
            
            # Chọn sprite phù hợp
            enemy_img = self.enemy_sprites.get(e.etype)
            if enemy_img:
                # Rotate sprite based on movement direction
                if e.idx < len(e.path):
                    tx, ty = e.path[e.idx]
                    angle = -math.degrees(math.atan2(ty - y, tx - x))
                    rotated_img = pygame.transform.rotate(enemy_img, angle)
                else:
                    rotated_img = enemy_img
                
                # Vẽ sprite với kích thước phù hợp
                img_rect = rotated_img.get_rect(center=(int(x), int(y)))
                
                # [FIRE] Boss border highlight với alpha
                if e.etype == "boss" and alpha > 0.1:
                    border_color = (*[int(c * alpha) for c in (255, 215, 0)], int(255 * alpha))
                    border_surf = pygame.Surface((img_rect.width + 10, img_rect.height + 10), pygame.SRCALPHA)
                    pygame.draw.circle(border_surf, border_color, (border_surf.get_width()//2, border_surf.get_height()//2), int(img_rect.width//2 + 5), 3)
                    self.screen.blit(border_surf, (img_rect.x - 5, img_rect.y - 5))
                
                # Áp dụng alpha cho sprite
                if alpha < 1.0:
                    temp_surf = rotated_img.copy()
                    temp_surf.set_alpha(int(255 * alpha))
                    self.screen.blit(temp_surf, img_rect)
                else:
                    self.screen.blit(rotated_img, img_rect)
                
                # Vẽ tên enemy type ở trên đầu với alpha
                if alpha > 0.3:  # Chỉ vẽ tên khi alpha đủ cao
                    enemy_name = ENEMY_TYPES[e.etype]["name"]
                    name_color = ENEMY_TYPES[e.etype]["color"]
                    
                    # [FIRE] Special indicator for BOSS
                    if e.etype == "boss":
                        enemy_name = "[CROWN] BOSS [CROWN]"
                        name_color = (255, 215, 0)  # Gold color
                    
                    # Áp dụng alpha cho màu text
                    alpha_color = (*[int(c * alpha) for c in name_color[:3]], int(255 * alpha))
                    name_surf = pygame.font.Font(None, 16).render(enemy_name, True, name_color)
                    if alpha < 1.0:
                        name_surf.set_alpha(int(255 * alpha))
                    name_rect = name_surf.get_rect(center=(int(x), int(y - img_rect.height//2 - 12)))
                    self.screen.blit(name_surf, name_rect)
                
            else:
                # Fallback: circle với màu sắc và alpha
                color = ENEMY_TYPES[e.etype]["color"]
                base_radius = int(16 * e.size_mul)
                
                if alpha < 1.0:
                    # Vẽ với alpha bằng surface
                    circle_surf = pygame.Surface((base_radius * 2, base_radius * 2), pygame.SRCALPHA)
                    alpha_color = (*color[:3], int(255 * alpha))
                    pygame.draw.circle(circle_surf, alpha_color, (base_radius, base_radius), base_radius)
                    self.screen.blit(circle_surf, (int(x - base_radius), int(y - base_radius)))
                else:
                    pygame.draw.circle(self.screen, color, (int(x), int(y)), base_radius)
                
                # Tên cho fallback với alpha
                if alpha > 0.3:
                    enemy_name = ENEMY_TYPES[e.etype]["name"]
                    name_surf = pygame.font.Font(None, 16).render(enemy_name, True, WHITE)
                    if alpha < 1.0:
                        name_surf.set_alpha(int(255 * alpha))
                    name_rect = name_surf.get_rect(center=(int(x), int(y - base_radius - 12)))
                    self.screen.blit(name_surf, name_rect)
            
            # Thanh máu với màu sắc theo loại và alpha
            if alpha > 0.2:  # Chỉ vẽ thanh máu khi alpha đủ cao
                ratio = max(0.0, e.hp / e.max_hp)
                w, bh = int(30 * e.size_mul), 4
                bar_bg = pygame.Rect(int(x - w/2), int(y - 26 * e.size_mul), w, bh)
                bar_fg = pygame.Rect(int(x - w/2), int(y - 26 * e.size_mul), int(w * ratio), bh)
                
                # Màu thanh máu theo HP ratio với alpha
                if ratio > 0.7:
                    hp_color = GREEN
                elif ratio > 0.3:
                    hp_color = YELLOW
                else:
                    hp_color = RED
                
                if alpha < 1.0:
                    # Vẽ thanh máu với alpha
                    bg_surf = pygame.Surface((w, bh), pygame.SRCALPHA)
                    fg_surf = pygame.Surface((int(w * ratio), bh), pygame.SRCALPHA)
                    
                    dark_alpha = (*DARK[:3], int(255 * alpha))
                    hp_alpha = (*hp_color[:3], int(255 * alpha))
                    
                    bg_surf.fill(dark_alpha)
                    fg_surf.fill(hp_alpha)
                    
                    self.screen.blit(bg_surf, bar_bg.topleft)
                    self.screen.blit(fg_surf, bar_fg.topleft)
                else:
                    pygame.draw.rect(self.screen, DARK, bar_bg)
                    pygame.draw.rect(self.screen, hp_color, bar_fg)
            
            # Hiệu ứng đặc biệt với alpha
            if e.etype == "boss" and e.regen_rate > 0 and alpha > 0.3:
                # Aura cho commander với alpha
                aura_radius = int(20 * e.size_mul)
                base_alpha = int(60 * alpha)
                aura_color = (*ENEMY_TYPES[e.etype]["color"], base_alpha)
                aura_surf = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(aura_surf, aura_color, (aura_radius, aura_radius), aura_radius)
                self.screen.blit(aura_surf, (int(x - aura_radius), int(y - aura_radius)))
            
            # Hiệu ứng Poison DoT với alpha
            if e.poison_timer > 0 and alpha > 0.2:
                self._draw_poison_effect_on_enemy(e, x, y, alpha)

    def draw_towers(self):
        for t in self.towers:
            cx, cy = t.center()
            
            # Hiệu ứng phát sáng cho tower level 2 và 3
            if t.level >= 2:
                self._draw_tower_glow(t, cx, cy)
            
            # Highlight tower được chọn
            if t == self.selected_tower_for_range:
                # Vẽ vòng tròn highlight xung quanh tower
                pygame.draw.circle(self.screen, (255, 255, 100), (int(cx), int(cy)), 30, 3)
                # Hiệu ứng nhấp nháy nhẹ
                pulse = int(128 + 127 * math.sin(time.time() * 4))
                pygame.draw.circle(self.screen, (255, 255, 100, pulse), (int(cx), int(cy)), 25, 2)
            
            base_img = self.tower_sprites.get(t.ttype)
            if base_img:
                angle_deg = -math.degrees(t.angle)
                img = pygame.transform.rotate(base_img, angle_deg)
                rect = img.get_rect(center=(int(cx), int(cy)))
                self.screen.blit(img, rect)
                # --- Huy hiệu cấp ở góc phải-trên của sprite ---
                draw_level_badge(self.screen, rect.right - 10, rect.top + 10, t.level, small=False)
            else:
                pygame.draw.circle(self.screen, BLUE, (int(cx), int(cy)), 18)
                pygame.draw.circle(self.screen, WHITE, (int(cx), int(cy)), 6)
                # Badge cho trường hợp không có sprite
                draw_level_badge(self.screen, int(cx)+18, int(cy)-18, t.level, small=False)
    
    def _draw_tower_glow(self, tower, cx, cy):
        """Vẽ hiệu ứng phát sáng xung quanh tower level 2 và 3."""
        # Tính toán pulse effect
        pulse = abs(math.sin(time.time() * 2)) * 0.3 + 0.7  # 0.7 -> 1.0
        
        # Màu sắc dựa trên level
        if tower.level == 2:
            # Level 2 - Màu xanh dương nhạt
            glow_color = (100, 150, 255)
            radius_base = 35
        else:  # Level 3
            # Level 3 - Màu vàng gold
            glow_color = (255, 215, 0)
            radius_base = 40
        
        # Vẽ nhiều lớp glow với alpha giảm dần
        num_layers = 4
        for i in range(num_layers):
            alpha = int(60 * pulse * (1 - i / num_layers))  # Alpha giảm dần từ ngoài vào
            radius = int(radius_base * pulse * (1 + i * 0.15))
            
            # Tạo surface trong suốt cho glow
            glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*glow_color, alpha), (radius, radius), radius)
            
            # Vẽ lên screen
            self.screen.blit(glow_surf, (int(cx - radius), int(cy - radius)))

    def draw_projectiles(self):
        for p in self.projectiles:
            self._draw_projectile_with_effects(p)
    
    def _draw_projectile_with_effects(self, p):
        """Vẽ projectile với hiệu ứng đặc biệt"""
        x, y = int(p.x), int(p.y)
        
        if p.projectile_type == "basic" or p.projectile_type == "sniper" or p.projectile_type == "minigun":
            # Đạn cơ bản - giữ nguyên
            color = YELLOW if p.splash == 0 else ORANGE
            pygame.draw.circle(self.screen, color, (x, y), 4)
            
        elif p.projectile_type == "laser":
            # [RED] Tia laser - màu đỏ sáng với đuôi và hiệu ứng phát sáng
            self._draw_laser_glow(p, x, y)
            self._draw_trail(p, (255, 50, 50), (255, 150, 150))
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 6)
            pygame.draw.circle(self.screen, (255, 0, 0), (x, y), 4)
            
        elif p.projectile_type == "rocket":
            # [ROCKET] Tên lửa - lớn, màu cam với lửa phía sau và hình dạng thực tế
            self._draw_rocket_trail(p)
            self._draw_rocket_body(p, x, y)
            # Đầu tên lửa (nhọn)
            pygame.draw.circle(self.screen, (255, 100, 0), (x, y), 5)
            
        elif p.projectile_type == "electric":
            # Điện - màu xanh dương với tia điện và hiệu ứng sét
            self._draw_electric_effect(p)
            self._draw_electric_aura(p, x, y)
            pygame.draw.circle(self.screen, (0, 150, 255), (x, y), 5)
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 2)
            
        elif p.projectile_type == "poison":
            # [GREEN] Độc - màu xanh lá với bong bóng
            self._draw_poison_bubbles(p)
            pygame.draw.circle(self.screen, (0, 200, 0), (x, y), 5)
            pygame.draw.circle(self.screen, (100, 255, 100), (x, y), 3)
            
        elif p.projectile_type == "flame":
            # [FIRE] Lửa - màu đỏ cam với hiệu ứng cháy
            self._draw_flame_effect(p)
            
        elif p.projectile_type == "ice":
            # ❄️ Băng - màu xanh nhạt với tinh thể
            self._draw_ice_crystals(p)
            pygame.draw.circle(self.screen, (100, 200, 255), (x, y), 5)
            pygame.draw.circle(self.screen, (200, 230, 255), (x, y), 3)
            
        elif p.projectile_type == "mortar":
            # [BOMB] Cối phá hủy - lớn, màu đen với đuôi khói
            self._draw_mortar_smoke(p)
            pygame.draw.circle(self.screen, (50, 50, 50), (x, y), 8)
            pygame.draw.circle(self.screen, (100, 80, 60), (x, y), 6)
    
    def _draw_trail(self, p, color1, color2):
        """Vẽ đuôi đạn gradient"""
        if not p.trail_points or len(p.trail_points) < 2:
            return
            
        for i in range(len(p.trail_points) - 1):
            x1, y1, t1 = p.trail_points[i]
            x2, y2, t2 = p.trail_points[i + 1]
            
            # Alpha dựa trên thời gian
            alpha = max(0, 1 - (p.lifetime - t1) * 2)
            width = max(1, int(alpha * 8))
            
            if alpha > 0:
                # Blend color
                r = int(color1[0] * alpha + color2[0] * (1 - alpha))
                g = int(color1[1] * alpha + color2[1] * (1 - alpha))
                b = int(color1[2] * alpha + color2[2] * (1 - alpha))
                
                pygame.draw.line(self.screen, (r, g, b), (int(x1), int(y1)), (int(x2), int(y2)), width)
    
    def _draw_rocket_trail(self, p):
        """Vẽ đuôi lửa cho tên lửa"""
        if not p.trail_points:
            return
            
        for i, (x, y, t) in enumerate(p.trail_points):
            age = p.lifetime - t
            if age > 0.5:  # Chỉ vẽ trail gần đây
                continue
                
            alpha = max(0, 1 - age * 2)
            size = int(alpha * 12)
            
            if size > 0:
                # Lửa đỏ cam
                colors = [(255, 100, 0), (255, 200, 0), (255, 255, 100)]
                color_idx = min(2, int(age * 6))
                color = colors[color_idx]
                
                pygame.draw.circle(self.screen, color, (int(x), int(y)), size)
    
    def _draw_electric_effect(self, p):
        """Vẽ hiệu ứng tia điện"""
        x, y = int(p.x), int(p.y)
        
        # Tia điện ngẫu nhiên xung quanh
        for _ in range(3):
            angle = random.uniform(0, math.pi * 2)
            length = random.uniform(10, 25)
            end_x = x + math.cos(angle) * length
            end_y = y + math.sin(angle) * length
            
            pygame.draw.line(self.screen, (100, 150, 255), (x, y), (int(end_x), int(end_y)), 2)
    
    def _draw_poison_bubbles(self, p):
        """Vẽ bong bóng độc"""
        x, y = int(p.x), int(p.y)
        
        # Bong bóng nhỏ xung quanh
        for i in range(2):
            offset_x = random.uniform(-8, 8)
            offset_y = random.uniform(-8, 8)
            bubble_size = random.randint(2, 4)
            
            pygame.draw.circle(self.screen, (0, 255, 100), 
                             (int(x + offset_x), int(y + offset_y)), bubble_size)
    
    def _draw_flame_effect(self, p):
        """Vẽ hiệu ứng lửa sinh động với particles"""
        x, y = int(p.x), int(p.y)
        
        # Lửa chính với nhiều lớp màu và hiệu ứng flicker
        flame_intensity = 0.7 + 0.3 * math.sin(p.lifetime * 10)  # Dao động
        
        colors = [(255, 0, 0), (255, 100, 0), (255, 200, 0)]
        base_sizes = [7, 5, 3]
        
        for i, (color, base_size) in enumerate(zip(colors, base_sizes)):
            # Kích thước dao động theo thời gian
            size = int(base_size * flame_intensity)
            
            # Offset ngẫu nhiên để tạo hiệu ứng lửa bốc
            flicker_range = 3 - i  # Lớp ngoài dao động nhiều hơn
            offset_x = random.uniform(-flicker_range, flicker_range)
            offset_y = random.uniform(-flicker_range, flicker_range)
            
            if size > 0:
                pygame.draw.circle(self.screen, color, (int(x + offset_x), int(y + offset_y)), size)
        
        # Thêm particles lửa bay tung tóe
        if random.random() < 0.4:  # 40% cơ hội tạo particle
            for _ in range(random.randint(1, 3)):
                spark_x = x + random.uniform(-8, 8)
                spark_y = y + random.uniform(-8, 8) 
                spark_color = random.choice([(255, 150, 0), (255, 200, 50), (255, 255, 100)])
                spark_size = random.randint(1, 2)
                pygame.draw.circle(self.screen, spark_color, (int(spark_x), int(spark_y)), spark_size)
    
    def _draw_ice_crystals(self, p):
        """Vẽ tinh thể băng với hiệu ứng lấp lánh"""
        x, y = int(p.x), int(p.y)
        
        # Tinh thể chính - hình sao 6 cánh
        crystal_size = 8 + 2 * math.sin(p.lifetime * 8)  # Pulsing effect
        
        # Vẽ tinh thể bên ngoài
        outer_points = []
        inner_points = []
        for i in range(6):
            angle = i * math.pi / 3 + p.rotation * 0.5  # Xoay chậm
            
            # Điểm ngoài (đầu nhọn)
            outer_x = x + math.cos(angle) * crystal_size
            outer_y = y + math.sin(angle) * crystal_size
            outer_points.append((outer_x, outer_y))
            
            # Điểm trong (chỗ lõm)
            inner_angle = angle + math.pi / 6
            inner_x = x + math.cos(inner_angle) * (crystal_size * 0.5)
            inner_y = y + math.sin(inner_angle) * (crystal_size * 0.5)
            inner_points.append((inner_x, inner_y))
        
        # Tạo hình sao bằng cách nối các điểm
        star_points = []
        for i in range(6):
            star_points.append(outer_points[i])
            star_points.append(inner_points[i])
            
        if len(star_points) >= 6:
            # Vẽ tinh thể với gradient màu
            pygame.draw.polygon(self.screen, (100, 180, 255), star_points)
            pygame.draw.polygon(self.screen, (150, 200, 255), star_points, 2)
        
        # Hiệu ứng lấp lánh xung quanh
        if random.random() < 0.3:  # 30% cơ hội lấp lánh
            for _ in range(random.randint(2, 4)):
                sparkle_x = x + random.uniform(-12, 12)
                sparkle_y = y + random.uniform(-12, 12)
                sparkle_size = random.randint(1, 2)
                pygame.draw.circle(self.screen, (200, 230, 255), (int(sparkle_x), int(sparkle_y)), sparkle_size)
    
    def _draw_mortar_smoke(self, p):
        """Vẽ khói cối phá hủy"""
        if not p.trail_points:
            return
            
        for i, (x, y, t) in enumerate(p.trail_points):
            age = p.lifetime - t
            if age > 1.0:  # Khói tồn tại lâu hơn
                continue
                
            alpha = max(0, 1 - age)
            size = int(alpha * 15 + age * 5)  # Khói lan rộng theo thời gian
            
            if size > 0:
                gray_level = int(100 * alpha)
                pygame.draw.circle(self.screen, (gray_level, gray_level, gray_level), 
                                 (int(x), int(y)), size)
    
    def _draw_laser_glow(self, p, x, y):
        """Vẽ hiệu ứng phát sáng cho laser"""
        # Tạo hiệu ứng glow bằng các vòng tròn trong suốt
        glow_colors = [
            (255, 100, 100, 30),   # Đỏ nhạt
            (255, 150, 150, 20),   # Đỏ rất nhạt
            (255, 200, 200, 10)    # Đỏ cực nhạt
        ]
        glow_sizes = [12, 16, 20]
        
        for color, size in zip(glow_colors, glow_sizes):
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (size, size), size)
            self.screen.blit(surf, (x - size, y - size))
    
    def _draw_electric_aura(self, p, x, y):
        """Vẽ hiệu ứng hào quang điện cho electric projectile"""
        # Vẽ vòng tròn điện xung quanh
        aura_colors = [
            (0, 100, 255, 40),     # Xanh dương nhạt
            (100, 150, 255, 25),   # Xanh dương rất nhạt
            (150, 200, 255, 15)    # Xanh dương cực nhạt
        ]
        aura_sizes = [8, 12, 16]
        
        for color, size in zip(aura_colors, aura_sizes):
            surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (size, size), size)
            self.screen.blit(surf, (x - size, y - size))
            
        # Thêm tia sét nhỏ quanh projectile
        if random.random() < 0.3:  # 30% cơ hội tia sét
            for _ in range(2):
                angle = random.uniform(0, math.pi * 2)
                length = random.uniform(8, 15)
                end_x = x + math.cos(angle) * length
                end_y = y + math.sin(angle) * length
                
                # Vẽ tia sét với độ dày ngẫu nhiên
                thickness = random.randint(1, 2)
                pygame.draw.line(self.screen, (200, 220, 255), (x, y), (int(end_x), int(end_y)), thickness)
    
    def _draw_poison_effect_on_enemy(self, enemy, x, y, alpha=1.0):
        """Vẽ hiệu ứng poison trên enemy"""
        # Tính alpha dựa trên thời gian còn lại của poison và alpha fade-out
        alpha_factor = min(1.0, enemy.poison_timer / 2.0) * alpha  # Fade trong 2 giây cuối với alpha
        
        # Vệt poison xanh lục quanh enemy
        poison_radius = int(18 * enemy.size_mul)
        poison_alpha = int(60 * alpha_factor)
        
        if poison_alpha > 0:
            # Vệt poison xoắn ốc
            poison_surf = pygame.Surface((poison_radius * 2, poison_radius * 2), pygame.SRCALPHA)
            poison_color = (0, 255, 100, poison_alpha)
            pygame.draw.circle(poison_surf, poison_color, (poison_radius, poison_radius), poison_radius)
            self.screen.blit(poison_surf, (int(x - poison_radius), int(y - poison_radius)))
            
            # Bong bóng poison nhỏ bay lên
            if random.random() < 0.4:  # 40% cơ hội
                for _ in range(random.randint(1, 3)):
                    bubble_x = x + random.uniform(-poison_radius//2, poison_radius//2)
                    bubble_y = y + random.uniform(-poison_radius//2, poison_radius//2)
                    bubble_size = random.randint(2, 4)
                    bubble_alpha = int(120 * alpha_factor)
                    
                    if bubble_alpha > 0:
                        bubble_surf = pygame.Surface((bubble_size*2, bubble_size*2), pygame.SRCALPHA)
                        pygame.draw.circle(bubble_surf, (100, 255, 150, bubble_alpha), (bubble_size, bubble_size), bubble_size)
                        self.screen.blit(bubble_surf, (int(bubble_x - bubble_size), int(bubble_y - bubble_size)))
            
            # Hiện thông tin poison damage trên thanh HP
            if enemy.poison_damage > 0:
                poison_text = f"-{enemy.poison_damage:.0f}/s"
                poison_surf = pygame.font.Font(None, 14).render(poison_text, True, (0, 255, 100))
                poison_rect = poison_surf.get_rect(center=(int(x + 20), int(y - 30)))
                self.screen.blit(poison_surf, poison_rect)
    
    def _draw_rocket_body(self, p, x, y):
        """Vẽ thân tên lửa với hình dạng thực tế"""
        # Tính toán hướng của tên lửa
        angle = p.rotation
        
        # Vẽ thân tên lửa như hình elip dài theo hướng bay
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Các điểm của thân tên lửa
        body_length = 12
        body_width = 4
        
        # Điểm đuôi và đầu tên lửa
        tail_x = x - cos_a * body_length
        tail_y = y - sin_a * body_length
        
        # Vẽ thân bằng đường thẳng dày
        pygame.draw.line(self.screen, (100, 100, 100), (int(tail_x), int(tail_y)), (x, y), body_width)
        pygame.draw.line(self.screen, (150, 150, 150), (int(tail_x), int(tail_y)), (x, y), body_width - 2)
        
        # Vẽ cánh tên lửa nhỏ
        wing_length = 6
        wing_offset = body_length * 0.7
        
        wing_base_x = x - cos_a * wing_offset
        wing_base_y = y - sin_a * wing_offset
        
        # Cánh trái và phải
        for side in [-1, 1]:
            wing_x = wing_base_x + sin_a * wing_length * side
            wing_y = wing_base_y - cos_a * wing_length * side
            pygame.draw.line(self.screen, (80, 80, 80), 
                           (int(wing_base_x), int(wing_base_y)), 
                           (int(wing_x), int(wing_y)), 2)

    def draw_death_effects(self):
        """Vẽ hiệu ứng khi địch chết"""
        for effect in self.death_effects:
            effect.draw(self.screen)
            
    def draw_damage_texts(self):
        """Vẽ text sát thương bay lên"""
        for damage_text in self.damage_texts:
            damage_text.draw(self.screen)
            
    def draw_range_circles(self):
        """Vẽ vòng tròn tầm bắn cho tower"""
        # Hiển thị tầm bắn của tower được chọn
        if self.selected_tower_for_range:
            self._draw_tower_range(self.selected_tower_for_range, (255, 255, 255, 80))  # Trắng trong suốt
            
        # Hiển thị tất cả tầm bắn nếu được bật
        if self.show_all_ranges:
            for tower in self.towers:
                if tower != self.selected_tower_for_range:  # Không vẽ lại tower đã chọn
                    # Màu khác nhau theo loại tower
                    if tower.ttype in ["gun", "sniper"]:
                        color = (255, 255, 0, 50)  # Vàng cho gun/sniper
                    elif tower.ttype in ["splash", "rocket", "mortar"]:
                        color = (255, 100, 0, 50)  # Cam cho splash
                    elif tower.ttype == "slow":
                        color = (100, 200, 255, 50)  # Xanh cho slow
                    elif tower.ttype in ["poison", "flame"]:
                        color = (100, 255, 100, 50)  # Xanh lá cho poison/flame
                    else:
                        color = (200, 200, 200, 50)  # Xám cho các loại khác
                    
                    self._draw_tower_range(tower, color)
                    
    def _draw_tower_range(self, tower, color):
        """Vẽ tầm bắn cho một tower"""
        cx, cy = tower.center()
        
        # Tạo surface trong suốt để vẽ vòng tròn
        circle_surface = pygame.Surface((tower.range * 2, tower.range * 2), pygame.SRCALPHA)
        
        # Vẽ vòng tròn đổ màu trong suốt
        pygame.draw.circle(circle_surface, color, 
                          (int(tower.range), int(tower.range)), int(tower.range))
        
        # Vẽ viền vòng tròn
        border_color = (color[0], color[1], color[2], min(255, color[3] * 3))
        pygame.draw.circle(circle_surface, border_color, 
                          (int(tower.range), int(tower.range)), int(tower.range), 2)
        
        # Blit surface lên screen
        self.screen.blit(circle_surface, 
                        (cx - tower.range, cy - tower.range))
                        
    def draw_placement_preview(self):
        """Vẽ preview khi chuẩn bị đặt tower"""
        if not self.selected_tower or self.paused:
            return
            
        mx, my = pygame.mouse.get_pos()
        
        # Chỉ hiện preview trong game area
        if mx >= GAME_WIDTH or my >= GAME_HEIGHT:
            return
            
        gx, gy = px_to_grid(mx, my)
        
        # Kiểm tra có thể đặt tower không
        if (0 <= gx < GRID_W and 0 <= gy < GRID_H and 
            (gx, gy) not in self.path_cells and 
            (gx, gy) not in self.occupied):
            
            # Lấy thông số tower từ config
            tower_def = TOWER_DEFS[self.selected_tower]
            preview_range = tower_def["range"]
            
            # Vị trí center của ô
            cx, cy = grid_to_px(gx, gy)
            
            # Vẽ preview tầm bắn với màu xanh lá trong suốt
            circle_surface = pygame.Surface((preview_range * 2, preview_range * 2), pygame.SRCALPHA)
            
            # Vòng tròn preview
            pygame.draw.circle(circle_surface, (100, 255, 100, 60), 
                              (int(preview_range), int(preview_range)), int(preview_range))
            
            # Viền vòng tròn preview
            pygame.draw.circle(circle_surface, (100, 255, 100, 120), 
                              (int(preview_range), int(preview_range)), int(preview_range), 2)
            
            self.screen.blit(circle_surface, 
                            (cx - preview_range, cy - preview_range))
            
            # Vẽ preview tower sprite (mờ)
            if self.selected_tower in self.tower_sprites:
                sprite = self.tower_sprites[self.selected_tower]
                # Tạo surface mờ
                preview_sprite = sprite.copy()
                preview_sprite.set_alpha(150)  # 150/255 độ mờ
                sprite_rect = preview_sprite.get_rect(center=(cx, cy))
                self.screen.blit(preview_sprite, sprite_rect)
                
    def draw_setup_countdown(self):
        """Vẽ thanh đếm ngược setup phase"""
        # Thanh progress ở giữa màn hình
        bar_width = 300
        bar_height = 30
        bar_x = (GAME_WIDTH - bar_width) // 2
        bar_y = 100
        
        # Tính phần trăm thời gian còn lại
        progress = max(0, self.setup_time / 15.0)  # 15 giây ban đầu
        
        # Vẽ background thanh
        pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=15)
        
        # Vẽ thanh progress
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            # Màu chuyển từ xanh → vàng → đỏ
            if progress > 0.6:
                color = (100, 200, 100)  # Xanh
            elif progress > 0.3:
                color = (200, 200, 100)  # Vàng
            else:
                color = (200, 100, 100)  # Đỏ
                
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, fill_width, bar_height), border_radius=15)
        
        # Viền thanh
        pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 2, border_radius=15)
        
        # Text đếm ngược với hiệu ứng nhấp nháy khi gần hết thời gian
        countdown_text = f"THỜI GIAN CHUẨN BỊ: {int(self.setup_time)}s"
        
        # Màu text thay đổi và nhấp nháy khi còn ít thời gian
        if self.setup_time <= 3:
            # Nhấp nháy đỏ
            blink = int(time.time() * 4) % 2  # Nhấp nháy 2 lần/giây
            text_color = (255, 100, 100) if blink else (255, 200, 200)
        elif self.setup_time <= 6:
            text_color = (255, 200, 100)  # Vàng
        else:
            text_color = WHITE  # Trắng bình thường
            
        text_surface = self.font.render(countdown_text, True, text_color)
        text_rect = text_surface.get_rect(center=(bar_x + bar_width//2, bar_y - 25))
        self.screen.blit(text_surface, text_rect)
        
        # Hướng dẫn
        guide_text = "Đặt tháp của bạn! Nhấn SPACE để bắt đầu sớm"
        guide_surface = self.font.render(guide_text, True, YELLOW)
        guide_rect = guide_surface.get_rect(center=(bar_x + bar_width//2, bar_y + bar_height + 25))
        self.screen.blit(guide_surface, guide_rect)

    # --- vùng toạ độ UI ---
    def _powerup_rects(self) -> Dict[str, pygame.Rect]:
        # Đặt panel hỗ trợ ở khu vực bên phải ngoài map, rộng hơn và cao hơn để dễ click
        bx = GAME_WIDTH + 5; by = 45  # Tăng vùng click bằng cách giảm margin
        return {
            "freeze": pygame.Rect(bx, by, 260, 50),      # Tăng từ 240x38 → 260x50
            "air":    pygame.Rect(bx, by+55, 260, 50),   # Tăng từ 240x38 → 260x50, gap từ 48 → 55
        }

    def _hotbar_rects(self) -> Dict[str, pygame.Rect]:
        # Đặt thanh chọn tower ở khu vực dưới cùng ngoài map
        w = 90; h = 70; gap = 10
        
        # Lấy loadout hiện tại thay vì TOWER_KEYS cố định
        if self.current_user and self.current_user in self.accounts:
            account = self.accounts[self.current_user]
            current_loadout = account.get("current_loadout", DEFAULT_LOADOUT.copy())
        else:
            current_loadout = DEFAULT_LOADOUT.copy()
        
        # Tính toán layout dựa trên số tháp trong loadout
        tower_count = len(current_loadout)
        total = tower_count * w + (tower_count - 1) * gap
        left = (GAME_WIDTH//2) - (total//2)  # Căn giữa theo chiều rộng của game map
        y = GAME_HEIGHT + 25  # Đặt dưới map với khoảng cách 25px để có chỗ cho label "Chọn Trụ"
        
        rects = {}
        for i, key in enumerate(current_loadout):
            x = left + i*(w+gap)
            rects[key] = pygame.Rect(x, y, w, h)
        return rects

    def draw_hud(self):
        name = self.player_name
        
        # Setup phase indicator và combat indicator - Gọn gàng hơn
        if self.in_setup_phase:
            # Dòng 1: Setup phase với thời gian - sử dụng font nhỏ hơn với viền
            setup_text = f"[TOOL] SETUP - {int(self.setup_time)}s (SPACE: Bắt đầu)"
            hud_font = self._get_font(16)
            self._draw_text_with_outline(setup_text, hud_font, YELLOW, (0, 0, 0), 10, 10, 1)
            
            # Dòng 2: Thông tin game cơ bản với spacing đủ và viền
            basic_info = f"{name} | L{self.level}/{TOTAL_LEVELS} | ${self.money} | ♥{self.lives}"
            self._draw_text_with_outline(basic_info, hud_font, WHITE, (0, 0, 0), 10, 30, 1)
            # KHÔNG return ở đây để tiếp tục vẽ panels
        else:
            # Chia thông tin thành 2 dòng để tránh đè lên nhau
            
            # Dòng 1: Thông tin player và level
            lives_warning = ""
            if self.lives <= 1:
                lives_warning = "!"
            elif self.lives <= 2:
                lives_warning = "!"
            
            # Boss indicator ngắn gọn
            boss_text = ""
            if hasattr(self, 'wave_mgr') and hasattr(self.wave_mgr, 'level') and self.wave_mgr.level in BOSS_LEVELS:
                if hasattr(self.wave_mgr, 'is_boss_wave') and self.wave_mgr.is_boss_wave:
                    boss_text = "[CROWN]BOSS"
                else:
                    boss_text = "[CROWN]"
                    
            line1 = f"{name} | {self.mode_name} L{self.level}/{TOTAL_LEVELS} {boss_text} | ♥{self.lives}{lives_warning}"
            
            # Dòng 2: Thông tin wave và trạng thái
            speed_text = "PAUSE" if self.paused else ("x2" if self.speed_scale > 1 else "")
            max_waves_display = "∞" if getattr(self, 'is_permanent_map', False) else str(self.max_waves)
            line2 = f"Wave {self.wave_mgr.wave_no}/{max_waves_display} | ${self.money} | {speed_text}"
            
            # Màu sắc dựa trên trạng thái
            if boss_text == "[CROWN]BOSS":
                text_color = ORANGE
            elif self.lives <= 1:
                text_color = RED  
            elif self.lives <= 2:
                text_color = YELLOW
            else:
                text_color = WHITE
                
            # Sử dụng font nhỏ hơn với viền để dễ đọc trên mọi background
            hud_font = self._get_font(16)  # Nhỏ hơn để tránh đè
            self._draw_text_with_outline(line1, hud_font, text_color, (0, 0, 0), 10, 10, 1)
            self._draw_text_with_outline(line2, hud_font, WHITE, (0, 0, 0), 10, 30, 1)
            
            # Cảnh báo đặc biệt cho boss wave - dòng riêng với viền đậm hơn
            if hasattr(self.wave_mgr, 'is_boss_wave') and self.wave_mgr.is_boss_wave:
                warning_text = "! BOSS thoát = GAME OVER! [SKULL]"
                self._draw_text_with_outline(warning_text, hud_font, RED, (0, 0, 0), 10, 50, 2)

        # --- Panel Hỗ trợ (Freeze/Airstrike) - Hiển thị luôn ---
        panel_x = GAME_WIDTH + 5   # Giảm margin để phù hợp với vùng click
        panel_y = 25               # Điều chỉnh để phù hợp
        
        # Hiển thị panel hỗ trợ trong cả setup phase và combat, rộng và cao hơn
        if self.in_setup_phase:
            # Trong setup phase - hiển thị với chú thích khác  
            pygame.draw.rect(self.screen, (70,70,35), (panel_x-5, panel_y-5, 275, 135), border_radius=12)  # Tăng kích thước
            self.screen.blit(self.font.render("Hỗ trợ (Combat)", True, YELLOW), (panel_x, panel_y))
        else:
            # Trong combat - hiển thị bình thường
            pygame.draw.rect(self.screen, (35,45,70), (panel_x-5, panel_y-5, 275, 135), border_radius=12)  # Tăng kích thước
            self.screen.blit(self.font.render("Hỗ trợ", True, WHITE), (panel_x, panel_y))
            
        rects = self._powerup_rects()
        
        # Freeze button - disable trong setup phase với màu đẹp hơn + hover effect
        enough = self.money >= POWERUPS["freeze"]["cost"] and not self.in_setup_phase
        is_hovered = self.hovered_powerup == "freeze"
        
        if self.in_setup_phase:
            button_color = (70, 70, 70)  # Xám nhạt
            border_color = (100, 100, 100)
            text_color = GRAY
        elif enough:
            if is_hovered:
                button_color = (120, 200, 150)  # Sáng hơn khi hover
                border_color = (150, 240, 180)
            else:
                button_color = (100, 180, 130)  # Xanh lục sáng
                border_color = (130, 220, 160)
            text_color = WHITE
        else:
            if is_hovered:
                button_color = (130, 120, 110)  # Sáng hơn một chút khi hover
                border_color = (160, 150, 140)
            else:
                button_color = (110, 100, 90)  # Nâu nhạt
                border_color = (140, 130, 120)
            text_color = GRAY
            
        pygame.draw.rect(self.screen, button_color, rects["freeze"], border_radius=10)
        pygame.draw.rect(self.screen, border_color, rects["freeze"], width=3, border_radius=10)  # Tăng độ dày viền
        small_font = self._get_font(17)  # Tăng size font
        self.screen.blit(small_font.render("Đóng băng (F) $500", True, text_color), (rects["freeze"].x+10, rects["freeze"].y+15))  # Căn giữa tốt hơn
        
        # Airstrike button - disable trong setup phase với màu đẹp hơn + hover effect  
        enough = self.money >= POWERUPS["air"]["cost"] and not self.in_setup_phase
        is_hovered = self.hovered_powerup == "air"
        
        if self.in_setup_phase:
            button_color = (70, 70, 70)  # Xám nhạt
            border_color = (100, 100, 100)
            text_color = GRAY
        elif enough:
            if is_hovered:
                button_color = (200, 160, 120)  # Sáng hơn khi hover
                border_color = (240, 190, 150)
            else:
                button_color = (180, 140, 100)  # Cam sáng
                border_color = (220, 170, 130)
            text_color = WHITE
        else:
            if is_hovered:
                button_color = (140, 120, 100)  # Sáng hơn một chút khi hover
                border_color = (170, 150, 130)
            else:
                button_color = (120, 100, 80)  # Nâu đậm
                border_color = (150, 130, 110)
            text_color = GRAY
            
        pygame.draw.rect(self.screen, button_color, rects["air"], border_radius=10)
        pygame.draw.rect(self.screen, border_color, rects["air"], width=3, border_radius=10)  # Tăng độ dày viền
        self.screen.blit(small_font.render("Tất cả (A) $1k", True, text_color), (rects["air"].x+10, rects["air"].y+15))  # Căn giữa tốt hơn

        # --- Panel Compact Game Info ---
        info_y = panel_y + 160
        
        if self.in_setup_phase:
            # Panel setup phase - màu đẹp hơn với border, rộng hơn nữa
            panel_bg = (80, 100, 50)  # Xanh lá đậm
            border_color = (120, 150, 80)  # Xanh lá sáng
            pygame.draw.rect(self.screen, panel_bg, (panel_x-5, info_y-5, 320, 85), border_radius=10)
            pygame.draw.rect(self.screen, border_color, (panel_x-5, info_y-5, 320, 85), width=2, border_radius=10)
            self.screen.blit(self._get_font(20, bold=True).render("CHUẨN BỊ", True, YELLOW), (panel_x, info_y))
            # Font nhỏ hơn cho text dài
            small_font = self._get_font(16)
            line1 = f"Thời gian: {int(self.setup_time)}s | Tháp: {len(self.towers)} | ${self.money}"
            line2 = "SPACE: Bắt đầu sớm"
            self.screen.blit(small_font.render(line1, True, WHITE), (panel_x, info_y + 20))
            self.screen.blit(small_font.render(line2, True, GREEN), (panel_x, info_y + 40))
            self.screen.blit(small_font.render("Đặt phòng thủ!", True, YELLOW), (panel_x, info_y + 60))
        else:
            # Panel combat - màu đẹp hơn với border, rộng hơn nữa
            panel_bg = (50, 60, 90)  # Xanh dương đậm
            border_color = (80, 100, 140)  # Xanh dương sáng
            pygame.draw.rect(self.screen, panel_bg, (panel_x-5, info_y-5, 320, 85), border_radius=10)
            pygame.draw.rect(self.screen, border_color, (panel_x-5, info_y-5, 320, 85), width=2, border_radius=10)
            self.screen.blit(self._get_font(20, bold=True).render("TRẠNG THÁI", True, WHITE), (panel_x, info_y))
            # Font nhỏ hơn cho text dài
            small_font = self._get_font(16)
            line1 = f"Đợt {self.wave_mgr.wave_no}/{self.max_waves} | Quái: {len(self.enemies)} | Tháp: {len(self.towers)}"
            line2 = f"Diệt: {self.kills} | Tốc độ: {'x2' if self.speed_scale>1 else 'x1'}"
            self.screen.blit(small_font.render(line1, True, WHITE), (panel_x, info_y + 20))
            self.screen.blit(small_font.render(line2, True, WHITE), (panel_x, info_y + 40))
                
        # Panel Range - màu đẹp hơn với border, rộng hơn nữa
        guide_y = info_y + 95
        range_panel_bg = (70, 50, 40)  # Nâu đậm
        range_border_color = (110, 80, 60)  # Nâu sáng
        pygame.draw.rect(self.screen, range_panel_bg, (panel_x-5, guide_y-5, 320, 75), border_radius=10)
        pygame.draw.rect(self.screen, range_border_color, (panel_x-5, guide_y-5, 320, 75), width=2, border_radius=10)
        small_font = self._get_font(16)
        
        if self.selected_tower_for_range:
            # Thông tin tower được chọn - gọn
            tower = self.selected_tower_for_range
            title = f"{TOWER_DEFS[tower.ttype]['name']} Lv.{tower.level}"
            specs = f"Dmg {tower.damage} | Range {int(tower.range)} | Rate {tower.fire_rate:.1f}/s"
            upgrade_text = "Click to upgrade" if tower.can_upgrade() else "Max level"
            
            # Dùng font nhỏ hơn cho tiêu đề để vừa khung
            self.screen.blit(self._get_font(18, bold=True).render(title, True, YELLOW), (panel_x, guide_y))
            self.screen.blit(small_font.render(specs, True, WHITE), (panel_x, guide_y + 18))
            color = GREEN if tower.can_upgrade() else GRAY
            self.screen.blit(small_font.render(upgrade_text, True, color), (panel_x, guide_y + 36))
        else:
            # Hướng dẫn sử dụng - gọn
            self.screen.blit(self._get_font(18, bold=True).render("TẦM BẮN", True, WHITE), (panel_x, guide_y))
            help1 = f"Click tháp | R: Tất cả {'BẬT' if self.show_all_ranges else 'TẮT'}"
            help2 = "Di chuột: Xem trước"
            self.screen.blit(small_font.render(help1, True, WHITE), (panel_x, guide_y + 18))
            self.screen.blit(small_font.render(help2, True, WHITE), (panel_x, guide_y + 36))

        # ENEMY COMPOSITION PANEL - Bên phải dưới panel TẦM BẮN
        self._draw_enemy_composition_panel(panel_x, guide_y + 85)
        
        # AUDIO CONTROLS - Nút bật/tắt âm thanh bên phải
        self._draw_audio_controls(panel_x, guide_y + 195)

        # --- Thanh chọn trụ (hotbar) - Hiển thị luôn ---
        # Thêm label cho khu vực chọn tower - đặt giữa map và hotbar
        hotbar_label_y = GAME_HEIGHT + 2  # Chỉ cách map 2px để không đè lên map
        label_x = (GAME_WIDTH//2) - 40
        
        hotbar_font = self._get_font(18, bold=True)
        money_font = self._get_font(16, bold=True)
        
        # Hiển thị tiền với highlight đỏ nếu không đủ mua tháp đang chọn
        money_text = f"${self.money}"
        
        # Kiểm tra xem có đủ tiền mua tháp đang chọn không
        selected_tower_cost = 0
        if self.selected_tower and self.selected_tower in TOWER_DEFS:
            selected_tower_cost = TOWER_DEFS[self.selected_tower]["cost"]
        
        can_afford_selected = self.money >= selected_tower_cost
        
        # Màu sắc và highlight
        if self.selected_tower and not can_afford_selected:
            # HIGHLIGHT ĐỎ khi không đủ tiền mua tháp đang chọn
            money_color = RED
            highlight_color = (255, 100, 100)  # Đỏ sáng cho highlight
        else:
            # Màu thường
            money_color = GREEN if self.money >= 100 else (YELLOW if self.money >= 50 else RED)
            highlight_color = None
        
        if self.in_setup_phase:
            self._draw_text_with_outline("Chọn Tháp", hotbar_font, YELLOW, (0, 0, 0), label_x - 10, hotbar_label_y, 1)
        else:
            self._draw_text_with_outline("Chọn Tháp", hotbar_font, WHITE, (0, 0, 0), label_x, hotbar_label_y, 1)
            
        # Vẽ background highlight nếu cần
        money_x = label_x + 120
        money_y = hotbar_label_y + 2
        if highlight_color:
            # Tạo background highlight nhấp nháy
            import math
            alpha = int(100 + 50 * math.sin(pygame.time.get_ticks() * 0.01))
            highlight_surf = pygame.Surface((80, 22), pygame.SRCALPHA)
            highlight_surf.fill((*highlight_color, alpha))
            self.screen.blit(highlight_surf, (money_x - 5, money_y - 2))
            
        # Vẽ text tiền với viền đậm hơn nếu highlight
        outline_width = 2 if highlight_color else 1
        self._draw_text_with_outline(money_text, money_font, money_color, (0, 0, 0), money_x, money_y, outline_width)
        
        hot = self._hotbar_rects()
        for key, r in hot.items():
            # Tất cả tháp trong loadout đều được xem là owned
            owned = True  # Vì đã có trong loadout
            
            # Màu sắc đẹp hơn với border
            if self.in_setup_phase:
                bg = (90, 120, 70) if owned else (65, 65, 65)  # Xanh lá sáng trong setup
                border = (120, 150, 100) if owned else (90, 90, 90)
            else:
                bg = (70, 90, 130) if owned else (65, 65, 65)  # Xanh dương sáng trong combat  
                border = (100, 120, 160) if owned else (90, 90, 90)
                
            pygame.draw.rect(self.screen, bg, r, border_radius=10)
            pygame.draw.rect(self.screen, border, r, width=2, border_radius=10)
            
            # icon
            img = self.tower_sprites.get(key)
            if img:
                icon = pygame.transform.smoothscale(img, (38,38))
                icon_rect = icon.get_rect(center=(r.centerx, r.y+25))
                self.screen.blit(icon, icon_rect)
                # --- Badge Lv1 nhỏ ở góc phải-trên icon ---
                draw_level_badge(self.screen, icon_rect.right - 4, icon_rect.top + 4, 1, small=True)

            # Hiển thị giá với màu sắc thông minh
            cost = TOWER_DEFS[key]["cost"]
            can_afford = self.money >= cost
            
            # Màu sắc dựa trên khả năng mua
            if not owned:
                price_color = GRAY
            elif can_afford:
                price_color = GREEN  # Đủ tiền
            elif cost - self.money <= 20:
                price_color = YELLOW  # Gần đủ tiền
            else:
                price_color = RED  # Không đủ tiền
                
            price_font = self._get_font(14, bold=True)
            self._draw_text_with_outline(f"${cost}", price_font, price_color, (0, 0, 0), 
                                       r.centerx - 15, r.y + 46, 1)
            
            # ô đang chọn
            if self.selected_tower==key:
                border_color = YELLOW if self.in_setup_phase else ORANGE
                pygame.draw.rect(self.screen, border_color, r, width=3, border_radius=10)

        # Gợi ý nâng cấp / trạng thái wave / thông tin decoration
        mx, my = pygame.mouse.get_pos()
        gx, gy = px_to_grid(mx, my)
        t = self._find_tower_at((gx,gy))
        
        # Sử dụng font nhỏ hơn với viền cho tooltip để đọc rõ hơn
        tooltip_font = self._get_font(14)
        tooltip_y = 70  # Đặt thấp hơn để không đè lên HUD chính
        
        if t:
            up_txt = "MAX" if not t.can_upgrade() else f"Upgrade: ${t.upgrade_cost()}"
            tip = f"{TOWER_DEFS[t.ttype]['name']} Lv{t.level} | Rng {int(t.range)} | FR {t.fire_rate:.2f}/s | Dmg {t.damage} | {up_txt}"
            self._draw_text_with_outline(tip, tooltip_font, WHITE, (0, 0, 0), 10, tooltip_y, 1)
        elif (gx, gy) in getattr(self, 'tower_slots', set()) and (gx, gy) not in self.occupied:
            # Thông tin về ô đặt tower với viền
            self._draw_text_with_outline("Ô đặt trụ - Click để đặt trụ đã chọn", tooltip_font, (150, 255, 150), (0, 0, 0), 10, tooltip_y, 1)
        elif hasattr(self, 'decorative_objects'):
            # Kiểm tra hover qua decoration
            decoration_info = self._get_decoration_at(gx, gy)
            if decoration_info:
                decoration_names = {
                    "broken_tower": "Tháp cổ bị hư hỏng",
                    "dead_tree": "Cây khô héo", 
                    "rocks": "Những tảng đá cổ",
                    "thorns": "Bụi gai sắc nhọn",
                    "ruins": "Tàn tích cổ đại",
                    "crystal": "Pha lê năng lượng",
                    "bones": "Hài cốt cổ"
                }
                name = decoration_names.get(decoration_info, "Vật trang trí")
                self._draw_text_with_outline(f"{name} - Không thể đặt trụ ở đây", tooltip_font, (200, 200, 100), (0, 0, 0), 10, tooltip_y, 1)
            else:
                # Thông tin wave thông thường với viền
                if self.wave_mgr.active: status = f"Đang sinh: còn {self.wave_mgr.enemies_left_to_spawn} địch"
                elif self.wave_mgr.is_between_waves(): status = f"Nghỉ wave: {self.wave_mgr.cooldown:.1f}s"
                else: status = "Chuẩn bị wave tiếp theo..."
                self._draw_text_with_outline(status, tooltip_font, WHITE, (0, 0, 0), 10, tooltip_y, 1)
        else:
            if self.wave_mgr.active: status = f"Đang sinh: còn {self.wave_mgr.enemies_left_to_spawn} địch"
            elif self.wave_mgr.is_between_waves(): status = f"Nghỉ wave: {self.wave_mgr.cooldown:.1f}s"
            else: status = "Chuẩn bị wave tiếp theo..."
            self._draw_text_with_outline(status, tooltip_font, WHITE, (0, 0, 0), 10, tooltip_y, 1)
            
        # Hiển thị hint về placement grid
        grid_status = "ON" if getattr(self, 'show_placement_grid', True) else "OFF"
        grid_hint = f"Placement Grid: {grid_status} (G)"
        self.screen.blit(self.font.render(grid_hint, True, (180, 180, 180)), (8, HEIGHT - 25))

        # VẼ PLACEMENT GRID Ở ĐÂY ĐỂ ĐẢM BẢO KHÔNG BỊ CHE
        if getattr(self, 'show_placement_grid', True) and hasattr(self, 'tower_slots'):
            decoration_positions = set()
            if hasattr(self, 'decorative_objects'):
                decoration_positions = {decoration["pos"] for decoration in self.decorative_objects}
                
            for (gx, gy) in self.tower_slots:
                if (gx, gy) not in decoration_positions:  # Không vẽ lên decorations
                    center_x = gx*TILE + TILE//2
                    center_y = gy*TILE + TILE//2
                    
                    if (gx, gy) in self.occupied:
                        # Ô có tower - viền xanh đậm
                        rect = pygame.Rect(gx*TILE + 1, gy*TILE + 1, TILE-2, TILE-2)
                        pygame.draw.rect(self.screen, (0, 255, 0), rect, width=4, border_radius=8)
                    else:
                        # Ô có thể đặt tower - dấu "+" trắng nổi bật
                        # Dấu + với outline đen
                        for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                            pygame.draw.line(self.screen, (0, 0, 0), 
                                           (center_x - 15 + dx, center_y + dy), 
                                           (center_x + 15 + dx, center_y + dy), 4)
                            pygame.draw.line(self.screen, (0, 0, 0), 
                                           (center_x + dx, center_y - 15 + dy), 
                                           (center_x + dx, center_y + 15 + dy), 4)
                        # Dấu + trắng chính
                        pygame.draw.line(self.screen, (255, 255, 255), 
                                       (center_x - 15, center_y), (center_x + 15, center_y), 4)
                        pygame.draw.line(self.screen, (255, 255, 255), 
                                       (center_x, center_y - 15), (center_x, center_y + 15), 4)
    
    def _get_decoration_at(self, gx, gy):
        """Lấy thông tin decoration tại vị trí (gx, gy)."""
        if hasattr(self, 'decorative_objects'):
            for decoration in self.decorative_objects:
                if decoration["pos"] == (gx, gy):
                    return decoration["type"]
        return None

        # Thông báo nhỏ với viền đẹp
        if self.notice_timer>0 and self.notice_msg:
            notice_font = self._get_font(18, bold=True)
            
            # Tạo background với size phù hợp
            temp_surface = notice_font.render(self.notice_msg, True, YELLOW)
            bg = pygame.Surface((temp_surface.get_width()+20, temp_surface.get_height()+12), pygame.SRCALPHA)
            bg.fill((0,0,0,200))  # Background đậm hơn
            
            # Đặt ở giữa màn hình, phía trên một chút
            bg_x = (WIDTH - bg.get_width()) // 2
            bg_y = 80  # Cách HUD một khoảng an toàn
            
            self.screen.blit(bg, (bg_x, bg_y))
            # Vẽ text với viền đậm
            self._draw_text_with_outline(self.notice_msg, notice_font, YELLOW, (0, 0, 0), bg_x + 10, bg_y + 6, 2)

    def draw_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        if self.lives <= 0:
            # Hiển thị thông báo khác nhau tùy theo lý do thua
            if hasattr(self, 'game_over_reason') and self.game_over_reason == "boss_escaped":
                gg = self.bigfont.render(" BOSS THOÁT! GAME OVER! ", True, RED)
                tip = self.font.render("Boss đã thoát khỏi bản đồ - Thất bại hoàn toàn!", True, YELLOW)
                tip2 = self.font.render("Nhấn R để thử lại | ESC về menu", True, WHITE)
                self.screen.blit(gg, gg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
                self.screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
                self.screen.blit(tip2, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))
            else:
                gg = self.bigfont.render("HẾT MẠNG! THUA RỒI!", True, ORANGE)
                tip = self.font.render("Đã để quá nhiều địch thoát qua", True, WHITE)
                tip2 = self.font.render("Nhấn R để chơi lại level | ESC về menu", True, WHITE)
                self.screen.blit(gg, gg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))
                self.screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
                self.screen.blit(tip2, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
            return

        if self.win_level:
            gg = self.bigfont.render("LEVEL CLEARED!", True, ORANGE)
            
            # Hiển thị số sao đạt được - theo performance
            max_lives = MODE_PARAMS[self.mode_name]["lives"]
            lives_lost = max_lives - self.lives
            
            # Áp dụng cùng công thức chấm sao
            if self.lives <= 0:
                stars_earned = 1  # Game over case
            else:
                stars_earned = max(1, 3 - lives_lost)
            
            # Tạo text hiển thị sao (chỉ hiển thị sao đầy)
            star_text = "★" * stars_earned
            star_color = YELLOW if stars_earned == 3 else ORANGE if stars_earned == 2 else WHITE
            star_render = self.bigfont.render(star_text, True, star_color)
            
            # Text mô tả với cả star và coin (dùng text thay emoji)
            lives_remaining = self.lives
            desc_text = f"+{stars_earned} Sao +1 Coin | Còn lại: {lives_remaining}/{max_lives} mạng"
            desc_color = star_color
            
            desc_render = self.font.render(desc_text, True, desc_color)
            tip = self.font.render("Nhấn N để sang level mới | R chơi lại", True, WHITE)
            
            # Vẽ theo thứ tự từ trên xuống 
            self.screen.blit(gg, gg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50)))
            # self.screen.blit(star_render, star_render.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))  # Tạm bỏ
            self.screen.blit(desc_render, desc_render.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))  # Di chuyển lên
            self.screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
            return

        title = self.bigfont.render("TẠM DỪNG", True, ORANGE)
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 180)))
        
        # Kiểm tra xem pause_buttons có tồn tại không
        if hasattr(self, 'pause_buttons') and self.pause_buttons:
            for b in self.pause_buttons: b.draw(self.screen, self.font)
        else:
            # Nếu chưa có pause_buttons, hiển thị thông báo tạm thời
            temp_text = self.font.render("Nhấn ESC để về menu", True, WHITE)
            self.screen.blit(temp_text, temp_text.get_rect(center=(WIDTH//2, HEIGHT//2)))
    
    def _draw_enemy_composition_panel(self, panel_x, panel_y):
        """Vẽ panel hiển thị chi tiết từng loại quái - HIỂN THỊ XUYÊN SUỐT"""
        if not hasattr(self, 'wave_mgr') or not self.wave_mgr:
            return
            
        panel_width = 320
        panel_height = 100
        
        # Background panel với viền đẹp
        panel_bg = (30, 45, 65)  # Xanh navy đậm
        border_color = (60, 90, 130)  # Xanh navy sáng
        pygame.draw.rect(self.screen, panel_bg, (panel_x-5, panel_y-5, panel_width+10, panel_height+10), border_radius=8)
        pygame.draw.rect(self.screen, border_color, (panel_x-5, panel_y-5, panel_width+10, panel_height+10), width=2, border_radius=8)
        
        # Fonts
        title_font = self._get_font(16, bold=True)
        info_font = self._get_font(14)
        
        # Tiêu đề
        title_text = f"ENEMIES - WAVE {self.wave_mgr.wave_no}"
        self.screen.blit(title_font.render(title_text, True, (255, 220, 100)), (panel_x, panel_y))
        
        # LUÔN LUÔN hiển thị thông tin enemies - không phân biệt active hay không
        
        # Đếm enemies trên map theo loại
        enemies_on_map = {"normal": 0, "fast": 0, "tank": 0, "boss": 0}
        for enemy in self.enemies:
            enemy_type = getattr(enemy, 'etype', 'normal')
            if enemy_type in enemies_on_map:
                enemies_on_map[enemy_type] += 1
        
        # Đếm enemies chờ spawn theo loại (chỉ khi wave đang active)
        enemies_to_spawn = {"normal": 0, "fast": 0, "tank": 0, "boss": 0}
        if self.wave_mgr.active:
            remaining_spawn = self.wave_mgr.enemies_left_to_spawn
            
            if self.wave_mgr.is_boss_wave and hasattr(self.wave_mgr, 'boss_group') and self.wave_mgr.boss_group:
                # Boss wave - đếm chính xác từ boss_group
                for i in range(remaining_spawn):
                    if i < len(self.wave_mgr.boss_group):
                        boss_index = len(self.wave_mgr.boss_group) - remaining_spawn + i
                        if boss_index >= 0 and boss_index < len(self.wave_mgr.boss_group):
                            enemy_type = self.wave_mgr.boss_group[boss_index]
                            enemies_to_spawn[enemy_type] += 1
            else:
                # Wave thường - ước tính
                if hasattr(self.wave_mgr, 'current_wave_has_tank') and self.wave_mgr.current_wave_has_tank and remaining_spawn > 0:
                    total_wave = self.wave_mgr._wave_size(self.wave_mgr.wave_no) if hasattr(self.wave_mgr, '_wave_size') else 10
                    spawned = total_wave - remaining_spawn
                    if spawned == 0:  # Tank chưa spawn
                        enemies_to_spawn["tank"] += 1
                        remaining_spawn -= 1
                
                # Phân bổ còn lại cho normal/fast
                if remaining_spawn > 0:
                    if self.wave_mgr.level >= 4:  # Có fast từ level 4
                        fast_count = max(0, int(remaining_spawn * 0.4))
                        normal_count = remaining_spawn - fast_count
                        enemies_to_spawn["fast"] += fast_count
                        enemies_to_spawn["normal"] += normal_count
                    else:
                        enemies_to_spawn["normal"] += remaining_spawn
        
        # Hiển thị từng loại với màu sắc và icon - LUÔN HIỂN THỊ
        y_offset = 22
        enemy_info = [
            ("Normal", enemies_to_spawn["normal"] + enemies_on_map["normal"], (100, 255, 100)),
            ("Fast", enemies_to_spawn["fast"] + enemies_on_map["fast"], (255, 255, 100)),
            ("Tank", enemies_to_spawn["tank"] + enemies_on_map["tank"], (255, 100, 100)),
            ("Boss", enemies_to_spawn["boss"] + enemies_on_map["boss"], (255, 100, 255))
        ]
        
        # Luôn hiển thị tất cả loại enemies, kể cả khi = 0
        for i, (name, total, color) in enumerate(enemy_info):
            x = panel_x + (i * 75)
            y = panel_y + y_offset
            
            # Icon tròn nhỏ - mờ hơn khi = 0
            if total > 0:
                pygame.draw.circle(self.screen, color, (x + 8, y + 8), 5)
                pygame.draw.circle(self.screen, (0, 0, 0), (x + 8, y + 8), 5, width=1)
                text_color = color
            else:
                # Màu mờ khi = 0
                muted_color = tuple(c // 3 for c in color)  # Làm tối màu đi 3 lần
                pygame.draw.circle(self.screen, muted_color, (x + 8, y + 8), 5)
                pygame.draw.circle(self.screen, (0, 0, 0), (x + 8, y + 8), 5, width=1)
                text_color = muted_color
            
            # Tên và số lượng
            text = f"{name}: {total}"
            self.screen.blit(info_font.render(text, True, text_color), (x + 18, y))
        
        # Tổng số - LUÔN HIỂN THỊ
        total_all = sum(enemies_to_spawn.values()) + sum(enemies_on_map.values())
        total_text = f"Tổng cộng: {total_all}"
        self.screen.blit(info_font.render(total_text, True, WHITE), (panel_x, panel_y + 60))
    
    def _audio_control_rects(self, panel_x, panel_y):
        """Trả về rects cho các nút điều khiển âm thanh."""
        button_width = 130
        button_height = 32
        gap = 8
        
        music_rect = pygame.Rect(panel_x, panel_y + 25, button_width, button_height)
        sfx_rect = pygame.Rect(panel_x + button_width + gap, panel_y + 25, button_width, button_height)
        
        return {"music": music_rect, "sfx": sfx_rect}
    
    def _draw_audio_controls(self, panel_x, panel_y):
        """Vẽ panel điều khiển âm thanh bên phải."""
        panel_width = 320
        panel_height = 70
        
        # Background panel
        panel_bg = (40, 50, 60)
        border_color = (70, 90, 110)
        pygame.draw.rect(self.screen, panel_bg, (panel_x-5, panel_y-5, panel_width, panel_height), border_radius=10)
        pygame.draw.rect(self.screen, border_color, (panel_x-5, panel_y-5, panel_width, panel_height), width=2, border_radius=10)
        
        # Title
        title_font = self._get_font(16, bold=True)
        self.screen.blit(title_font.render("ÂM THANH", True, WHITE), (panel_x, panel_y))
        
        rects = self._audio_control_rects(panel_x, panel_y)
        small_font = self._get_font(13)
        
        # Nút nhạc nền
        music_enabled = self.save["settings"]["music"]
        music_color = (45, 140, 85) if music_enabled else (140, 60, 60)
        music_text = "Nhạc: BẬT" if music_enabled else "Nhạc: TẮT"
        
        pygame.draw.rect(self.screen, music_color, rects["music"], border_radius=8)
        pygame.draw.rect(self.screen, WHITE, rects["music"], width=2, border_radius=8)
        text_surf = small_font.render(music_text, True, WHITE)
        text_rect = text_surf.get_rect(center=rects["music"].center)
        self.screen.blit(text_surf, text_rect)
        
        # Nút âm thanh hiệu ứng
        sfx_enabled = self.save["settings"]["sfx"]
        sfx_color = (45, 140, 85) if sfx_enabled else (140, 60, 60)
        sfx_text = "Hiệu ứng: BẬT" if sfx_enabled else "Hiệu ứng: TẮT"
        
        pygame.draw.rect(self.screen, sfx_color, rects["sfx"], border_radius=8)
        pygame.draw.rect(self.screen, WHITE, rects["sfx"], width=2, border_radius=8)
        text_surf = small_font.render(sfx_text, True, WHITE)
        text_rect = text_surf.get_rect(center=rects["sfx"].center)
        self.screen.blit(text_surf, text_rect)
    
    def _draw_gradient_background(self, color1, color2, vertical=True):
        """[ART] Vẽ gradient background siêu đẹp"""
        if vertical:
            for y in range(HEIGHT):
                ratio = y / HEIGHT
                r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                pygame.draw.line(self.screen, (r, g, b), (0, y), (WIDTH, y))
        else:
            for x in range(WIDTH):
                ratio = x / WIDTH
                r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                pygame.draw.line(self.screen, (r, g, b), (x, 0), (x, HEIGHT))
    
    def _draw_gradient_rect(self, rect, color1, color2, border_radius=0):
        """[ART] Vẽ hình chữ nhật gradient siêu đẹp"""
        for y in range(rect.height):
            ratio = y / rect.height if rect.height > 0 else 0
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            
            line_rect = pygame.Rect(rect.x, rect.y + y, rect.width, 1)
            if border_radius > 0 and (y < border_radius or y >= rect.height - border_radius):
                # Xử lý border radius đơn giản
                corner_offset = min(border_radius - abs(y - border_radius), border_radius) if y < border_radius else min(border_radius - abs((rect.height - 1 - y) - border_radius), border_radius)
                if corner_offset > 0:
                    line_rect.x += corner_offset
                    line_rect.width -= 2 * corner_offset
            
            if line_rect.width > 0:
                pygame.draw.rect(self.screen, (r, g, b), line_rect)

# ------------------- MAIN -------------------
def main():
    Game().run()

if __name__ == "__main__":
    main()




