import pygame
from src.settings import *
from src.vfx import AnimationPlayer

class GameSprite(pygame.sprite.Sprite):
    """
    基础精灵类。
    所有能画在屏幕上的东西都继承它。
    """
    def __init__(self, groups, pos, z_layer):
        super().__init__(groups)
        # 默认创建一个方块作为占位图 (如果有子类加载了图片，会覆盖这个)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(topleft=pos)
        self.z_layer = z_layer
        
        # 物理碰撞箱 (通常比渲染图稍小，手感更好)
        self.hitbox = self.rect.inflate(0, -10) 

class Entity(GameSprite):
    """
    实体类。
    所有能移动的生物（玩家、敌人）都继承它。
    """
    def __init__(self, groups, pos, z_layer):
        super().__init__(groups, pos, z_layer)
        self.direction = pygame.math.Vector2() # 移动方向 (x, y)
        self.speed = 0                         # 移动速度
        self.obstacle_sprites = None           # 障碍物组 (用于碰撞检测)

    def set_obstacles(self, obstacle_sprites):
        self.obstacle_sprites = obstacle_sprites

    def move(self, dt):
        """
        处理移动和碰撞。
        dt: delta time (秒)
        """
        # 归一化向量 (防止斜向移动速度变快)
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        # 分离轴移动 (X轴)
        self.hitbox.x += self.direction.x * self.speed * dt
        self.collision('horizontal')
        
        # 分离轴移动 (Y轴)
        self.hitbox.y += self.direction.y * self.speed * dt
        self.collision('vertical')
        
        # 同步渲染矩形 (rect 跟随 hitbox)
        self.rect.center = self.hitbox.center

    def collision(self, direction):
        """
        处理与障碍物的碰撞
        """
        if not self.obstacle_sprites:
            return

        # 检测 hitbox 与 obstacle_sprites 的碰撞
        hits = pygame.sprite.spritecollide(self, self.obstacle_sprites, False, 
                                           lambda sprite, obstacle: sprite.hitbox.colliderect(obstacle.hitbox))
        
        if hits:
            if direction == 'horizontal':
                for sprite in hits:
                    # 向右撞
                    if self.direction.x > 0:
                        self.hitbox.right = sprite.hitbox.left
                    # 向左撞
                    if self.direction.x < 0:
                        self.hitbox.left = sprite.hitbox.right
            
            if direction == 'vertical':
                for sprite in hits:
                    # 向下撞
                    if self.direction.y > 0:
                        self.hitbox.bottom = sprite.hitbox.top
                    # 向上撞
                    if self.direction.y < 0:
                        self.hitbox.top = sprite.hitbox.bottom

class Shadow(pygame.sprite.Sprite):
    """通用阴影类"""
    def __init__(self, target_sprite, groups, shadow_surf):
        # 阴影放在 vfx_bottom 层 (地板之上，物体之下)
        super().__init__(groups)
        self.target = target_sprite
        self.image = shadow_surf
        self.rect = self.image.get_rect()
        self.z_layer = LAYERS['vfx_bottom']
        # [修复] 添加 hitbox 防止 collision 检测报错
        self.hitbox = self.rect 
        
        # 初始位置
        self._update_pos()

    def _update_pos(self):
        # 阴影位于物体底部中心
        self.rect.centerx = self.target.rect.centerx
        # 稍微向下偏移一点，制造立体感
        self.rect.centery = self.target.rect.bottom - 5

    def update(self, dt):
        if not self.target.alive():
            self.kill()
        else:
            self._update_pos()

