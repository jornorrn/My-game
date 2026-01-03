import pygame
from src.components import Entity
from src.settings import *
from src.vfx import AnimationPlayer, FlashEffect, Explosion

class Enemy(Entity):
    def __init__(self, pos, enemy_id, groups, obstacle_sprites, player, resource_manager):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.player = player
        self.set_obstacles(obstacle_sprites)
        self.res = resource_manager
        # 数据读取
        data = resource_manager.data['enemies'][enemy_id]
        self.stats = data
        self.speed = data['speed']
        self.current_hp = data['hp'] 
        
        # 动画与图像
        img_key = data['image']
        full_image = resource_manager.get_image(img_key)

        anim_data = data.get('data', {})
        self.scale = anim_data.get('scale', 1.0)
        self.anim_player = AnimationPlayer(full_image, anim_data, default_speed=8)
        
        # 初始化图像
        self.image = self.anim_player.get_frame_image(0, loop=True, scale=self.scale)

        # 生成阴影
        shadow_img = self.res.get_image('shadows')
        shadow_img = pygame.transform.scale(shadow_img, (24, 10))
        shadow_img.set_alpha(100)
        
        from src.components import Shadow # 局部导入防循环，或放顶部
        Shadow(self, groups, shadow_img)
        
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

        # 2. 播放动画
        self.image = self.anim_player.get_frame_image(dt, loop=True, scale=self.scale)
        
        # 3. 移动与碰撞伤害 (撞玩家)
        self.move(dt)
        if self.hitbox.colliderect(self.player.hitbox):
            self.player.take_damage(self.stats['damage'])

    def take_damage(self, amount):
        """
        敌人受击逻辑
        """
        self.current_hp -= amount
        print(f"[DEBUG] Enemy hit! Damage: {amount}, Remaining HP: {self.current_hp}")
        # 防止特效加入 enemy_sprites 组
        # self.groups()[0] 通常是 all_sprites (YSortCameraGroup)
        # 我们只把特效加到渲染组，不加到碰撞组
        render_group = self.groups()[0] 
        FlashEffect(self, [render_group], duration=0.1)
        # 死亡判定
        if self.current_hp <= 0:
            self.die()

    def die(self):
        if not self.groups():
            return
        self.player.xp += self.stats.get('xp', 10)
        print(f"[DEBUG] Enemy died. Player XP: {self.player.xp}")
        # 播放死亡爆炸动画
        expl_surf = self.res.get_image('vfx_explosion') 
        if expl_surf.get_width() > 32:
             Explosion(self.rect.center, self.groups(), expl_surf, frame_count=12, scale=2.5)
        
        self.kill()