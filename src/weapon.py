import pygame
import math
from src.components import GameSprite
from src.settings import *

class Projectile(GameSprite):
    """
    子弹/投射物类
    """
    def __init__(self, pos, direction, weapon_data, groups, enemy_sprites):
        # 子弹通常在 main 层，或者 particles 层
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.enemy_sprites = enemy_sprites
        self.damage = weapon_data['damage']
        self.speed = weapon_data['speed']
        self.range = weapon_data.get('range', 0) # 0 代表无限射程(直到出屏幕)
        self.spawn_time = pygame.time.get_ticks()
        
        # 运动方向
        self.direction = direction.normalize() if direction.magnitude() != 0 else pygame.math.Vector2(1, 0)
        
        # 设置图片 (从 Loader 加载的图片中获取，这里假设已经传入了 image surface)
        # 注意：实际实例化时，我们会把 image surface 传进来，或者在这里通过 resource_manager 获取
        # 为了解耦，建议在 WeaponController 里获取好 image 传给 Projectile，或者 Projectile 持有 res_manager
        # 这里演示简单做法：外部传入 image
        self.image = weapon_data['image_surf'] 
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-10, -10)
        
        # 旋转图片以匹配方向
        angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=self.hitbox.center)

    def update(self, dt):
        # 移动
        self.hitbox.x += self.direction.x * self.speed * dt
        self.hitbox.y += self.direction.y * self.speed * dt
        self.rect.center = self.hitbox.center
        
        # 碰撞检测 (击中敌人)
        hits = pygame.sprite.spritecollide(self, self.enemy_sprites, False)
        for enemy in hits:
            # 这里的 enemy 是 Enemy 类的实例
            if hasattr(enemy, 'take_damage'):
                enemy.take_damage(self.damage)
            
            # 简单的子弹击中后销毁 (如果是穿透类武器，这里加判断)
            self.kill()
            # TODO: 可以在这里触发击中特效 VFX
            
        # 射程/出界检测
        current_time = pygame.time.get_ticks()
        # 如果有射程限制 (range > 0) 且 飞行时间 * 速度 > 射程 -> 销毁
        # 或者简单的：飞出屏幕太远就销毁
        # 这里简单写：飞出屏幕 100 像素就销毁
        if (self.rect.right < -100 or self.rect.left > WINDOW_WIDTH + 100 or
            self.rect.bottom < -100 or self.rect.top > WINDOW_HEIGHT + 100):
            self.kill()

# [src/weapon.py] -> WeaponController 类

class WeaponController:
    def __init__(self, player, groups, enemy_sprites, resource_manager):
        self.player = player
        self.groups = groups
        self.enemy_sprites = enemy_sprites
        self.res = resource_manager
        
        # 初始武器 (假设 ID 3001 是魔杖)
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
            
            # 检查冷却
            if current_time - self.cooldowns.get(w_id, 0) >= w_data['cooldown']:
                self.fire(w_data, direction)
                self.cooldowns[w_id] = current_time

    def fire(self, w_data, direction):
        # 这里的 direction 已经是计算好的鼠标方向了
        player_pos = pygame.math.Vector2(self.player.rect.center)
        
        projectile_data = w_data.copy()
        img_key = w_data['image']
        projectile_data['image_surf'] = self.res.get_image(img_key)
        
        Projectile(player_pos, direction, projectile_data, self.groups, self.enemy_sprites)