# --- src/weapon.py ---
import pygame
import math
from src.components import GameSprite
from src.settings import *
from src.vfx import slice_frames, AnimationPlayer

class Projectile(GameSprite):
    '''子弹类武器'''
    def __init__(self, pos, direction, weapon_data, groups, 
                 enemy_sprites, obstacle_sprites, angle_offset=0):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.enemy_sprites = enemy_sprites
        self.obstacle_sprites = obstacle_sprites

        self.damage = weapon_data['damage']
        self.speed = weapon_data['speed']
        self.range = weapon_data.get('range', 1000)
        self.scale = weapon_data.get('data', {}).get('scale', 1.0)

        # 1. 处理方向
        # 原始方向向量为发射角度
        base_angle = math.degrees(math.atan2(-direction.y, direction.x))
        # 加上偏移量（实现多把武器扇形发射）
        final_angle = base_angle + angle_offset
        rad = math.radians(final_angle)
        self.direction = pygame.math.Vector2(math.cos(rad), - math.sin(rad))
            
        # 使用通用控制器获取原始帧
        # 注意：子弹比较特殊，因为需要旋转。如果每帧 update 都旋转，性能开销大。
        # 最佳实践是：在 init 里把所有动画帧都预先旋转好。
        
        # [逻辑] 检查占位符
        full_image = weapon_data.get('image_surf')
        is_placeholder = False
        if full_image.get_size() == (32, 32):
             if full_image.get_at((16, 16)) == (255, 0, 255, 255):
                is_placeholder = True
        
        self.rotated_frames = []
        self.anim_player = None # 标记是否有动画
        
        if is_placeholder:    # 黄色圆形占位符，不需要旋转
            r = int(10 * self.scale)
            self.image = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (255, 200, 50), (r, r), r-2)
        else:   # 正常图片：处理动画与预旋转
            temp_anim = AnimationPlayer(
                full_image=full_image,
                data_dict=weapon_data.get('data', {}),
                default_speed=10
            )
            raw_frames = temp_anim.get_all_frames()

            # 处理流程： 原图 -> 缩放 -> 旋转 -> 保存
            for frame in raw_frames:
                # 1. 缩放
                if self.scale != 1.0:
                    w = int(frame.get_width() * self.scale)
                    h = int(frame.get_height() * self.scale)
                    scaled_frame = pygame.transform.scale(frame, (w, h))
                else:
                    scaled_frame = frame
                
                # 2. 旋转
                rotated_frame = pygame.transform.rotate(scaled_frame, final_angle)
                self.rotated_frames.append(rotated_frame)
            
            self.image = self.rotated_frames[0]
            self.anim_player = True 

        self.frame_index = 0
        self.animation_speed = 10 
        
        self.rect = self.image.get_rect(center=pos)

        # 3. 设置 Rect 和 Hitbox
        self.rect = self.image.get_rect(center=pos)
        # Hitbox 大小跟随 scale
        box_size = int(10 * self.scale)
        self.hitbox = pygame.Rect(0, 0, box_size, box_size)
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

        # 仅当不是占位符且有多帧时，播放预旋转的动画
        if self.anim_player and len(self.rotated_frames) > 1:
            self.frame_index += self.animation_speed * dt
            if self.frame_index >= len(self.rotated_frames):
                self.frame_index = 0
            self.image = self.rotated_frames[int(self.frame_index)]
            # 保持 rect 中心
            self.rect = self.image.get_rect(center=self.hitbox.center)

        # 撞墙检测
        if self.obstacle_sprites:
            wall_hits = pygame.sprite.spritecollide(self, self.obstacle_sprites, 
                        False, lambda s, o: s.hitbox.colliderect(o.hitbox))
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

