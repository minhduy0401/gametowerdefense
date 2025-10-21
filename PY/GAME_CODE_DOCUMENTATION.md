# 📖 TOWER DEFENSE GAME - DOCUMENTATION CHI TIẾT

## 🏗️ TỔNG QUAN KIẾN TRÚC

### Cấu trúc thư mục:
```
d:\PY\
├── tower_defense.py      # File chính - Game engine
├── config.py            # Cấu hình game (constants, settings)
├── entities.py          # Các đối tượng game (Enemy, Tower, Projectile) 
├── wave_manager.py      # Quản lý wave và spawn enemy
├── ui.py               # UI components (Button, draw utilities)
├── utils.py            # Utilities (load/save, âm thanh, hình ảnh)
├── projectile_effects.py # Hiệu ứng projectile đặc biệt
├── save.json           # Dữ liệu save game của player
├── accounts.json       # Database accounts (user, password, progress)
└── assets/             # Hình ảnh, âm thanh, music
```

---

## 🎮 1. TOWER_DEFENSE.PY - GAME ENGINE CHÍNH

### Lớp Game (Class Game):
Đây là lớp chính điều khiển toàn bộ game loop và logic.

#### 🎯 Thuộc tính quan trọng:

**Scene Management (Quản Lý Màn Hình):**
```python
self.scene = SCENE_MENU  # Màn hình hiện tại (menu/game/auth...)
```

**Game State (Trạng Thái Game):**
```python
self.money = 10000      # Tiền của player
self.lives = 5          # Số mạng sống
self.level = 1          # Level hiện tại
self.paused = False     # Trạng thái tạm dừng
self.game_over_reason   # Lý do thua game
```

**Collections (Bộ Sưu Tập):**
```python
self.towers = []        # Danh sách tháp đã đặt
self.enemies = []       # Danh sách enemy trên map  
self.projectiles = []   # Danh sách đạn bay
self.paths_px = []      # Đường đi của enemy (pixel coords)
```

#### 🎯 Phương thức quan trọng:

**Game Loop (Vòng Lặp Game):**
```python
def run(self):
    # Vòng lặp chính pygame
    while True:
        for event in pygame.event.get():
            self.handle_event(event)
        self.update()
        self.draw()
```

**Event Handling (Xử Lý Sự Kiện):**
```python
def handle_event(self, event):
    # Route events tới handler tương ứng theo scene
    if self.scene == SCENE_MENU: self.handle_menu_event(event)
    elif self.scene == SCENE_GAME: self.handle_game_event(event)
    # ...
```

**Core Game Logic (Logic Game Cốt Lõi):**
```python
def update(self):
    # Cập nhật game logic mỗi frame
    if self.scene == SCENE_GAME and not self.paused:
        self._update_wave_spawning()  # Spawn enemy theo wave
        self._update_towers()         # Tower tự động bắn
        self._update_projectiles()    # Di chuyển projectile
        self._update_enemies()        # Di chuyển enemy
        self._check_game_over()       # Kiểm tra thua/thắng
```

#### 🎯 Hệ thống Tower:

**Đặt Tower:**
```python
def _place_tower_click(self, mx, my):
    gx, gy = px_to_grid(mx, my)
    if (gx, gy) not in self.occupied and (gx, gy) not in self.path_cells:
        cost = TOWER_DEFS[self.selected_tower]["cost"]
        if self.money >= cost:
            tower = Tower(gx, gy, self.selected_tower)
            self.towers.append(tower)
            self.money -= cost
```

**Tower Shooting (Tháp Bắn):**
```python
def _update_towers(self):
    for tower in self.towers:
        target = tower.find_target(self.enemies)  # Tìm enemy trong tầm
        if target and tower.can_fire():
            projectile = tower.fire_at(target)    # Tạo projectile
            self.projectiles.append(projectile)
```

#### 🎯 Hệ thống Wave:

