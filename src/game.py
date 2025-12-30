import pygame
import sys
import random
from src.settings import *
from src.loader import ResourceManager
from src.player import Player
from src.enemy import Enemy
from src.components import YSortCameraGroup, Tile

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("My Roguelite Game")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # 1. 加载资源
        self.loader = ResourceManager()
        self.loader.load_all()

        # 2. 创建摄像机组
        self.all_sprites = YSortCameraGroup() 
        self.obstacle_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        # 3. 生成地图和玩家
        self.setup_test_map()
        
        # 4. 生成敌人 (使用关键字参数，防止传错)
        self.spawn_enemies(resource_manager=self.loader)

        # 暂时屏蔽 UI，防止报错
        # from src.ui import UI
        # self.ui = UI(self.screen, self.loader) 
        
        self.state = 'PLAYING' 

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

    def spawn_enemies(self, resource_manager):
        # 随机生成 10 个敌人
        for _ in range(10):
            # 在地图范围内随机 (注意不要生成在墙里，这里简单处理先随机)
            x = random.randint(2 * TILE_SIZE, 38 * TILE_SIZE)
            y = random.randint(2 * TILE_SIZE, 38 * TILE_SIZE)
            
            Enemy(
                pos=(x, y), 
                enemy_id=2001, 
                groups=[self.all_sprites, self.enemy_sprites], 
                obstacle_sprites=self.obstacle_sprites, 
                player=self.player, 
                resource_manager=resource_manager
            )

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt):
        self.all_sprites.update(dt)

    def draw(self):
        self.screen.fill(COLORS['bg_void'])
        
        # 只画场景，不画 UI
        self.all_sprites.custom_draw(self.player)
        
        pygame.display.update()
