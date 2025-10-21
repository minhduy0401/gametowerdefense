# 🎨 Cấu hình màu sắc và hiệu ứng cho các loại projectile

# Màu sắc cho từng loại tháp
PROJECTILE_COLORS = {
    "basic": {
        "main": (255, 255, 0),      # Vàng
        "trail": (255, 200, 0)      # Vàng nhạt
    },
    "sniper": {
        "main": (255, 255, 0),      # Vàng
        "trail": (255, 200, 0)      # Vàng nhạt  
    },
    "laser": {
        "main": (255, 0, 0),        # Đỏ sáng
        "trail": (255, 150, 150),   # Đỏ nhạt
        "core": (255, 255, 255),    # Trắng (lõi)
        "glow": (255, 100, 100)     # Đỏ phát sáng
    },
    "rocket": {
        "body": (100, 100, 100),    # Xám (thân)
        "tip": (255, 100, 0),       # Cam (đầu)
        "flame_colors": [
            (255, 100, 0),          # Cam đậm
            (255, 200, 0),          # Cam vàng  
            (255, 255, 100)         # Vàng nhạt
        ]
    },
    "electric": {
        "main": (0, 150, 255),      # Xanh dương
        "core": (255, 255, 255),    # Trắng
        "spark": (100, 150, 255),   # Xanh nhạt
        "chain": (200, 200, 255)    # Xanh tím nhạt
    },
    "poison": {
        "main": (0, 200, 0),        # Xanh lá đậm
        "bubble": (100, 255, 100),  # Xanh lá nhạt
        "gas": (0, 255, 100)        # Xanh lá sáng
    },
    "flame": {
        "colors": [
            (255, 0, 0),            # Đỏ (trong)
            (255, 100, 0),          # Cam
            (255, 200, 0)           # Vàng cam (ngoài)
        ]
    },
    "ice": {
        "main": (100, 200, 255),    # Xanh nhạt
        "crystal": (200, 230, 255), # Xanh rất nhạt
        "frost": (150, 200, 255)    # Xanh băng
    },
    "minigun": {
        "main": (255, 255, 0),      # Vàng (như basic)
        "tracer": (255, 150, 0)     # Cam (đạn tracer)
    },
    "mortar": {
        "body": (50, 50, 50),       # Đen
        "shell": (100, 80, 60),     # Nâu
        "smoke_colors": [
            (150, 150, 150),        # Xám nhạt
            (100, 100, 100),        # Xám
            (80, 80, 80)            # Xám đậm
        ]
    }
}

# Kích thước hiệu ứng
PROJECTILE_SIZES = {
    "basic": {"main": 4},
    "sniper": {"main": 4},
    "laser": {"main": 6, "core": 4, "trail_width": 8},
    "rocket": {"body": 7, "tip": 5, "trail_size": 12},
    "electric": {"main": 5, "core": 2, "spark_length": 25},
    "poison": {"main": 5, "bubble": 4, "bubble_count": 2},
    "flame": {"sizes": [7, 5, 3]},
    "ice": {"main": 5, "crystal": 3, "frost_radius": 8},
    "minigun": {"main": 3},  # Nhỏ hơn vì bắn nhanh
    "mortar": {"body": 8, "shell": 6, "smoke_size": 15}
}

# Cấu hình hiệu ứng đặc biệt
EFFECT_CONFIG = {
    "laser": {
        "trail_lifetime": 1.5,
        "pierce_glow": True
    },
    "rocket": {
        "trail_lifetime": 0.5,
        "flame_particles": 3
    },
    "electric": {
        "chain_sparks": 3,
        "spark_frequency": 0.1
    },
    "poison": {
        "bubble_frequency": 0.2,
        "gas_spread": 8
    },
    "flame": {
        "flicker_intensity": 2,
        "particle_count": 3
    },
    "ice": {
        "crystal_sides": 6,
        "frost_particles": 2
    },
    "mortar": {
        "smoke_lifetime": 1.0,
        "smoke_spread": 5
    }
}