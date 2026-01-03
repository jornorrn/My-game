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
        # #region agent log
        import json
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "D",
            "location": "enemy.py:__init__",
            "message": "Enemy image loaded",
            "data": {
                "enemy_id": enemy_id,
                "enemy_name": data.get('name', 'unknown'),
                "img_key": img_key,
                "image_is_none": full_image is None,
                "image_size": full_image.get_size() if full_image else None
            },
            "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
        }
        try:
            with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        except: pass
        # #endregion

        anim_data = data.get('data', {})
        self.scale = anim_data.get('scale', 1.0)
        # #region agent log
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "B",
            "location": "enemy.py:__init__",
            "message": "Animation data",
            "data": {
                "enemy_id": enemy_id,
                "anim_data": anim_data,
                "scale": self.scale
            },
            "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
        }
        try:
            with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        except: pass
        # #endregion
        self.anim_player = AnimationPlayer(full_image, anim_data, default_speed=8)
        
        # 初始化图像
        self.image = self.anim_player.get_frame_image(0, loop=True, scale=self.scale)
        # #region agent log
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "F",
            "location": "enemy.py:__init__",
            "message": "Initial image set",
            "data": {
                "enemy_id": enemy_id,
                "image_is_none": self.image is None,
                "image_size": self.image.get_size() if self.image else None,
                "anim_frames_count": len(self.anim_player.frames) if hasattr(self.anim_player, 'frames') else 0
            },
            "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
        }
        try:
            with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        except: pass
        # #endregion

        # 生成阴影
        shadow_img = self.res.get_image('shadows')
        shadow_img = pygame.transform.scale(shadow_img, (24, 10))
        shadow_img.set_alpha(100)
        
        from src.components import Shadow # 局部导入防循环，或放顶部
        Shadow(self, groups, shadow_img)
        
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-10, -10)
        self.resistance = 3
    
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
        
        # 1. 计算指向玩家的向量
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(self.player.rect.center)
        diff = player_vec - enemy_vec
        if diff.magnitude() > 0:
            self.direction = diff.normalize()
        else:
            self.direction = pygame.math.Vector2()

        # 2. 播放动画
        new_image = self.anim_player.get_frame_image(dt, loop=True, scale=self.scale)
        # #region agent log
        import json
        if new_image is None or (hasattr(self, 'image') and self.image is None):
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "C",
                "location": "enemy.py:update",
                "message": "Image is None in update",
                "data": {
                    "enemy_id": self.stats.get('id', 'unknown') if hasattr(self, 'stats') else 'unknown',
                    "new_image_is_none": new_image is None,
                    "old_image_is_none": self.image is None if hasattr(self, 'image') else True,
                    "frame_index": int(self.anim_player.frame_index) if hasattr(self.anim_player, 'frame_index') else -1,
                    "total_frames": len(self.anim_player.frames) if hasattr(self.anim_player, 'frames') else 0
                },
                "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
            }
            try:
                with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except: pass
        # #endregion
        self.image = new_image
        
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
            # 播放死亡爆炸动画（只有正常死亡才播放）
            expl_surf = self.res.get_image('vfx_explosion') 
            if expl_surf.get_width() > 32:
                 Explosion(self.rect.center, self.groups(), expl_surf, frame_count=12, scale=2.5)
        else:
            # 墙外死亡，静默移除，不播放音效和动画
            print(f"[DEBUG] Enemy removed (out of bounds), no XP given")
        
        self.kill()