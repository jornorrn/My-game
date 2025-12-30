import pygame
import json
import os
from src.settings import *

class ResourceManager:
    def __init__(self):
        # 统一图片仓库：Key = 文件名(无后缀), Value = Surface
        self.images = {} 
        # 统一音频仓库
        self.sounds = {}
        # 数据仓库
        self.data = {
            'upgrades': {}, # Key = ID (int)
            'enemies': {},
            'weapons': {}
        }
        
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_path = os.path.join(self.base_path, 'assets')

    def load_all(self):
        print(f"--- System: Loading Assets from {self.assets_path} ---")
        
        # 1. 递归加载所有图形资源 (不分文件夹，建立全局索引)
        graphics_path = os.path.join(self.assets_path, 'graphics')
        self._load_graphics_recursive(graphics_path)
        
        # 2. 加载 JSON 配置
        # 必须确保 JSON 中的 "image" 字段的值，在上面的 self.images 中能找到 Key
        self._load_json('upgrades.json', 'upgrades', ID_RANGE_UPGRADE)
        self._load_json('enemies.json', 'enemies', ID_RANGE_ENEMY)
        self._load_json('weapons.json', 'weapons', ID_RANGE_WEAPON)
        
        print("--- System: Asset Loading Complete ---")

    def _load_graphics_recursive(self, folder_path):
        """
        递归扫描文件夹，支持 .png, .jpg, .jpeg
        Key 为文件名（小写，不含后缀）
        """
        supported_ext = ('.png', '.jpg', '.jpeg')
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(supported_ext):
                    # 获取不带后缀的文件名作为 Key
                    file_name_no_ext = os.path.splitext(file)[0].lower()
                    full_path = os.path.join(root, file)
                    
                    try:
                        surf = pygame.image.load(full_path).convert_alpha()
                        
                        # 检查重名冲突 (Warn only)
                        if file_name_no_ext in self.images:
                            print(f"[WARNING] Duplicate filename found: {file_name_no_ext}. Overwriting.")
                        
                        self.images[file_name_no_ext] = surf
                        
                    except Exception as e:
                        print(f"[ERROR] Failed to load image {full_path}: {e}")

    def _load_json(self, filename, target_key, id_range):
        """通用 JSON 加载器"""
        path = os.path.join(self.assets_path, 'json', filename)
        if not os.path.exists(path):
            print(f"[ERROR] JSON file missing: {path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
            
            for item in data_list:
                # 1. ID 校验
                if 'id' not in item: continue
                u_id = int(item['id'])
                if not (id_range[0] <= u_id <= id_range[1]):
                    print(f"[WARNING] ID {u_id} out of range {id_range} in {filename}")
                    continue
                
                # 2. 图片资源预检 (可选，但推荐)
                # 检查 item['image'] 是否在 self.images 里，如果不在，打印警告
                if 'image' in item:
                    img_key = item['image'].lower()
                    if img_key not in self.images:
                        print(f"[WARNING] Asset '{img_key}' referenced in {filename} not found in graphics.")
                
                self.data[target_key][u_id] = item
                
        except Exception as e:
            print(f"[ERROR] JSON parse error in {filename}: {e}")

    def get_image(self, key):
        """安全获取图片，缺失返回洋红色方块"""
        key = str(key).lower()
        if key in self.images:
            return self.images[key]
        else:
            # 缺失素材时的 Fallback：洋红色方块
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 255)) # 纯洋红
            return surf