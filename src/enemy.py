import pygame
from src.components import Entity
from src.settings import *

class Enemy(Entity):
    def __init__(self, pos, enemy_id, groups, obstacle_sprites, player, resource_manager):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.player = player
        data = resource_manager.data['enemies'][enemy_id]
        
        self.stats = data
        img_key = data['image']
        self.image = resource_manager.get_image(img_key)
        
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-10, -10)
        self.resistance = 3

    def get_player_direction(self):
        """计算指向玩家的向量"""
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(self.player.rect.center)
        
        distance = (player_vec - enemy_vec).magnitude()
        
        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()
            
        return direction, distance
    
    def update(self, dt):
        # 1. 计算指向玩家的向量
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(self.player.rect.center)
        
        diff = player_vec - enemy_vec
        
        if diff.magnitude() > 0:
            self.direction = diff.normalize()
        else:
            self.direction = pygame.math.Vector2()
            
        # 2. 调用父类 Entity 的移动逻辑
        self.move(dt)
        
        # 3. 简单的碰撞伤害 
        if self.hitbox.colliderect(self.player.hitbox):
            self.player.take_damage(self.stats['damage'])