import pygame
from src.settings import *

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

        # 初始化字体
        self.font = pygame.font.Font(None, 30) # 后期可换成 self.res.fonts['pixel']
        
        # 运行时临时数据 (用于存储按钮/卡片的 rect，以便检测点击)
        self.current_ui_rects = [] 
        # TODO: 预加载通用的 UI 素材 (如通用背景框 self.bg_panel = self.res.get_image('ui_panel'))

    # ====================================================
    # 1. 战斗 HUD (状态: PLAYING)
    # ====================================================
    def draw_hud(self, player):
        #我希望用素材来做血条显示。所以不要直接在这里写血条显示硬编码代码！！！
        pass

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
    def draw_pause(self):
        """
        绘制暂停文字和按钮
        """
        # self.current_ui_rects = []
        # 实现逻辑：
        # 1. 绘制遮罩
        # 2. 绘制 "PAUSED" 文字
        # 3. (可选) 绘制 "RESUME" 按钮并记录 Rect
        pass

    # ====================================================
    # 4. 游戏结束 (状态: GAME_OVER)
    # ====================================================
    def draw_game_over(self):
        """
        绘制死亡结算
        """
        # 实现逻辑：
        # 1. 绘制红色/黑色遮罩
        # 2. 绘制 "YOU DIED" 大字
        pass

    # ====================================================
    # 交互入口 (Game.events 调用)
    # ====================================================
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