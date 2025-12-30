import pygame
from src.settings import *
from src.components import Entity
from src.weapon import WeaponController

class Player(Entity):
    def __init__(self, pos, groups, obstacle_sprites, enemy_sprites, resource_manager):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        # 1. 图像设置 (暂时用绿色方块代替，稍后在 load 阶段替换)
        self.image.fill(COLORS['debug']) 
        self.hitbox = self.rect.inflate(-10, -10) # 稍微缩小碰撞箱
        self.set_obstacles(obstacle_sprites)

        # 2. 数值属性
        self.stats = {
            'max_hp': 100,
            'speed': 300,        # 像素/秒
            'pickup_range': 150
        }
        self.current_hp = self.stats['max_hp']
        self.xp = 0
        self.level = 1
        self.xp_required = 100
        
        # 3. 战斗状态
        self.is_dead = False
        self.iframes = 500       # 无敌时间 (毫秒)
        self.last_hit_time = 0
        
        # 4. 武器接口
        self.weapon_controller = WeaponController(self, groups, enemy_sprites, resource_manager)

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

        # 鼠标朝向逻辑 (Flip)
        # 获取鼠标在屏幕上的位置
        mouse_x, _ = pygame.mouse.get_pos()
        # 获取玩家在屏幕上的位置 (注意：如果有摄像机，这里需要减去摄像机偏移量)
        # 目前暂时用 rect.centerx 近似，等摄像机做好后需要修正
        if mouse_x < self.rect.centerx:
            # 鼠标在左，翻转图像 (假设原始素材是朝右的)
            # self.image = pygame.transform.flip(self.original_image, True, False)
            pass 

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