**Wave Spawning (Sinh Quái):**
```python
def _update_wave_spawning(self):
    if not self.wave_mgr.wave_active and len(self.enemies) == 0:
        if not self.wave_mgr.all_waves_done():
            self.wave_mgr.start_next_wave()  # Bắt đầu wave tiếp theo
        else:
            self.handle_level_clear()        # Hoàn thành level
```

---

## ⚙️ 2. CONFIG.PY - CẤU HÌNH GAME

### Constants quan trọng (Important Constants):

**Map & Display (Bản Đồ & Hiển Thị):**
```python
TILE = 64                    # Kích thước 1 ô grid (64x64 pixels)
GRID_W, GRID_H = 15, 10     # Kích thước map (15x10 ô)
GAME_WIDTH = 960            # Chiều rộng game area
GAME_HEIGHT = 640           # Chiều cao game area  
WIDTH = 1240               # Tổng chiều rộng màn hình
HEIGHT = 740               # Tổng chiều cao màn hình
```

**Economy (Kinh Tế):**
```python
BASE_START_MONEY = 10000    # Tiền ban đầu
BASE_START_LIVES = 5        # Số mạng ban đầu
SELL_REFUND_RATE = 0.5     # Tỷ lệ hoàn tiền khi bán tower
```

**Scenes (Màn Hình):**
```python
SCENE_MENU = 0          # Menu chính
SCENE_GAME = 1          # Trong game
SCENE_AUTH = 8          # Đăng nhập/đăng ký
SCENE_LEVEL_SELECT = 3  # Chọn màn chơi
SCENE_SETTINGS = 10     # Cài đặt âm thanh
```

### Tower Definitions (Định Nghĩa Tháp):
```python
TOWER_DEFS = {
    "gun": {
        "name": "Súng Máy",
        "cost": 120,
        "range": RANGE_PX,      # Tầm bắn
        "firerate": 1.2,        # Tốc độ bắn (shots/second)
        "damage": 18,           # Sát thương
        "sprite": "tower_lv1.png",
        "type": "basic"
    },
    # ... định nghĩa các tower khác
}
```

---

## 🤖 3. ENTITIES.PY - CÁC ĐỐI TƯỢNG GAME

### Lớp Enemy:
```python
class Enemy:
    def __init__(self, enemy_type, path_px, hp_mul=1.0, spd_mul=1.0):
        self.enemy_type = enemy_type    # "normal", "fast", "tank", "boss"
        self.path_px = path_px         # Đường đi (list of pixel coordinates)
        self.path_index = 0           # Vị trí hiện tại trên path
        self.x, self.y = path_px[0]   # Tọa độ hiện tại
        self.hp = base_hp * hp_mul    # HP được scale theo wave
        self.max_hp = self.hp
        self.speed = base_speed * spd_mul
        
    def update(self, dt):
        # Di chuyển enemy theo path
        # Trả về True nếu enemy đến cuối đường (player mất mạng)
        
    def take_damage(self, damage):
        # Nhận sát thương, trả về True nếu chết
```

### Lớp Tower:
```python
class Tower:
    def __init__(self, grid_x, grid_y, tower_type):
        self.x, self.y = grid_x, grid_y
        self.ttype = tower_type
        self.level = 1
        self.last_fire_time = 0
        
        # Load stats từ TOWER_DEFS
        defs = TOWER_DEFS[tower_type]
        self.range = defs["range"]
        self.fire_rate = defs["firerate"] 
        self.damage = defs["damage"]
        
    def find_target(self, enemies):
        # Tìm enemy gần nhất trong tầm bắn
        
    def can_fire(self):
        # Kiểm tra cooldown có thể bắn không
        
    def fire_at(self, target):
        # Tạo projectile bắn về target
```

### Lớp Projectile:
```python
class Projectile:
    def __init__(self, start_pos, target, damage, ptype="basic"):
        self.x, self.y = start_pos
        self.target = target      # Enemy được nhắm
        self.damage = damage
        self.projectile_type = ptype  # "basic", "rocket", "laser"...
        self.speed = PROJECTILE_SPEED
        
    def update(self, dt):
        # Di chuyển về phía target
        # Trả về True nếu hit target hoặc target chết
        
    def hit_target(self, enemies):
        # Xử lý sát thương khi hit
        # Projectile đặc biệt (rocket) có splash damage
```

