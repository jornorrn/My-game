import pygame
from src.settings import *

class UIElement:
    """
    UI 交互元素的基类。
    负责通用的悬停检测、点击检测和悬停时的缩放动画。
    后续的 UpgradeCard 也可以继承此类。
    """
    def __init__(self, center_pos, surface_normal, surface_hover=None, scale_on_hover=True):
        self.original_image = surface_normal
        # 如果没有专门的 hover 图片，就用原图
        self.hover_image = surface_hover if surface_hover else surface_normal
        
        self.image = self.original_image
        self.rect = self.image.get_rect(center=center_pos)
        
        self.is_hovered = False
        self.scale_on_hover = scale_on_hover
        self.scale_factor = 1.0
        self.target_scale = 1.0

    def update(self, mouse_pos):
        """更新状态：悬停检测与动画计算"""
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # 悬停缩放逻辑
        if self.scale_on_hover:
            self.target_scale = 1.1 if self.is_hovered else 1.0
            # 简单的线性插值动画 (Lerp)
            self.scale_factor += (self.target_scale - self.scale_factor) * 0.2

    def draw(self, surface):
        """绘制逻辑"""
        img_to_draw = self.hover_image if self.is_hovered else self.original_image
        
        if self.scale_on_hover and abs(self.scale_factor - 1.0) > 0.01:
            # 动态缩放
            w = int(img_to_draw.get_width() * self.scale_factor)
            h = int(img_to_draw.get_height() * self.scale_factor)
            img_to_draw = pygame.transform.scale(img_to_draw, (w, h))
        
        # 保持中心位置不变
        draw_rect = img_to_draw.get_rect(center=self.rect.center)
        surface.blit(img_to_draw, draw_rect)

    def check_click(self, mouse_pos, mouse_pressed):
        """返回是否被点击"""
        if self.is_hovered and mouse_pressed[0]:
            return True
        return False

