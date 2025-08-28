# tower_defense.py
# Tower Defense: 15 level, wave/level = level, 3 mode, wave size 2->15,
# nâng cấp tháp, menu + login mock, âm thanh bắn (safe),
# sprite tháp xoay theo mục tiêu, sprite địch xoay theo hướng (fallback nếu thiếu).

import os, io, wave, struct
import math
import pygame
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set

# ----------------------- CONFIG -----------------------
TILE = 64
GRID_W, GRID_H = 15, 10
WIDTH, HEIGHT = GRID_W * TILE, GRID_H * TILE
FPS = 60

# Màu
WHITE=(255,255,255); BLACK=(0,0,0); GRAY=(120,120,120); DARK=(40,40,40)
GREEN=(60,200,80); RED=(220,60,60); BLUE=(60,120,255); YELLOW=(240,200,60)
ORANGE=(255,140,0); SAND=(210,190,140); GRASS=(60,170,60); PURPLE=(170,80,200)

# Thư mục asset (đặt PNG ở đây)
ASSETS_DIR = "assets"

# Kinh tế
BASE_START_MONEY = 300
BASE_START_LIVES = 20
TOWER_COST = 100
SELL_REFUND_RATE = 0.5

# Tháp
TOWER_RANGE = 150
TOWER_FIRE_RATE = 0.8    # viên/giây
PROJECTILE_SPEED = 420
PROJECTILE_DAMAGE = 25

# Nâng cấp tháp
UPGRADE_COST_LV2 = 120
UPGRADE_COST_LV3 = 180
RANGE_LV2 = int(TOWER_RANGE * 1.15)
RANGE_LV3 = int(RANGE_LV2 * 1.15)
FIRE_RATE_LV2 = TOWER_FIRE_RATE * 1.25
FIRE_RATE_LV3 = FIRE_RATE_LV2 * 1.25
DMG_LV2 = int(PROJECTILE_DAMAGE * 1.4)
DMG_LV3 = int(DMG_LV2 * 1.4)

# Địch
ENEMY_HP_BASE = 65
ENEMY_SPEED_BASE = 60
ENEMY_REWARD = 20
ENEMY_DAMAGE_TO_LIVES = 1

# Wave
SPAWN_GAP = 0.8
WAVE_COOLDOWN = 3.0

# Level & Mode
TOTAL_LEVELS = 15
def waves_in_level(level: int) -> int:
    return max(1, min(level, TOTAL_LEVELS))  # L1=1 wave … L15=15 waves

MODES = ["Easy", "Normal", "Hard"]
MODE_PARAMS = {
    "Easy":   {"hp_mul":0.85, "spd_mul":0.95, "money":BASE_START_MONEY+100, "lives":BASE_START_LIVES+5},
    "Normal": {"hp_mul":1.00, "spd_mul":1.00, "money":BASE_START_MONEY,     "lives":BASE_START_LIVES},
    "Hard":   {"hp_mul":1.30, "spd_mul":1.15, "money":BASE_START_MONEY-50,  "lives":BASE_START_LIVES-5},
}

# ------------------- TIỆN ÍCH -------------------
def grid_to_px(gx: int, gy: int) -> Tuple[float, float]:
    return gx * TILE + TILE / 2, gy * TILE + TILE / 2

def px_to_grid(px: float, py: float) -> Tuple[int, int]:
    return int(px // TILE), int(py // TILE)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def load_sprite(filename: str, size: int) -> Optional[pygame.Surface]:
    """Tải PNG từ assets/ và scale; trả None nếu lỗi/không có."""
    try:
        path = os.path.join(ASSETS_DIR, filename)
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, (size, size))
    except Exception:
        return None

def load_shoot_sound():
    """
    Safe loader:
    - Có shoot.wav cạnh file -> dùng.
    - Không có -> synth beep ngắn bằng stdlib (không cần numpy).
    - Nếu mixer lỗi -> trả None (im lặng).
    """
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
    except Exception:
        return None

    if os.path.exists("shoot.wav"):
        try:
            s = pygame.mixer.Sound("shoot.wav")
            s.set_volume(0.6)
            return s
        except Exception:
            pass

    # synth beep 120ms
    try:
        sr = 22050
        dur = 0.12
        freq = 900.0
        nframes = int(sr * dur)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(sr)
            for i in range(nframes):
                t = i / sr
                attack = min(1.0, i / (0.01*sr))
                decay = 1.0 - min(1.0, max(0, i - int((dur-0.02)*sr)) / (0.02*sr))
                env = max(0.0, attack * decay)
                sample = int(32767 * 0.8 * env * math.sin(2*math.pi*freq*t))
                wav.writeframes(struct.pack("<h", sample))
        buf.seek(0)
        s = pygame.mixer.Sound(buf); s.set_volume(0.6)
        return s
    except Exception:
        return None

