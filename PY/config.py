import os
import math

# ----------------------- CẤU HÌNH CHUNG -----------------------
TILE = 64
GRID_W, GRID_H = 15, 10
GAME_WIDTH, GAME_HEIGHT = GRID_W * TILE, GRID_H * TILE  # Kích thước map game (960x640)
UI_PANEL_WIDTH = 280  # Không gian cho panel bên phải (tăng từ 200)
UI_PANEL_HEIGHT = 100  # Không gian cho panel dưới
WIDTH = GAME_WIDTH + UI_PANEL_WIDTH    # Tổng chiều rộng màn hình (1240)
HEIGHT = GAME_HEIGHT + UI_PANEL_HEIGHT  # Tổng chiều cao màn hình (740)
FPS = 60

# Màu dùng nhanh
WHITE=(255,255,255); BLACK=(0,0,0); DARK=(40,40,40)
GREEN=(60,200,80); RED=(220,60,60); BLUE=(60,120,255); YELLOW=(240,200,60)
ORANGE=(255,140,0); SAND=(210,190,140); GRASS=(60,170,60); PURPLE=(170,80,200)
CYAN=(80,220,220); PINK=(240,120,180); BROWN=(150,110,70); GRAY=(120,120,120)

# Assets path
ASSETS_DIR = "assets"
MUSIC_MENU_DIR = os.path.join(ASSETS_DIR, "music", "menu")
MUSIC_GAME_DIR = os.path.join(ASSETS_DIR, "music", "game")
SAVE_FILE = "save.json"
ACCOUNTS_FILE = "accounts.json"


# Kinh tế
BASE_START_MONEY = 10000
BASE_START_LIVES = 5
SELL_REFUND_RATE = 0.5
PROJECTILE_SPEED = 420

# Định nghĩa các loại trụ
RANGE_TILES = 2
RANGE_PX = RANGE_TILES * TILE
H_RANGE_TILES = 4
H_RANGE_PX = H_RANGE_TILES * TILE
# Tầm bắn đặc biệt cho Sniper (8 ô)
SNIPER_RANGE_TILES = 8
SNIPER_RANGE_PX = SNIPER_RANGE_TILES * TILE

TOWER_DEFS = {
    # Tháp cơ bản - Entry level, rẻ và đáng tin cậy
    "gun":     {"name":"Súng Máy", "cost":120, "range":RANGE_PX, "firerate":1.2,  "damage":18, "sprite":"tower_lv1.png", "type":"basic"},
    "sniper":  {"name":"Súng Bắn Tỉa",      "cost":200, "range":SNIPER_RANGE_PX, "firerate":0.4, "damage":85, "sprite":"tower_lv2.png", "type":"long_range"},
    "splash":  {"name":"Đại Pháo",      "cost":250, "range":RANGE_PX, "firerate":0.6,  "damage":25, "splash":75, "sprite":"tower_lv3.png", "type":"splash"},
    "slow":    {"name":"Tháp Băng Giá", "cost":180, "range":RANGE_PX, "firerate":0.8,  "damage":12, "slow":0.5, "slow_time":3.0, "sprite":"tower_lv4.png", "type":"support"},
    
    # Tháp nâng cao - Chuyên môn hóa cao
    "laser":   {"name":"Tia Laser",  "cost":400, "range":RANGE_PX*1.3, "firerate":2.5, "damage":22, "sprite":"tower_laser.png", "type":"energy", "special":"piercing"},
    "rocket":  {"name":"Tên Lửa",      "cost":600, "range":RANGE_PX*1.6, "firerate":0.35, "damage":120, "splash":100, "sprite":"tower_rocket.png", "type":"heavy"},
    "electric": {"name":"Súng Điện Tesla", "cost":350, "range":RANGE_PX*0.9, "firerate":0.9, "damage":45, "sprite":"tower_electric.png", "type":"energy", "special":"chain"},
    "poison":  {"name":"Phi Tiêu Độc", "cost":280, "range":RANGE_PX*1.2, "firerate":0.7, "damage":5, "sprite":"tower_poison.png", "type":"poison", "poison_damage":12, "poison_time":5.0},
    
    # Tháp đặc biệt - End game, đắt nhưng mạnh
    "minigun": {"name":"Súng Máy Vip",     "cost":500, "range":RANGE_PX*0.8, "firerate":2.0, "damage":15, "sprite":"tower_minigun.png", "type":"rapid_fire"},
    "mortar":  {"name":"Cối Phá Hủy",      "cost":800, "range":RANGE_PX*2.2, "firerate":0.3, "damage":100, "splash":120, "sprite":"tower_mortar.png", "type":"artillery"},
    "ice":     {"name":"Tia Băng",    "cost":450, "range":RANGE_PX*1.1, "firerate":0.5, "damage":30, "slow":0.75, "slow_time":5.0, "sprite":"tower_ice.png", "type":"freeze"},
    "flame":   {"name":"Phun Lửa","cost":320, "range":RANGE_PX*0.7, "firerate":1.8, "damage":12, "sprite":"tower_flame.png", "type":"fire", "burn_damage":5, "burn_time":3.0},
}