---

## 🌊 4. WAVE_MANAGER.PY - QUẢN LÝ WAVE

### Lớp WaveManager:
```python
class WaveManager:
    def __init__(self, level, max_waves, special_mode=None):
        self.level = level
        self.max_waves = max_waves
        self.wave_no = 0
        self.special_mode = special_mode  # 'permanent' cho endless mode
        self.wave_active = False
        self.enemies_to_spawn = []
        
    def start_next_wave(self):
        self.wave_no += 1
        enemies = self._generate_wave_enemies()
        self.enemies_to_spawn = enemies
        self.wave_active = True
        
    def _generate_wave_enemies(self):
        # Tạo danh sách enemy cho wave hiện tại
        # Logic phức tạp: tăng dần độ khó, thêm boss, etc.
```

#### 🎯 Enemy Scaling Logic:
```python
def _get_scaling_factors(self):
    # HP và speed tăng dần theo wave
    if self.special_mode == 'permanent':
        # Permanent map: scaling mạnh hơn
        hp_scale = 1.0 + 0.20 * (self.wave_no - 1)
        if self.wave_no >= 5:  # Speed tăng từ wave 5
            spd_scale = 1.0 + 0.12 * (self.wave_no - 4)
    else:
        # Level thường: scaling nhẹ hơn
        hp_scale = 1.0 + 0.15 * (self.wave_no - 1)
        spd_scale = 1.0 + 0.08 * max(0, self.wave_no - 3)
```

#### 🎯 Boss Logic:
```python
def _is_boss_wave(self):
    if self.special_mode == 'permanent':
        return self.wave_no % 5 == 0  # Boss mỗi 5 wave
    else:
        return self.wave_no == self.max_waves  # Boss ở wave cuối
```

---

## 🎨 5. UI.PY - GIAO DIỆN NGƯỜI DÙNG

### Lớp Button:
```python
class Button:
    def __init__(self, rect, text, on_click, bg=(70,90,120), fg=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click    # Callback function
        self.bg = bg               # Màu nền
        self.fg = fg               # Màu chữ
        self.pressed = False       # Trạng thái nhấn
        
    def draw(self, screen, font):
        # Vẽ button với hiệu ứng hover, shadow, animation
        is_hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        # Hover effect: làm sáng màu
        # Press effect: button "lún xuống"
        # Border và shadow cho 3D effect
        
    def handle(self, event):
        # Xử lý click event
```

---

## 🛠️ 6. UTILS.PY - TIỆN ÍCH

### File I/O (Đọc/Ghi File):
```python
def load_save():
    # Load save.json, trả về dict với defaults nếu file không tồn tại
    
def save_save(save_data):
    # Ghi save_data vào save.json
    
def load_accounts():
    # Load accounts.json (database users)
    
def save_accounts(accounts_data):
    # Ghi accounts_data vào accounts.json
```

### Audio System (Hệ Thống Âm Thanh):
```python
def load_shoot_sound():
    # Load âm thanh bắn súng từ assets/shoot.wav
    
def list_music(dirpath):
    # Scan thư mục tìm file nhạc (.mp3, .wav, .ogg)
    
def play_random_music(files, volume=0.2, loop=True):
    # Phát nhạc ngẫu nhiên từ danh sách
    pygame.mixer.music.load(random_file)
    pygame.mixer.music.play(-1 if loop else 0)
```

### Graphics (Đồ Họa):
```python
def load_img(path, size=None):
    # Load hình ảnh với optional resize
    
def try_tileset():
    # Load tất cả tiles từ assets/tiles/
    return {"grass": surface, "sand_center": surface, ...}
```

