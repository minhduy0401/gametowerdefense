import math
import random
import pygame
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

from config import PROJECTILE_SPEED, WIDTH, HEIGHT, TOWER_UPGRADE
from utils import grid_to_px


@dataclass
class Enemy:
    path: List[Tuple[float, float]]
    max_hp: float
    speed: float
    reward: int
    etype: str = "normal"
    x: float = 0.0
    y: float = 0.0
    hp: float = 1.0
    idx: int = 0
    alive: bool = True
    reached_end: bool = False
    slow_mul: float = 1.0
    slow_timer: float = 0.0
    # 🆕 Enhanced enemy features
    size_mul: float = 1.0      # Kích thước hiển thị (0.8 cho scout, 1.6 cho boss)
    slow_resist: float = 0.0   # Kháng slow (0.5 cho tank = chỉ bị slow 50%)
    regen_rate: float = 0.0    # Hồi máu/giây (5 cho commander)
    regen_timer: float = 0.0   # Timer cho regeneration
    
    # 🆕 Poison DoT system
    poison_damage: float = 0.0  # Sát thương độc mỗi giây
    poison_timer: float = 0.0   # Thời gian còn lại của poison
    poison_tick_timer: float = 0.0  # Timer để tick poison damage
    
    # 🆕 Junction system
    junction_paths: Optional[List[List[Tuple[float, float]]]] = None
    switch_count: int = 0       # Số lần đã chuyển path
    last_switch_idx: int = -1   # Waypoint cuối cùng đã switch để tránh switch liên tục
    
    def __post_init__(self):
        self.x, self.y = self.path[0]
        self.hp = self.max_hp
        self.idx = 1
        self.regen_timer = 1.0  # Bắt đầu regen sau 1 giây
        self.junction_paths = []
    
    def set_junction_paths(self, junction_paths: List[List[Tuple[float, float]]]):
        """Thiết lập các đường junction mà enemy có thể chuyển sang"""
        self.junction_paths = junction_paths if junction_paths else []
    
    def _check_junction_switch(self):
        """Kiểm tra và chuyển sang junction path nếu có thể"""
        # 🔧 ENHANCED safety checks
        if not self.junction_paths:
            return
        if self.idx >= len(self.path):
            return
        if self.idx == self.last_switch_idx:  # Tránh switch liên tục tại cùng waypoint
            return
        if not self.alive:  # Không switch nếu enemy đã chết
            return
            
        current_pos = (self.x, self.y)
        
        # 🆕 Tất cả enemy đều có khả năng chuyển đường cao - tạo nhiều tuyến đường
        if self.etype == "tank":
            max_switches = 3
            switch_chance = 0.8  # Tank rất hay chuyển đường
        elif self.etype == "fast":
            max_switches = 2  
            switch_chance = 0.6  # Fast enemy chuyển đường nhanh
        elif self.etype == "boss":
            max_switches = 2
            switch_chance = 0.5  # Boss có chiến thuật
        else:  # normal
            max_switches = 2
            switch_chance = 0.5  # Normal enemy cũng có thể chuyển đường
        
        # Nếu đã chuyển quá nhiều lần thì dừng
        if self.switch_count >= max_switches:
            return
        
        # 🆕 Cải tiến junction switching - kiểm tra tất cả junction paths và chọn tốt nhất
        best_junction = None
        best_distance = float('inf')
        
        # Tìm junction path gần nhất
        for i, junction_path in enumerate(self.junction_paths):
            if len(junction_path) < 2:
                continue
                
            start_pos = junction_path[0]
            # Kiểm tra khoảng cách đến điểm đầu junction
            dist = math.hypot(current_pos[0] - start_pos[0], 
                             current_pos[1] - start_pos[1])
            
            # Nếu đủ gần và gần hơn các junction khác
            if dist < 96 and dist < best_distance:  # Tăng bán kính từ 64→96px
                best_junction = (i, junction_path, dist)
                best_distance = dist
        
        # Nếu tìm thấy junction phù hợp, thử chuyển
        if best_junction and random.random() < switch_chance:
            i, junction_path, dist = best_junction
            print(f"🔄 {self.etype.upper()} switching to junction path {i} (switch #{self.switch_count + 1}, dist: {dist:.1f})")
            
            # 🔧 SAFETY CHECK: Đảm bảo junction path hợp lệ
            if len(junction_path) >= 2:
                self.path = junction_path
                # 🔧 Tìm waypoint gần nhất trong junction path thay vì hardcode idx=1
                closest_idx = 0
                closest_dist = float('inf')
                current_pos = (self.x, self.y)
                
                for wp_idx, (wp_x, wp_y) in enumerate(junction_path):
                    wp_dist = math.hypot(current_pos[0] - wp_x, current_pos[1] - wp_y)
                    if wp_dist < closest_dist:
                        closest_dist = wp_dist
                        closest_idx = wp_idx
                
                # Bắt đầu từ waypoint tiếp theo (không quay lại)
                self.idx = min(closest_idx + 1, len(junction_path) - 1)
                self.switch_count += 1
                self.last_switch_idx = self.idx
                
                print(f"   → Started at waypoint {self.idx}/{len(junction_path)-1}, closest was {closest_idx}")
            else:
                print(f"   ❌ Junction path {i} too short ({len(junction_path)} waypoints), skipping")

    def update(self, dt: float):
        if not self.alive or self.reached_end:
            return
            
        # 🆕 Regeneration (commander feature)
        if self.regen_rate > 0:
            self.regen_timer -= dt
            if self.regen_timer <= 0:
                if self.hp < self.max_hp and self.hp > 0:
                    self.hp = min(self.max_hp, self.hp + self.regen_rate * dt)
                    
        # Slow effect handling
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_mul = 1.0
        
        # 🆕 Poison DoT handling
        if self.poison_timer > 0:
            self.poison_timer -= dt
            self.poison_tick_timer -= dt
            
            # Tick poison damage mỗi giây
            if self.poison_tick_timer <= 0:
                self.hit(self.poison_damage)  # Gây poison damage
                self.poison_tick_timer = 1.0  # Reset tick timer cho 1 giây tiếp theo
            
            # Hết thời gian poison
            if self.poison_timer <= 0:
                self.poison_damage = 0.0
                self.poison_tick_timer = 0.0
                
        # 🔧 MOVEMENT với safety checks
        if self.idx >= len(self.path):
            self.reached_end = True
            return
            
        # 🔧 Đảm bảo idx không vượt quá path bounds
        if self.idx < 0:
            self.idx = 0
        if self.idx >= len(self.path):
            self.reached_end = True
            return
            
        tx, ty = self.path[self.idx]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        
        # 🔧 Nếu quá gần waypoint hiện tại, chuyển sang waypoint tiếp theo
        if dist < 1e-6:
            self.idx += 1
            # 🔧 Check bounds sau khi tăng idx
            if self.idx >= len(self.path):
                self.reached_end = True
            return
            
        dirx, diry = dx / dist, dy / dist
        step = self.speed * self.slow_mul * dt
        
        if step >= dist:
            # Đã đến waypoint target
            self.x, self.y = tx, ty
            self.idx += 1
            
            # 🔧 Check bounds trước khi junction switch
            if self.idx < len(self.path):
                # 🆕 Check junction khi đến waypoint mới
                self._check_junction_switch()
            else:
                self.reached_end = True
        else:
            # Di chuyển về phía waypoint target
            self.x += dirx * step
            self.y += diry * step

    def hit(self, dmg: float):
        if not self.alive:
            return False
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def apply_slow(self, mul: float, t: float):
        # 🆕 Apply slow resistance (tank feature)
        if self.slow_resist > 0:
            # Giảm hiệu quả slow dựa trên kháng slow
            effective_mul = 1.0 - ((1.0 - mul) * (1.0 - self.slow_resist))
            effective_time = t * (1.0 - self.slow_resist * 0.5)  # Giảm thời gian slow
            self.slow_mul = min(self.slow_mul, effective_mul)
            self.slow_timer = max(self.slow_timer, effective_time)
        else:
            # Slow bình thường
            self.slow_mul = min(self.slow_mul, mul)
            self.slow_timer = max(self.slow_timer, t)
    
    def apply_poison(self, poison_dmg: float, poison_time: float):
        """🆕 Áp dụng hiệu ứng poison DoT"""
        # Nếu đã bị poison, làm mới thời gian và cộng damage
        if self.poison_timer > 0:
            self.poison_damage = max(self.poison_damage, poison_dmg)  # Lấy poison mạnh hơn
            self.poison_timer = max(self.poison_timer, poison_time)   # Làm mới thời gian
        else:
            self.poison_damage = poison_dmg
            self.poison_timer = poison_time
        self.poison_tick_timer = 1.0  # Tick đầu tiên sau 1 giây

    def pos(self) -> Tuple[float, float]:
        return self.x, self.y