class Tile(GameSprite):
    """
    地图图块类 (墙壁、地板、装饰物)
    支持：高墙逻辑 (Hitbox只在底部)、自动生成阴影
    """
    def __init__(self, pos, groups, sprite_type, surface, 
                 shadow_surf=None, scale_to_width=None):
        super().__init__(groups, pos, z_layer=LAYERS['ground'])
        self.sprite_type = sprite_type

         # 1. 图像处理
        if surface:
            if scale_to_width:
                # [新增] 高墙逻辑：按宽度比例缩放，保持纵横比
                orig_w, orig_h = surface.get_size()
                scale_factor = scale_to_width / orig_w
                new_h = int(orig_h * scale_factor)
                self.image = pygame.transform.smoothscale(surface, (scale_to_width, new_h))
            else:
                self.image = surface
        else:
            self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
            self.image.fill((100, 100, 100))
            
        self.rect = self.image.get_rect(topleft=pos)
        
         # 2. 层级与碰撞箱处理
        if sprite_type == 'wall' or sprite_type == 'tree':
            if sprite_type == 'tree':
                self.z_layer = LAYERS['vfx_top']  # 树放在顶层，实现完全遮挡
            else:
                self.z_layer = LAYERS['main']  # 墙保持在main层
            
            # [核心逻辑] 处理“高物体”
            # 如果图片高度大于 TILE_SIZE (比如 124px 的墙)，
            # 我们认为它的“物理占地”只有最下面那一格 (32x32)
            # 视觉上它会向上延伸
            
            # 重新调整 rect：让 rect 的底部对齐 pos 的底部
            # 注意：传入的 pos 通常是 grid 坐标，即物体的左上角。
            # 对于高物体，pos 应该是它“占地格子”的左上角。
            
            # 底部对齐逻辑
            self.rect.bottomleft = (pos[0], pos[1] + TILE_SIZE)
            
            # 碰撞箱只取底部(32x32)
            self.hitbox = pygame.Rect(self.rect.left, self.rect.bottom - TILE_SIZE, TILE_SIZE, TILE_SIZE)
            # 微调：稍微缩小一点方便移动
            self.hitbox = self.hitbox.inflate(0, -10)
            
            # [新增] 生成阴影 (如果是树)
            if sprite_type == 'tree' and shadow_surf:
                Shadow(self, groups, shadow_surf)
                
        else:
            # 地板、装饰物
            self.z_layer = LAYERS['ground']
            self.hitbox = self.rect # 地板不需要碰撞，但为了兼容性保留
            
            if sprite_type == 'deco':
                # 装饰物也可以稍微有点遮挡关系，或者放在 ground 层
                # 这里简单处理：放在 ground
                pass

