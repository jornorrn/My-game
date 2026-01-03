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
    """
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player):
        """
        替代原本的 draw() 方法
        """
        # 1. 计算偏移量 (目标是让 player 永远在屏幕中心)
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # 2. 对所有精灵进行排序 (Y坐标小的先画，Y坐标大的后画 -> 产生遮挡关系)
        #    注意：只对 LAYERS['main'] 层级的物体排序，地板层不需要排序
        #    为了性能，我们分层绘制
        
        # 先画地板 (Ground)
        for sprite in self.sprites():
            if sprite.z_layer == LAYERS['ground']:
                offset_pos = sprite.rect.topleft - self.offset
                # 简单的视锥剔除 (Culling): 如果物体在屏幕外，就不画 (优化性能)
                if -TILE_SIZE < offset_pos.x < WINDOW_WIDTH and -TILE_SIZE < offset_pos.y < WINDOW_HEIGHT:
                    self.display_surface.blit(sprite.image, offset_pos)

        # [新增] 画底层特效 (Layer 1: vfx_bottom) - 比如光环、脚印
        # 这些东西在地面之上，但在角色之下，且不需要Y轴排序(通常扁平)
        for sprite in self.sprites():
            if sprite.z_layer == LAYERS['vfx_bottom']:
                offset_pos = sprite.rect.topleft - self.offset
                self.display_surface.blit(sprite.image, offset_pos)

        # 3. 画活动物体 (Layer 2: main) - 需要 YSort
        # 只筛选 main 层的物体进行排序
        main_sprites = [s for s in self.sprites() if s.z_layer == LAYERS['main']]
        sorted_sprites = sorted(main_sprites, key=lambda s: s.rect.centery)

        for sprite in sorted_sprites:
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

        # 4. 画顶层特效 (Layer 3: vfx_top) - 比如爆炸、悬浮武器
        for sprite in self.sprites():
            if sprite.z_layer == LAYERS['vfx_top']:
                offset_pos = sprite.rect.topleft - self.offset
                self.display_surface.blit(sprite.image, offset_pos)