### Coordinate Conversion (Chuyển Đổi Tọa Độ):
```python
def grid_to_px(gx, gy):
    # Chuyển grid coordinates (0,0) -> pixel coordinates (32, 32)
    return gx * TILE + TILE // 2, gy * TILE + TILE // 2
    
def px_to_grid(px, py):
    # Chuyển pixel -> grid coordinates
    return int(px // TILE), int(py // TILE)
```

---

## 🎯 7. PROJECTILE_EFFECTS.PY - HIỆU ỨNG ĐẶC BIỆT

### Splash Damage (Sát Thương Nổ):
```python
def apply_splash_damage(center_pos, splash_radius, damage, enemies):
    # Gây sát thương AoE cho tất cả enemy trong bán kính
    for enemy in enemies:
        distance = math.sqrt((enemy.x - center_pos[0])**2 + ...)
        if distance <= splash_radius:
            enemy.take_damage(damage * splash_factor)
```

### Slow Effect (Hiệu Ứng Làm Chậm):
```python
def apply_slow_effect(enemy, slow_factor, duration):
    # Làm chậm enemy trong thời gian nhất định
    enemy.slow_factor = slow_factor
    enemy.slow_timer = duration
```

---

## 💾 8. DỮ LIỆU SAVE SYSTEM

### save.json Structure (Cấu Trúc File Save):
```json
{
  "level_unlocked_by_mode": {
    "Easy": 5,      # Level cao nhất unlock ở chế độ Easy
    "Normal": 3,    # Level cao nhất unlock ở chế độ Normal  
    "Hard": 1       # Level cao nhất unlock ở chế độ Hard
  },
  "level_stars": {
    "Easy_L1": 3,   # Số sao đạt được ở Easy Level 1
    "Normal_L1": 2, # Key format: "{mode}_L{level}"
    ...
  },
  "player_name": "Player",
  "stars": 25,      # Tổng số sao để mua tower
  "settings": {
    "music": true,  # Bật/tắt nhạc nền
    "sfx": true,    # Bật/tắt âm thanh hiệu ứng
    "volume": 0.1   # Âm lượng nhạc
  }
}
```

### accounts.json Structure (Cấu Trúc File Tài Khoản):
```json
{
  "username": {
    "salt": "random_salt",
    "pw": "hashed_password",    # SHA256 hash
    "level_unlocked": 10,       # Legacy field
    "level_unlocked_by_mode": {
      "Easy": 15,
      "Normal": 8, 
      "Hard": 3
    },
    "stars": 45,
    "coins": 12,               # Tiền mua tower
    "unlocked_towers": ["gun", "sniper", ...],
    "leaderboard": [           # Chỉ cho Permanent Map
      {
        "name": "username",
        "level": 999,          # Permanent map level
        "wave": 25,           # Wave đạt được
        "score": 15000,       # Điểm số = kills*10 + wave*500
        "ts": 1697123456,     # Timestamp
        "is_permanent": true
      }
    ],
    "achievements": {},
    "total_kills": 1500,
    "total_towers_built": 200,
    "total_money_spent": 50000,
    ...
  }
}
```

---

## 🎯 9. GAME MECHANICS CHI TIẾT

### A. Tower System (Hệ Thống Tháp):

**Tower Types (Loại Tháp):**
- **Basic**: gun, sniper, splash (entry level)
- **Advanced**: slow, rocket, electric, laser, minigun 
- **Special**: poison, flame, mortar, ice (unlock với stars)

**Upgrade System (Hệ Thống Nâng Cấp):**
```python
def upgrade_tower(tower):
    if tower.level < 4:  # Max level 4
        cost = tower.get_upgrade_cost()
        tower.level += 1
        tower.damage *= 1.3      # +30% damage mỗi level
        tower.fire_rate *= 1.15  # +15% fire rate
        tower.range *= 1.05      # +5% range
```

### B. Economy System (Hệ Thống Kinh Tế):

**Income Sources (Nguồn Thu Nhập):**
- Kill enemy: +10-50 coins tùy loại
- Complete wave: bonus coins
- Perfect clear: bonus stars

