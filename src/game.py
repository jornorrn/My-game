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

        #self.setup_test_map()
        
        self.spawn_timer = 0
        self.base_spawn_interval = 1200

        self.ui = UI(self.screen, self.loader) 
        
        self.state = 'PLAYING' 

    #def setup_test_map(self):
        # 生成 40x40 的大地图
        #map_width = 40
        #map_height = 40
        
        #for x in range(map_width):
            #for y in range(map_height):
                #pos = (x * TILE_SIZE, y * TILE_SIZE)
                # 地板
                #Tile(pos, [self.all_sprites], 'floor')
                # 围墙
                #if x == 0 or x == map_width - 1 or y == 0 or y == map_height - 1:
                #    Tile(pos, [self.all_sprites, self.obstacle_sprites], 'wall')
                # 随机障碍物 
                #elif random.random() < 0.01:
                #    Tile(pos, [self.all_sprites, self.obstacle_sprites], 'wall')

        # 玩家放在地图中心
        #self.player = Player(
        #    pos=(map_width * TILE_SIZE // 2, map_height * TILE_SIZE // 2), 
        #    groups=[self.all_sprites], 
        #    obstacle_sprites=self.obstacle_sprites,
        #    enemy_sprites=self.enemy_sprites,
        #    resource_manager=self.loader
        #)

    def enemy_spawner(self, dt):
        self.spawn_timer += dt * 1000 
        
        # [修改] 动态间隔: 基础1200ms - (等级-1)*50ms，最低200ms
        # 建议后续将 1200 提取为 settings.SPAWN_INTERVAL_BASE
        current_interval = max(200, 1200 - (self.player.level - 1) * 50)
        
        if self.spawn_timer >= current_interval:
            self.spawn_timer = 0
            
            # 筛选符合当前等级(tier <= player.level)的怪物
            available_enemies = []
            for e_id, data in self.loader.data['enemies'].items():
                tier = data.get('tier', 1)
                if tier <= self.player.level:
                    available_enemies.append(e_id)
            
            if not available_enemies: return

            enemy_id = random.choice(available_enemies)
            
            # 随机坐标逻辑 (简单防卡死版)
            for _ in range(10): # 尝试10次
                x = random.randint(2 * TILE_SIZE, 38 * TILE_SIZE)
                y = random.randint(2 * TILE_SIZE, 38 * TILE_SIZE)
                spawn_pos = pygame.math.Vector2(x, y)
                if spawn_pos.distance_to(self.player.rect.center) > 500:
                    Enemy((x, y), enemy_id, [self.all_sprites, self.enemy_sprites], 
                          self.obstacle_sprites, self.player, self.loader)
                    break

    def update(self, dt):
        if self.state == 'PLAYING':
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
        
        # 重新生成地图和玩家
        self.setup_test_map()
        
        # 重置数值
        self.spawn_timer = 0
        self.state = 'PLAYING'
        self.death_timer = 0

    def draw(self):
        self.screen.fill(COLORS['bg_void'])
        self.all_sprites.custom_draw(self.player)
        self.ui.draw_hud(self.player)

        if self.state == 'PAUSED':
            self.ui.draw_pause()
        elif self.state == 'GAME_OVER':
            self.ui.draw_game_over()
        elif self.state == 'LEVEL_UP':
            self.ui.draw_level_up()

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
                    # 传入当前 state，让 UI 判断检测哪组按钮
                    if self.state in ['PAUSED', 'GAME_OVER', 'PLAYING']:
                        action = self.ui.get_click_action(self.state)
                        if action == 'resume': self.state = 'PLAYING'
                        elif action == 'restart': self.reset_game()
                        elif action == 'quit': self.running = False
                        elif action == 'pause_game': self.state = 'PAUSED'

                    elif self.state == 'LEVEL_UP':
                        selected_option = self.ui.get_level_up_choice()
                        if selected_option:
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
