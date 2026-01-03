# 游戏性能优化方案

本文档列出了所有可以优化游戏性能的方法，按照优先级和影响程度分类。

## 🔴 高优先级优化（立即实施）

### 1. 渲染优化

#### 1.1 视锥剔除（Frustum Culling）
**问题**：当前只有 ground 层做了视锥剔除，其他层（main、vfx_top、vfx_bottom）每帧都绘制所有精灵。

**优化方案**：
- 在 `YSortCameraGroup.custom_draw()` 中，对所有层级的精灵都进行视锥剔除
- 只绘制屏幕可见区域内的精灵（考虑精灵大小，使用更宽松的边界）

**预期提升**：减少 30-50% 的绘制调用

#### 1.2 减少重复遍历
**问题**：`custom_draw()` 方法遍历所有精灵 4 次（ground、vfx_bottom、main、vfx_top）

**优化方案**：
- 只遍历一次，按层级分组，然后分别绘制
- 使用字典缓存按层级分组的精灵列表，只在精灵数量变化时重新分组

**预期提升**：减少 50-75% 的遍历开销

#### 1.3 Y轴排序优化
**问题**：每帧都对所有 main 层精灵进行排序

**优化方案**：
- 使用更高效的排序算法（如 Timsort，Python 内置）
- 只在精灵位置变化时重新排序（使用脏标记）
- 对于远离玩家的精灵，可以降低排序精度

**预期提升**：减少 20-40% 的排序开销

### 2. 碰撞检测优化

#### 2.1 空间分区（Spatial Partitioning）
**问题**：每帧所有子弹都要检测与所有敌人的碰撞（O(n*m) 复杂度）

**优化方案**：
- 实现网格空间分区（Grid-based Spatial Partitioning）
- 将地图划分为网格，只检测同一网格或相邻网格内的碰撞
- 使用 `pygame.sprite.Group` 的 `collide_rect` 配合空间分区

**预期提升**：减少 70-90% 的碰撞检测计算

#### 2.2 碰撞检测频率降低
**问题**：每帧都检测所有碰撞

**优化方案**：
- 对于环绕物（Orbital）和光环（Aura），使用时间间隔控制碰撞检测频率
- 对于远距离的敌人，降低碰撞检测频率（如每 2-3 帧检测一次）

**预期提升**：减少 30-50% 的碰撞检测调用

#### 2.3 使用更高效的碰撞检测
**问题**：使用 `spritecollide` 可能效率不高

**优化方案**：
- 对于子弹，使用距离检测先过滤远距离敌人
- 使用 `collide_circle` 代替 `colliderect`（如果适用）
- 缓存碰撞结果，避免重复计算

**预期提升**：减少 20-30% 的碰撞检测时间

### 3. 动画和特效优化

#### 3.1 动画帧率降低
**问题**：所有动画都以 60 FPS 更新

**优化方案**：
- 对于远离玩家的精灵，降低动画更新频率（如每 2-3 帧更新一次）
- 对于屏幕外的精灵，暂停动画更新

**预期提升**：减少 30-50% 的动画计算

#### 3.2 特效数量限制
**问题**：虽然已有 `MAX_VFX_COUNT`，但可能不够严格

**优化方案**：
- 更严格地限制特效数量
- 使用对象池（Object Pooling）重用特效对象
- 优先销毁远离玩家的特效

**预期提升**：减少 20-40% 的特效相关计算

#### 3.3 FlashEffect 优化
**问题**：每帧都要检查图像大小变化并重新生成 mask

**优化方案**：
- 缓存 mask，只在必要时重新生成
- 使用更轻量的闪烁效果（如简单的颜色叠加）

**预期提升**：减少 50-70% 的 FlashEffect 开销

### 4. 图像处理优化

#### 4.1 减少实时缩放
**问题**：Aura 和 Orbital 每帧都要缩放图像

**优化方案**：
- 预计算不同缩放级别的图像（缓存）
- 只在缩放值变化时重新计算
- 使用整数缩放值，避免浮点计算

**预期提升**：减少 40-60% 的图像处理时间

