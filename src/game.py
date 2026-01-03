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
        # 确保窗口有焦点，防止键盘输入被系统拦截
        # 在 macOS 上，这有助于防止输入法拦截按键
        pygame.display.get_surface().set_alpha(None)  # 确保窗口可见
        # 禁用按键重复，避免按键事件被系统重复处理
        pygame.key.set_repeat(0)  # 0 表示禁用按键重复
        # 禁用文本输入，防止中文输入法拦截键盘事件（特别是 WASD 键）
        # 这对于游戏来说很重要，因为我们不需要文本输入功能
        pygame.key.stop_text_input()
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

            # [优化] 使用对数增长公式，避免后期怪物数量爆炸
            # 公式：基础数量 + log(等级) * 系数，并设置上限
            import math
            base_count = 1
            log_factor = 2.0  # 对数增长系数
            max_per_spawn = MAX_SPAWN_COUNT  # 单次最大生成数量
            
            # 使用对数增长：1级=1, 5级≈2, 10级≈3, 20级≈4, 30级≈5
            spawn_count = min(max_per_spawn, 
                            max(1, base_count + int(math.log(self.player.level) * log_factor)))
            
            # [优化] 检查当前敌人数量，如果已接近上限则减少生成
            current_enemy_count = len(self.enemy_sprites)
            if current_enemy_count >= MAX_ENEMIES * 0.8:  # 达到80%上限时
                spawn_count = max(1, spawn_count // 2)  # 减半生成
            elif current_enemy_count >= MAX_ENEMIES:  # 已达到上限
                return  # 不生成新敌人
            
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
            
            # [优化] 循环生成多个怪物，但限制总数量
            for _ in range(spawn_count):
                # 再次检查敌人数量（防止循环中超过上限）
                if len(self.enemy_sprites) >= MAX_ENEMIES:
                    break
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
        
        # 在游戏状态下，确保文本输入被禁用，防止中文输入法拦截键盘事件
        if self.state == 'PLAYING':
            pygame.key.stop_text_input()
        
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
            
            # 处理文本输入事件，防止中文输入法显示（macOS 上特别重要）
            # 当输入法处于中文状态时，这些事件会被触发，我们需要阻止它们
            if event.type == pygame.TEXTINPUT:
                # 游戏不需要文本输入，直接忽略这些事件
                # 这样可以防止中文输入法在按下 WASD 时显示输入框
                pass
            elif event.type == pygame.TEXTEDITING:
                # 文本编辑事件（输入法候选词等），同样忽略
                pass
            
            if event.type == pygame.KEYDOWN:
                # 明确处理 WASD 键，防止系统输入法拦截（特别是在 macOS 上）
                # 即使这些键通过 pygame.key.get_pressed() 在 player.input() 中处理，
                # 我们也需要在这里捕获 KEYDOWN 事件来阻止系统默认行为
                wasd_keys = (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)
                if event.key in wasd_keys:
                    # 在游戏状态下，这些键用于移动，不应该触发系统输入
                    # 通过明确处理这些事件，我们可以防止 macOS 输入法拦截它们
                    if self.state == 'PLAYING':
                        # 明确处理，阻止默认行为
                        # 注意：实际的移动逻辑在 player.input() 中通过 get_pressed() 处理
                        pass
                elif event.key == pygame.K_ESCAPE:
                    if self.state == 'PLAYING':
                        self.state = 'PAUSED'
                    elif self.state == 'PAUSED':
                        self.state = 'PLAYING'
            
            # 处理窗口焦点事件，确保游戏窗口有焦点时能正确接收键盘输入
            if event.type == pygame.ACTIVEEVENT:
                if event.gain == 1:  # 窗口获得焦点
                    # 窗口获得焦点时，确保禁用文本输入，防止输入法拦截
                    pygame.key.stop_text_input()
            
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
