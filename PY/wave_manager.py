import random
from typing import List, Tuple
from entities import Enemy
from config import ENEMY_TYPES, SPAWN_GAP, WAVE_COOLDOWN, BOSS_LEVELS, BOSS_HP_MULTIPLIER, BOSS_REWARD_MULTIPLIER, waves_in_level

class WaveManager:
    def __init__(self, paths_px: List[List[Tuple[float, float]]], hp_mul: float = 1.0, spd_mul: float = 1.0, level: int = 1, special_mode: str = None):
        self.paths = paths_px
        self.active = False
        self.wave_no = 0
        self.enemies_left_to_spawn = 0
        self.spawn_timer = 0.0
        self.cooldown = 0.0
        self.level = level
        self.hp_mul = hp_mul
        self.spd_mul = spd_mul
        self.special_mode = special_mode  # e.g., 'permanent'
        self.hp_scale = 1.0
        self.spd_scale = 1.0
        self.is_boss_wave = False
        self.boss_group = None
        self.just_started_boss_wave = False
        
        # 🆕 Junction System - tách paths thành entrance paths và junction paths
        self.entrance_paths = []  # Paths bắt đầu từ -1 (entrance)
        self.junction_paths = []  # Paths bắt đầu từ điểm giao
        self._separate_paths()
        
        print(f"🛤️  Paths: {len(self.entrance_paths)} entrance + {len(self.junction_paths)} junction = {len(self.paths)} total")
        
        # Tank distribution system (từ level 6+)
        self.tank_waves = []  # Danh sách wave nào có tank
        self.current_wave_has_tank = False
        self.tank_distribution_setup = False  # Flag to setup once per level
        
        # 🆕 Entrance path rotation để đảm bảo sử dụng đều tất cả đường
        self.global_enemy_count = 0  # Đếm enemy toàn cục qua tất cả waves
    
    def _separate_paths(self):
        """Tách paths thành entrance paths và junction paths"""
        self.entrance_paths = []
        self.junction_paths = []
        
        for i, path in enumerate(self.paths):
            if len(path) >= 2:
                start_x, start_y = path[0]
                if start_x < 0:  # Bắt đầu từ ngoài map (-1) = entrance path
                    self.entrance_paths.append(path)
                else:  # Bắt đầu từ trong map = junction path
                    self.junction_paths.append(path)

    def _wave_size(self, wave_no: int) -> int:
        return min(2 + (wave_no - 1), 15)
    
    def _setup_tank_distribution(self):
        """Setup tank distribution cho level hiện tại"""
        self.tank_waves = []
        
        if self.level < 6:
            return  # Không có tank trước level 6
            
        # Tính số tank theo công thức: level 6=4, level 7=5, ..., level 15=13
        num_tanks = min(self.level - 2, 13)  # level 6 → 4, level 7 → 5, ..., level 15 → 13
        max_waves = waves_in_level(self.level)
        
        if num_tanks >= max_waves:
            # Nếu số tank >= số waves, mỗi wave có 1 tank
            self.tank_waves = list(range(1, max_waves + 1))
        else:
            # Rải đều tanks qua các waves
            import math
            wave_step = max_waves / num_tanks
            self.tank_waves = []
            for i in range(num_tanks):
                wave_index = math.ceil((i + 1) * wave_step)
                self.tank_waves.append(wave_index)
        
        print(f"🚗 TANK DISTRIBUTION Level {self.level}: {num_tanks} tanks in waves {self.tank_waves}")

    def start_next_wave(self):
        self.wave_no += 1
        size = self._wave_size(self.wave_no)
        max_waves_in_level = waves_in_level(self.level)
        # In special permanent mode, enforce boss once across 5 waves (last wave boss)
        if self.special_mode == 'permanent':
            # Infinite waves: boss appears every 5th wave
            self.is_boss_wave = (self.wave_no % 5 == 0)
        else:
            self.is_boss_wave = (self.level in BOSS_LEVELS) and (self.wave_no == max_waves_in_level)
        

        
        # Setup tank distribution once per level
        if not self.tank_distribution_setup:
            self._setup_tank_distribution()
            self.tank_distribution_setup = True
            
        # Check if this wave has tanks
        self.current_wave_has_tank = self.wave_no in self.tank_waves
        
        print(f"🔧 SET is_boss_wave = {self.is_boss_wave} (level {self.level} in BOSS_LEVELS: {self.level in BOSS_LEVELS}, wave {self.wave_no} == max {max_waves_in_level}: {self.wave_no == max_waves_in_level})")
        if self.current_wave_has_tank:
            print(f"🚗 TANK WAVE! Level {self.level}, Wave {self.wave_no}")
        
        if self.is_boss_wave:
            self.boss_group = self._create_boss_group()
            self.enemies_left_to_spawn = len(self.boss_group)
            print(f"🔥🔥🔥 BOSS WAVE! Level {self.level}, Wave {self.wave_no}, Group: {self.boss_group} 🔥🔥🔥")
        else:
            self.boss_group = None
            self.enemies_left_to_spawn = size
            
        self.spawn_timer = 0.0
        self.active = True
        # HP increases each wave (progressive difficulty)
        self.hp_scale = (1.0 + 0.20 * (self.wave_no - 1)) * self.hp_mul
        # Speed increases starting from wave 5 in permanent mode, otherwise scale gradually
        if self.special_mode == 'permanent':
            if self.wave_no < 5:
                self.spd_scale = 1.0 * self.spd_mul
            else:
                # from wave 5, increase speed progressively
                self.spd_scale = (1.0 + 0.12 * (self.wave_no - 4)) * self.spd_mul
        else:
            self.spd_scale = (1.0 + 0.05 * (self.wave_no - 1)) * self.spd_mul
        self.just_started_boss_wave = self.is_boss_wave
    
    def _create_boss_group(self):
        group = []
        group.append("boss")
        if self.level == 3:
            group.append("normal")
        else:
            group.append("normal")
            group.append("fast")
        return group

    def _pick_enemy_type(self):
        print(f"🔍 _pick_enemy_type: is_boss_wave={self.is_boss_wave}, boss_group={self.boss_group}, enemies_left={self.enemies_left_to_spawn}")
        if self.is_boss_wave and self.boss_group:
            # enemies_left_to_spawn is decremented BEFORE calling this method
            # So enemies_left represents remaining enemies after current spawn
            # We want: boss first, then escorts
            # enemies_left=1 means this is the first spawn (2→1), should return boss_group[0]
            # enemies_left=0 means this is the second spawn (1→0), should return boss_group[1]
            if self.enemies_left_to_spawn < len(self.boss_group):
                spawned_index = len(self.boss_group) - 1 - self.enemies_left_to_spawn
                print(f"🔍 Boss index calc: len={len(self.boss_group)}, enemies_left={self.enemies_left_to_spawn}, spawned_index={spawned_index}")
                enemy_type = self.boss_group[spawned_index]
                print(f"🔍 Returning BOSS enemy: {enemy_type}")
                return enemy_type
            else:
                print(f"❌ enemies_left >= group size: {self.enemies_left_to_spawn}")
        else:
            print(f"🔍 Not boss wave or no boss_group")
        
        # Tank distribution system - guaranteed tanks in specified waves
        if self.current_wave_has_tank and self.level >= 6:
            # In tank waves, spawn exactly 1 tank per wave (yêu cầu của user)
            # Since enemies_left_to_spawn is decremented BEFORE this method,
            # we need to check if this is the first spawn of the wave
            total_enemies = self._wave_size(self.wave_no)
            remaining_enemies = self.enemies_left_to_spawn
            spawned_count = total_enemies - remaining_enemies - 1  # -1 because current spawn is in progress
            
            print(f"🚗 Tank check: total={total_enemies}, remaining={remaining_enemies}, spawned={spawned_count}")
            
            if spawned_count == 0:  # This is the first enemy in the wave - should be tank
                print(f"🚗 Spawning TANK (guaranteed - first enemy in tank wave)")
                return "tank"
        
        # Regular enemy distribution cho non-tank enemies
        r = random.random()
        if self.wave_no >= 4 and r < 0.45: 
            return "fast"
        return "normal"

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
            
            et = self._pick_enemy_type()
            base = ENEMY_TYPES[et]
            
            print(f"⚡ SPAWNING: {et}")
            if et == "boss":
                print("👑👑👑 COMMANDER BOSS HAS ARRIVED! 👑👑👑")
            
            if et == "boss":
                hp = base["hp"] * BOSS_HP_MULTIPLIER * self.hp_scale
                reward = int(base["reward"] * BOSS_REWARD_MULTIPLIER)
            else:
                hp = base["hp"] * self.hp_scale
                reward = base["reward"]
                
            spd = base["spd"] * self.spd_scale
            
            # 🆕 Multi-path spawning - GLOBAL ROTATION để đảm bảo dùng đều tất cả entrance paths
            if self.entrance_paths:
                if len(self.entrance_paths) > 1:
                    # Xoay vòng toàn cục để đảm bảo tất cả entrance paths được dùng qua các waves
                    path_id = self.global_enemy_count % len(self.entrance_paths)
                    path = self.entrance_paths[path_id]
                    print(f"🚶 {et.upper()} spawning from entrance path {path_id}/{len(self.entrance_paths)} (global rotation #{self.global_enemy_count})")
                else:
                    path = self.entrance_paths[0]
                    print(f"🚶 {et.upper()} spawning from single entrance path")
                self.global_enemy_count += 1
            else:
                path = random.choice(self.paths)  # Fallback nếu không có entrance paths
            
            enemy = Enemy(path, hp, spd, reward, etype=et)
            
            # 🆕 Cho enemy biết về junction paths để có thể chuyển đường
            if hasattr(enemy, 'set_junction_paths'):
                enemy.set_junction_paths(self.junction_paths)
            enemy.size_mul = base.get("size_mul", 1.0)
            enemy.slow_resist = base.get("slow_resist", 0.0)  
            enemy.regen_rate = base.get("regen", 0.0)
            
            spawned.append(enemy)
        return spawned

    def is_between_waves(self) -> bool:
        return (not self.active) and (self.cooldown > 0.0)
