import pygame
from src.components import Entity
from src.settings import *
from src.vfx import AnimationPlayer, FlashEffect, Explosion

class Enemy(Entity):
    def __init__(self, pos, enemy_id, groups, obstacle_sprites, player, resource_manager, audio_manager=None, map_manager=None):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.player = player
        self.set_obstacles(obstacle_sprites)
        self.res = resource_manager
        self.audio_manager = audio_manager
        self.map_manager = map_manager  # 保存地图管理器引用，用于边界检查
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
        
        # [优化] 更新频率控制（根据距离玩家远近）
        self.update_frame_skip = 1  # 每帧更新
        self.frame_count = 0  # 帧计数器
    
    def _check_out_of_bounds(self):
        """
        检查怪物是否在墙外，如果在墙外则自动死亡
        这是一个安全机制，防止怪物出现在墙外
        """
        if not self.map_manager:
            return False  # 如果没有地图管理器，跳过检查
        
        # 获取怪物中心位置的网格坐标
        center_x = self.rect.centerx
        center_y = self.rect.centery
        grid_x = center_x // TILE_SIZE
        grid_y = center_y // TILE_SIZE
        
        # 检查是否在边界墙的网格坐标上
        if (grid_x <= 0 or grid_x >= self.map_manager.width - 1 or
            grid_y <= 0 or grid_y >= self.map_manager.height - 1):
            return True  # 在墙外
        
        # 检查像素坐标是否超出安全范围
        if (center_x < TILE_SIZE or center_x > (self.map_manager.width - 2) * TILE_SIZE or
            center_y < TILE_SIZE or center_y > (self.map_manager.height - 2) * TILE_SIZE):
            return True  # 在墙外
        
        # 检查是否在墙的网格坐标上（使用地图网格数据）
        if (grid_x, grid_y) in self.map_manager.grid:
            if self.map_manager.grid[(grid_x, grid_y)] == 'wall':
                return True  # 在墙上
        
        return False  # 在墙内，安全
    
    def update(self, dt):
        # 0. [新增] 检查是否在墙外，如果是则自动死亡
        if self._check_out_of_bounds():
            print(f"[WARNING] Enemy detected outside walls at ({self.rect.centerx}, {self.rect.centery}), auto-killing...")
            self.die(give_xp=False)  # 墙外死亡不给予经验值
            return  # 死亡后不再执行后续逻辑
        
        # [优化] 根据距离玩家远近决定更新频率
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(self.player.rect.center)
        distance_sq = (player_vec - enemy_vec).length_squared()
        distance = distance_sq ** 0.5
        
        # 根据距离设置更新频率
        if distance > 800:  # 远离玩家（>800像素）
            self.update_frame_skip = 3  # 每3帧更新一次
        elif distance > 400:  # 中等距离（400-800像素）
            self.update_frame_skip = 2  # 每2帧更新一次
        else:  # 近距离（<400像素）
            self.update_frame_skip = 1  # 每帧更新
        
        # 只在需要时更新（根据更新频率）
        self.frame_count += 1
        should_update = (self.frame_count % self.update_frame_skip == 0)
        
        # 1. 计算指向玩家的向量（总是更新，确保敌人能追踪玩家）
        diff = player_vec - enemy_vec
        if diff.magnitude() > 0:
            self.direction = diff.normalize()
        else:
            self.direction = pygame.math.Vector2()

        # 2. 播放动画（根据更新频率）
        if should_update:
            self.image = self.anim_player.get_frame_image(dt * self.update_frame_skip, loop=True, scale=self.scale)
        
        # 3. 移动与碰撞伤害 (撞玩家) - 总是更新，确保碰撞检测准确
        self.move(dt)
        if self.hitbox.colliderect(self.player.hitbox):
            self.player.take_damage(self.stats['damage'])

    def take_damage(self, amount):
        """
        敌人受击逻辑
        """
        self.current_hp -= amount
        print(f"[DEBUG] Enemy hit! Damage: {amount}, Remaining HP: {self.current_hp}")
        # [优化] 减少受击特效生成频率，避免后期特效过多
        import random
        from src.settings import MAX_ENEMIES
        
        # 如果玩家等级较高或敌人数量很多，减少受击特效生成
        should_create_flash = True
        if self.player.level > 15:
            # 15级后，只有30%概率生成受击特效
            should_create_flash = random.random() < 0.3
        elif len([s for s in self.groups()[0].sprites() if hasattr(s, 'stats')]) > MAX_ENEMIES * 0.6:
            # 敌人数量超过60%上限时，50%概率生成受击特效
            should_create_flash = random.random() < 0.5
        
        if should_create_flash:
            # 防止特效加入 enemy_sprites 组
            # self.groups()[0] 通常是 all_sprites (YSortCameraGroup)
            # 我们只把特效加到渲染组，不加到碰撞组
            render_group = self.groups()[0] 
            FlashEffect(self, [render_group], duration=0.1)
        # 死亡判定
        if self.current_hp <= 0:
            self.die()

    def die(self, give_xp=True):
        """
        敌人死亡逻辑
        give_xp: 是否给予玩家经验值（墙外死亡时不给予）
        """
        if not self.groups():
            return
        # 只有正常死亡才给予经验值
        if give_xp:
            self.player.xp += self.stats.get('xp', 10)
            print(f"[DEBUG] Enemy died. Player XP: {self.player.xp}")
            # 播放死亡音效（只有正常死亡才播放）
            if self.audio_manager:
                self.audio_manager.play_sfx('sfx_enemydied', volume=0.6)
            # [优化] 检查特效数量，只在特效数量未达上限时创建
            # 当敌人数量过多时，减少特效生成频率
            from src.settings import MAX_VFX_COUNT, MAX_ENEMIES
            import random
            should_create_vfx = True
            
            # 如果敌人数量很多，随机跳过部分特效
            # 通过检查 enemy_sprites 组的大小来判断（需要传入或访问）
            # 这里使用一个简单的方法：通过检查所有精灵中敌人的数量
            # 由于 enemy_sprites 组在 game 中，我们无法直接访问，所以使用概率控制
            # 当敌人密度高时（通过检查周围敌人数量或使用固定概率）
            # 使用固定概率：后期减少50%的特效生成
            if self.player.level > 10:
                # 10级后，50%概率跳过特效生成
                should_create_vfx = random.random() < 0.5
            
            # 播放死亡爆炸动画（只有正常死亡且允许创建特效时才播放）
            if should_create_vfx:
                expl_surf = self.res.get_image('vfx_explosion') 
                if expl_surf and expl_surf.get_width() > 32:
                    Explosion(self.rect.center, self.groups(), expl_surf, frame_count=12, scale=1.25)
        else:
            # 墙外死亡，静默移除，不播放音效和动画
            print(f"[DEBUG] Enemy removed (out of bounds), no XP given")
        
        self.kill()