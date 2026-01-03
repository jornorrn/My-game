# [src/map_manager.py]
import pygame
import random
from src.settings import *
from src.components import Tile, AnimatedTile, Shadow

class MapManager:
    def __init__(self, game, map_width=80, map_height=60):
        self.game = game
        self.width = map_width
        self.height = map_height
        
        # 网格数据: 0=空/草地, 1=墙, 2=水, 3=树, 4=装饰
        self.grid = {} 
        self.spawn_point = (0, 0)

    def _has_obstacle_in_range(self, x, y, grid):
        """检查目标位置周围2x2范围内是否有障碍物"""
        for dx in range(-1, 2):  # -1, 0, 1
            for dy in range(-1, 2):  # -1, 0, 1
                if (x + dx, y + dy) in grid:
                    return True
        return False

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
            
        # 3. 生成随机水域 （已删除，因效果不佳。）
            
        # 4. 撒树 (障碍物)
        # 每个障碍物2x2范围内没有其他障碍物，使生成更均匀
        trees_placed = 0
        max_attempts = 1000  # 防止无限循环
        attempts = 0
        while trees_placed < 100 and attempts < max_attempts:
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
            if (x, y) not in self.grid and not self._has_obstacle_in_range(x, y, self.grid):
                self.grid[(x, y)] = 'tree'
                trees_placed += 1
            attempts += 1
                
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

    def _instantiate_map(self):
        """将 Grid 数据转为 Sprite"""
        res = self.game.loader
        
        # --- 1. 素材准备与切割 ---
        img_floor = res.get_image('tile_grass')
        img_wall = res.get_image('tile_wall')
            
        # 装饰列表 (扫描所有 deco_ 开头的)
        deco_images = []
        for key, surf in res.images.items():
            if key.startswith('deco_'):
                deco_images.append(surf)
                
        if not deco_images: # 兜底
            deco_images.append(pygame.Surface((32, 32))) 
        
        # 阴影
        img_shadow = pygame.transform.scale(res.get_image('shadows'), (24, 12))
        img_shadow.set_alpha(80)

        # 树木(8帧, 宽1536 -> 单帧192) 
        # 缩放到 0.3 -> 57x76 (约占 2x2 格)
        tree_configs = [
            {'key': 'obs_tree1_anim', 'frames': 8, 'frame_width': 192, 'scale': 1.0, 'offset_y': 0},
            {'key': 'obs_tree2_anim', 'frames': 8, 'frame_width': 192, 'scale': 1.0, 'offset_y': 0},
            {'key': 'obs_tree3_anim', 'frames': 8, 'frame_width': 192, 'scale': 1.0, 'offset_y': 0},
            {'key': 'obs_tree4_anim', 'frames': 8, 'frame_width': 192, 'scale': 1.0, 'offset_y': 0}
        ]
        
        # --- 实例化 ---
        
        # 铺地板
        for x in range(self.width - 1):
            for y in range(self.height - 1):
                pos = (x * TILE_SIZE, y * TILE_SIZE)
                Tile(pos, [self.game.all_sprites], 'floor', surface=img_floor)
        
        # 生成物件
        for coords, type_name in self.grid.items():
            # 这里的 pos 是网格坐标
            pos = (coords[0] * TILE_SIZE, coords[1] * TILE_SIZE)
            
            if type_name == 'wall':
                # 墙壁 (带高墙逻辑)
                # 传入 scale_to_width=32，让高墙自动按比例缩放
                Tile(pos, [self.game.all_sprites, self.game.obstacle_sprites], 'wall', 
                     surface=img_wall, scale_to_width=TILE_SIZE)
                
            elif type_name == 'deco':
                # 随机选一个装饰
                img = random.choice(deco_images)
                # 将装饰物缩放到 64x64
                img_scaled = pygame.transform.smoothscale(img, (64, 64))
                # 调整位置使装饰物居中在网格上（装饰物64x64，网格32x32，需要向左上偏移16像素）
                deco_pos = (pos[0] - 16, pos[1] - 16)
                # 创建装饰物 Tile，放在 ground 层
                Tile(deco_pos, [self.game.all_sprites], 'deco', surface=img_scaled)
            
            elif type_name == 'tree':
                # 随机选一种树
                cfg = random.choice(tree_configs)
                raw_surf = res.get_image(cfg['key'])
                frame_data = {
                    'frames': cfg['frames'], 
                    'frame_width': cfg['frame_width'], 
                    'speed': 5
                }
                # 树木通常向上生长，所以 offset_y 设为负数，让根部对齐格子
                offset = (0, cfg.get('offset_y', -30))
                
                AnimatedTile(pos, [self.game.all_sprites, self.game.obstacle_sprites], 'tree',
                             surface=raw_surf, frame_data=frame_data, 
                             visual_scale=cfg['scale'], offset=offset)
                
                # 手动加阴影 (位置可能需要根据树的 scale 微调)
                Shadow(self.game.all_sprites.sprites()[-1], [self.game.all_sprites], img_shadow)
                
        
