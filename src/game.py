import pygame
import sys
import random
from src.settings import *
from src.loader import ResourceManager
from src.player import Player
from src.enemy import Enemy
from src.components import YSortCameraGroup, Tile
from src.upgrade_system import UpgradeManager
from src.ui import UI
from src.map_manager import MapManager
from src.audio_manager import AudioManager

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("MysticEcho")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # 加载资源
        self.loader = ResourceManager()
        self.loader.load_all()

        self.all_sprites = YSortCameraGroup() 
        self.obstacle_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        # [新增] 初始化地图管理器
        self.map_manager = MapManager(self)
        self.map_manager.generate_forest() # 生成地图
        # [修改] 使用生成的出生点
        spawn_pos = self.map_manager.spawn_point
        self.player = Player(
            pos=spawn_pos, 
            groups=[self.all_sprites], 
            obstacle_sprites=self.obstacle_sprites,
            enemy_sprites=self.enemy_sprites,
            resource_manager=self.loader
        )
        self.upgrade_manager = UpgradeManager(self.loader)

        self.spawn_timer = 0
        self.base_spawn_interval = 1200

        self.ui = UI(self.screen, self.loader) 
        
        # 初始化音频管理器
        self.audio_manager = AudioManager(self.loader)
        
        # 初始化声音按钮图标状态
        self.ui.update_sound_button_icon(self.audio_manager.is_muted)
        
        self.state = 'MENU'
        # 初始化时播放主菜单音乐
        self.audio_manager.update_music_for_state(self.state)

    def _is_valid_spawn_position(self, x, y, min_distance=400):
        """
        检查生成位置是否有效（不在墙上，不与障碍物碰撞，距离玩家足够远）
        """
        # 1. 距离检查
        spawn_pos = pygame.math.Vector2(x, y)
        if spawn_pos.distance_to(self.player.rect.center) <= min_distance:
            return False
        
        # 2. 严格的边界检查：确保完全在墙内
        # 墙在网格坐标 0 和 width-1, height-1
        # 墙的碰撞箱范围：x 从 0 到 TILE_SIZE（左墙），或 (width-1)*TILE_SIZE 到 width*TILE_SIZE（右墙）
        # 同样适用于 y 轴
        
        map_width_px = self.map_manager.width * TILE_SIZE
        map_height_px = self.map_manager.height * TILE_SIZE
        
        # 确保生成位置至少距离边界墙一个完整的 TILE_SIZE
        # 左边界：x >= TILE_SIZE
        # 右边界：x <= (width - 2) * TILE_SIZE
        # 上边界：y >= TILE_SIZE
        # 下边界：y <= (height - 2) * TILE_SIZE
        if x < TILE_SIZE or x > (self.map_manager.width - 2) * TILE_SIZE:
            return False
        if y < TILE_SIZE or y > (self.map_manager.height - 2) * TILE_SIZE:
            return False
        
        # 3. 网格坐标检查：使用地图网格数据直接验证
        grid_x = x // TILE_SIZE
        grid_y = y // TILE_SIZE
        
        # 检查是否在边界墙的网格坐标上或紧邻边界
        if (grid_x <= 0 or grid_x >= self.map_manager.width - 1 or
            grid_y <= 0 or grid_y >= self.map_manager.height - 1):
            return False
        
        # 3.5 使用地图网格数据检查：如果该网格坐标是墙，直接拒绝
        if (grid_x, grid_y) in self.map_manager.grid:
            if self.map_manager.grid[(grid_x, grid_y)] == 'wall':
                return False
        
        # 4. 检查是否与障碍物碰撞（使用实际碰撞箱）
        # 创建一个临时的碰撞箱来检测（与 Enemy 的 hitbox 创建方式一致）
        # Enemy 的 rect 基于 topleft=pos，然后 inflate(-10, -10)
        test_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        test_hitbox = test_rect.inflate(-10, -10)
        
        # 检查是否与任何障碍物碰撞（包括墙）
        for obstacle in self.obstacle_sprites:
            if test_hitbox.colliderect(obstacle.hitbox):
                return False
        
        return True

    def enemy_spawner(self, dt):
        self.spawn_timer += dt * 1000 
        
        # [修改] 动态间隔: 基础间隔 - (等级-1)*减少量，最低最小间隔
        current_interval = max(SPAWN_INTERVAL_MIN, 
                              SPAWN_INTERVAL_BASE - (self.player.level - 1) * SPAWN_INTERVAL_DECREASE)
        
        if self.spawn_timer >= current_interval:
            self.spawn_timer = 0
            
            # 筛选符合当前等级(tier <= player.level)的怪物
            available_enemies = []
            for e_id, data in self.loader.data['enemies'].items():
                tier = data.get('tier', 1)
                if tier <= self.player.level:
                    available_enemies.append(e_id)
            
            if not available_enemies: return

            # [修改] 根据等级计算生成数量，实现指数级增长
            spawn_count = max(1, int(1.5 ** (self.player.level - 1)))
            
            # 随机坐标逻辑 (严格限制在墙内)
            # 墙在网格坐标 0 和 width-1, height-1
            # 为了确保怪物完全在墙内，生成范围至少距离边界一个 TILE_SIZE
            # 左边界墙：grid_x = 0，像素范围 0 到 TILE_SIZE
            # 右边界墙：grid_x = width-1，像素范围 (width-1)*TILE_SIZE 到 width*TILE_SIZE
            # 所以安全生成范围：TILE_SIZE 到 (width-2)*TILE_SIZE
            
            min_x = TILE_SIZE  # 至少距离左墙一个格子
            max_x = (self.map_manager.width - 2) * TILE_SIZE  # 至少距离右墙一个格子
            min_y = TILE_SIZE  # 至少距离上墙一个格子
            max_y = (self.map_manager.height - 2) * TILE_SIZE  # 至少距离下墙一个格子
            
            # 确保范围有效
            if max_x <= min_x or max_y <= min_y:
                return  # 地图太小，无法生成怪物
            
            # [修改] 循环生成多个怪物
            for _ in range(spawn_count):
                enemy_id = random.choice(available_enemies)
                spawned = False
                
                for attempt in range(20):  # 增加尝试次数
                    x = random.randint(min_x, max_x)
                    y = random.randint(min_y, max_y)
                    
                    # [修改] 使用辅助方法检查生成位置是否有效
                    if self._is_valid_spawn_position(x, y):
                        Enemy((x, y), enemy_id, [self.all_sprites, self.enemy_sprites], 
                              self.obstacle_sprites, self.player, self.loader, self.audio_manager, self.map_manager)
                        spawned = True
                        break
                
                # 如果20次尝试都失败，跳过这个怪物（避免卡死）
                if not spawned:
                    continue

    def update(self, dt):
        # 根据游戏状态更新背景音乐（取消静音后会自动恢复）
        self.audio_manager.update_music_for_state(self.state)
        
        if self.state == 'MENU':
            pass  # 主菜单状态下不更新游戏逻辑
        elif self.state == 'TUTORIAL':
            pass  # 教程状态下不更新游戏逻辑
        elif self.state == 'PLAYING':
            self.all_sprites.update(dt)
            self.enemy_spawner(dt)

            if self.player.is_dead:
                self.state = 'GAME_OVER'

            # 升级逻辑
            if self.player.check_level_up():
                print(f"--- LEVEL UP! Level: {self.player.level} ---")
                
                # 1. 获取随机选项 (UpgradeManager 已保证不重复)
                options = self.upgrade_manager.get_random_options(self.player.level, amount=3)
                if options:
                    # 2. 初始化 UI 卡片
                    self.ui.setup_level_up(options)
                    # 3. 切换状态
                    self.state = 'LEVEL_UP'
                else:
                    print("[WARNING] No upgrades available!")
                    
        elif self.state == 'LEVEL_UP':
            pass

        elif self.state == 'GAME_OVER':
            pass

    def reset_game(self):
        """[新增] 快速重置游戏状态"""
        # 清空所有精灵
        self.all_sprites.empty()
        self.obstacle_sprites.empty()
        self.enemy_sprites.empty()
        
        # 重置音频管理器
        self.audio_manager.reset()
        
        # 重新生成地图和玩家
        self.map_manager.generate_forest()
        spawn_pos = self.map_manager.spawn_point
        self.player = Player(
            pos=spawn_pos, 
            groups=[self.all_sprites], 
            obstacle_sprites=self.obstacle_sprites,
            enemy_sprites=self.enemy_sprites,
            resource_manager=self.loader
        )
        
        # 重置数值
        self.spawn_timer = 0
        self.state = 'PLAYING'

    def draw(self):
        if self.state == 'MENU':
            # 主菜单状态：只绘制主菜单（声音按钮已在 draw_main_menu 中绘制）
            self.ui.draw_main_menu()
        else:
            # 其他状态：绘制游戏内容
            self.screen.fill(COLORS['bg_void'])
            
            # 始终绘制游戏内容（包括教程状态下）
            self.all_sprites.custom_draw(self.player)
            self.ui.draw_hud(self.player)  # draw_hud 中已包含声音按钮
            
            if self.state == 'TUTORIAL':
                # 教程状态下在游戏画面上叠加教程界面
                self.ui.draw_tutorial()
                # 在教程状态下也绘制声音按钮（在教程遮罩之上）
                mouse_pos = pygame.mouse.get_pos()
                self.ui.sound_button.update(mouse_pos)
                self.ui.sound_button.draw(self.ui.display_surface)
            elif self.state == 'PAUSED':
                self.ui.draw_pause()
                # 在暂停菜单下也绘制声音按钮（在菜单之上）
                mouse_pos = pygame.mouse.get_pos()
                self.ui.sound_button.update(mouse_pos)
                self.ui.sound_button.draw(self.ui.display_surface)
            elif self.state == 'GAME_OVER':
                self.ui.draw_game_over()
                # 在死亡菜单下也绘制声音按钮（在菜单之上）
                mouse_pos = pygame.mouse.get_pos()
                self.ui.sound_button.update(mouse_pos)
                self.ui.sound_button.draw(self.ui.display_surface)
            elif self.state == 'LEVEL_UP':
                self.ui.draw_level_up()
                # 在升级选择界面下也绘制声音按钮（在菜单之上）
                mouse_pos = pygame.mouse.get_pos()
                self.ui.sound_button.update(mouse_pos)
                self.ui.sound_button.draw(self.ui.display_surface)

        self.ui.draw_custom_cursor()
        pygame.display.update()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == 'PLAYING':
                        self.state = 'PAUSED'
                    elif self.state == 'PAUSED':
                        self.state = 'PLAYING'
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # 主菜单点击处理
                    if self.state == 'MENU':
                        action = self.ui.get_main_menu_click(mouse_pos)
                        if action == 'start':
                            # 停止主页 BGM，避免与开始游戏音效重叠
                            self.audio_manager.stop_bgm()
                            self.audio_manager.play_sfx('sfx_startgame', volume=0.7)
                            self.state = 'TUTORIAL'
                        elif action == 'quit':
                            self.running = False
                        elif action == 'toggle_sound':
                            is_muted = self.audio_manager.toggle_mute()
                            self.ui.update_sound_button_icon(is_muted)
                            # 如果取消静音，立即更新音乐状态以恢复播放
                            if not is_muted:
                                self.audio_manager.update_music_for_state(self.state)
                    # 新手引导教程：点击图片外区域关闭
                    elif self.state == 'TUTORIAL':
                        # 检查是否点击了声音按钮
                        if self.ui.sound_button.check_click(mouse_pos, pygame.mouse.get_pressed()):
                            is_muted = self.audio_manager.toggle_mute()
                            self.ui.update_sound_button_icon(is_muted)
                            # 如果取消静音，立即更新音乐状态以恢复播放
                            if not is_muted:
                                self.audio_manager.update_music_for_state(self.state)
                        elif self.ui.check_tutorial_click(mouse_pos):
                            self.state = 'PLAYING'
                    # 传入当前 state，让 UI 判断检测哪组按钮
                    elif self.state in ['PAUSED', 'GAME_OVER', 'PLAYING']:
                        action = self.ui.get_click_action(self.state)
                        if action:
                            # 播放按钮点击音效（如果未静音）
                            self.audio_manager.play_sfx('sfx_pressbutton', volume=0.5)
                        if action == 'resume': self.state = 'PLAYING'
                        elif action == 'restart': self.reset_game()
                        elif action == 'quit': self.running = False
                        elif action == 'home': self.state = 'MENU'
                        elif action == 'pause_game': self.state = 'PAUSED'
                        elif action == 'toggle_sound':
                            is_muted = self.audio_manager.toggle_mute()
                            self.ui.update_sound_button_icon(is_muted)
                            # 如果取消静音，立即更新音乐状态以恢复播放
                            if not is_muted:
                                self.audio_manager.update_music_for_state(self.state)

                    elif self.state == 'LEVEL_UP':
                        # 检查是否点击了声音按钮
                        if self.ui.sound_button.check_click(mouse_pos, pygame.mouse.get_pressed()):
                            is_muted = self.audio_manager.toggle_mute()
                            self.ui.update_sound_button_icon(is_muted)
                            # 如果取消静音，立即更新音乐状态以恢复播放
                            if not is_muted:
                                self.audio_manager.update_music_for_state(self.state)
                        else:
                            selected_option = self.ui.get_level_up_choice()
                            if selected_option:
                                # 播放按钮点击音效
                                self.audio_manager.play_sfx('sfx_pressbutton', volume=0.5)
                                # 1. 应用效果
                                print(f">> Selected Upgrade: {selected_option.title}")
                                selected_option.apply(self.player)
                                
                                # 2. 刷新玩家射击状态 (防止卡住开火)
                                # 简单的做法是重置按键状态标记，或者什么都不做
                                # 因为 input() 是每帧检测的，只要状态回到 PLAYING，
                                # 这里暂时只需恢复状态
                                self.state = 'PLAYING'

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()