# ------------------- LỚP CỐT LÕI -------------------
@dataclass
class Enemy:
    path: List[Tuple[float, float]]
    max_hp: float
    speed: float
    reward: int = ENEMY_REWARD
    lives_damage: int = ENEMY_DAMAGE_TO_LIVES
    x: float = 0.0
    y: float = 0.0
    hp: float = 1.0
    idx: int = 0
    alive: bool = True
    reached_end: bool = False

    def __post_init__(self):
        self.x, self.y = self.path[0]
        self.hp = self.max_hp
        self.idx = 1

    def update(self, dt: float, speed_scale: float = 1.0):
        if not self.alive or self.reached_end: return
        if self.idx >= len(self.path):
            self.reached_end = True
            return
        tx, ty = self.path[self.idx]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            self.idx += 1
            return
        dirx, diry = dx / dist, dy / dist
        step = self.speed * speed_scale * dt
        if step >= dist:
            self.x, self.y = tx, ty
            self.idx += 1
        else:
            self.x += dirx * step
            self.y += diry * step

    def hit(self, dmg: float):
        if not self.alive: return False
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def pos(self) -> Tuple[float, float]:
        return self.x, self.y


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    target: Optional[Enemy]
    alive: bool = True

    def update(self, dt: float):
        if not self.alive: return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.target and self.target.alive:
            tx, ty = self.target.pos()
            if (self.x - tx) ** 2 + (self.y - ty) ** 2 <= (12 ** 2):
                self.alive = False
                self.target.hit(self.damage)
        if not (0 <= self.x <= WIDTH and 0 <= self.y <= HEIGHT):
            self.alive = False


@dataclass
class Tower:
    gx: int
    gy: int
    level: int = 1
    range: float = TOWER_RANGE
    fire_rate: float = TOWER_FIRE_RATE
    cooldown: float = 0.0
    damage: int = PROJECTILE_DAMAGE
    angle: float = 0.0  # góc nòng (radian), 0 = nhìn sang phải

    def center(self) -> Tuple[float, float]:
        return grid_to_px(self.gx, self.gy)

    def update(self, dt: float):
        self.cooldown = max(0.0, self.cooldown - dt)

    def aim(self, enemies: List["Enemy"]):
        """Cập nhật góc nòng nhìn vào địch gần nhất trong tầm."""
        cx, cy = self.center()
        nearest = None
        best_d2 = float("inf")
        for e in enemies:
            if not e.alive: continue
            ex, ey = e.pos()
            d2 = (ex - cx)**2 + (ey - cy)**2
            if d2 <= self.range**2 and d2 < best_d2:
                best_d2 = d2; nearest = (ex, ey)
        if nearest:
            ex, ey = nearest
            self.angle = math.atan2(ey - cy, ex - cx)

    def try_fire(self, enemies: List[Enemy]) -> Optional[Projectile]:
        if self.cooldown > 0: return None
        cx, cy = self.center()
        target = None; best_prog = -1
        for e in enemies:
            if not e.alive: continue
            ex, ey = e.pos()
            if (ex - cx)**2 + (ey - cy)**2 <= self.range**2:
                if e.idx > best_prog:
                    best_prog = e.idx; target = e
        if not target: return None
        tx, ty = target.pos()
        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy)
        if dist == 0: return None
        vx, vy = (dx/dist)*PROJECTILE_SPEED, (dy/dist)*PROJECTILE_SPEED
        self.cooldown = 1.0 / self.fire_rate
        return Projectile(cx, cy, vx, vy, self.damage, target)

    def can_upgrade(self) -> bool:
        return self.level < 3

    def upgrade_cost(self) -> int:
        return UPGRADE_COST_LV2 if self.level == 1 else (UPGRADE_COST_LV3 if self.level == 2 else 999999)

    def apply_upgrade(self):
        if self.level == 1:
            self.level = 2
            self.range = RANGE_LV2
            self.fire_rate = FIRE_RATE_LV2
            self.damage = DMG_LV2
        elif self.level == 2:
            self.level = 3
            self.range = RANGE_LV3
            self.fire_rate = FIRE_RATE_LV3
            self.damage = DMG_LV3