class Button(UIElement):
    """
    具体的按钮类。
    集成背景图、按下图、Icon的组合逻辑。
    """
    def __init__(self, center_pos, bg_normal, bg_pressed, icon=None, action_name=None):
        # 预先合成 Icon 到背景上，避免每帧 blit 两次
        self.surf_normal = bg_normal.copy()
        self.surf_pressed = bg_pressed.copy()
        
        if icon:
            # 将 Icon 居中绘制到按钮背景上
            icon_rect = icon.get_rect(center=(bg_normal.get_width()//2, bg_normal.get_height()//2 - 8))
            self.surf_normal.blit(icon, icon_rect)
            
            # 按下状态，Icon 下沉 2px
            icon_rect.y += 4
            self.surf_pressed.blit(icon, icon_rect)
            
        super().__init__(center_pos, self.surf_normal, self.surf_pressed, scale_on_hover=True)
        self.action_name = action_name


class UI:
    """
    UI 管理类。
    职责：
    1. 绘制 HUD (血条、经验、击杀)
    2. 绘制 交互菜单 (升级选择、暂停、结算)
    注意：所有图片资源必须通过 self.res.get_image(key) 获取
    """
    
    def __init__(self, display_surface, resource_manager):
        self.display_surface = display_surface
        self.res = resource_manager
        # 1. 字体
        try:
            self.font = pygame.font.Font('assets/fonts/pixel.ttf', 24)
            self.title_font = pygame.font.Font('assets/fonts/pixel.ttf', 60)
            self.info_font = pygame.font.Font('assets/fonts/pixel.ttf', 30)
        except:
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 60)
            self.info_font = pygame.font.Font(None, 30)
        # 2. 加载光标
        self.cursor_ptr = self.res.get_image('pointer') # 默认箭头
        self.cursor_hov = self.res.get_image('cursor')  # 悬停手势
        pygame.mouse.set_visible(False) # 隐藏系统光标

        # 运行时临时数据 (用于存储按钮/卡片的 rect，以便检测点击)
        self.current_ui_rects = [] 

        # 绘制血条准备
        self.bar_L = self.res.get_image('bar_left')
        self.bar_M = self.res.get_image('bar_mid')
        self.bar_R = self.res.get_image('bar_right')
        self.bar_fill = self.res.get_image('bigbar_fill') 
        self.w_L = self.bar_L.get_width() - 12  # 22-10=10
        self.w_R = self.bar_R.get_width() - 14   # 24-14=10
        self.frame_height = 50
        self.fill_height = 24
        self.fill_offset_y = 12

        # 创建半透明遮罩 (黑色，透明度 150/255)
        self.mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.mask.fill((0, 0, 0))
        self.mask.set_alpha(150)

        # 加载 Banner
        self.banner_w = WINDOW_WIDTH // 3
        self.banner_h = WINDOW_HEIGHT // 5
        raw_banner_blue = self.res.get_image('ribbon_blue_3slides')
        raw_banner_red  = self.res.get_image('ribbon_red_3slides')
        self.banner_blue = pygame.transform.scale(raw_banner_blue, (self.banner_w, self.banner_h))
        self.banner_red  = pygame.transform.scale(raw_banner_red, (self.banner_w, self.banner_h))

        self._init_buttons()

    def _init_buttons(self):
        """组装所有按钮"""
        # 辅助加载与缩放 Icon
        def get_icon(key):
            return pygame.transform.scale(self.res.get_image(key), (32, 32))
        icon_resume = get_icon('icon_resume')
        icon_restart = get_icon('icon_restart')
        icon_quit = get_icon('icon_quit')
        icon_pause = get_icon('icon_pause')
        
        # 按钮背景
        btn_blue = self.res.get_image('button_blue')
        btn_blue_p = self.res.get_image('button_blue_pressed')
        btn_red = self.res.get_image('button_red')
        btn_red_p = self.res.get_image('button_red_pressed')
        btn_yellow = self.res.get_image('button_yellow')
        btn_yellow_p = self.res.get_image('button_yellow_pressed')
        
        # 布局中心
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        # 按钮位于 Banner 下方，间距随 Banner 高度调整
        btn_y = cy + self.banner_h // 2 + 20 
        spacing = 90
        # --- 暂停菜单按钮组 ---
        self.pause_buttons = [
            # Resume (Yellow)
            Button((cx, btn_y), btn_yellow, btn_yellow_p, icon_resume, 'resume'),
            # Restart (Blue)
            Button((cx - spacing, btn_y), btn_blue, btn_blue_p, icon_restart, 'restart'),
            # Quit (Red)
            Button((cx + spacing, btn_y), btn_red, btn_red_p, icon_quit, 'quit')
        ]
        # --- 死亡菜单按钮组 ---
        self.death_buttons = [
            # Restart (Blue) - 居左
            Button((cx - 50, btn_y), btn_blue, btn_blue_p, icon_restart, 'restart'),
            # Quit (Red) - 居右
            Button((cx + 50, btn_y), btn_red, btn_red_p, icon_quit, 'quit')
        ]
        # --- 右上角 HUD 暂停按钮 ---
        self.hud_buttons = [
            Button((WINDOW_WIDTH - 50, 50), btn_yellow, btn_yellow_p, icon_pause, 'pause_game')
        ]

    def draw_custom_cursor(self):
        """绘制自定义光标"""
        mouse_pos = pygame.mouse.get_pos()
        
        # 检查是否悬停在任何活跃按钮上
        hovering = False
        
        # 收集当前屏幕上所有可能交互的按钮
        active_lists = [self.hud_buttons] # HUD 按钮总是活跃
        # 如果是暂停，加上暂停按钮... 这里为了简化，我们只检查当前绘制的按钮状态
        # 由于 draw 方法里已经更新了 button.is_hovered，我们可以直接利用
        
        all_active_btns = self.hud_buttons + self.pause_buttons + self.death_buttons
        if any(btn.is_hovered for btn in all_active_btns):
            hovering = True
            
        cursor_img = self.cursor_hov if hovering else self.cursor_ptr
        self.display_surface.blit(cursor_img, mouse_pos)

    def draw_bar(self, x, y, current, max_val, target_width=300):
        """
        绘制血条
        x, y: 外框左上角
        target_width: 外框总宽度
        """
        # --- 1. 绘制背景框 ---
        self.display_surface.blit(self.bar_L, (x, y))
        # 右坐标 = x + 总宽 - 右宽
        self.display_surface.blit(self.bar_R, (x + target_width - self.w_R, y))
        # 中间 (拉伸) 宽度 = 总宽 - 左宽 - 右宽
        mid_target_w = target_width - self.w_L - self.w_R
        if mid_target_w > 0:
            mid_scaled = pygame.transform.scale(self.bar_M, (mid_target_w, self.frame_height))
            # 坐标 = x + 左宽
            self.display_surface.blit(mid_scaled, (x + self.w_L, y))
        
        # --- 2. 绘制血条填充 ---
        ratio = current / max_val
        ratio = max(0, min(1, ratio))
        # 填充区域的最大宽度 = 中间部分的宽度 (即不覆盖左右两边的盖子)
        max_fill_w = mid_target_w + 12
        # 当前实际宽度
        current_fill_w = int(max_fill_w * ratio)
        if current_fill_w > 0:
            # 拉伸 fill 素材
            fill_surf = pygame.transform.scale(self.bar_fill, (current_fill_w, self.fill_height))
            # 绘制坐标：
            self.display_surface.blit(fill_surf, (x + self.w_L, y + self.fill_offset_y))
            
        # --- 3. 绘制文字 ---
        txt = f"{int(current)}/{max_val}"
        txt_surf = self.font.render(txt, False, (255, 255, 255))
        # 稍微向下微调一点视觉中心
        txt_rect = txt_surf.get_rect(center=(x + target_width // 2, y + self.frame_height // 2 - 2))
        self.display_surface.blit(txt_surf, txt_rect)

    def draw_hud(self, player):
        '''绘制战斗HUD'''
        self.draw_bar(20, 20, player.current_hp, player.stats['max_hp'], target_width=300)
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.hud_buttons:
            btn.update(mouse_pos)
            btn.draw(self.display_surface)

    def draw_xp_text(self, level, xp):
        # 简单显示等级
        text_surf = self.font.render(f'LV: {level}  XP: {int(xp)}', False, COLORS['white'])
        x = self.display_surface.get_width() - 10
        y = 10
        text_rect = text_surf.get_rect(topright=(x, y))
        self.display_surface.blit(text_surf, text_rect)

    #def display(self, player):
        #"""每帧调用的绘制入口"""
        #self.draw_health_bar(player.current_hp, player.stats['max_hp'])
        #self.draw_xp_text(player.level, player.xp)

    # ====================================================
    # 2. 升级选择 (状态: LEVEL_UP)
    # ====================================================
    def draw_level_up(self, options):
        """
        绘制三选一窗口。
        options: 包含 3 个升级数据的列表 (来自 JSON)
        """
        # 清空上一帧的点击区域
        self.current_ui_rects = []
        
        # 实现逻辑：
        # 1. 绘制半透明黑色遮罩 (覆盖全屏)
        # 2. 循环绘制 3 个卡片面板
        #    - 从 option['image'] 获取图标 key -> self.res.get_image(key)
        #    - 绘制标题、描述
        #    - 将卡片的 Rect 添加到 self.current_ui_rects 列表中
        pass

    # ====================================================
    # 3. 暂停菜单 (状态: PAUSED)
    # ====================================================
    def _draw_menu_base(self, banner_img, title_text, buttons):
        """通用菜单绘制"""
        # 遮罩
        self.display_surface.blit(self.mask, (0, 0))
        
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        mouse_pos = pygame.mouse.get_pos()
        
        # 绘制 Banner
        banner_rect = banner_img.get_rect(center=(cx, cy - 50))
        self.display_surface.blit(banner_img, banner_rect)
        
        # 绘制标题
        title_surf = self.title_font.render(title_text, False, (50, 30, 30))
        title_rect = title_surf.get_rect(center=(banner_rect.centerx, banner_rect.centery - 10))
        self.display_surface.blit(title_surf, title_rect)
        
        # 绘制按钮
        for btn in buttons:
            btn.update(mouse_pos)
            btn.draw(self.display_surface)

    def draw_pause(self):
        self._draw_menu_base(self.banner_blue, "PAUSED", self.pause_buttons)

    def draw_game_over(self):
        self._draw_menu_base(self.banner_red, "YOU DIED", self.death_buttons)
        

    # ====================================================
    # 交互入口 (Game.events 调用)
    # ====================================================
    def get_click_action(self, state):
        """专门处理点击事件，供 Game 类调用"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        # 确定当前有效的按钮列表
        target_buttons = []
        if state == 'PLAYING':
            target_buttons = self.hud_buttons
        elif state == 'PAUSED':
            target_buttons = self.pause_buttons
        elif state == 'GAME_OVER':
            target_buttons = self.death_buttons
            
        for btn in target_buttons:
            if btn.check_click(mouse_pos, mouse_pressed):
                return btn.action_name
        return None

    def process_click(self, mouse_pos, game_state):
        """
        处理鼠标点击事件。
        返回: 被点击的对象的索引或 ID，如果没有点中则返回 None
        """
        if game_state == 'LEVEL_UP':
            for index, rect in enumerate(self.current_ui_rects):
                if rect.collidepoint(mouse_pos):
                    return index # 返回选中了第几个卡片
        
        # 可以在这里扩展 PAUSE 菜单的按钮点击
        return None