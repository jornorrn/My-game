# --- src/weapon.py ---
import pygame
import math
from src.components import GameSprite
from src.settings import *

class Projectile(GameSprite):
    '''子弹类武器'''
    def __init__(self, pos, direction, weapon_data, groups, enemy_sprites, obstacle_sprites):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.enemy_sprites = enemy_sprites
        self.obstacle_sprites = obstacle_sprites
        
        self.damage = weapon_data['damage']
        self.speed = weapon_data['speed']
        self.range = weapon_data.get('range', 1000)
        
        # 1. 处理方向
        if direction.magnitude() != 0:
            self.direction = direction.normalize()
        else:
            self.direction = pygame.math.Vector2(1, 0)
            
        # 2. 图像处理核心逻辑
        original_image = weapon_data.get('image_surf')
        
        # [检测] 是否为 Loader 返回的默认洋红色占位符 (32x32 且中心点是洋红)
        is_placeholder = False
        if original_image.get_size() == (32, 32):
            if original_image.get_at((16, 16)) == (255, 0, 255, 255):
                is_placeholder = True

        if is_placeholder:
            # [绘制圆形] 替代洋红色方块
            self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (255, 200, 50), (10, 10), 8) # 黄色子弹
            # 占位圆不需要旋转，因为是圆的
        else:
            # [正常素材] 进行中心旋转
            angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
            self.image = pygame.transform.rotate(original_image, angle)

        # 3. 设置 Rect 和 Hitbox
        # 必须基于中心定位，否则旋转会造成位移
        self.rect = self.image.get_rect(center=pos)
        
        # [固定 Hitbox] 无论图像多大，判定范围固定，防止旋转导致判定框变大
        self.hitbox = pygame.Rect(0, 0, 10, 10) 
        self.hitbox.center = self.rect.center

        # 4. 记录起始位置
        self.pos_vec = pygame.math.Vector2(self.rect.center)
        self.distance_traveled = 0

    def update(self, dt):
        # 移动
        move_amount = self.speed * dt
        self.pos_vec += self.direction * move_amount
        self.hitbox.center = round(self.pos_vec.x), round(self.pos_vec.y)
        self.rect.center = self.hitbox.center
        self.distance_traveled += move_amount

        # 撞墙检测
        if self.obstacle_sprites:
            wall_hits = pygame.sprite.spritecollide(self, self.obstacle_sprites, False, lambda s, o: s.hitbox.colliderect(o.hitbox))
            if wall_hits:
                self.kill()
                return

        # 撞人检测
        hits = pygame.sprite.spritecollide(self, self.enemy_sprites, False, lambda s, e: s.hitbox.colliderect(e.hitbox))
        for enemy in hits:
            if hasattr(enemy, 'take_damage'):
                enemy.take_damage(self.damage)
            self.kill()
            return

        # 射程检测
        if self.distance_traveled > self.range:
            self.kill()

class WeaponController:
    def __init__(self, player, groups, enemy_sprites, obstacle_sprites, resource_manager):
        self.player = player
        self.groups = groups
        self.enemy_sprites = enemy_sprites
        self.obstacle_sprites = obstacle_sprites
        self.res = resource_manager
        
        self.equipped_weapons = [3001] 
        self.cooldowns = { 3001: 0 }

    def update(self):
        current_time = pygame.time.get_ticks()
        
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        screen_center = pygame.math.Vector2(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        direction = mouse_pos - screen_center
        
        for w_id in self.equipped_weapons:
            w_data = self.res.data['weapons'].get(w_id)
            if not w_data: continue
            
            if current_time - self.cooldowns.get(w_id, 0) >= w_data['cooldown']:
                self.fire(w_data, direction)
                self.cooldowns[w_id] = current_time

    def fire(self, w_data, direction):
        player_pos = pygame.math.Vector2(self.player.rect.center)
        
        projectile_data = w_data.copy()
        img_key = w_data['image']
        projectile_data['image_surf'] = self.res.get_image(img_key)
        
        Projectile(
            pos=player_pos, 
            direction=direction, 
            weapon_data=projectile_data, 
            groups=self.groups, 
            enemy_sprites=self.enemy_sprites,
            obstacle_sprites=self.obstacle_sprites
        )