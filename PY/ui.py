import pygame
from typing import Callable
from config import WHITE, ORANGE

class Button:
    def __init__(self, rect, text, on_click, bg=(70,90,120), fg=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.bg = bg; self.fg = fg
        self.pressed = False
        
    def draw(self, screen, font):
        # Kiểm tra hover
        is_hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        
        # Màu nền với hiệu ứng hover
        current_bg = self.bg
        if is_hovered:
            # Làm sáng màu khi hover
            current_bg = tuple(min(255, c + 20) for c in self.bg)
        
        # Hiệu ứng nhấn
        draw_rect = self.rect.copy()
        if self.pressed:
            draw_rect.x += 1
            draw_rect.y += 1
        else:
            # Vẽ shadow nhẹ khi không nhấn
            shadow_rect = self.rect.copy()
            shadow_rect.x += 2
            shadow_rect.y += 2
            pygame.draw.rect(screen, (0, 0, 0, 50), shadow_rect, border_radius=10)
        
        # Vẽ nút chính
        pygame.draw.rect(screen, current_bg, draw_rect, border_radius=10)
        
        # Vẽ border đẹp
        border_color = (255, 255, 255, 100) if is_hovered else (200, 200, 200, 80)
        pygame.draw.rect(screen, border_color, draw_rect, width=2, border_radius=10)
        
        # Căn giữa text
        text_surface = font.render(self.text, True, self.fg)
        text_x = draw_rect.centerx - text_surface.get_width() // 2
        text_y = draw_rect.centery - text_surface.get_height() // 2
        screen.blit(text_surface, (text_x, text_y))
        
    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.pressed = True
                self.on_click()
        elif event.type == pygame.MOUSEBUTTONUP and event.button==1:
            self.pressed = False


def draw_level_badge(surface, x, y, lvl: int, small=False):
    if small:
        r = 10
        bg = (255, 180, 40)  # cam sáng
        font_size = 14
    else:
        r = 12
        bg = (255, 160, 50)
        font_size = 16

    pygame.draw.circle(surface, (0, 0, 0), (x, y), r + 2)  # viền đen
    pygame.draw.circle(surface, bg, (x, y), r)
    f = pygame.font.SysFont("consolas", font_size, bold=True)
    txt = f.render(str(lvl), True, (30, 30, 30))
    surface.blit(txt, txt.get_rect(center=(x, y)))
