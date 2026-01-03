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

class Tile(GameSprite):
    """
    地图图块类 (墙壁、地板、装饰物)
    """
    def __init__(self, pos, groups, sprite_type, surface=None):
        # 如果没有传入图片，就画一个灰色方块
        super().__init__(groups, pos, z_layer=LAYERS['ground'])
        self.sprite_type = sprite_type
        
        if surface:
            self.image = surface
        else:
            self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
            if sprite_type == 'wall':
                self.image.fill((100, 100, 100)) # 墙是深灰
                self.z_layer = LAYERS['main']    # 墙和玩家同一层，参与遮挡
            else:
                self.image.fill((50, 50, 50))    # 地板是浅灰
                self.z_layer = LAYERS['ground']  # 地板在最底层

        self.rect = self.image.get_rect(topleft=pos)
        # 如果是墙壁，hitbox 稍微缩小一点，如果是地板，不需要 hitbox (但为了统一先保留)
        self.hitbox = self.rect.inflate(0, -10)

class AnimatedTile(Tile):
    """支持序列帧动画的地块 (如水面、火海)"""
    def __init__(self, pos, groups, sprite_type, surface, frame_data):
        # 初始化父类，先不传 image
        super().__init__(pos, groups, sprite_type, surface=None)
        
        # 使用通用动画播放器
        # frame_data 格式: {'frames': 16, 'frame_width': 192, 'speed': 10}
        self.anim_player = AnimationPlayer(surface, frame_data, default_speed=frame_data.get('speed', 5))
        
        self.image = self.anim_player.frames[0]
        # 如果素材比 TILE_SIZE 大，需要缩放吗？
        # 这里假设水面素材如果是 192x192，我们把它缩放到 TILE_SIZE (64x64)
        if self.image.get_width() != TILE_SIZE:
             self.image = pygame.transform.scale(self.image, (TILE_SIZE, TILE_SIZE))
             
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, 0) # 或者是 (-10, -10)

    def update(self, dt):
        # 播放动画
        raw_frame = self.anim_player.update(dt, loop=True)
        # 实时缩放以匹配地图网格
        self.image = pygame.transform.scale(raw_frame, (TILE_SIZE, TILE_SIZE))

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