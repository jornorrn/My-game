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
        self.upgrade_manager = UpgradeManager(self.loader)

        self.setup_test_map()
        
        self.spawn_timer = 0
        self.base_spawn_interval = 1200

        self.ui = UI(self.screen, self.loader) 
        
        self.state = 'PLAYING' 

        # [新增] 死亡计时器
        self.death_timer = 0

    def setup_test_map(self):
        # 生成 40x40 的大地图
        map_width = 40
        map_height = 40
        
        for x in range(map_width):
            for y in range(map_height):
                pos = (x * TILE_SIZE, y * TILE_SIZE)
                # 地板
                Tile(pos, [self.all_sprites], 'floor')
                # 围墙
                if x == 0 or x == map_width - 1 or y == 0 or y == map_height - 1:
                    Tile(pos, [self.all_sprites, self.obstacle_sprites], 'wall')
                # 随机障碍物 
                elif random.random() < 0.01:
                    Tile(pos, [self.all_sprites, self.obstacle_sprites], 'wall')

        # 玩家放在地图中心
        self.player = Player(
            pos=(map_width * TILE_SIZE // 2, map_height * TILE_SIZE // 2), 
            groups=[self.all_sprites], 
            obstacle_sprites=self.obstacle_sprites,
            enemy_sprites=self.enemy_sprites,
            resource_manager=self.loader
        )

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

            #死亡检测
            if self.player.is_dead:
                self.state = 'GAME_OVER'
                self.death_timer = 0 # 重置计时

            # 升级检测
            if self.player.check_level_up():
                print(f"--- LEVEL UP! Level: {self.player.level} ---")
                # [强制修改] 为了测试扇形，无视 JSON，直接塞一把 ID 3001 的武器
                print(f">> [DEBUG] Force adding Weapon 3001. Old count: {len(self.player.weapon_controller.equipped_weapons)}")
                self.player.weapon_controller.equipped_weapons.append(3001)
                print(f">> [DEBUG] New count: {len(self.player.weapon_controller.equipped_weapons)}")
                
        elif self.state == 'GAME_OVER':
            # [新增] 死亡倒计时逻辑
            self.death_timer += dt
            if self.death_timer >= 2.0: # 2秒后重启
                print(">> Restarting Game...")
                self.reset_game()

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
        
        pygame.display.update()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()