class Orbital(GameSprite):
    def __init__(self, player, groups, enemy_sprites, weapon_data, start_angle):
        # 环绕物通常在 main 层或 vfx 层
        super().__init__(groups, player.rect.center, z_layer=LAYERS['vfx_top'])
        
        self.player = player
        self.enemy_sprites = enemy_sprites
        self.weapon_data = weapon_data
        self.data_ref = weapon_data.get('data', {}) # 引用

        # 获取数据
        self.damage = weapon_data['damage']
        self.rot_speed = weapon_data['speed'] # 角度/秒
        self.radius = self.data_ref.get('radius', 80)
        self.dmg_interval = weapon_data['cooldown']

        # 使用通用动画控制器
        self.anim_player = AnimationPlayer(
            full_image=weapon_data['image_surf'],
            data_dict=weapon_data.get('data', {}),
            default_speed=15
        )
        # 图像处理 (从 effect 字段获取实物图)
        self.image = self.anim_player.frames[0]
        self.rect = self.image.get_rect(center=player.rect.center)
        # 判定箱：使用图片实际大小
        self.hitbox = self.rect.inflate(0, 0)
        # 运行时状态
        self.angle = start_angle
        self.attack_timer = 0 # 用于控制伤害间隔

    def update(self, dt):
        # 读取最新 Scale
        current_scale = self.data_ref.get('scale', 1.0)

        # 1. 旋转位置计算
        self.angle += self.rot_speed * dt
        if self.angle >= 360: self.angle -= 360
        
        # 简单的极坐标转换
        rad = math.radians(self.angle)
        offset_x = math.cos(rad) * self.radius
        offset_y = math.sin(rad) * self.radius
        
        # 跟随玩家中心
        self.rect.centerx = self.player.rect.center[0] + offset_x
        self.rect.centery = self.player.rect.center[1] + offset_y

        # 动画更新 + 实时缩放
        raw_img = self.anim_player.update(dt, loop=True)
        if current_scale != 1.0:
            w = int(raw_img.get_width() * current_scale)
            h = int(raw_img.get_height() * current_scale)
            self.image = pygame.transform.scale(raw_img, (w, h))
        else:
            self.image = raw_img
        
        # [新增] 动态更新 Hitbox (如果升级导致 scale 变化，hitbox 也要变)
        # 假设判定范围就是图片大小
        self.rect = self.image.get_rect(center=self.rect.center)
        self.hitbox = self.rect.inflate(0, 0)

        # 伤害判定 (基于时间间隔)
        current_time = pygame.time.get_ticks()
        if current_time - self.attack_timer >= self.dmg_interval:
            # 检测碰撞
            hits = pygame.sprite.spritecollide(self, self.enemy_sprites, False, 
                                               lambda s, e: s.hitbox.colliderect(e.hitbox))
            
            if hits:
                # 对碰到的所有敌人生效
                for enemy in hits:
                    if hasattr(enemy, 'take_damage'):
                        enemy.take_damage(self.damage)
                
                # 重置计时器 (造成一次伤害后进入冷却)
                self.attack_timer = current_time

