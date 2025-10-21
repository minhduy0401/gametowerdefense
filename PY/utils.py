import os, json, time, math, random
import pygame
from typing import List, Tuple, Optional, Set, Dict
from config import ASSETS_DIR, SAVE_FILE, ACCOUNTS_FILE, TILE

# Grid helpers

def grid_to_px(gx: int, gy: int) -> Tuple[float, float]:
    return gx * TILE + TILE / 2, gy * TILE + TILE / 2

def px_to_grid(px: float, py: float) -> Tuple[int, int]:
    return int(px // TILE), int(py // TILE)

def clamp(v, lo, hi): return max(lo, min(hi, v))

# Image/sprite loading
def load_img(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        return None

def load_sprite(filename: str, size: int):
    return load_img(os.path.join(ASSETS_DIR, filename), (size, size))

def try_tileset():
    size = (TILE, TILE)
    base = ASSETS_DIR
    tiles = {
        "grass": load_img(os.path.join(base, "tiles", "grass.png"), size),
        "sand_center": load_img(os.path.join(base, "tiles", "sand_center.png"), size),
        "sand_edge_n": load_img(os.path.join(base, "tiles", "sand_edge_n.png"), size),
        "sand_edge_s": load_img(os.path.join(base, "tiles", "sand_edge_s.png"), size),
        "sand_edge_w": load_img(os.path.join(base, "tiles", "sand_edge_w.png"), size),
        "sand_edge_e": load_img(os.path.join(base, "tiles", "sand_edge_e.png"), size),
        "sand_corner_ne": load_img(os.path.join(base, "tiles", "sand_corner_ne.png"), size),
        "sand_corner_nw": load_img(os.path.join(base, "tiles", "sand_corner_nw.png"), size),
        "sand_corner_se": load_img(os.path.join(base, "tiles", "sand_corner_se.png"), size),
        "sand_corner_sw": load_img(os.path.join(base, "tiles", "sand_corner_sw.png"), size),
        "bush": load_img(os.path.join(base, "decor", "bush.png"), (int(TILE*0.9), int(TILE*0.9))),
        "rock": load_img(os.path.join(base, "decor", "rock.png"), (int(TILE*0.7), int(TILE*0.7))),
        "base": load_img(os.path.join(base, "decor", "base.png"), (int(TILE*0.9), int(TILE*0.9))),
        "gate": load_img(os.path.join(base, "decor", "gate.png"), (int(TILE*0.9), int(TILE*0.9))),
    }
    if tiles["grass"] is None and tiles["sand_center"] is None:
        return None
    return tiles

# Sound helpers
def load_shoot_sound():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
    except Exception:
        return None
    for fn in ["shoot.wav", os.path.join(ASSETS_DIR, "shoot.wav")]:
        if os.path.exists(fn):
            try:
                s = pygame.mixer.Sound(fn); s.set_volume(0.15); return s  # Âm lượng súng
            except Exception: pass
    # No bundled shoot sound found and synth fallback removed for simplicity
    return None

# Music
def list_music(dirpath):
    try:
        if not os.path.isdir(dirpath): return []
        files = [os.path.join(dirpath, f) for f in os.listdir(dirpath) if f.lower().endswith((".ogg",".mp3",".wav"))]
        return files
    except Exception:
        return []

def play_random_music(files, volume=0.2, loop=True):
    if not files:
        try: pygame.mixer.music.stop()
        except: pass
        return
    try:
        f = random.choice(files)
        pygame.mixer.music.load(f)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1 if loop else 0)
    except Exception:
        pass

# Save / accounts
DEFAULT_SAVE = {
    "player_name": "Player",
    "level_unlocked": 1,  # Giữ lại để tương thích với save cũ
    "level_unlocked_by_mode": {"Easy": 1, "Normal": 1, "Hard": 1},  # 🆕 Tiến độ riêng theo chế độ
    "level_stars": {},  # 🆕 Sao đạt được cho mỗi level theo format "Mode_L{level}": stars
    "unlocked_towers": [],  
    "achievements": {},
    "leaderboard": [],
    "stars": 0,
    "settings": {"music": True, "sfx": True, "volume": 0.1},  #Âm lượng nhạc
}

SAVE_KEYS_ORDER = list(DEFAULT_SAVE.keys())


def load_save():
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE,"r",encoding="utf-8") as f:
                data=json.load(f)
                for k in SAVE_KEYS_ORDER:
                    if k not in data: data[k] = DEFAULT_SAVE[k]
                return data
    except Exception:
        pass
    return DEFAULT_SAVE.copy()


def save_save(data):
    try:
        with open(SAVE_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
    except Exception as e:
        print("Save failed:", e)

# Accounts (simple wrapper used by game)
def load_accounts():
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_accounts(db: dict):
    try:
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save accounts failed:", e)