class WaveManager:
    def __init__(self, path_nodes_px: List[Tuple[float, float]], hp_mul:float=1.0, spd_mul:float=1.0):
        self.path = path_nodes_px
        self.wave_no = 0
        self.enemies_left_to_spawn = 0
        self.spawn_timer = 0.0
        self.cooldown = 0.0
        self.active = False
        self.hp_mul = hp_mul
        self.spd_mul = spd_mul

    def _wave_size(self, wave_no:int) -> int:
        return min(2 + (wave_no - 1), 15)  # 2->15

    def start_next_wave(self):
        self.wave_no += 1
        size = self._wave_size(self.wave_no)
        self.enemies_left_to_spawn = size
        self.spawn_timer = 0.0
        self.active = True
        # scale theo wave + theo mode
        self.hp_scale = (1.0 + 0.16 * (self.wave_no - 1)) * self.hp_mul
        self.spd_scale = (1.0 + 0.05 * (self.wave_no - 1)) * self.spd_mul

    def update(self, dt: float) -> List[Enemy]:
        spawned: List[Enemy] = []
        if not self.active:
            self.cooldown = max(0.0, self.cooldown - dt)
            return spawned
        if self.enemies_left_to_spawn <= 0:
            self.active = False
            self.cooldown = WAVE_COOLDOWN
            return spawned
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0 and self.enemies_left_to_spawn > 0:
            self.spawn_timer = SPAWN_GAP
            self.enemies_left_to_spawn -= 1
            hp = ENEMY_HP_BASE * self.hp_scale
            spd = ENEMY_SPEED_BASE * self.spd_scale
            spawned.append(Enemy(self.path, hp, spd))
        return spawned

    def is_between_waves(self) -> bool:
        return (not self.active) and (self.cooldown > 0.0)


# ------------------- MAP / ĐƯỜNG ĐI -------------------
def build_path_nodes_for_level(level: int) -> List[Tuple[int, int]]:
    m = level % 3
    if m == 1:
        return [(-1, 2), (14, 2), (14, 5), (0, 5), (0, 8), (15, 8)]
    elif m == 2:
        return [(-1, 1), (6, 1), (6, 6), (12, 6), (12, 8), (15, 8)]
    else:
        return [(-1, 4), (4, 4), (4, 1), (10, 1), (10, 7), (15, 7)]