**Expenses (Chi Tiêu):**
- Build tower: 120-400 coins
- Upgrade tower: cost tăng exponential
- Buy special tower: cost stars

### C. Difficulty Scaling (Điều Chỉnh Độ Khó):

**Mode Multipliers (Hệ Số Chế Độ):**
```python
MODE_PARAMS = {
    "Easy": {"money": 12000, "lives": 7},    # +20% money, +40% lives
    "Normal": {"money": 10000, "lives": 5},  # Standard
    "Hard": {"money": 8000, "lives": 3}      # -20% money, -40% lives
}
```

**Wave Scaling (Tăng Độ Khó Theo Wave):**
- Enemy HP: +15-20% mỗi wave
- Enemy speed: +8-12% từ wave 3-5
- Enemy count: tăng dần từ 5 -> 20+ enemies
- Boss frequency: wave cuối (normal), mỗi 5 wave (permanent)

### D. Permanent Map Special Rules (Quy Tắc Đặc Biệt Map Vĩnh Viễn):

**Infinite Mode (Chế Độ Vô Tận):**
```python
if self.is_permanent_map:
    self.max_waves = float('inf')  # Không giới hạn wave
    # Không update progression khi hoàn thành
    # Chỉ lưu điểm vào leaderboard
    
# Scoring chỉ dựa trên performance:
score = kills * 10 + wave * 500  # Bỏ lives, money, time penalty
```

---

## 🎨 10. RENDERING & GRAPHICS

### A. Draw Pipeline (Quy Trình Vẽ):
```python
def draw_game(self):
    # 1. Background
    self._draw_enhanced_background()  # Theme theo level/permanent
    
    # 2. Grid & Paths  
    self._draw_tiles_autotile()      # Vẽ đường đi
    
    # 3. Game Objects
    self.draw_towers()               # Vẽ towers với range circles
    self.draw_enemies()              # Vẽ enemies với HP bars
    self.draw_projectiles()          # Vẽ đạn bay
    
    # 4. Effects
    self.draw_death_effects()        # Hiệu ứng nổ khi enemy chết
    self.draw_damage_texts()         # Text damage bay lên
    
    # 5. UI
    self.draw_hud()                  # HUD (money, lives, wave)
    self.draw_hotbar()               # Thanh chọn tower
```

### B. Theme System (Hệ Thống Chủ Đề):
```python
def _draw_enhanced_background(self):
    if getattr(self, 'is_permanent_map', False):
        # Snow theme cho Permanent Map
        base_color = (240, 245, 255)    # Trắng tuyết
        dark_color = (220, 225, 235)
        light_color = (255, 255, 255)
    elif level <= 3:
        # Grass theme
        base_color = (45, 120, 60)
    elif level <= 6:
        # Desert theme  
        base_color = (140, 115, 80)
    # ... Sand, Lava themes
```

---

## 🎯 11. EVENT HANDLING & STATE MANAGEMENT

### A. Scene Router (Bộ Định Tuyến Màn Hình):
```python
def handle_event(self, event):
    # Route events dựa trên scene hiện tại
    scene_handlers = {
        SCENE_MENU: self.handle_menu_event,
        SCENE_GAME: self.handle_game_event, 
        SCENE_AUTH: self.handle_auth_event,
        SCENE_LEVEL_SELECT: self.handle_level_select_event,
        SCENE_SETTINGS: self.handle_settings_event
    }
    handler = scene_handlers.get(self.scene, self.handle_submenu_event)
    handler(event)
```

### B. Game Event Handling (Xử Lý Sự Kiện Game):
```python
def handle_game_event(self, event):
    if event.type == pygame.KEYDOWN:
        # Hotkeys
        if event.key == pygame.K_SPACE: self.toggle_pause()
        elif event.key == pygame.K_1: self.select_tower("gun")
        elif event.key == pygame.K_r: self.toggle_range_display()
        
    elif event.type == pygame.MOUSEBUTTONDOWN:
        mx, my = pygame.mouse.get_pos()
        
        # Click priority system:
        if self._powerup_click(mx, my): return      # 1. Powerups  
        elif self._hotbar_click(mx, my): return     # 2. Tower selection
        elif self._place_tower_click(mx, my): return # 3. Place tower
        elif self._upgrade_tower_click(mx, my): return # 4. Upgrade tower
```