@dataclass 
class DamageText:
    """Hiệu ứng text sát thương bay lên"""
    x: float
    y: float
    damage: int
    max_duration: float = 1.0
    time_left: float = 1.0
    alive: bool = True
    
    def __post_init__(self):
        self.time_left = self.max_duration
        self.start_y = self.y
        
    def update(self, dt: float):
        if not self.alive:
            return
            
        self.time_left -= dt
        if self.time_left <= 0:
            self.alive = False
            return
            
        # Text bay lên và mờ dần
        self.y = self.start_y - (1 - self.time_left / self.max_duration) * 40
        
    def draw(self, screen):
        if not self.alive:
            return
            
        alpha_factor = self.time_left / self.max_duration
        alpha = int(255 * alpha_factor)
        
        if alpha > 0:
            # Chọn màu dựa trên sát thương
            if self.damage >= 100:
                color = (255, 100, 100)  # Đỏ cho sát thương cao
            elif self.damage >= 50:
                color = (255, 200, 100)  # Cam cho sát thương trung bình  
            else:
                color = (255, 255, 100)  # Vàng cho sát thương thấp
                
            # Vẽ text
            font = pygame.font.Font(None, 24)
            text_surface = font.render(str(self.damage), True, color)
            screen.blit(text_surface, (int(self.x - text_surface.get_width()//2), int(self.y)))


@dataclass
class DeathEffect:
    """Hiệu ứng khi địch chết"""
    x: float
    y: float
    enemy_type: str
    max_duration: float = 1.0
    time_left: float = 1.0
    particles: Optional[List[dict]] = None
    alive: bool = True
    
    def __post_init__(self):
        self.time_left = self.max_duration
        
        # Tạo particles dựa trên loại địch với hiệu ứng đặc biệt
        self.particles = []
        if self.enemy_type == "boss":
            num_particles = 12
            speed_range = (80, 200)
            self.max_duration = 1.5  # Boss chết lâu hơn
        elif self.enemy_type == "tank":
            num_particles = 8
            speed_range = (60, 160)
            self.max_duration = 1.2
        elif self.enemy_type == "fast":
            num_particles = 6
            speed_range = (100, 220)  # Fast địch chết nhanh với particles nhanh
            self.max_duration = 0.8
        else:  # normal
            num_particles = 5
            speed_range = (50, 150)
        
        self.time_left = self.max_duration
        
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            particle_size = random.uniform(3, 8) if self.enemy_type == "boss" else random.uniform(2, 6)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': 1.0,
                'size': particle_size,
                'rotation': random.uniform(0, 360),  # Để tạo hiệu ứng xoay
                'rot_speed': random.uniform(-360, 360)
            })
    
    def update(self, dt: float):
        if not self.alive:
            return
            
        self.time_left -= dt
        if self.time_left <= 0:
            self.alive = False
            return
            
        # Update particles
        if self.particles:
            for particle in self.particles:
                particle['x'] += particle['vx'] * dt
                particle['y'] += particle['vy'] * dt
                particle['vy'] += 200 * dt  # Gravity
                particle['vx'] *= 0.98  # Friction
                particle['life'] = self.time_left / self.max_duration
                particle['rotation'] += particle['rot_speed'] * dt
            
    def draw(self, screen):
        if not self.alive:
            return
            
        # Chọn màu dựa trên loại địch
        if self.enemy_type == "boss":
            base_color = (160, 100, 200)  # Purple
        elif self.enemy_type == "tank":
            base_color = (200, 60, 60)    # Red
        elif self.enemy_type == "fast":
            base_color = (120, 200, 120)  # Green
        else:
            base_color = (140, 140, 120)  # Gray
            
        # Vẽ particles
        if self.particles:
            alpha_factor = self.time_left / self.max_duration
            for particle in self.particles:
                alpha = int(255 * alpha_factor * particle['life'])
                if alpha > 0:
                    size = max(1, int(particle['size'] * alpha_factor))
                    color = (
                        min(255, int(base_color[0] + (255 - base_color[0]) * (1 - alpha_factor))),
                        min(255, int(base_color[1] + (255 - base_color[1]) * (1 - alpha_factor))),
                        min(255, int(base_color[2] + (255 - base_color[2]) * (1 - alpha_factor)))
                    )
                    
                    # Vẽ particle với hiệu ứng đặc biệt cho boss
                    try:
                        if self.enemy_type == "boss":
                            # Boss có hiệu ứng sáng lóa
                            pygame.draw.circle(screen, (255, 255, 255), 
                                             (int(particle['x']), int(particle['y'])), size + 2)
                        pygame.draw.circle(screen, color, 
                                         (int(particle['x']), int(particle['y'])), size)
                    except:
                        pass  # Ignore if particle is out of screen


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    target: Optional[Enemy]
    splash: float = 0.0
    slow_mul: float = 1.0
    slow_time: float = 0.0
    poison_damage: float = 0.0  # 🆕 Poison damage per second
    poison_time: float = 0.0    # 🆕 Poison duration
    alive: bool = True
    # 🆕 Các thuộc tính mới cho hiệu ứng đặc biệt
    projectile_type: str = "basic"  # basic, laser, rocket, electric, poison, flame, ice, etc.
    trail_points: Optional[List] = None  # Để tạo đuôi đạn
    rotation: float = 0.0  # Góc xoay của đạn
    lifetime: float = 0.0  # Thời gian sống
    max_lifetime: float = 3.0  # Thời gian sống tối đa
    special_data: Optional[Dict] = None  # Dữ liệu đặc biệt cho từng loại đạn
    
    def __post_init__(self):
        if self.trail_points is None:
            self.trail_points = []
        if self.special_data is None:
            self.special_data = {}

    def update(self, dt: float, enemies: List[Enemy]):
        if not self.alive:
            return
            
        # 🆕 Cập nhật thời gian sống và hiệu ứng đặc biệt
        self.lifetime += dt
        if self.lifetime > self.max_lifetime:
            self.alive = False
            return
            
        # 🆕 Cập nhật góc xoay dựa trên hướng di chuyển
        if abs(self.vx) > 1e-6 or abs(self.vy) > 1e-6:
            self.rotation = math.atan2(self.vy, self.vx)
            
        # 🆕 Thêm điểm vào trail (đuôi đạn)
        if self.projectile_type in ["laser", "rocket", "electric", "ice"] and self.trail_points is not None:
            self.trail_points.append((self.x, self.y, self.lifetime))
            # Giữ tối đa 10 điểm trail
            if len(self.trail_points) > 10:
                self.trail_points.pop(0)

        # If target alive -> home to it
        if self.target and self.target.alive:
            tx, ty = self.target.pos()
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)

            spd = math.hypot(self.vx, self.vy)
            if spd <= 1e-6:
                spd = PROJECTILE_SPEED

            if dist <= max(10.0, spd * dt):
                self.alive = False
                self.target.hit(self.damage)
                if self.slow_time > 0:
                    self.target.apply_slow(self.slow_mul, self.slow_time)
                # 🆕 Apply poison effect
                if self.poison_time > 0:
                    self.target.apply_poison(self.poison_damage, self.poison_time)
                if self.splash > 0:
                    r2 = self.splash * self.splash
                    for e in enemies:
                        if e is self.target or not e.alive:
                            continue
                        ex, ey = e.pos()
                        if (ex - tx) ** 2 + (ey - ty) ** 2 <= r2:
                            e.hit(self.damage * 0.8)
                            if self.slow_time > 0:
                                e.apply_slow(self.slow_mul, self.slow_time)
                            # 🆕 Apply poison to splash targets too
                            if self.poison_time > 0:
                                e.apply_poison(self.poison_damage, self.poison_time)
                return
            dirx, diry = dx / dist, dy / dist
            self.vx, self.vy = dirx * spd, diry * spd

        # Move
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Out of screen
        if not (0 <= self.x <= WIDTH and 0 <= self.y <= HEIGHT):
            self.alive = False


