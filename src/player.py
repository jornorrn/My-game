import pygame
import math
from src.settings import *
from src.components import Entity
from src.weapon import WeaponController
from src.vfx import FlashEffect

class FloatingWeapon(pygame.sprite.Sprite):
    """纯装饰用的悬浮武器"""
    def __init__(self, groups, image, player, angle_offset, distance=50):
        # 放在 vfx_top 层，不挡住玩家
        super().__init__(groups)
        self.player = player
        self.original_image = image
        self.image = image
        self.z_layer = LAYERS['vfx_top']
        self.angle_offset = angle_offset
        self.distance = distance
        self.rect = self.image.get_rect()
        # 不需要 hitbox，因为只是装饰

    def update(self, dt):
        center = self.player.rect.center
        
        # 简单的环绕动画
        # t = pygame.time.get_ticks() / 1000 # 旋转速度
        # angle = t * 2 + math.radians(self.angle_offset) # 动态旋转
        
        # 或者 保持固定相对位置 (跟随身后)
        rad = math.radians(self.angle_offset)
        
        # [修改] 距离计算：基于角色大小 + 基础距离 + 呼吸浮动
        base_dist = (self.player.hitbox.width / 2) + 15 
        t = pygame.time.get_ticks() / 300
        hover_offset = math.sin(t + self.angle_offset) * 3
        
        final_dist = base_dist + hover_offset
        
        x = center[0] + math.cos(rad) * final_dist
        y = center[1] + math.sin(rad) * final_dist
        
        self.rect.center = (x, y)


