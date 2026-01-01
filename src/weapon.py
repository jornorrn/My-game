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

    def update(self):
        # [新增] 调试打印：每 60 帧 (约1秒) 打印一次当前持有数量
        if pygame.time.get_ticks() % 1000 < 20:
             print(f"[WEAPON DEBUG] Holding {len(self.equipped_weapons)} weapons. Cooldowns len: {len(self.cooldowns)}")

        current_time = pygame.time.get_ticks()
        
        # 1. 自动扩容冷却列表 (防止数组越界)
        while len(self.cooldowns) < len(self.equipped_weapons):
            self.cooldowns.append(0)

        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        screen_center = pygame.math.Vector2(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        direction = mouse_pos - screen_center
        
        # 2. 统计每种ID的总数 (用于计算扇形)
        total_counts = {}
        for w_id in self.equipped_weapons:
            total_counts[w_id] = total_counts.get(w_id, 0) + 1
            
        # 3. 记录处理进度
        processed_rank = {}

        # 4. 按【索引】遍历，实现独立冷却
        for i, w_id in enumerate(self.equipped_weapons):
            w_data = self.res.data['weapons'].get(w_id)
            if not w_data: continue
            
            # 计算扇形参数
            count = total_counts[w_id]
            rank = processed_rank.get(w_id, 0)
            processed_rank[w_id] = rank + 1
            
            angle_offset = 0
            if count > 1:
                spread = 15 * (count - 1)
                angle_offset = (-spread / 2) + (rank * (spread / (count - 1)))

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