def expand_path_cells(nodes: List[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    cells: Set[Tuple[int, int]] = set()
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

def grid_nodes_to_px(nodes: List[Tuple[int, int]]) -> List[Tuple[float, float]]:
    return [grid_to_px(x, y) for x, y in nodes]

# ------------------- SCENE -------------------
SCENE_MENU = 0
SCENE_GAME = 1
SCENE_ALL_CLEAR = 2

# ------------------- GAME -------------------
class Game:
    def __init__(self):
        # Khởi tạo mixer chắc chắn
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
        except Exception as e:
            print("Mixer init failed:", e)

        pygame.init()
        pygame.display.set_caption("Xây thành đánh giặc - Tower Defense")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.bigfont = pygame.font.SysFont("consolas", 40, bold=True)

        self.scene = SCENE_MENU
        self.menu_mode_idx = 1  # default Normal
        self.logged_in = False
        self.nickname = "Guest"

        # Game state
        self._init_runtime("Normal", level=1)

    def _init_runtime(self, mode_name:str, level:int):
        self.mode_name = mode_name
        mp = MODE_PARAMS[self.mode_name]
        self.level = level
        self.max_waves = waves_in_level(self.level)
        self.money = mp["money"]
        self.lives = mp["lives"]
        self.paused = False
        self.speed_scale = 1.0
        self.win_level = False
        self.game_cleared = False

        # Âm thanh
        self.snd_shoot = load_shoot_sound()
        self._shoot_snd_cooldown = 0.0

        # Sprites tháp
        self.tower_sprites = [
            load_sprite("tower_lv1.png", 48),
            load_sprite("tower_lv2.png", 52),
            load_sprite("tower_lv3.png", 56),
        ]
        # Sprite địch
        self.enemy_sprite = load_sprite("enemy.png", 36)  # None nếu chưa có

        # World
        self.towers: List[Tower] = []
        self.projectiles: List[Projectile] = []
        self.enemies: List[Enemy] = []

        # Path
        self.path_nodes_grid = build_path_nodes_for_level(self.level)
        self.path_nodes_px = grid_nodes_to_px(self.path_nodes_grid)
        self.path_cells = expand_path_cells(self.path_nodes_grid)
        self.exit_cell = self.path_nodes_grid[-1]
        self.occupied: Set[Tuple[int, int]] = set()

        # Waves
        self.wave_mgr = WaveManager(self.path_nodes_px, mp["hp_mul"], mp["spd_mul"])
        self.wave_mgr.start_next_wave()

    # ------------------- LOOP -------------------
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

    # ------------------- INPUT -------------------
    def handle_event(self, event):
        if self.scene == SCENE_MENU:
            self.handle_menu_event(event)
        elif self.scene == SCENE_GAME:
            self.handle_game_event(event)
        elif self.scene == SCENE_ALL_CLEAR:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene = SCENE_MENU

    def handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.menu_mode_idx = (self.menu_mode_idx - 1) % len(MODES)
            elif event.key == pygame.K_RIGHT:
                self.menu_mode_idx = (self.menu_mode_idx + 1) % len(MODES)
            elif event.key == pygame.K_RETURN:
                mode = MODES[self.menu_mode_idx]
                self._init_runtime(mode, level=1)
                self.scene = SCENE_GAME
            elif event.key == pygame.K_l:
                self.logged_in = not self.logged_in
                self.nickname = "Player" if self.logged_in else "Guest"

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if 380 <= mx <= 580 and 360 <= my <= 400:
                mode = MODES[self.menu_mode_idx]
                self._init_runtime(mode, level=1)
                self.scene = SCENE_GAME
            if 360 <= mx <= 600 and 260 <= my <= 300:
                self.menu_mode_idx = (self.menu_mode_idx + 1) % len(MODES)
            if 360 <= mx <= 600 and 200 <= my <= 240:
                self.logged_in = not self.logged_in
                self.nickname = "Player" if self.logged_in else "Guest"

    def handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.scene = SCENE_MENU
            elif event.key == pygame.K_p:
                self.paused = not self.paused
            elif event.key == pygame.K_SPACE:
                self.speed_scale = 1.0 if self.speed_scale > 1.0 else 2.0
            elif event.key == pygame.K_r:
                self._init_runtime(self.mode_name, self.level)
            elif event.key == pygame.K_n and self.win_level:
                if self.level >= TOTAL_LEVELS:
                    self.scene = SCENE_ALL_CLEAR
                else:
                    self._init_runtime(self.mode_name, self.level + 1)

        elif event.type == pygame.MOUSEBUTTONDOWN and self.lives > 0 and not self.win_level:
            mx, my = pygame.mouse.get_pos()
            gx, gy = px_to_grid(mx, my)
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                cell = (gx, gy)
                if event.button == 1:
                    tower = self._find_tower_at(cell)
                    if tower:
                        self.try_upgrade_tower(tower)
                    else:
                        self.try_place_tower(gx, gy)
                elif event.button == 3:
                    self.try_remove_tower(gx, gy)

    def _find_tower_at(self, cell:Tuple[int,int]) -> Optional[Tower]:
        for t in self.towers:
            if (t.gx, t.gy) == cell:
                return t
        return None

    def try_place_tower(self, gx: int, gy: int):
        cell = (gx, gy)
        if cell in self.path_cells or cell in self.occupied or self.money < TOWER_COST:
            return
        self.money -= TOWER_COST
        self.towers.append(Tower(gx, gy))
        self.occupied.add(cell)

    def try_remove_tower(self, gx: int, gy: int):
        cell = (gx, gy)
        for i, t in enumerate(self.towers):
            if (t.gx, t.gy) == cell:
                del self.towers[i]
                self.occupied.discard(cell)
                self.money += int(TOWER_COST * SELL_REFUND_RATE)
                return

    def try_upgrade_tower(self, tower: Tower):
        if not tower.can_upgrade(): return
        cost = tower.upgrade_cost()
        if self.money >= cost:
            self.money -= cost
            tower.apply_upgrade()

    # ------------------- UPDATE -------------------
    def update(self, dt: float):
        if self.scene != SCENE_GAME: return
        if self.paused or self.lives <= 0 or self.win_level:
            return

        self._shoot_snd_cooldown = max(0.0, self._shoot_snd_cooldown - dt)
        sdt = dt * self.speed_scale

        # spawn
        spawned = self.wave_mgr.update(sdt)
        self.enemies.extend(spawned)

        # enemies
        for e in self.enemies:
            e.update(sdt, speed_scale=1.0)

        # reach end
        for e in self.enemies:
            if e.alive and e.reached_end:
                e.alive = False
                self.lives -= e.lives_damage

        # towers
        for t in self.towers:
            t.update(sdt)
            t.aim(self.enemies)
            prj = t.try_fire(self.enemies)
            if prj:
                self.projectiles.append(prj)
                if self.snd_shoot and self._shoot_snd_cooldown <= 0.0:
                    try: self.snd_shoot.play()
                    except Exception: pass
                    self._shoot_snd_cooldown = 0.06

        # projectiles
        for p in self.projectiles:
            p.update(sdt)

        # reward
        for e in self.enemies:
            if not e.alive and e.hp <= 0 and e.reward > 0:
                self.money += e.reward
                e.reward = 0

        # cleanup
        self.enemies = [e for e in self.enemies if e.alive]
        self.projectiles = [p for p in self.projectiles if p.alive]

        # next wave / win level
        if (not self.wave_mgr.active) and self.wave_mgr.cooldown <= 0.0 and len(self.enemies) == 0:
            if self.wave_mgr.wave_no >= self.max_waves:
                self.win_level = True
                return
            else:
                self.wave_mgr.start_next_wave()

    # ------------------- DRAW -------------------
    def draw(self):
        if self.scene == SCENE_MENU:
            self.draw_menu()
        elif self.scene == SCENE_GAME:
            self.draw_game()
        elif self.scene == SCENE_ALL_CLEAR:
            self.draw_all_clear()
        pygame.display.flip()

    def draw_menu(self):
        self.screen.fill((25,25,30))
        title = self.bigfont.render("Tower Defense", True, ORANGE)
        self.screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))

        # login mock
        if self.logged_in:
            login_text = f"Login with Google (mock): Signed in as {self.nickname}  (click to sign out)"
        else:
            login_text = "Login with Google (mock): Click to sign in"
        pygame.draw.rect(self.screen, (60,60,90), (360,200,240,40), border_radius=8)
        self.screen.blit(self.font.render(login_text, True, WHITE), (370, 210))

        # mode
        mode = MODES[self.menu_mode_idx]
        pygame.draw.rect(self.screen, (60,60,90), (360,260,240,40), border_radius=8)
        self.screen.blit(self.font.render(f"Mode: {mode}  (← →)", True, WHITE), (370, 270))

        # start
        pygame.draw.rect(self.screen, (90,140,90), (380,360,200,40), border_radius=10)
        self.screen.blit(self.font.render("Start (Enter)", True, WHITE), (420, 370))

        hints = [
            "Điều khiển:",
            "- Trái: đặt tháp / nâng cấp (nhấp vào tháp)",
            "- Phải: bán tháp (+50%)",
            "- SPACE: tua nhanh  |  P: tạm dừng",
            "- R: chơi lại level  |  ESC: về menu",
        ]
        for i, s in enumerate(hints):
            self.screen.blit(self.font.render(s, True, WHITE), (40, 450 + i*22))

    def draw_all_clear(self):
        self.screen.fill((10,10,20))
        msg = self.bigfont.render("HOÀN THÀNH 15 LEVEL! 🎉", True, ORANGE)
        self.screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))
        tip = self.font.render("Nhấn ESC để về menu", True, WHITE)
        self.screen.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))

    def draw_game(self):
        self.draw_grid()
        self.draw_projectiles()
        self.draw_enemies()
        self.draw_towers()
        self.draw_hud()

    def draw_grid(self):
        self.screen.fill(GRASS)
        for (gx, gy) in self.path_cells:
            rect = pygame.Rect(gx * TILE, gy * TILE, TILE, TILE)
            pygame.draw.rect(self.screen, SAND, rect)
        ex, ey = self.exit_cell
        ex = clamp(ex, 0, GRID_W - 1); ey = clamp(ey, 0, GRID_H - 1)
        base_rect = pygame.Rect(ex * TILE + 8, ey * TILE + 8, TILE - 16, TILE - 16)
        pygame.draw.rect(self.screen, PURPLE, base_rect, border_radius=6)
        for x in range(GRID_W + 1):
            pygame.draw.line(self.screen, DARK, (x * TILE, 0), (x * TILE, HEIGHT))
        for y in range(GRID_H + 1):
            pygame.draw.line(self.screen, DARK, (0, y * TILE), (WIDTH, y * TILE))

    def draw_enemies(self):
        for e in self.enemies:
            x, y = e.pos()

            if self.enemy_sprite:
                # Xoay theo hướng waypoint tiếp theo
                img = self.enemy_sprite
                if e.idx < len(self.path_nodes_px):
                    tx, ty = self.path_nodes_px[e.idx]
                    angle = -math.degrees(math.atan2(ty - y, tx - x))  # trục y xuống -> đảo dấu
                    img = pygame.transform.rotate(self.enemy_sprite, angle)
                rect = img.get_rect(center=(int(x), int(y)))
                self.screen.blit(img, rect)
            else:
                pygame.draw.circle(self.screen, RED, (int(x), int(y)), 16)

            # HP bar
            ratio = max(0.0, e.hp / e.max_hp)
            w, bh = 30, 4
            bar_bg = pygame.Rect(int(x - w/2), int(y - 26), w, bh)
            bar_fg = pygame.Rect(int(x - w/2), int(y - 26), int(w * ratio), bh)
            pygame.draw.rect(self.screen, DARK, bar_bg)
            pygame.draw.rect(self.screen, GREEN, bar_fg)

    def draw_towers(self):
        for t in self.towers:
            cx, cy = t.center()
            idx = max(0, min(t.level - 1, 2))
            base_img = self.tower_sprites[idx] if hasattr(self, "tower_sprites") else None

            if base_img:
                angle_deg = -math.degrees(t.angle)  # 0° = nhìn sang phải
                img = pygame.transform.rotate(base_img, angle_deg)
                rect = img.get_rect(center=(int(cx), int(cy)))
                self.screen.blit(img, rect)
            else:
                pygame.draw.circle(self.screen, BLUE, (int(cx), int(cy)), 18)
                pygame.draw.circle(self.screen, WHITE, (int(cx), int(cy)), 6)

    def draw_projectiles(self):
        for p in self.projectiles:
            pygame.draw.circle(self.screen, YELLOW, (int(p.x), int(p.y)), 4)

    def draw_hud(self):
        name = self.nickname if self.logged_in else "Player"
        txt = (
            f"{name} | Mode {self.mode_name} | "
            f"Level {self.level}/{TOTAL_LEVELS} | "
            f"Wave {self.wave_mgr.wave_no}/{self.max_waves} | "
            f"$ {self.money} | ♥ {self.lives} | "
            f"{'PAUSE' if self.paused else ('x2' if self.speed_scale>1 else 'x1')}"
        )
        self.screen.blit(self.font.render(txt, True, WHITE), (8, 8))

        mx, my = pygame.mouse.get_pos()
        gx, gy = px_to_grid(mx, my)
        t = self._find_tower_at((gx, gy))
        if t:
            up_txt = "MAX" if not t.can_upgrade() else f"Upgrade cost: {t.upgrade_cost()}"
            tip = f"Tower Lv{t.level} | Range {int(t.range)} | FireRate {t.fire_rate:.2f}/s | Dmg {t.damage} | {up_txt} (Left Click)"
            self.screen.blit(self.font.render(tip, True, WHITE), (8, 32))
        else:
            if self.wave_mgr.active:
                status = f"Đang sinh: còn {self.wave_mgr.enemies_left_to_spawn} địch"
            elif self.wave_mgr.is_between_waves():
                status = f"Nghỉ giữa wave: {self.wave_mgr.cooldown:.1f}s"
            else:
                status = "Chuẩn bị wave tiếp theo..."
            self.screen.blit(self.font.render(status, True, WHITE), (8, 32))

        if self.lives <= 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            gg = self.bigfont.render("THUA RỒI!", True, ORANGE)
            tip = self.font.render("Nhấn R để chơi lại level | ESC về menu", True, WHITE)
            self.screen.blit(gg, gg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            self.screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))

        if self.win_level:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            gg = self.bigfont.render("LEVEL CLEARED!", True, ORANGE)
            tip = self.font.render("Nhấn N để sang level mới | R chơi lại", True, WHITE)
            self.screen.blit(gg, gg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            self.screen.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))


def main():
    Game().run()

if __name__ == "__main__":
    main()