---

## 🚀 12. PERFORMANCE & OPTIMIZATION

### A. Object Pooling (Tái Sử Dụng Đối Tượng):
```python
# Tái sử dụng objects thay vì tạo mới liên tục
self.death_effects = []     # Pool of reusable effect objects
self.damage_texts = []      # Pool of reusable text objects

def create_death_effect(self, pos):
    # Tìm effect object không dùng trong pool
    for effect in self.death_effects:
        if not effect.active:
            effect.reset(pos)
            return
    # Tạo mới chỉ khi pool full
    self.death_effects.append(DeathEffect(pos))
```

### B. Spatial Optimization (Tối Ưu Không Gian):
```python
def find_target(self, enemies):
    # Chỉ check enemies trong bounding box của tower range
    tower_rect = pygame.Rect(self.x*TILE - self.range, 
                           self.y*TILE - self.range,
                           self.range*2, self.range*2)
    
    candidates = [e for e in enemies if tower_rect.collidepoint(e.x, e.y)]
    # Sort by distance, return closest
```

---

## 🎯 13. CHEAT CODES & DEBUG

### Debug Commands (Lệnh Debug - trong game):
```python
# Trong handle_game_event():
if event.key == pygame.K_F1:
    self.money += 10000     # Thêm tiền
elif event.key == pygame.K_F2:  
    self.lives += 5         # Thêm mạng
elif event.key == pygame.K_F3:
    self.enemies.clear()    # Xóa tất cả enemy
```

---

## 📋 14. CODING PATTERNS & BEST PRACTICES

### A. Error Handling (Xử Lý Lỗi):
```python
def load_save():
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_SAVE.copy()  # Fallback to defaults
```

### B. Configuration-Driven Design (Thiết Kế Dựa Trên Cấu Hình):
```python
# Tất cả game constants trong config.py
# Tower stats trong TOWER_DEFS dictionary
# Dễ dàng balance và modify mà không đụng logic code
```

### C. Modular Architecture (Kiến Trúc Modular):
```python
# Mỗi file có responsibility rõ ràng:
# - entities.py: Game objects
# - wave_manager.py: Enemy spawning logic  
# - ui.py: User interface components
# - utils.py: Shared utilities
```

---

## 🎯 15. EXTENSION POINTS

### A. Thêm Tower Type Mới (Adding New Tower Type):
1. Thêm definition vào `TOWER_DEFS` trong config.py
2. Thêm sprite vào assets/
3. Implement logic đặc biệt trong `Tower.fire_at()` nếu cần
4. Thêm vào unlock progression

### B. Thêm Enemy Type Mới (Adding New Enemy Type):
1. Thêm vào `ENEMY_DEFS` trong config.py
2. Thêm sprite vào assets/enemies/
3. Implement behavior đặc biệt trong `Enemy.update()` nếu cần
4. Cập nhật wave generation logic

### C. Thêm Game Mode Mới (Adding New Game Mode):
1. Thêm constant vào `MODE_PARAMS`
2. Cập nhật UI mode selector
3. Implement logic đặc biệt trong WaveManager
4. Update save/progression system

---

## 🎯 KẾT LUẬN

Game Tower Defense này được xây dựng với kiến trúc modular rõ ràng, dễ maintain và extend. 

**Điểm mạnh:**
- Code structure rõ ràng, separation of concerns tốt
- Hệ thống save/load robust với error handling
- UI system linh hoạt với component-based approach  
- Performance tối ưu với object pooling và spatial optimization
- Configuration-driven design dễ balance

**Có thể cải thiện:**
- Thêm unit tests cho các module quan trọng
- Implement asset loading manager để tối ưu memory
- Thêm animation system cho smooth transitions
- Implement sound effects pool tương tự object pooling