#### 4.2 图像缓存
**问题**：可能重复加载或处理相同的图像

**优化方案**：
- 确保所有图像只加载一次并缓存
- 预缩放常用图像
- 使用 `pygame.transform.smoothscale` 代替 `scale`（如果质量要求高）

**预期提升**：减少 20-30% 的图像处理开销

## 🟡 中优先级优化（建议实施）

### 5. 敌人 AI 优化

#### 5.1 敌人更新频率降低
**问题**：所有敌人每帧都更新

**优化方案**：
- 对于远离玩家的敌人，降低更新频率（如每 2-3 帧更新一次）
- 对于屏幕外的敌人，暂停 AI 更新（只保留基本移动）

**预期提升**：减少 30-50% 的 AI 计算

#### 5.2 方向计算优化
**问题**：每个敌人每帧都要计算到玩家的方向向量

**优化方案**：
- 缓存方向向量，只在玩家位置变化超过阈值时重新计算
- 使用距离平方比较（避免开方运算）

**预期提升**：减少 20-30% 的向量计算

### 6. 地图优化

#### 6.1 地板绘制优化
**问题**：地图很大（80x60 = 4800 个格子），每帧都要绘制所有地板

**优化方案**：
- 使用更大的地板图块（减少图块数量）
- 只绘制可见区域的地板
- 使用静态 Surface 缓存整个地图（如果内存允许）

**预期提升**：减少 50-70% 的地板绘制调用

#### 6.2 地图图块动画优化
**问题**：所有 AnimatedTile 每帧都更新动画

**优化方案**：
- 对于屏幕外的图块，暂停动画
- 降低动画更新频率

**预期提升**：减少 30-50% 的图块动画计算

### 7. UI 优化

#### 7.1 文字渲染优化
**问题**：主菜单每帧都要重新渲染渐变文字（如果悬停）

**优化方案**：
- 缓存渲染好的文字 Surface
- 只在文字内容或状态变化时重新渲染

**预期提升**：减少 80-90% 的文字渲染开销

#### 7.2 UI 元素更新优化
**问题**：所有 UI 元素每帧都更新

**优化方案**：
- 只在鼠标移动或状态变化时更新相关 UI 元素
- 使用事件驱动更新

**预期提升**：减少 40-60% 的 UI 更新开销

## 🟢 低优先级优化（可选实施）

### 8. 代码结构优化

#### 8.1 减少函数调用开销
**问题**：频繁的函数调用可能带来开销

**优化方案**：
- 内联简单的函数
- 减少不必要的属性访问
- 使用局部变量缓存频繁访问的属性

**预期提升**：减少 5-10% 的 CPU 开销

#### 8.2 内存管理优化
**问题**：频繁创建和销毁对象可能导致内存碎片

**优化方案**：
- 使用对象池重用对象
- 减少临时对象的创建
- 使用 `__slots__` 减少内存占用

**预期提升**：减少内存分配开销，提高稳定性

### 9. 调试代码移除

#### 9.1 移除调试日志
**问题**：代码中有大量调试日志写入文件

**优化方案**：
- 移除或禁用所有调试日志
- 使用条件编译或配置开关

**预期提升**：减少 I/O 开销

### 10. 其他优化

#### 10.1 使用 Pygame 的优化功能
**问题**：可能没有充分利用 Pygame 的优化功能

**优化方案**：
- 使用 `pygame.sprite.Group` 的 `draw()` 方法（如果适用）
- 使用硬件加速（如果可用）
- 使用双缓冲（已在使用）

**预期提升**：轻微提升

#### 10.2 帧率限制
**问题**：如果帧率过高，可能浪费 CPU

**优化方案**：
- 确保 `clock.tick(FPS)` 正确工作
- 考虑动态调整 FPS（根据性能）

**预期提升**：减少不必要的计算

## 📊 实施优先级建议

### 第一阶段（立即实施）：
1. 视锥剔除优化（所有层级）
2. 空间分区碰撞检测
3. 减少重复遍历精灵
4. 动画帧率降低（远离玩家的精灵）