@dataclass
class Tower:
    gx: int
    gy: int
    ttype: str = "gun"
    level: int = 1
    range: float = 150
    fire_rate: float = 0.8
    cooldown: float = 0.0
    damage: int = 25
    angle: float = 0.0
    splash: float = 0.0
    slow_mul: float = 1.0
    slow_time: float = 0.0
    poison_damage: float = 0.0  # 🆕 Poison damage per second
    poison_time: float = 0.0    # 🆕 Poison duration

    def center(self) -> Tuple[float, float]:
        return grid_to_px(self.gx, self.gy)

    def update(self, dt: float):
        self.cooldown = max(0.0, self.cooldown - dt)

    def aim(self, enemies):
        cx, cy = self.center()
        nearest = None
        best_dy = float("inf")
        from config import H_RANGE_PX
        for e in enemies:
            if not e.alive:
                continue
            ex, ey = e.pos()
            dy = abs(ey - cy)
            dx = abs(ex - cx)
            if dy <= self.range and dx <= H_RANGE_PX and dy < best_dy:
                best_dy = dy
                nearest = (ex, ey)
        if nearest:
            ex, ey = nearest
            self.angle = math.atan2(ey - cy, ex - cx)

    def try_fire(self, enemies):
        if self.cooldown > 0:
            return None
        cx, cy = self.center()

        target = None
        best_prog = -1
        for e in enemies:
            if not e.alive:
                continue
            ex, ey = e.pos()
            from config import H_RANGE_PX
            if abs(ey - cy) <= self.range and abs(ex - cx) <= H_RANGE_PX:
                prog = e.idx
                if prog > best_prog:
                    best_prog = prog
                    target = e

        if not target:
            return None

        tx, ty = target.pos()
        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy) or 1.0
        
        # 🆕 Tốc độ và loại projectile dựa trên tháp
        speed = PROJECTILE_SPEED
        projectile_type = "basic"
        max_lifetime = 3.0
        special_data = {}
        
        if self.ttype == "sniper":
            speed = PROJECTILE_SPEED * 1.1
            projectile_type = "sniper"
        elif self.ttype == "laser":
            speed = PROJECTILE_SPEED * 2.0
            projectile_type = "laser"
            max_lifetime = 1.5  # Laser nhanh, sống ngắn
        elif self.ttype == "rocket":
            speed = PROJECTILE_SPEED * 0.7
            projectile_type = "rocket" 
            max_lifetime = 4.0  # Rocket chậm, sống lâu
        elif self.ttype == "electric":
            speed = PROJECTILE_SPEED * 1.3
            projectile_type = "electric"
            special_data = {"chain_count": 0, "max_chains": 3}
        elif self.ttype == "poison":
            speed = PROJECTILE_SPEED * 0.9
            projectile_type = "poison"
        elif self.ttype == "flame":
            speed = PROJECTILE_SPEED * 1.1
            projectile_type = "flame"
        elif self.ttype == "ice":
            speed = PROJECTILE_SPEED * 0.8
            projectile_type = "ice"
        elif self.ttype == "minigun":
            speed = PROJECTILE_SPEED * 1.4
            projectile_type = "minigun"
        elif self.ttype == "mortar":
            speed = PROJECTILE_SPEED * 0.5
            projectile_type = "mortar"
            max_lifetime = 5.0  # Mortar bay cao, sống lâu
            
        vx, vy = (dx / dist) * speed, (dy / dist) * speed
        self.cooldown = 1.0 / self.fire_rate
        
        return Projectile(
            cx, cy, vx, vy, self.damage, target,
            splash=self.splash, slow_mul=self.slow_mul, slow_time=self.slow_time,
            poison_damage=self.poison_damage, poison_time=self.poison_time,  # 🆕 Poison data
            projectile_type=projectile_type, trail_points=[], rotation=0.0,
            lifetime=0.0, max_lifetime=max_lifetime, special_data=special_data
        )

    def can_upgrade(self) -> bool:
        return self.level < 3

    def upgrade_cost(self) -> int:
        if self.level<=2:
            return TOWER_UPGRADE[self.level-1]["cost"]
        return 10**9

    def apply_upgrade(self):
        if not self.can_upgrade():
            return
        u = TOWER_UPGRADE[self.level-1]
        self.level += 1
        self.range = int(self.range * u["range"])  
        self.fire_rate = self.fire_rate * u["firerate"]
        self.damage = int(self.damage * u["damage"])