class Aura(GameSprite):
    def __init__(self, player, groups, enemy_sprites, weapon_data):
        super().__init__(groups, player.rect.center, z_layer=LAYERS['vfx_bottom'])
        
        self.player = player
        self.enemy_sprites = enemy_sprites
        
        # 保存 data 的引用，而不是只读取一次数值
        self.weapon_data = weapon_data 
        self.data_ref = weapon_data.get('data', {}) # 快捷引用
        # 初始读取
        self.damage = weapon_data['damage']
        self.dmg_interval = weapon_data['cooldown']
        self.current_scale = self.data_ref.get('scale', 1.0)
        self.radius_base = self.data_ref.get('radius', 100)

        # [逻辑] 检查是否为占位符 (32x32 洋红色)
        full_image = weapon_data['image_surf']
        self.is_placeholder = False
        if full_image.get_size() == (32, 32):
             if full_image.get_at((16, 16)) == (255, 0, 255, 255): 
                 self.is_placeholder = True

        if self.is_placeholder:
            self.anim_player = None
            self.image = self._draw_placeholder_image()
        else:   # 正常素材：使用动画控制器
            anim_speed = weapon_data['speed']
            self.anim_player = AnimationPlayer(
                full_image=full_image, 
                data_dict=self.data_ref,
                default_speed=anim_speed if anim_speed > 0 else 10
            )
            self.image = self.anim_player.frames[0]

        self.rect = self.image.get_rect(center=player.rect.center)
        self.hitbox = self.rect.inflate(0, 0)
        self.attack_timer = 0

    def _draw_placeholder_image(self):
        """辅助函数：根据当前半径和缩放绘制占位符"""
        # 实时计算半径
        r = int(self.radius_base * self.current_scale)
        surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (0, 100, 255, 100), (r, r), r)
        return surf
    
    def update(self, dt):
        self.rect.center = self.player.rect.center
        # 每一帧都从源数据读取最新的 Scale
        # 这样 UpgradeSystem 修改了 json data 后，这里立刻生效
        target_scale = self.data_ref.get('scale', 1.0)
        self.current_scale = target_scale # 更新本地记录
        
        # 1. 图像处理
        if self.is_placeholder:
            # 如果是占位符，如果缩放变了，需要重画（或者简单点，每帧重画）
            # 为了性能，可以判断 scale 是否变化，这里简化为每帧重画确保正确
            self.image = self._draw_placeholder_image()
        elif self.anim_player:
            # 获取原始帧
            raw_img = self.anim_player.update(dt, loop=True)
            # 应用缩放
            if target_scale != 1.0:
                w = int(raw_img.get_width() * target_scale)
                h = int(raw_img.get_height() * target_scale)
                self.image = pygame.transform.scale(raw_img, (w, h))
            else:
                self.image = raw_img
        
        # 2. 判定箱处理 (Visual 跟随 Scale, 判定也跟随 Scale)
        # 逻辑：判定半径 = 基础半径 * 缩放倍率
        current_radius = self.radius_base * self.current_scale
        target_diameter = int(current_radius * 2)
        
        # 确保 rect 中心正确
        self.rect = self.image.get_rect(center=self.player.rect.center)
        
        # 强制 Hitbox 大小跟随计算出的直径
        if self.hitbox.width != target_diameter:
             self.hitbox = pygame.Rect(0, 0, target_diameter, target_diameter)
        
        self.hitbox.center = self.rect.center
        
        # 3. 伤害逻辑
        current_time = pygame.time.get_ticks()
        if current_time - self.attack_timer >= self.dmg_interval:
            hits = pygame.sprite.spritecollide(self, self.enemy_sprites, False, 
                                               lambda s, e: s.hitbox.colliderect(e.hitbox))
            for enemy in hits:
                if hasattr(enemy, 'take_damage'): enemy.take_damage(self.damage)
            self.attack_timer = current_time

