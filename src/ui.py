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

class UpgradeCard(UIElement):
    """
    升级选项卡片。
    继承 UIElement 以获得鼠标悬停时的整体缩放效果。
    """
    def __init__(self, center_pos, size, bg_image, option_data, font_title, font_desc):
        # 1. 准备卡片的基础 Surface (未缩放状态)
        self.w, self.h = size
        self.base_surface = pygame.transform.scale(bg_image, size)
        self.option = option_data # 存储 UpgradeOption 对象
        
        # 2. 绘制静态内容到 base_surface 上 (Icon, Title, Desc)
        # 这样缩放时，文字和图标会跟着背景一起缩放
        
        # A. 绘制图标 (居中，靠上)
        # 假设 icon 是 32x32，放大一点显示 (比如 64x64)
        if hasattr(option_data, 'icon_key'): # 确保有图片
            # 这里需要回调 resource manager 获取图片，但为了解耦，
            # 我们假设外部传进来的是已经获取好的 image surface，或者我们在 draw 时绘制
            # 为了简单，我们在外部初始化时把 icon surface 传进来，或者暂时只存数据
            pass

        # 为了性能，我们将内容预渲染到 self.content_surface
        self.content_surface = self.base_surface.copy()
        
        # 计算布局坐标 (相对于卡片左上角)
        cx = self.w // 2
        
        # B. 绘制标题
        title_surf = font_title.render(self.option.title, False, (50, 30, 30))
        title_rect = title_surf.get_rect(center=(cx, self.h * 0.45)) # 放在中间偏上
        self.content_surface.blit(title_surf, title_rect)

        # C. 绘制描述 (支持多行)
        # 逻辑：手动计算文字宽度，如果超过卡片宽度就换行
        max_width = self.w - 40 
        text = self.option.description
        lines = []
        current_line = ""
        
        for char in text:
            # 试探性加上这个字符，计算宽度
            test_line = current_line + char
            w, h = font_desc.size(test_line)
            
            if w < max_width:
                current_line = test_line
            else:
                # 超出了，把之前的存入，当前字符作为新行开始
                lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
            
        # 限制最多显示 3 行
        lines = lines[:3]
        # 绘制行
        line_height = font_desc.get_height() + 5
        # 起始 Y 坐标
        start_y = self.h * 0.65 
        
        for i, line in enumerate(lines):
            desc_surf = font_desc.render(line, False, (80, 80, 80))
            desc_rect = desc_surf.get_rect(center=(cx, start_y + i * line_height))
            self.content_surface.blit(desc_surf, desc_rect)

        # 初始化基类
        # 注意：UIElement 默认接受 surface_normal。这里我们用预渲染好的 content_surface
        super().__init__(center_pos, self.content_surface, scale_on_hover=True)

    def draw_icon(self, icon_surf):
        """额外方法：因为 icon 需要从 loader 获取，可能在 init 后绘制"""
        # 将 icon 绘制到 content_surface 上 (覆盖原有)
        # 重新生成 content_surface = base + icon + text
        self.content_surface = self.base_surface.copy()
        
        # 1. Icon (放大显示)
        icon_scaled = pygame.transform.scale(icon_surf, (64, 64))
        icon_rect = icon_scaled.get_rect(center=(self.w // 2, self.h * 0.20))
        self.content_surface.blit(icon_scaled, icon_rect)
        
        # 2. 重新把 original_image 指向包含 Icon 的图，以便 update 缩放逻辑生效
        self.original_image = self.content_surface
        self.hover_image = self.content_surface

        # 3. 补回文字 (简略写法，实际应该把文字绘制也封装)
        # 由于我们覆盖了 content_surface，这里为了省事，假设 icon 是最后画的
        # 更好的做法是在 __init__ 里传 icon_surf
        pass 

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
        # 字体
        try:
            self.font = pygame.font.Font('assets/fonts/pixel.ttf', 24)
            self.title_font = pygame.font.Font('assets/fonts/pixel.ttf', 60)
            self.info_font = pygame.font.Font('assets/fonts/pixel.ttf', 30)
            self.card_title_font = pygame.font.Font('assets/fonts/pixel.ttf', 32)
            self.card_desc_font = pygame.font.Font('assets/fonts/pixel.ttf', 20)
            # 主菜单字体
            self.menu_title_font = pygame.font.Font('assets/fonts/CevicheOne.ttf', 120)
            self.menu_button_font = pygame.font.Font('assets/fonts/CevicheOne.ttf', 48)
        except:
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 60)
            self.info_font = pygame.font.Font(None, 30)
            self.card_title_font = pygame.font.Font(None, 40)
            self.card_desc_font = pygame.font.Font(None, 24)
            # 主菜单字体 fallback
            self.menu_title_font = pygame.font.Font(None, 120)
            self.menu_button_font = pygame.font.Font(None, 48)
        # 加载光标
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
        self.banner_yellow = self.res.get_image('ribbon_yellow_3slides')
        self.banner_blue = pygame.transform.scale(raw_banner_blue, (self.banner_w, self.banner_h))
        self.banner_red  = pygame.transform.scale(raw_banner_red, (self.banner_w, self.banner_h))
        self.banner_yellow = pygame.transform.scale(self.banner_yellow, (self.banner_w, self.banner_h))
        
        self.card_bg = self.res.get_image('banner_slots')
        self._init_buttons()
        self.level_up_cards = []
        
        # 加载新手引导图片
        self.guide_image = self.res.get_image('guide')
        
        # 创建灰色半透明遮罩（用于教程，能看到游戏画面）
        self.tutorial_mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.tutorial_mask.fill((100, 100, 100))  # 灰色
        self.tutorial_mask.set_alpha(180)  # 透明度
        
        # 加载主菜单背景图片
        self.menu_bg = self.res.get_image('cover')
        # 缩放背景图片到窗口大小
        self.menu_bg = pygame.transform.scale(self.menu_bg, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # 主菜单按钮文本和位置（用于点击检测）
        self.menu_started_rect = None
        self.menu_quit_rect = None

    def _init_buttons(self):
        """组装所有按钮"""
        # 辅助加载与缩放 Icon
        def get_icon(key):
            return pygame.transform.scale(self.res.get_image(key), (32, 32))
        icon_resume = get_icon('icon_resume')
        icon_restart = get_icon('icon_restart')
        icon_quit = get_icon('icon_quit')
        icon_home = get_icon('icon_home')
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
            # Home (Red)
            Button((cx + spacing, btn_y), btn_red, btn_red_p, icon_home, 'home')
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
        
        # 检查主菜单按钮
        if hasattr(self, 'menu_started_rect') and self.menu_started_rect:
            if self.menu_started_rect.collidepoint(mouse_pos):
                hovering = True
        if hasattr(self, 'menu_quit_rect') and self.menu_quit_rect:
            if self.menu_quit_rect.collidepoint(mouse_pos):
                hovering = True
        
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

    def setup_level_up(self, options):
        """
        当升级发生时调用。接收 3 个 Option 数据，生成 3 个 Card 对象。
        """
        self.level_up_cards = []
        
        # 布局计算
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        
        # 卡片大小：宽约为屏幕 1/5，高约为屏幕 3/5 (保持比例)
        card_w = 260
        card_h = 450
        spacing = 40
        total_w = 3 * card_w + 2 * spacing
        start_x = cx - total_w // 2 + card_w // 2
        
        for i, opt in enumerate(options):
            pos_x = start_x + i * (card_w + spacing)
            pos_y = cy + 30 # 稍微靠下，留出上方 Banner 位置
            
            # 创建卡片
            card = UpgradeCard(
                center_pos=(pos_x, pos_y),
                size=(card_w, card_h),
                bg_image=self.card_bg,
                option_data=opt,
                font_title=self.card_title_font,
                font_desc=self.card_desc_font
            )
            
            # 注入 Icon (如果有)
            if hasattr(opt, 'icon_key') and opt.icon_key:
                icon_surf = self.res.get_image(opt.icon_key)
                # 这是一个 Hack，手动把 Icon 画上去并刷新 texture
                # 重新绘制流程：
                final_surf = card.base_surface.copy()
                
                # 画 Icon
                icon_scaled = pygame.transform.scale(icon_surf, (80, 80))
                icon_rect = icon_scaled.get_rect(center=(card_w // 2, card_h * 0.25))
                final_surf.blit(icon_scaled, icon_rect)
                
                # 画 Title
                t_surf = self.card_title_font.render(opt.title, False, (60, 40, 40))
                t_rect = t_surf.get_rect(center=(card_w // 2, card_h * 0.55))
                final_surf.blit(t_surf, t_rect)
                
                # 画 Desc (简单折行处理：如果太长手动切一下，这里暂做单行)
                d_surf = self.card_desc_font.render(opt.description, False, (100, 80, 80))
                d_rect = d_surf.get_rect(center=(card_w // 2, card_h * 0.70))
                final_surf.blit(d_surf, d_rect)
                
                card.original_image = final_surf
                card.hover_image = final_surf # 悬停时不换图，只缩放
            
            self.level_up_cards.append(card)

    def draw_level_up(self):
        # 1. 遮罩
        self.display_surface.blit(self.mask, (0, 0))
        
        # 2. 顶部 Banner
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        banner_rect = self.banner_yellow.get_rect(center=(cx, 80)) # 顶部
        self.display_surface.blit(self.banner_yellow, banner_rect)
        
        # Banner 文字 "Level UP"
        title_surf = self.title_font.render("Level UP", False, (80, 50, 20))
        title_rect = title_surf.get_rect(center=(cx, 75))
        self.display_surface.blit(title_surf, title_rect)
        
        # 3. 底部提示文字
        info_surf = self.info_font.render("Click To Choose Your Reward", False, (255, 255, 255))
        info_rect = info_surf.get_rect(center=(cx, WINDOW_HEIGHT - 50))
        self.display_surface.blit(info_surf, info_rect)
        
        # 4. 绘制卡片
        mouse_pos = pygame.mouse.get_pos()
        for card in self.level_up_cards:
            card.update(mouse_pos)
            card.draw(self.display_surface)

    def get_level_up_choice(self):
        """检测升级界面点击，返回选中的 UpgradeOption"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        for card in self.level_up_cards:
            if card.check_click(mouse_pos, mouse_pressed):
                return card.option
        return None

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

    # ====================================================
    # 4. 新手引导教程 (状态: TUTORIAL)
    # ====================================================
    def draw_tutorial(self):
        """绘制新手引导教程"""
        # 1. 绘制灰色半透明遮罩（能看到游戏画面）
        self.display_surface.blit(self.tutorial_mask, (0, 0))
        
        # 2. 居中显示 guide.png
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        guide_rect = self.guide_image.get_rect(center=(cx, cy))
        self.display_surface.blit(self.guide_image, guide_rect)
        
        # 存储 guide_rect 以便点击检测
        self.guide_rect = guide_rect

    def check_tutorial_click(self, mouse_pos):
        """检测点击是否在 guide.png 区域外，返回 True 表示应该关闭教程"""
        if hasattr(self, 'guide_rect'):
            # 如果点击位置不在 guide_rect 内，返回 True（关闭教程）
            return not self.guide_rect.collidepoint(mouse_pos)
        return True

    def _render_text_with_outline(self, font, text, text_color, outline_color, outline_width=2):
        """渲染带描边的文字"""
        # 先渲染描边（在多个方向偏移）
        offsets = [(-outline_width, -outline_width), (outline_width, -outline_width),
                   (-outline_width, outline_width), (outline_width, outline_width),
                   (0, -outline_width), (0, outline_width),
                   (-outline_width, 0), (outline_width, 0)]
        
        # 获取文字尺寸
        text_surf = font.render(text, True, text_color)
        w, h = text_surf.get_size()
        
        # 创建更大的 Surface 以容纳描边
        outline_surf = pygame.Surface((w + outline_width * 2, h + outline_width * 2), pygame.SRCALPHA)
        
        # 绘制描边
        for offset_x, offset_y in offsets:
            outline_text = font.render(text, True, outline_color)
            outline_surf.blit(outline_text, (outline_width + offset_x, outline_width + offset_y))
        
        # 绘制主文字（在描边之上）
        text_surf = font.render(text, True, text_color)
        outline_surf.blit(text_surf, (outline_width, outline_width))
        
        return outline_surf

    # ====================================================
    # 5. 主菜单 (状态: MENU)
    # ====================================================
    def draw_main_menu(self):
        """绘制主菜单"""
        # 1. 绘制背景图片
        self.display_surface.blit(self.menu_bg, (0, 0))
        
        # 2. 绘制标题（使用 title.svg）
        # 距离顶部220px，距离右边距100px
        title_image = self.res.get_image('title')
        title_rect = title_image.get_rect()
        title_rect.top = 200  # 距离顶部220px
        title_rect.right = WINDOW_WIDTH - 100  # 距离右边距100px
        self.display_surface.blit(title_image, title_rect)
        
        # 3. 加载选项背景
        choice_bg = self.res.get_image('choice_bg')
        
        # 4. 计算选项位置
        # 标题底部位置
        title_bottom = title_rect.bottom
        # 标题和选项之间间距为 36
        first_option_top = title_bottom + 36
        # 选项之间间距为 16
        option_spacing = 16
        
        # 计算第一个选项的中心 Y 坐标（需要知道背景高度）
        bg_height = choice_bg.get_height()
        first_option_center_y = first_option_top + bg_height // 2
        second_option_center_y = first_option_center_y + bg_height + option_spacing
        
        # 选项的X坐标：与标题右对齐（距离右边距100px）
        option_x = WINDOW_WIDTH - 100 - choice_bg.get_width() // 2
        
        mouse_pos = pygame.mouse.get_pos()
        
        # 5. 绘制 "Started" 选项
        started_bg_rect = choice_bg.get_rect(center=(option_x, first_option_center_y))
        self.display_surface.blit(choice_bg, started_bg_rect)
        
        # 渲染带描边的文字
        started_text_surf = self._render_text_with_outline(
            self.menu_button_font, "Started", 
            (0, 0, 0),  # 黑色文字
            (255, 255, 255),  # 白色描边
            outline_width=2
        )
        started_text_rect = started_text_surf.get_rect(center=started_bg_rect.center)
        self.display_surface.blit(started_text_surf, started_text_rect)
        
        # 更新点击检测区域（使用背景区域）
        self.menu_started_rect = started_bg_rect
        
        # 6. 绘制 "Quit" 选项
        quit_bg_rect = choice_bg.get_rect(center=(option_x, second_option_center_y))
        self.display_surface.blit(choice_bg, quit_bg_rect)
        
        # 渲染带描边的文字
        quit_text_surf = self._render_text_with_outline(
            self.menu_button_font, "Quit",
            (0, 0, 0),  # 黑色文字
            (255, 255, 255),  # 白色描边
            outline_width=2
        )
        quit_text_rect = quit_text_surf.get_rect(center=quit_bg_rect.center)
        self.display_surface.blit(quit_text_surf, quit_text_rect)
        
        # 更新点击检测区域（使用背景区域）
        self.menu_quit_rect = quit_bg_rect

    def get_main_menu_click(self, mouse_pos):
        """检测主菜单点击位置，返回 'start' 或 'quit' 或 None"""
        if self.menu_started_rect and self.menu_started_rect.collidepoint(mouse_pos):
            return 'start'
        if self.menu_quit_rect and self.menu_quit_rect.collidepoint(mouse_pos):
            return 'quit'
        return None