### 第二阶段（短期实施）：
5. 碰撞检测频率降低
6. 图像处理优化（缓存缩放结果）
7. 敌人 AI 更新频率降低
8. UI 文字渲染缓存

### 第三阶段（长期优化）：
9. 对象池实现
10. 代码结构优化
11. 调试代码移除

## 🔧 实施示例

### 示例 1：视锥剔除优化

```python
# 在 YSortCameraGroup.custom_draw() 中
def custom_draw(self, player):
    self.offset.x = player.rect.centerx - self.half_width
    self.offset.y = player.rect.centery - self.half_height
    
    # 计算可见区域（扩大边界以包含部分屏幕外的精灵）
    view_left = -TILE_SIZE * 2
    view_right = WINDOW_WIDTH + TILE_SIZE * 2
    view_top = -TILE_SIZE * 2
    view_bottom = WINDOW_HEIGHT + TILE_SIZE * 2
    
    # 对所有层级都进行视锥剔除
    for sprite in self.sprites():
        offset_pos = sprite.rect.topleft - self.offset
        # 检查是否在可见区域内
        if (view_left < offset_pos.x < view_right and 
            view_top < offset_pos.y < view_bottom):
            # 根据层级绘制
            if sprite.z_layer == LAYERS['ground']:
                self.display_surface.blit(sprite.image, offset_pos)
            # ... 其他层级
```

### 示例 2：空间分区碰撞检测

```python
# 创建空间分区类
class SpatialGrid:
    def __init__(self, cell_size=128):
        self.cell_size = cell_size
        self.grid = {}
    
    def get_cell(self, pos):
        return (int(pos[0] // self.cell_size), int(pos[1] // self.cell_size))
    
    def add_sprite(self, sprite):
        cell = self.get_cell(sprite.rect.center)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(sprite)
    
    def get_nearby_sprites(self, pos, radius):
        # 获取附近网格内的精灵
        center_cell = self.get_cell(pos)
        nearby = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                if cell in self.grid:
                    nearby.extend(self.grid[cell])
        return nearby
```

### 示例 3：动画更新频率降低

```python
# 在 Enemy.update() 中
def update(self, dt):
    # 计算到玩家的距离
    distance = self.rect.center.distance_to(self.player.rect.center)
    
    # 根据距离决定更新频率
    if distance > 800:  # 远离玩家
        self.update_frame_skip = 3  # 每 3 帧更新一次
    elif distance > 400:
        self.update_frame_skip = 2  # 每 2 帧更新一次
    else:
        self.update_frame_skip = 1  # 每帧更新
    
    # 只在需要时更新动画
    if self.frame_count % self.update_frame_skip == 0:
        new_image = self.anim_player.get_frame_image(dt, loop=True, scale=self.scale)
        self.image = new_image
    self.frame_count += 1
```

## 📈 性能监控

建议添加性能监控代码：

```python
import time

class PerformanceMonitor:
    def __init__(self):
        self.frame_times = []
        self.max_samples = 60
    
    def update(self, frame_time):
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_samples:
            self.frame_times.pop(0)
    
    def get_fps(self):
        if not self.frame_times:
            return 0
        avg_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_time if avg_time > 0 else 0
    
    def get_stats(self):
        if not self.frame_times:
            return "N/A"
        avg = sum(self.frame_times) / len(self.frame_times)
        min_time = min(self.frame_times)
        max_time = max(self.frame_times)
        return f"FPS: {1.0/avg:.1f}, Min: {1.0/max_time:.1f}, Max: {1.0/min_time:.1f}"
```

## 🎯 总结

通过实施这些优化，预期可以获得：
- **帧率提升**：从可能的 30-40 FPS 提升到稳定的 60 FPS
- **CPU 使用率降低**：减少 40-60% 的 CPU 使用
- **内存使用优化**：减少内存分配和碎片
- **游戏体验改善**：更流畅的游戏体验，特别是在后期敌人数量多的时候

建议按照优先级逐步实施，每次实施后测试性能，确保优化有效且没有引入新的问题。