class AnimatedTile(Tile):
    """支持序列帧动画的地块 (如水面、火海)"""
    def __init__(self, pos, groups, sprite_type, surface, frame_data, 
                 visual_scale=1.0, offset=(0,0)):
        # 初始化父类，先不传 image
        super().__init__(pos, groups, sprite_type, surface=None)
        
        # 使用通用动画播放器
        # frame_data 格式: {'frames': 16, 'frame_width': 192, 'speed': 10}
        self.anim_player = AnimationPlayer(surface, frame_data, default_speed=frame_data.get('speed', 8))
        self.visual_scale = visual_scale
        self.offset = offset # (x, y) 修正渲染位置
        
        # 初始化第一帧 (dt=0)
        self.image = self.anim_player.get_frame_image(0, loop=True, scale=self.visual_scale)
        # 3. 设置 Hitbox (物理真理)
        # 判定箱严格位于网格坐标 pos，大小为 TILE_SIZE
        self.hitbox = pygame.Rect(pos[0], pos[1], TILE_SIZE, TILE_SIZE).inflate(-10,-10)

        # 4. 设置 Image Rect (视觉对齐)
        self.rect = self.image.get_rect()
        
        if sprite_type == 'tree':
            self.z_layer = LAYERS['vfx_top']  # 树放在顶层，实现完全遮挡
            # [核心对齐]：图片的底边中心 = 判定箱的底边中心 + 偏移量
            # 只要你裁剪了图片底部的透明像素，这行代码能保证树根就在判定箱里
            target_x = self.hitbox.centerx + offset[0]
            target_y = self.hitbox.bottom + offset[1]
            self.rect.midbottom = (target_x, target_y)

        else:
            # 默认逻辑 (居中)
            self.rect = self.image.get_rect(center=(pos[0] + TILE_SIZE//2, pos[1] + TILE_SIZE//2))
            self.z_layer = LAYERS['ground']
            self.hitbox = self.rect

    def update(self, dt):
        # 记录旧的对齐点 (对于树木是底部，对于其他可能是中心)
        old_midbottom = self.rect.midbottom
        old_center = self.rect.center
        
        # 更新图像
        self.image = self.anim_player.get_frame_image(dt, loop=True, scale=self.visual_scale)
        self.rect = self.image.get_rect()
        
        # 恢复位置
        if self.sprite_type == 'tree':
            self.rect.midbottom = old_midbottom
        else:
            self.rect.center = old_center

class YSortCameraGroup(pygame.sprite.Group):
    """
    自定义渲染组：
    1. 摄像机跟随 (Camera Follow)
    2. Y轴排序 (Y-Sort)
    [优化] 单次遍历分组 + 全层级视锥剔除
    """
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()
        
        # [优化] 视锥剔除边界（考虑精灵可能比 TILE_SIZE 大）
        self.cull_margin = TILE_SIZE * 4  # 扩大边界以包含大型精灵

    def _is_visible(self, offset_pos, sprite):
        """检查精灵是否在可见区域内"""
        # 修复：检查精灵矩形是否与屏幕矩形相交
        # 使用精灵实际大小来判断，考虑精灵可能部分在屏幕外但仍可见
        sprite_w = sprite.rect.width
        sprite_h = sprite.rect.height
        
        # 精灵的屏幕矩形
        sprite_rect = pygame.Rect(offset_pos[0], offset_pos[1], sprite_w, sprite_h)
        # 屏幕矩形（加上边距）
        screen_rect = pygame.Rect(-self.cull_margin, -self.cull_margin, 
                                  WINDOW_WIDTH + 2 * self.cull_margin, 
                                  WINDOW_HEIGHT + 2 * self.cull_margin)
        
        return sprite_rect.colliderect(screen_rect)

    def custom_draw(self, player):
        """
        替代原本的 draw() 方法
        [优化] 单次遍历所有精灵，按层级分组，统一视锥剔除
        """
        # 1. 计算偏移量 (目标是让 player 永远在屏幕中心)
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # 2. [优化] 单次遍历，按层级分组
        ground_sprites = []
        vfx_bottom_sprites = []
        main_sprites = []
        vfx_top_sprites = []
        
        for sprite in self.sprites():
            z = sprite.z_layer
            if z == LAYERS['ground']:
                ground_sprites.append(sprite)
            elif z == LAYERS['vfx_bottom']:
                vfx_bottom_sprites.append(sprite)
            elif z == LAYERS['main']:
                main_sprites.append(sprite)
            elif z == LAYERS['vfx_top']:
                vfx_top_sprites.append(sprite)

        # 3. 分层绘制，所有层都应用视锥剔除
        
        # 3.1 地板层 (Ground) - 修复：确保地板能覆盖整个屏幕
        # 对于地板层，暂时禁用视锥剔除，确保所有地板都能被绘制
        # 这样可以避免因为视锥剔除导致背景显示为黑色
        for sprite in ground_sprites:
            offset_pos = sprite.rect.topleft - self.offset
            # 暂时不进行视锥剔除，直接绘制所有地板
            # 这样可以确保屏幕范围内都有地板显示
            self.display_surface.blit(sprite.image, offset_pos)

        # 3.2 底层特效 (vfx_bottom) - 光环、脚印、阴影
        for sprite in vfx_bottom_sprites:
            offset_pos = sprite.rect.topleft - self.offset
            if self._is_visible(offset_pos, sprite):
                self.display_surface.blit(sprite.image, offset_pos)

        # 3.3 主层 (main) - 需要 Y 排序
        # 只对可见的精灵排序，减少排序开销
        visible_main = []
        for sprite in main_sprites:
            offset_pos = sprite.rect.topleft - self.offset
            if self._is_visible(offset_pos, sprite):
                visible_main.append((sprite, offset_pos))
        
        # Y 排序
        visible_main.sort(key=lambda x: x[0].rect.centery)
        
        for sprite, offset_pos in visible_main:
            self.display_surface.blit(sprite.image, offset_pos)

        # 3.4 顶层特效 (vfx_top) - 爆炸、悬浮武器、树木
        for sprite in vfx_top_sprites:
            offset_pos = sprite.rect.topleft - self.offset
            if self._is_visible(offset_pos, sprite):
                self.display_surface.blit(sprite.image, offset_pos)