# Tất cả các loại tháp có thể có (sắp xếp theo giá tiền)
ALL_TOWER_KEYS = ["gun", "slow", "sniper", "splash", "poison", "flame", "electric", "laser", "ice", "minigun", "rocket", "mortar"]

# Keys cho 4 tháp ban đầu (backward compatibility)
TOWER_KEYS = ["gun", "sniper", "splash", "slow"]

# Tháp mặc định cho người chơi mới (chỉ súng máy - người chơi phải unlock từng súng)
DEFAULT_LOADOUT = ["gun"]

# Nâng cấp trụ (2 cấp)
TOWER_UPGRADE = [
    {"range":1.15, "firerate":1.25, "damage":1.4,  "cost":120},
    {"range":1.15, "firerate":1.25, "damage":1.4,  "cost":180},
]

# Enemy system - 4 loại địch với vai trò riêng biệt
ENEMY_TYPES = {
    "normal":  {"hp":100,  "spd":60,  "reward":22, "color":(140,140,120), "name":"Soldier", "size_mul":1.0, "description":"Cân bằng, backbone của wave"},
    "fast":    {"hp":50,  "spd":150, "reward":15, "color":(120,200,120), "name":"Scout", "size_mul":0.8, "description":"Tốc độ cao, cần xử lý nhanh"},  
    "tank":    {"hp":300, "spd":40,  "reward":45, "color":(200,60,60), "name":"Heavy", "size_mul":1.3, "description":"Máu dày, chống slow 50%", "slow_resist":0.5},
    "boss":    {"hp":600, "spd":45,  "reward":120, "color":(160,100,200), "name":"Commander", "size_mul":1.6, "description":"Hồi máu, tăng buff cho địch gần", "regen":5, "buff_range":80},
}

# Tất cả loại địch
ALL_ENEMY_KEYS = ["normal", "fast", "tank", "boss"]

# Spawn weights theo level (có thể dùng trong wave_manager)
ENEMY_SPAWN_WEIGHTS = {
    "early":  {"normal": 0.8, "fast": 0.2, "tank": 0.0, "boss": 0.0},  # Level 1-3
    "mid":    {"normal": 0.6, "fast": 0.25, "tank": 0.15, "boss": 0.0}, # Level 4-6  
    "hard":   {"normal": 0.45, "fast": 0.25, "tank": 0.25, "boss": 0.05}, # Level 7-10
    "expert": {"normal": 0.35, "fast": 0.2, "tank": 0.3, "boss": 0.15},   # Level 11+
}

# Wave
SPAWN_GAP = 0.8
WAVE_COOLDOWN = 3.0

# 🆕 Boss level configuration
BOSS_LEVELS = [3, 5, 7, 9, 11, 13, 15]  # Level có boss ở wave cuối
BOSS_HP_MULTIPLIER = 4.0  # Boss có HP x4 so với bình thường
BOSS_REWARD_MULTIPLIER = 2.0  # Boss cho extra reward

# Mode & level  
TOTAL_LEVELS = 15  # Level với map cố định
MAX_LEVELS = 999   # Level tối đa (với map tự động)

# Level dành cho map chơi vĩnh viễn (special endless-like map with leaderboard)
PERMANENT_MAP_LEVEL = 999

def waves_in_level(level: int) -> int: 
    """Tính số wave trong level. Tăng dần theo level."""
    if level <= TOTAL_LEVELS:
        return max(1, min(level, TOTAL_LEVELS))
    else:
        # Level > 15: tăng wave mỗi 5 level
        return TOTAL_LEVELS + (level - TOTAL_LEVELS) // 5

MODES = ["Easy", "Normal", "Hard"]
MODE_PARAMS = {
    "Easy":   {"hp_mul":0.85, "spd_mul":0.95, "money":BASE_START_MONEY+100, "lives":BASE_START_LIVES+5},
    "Normal": {"hp_mul":1.00, "spd_mul":1.00, "money":BASE_START_MONEY,     "lives":BASE_START_LIVES},
    "Hard":   {"hp_mul":1.30, "spd_mul":1.15, "money":BASE_START_MONEY-300,  "lives":BASE_START_LIVES-4},
}

# Powerups
POWERUPS = {
    "freeze": {"name":"Freeze", "cost":500, "desc":"Làm chậm toàn bộ địch 50% trong 5s", "slow":0.5, "time":5.0},
    "air":    {"name":"Airstrike", "cost":1000, "desc":"Gây 120 sát thương cho tất cả địch", "damage":120},
}

# Scene identifiers (màn chơi / menu / shop / auth...)
SCENE_MENU = 0
SCENE_GAME = 1
SCENE_ALL_CLEAR = 2
SCENE_LEVEL_SELECT = 3  # Thêm scene chọn màn
SCENE_SHOP = 4
SCENE_STATS = 5
SCENE_LEADER = 6
SCENE_NAME = 7
SCENE_AUTH = 8
SCENE_MAP_PREVIEW = 9
SCENE_SETTINGS = 10  # Scene cài đặt âm thanh