class Player(Entity):
    def __init__(self, pos, groups, obstacle_sprites, enemy_sprites, resource_manager):
        super().__init__(groups, pos, z_layer=LAYERS['main'])
        
        self.res = resource_manager
        
        # 动画状态机
        self.status = 'down'
        self.frame_index = 0
        self.animation_speed = 10
        self.animations = {} # 存放切割后的图片列表
        # 加载并切割图片
        self.import_assets()
        # 设置初始图片
        self.image = self.animations[self.status][0]
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(-4, -10) # 针对16x20的小人微调碰撞箱
        self.set_obstacles(obstacle_sprites)
        # 生成阴影
        shadow_img = self.res.get_image('shadows')
        shadow_img = pygame.transform.scale(shadow_img, (24, 10))
        shadow_img.set_alpha(100)
        
        from src.components import Shadow # 局部导入防循环，或放顶部
        Shadow(self, groups, shadow_img)

        # 数值属性
        self.stats = {
            'max_hp': 100,
            'speed': 300,        # 像素/秒
            'pickup_range': 150
        }
        self.current_hp = self.stats['max_hp']
        self.xp = 0
        self.level = 1
        # 使用经验计算公式初始化经验要求
        self.xp_required = self.calculate_xp_required(self.level)
        
        # 战斗状态
        self.is_dead = False
        self.iframes = 500       # 无敌时间 (毫秒)
        self.last_hit_time = 0
        
        # 武器接口
        self.weapon_controller = WeaponController(self, groups, enemy_sprites, 
                        obstacle_sprites, resource_manager)
        
        # 悬浮武器组
        self.floating_weapons = pygame.sprite.Group()
        self.visual_weapon_cache = [] # 记录当前显示的武器ID列表，防止每帧重建

    def update_floating_weapons(self):
        """
        检查武器列表变化，更新悬浮显示
        """
        current_ids = self.weapon_controller.equipped_weapons
        # 只关心发射型武器 (projectile)
        proj_ids = []
        for w_id in current_ids:
            w_data = self.res.data['weapons'].get(w_id)
            if w_data and w_data.get('type', 'projectile') == 'projectile':
                proj_ids.append(w_id)
        
        # 如果列表没变，不处理
        if proj_ids == self.visual_weapon_cache:
            return
        self.visual_weapon_cache = proj_ids.copy()
        # 清空旧的
        for s in self.floating_weapons: s.kill()
        self.floating_weapons.empty()
        # 重新生成
        count = len(proj_ids)
        if count == 0: return
        
        # 排列逻辑：均匀分布在玩家身后 (-45度 到 225度) 或者是 360度
        step = 360 / count
        for i, w_id in enumerate(proj_ids):
            w_data = self.res.data['weapons'].get(w_id)
            # 使用 ICON 图像
            img = self.res.get_image(w_data['image'])
            # 缩小一点
            img = pygame.transform.scale(img, (24, 24))
            
            FloatingWeapon(
                groups=[self.groups()[0], self.floating_weapons], # 加入 all_sprites 以便被绘制
                image=img,
                player=self,
                angle_offset=i * step,
                distance=40
            )

    def input(self):
        """处理键盘输入"""
        keys = pygame.key.get_pressed()

        # 移动输入
        if keys[pygame.K_w]:
            self.direction.y = -1
        elif keys[pygame.K_s]:
            self.direction.y = 1
        else:
            self.direction.y = 0

        if keys[pygame.K_a]:
            self.direction.x = -1
        elif keys[pygame.K_d]:
            self.direction.x = 1
        else:
            self.direction.x = 0

    def import_assets(self):
        """切割 Sprite Sheet"""
        # 1. 获取整张大图 (Key 是文件名，无后缀)
        sprite_sheet = self.res.get_image('character_18_frame16x20')
        
        # 2. 确认单帧尺寸 (根据文件名)
        frame_w, frame_h = 16, 20
        
        # 3. 切割逻辑 (假设 3列 4行: 下, 左, 右, 上)
        self.animations = {'down': [], 'left': [], 'right': [], 'up': []}
        
        # 辅助函数: 切割一行
        def get_row(row_index, amount):
            frames = []
            for col in range(amount):
                x = col * frame_w
                y = row_index * frame_h
                # subsurface 共享内存，效率高
                rect = pygame.Rect(x, y, frame_w, frame_h)
                # 放大一点显示，不然16像素太小了 (可选，这里放大2倍)
                surf = sprite_sheet.subsurface(rect)
                scaled_surf = pygame.transform.scale(surf, (32, 40)) 
                frames.append(scaled_surf)
            return frames

        self.animations['down']  = get_row(0, 3)
        self.animations['left']  = get_row(1, 3)
        self.animations['right'] = get_row(2, 3)
        self.animations['up']    = get_row(3, 3)

    def animate(self, dt):
        # 如果停止移动
        if self.direction.magnitude() == 0:
            # [修改] 静止时显示第 1 帧 (中间的站立图)
            self.image = self.animations[self.status][1]
            # 可选：重置 frame_index 到 1，这样下次移动从 1 开始算
            # self.frame_index = 1
        else:
            # 移动中：循环播放 0 -> 1 -> 2 -> 0
            self.frame_index += self.animation_speed * dt
            if self.frame_index >= len(self.animations[self.status]):
                self.frame_index = 0
            
            # 取整显示当前帧
            self.image = self.animations[self.status][int(self.frame_index)]
            
        # 保持 rect 中心对齐 (防止图片尺寸微小差异导致抖动)
        # 注意：这行代码非常重要，必须保留
        self.rect = self.image.get_rect(center=self.hitbox.center)
    def get_mouse_direction(self):
        """计算鼠标相对于屏幕中心的角度，并改变朝向图片"""
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        screen_center = pygame.math.Vector2(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        diff = mouse_pos - screen_center
        
        # 计算角度 (-180 到 180)
        angle = math.degrees(math.atan2(-diff.y, diff.x))
        if -45 <= angle < 45: self.status = 'right'
        elif 45 <= angle < 135: self.status = 'up'
        elif -135 <= angle < -45: self.status = 'down'
        else: self.status = 'left'

    def calculate_xp_required(self, level):
        """
        根据等级计算所需经验值
        使用指数增长曲线，使升级随等级提升变慢
        公式：base * (multiplier ^ (level - 1))
        """
        base_xp = 100  # 基础经验值（1级）
        multiplier = 1.5  # 增长倍数，使升级变慢
        
        # 使用指数增长，匹配游戏难度
        # 等级越高，所需经验值增长越快
        xp_needed = base_xp * (multiplier ** (level - 1))
        
        # 为了匹配难度，可以添加额外的难度系数
        # 例如：高等级时额外增加经验要求
        if level > 10:
            difficulty_bonus = 1.0 + (level - 10) * 0.1  # 10级后每级额外增加10%
            xp_needed *= difficulty_bonus
        
        return int(xp_needed)
    
    def check_level_up(self):
        """检查是否升级"""
        if self.xp >= self.xp_required:
            self.xp -= self.xp_required
            self.level += 1
            # 使用新的经验计算公式，使升级随等级提升变慢
            self.xp_required = self.calculate_xp_required(self.level)
            return True
        return False

    def take_damage(self, amount):
        """受击逻辑"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_hit_time < self.iframes:
            return

        self.current_hp -= amount
        # 确保生命值不会低于0
        if self.current_hp < 0:
            self.current_hp = 0
        self.last_hit_time = current_time
        print(f"[DEBUG] Player hit! HP: {self.current_hp}")
        FlashEffect(self, [self.groups()[0]], duration=0.2)

        if self.current_hp <= 0:
            self.is_dead = True

    def update(self, dt):
        self.speed = self.stats['speed']
        self.input()
        self.get_mouse_direction()
        self.animate(dt) # [新增] 驱动动画
        self.move(dt)
        self.weapon_controller.update()
        self.update_floating_weapons()
        self.floating_weapons.update(dt) # 虽然 all_sprites 会 update 它们，但这不冲突

