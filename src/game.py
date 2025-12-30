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
        pygame.display.set_caption("MysticEcho")
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
        self.spawn_timer = 0
        self.spawn_interval = 1000

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
        if self.state == 'PLAYING':
            self.all_sprites.update(dt)
            self.enemy_spawner(dt) # 驱动刷怪笼

    def draw(self):
        self.screen.fill(COLORS['bg_void'])
        
        # 只画场景，不画 UI
        self.all_sprites.custom_draw(self.player)
        
        pygame.display.update()

    def enemy_spawner(self, dt):
        """
        无限怪群生成逻辑
        """
        self.spawn_timer += dt * 1000 # 转毫秒
        
        # 随着等级提高，生成间隔变短 (最快 0.2秒一只)
        current_interval = max(200, self.spawn_interval - (self.player.level * 50))
        
        if self.spawn_timer >= current_interval:
            self.spawn_timer = 0
            
            # 1. 筛选当前等级合法的怪物
            # 需确保 enemies.json 里有 tier 字段，如果没有默认 tier=1
            available_enemies = []
            for e_id, data in self.loader.data['enemies'].items():
                tier = data.get('tier', 1)
                if tier <= self.player.level: # 如果怪物阶级 <= 玩家等级
                    available_enemies.append(e_id)
            
            if not available_enemies: return

            # 2. 随机选择一种
            enemy_id = random.choice(available_enemies)
            
            # 3. 随机位置 (在玩家屏幕外生成)
            # 简单实现：在地图范围内随机，但离玩家有一定距离
            # 更好的实现是：摄像机视野外圈
            while True:
                x = random.randint(2 * TILE_SIZE, 38 * TILE_SIZE)
                y = random.randint(2 * TILE_SIZE, 38 * TILE_SIZE)
                spawn_pos = pygame.math.Vector2(x, y)
                player_pos = pygame.math.Vector2(self.player.rect.center)
                
                # 距离检查：距离玩家至少 600 像素才生成
                if spawn_pos.distance_to(player_pos) > 600:
                    break
            
            Enemy(
                pos=(x, y), 
                enemy_id=enemy_id, 
                groups=[self.all_sprites, self.enemy_sprites], 
                obstacle_sprites=self.obstacle_sprites, 
                player=self.player, 
                resource_manager=self.loader
            )
            #debug
            print(f"[DEBUG] Spawned enemy {enemy_id} at {x},{y}")

