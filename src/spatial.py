"""
空间分区系统 - 用于优化碰撞检测
将地图划分为网格，只检测同一网格或相邻网格内的碰撞
"""
import pygame
from src.settings import TILE_SIZE

class SpatialGrid:
    """
    网格空间分区系统
    将地图划分为固定大小的网格，用于快速查找附近的精灵
    """
    def __init__(self, cell_size=128):
        """
        :param cell_size: 网格大小（像素），默认 128
        """
        self.cell_size = cell_size
        # 网格字典：{(grid_x, grid_y): [sprite1, sprite2, ...]}
        self.grid = {}
    
    def get_cell(self, pos):
        """
        根据世界坐标获取网格坐标
        :param pos: (x, y) 世界坐标
        :return: (grid_x, grid_y) 网格坐标
        """
        return (int(pos[0] // self.cell_size), int(pos[1] // self.cell_size))
    
    def add_sprite(self, sprite):
        """
        将精灵添加到对应的网格
        :param sprite: 要添加的精灵
        """
        cell = self.get_cell(sprite.rect.center)
        if cell not in self.grid:
            self.grid[cell] = []
        if sprite not in self.grid[cell]:
            self.grid[cell].append(sprite)
    
    def remove_sprite(self, sprite):
        """
        从网格中移除精灵
        :param sprite: 要移除的精灵
        """
        cell = self.get_cell(sprite.rect.center)
        if cell in self.grid and sprite in self.grid[cell]:
            self.grid[cell].remove(sprite)
            # 如果网格为空，删除网格（可选，节省内存）
            if not self.grid[cell]:
                del self.grid[cell]
    
    def update_sprite(self, sprite, old_pos=None):
        """
        更新精灵在网格中的位置
        :param sprite: 要更新的精灵
        :param old_pos: 旧位置（如果提供，会先从旧位置移除）
        """
        if old_pos:
            old_cell = self.get_cell(old_pos)
            if old_cell in self.grid and sprite in self.grid[old_cell]:
                self.grid[old_cell].remove(sprite)
                if not self.grid[old_cell]:
                    del self.grid[old_cell]
        
        # 添加到新位置
        self.add_sprite(sprite)
    
    def get_nearby_sprites(self, pos, radius=None):
        """
        获取指定位置附近的精灵
        :param pos: (x, y) 世界坐标
        :param radius: 搜索半径（像素），如果为 None 则只搜索同一网格
        :return: 附近的精灵列表
        """
        center_cell = self.get_cell(pos)
        nearby = []
        
        if radius is None:
            # 只搜索同一网格
            if center_cell in self.grid:
                nearby.extend(self.grid[center_cell])
        else:
            # 搜索中心网格和相邻网格
            # 计算需要搜索的网格范围
            cells_to_check = int(radius // self.cell_size) + 1
            
            for dx in range(-cells_to_check, cells_to_check + 1):
                for dy in range(-cells_to_check, cells_to_check + 1):
                    cell = (center_cell[0] + dx, center_cell[1] + dy)
                    if cell in self.grid:
                        nearby.extend(self.grid[cell])
        
        return nearby
    
    def clear(self):
        """清空所有网格"""
        self.grid.clear()
