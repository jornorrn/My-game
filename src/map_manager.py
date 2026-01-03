# [src/map_manager.py]
import pygame
import random
from src.settings import *
from src.components import Tile, AnimatedTile

class MapManager:
    def __init__(self, game, map_width=80, map_height=60):
        self.game = game
        self.width = map_width
        self.height = map_height
        
        # 网格数据: 0=空/草地, 1=墙, 2=水, 3=树, 4=装饰
        self.grid = {} 
        self.spawn_point = (0, 0)

    def generate_forest(self):
        """生成森林地图"""
        print("[Map] Generating Forest...")
        self.grid = {}
        
        # 1. 填充基础地面 (虚拟填充，实际只存特殊块)
        # 我们默认所有坐标都是草地，只记录墙、水、树
        
        # 2. 生成边界墙
        for x in range(self.width):
            self.grid[(x, 0)] = 'wall'
            self.grid[(x, self.height - 1)] = 'wall'
        for y in range(self.height):
            self.grid[(0, y)] = 'wall'
            self.grid[(self.width - 1, y)] = 'wall'
            
        # 3. 生成随机水域 (Cellular Automata 简化版: 随机生长)
        num_pools = random.randint(2, 5)
        for _ in range(num_pools):
            self._generate_water_pool()
            
        # 4. 撒树 (障碍物)
        # 避开水和墙
        for _ in range(200): # 尝试种200棵树
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
            if (x, y) not in self.grid:
                self.grid[(x, y)] = 'tree'
                
        # 5. 撒装饰物 (非障碍)
        for _ in range(100):
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
            if (x, y) not in self.grid:
                self.grid[(x, y)] = 'deco'

        # 6. 确定玩家出生点 (寻找一个空地)
        while True:
            cx = random.randint(self.width // 4, self.width * 3 // 4)
            cy = random.randint(self.height // 4, self.height * 3 // 4)
            if (cx, cy) not in self.grid:
                self.spawn_point = (cx * TILE_SIZE, cy * TILE_SIZE)
                break
                
        # 7. 实例化到游戏世界
        self._instantiate_map()

    def _generate_water_pool(self):
        """生成一个不规则水坑"""
        # 随机中心点
        cx = random.randint(5, self.width - 5)
        cy = random.randint(5, self.height - 5)
        pool_size = random.randint(10, 30) # 水块数量
        
        # 简单的随机游走生成连通水域
        current = (cx, cy)
        for _ in range(pool_size):
            if 0 < current[0] < self.width - 1 and 0 < current[1] < self.height - 1:
                self.grid[current] = 'water'
            
            # 向四周随机移动
            direction = random.choice([(0,1), (0,-1), (1,0), (-1,0)])
            current = (current[0] + direction[0], current[1] + direction[1])

    def _instantiate_map(self):
        """将 Grid 数据转为 Sprite"""
        res = self.game.loader
        
        # 获取素材
        img_floor = res.get_image('tile_grass')
        img_wall = res.get_image('tile_wall')
        img_tree = res.get_image('obs_tree')
        img_deco = res.get_image('deco_rock') # 或者是花
        img_water_anim = res.get_image('tile_water_anim') # 序列帧大图
        
        # 1. 铺满草地 (作为底层)
        for x in range(self.width):
            for y in range(self.height):
                pos = (x * TILE_SIZE, y * TILE_SIZE)
                # 创建草地
                Tile(pos, [self.game.all_sprites], 'floor', surface=img_floor)
        
        # 2. 根据 Grid 生成物件
        for coords, type_name in self.grid.items():
            pos = (coords[0] * TILE_SIZE, coords[1] * TILE_SIZE)
            
            if type_name == 'wall':
                Tile(pos, [self.game.all_sprites, self.game.obstacle_sprites], 'wall', surface=img_wall)
                
            elif type_name == 'tree':
                # 树木也是障碍物
                Tile(pos, [self.game.all_sprites, self.game.obstacle_sprites], 'tree', surface=img_tree)
                
            elif type_name == 'deco':
                # 装饰物无碰撞，只渲染
                Tile(pos, [self.game.all_sprites], 'deco', surface=img_deco)
                
            elif type_name == 'water':
                # 水是动态的，且是障碍物(不可行走)
                # 假设 water foam 只有一行，16帧
                frame_data = {'frames': 16, 'speed': 8} 
                AnimatedTile(pos, 
                             [self.game.all_sprites, self.game.obstacle_sprites], 
                             'water', 
                             surface=img_water_anim, 
                             frame_data=frame_data)