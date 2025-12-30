import pygame
import math
from src.settings import *
from src.components import Entity
from src.weapon import WeaponController

class Player(Entity):
    def __init__(self, pos, groups, obstacle_sprites, enemy_sprites, resource_manager):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.res = resource_manager # 保存引用以便切换图片
        self.animations = {     # 预加载四方向图片
            'up': self.res.get_image('player_up'),
            'down': self.res.get_image('player_down'),
            'left': self.res.get_image('player_left'),
            'right': self.res.get_image('player_right'),
            # 如果没有专门的图，可以用 fallback
            'idle': self.res.get_image('player') 
        }
        self.image = self.animations['down'] # 初始朝下
        self.image.fill(COLORS['debug']) 

        self.hitbox = self.rect.inflate(-10, -10) # 稍微缩小碰撞箱
        self.set_obstacles(obstacle_sprites)

        # 数值属性
        self.stats = {
            'max_hp': 100,
            'speed': 300,        # 像素/秒
            'pickup_range': 150
        }
        self.current_hp = self.stats['max_hp']
        self.xp = 0
        self.level = 1
        self.xp_required = 100
        
        # 战斗状态
        self.is_dead = False
        self.iframes = 500       # 无敌时间 (毫秒)
        self.last_hit_time = 0
        
        # 武器接口
        self.weapon_controller = WeaponController(self, groups, enemy_sprites, 
                        obstacle_sprites, resource_manager)

    def input(self):
        """处理键盘输入"""
        keys = pygame.key.get_pressed()

        # 移动输入
        if keys[pygame.K_w]:
            self.direction.y = -1
        elif keys[pygame.K_s]:
            self.direction.y = 1
        else:
            self.direction.y = 0

        if keys[pygame.K_a]:
            self.direction.x = -1
        elif keys[pygame.K_d]:
            self.direction.x = 1
        else:
            self.direction.x = 0

    def get_mouse_direction(self):
        """计算鼠标相对于屏幕中心的角度，并改变朝向图片"""
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        screen_center = pygame.math.Vector2(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        diff = mouse_pos - screen_center
        
        # 计算角度 (-180 到 180)
        angle = math.degrees(math.atan2(-diff.y, diff.x))
        if -45 <= angle < 45:
            self.status = 'right'
        elif 45 <= angle < 135:
            self.status = 'up'
        elif -135 <= angle < -45:
            self.status = 'down'
        else:
            self.status = 'left'

        # 切换图片
        if self.status in self.animations:
            self.image = self.animations[self.status]
            # 保持中心位置不变
            current_center = self.rect.center
            self.rect = self.image.get_rect(center=current_center)
            # hitbox 跟随 rect 中心
            self.hitbox.center = self.rect.center


    def check_level_up(self):
        """检查是否升级"""
        if self.xp >= self.xp_required:
            self.xp -= self.xp_required
            self.level += 1
            self.xp_required = int(self.xp_required * 1.2)
            return True
        return False

    def take_damage(self, amount):
        """受击逻辑"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_hit_time < self.iframes:
            return

        self.current_hp -= amount
        self.last_hit_time = current_time
        print(f"[DEBUG] Player hit! HP: {self.current_hp}")

        if self.current_hp <= 0:
            self.is_dead = True

    def update(self, dt):
        self.speed = self.stats['speed']
        self.input()
        self.move(dt)
        self.weapon_controller.update()