class WeaponController:
    def __init__(self, player, groups, enemy_sprites, obstacle_sprites, resource_manager):
        self.player = player
        self.groups = groups
        self.enemy_sprites = enemy_sprites
        self.obstacle_sprites = obstacle_sprites
        self.res = resource_manager
        
        # 武器列表 [3001, 3001, ...]
        self.equipped_weapons = [3001] 
        # 冷却列表 [0, 0, ...] (索引对应，独立计时)
        self.cooldowns = [0] * len(self.equipped_weapons)
        # [新增] 环绕物管理组
        # 我们用一个字典来追踪已生成的环绕物，Key=Index, Value=OrbitalSprite
        # 或者更简单：每帧检查数量是否变化，变了就全删重生成（Roguelite中升级不频繁，这很安全且能保证排列整齐）
        self.orbital_sprites = pygame.sprite.Group()
        self.aura_sprites = pygame.sprite.Group()

    def update(self):
        if pygame.time.get_ticks() % 1000 < 20:
             print(f"[WEAPON DEBUG] Holding {len(self.equipped_weapons)} weapons. Cooldowns len: {len(self.cooldowns)}")

        current_time = pygame.time.get_ticks()
        
        # 1. 自动扩容冷却列表 (防止数组越界)
        while len(self.cooldowns) < len(self.equipped_weapons):
            self.cooldowns.append(0)
        
        # 2. 统计武器数量和类型 (用于计算扇形)
        total_counts = {}
        for w_id in self.equipped_weapons:
            total_counts[w_id] = total_counts.get(w_id, 0) + 1
            
        # 3. 处理环绕物 (Orbital) 和光环（Aura）的生成与同步
        # 策略：检查当前持有的环绕物总数 vs 场景里的 Sprite 总数
        # 如果不一致，说明刚升级了，直接清空重画（确保 360 度均匀分布）
        
        # 统计当前应该有多少个环绕物和光环
        target_orbitals = []
        target_auras = []
        for w_id in self.equipped_weapons:
            w_data = self.res.data['weapons'].get(w_id)
            if not w_data: continue
            w_type = w_data.get('type', 'projectile')
            if w_type == 'orbital': target_orbitals.append(w_id)
            elif w_type == 'aura': target_auras.append(w_id)
                
        # 如果数量不对 (通常是变多了)，重置所有环绕物和光环
        if len(self.aura_sprites) != len(target_auras): self._respawn_auras(target_auras)
        if len(self.orbital_sprites) != len(target_orbitals): self._respawn_orbitals(target_orbitals)

        processed_rank = {}

        # 4. 按【索引】遍历，实现独立冷却
         # 4. 处理发射型 (Projectile)
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        screen_center = pygame.math.Vector2(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        direction = mouse_pos - screen_center

        total_counts = {}
        for w_id in self.equipped_weapons: total_counts[w_id] = total_counts.get(w_id, 0) + 1
        processed_rank = {}

        # [关键] 只有 type='projectile' (或没写type默认是projectile) 才执行发射逻辑
        for i, w_id in enumerate(self.equipped_weapons):
            w_data = self.res.data['weapons'].get(w_id)
            if not w_data: continue
            if w_data.get('type', 'projectile') != 'projectile': continue
            
            # 计算扇形参数
            total = total_counts[w_id]
            rank = processed_rank.get(w_id, 0)
            processed_rank[w_id] = rank + 1
            
            angle_offset = 0
            if total > 1:
                spread = 15 * (total - 1)
                angle_offset = (-spread / 2) + (rank * (spread / (total - 1)))
            # 独立冷却判定
            if current_time - self.cooldowns[i] >= w_data['cooldown']:
                self.fire(w_data, direction, angle_offset)
                self.cooldowns[i] = current_time

    def _respawn_orbitals(self, orbital_ids):
        """清空并重新生成所有环绕物，确保角度均匀"""
        # 1. 清理旧的
        for sprite in self.orbital_sprites:
            sprite.kill()
        self.orbital_sprites.empty()
        
        if not orbital_ids: return
        # 2. 重新生成
        count = len(orbital_ids)
        step = 360 / count # 均匀分布角度
        
        for i, w_id in enumerate(orbital_ids):
            w_data = self.res.data['weapons'].get(w_id)
            
            # 准备数据 (使用 effect 字段作为图像)
            orb_data = w_data.copy()
            # 优先使用 effect
            effect_key = w_data.get('effect', w_data['image'])
            orb_data['image_surf'] = self.res.get_image(effect_key)
            
            Orbital(self.player, [self.groups, self.orbital_sprites], 
                    self.enemy_sprites, orb_data, start_angle=i*step)
            
    def _respawn_auras(self, aura_ids):
        """重新生成所有 Aura"""
        for sprite in self.aura_sprites: sprite.kill()
        self.aura_sprites.empty()
        
        # Aura 不需要分布角度，它们都重叠在脚下 (或者如果种类不同，可以叠加)
        for w_id in aura_ids:
            w_data = self.res.data['weapons'].get(w_id)
            aura_data = w_data.copy()
            
            effect_key = w_data.get('effect', w_data['image'])
            aura_data['image_surf'] = self.res.get_image(effect_key)
            
            Aura(self.player, [self.groups, self.aura_sprites], 
                 self.enemy_sprites, aura_data)

    def fire(self, w_data, direction, angle_offset):
        player_pos = pygame.math.Vector2(self.player.rect.center)
        projectile_data = w_data.copy()
        
        # [Bug修复] 显式打印调试信息
        # 1. 尝试获取 effect 字段
        effect_key = w_data.get('effect')
        
        # 2. 如果没有 effect，回退到 image
        if not effect_key:
            # print(f"[WEAPON WARNING] ID {w_data['id']} missing 'effect' field. Using icon.")
            effect_key = w_data.get('image')
        
        # 3. 传入 Projectile 的是最终确定的 Surface
        projectile_data['image_surf'] = self.res.get_image(effect_key)
        
        Projectile(
            pos=player_pos, 
            direction=direction, 
            weapon_data=projectile_data, 
            groups=self.groups, 
            enemy_sprites=self.enemy_sprites,
            obstacle_sprites=self.obstacle_sprites,
            angle_offset=angle_offset
        )

