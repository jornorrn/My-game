import pygame
from src.settings import *

class Button:
    def __init__(self, x, y, image_normal, image_pressed, icon=None, action_name=None):
        self.image_normal = image_normal
        self.image_pressed = image_pressed
        self.rect = self.image_normal.get_rect(center=(x, y))
        self.icon = icon
        self.action_name = action_name # 用于返回点击了什么功能
        self.is_hovered = False
        self.is_pressed = False

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        return self.is_hovered

    def check_click(self, mouse_pos, mouse_pressed):
        # mouse_pressed[0] is Left Click
        if self.rect.collidepoint(mouse_pos):
            self.is_pressed = mouse_pressed[0]
            return self.is_pressed
        self.is_pressed = False
        return False

    def draw(self, surface):
        # 根据状态切换图片
        img = self.image_pressed if self.is_pressed else self.image_normal
        surface.blit(img, self.rect)
        
        # 绘制图标 (居中叠加)
        if self.icon:
            icon_rect = self.icon.get_rect(center=self.rect.center)
            # 如果按下了，图标稍微下沉一点点更有手感 (可选)
            if self.is_pressed:
                icon_rect.y += 2
            surface.blit(self.icon, icon_rect)


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
        try:
            self.font = pygame.font.Font('assets/fonts/pixel.ttf', 24)
        except:
            self.font = pygame.font.Font(None, 30)
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
        # 大字体 (用于标题)
        try:
            self.title_font = pygame.font.Font('assets/fonts/pixel.ttf', 80)
            self.info_font = pygame.font.Font('assets/fonts/pixel.ttf', 40)
        except:
            self.title_font = pygame.font.Font(None, 100)
            self.info_font = pygame.font.Font(None, 50)

    # 绘制暂停和死亡菜单及按钮准备
        # 1. 加载 Banner
        self.banner = self.res.get_image('ribbon_red_3slides') 
        # 2. 加载按钮 (64x64)
        btn_blue = self.res.get_image('button_blue')
        btn_blue_p = self.res.get_image('button_blue_pressed')
        btn_red = self.res.get_image('button_red')
        btn_red_p = self.res.get_image('button_red_pressed')
        # 3. 加载并缩放 Icon (200x200 -> 32x32)
        def load_scale_icon(name):
            img = self.res.get_image(name)
            return pygame.transform.scale(img, (32, 32))
        icon_resume = load_scale_icon('icon_resume') 
        icon_restart = load_scale_icon('icon_restart')
        icon_quit = load_scale_icon('icon_quit')
        # 屏幕中心
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        # 按钮间距
        btn_spacing = 80 
        # 暂停菜单按钮组 (Resume, Restart, Quit)
        self.pause_buttons = [
            # 中间: Resume
            Button(cx, cy + 20, btn_blue, btn_blue_p, icon_resume, 'resume'),
            # 左边: Restart
            Button(cx - btn_spacing, cy + 20, btn_blue, btn_blue_p, icon_restart, 'restart'),
            # 右边: Quit
            Button(cx + btn_spacing, cy + 20, btn_red, btn_red_p, icon_quit, 'quit')
        ]
        # 死亡菜单按钮组 (Restart, Quit)
        self.death_buttons = [
            # 左边: Restart
            Button(cx - 40, cy + 20, btn_blue, btn_blue_p, icon_restart, 'restart'),
            # 右边: Quit
            Button(cx + 40, cy + 20, btn_red, btn_red_p, icon_quit, 'quit')
        ]

    # 1. 战斗 HUD (状态: PLAYING)   
    def draw_bar(self, x, y, current, max_val, target_width=300):
        """
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
        self.draw_bar(20, 20, player.current_hp, player.stats['max_hp'], target_width=300)
    
    def draw_xp_text(self, level, xp):
        # 简单显示等级
        text_surf = self.font.render(f'LV: {level}  XP: {int(xp)}', False, COLORS['white'])
        x = self.display_surface.get_width() - 10
        y = 10
        text_rect = text_surf.get_rect(topright=(x, y))
        self.display_surface.blit(text_surf, text_rect)

    def display(self, player):
        """每帧调用的绘制入口"""
        self.draw_health_bar(player.current_hp, player.stats['max_hp'])
        self.draw_xp_text(player.level, player.xp)

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
    def draw_menu_common(self, title_text, buttons):
        """通用的菜单绘制逻辑"""
        # 1. 遮罩
        self.display_surface.blit(self.mask, (0, 0))
        
        # 2. Banner (位于屏幕中心偏上)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        banner_rect = self.banner.get_rect(center=(cx, cy - 80)) # 向上偏移
        self.display_surface.blit(self.banner, banner_rect)
        
        # 3. 标题文字 (绘制在 Banner 内部)
        # Banner 可用区域 110x44，我们需要把文字缩放或者选小号字体
        # 这里用 info_font (40px) 应该刚好
        title_surf = self.info_font.render(title_text, False, (50, 30, 30)) # 深褐色文字更有纸张感
        # 稍微向上提一点以垂直居中于 Ribbon
        title_rect = title_surf.get_rect(center=(banner_rect.centerx, banner_rect.centery - 5)) 
        self.display_surface.blit(title_surf, title_rect)
        
        # 4. 按钮交互与绘制
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        action = None
        for btn in buttons:
            btn.check_hover(mouse_pos)
            # 仅仅在这里处理显示状态 (按下效果)，实际逻辑在 Game 里处理
            # 或者我们可以简单点，在这里如果检测到松开鼠标就返回 Action
            is_down = btn.check_click(mouse_pos, mouse_pressed)
            btn.draw(self.display_surface)
            
        return action

    def draw_pause(self):
        # 绘制并返回当前被点击的按钮（如果有）
        self.draw_menu_common("PAUSED", self.pause_buttons)

    def draw_game_over(self):
        self.draw_menu_common("YOU DIED", self.death_buttons)
        

    # ====================================================
    # 交互入口 (Game.events 调用)
    # ====================================================
    def get_click_action(self, state):
        """专门处理点击事件，供 Game 类调用"""
        mouse_pos = pygame.mouse.get_pos()
        
        target_buttons = []
        if state == 'PAUSED':
            target_buttons = self.pause_buttons
        elif state == 'GAME_OVER':
            target_buttons = self.death_buttons
            
        for btn in target_buttons:
            if btn.rect.collidepoint(mouse_pos):
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