# --- src/weapon.py ---
import pygame
import math
from src.components import GameSprite
from src.settings import *

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
        
        # 1. 处理方向
        # 原始方向向量为发射角度
        base_angle = math.degrees(math.atan2(-direction.y, direction.x))
        # 加上偏移量（实现多把武器扇形发射）
        final_angle = base_angle + angle_offset
        rad = math.radians(final_angle)
        self.direction = pygame.math.Vector2(math.cos(rad), - math.sin(rad))
            
        # 2. 图像处理核心逻辑
        original_image = weapon_data.get('image_surf')
        
        # [检测] 是否为 Loader 返回的默认洋红色占位符 (32x32 且中心点是洋红)
        is_placeholder = False
        if original_image.get_size() == (32, 32):
            if original_image.get_at((16, 16)) == (255, 0, 255, 255):
                is_placeholder = True

        if is_placeholder:
            # [绘制黄色圆形占位]不需要旋转 
            self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (255, 200, 50), (10, 10), 8)
        else:
            # [正常素材] 进行中心旋转
            self.image = pygame.transform.rotate(original_image, final_angle)

        # 3. 设置 Rect 和 Hitbox
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
        super().__init__(groups, player.rect.center, z_layer=LAYERS['vfx_bottom'])
        
        self.player = player
        self.enemy_sprites = enemy_sprites
        
        # 数据解包
        self.damage = weapon_data['damage']
        self.rot_speed = weapon_data['speed'] # 角度/秒
        self.radius = weapon_data.get('data', {}).get('radius', 80)
        self.dmg_interval = weapon_data['cooldown']
        
        # 图像处理 (从 effect 字段获取实物图)
        # 注意：这里假设 Controller 已经处理好 image_surf 传进来了
        self.image = weapon_data['image_surf']
        self.rect = self.image.get_rect(center=player.rect.center)
        
        # 判定箱：使用图片实际大小
        self.hitbox = self.rect.inflate(0, 0)
        
        # 运行时状态
        self.angle = start_angle
        self.attack_timer = 0 # 用于控制伤害间隔

    def update(self, dt):
        # 1. 旋转位置计算
        self.angle += self.rot_speed * dt
        if self.angle >= 360: self.angle -= 360
        
        # 简单的极坐标转换
        rad = math.radians(self.angle)
        offset_x = math.cos(rad) * self.radius
        offset_y = math.sin(rad) * self.radius
        
        # 跟随玩家中心
        center_pos = self.player.rect.center
        self.rect.centerx = center_pos[0] + offset_x
        self.rect.centery = center_pos[1] + offset_y
        self.hitbox.center = self.rect.center

        # 2. 伤害判定 (基于时间间隔)
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

    def update(self):
        # [新增] 调试打印：每 60 帧 (约1秒) 打印一次当前持有数量
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
            
        # 3. 处理环绕物 (Orbital) 的生成与同步
        # 策略：检查当前持有的环绕物总数 vs 场景里的 Sprite 总数
        # 如果不一致，说明刚升级了，直接清空重画（确保 360 度均匀分布）
        
        # 统计当前应该有多少个环绕物
        target_orbitals = []
        for w_id in self.equipped_weapons:
            w_data = self.res.data['weapons'].get(w_id)
            if w_data and w_data.get('type') == 'orbital':
                target_orbitals.append(w_id)
                
        # 如果数量不对 (通常是变多了)，重置所有环绕物
        if len(self.orbital_sprites) != len(target_orbitals):
            self._respawn_orbitals(target_orbitals)

        processed_rank = {}

        # 4. 按【索引】遍历，实现独立冷却
         # 4. 处理发射型 (Projectile)
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        screen_center = pygame.math.Vector2(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        direction = mouse_pos - screen_center
        
        processed_rank = {}

        for i, w_id in enumerate(self.equipped_weapons):
            w_data = self.res.data['weapons'].get(w_id)
            if not w_data: continue
            
            # [关键] 只有 type='projectile' (或没写type默认是projectile) 才执行发射逻辑
            w_type = w_data.get('type', 'projectile')
            if w_type != 'projectile':
                continue
            
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

    # fire 方法保持不变，确保接收 angle_offset 传给 Projectile
    def fire(self, w_data, direction, angle_offset):
        player_pos = pygame.math.Vector2(self.player.rect.center)
        projectile_data = w_data.copy()
        projectile_data['image_surf'] = self.res.get_image(w_data['image'])
        
        Projectile(
            pos=player_pos, 
            direction=direction, 
            weapon_data=projectile_data, 
            groups=self.groups, 
            enemy_sprites=self.enemy_sprites,
            obstacle_sprites=self.obstacle_sprites,
            angle_offset=angle_offset
        )

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
            # 获取实物图 key
            effect_key = w_data.get('effect', w_data['image']) # 如果没配effect就用icon兜底
            orb_data['image_surf'] = self.res.get_image(effect_key)
            
            start_angle = i * step
            
            # 创建实体
            orb = Orbital(self.player, [self.groups, self.orbital_sprites], 
                          self.enemy_sprites, orb_data, start_angle)
            
            # 这里不需要手动 add 到 group，因为 Orbital.__init__ 里的 super 已经加了
