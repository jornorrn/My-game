import pygame
from src.components import Entity
from src.settings import *

class Enemy(Entity):
    def __init__(self, pos, enemy_id, groups, obstacle_sprites, player, resource_manager):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.player = player
        data = resource_manager.data['enemies'][enemy_id]
        
        self.stats = data
        self.speed = self.stats['speed']      # 必须赋值给 self.speed，父类 Entity.move 需要它
        self.current_hp = self.stats['hp']    # 初始化血量
        
        img_key = data['image']
        self.image = resource_manager.get_image(img_key)
        
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-10, -10)
        self.resistance = 3
    
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
        
        # 3. 碰撞伤害 (撞玩家)
        if self.hitbox.colliderect(self.player.hitbox):
            self.player.take_damage(self.stats['damage'])

    def take_damage(self, amount):
        """
        敌人受击逻辑
        """
        self.current_hp -= amount
        print(f"[DEBUG] Enemy hit! Damage: {amount}, Remaining HP: {self.current_hp}")
        
        # [修改] 简单的受击反馈（可选：稍微击退一下，或者变色，这里暂时只做数值）
        
        # 死亡判定
        if self.current_hp <= 0:
            self.die()

    def die(self):
        print(f"[DEBUG] Enemy died.")
        self.kill()
        # TODO: 这里可以播放死亡动画