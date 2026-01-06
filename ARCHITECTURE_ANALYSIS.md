# 项目文件详细分析

## 1. settings.py - 配置模块

### 功能
全局配置常量定义，包含窗口设置、颜色、渲染层级、ID区间、性能参数等。

### 函数列表
无函数，仅常量定义。

### 调用接口（依赖）
- `pygame`: 仅导入，未实际调用

### 实现接口（对外提供）
- **常量导出**:
  - `WINDOW_WIDTH`, `WINDOW_HEIGHT`, `FPS`, `TILE_SIZE`
  - `COLORS`: 颜色字典
  - `LAYERS`: 渲染层级字典
  - `ID_RANGE_VFX`, `ID_RANGE_UPGRADE`, `ID_RANGE_ENEMY`, `ID_RANGE_WEAPON`
  - `SPAWN_INTERVAL_BASE`, `SPAWN_INTERVAL_DECREASE`, `SPAWN_INTERVAL_MIN`
  - `MAX_ENEMIES`, `MAX_SPAWN_COUNT`, `MAX_VFX_COUNT`
  - `DEBUG`, `DEBUG_WEAPON`

---

## 2. loader.py - 资源管理模块

### 功能
统一资源加载和管理系统，负责加载图片、音频、JSON配置数据，提供统一的资源访问接口。

### 类定义
- `ResourceManager`: 资源管理器

### 函数列表

#### ResourceManager.__init__(self)
- **功能**: 初始化资源管理器，创建资源仓库
- **调用接口**: 无
- **实现接口**: 无

#### ResourceManager.load_all(self)
- **功能**: 加载所有资源（图片、音频、JSON）
- **调用接口**: 
  - `self._load_graphics_recursive()`
  - `self._load_audio()`
  - `self._load_json()`
- **实现接口**: 供 `Game.__init__()` 调用

#### ResourceManager._load_graphics_recursive(self, folder_path)
- **功能**: 递归加载图形资源（支持 .png, .jpg, .jpeg, .svg）
- **调用接口**:
  - `pygame.image.load()`: 加载图片
  - `self._load_svg()`: 加载SVG文件
  - `os.walk()`: 遍历目录
- **实现接口**: 内部方法

#### ResourceManager._load_svg(self, svg_path)
- **功能**: 加载SVG文件（尝试pygame直接加载，失败则使用cairosvg）
- **调用接口**:
  - `pygame.image.load()`: 尝试直接加载
  - `cairosvg.svg2png()`: SVG转PNG（如果可用）
  - `pygame.image.load(io.BytesIO())`: 从字节流加载
- **实现接口**: 内部方法

#### ResourceManager._load_json(self, filename, target_key, id_range)
- **功能**: 加载JSON配置文件并验证ID范围
- **调用接口**:
  - `json.load()`: 解析JSON
  - `os.path.join()`: 构建路径
  - `os.path.exists()`: 检查文件存在
- **实现接口**: 内部方法

#### ResourceManager._load_audio(self)
- **功能**: 加载音频资源（BGM和SFX）
- **调用接口**:
  - `pygame.mixer.init()`: 初始化音频系统
  - `pygame.mixer.Sound()`: 加载音效
  - `os.listdir()`: 列出目录文件
- **实现接口**: 内部方法

#### ResourceManager.get_image(self, key)
- **功能**: 安全获取图片，缺失时返回占位符
- **调用接口**:
  - `pygame.Surface()`: 创建占位符
- **实现接口**: 
  - 供所有需要图片的模块调用（Player, Enemy, UI, MapManager, Weapon等）

#### ResourceManager.get_sound(self, key)
- **功能**: 安全获取音频资源
- **调用接口**: 无
- **实现接口**: 
  - 供 `AudioManager` 调用

### 数据属性
- `self.images`: 图片字典 {key: Surface}
- `self.sounds`: 音频字典 {key: Sound/路径}
- `self.data`: 数据字典 {'upgrades': {}, 'enemies': {}, 'weapons': {}}

---

## 3. components.py - 基础组件模块

### 功能
定义游戏中的基础精灵类和组件系统，包括实体、图块、阴影、相机组等。

### 类定义
- `GameSprite`: 基础精灵类
- `Entity`: 实体基类（可移动）
- `Shadow`: 阴影组件
- `Tile`: 地图图块
- `AnimatedTile`: 动画图块
- `YSortCameraGroup`: Y轴排序相机组

### 函数列表

#### GameSprite.__init__(self, groups, pos, z_layer)
- **功能**: 初始化基础精灵
- **调用接口**: `pygame.sprite.Sprite.__init__()`
- **实现接口**: 基类，供其他类继承

#### Entity.__init__(self, groups, pos, z_layer)
- **功能**: 初始化实体（继承GameSprite）
- **调用接口**: `super().__init__()`
- **实现接口**: 基类，供Player和Enemy继承

#### Entity.set_obstacles(self, obstacle_sprites)
- **功能**: 设置障碍物精灵组
- **调用接口**: 无
- **实现接口**: 供Player/Enemy初始化时调用

#### Entity.move(self, dt)
- **功能**: 处理移动和碰撞检测（分离轴算法）
- **调用接口**:
  - `pygame.sprite.spritecollide()`: 碰撞检测
  - `self.direction.normalize()`: 向量归一化
- **实现接口**: 供Player/Enemy的update()调用

#### Entity.collision(self, direction)
- **功能**: 处理与障碍物的碰撞响应
- **调用接口**:
  - `pygame.sprite.spritecollide()`: 碰撞检测
- **实现接口**: 内部方法，由move()调用

#### Shadow.__init__(self, target_sprite, groups, shadow_surf)
- **功能**: 创建阴影精灵，跟随目标
- **调用接口**: `pygame.sprite.Sprite.__init__()`
- **实现接口**: 供Player/Enemy/Tile创建阴影时调用

#### Shadow._update_pos(self)
- **功能**: 更新阴影位置（跟随目标底部）
- **调用接口**: 无
- **实现接口**: 内部方法

#### Shadow.update(self, dt)
- **功能**: 更新阴影位置，目标死亡时自动销毁
- **调用接口**: `self.target.alive()`
- **实现接口**: 由精灵组自动调用

#### Tile.__init__(self, pos, groups, sprite_type, surface, scale_to_width=None)
- **功能**: 创建地图图块（墙壁、地板、装饰物）
- **调用接口**:
  - `super().__init__()`
  - `pygame.transform.smoothscale()`: 缩放图片
- **实现接口**: 供MapManager调用

#### AnimatedTile.__init__(self, pos, groups, sprite_type, surface, frame_data, visual_scale=1.0, offset=(0,0))
- **功能**: 创建动画图块（如树木）
- **调用接口**:
  - `super().__init__()`
  - `AnimationPlayer()`: 动画播放器
- **实现接口**: 供MapManager调用

#### AnimatedTile.update(self, dt)
- **功能**: 更新动画帧
- **调用接口**:
  - `self.anim_player.get_frame_image()`: 获取动画帧
- **实现接口**: 由精灵组自动调用

#### YSortCameraGroup.__init__(self)
- **功能**: 初始化相机组
- **调用接口**:
  - `pygame.sprite.Group.__init__()`
  - `pygame.display.get_surface()`: 获取显示表面
- **实现接口**: 供Game初始化时调用

#### YSortCameraGroup._is_visible(self, offset_pos, sprite)
- **功能**: 视锥剔除，检查精灵是否在可见区域
- **调用接口**:
  - `pygame.Rect.colliderect()`: 矩形相交检测
- **实现接口**: 内部方法

#### YSortCameraGroup.custom_draw(self, player)
- **功能**: 自定义绘制（相机跟随、Y排序、分层渲染）
- **调用接口**:
  - `pygame.Surface.blit()`: 绘制精灵
  - `sprite.rect.topleft`: 获取精灵位置
- **实现接口**: 供Game.draw()调用

---

## 4. vfx.py - 特效模块

### 功能
提供视觉特效系统，包括动画播放器、受击闪白、爆炸特效等。

### 函数列表

#### slice_frames(sheet, frame_count, frame_w=0, spacing=0, margin=0)
- **功能**: 通用工具，将序列帧大图切割为Surface列表
- **调用接口**:
  - `pygame.Surface.subsurface()`: 切割图片
- **实现接口**: 供AnimationPlayer调用

#### AnimationPlayer.__init__(self, full_image, data_dict, default_speed=10)
- **功能**: 初始化动画播放器
- **调用接口**:
  - `slice_frames()`: 切割帧
- **实现接口**: 供Enemy、Weapon、AnimatedTile等调用

#### AnimationPlayer.update(self, dt, loop=True)
- **功能**: 更新动画进度
- **调用接口**: 无
- **实现接口**: 内部方法

#### AnimationPlayer.get_frame_image(self, dt, loop=True, scale=1.0)
- **功能**: 获取当前帧图像（支持缩放和缓存）
- **调用接口**:
  - `self.update()`: 更新动画
  - `pygame.transform.scale()`: 缩放图片
- **实现接口**: 供Enemy、Weapon、AnimatedTile等调用

#### AnimationPlayer.get_all_frames(self)
- **功能**: 获取所有原始帧（用于预旋转等场景）
- **调用接口**: 无
- **实现接口**: 供Projectile调用

#### FlashEffect.__init__(self, target_sprite, groups, duration=0.1)
- **功能**: 创建受击闪白特效
- **调用接口**:
  - `pygame.sprite.Sprite.__init__()`
  - `pygame.mask.from_surface()`: 创建遮罩
  - `mask.to_surface()`: 遮罩转Surface
- **实现接口**: 供Player.take_damage()和Enemy.take_damage()调用

#### FlashEffect.update(self, dt)
- **功能**: 更新特效（跟随目标，计时销毁）
- **调用接口**:
  - `self.target.alive()`: 检查目标存活
  - `pygame.time.get_ticks()`: 获取时间
- **实现接口**: 由精灵组自动调用

#### Explosion.__init__(self, pos, groups, texture, frame_count=12, scale=1.0)
- **功能**: 创建爆炸特效
- **调用接口**:
  - `pygame.sprite.Sprite.__init__()`
  - `AnimationPlayer()`: 动画播放器
  - `pygame.transform.scale()`: 缩放帧
- **实现接口**: 供Enemy.die()调用

#### Explosion.update(self, dt)
- **功能**: 更新爆炸动画，播放完毕后销毁
- **调用接口**:
  - `self.anim_player.get_frame_image()`: 获取动画帧
  - `self.anim_player.finished`: 检查是否完成
- **实现接口**: 由精灵组自动调用

---

## 5. spatial.py - 空间优化模块

### 功能
空间分区系统，用于优化碰撞检测（当前未在项目中使用）。

### 类定义
- `SpatialGrid`: 网格空间分区系统

### 函数列表

#### SpatialGrid.__init__(self, cell_size=128)
- **功能**: 初始化空间网格
- **调用接口**: 无
- **实现接口**: 供外部初始化时调用

#### SpatialGrid.get_cell(self, pos)
- **功能**: 根据世界坐标获取网格坐标
- **调用接口**: 无
- **实现接口**: 内部方法

#### SpatialGrid.add_sprite(self, sprite)
- **功能**: 将精灵添加到对应网格
- **调用接口**: 无
- **实现接口**: 供外部调用（当前未使用）

#### SpatialGrid.remove_sprite(self, sprite)
- **功能**: 从网格中移除精灵
- **调用接口**: 无
- **实现接口**: 供外部调用（当前未使用）

#### SpatialGrid.update_sprite(self, sprite, old_pos=None)
- **功能**: 更新精灵在网格中的位置
- **调用接口**:
  - `self.get_cell()`: 获取网格坐标
  - `self.add_sprite()`: 添加精灵
- **实现接口**: 供外部调用（当前未使用）

#### SpatialGrid.get_nearby_sprites(self, pos, radius=None)
- **功能**: 获取指定位置附近的精灵
- **调用接口**:
  - `self.get_cell()`: 获取网格坐标
- **实现接口**: 供外部调用（当前未使用）

#### SpatialGrid.clear(self)
- **功能**: 清空所有网格
- **调用接口**: 无
- **实现接口**: 供外部调用（当前未使用）

---

## 6. player.py - 玩家模块

### 功能
玩家实体实现，包括输入处理、动画、移动、升级系统、武器控制等。

### 类定义
- `FloatingWeapon`: 悬浮武器装饰
- `Player`: 玩家类（继承Entity）

### 函数列表

#### FloatingWeapon.__init__(self, groups, image, player, angle_offset, distance=50)
- **功能**: 创建悬浮武器装饰
- **调用接口**:
  - `pygame.sprite.Sprite.__init__()`
- **实现接口**: 供Player.update_floating_weapons()调用

#### FloatingWeapon.update(self, dt)
- **功能**: 更新悬浮武器位置（环绕动画）
- **调用接口**:
  - `pygame.time.get_ticks()`: 获取时间
  - `math.sin()`, `math.cos()`: 三角函数
- **实现接口**: 由精灵组自动调用

#### Player.__init__(self, pos, groups, obstacle_sprites, enemy_sprites, resource_manager)
- **功能**: 初始化玩家
- **调用接口**:
  - `super().__init__()`: 调用Entity初始化
  - `self.import_assets()`: 加载动画资源
  - `Shadow()`: 创建阴影
  - `WeaponController()`: 创建武器控制器
- **实现接口**: 供Game初始化时调用

#### Player.import_assets(self)
- **功能**: 切割Sprite Sheet为动画帧
- **调用接口**:
  - `self.res.get_image()`: 获取图片
  - `pygame.Surface.subsurface()`: 切割图片
  - `pygame.transform.scale()`: 缩放图片
- **实现接口**: 内部方法

#### Player.input(self)
- **功能**: 处理键盘输入（WASD移动）
- **调用接口**:
  - `pygame.key.get_pressed()`: 获取按键状态
- **实现接口**: 由Player.update()调用

#### Player.animate(self, dt)
- **功能**: 播放动画（根据移动状态和朝向）
- **调用接口**: 无
- **实现接口**: 由Player.update()调用

#### Player.get_mouse_direction(self)
- **功能**: 根据鼠标位置计算玩家朝向
- **调用接口**:
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `math.atan2()`, `math.degrees()`: 角度计算
- **实现接口**: 由Player.update()调用

#### Player.calculate_xp_required(self, level)
- **功能**: 根据等级计算所需经验值（分段公式）
- **调用接口**: 无
- **实现接口**: 内部方法

#### Player.check_level_up(self)
- **功能**: 检查是否升级，升级后返回True
- **调用接口**:
  - `self.calculate_xp_required()`: 计算经验需求
- **实现接口**: 供Game.update()调用

#### Player.take_damage(self, amount)
- **功能**: 处理受击逻辑（无敌帧、生命值减少、死亡判定）
- **调用接口**:
  - `pygame.time.get_ticks()`: 获取时间
  - `FlashEffect()`: 创建受击特效
- **实现接口**: 供Enemy碰撞时调用

#### Player.update(self, dt)
- **功能**: 每帧更新玩家状态
- **调用接口**:
  - `self.input()`: 处理输入
  - `self.get_mouse_direction()`: 更新朝向
  - `self.animate()`: 播放动画
  - `self.move()`: 移动（继承自Entity）
  - `self.weapon_controller.update()`: 更新武器
  - `self.update_floating_weapons()`: 更新悬浮武器
- **实现接口**: 由Game.update()通过all_sprites.update()调用

#### Player.update_floating_weapons(self)
- **功能**: 检查武器列表变化，更新悬浮武器显示
- **调用接口**:
  - `self.res.get_image()`: 获取武器图标
  - `pygame.transform.scale()`: 缩放图标
  - `FloatingWeapon()`: 创建悬浮武器
- **实现接口**: 由Player.update()调用

---

## 7. enemy.py - 敌人模块

### 功能
敌人实体实现，包括AI追踪、动画、碰撞伤害、死亡处理等。

### 类定义
- `Enemy`: 敌人类（继承Entity）

### 函数列表

#### Enemy.__init__(self, pos, enemy_id, groups, obstacle_sprites, player, resource_manager, audio_manager=None, map_manager=None)
- **功能**: 初始化敌人
- **调用接口**:
  - `super().__init__()`: 调用Entity初始化
  - `self.res.get_image()`: 获取敌人图片
  - `AnimationPlayer()`: 创建动画播放器
  - `Shadow()`: 创建阴影
- **实现接口**: 供Game.enemy_spawner()调用

#### Enemy._check_out_of_bounds(self)
- **功能**: 检查敌人是否在墙外（安全机制）
- **调用接口**:
  - `self.map_manager.width`, `self.map_manager.height`: 地图尺寸
  - `self.map_manager.grid`: 地图网格数据
- **实现接口**: 内部方法

#### Enemy.update(self, dt)
- **功能**: 每帧更新敌人状态（AI追踪、动画、移动、碰撞伤害）
- **调用接口**:
  - `self._check_out_of_bounds()`: 边界检查
  - `pygame.math.Vector2()`: 向量计算
  - `self.anim_player.get_frame_image()`: 获取动画帧
  - `pygame.transform.flip()`: 翻转图像
  - `self.move()`: 移动（继承自Entity）
  - `self.player.take_damage()`: 对玩家造成伤害
- **实现接口**: 由Game.update()通过all_sprites.update()调用

#### Enemy.take_damage(self, amount)
- **功能**: 处理敌人受击逻辑
- **调用接口**:
  - `random.random()`: 随机数（控制特效生成频率）
  - `FlashEffect()`: 创建受击特效
- **实现接口**: 供Projectile/Orbital/Aura碰撞时调用

#### Enemy.die(self, give_xp=True)
- **功能**: 处理敌人死亡逻辑
- **调用接口**:
  - `self.player.xp`: 增加玩家经验
  - `self.audio_manager.play_sfx()`: 播放死亡音效
  - `Explosion()`: 创建爆炸特效
  - `self.kill()`: 销毁精灵
- **实现接口**: 由Enemy.take_damage()调用

---

## 8. weapon.py - 武器模块

### 功能
武器系统实现，包括投射物、环绕物、光环、武器控制器等。

### 类定义
- `Projectile`: 投射物类
- `Orbital`: 环绕物类
- `Aura`: 光环类
- `WeaponController`: 武器控制器

### 函数列表

#### Projectile.__init__(self, pos, direction, weapon_data, groups, enemy_sprites, obstacle_sprites, angle_offset=0)
- **功能**: 创建投射物
- **调用接口**:
  - `super().__init__()`: 调用GameSprite初始化
  - `math.atan2()`, `math.degrees()`, `math.radians()`: 角度计算
  - `AnimationPlayer()`: 创建动画播放器
  - `pygame.transform.rotate()`: 旋转图片
  - `pygame.transform.scale()`: 缩放图片
- **实现接口**: 供WeaponController.fire()调用

#### Projectile.update(self, dt)
- **功能**: 更新投射物（移动、动画、碰撞检测、射程检测）
- **调用接口**:
  - `pygame.sprite.spritecollide()`: 碰撞检测
  - `enemy.take_damage()`: 对敌人造成伤害
- **实现接口**: 由精灵组自动调用

#### Orbital.__init__(self, player, groups, enemy_sprites, weapon_data, start_angle)
- **功能**: 创建环绕物
- **调用接口**:
  - `super().__init__()`: 调用GameSprite初始化
  - `AnimationPlayer()`: 创建动画播放器
- **实现接口**: 供WeaponController._respawn_orbitals()调用

#### Orbital.update(self, dt)
- **功能**: 更新环绕物（旋转、动画、伤害判定）
- **调用接口**:
  - `math.cos()`, `math.sin()`: 三角函数
  - `pygame.time.get_ticks()`: 获取时间
  - `pygame.sprite.spritecollide()`: 碰撞检测
  - `enemy.take_damage()`: 对敌人造成伤害
- **实现接口**: 由精灵组自动调用

#### Aura.__init__(self, player, groups, enemy_sprites, weapon_data)
- **功能**: 创建光环
- **调用接口**:
  - `super().__init__()`: 调用GameSprite初始化
  - `AnimationPlayer()`: 创建动画播放器
  - `pygame.Surface()`, `pygame.draw.circle()`: 绘制占位符
- **实现接口**: 供WeaponController._respawn_auras()调用

#### Aura._draw_placeholder_image(self)
- **功能**: 绘制占位符图像（当没有素材时）
- **调用接口**:
  - `pygame.Surface()`, `pygame.draw.circle()`: 绘制圆形
- **实现接口**: 内部方法

#### Aura.update(self, dt)
- **功能**: 更新光环（跟随玩家、动画、伤害判定）
- **调用接口**:
  - `self.anim_player.get_frame_image()`: 获取动画帧
  - `pygame.time.get_ticks()`: 获取时间
  - `pygame.sprite.spritecollide()`: 碰撞检测
  - `enemy.take_damage()`: 对敌人造成伤害
- **实现接口**: 由精灵组自动调用

#### WeaponController.__init__(self, player, groups, enemy_sprites, obstacle_sprites, resource_manager)
- **功能**: 初始化武器控制器
- **调用接口**: 无
- **实现接口**: 供Player初始化时调用

#### WeaponController.update(self)
- **功能**: 更新武器系统（冷却、发射、环绕物/光环管理）
- **调用接口**:
  - `pygame.time.get_ticks()`: 获取时间
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `self.fire()`: 发射武器
  - `self._respawn_orbitals()`: 重新生成环绕物
  - `self._respawn_auras()`: 重新生成光环
- **实现接口**: 由Player.update()调用

#### WeaponController._respawn_orbitals(self, orbital_ids)
- **功能**: 清空并重新生成所有环绕物
- **调用接口**:
  - `self.res.get_image()`: 获取武器图片
  - `Orbital()`: 创建环绕物
- **实现接口**: 内部方法

#### WeaponController._respawn_auras(self, aura_ids)
- **功能**: 重新生成所有光环
- **调用接口**:
  - `self.res.get_image()`: 获取武器图片
  - `Aura()`: 创建光环
- **实现接口**: 内部方法

#### WeaponController.add_weapon(self, weapon_id)
- **功能**: 添加武器并标记变化
- **调用接口**: 无
- **实现接口**: 供UpgradeOption.apply()调用

#### WeaponController.fire(self, w_data, direction, angle_offset)
- **功能**: 发射投射物
- **调用接口**:
  - `self.res.get_image()`: 获取武器图片
  - `Projectile()`: 创建投射物
- **实现接口**: 由WeaponController.update()调用

---

## 9. map_manager.py - 地图模块

### 功能
地图生成和管理系统，负责生成随机地图、实例化图块、计算出生点。

### 类定义
- `MapManager`: 地图管理器

### 函数列表

#### MapManager.__init__(self, game, map_width=120, map_height=80)
- **功能**: 初始化地图管理器
- **调用接口**: 无
- **实现接口**: 供Game初始化时调用

#### MapManager._has_obstacle_in_range(self, x, y, grid)
- **功能**: 检查目标位置周围2x2范围内是否有障碍物
- **调用接口**: 无
- **实现接口**: 内部方法

#### MapManager.generate_forest(self)
- **功能**: 生成森林地图（边界墙、树木、装饰物、出生点）
- **调用接口**:
  - `random.randint()`: 随机数生成
  - `self._has_obstacle_in_range()`: 检查障碍物
  - `self._instantiate_map()`: 实例化地图
- **实现接口**: 供Game初始化或重置时调用

#### MapManager._instantiate_map(self)
- **功能**: 将Grid数据转为Sprite（地板、墙壁、装饰、树木）
- **调用接口**:
  - `self.game.loader.get_image()`: 获取图片资源
  - `Tile()`: 创建图块
  - `AnimatedTile()`: 创建动画图块
  - `Shadow()`: 创建阴影
- **实现接口**: 由generate_forest()调用

---

## 10. upgrade_system.py - 升级系统模块

### 功能
升级选项系统，管理升级数据库和升级效果应用。

### 类定义
- `UpgradeOption`: 升级选项基类
- `StatUpgrade`: 数值升级
- `WeaponAddUpgrade`: 武器添加升级
- `WeaponBuffUpgrade`: 武器强化升级
- `HealUpgrade`: 回血升级
- `SpecialUpgrade`: 特殊能力升级
- `UpgradeManager`: 升级管理器

### 函数列表

#### UpgradeOption.__init__(self, data)
- **功能**: 初始化升级选项基类
- **调用接口**: 无
- **实现接口**: 基类，供子类继承

#### UpgradeOption.apply(self, player)
- **功能**: 虚函数，应用升级效果（由子类实现）
- **调用接口**: 无
- **实现接口**: 供UI选择升级时调用

#### StatUpgrade.__init__(self, data)
- **功能**: 初始化数值升级
- **调用接口**: `super().__init__()`
- **实现接口**: 供UpgradeManager构建数据库时调用

#### StatUpgrade.apply(self, player)
- **功能**: 应用数值升级（修改player.stats）
- **调用接口**: 无
- **实现接口**: 由UpgradeOption.apply()调用

#### WeaponAddUpgrade.__init__(self, data)
- **功能**: 初始化武器添加升级
- **调用接口**: `super().__init__()`
- **实现接口**: 供UpgradeManager构建数据库时调用

#### WeaponAddUpgrade.apply(self, player)
- **功能**: 添加新武器
- **调用接口**:
  - `player.weapon_controller.add_weapon()`: 添加武器
- **实现接口**: 由UpgradeOption.apply()调用

#### WeaponBuffUpgrade.__init__(self, data)
- **功能**: 初始化武器强化升级
- **调用接口**: `super().__init__()`
- **实现接口**: 供UpgradeManager构建数据库时调用

#### WeaponBuffUpgrade.apply(self, player)
- **功能**: 强化现有武器（修改武器数据）
- **调用接口**:
  - `player.weapon_controller.res.data['weapons']`: 访问武器数据库
- **实现接口**: 由UpgradeOption.apply()调用

#### HealUpgrade.__init__(self, data)
- **功能**: 初始化回血升级
- **调用接口**: `super().__init__()`
- **实现接口**: 供UpgradeManager构建数据库时调用

#### HealUpgrade.apply(self, player)
- **功能**: 恢复玩家生命值
- **调用接口**: 无
- **实现接口**: 由UpgradeOption.apply()调用

#### SpecialUpgrade.__init__(self, data)
- **功能**: 初始化特殊能力升级
- **调用接口**: `super().__init__()`
- **实现接口**: 供UpgradeManager构建数据库时调用

#### SpecialUpgrade.apply(self, player)
- **功能**: 设置特殊能力（使用setattr）
- **调用接口**:
  - `setattr()`: 设置属性
- **实现接口**: 由UpgradeOption.apply()调用

#### UpgradeManager.__init__(self, resource_manager)
- **功能**: 初始化升级管理器
- **调用接口**:
  - `self._build_db()`: 构建数据库
- **实现接口**: 供Game初始化时调用

#### UpgradeManager._build_db(self)
- **功能**: 根据JSON构建升级对象池
- **调用接口**:
  - `self.res.data.get()`: 获取升级数据
  - 各种UpgradeOption子类构造函数
- **实现接口**: 内部方法

#### UpgradeManager.get_random_options(self, level, amount=3)
- **功能**: 抽取不重复的升级选项（根据等级过滤）
- **调用接口**:
  - `random.sample()`: 随机抽样
- **实现接口**: 供Game.update()调用（升级时）

---

## 11. audio_manager.py - 音频模块

### 功能
音频管理系统，负责背景音乐和音效的播放、状态管理、静音控制。

### 类定义
- `AudioManager`: 音频管理器

### 函数列表

#### AudioManager.__init__(self, resource_manager)
- **功能**: 初始化音频管理器
- **调用接口**: 无
- **实现接口**: 供Game初始化时调用

#### AudioManager.play_bgm(self, bgm_key, loops=-1, volume=0.6)
- **功能**: 播放背景音乐
- **调用接口**:
  - `self.res.get_sound()`: 获取音频路径
  - `pygame.mixer.music.load()`: 加载音乐
  - `pygame.mixer.music.set_volume()`: 设置音量
  - `pygame.mixer.music.play()`: 播放音乐
  - `pygame.mixer.music.stop()`: 停止音乐
- **实现接口**: 供Game和update_music_for_state()调用

#### AudioManager.stop_bgm(self)
- **功能**: 停止背景音乐
- **调用接口**:
  - `pygame.mixer.music.stop()`: 停止音乐
- **实现接口**: 供Game和update_music_for_state()调用

#### AudioManager.play_sfx(self, sfx_key, volume=0.9)
- **功能**: 播放音效
- **调用接口**:
  - `self.res.get_sound()`: 获取音效对象
  - `sound.set_volume()`: 设置音量
  - `sound.play()`: 播放音效
- **实现接口**: 供Game、Enemy、UI等调用

#### AudioManager.update_music_for_state(self, state)
- **功能**: 根据游戏状态更新背景音乐
- **调用接口**:
  - `self.play_bgm()`: 播放音乐
  - `self.stop_bgm()`: 停止音乐
  - `self.play_sfx()`: 播放音效
- **实现接口**: 供Game.update()调用

#### AudioManager.toggle_mute(self)
- **功能**: 切换静音状态
- **调用接口**:
  - `pygame.mixer.music.stop()`: 停止音乐
  - `pygame.mixer.stop()`: 停止所有音效
- **实现接口**: 供UI点击声音按钮时调用

#### AudioManager.reset(self)
- **功能**: 重置音频管理器状态（用于重新开始游戏）
- **调用接口**: 无
- **实现接口**: 供Game.cleanup_game()和Game.reset_game()调用

---

## 12. ui.py - UI模块

### 功能
用户界面系统，负责HUD绘制、菜单系统、交互元素、光标管理等。

### 类定义
- `UIElement`: UI交互元素基类
- `Button`: 按钮类
- `UpgradeCard`: 升级选项卡片
- `UI`: UI管理器

### 函数列表

#### UIElement.__init__(self, center_pos, surface_normal, surface_hover=None, scale_on_hover=True)
- **功能**: 初始化UI元素
- **调用接口**: 无
- **实现接口**: 基类，供Button和UpgradeCard继承

#### UIElement.update(self, mouse_pos)
- **功能**: 更新悬停状态和缩放动画
- **调用接口**:
  - `pygame.Rect.collidepoint()`: 碰撞检测
- **实现接口**: 由UI.draw_xxx()调用

#### UIElement.draw(self, surface)
- **功能**: 绘制UI元素
- **调用接口**:
  - `pygame.transform.scale()`: 缩放图片
  - `pygame.Surface.blit()`: 绘制图片
- **实现接口**: 由UI.draw_xxx()调用

#### UIElement.check_click(self, mouse_pos, mouse_pressed)
- **功能**: 检查是否被点击
- **调用接口**: 无
- **实现接口**: 供UI.get_click_action()调用

#### Button.__init__(self, center_pos, bg_normal, bg_pressed, icon=None, action_name=None)
- **功能**: 初始化按钮（合成背景和图标）
- **调用接口**:
  - `super().__init__()`: 调用基类
  - `pygame.Surface.blit()`: 合成图片
- **实现接口**: 供UI._init_buttons()调用

#### Button.update_icon(self, icon)
- **功能**: 更新按钮图标
- **调用接口**:
  - `pygame.Surface.blit()`: 合成图片
- **实现接口**: 供UI.update_sound_button_icon()调用

#### UpgradeCard.__init__(self, center_pos, size, bg_image, option_data, font_title, font_desc)
- **功能**: 初始化升级卡片
- **调用接口**:
  - `super().__init__()`: 调用基类
  - `pygame.transform.scale()`: 缩放背景
  - `font.render()`: 渲染文字
  - `pygame.Surface.blit()`: 绘制内容
- **实现接口**: 供UI.setup_level_up()调用

#### UpgradeCard.draw_icon(self, icon_surf)
- **功能**: 绘制图标到卡片上
- **调用接口**:
  - `pygame.transform.scale()`: 缩放图标
  - `pygame.Surface.blit()`: 绘制图标
- **实现接口**: 供UI.setup_level_up()调用

#### UI.__init__(self, display_surface, resource_manager)
- **功能**: 初始化UI管理器
- **调用接口**:
  - `pygame.font.Font()`: 加载字体
  - `self.res.get_image()`: 获取UI资源
  - `pygame.mouse.set_visible()`: 隐藏系统光标
  - `self._init_buttons()`: 初始化按钮
- **实现接口**: 供Game初始化时调用

#### UI._init_buttons(self)
- **功能**: 组装所有按钮
- **调用接口**:
  - `self.res.get_image()`: 获取按钮资源
  - `pygame.transform.scale()`: 缩放图标
  - `Button()`: 创建按钮
- **实现接口**: 内部方法

#### UI.update_sound_button_icon(self, is_muted)
- **功能**: 更新声音按钮图标
- **调用接口**:
  - `self.sound_button.update_icon()`: 更新图标
- **实现接口**: 供Game调用

#### UI.draw_custom_cursor(self)
- **功能**: 绘制自定义光标
- **调用接口**:
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `pygame.Surface.blit()`: 绘制光标
- **实现接口**: 由Game.draw()调用

#### UI.draw_bar(self, x, y, current, max_val, target_width=300)
- **功能**: 绘制血条
- **调用接口**:
  - `pygame.transform.scale()`: 缩放中间部分
  - `pygame.Surface.blit()`: 绘制血条
  - `font.render()`: 渲染文字
- **实现接口**: 供UI.draw_hud()调用

#### UI.draw_hud(self, player)
- **功能**: 绘制战斗HUD（血条、等级、按钮）
- **调用接口**:
  - `self.draw_bar()`: 绘制血条
  - `font.render()`: 渲染等级文字
  - `button.update()`: 更新按钮
  - `button.draw()`: 绘制按钮
- **实现接口**: 供Game.draw()调用

#### UI.draw_xp_text(self, level, xp)
- **功能**: 绘制经验值文字（当前未使用）
- **调用接口**:
  - `font.render()`: 渲染文字
  - `pygame.Surface.blit()`: 绘制文字
- **实现接口**: 预留接口

#### UI.setup_level_up(self, options)
- **功能**: 设置升级选择界面（创建3个卡片）
- **调用接口**:
  - `self.res.get_image()`: 获取卡片背景和图标
  - `UpgradeCard()`: 创建卡片
  - `pygame.transform.scale()`: 缩放图标
  - `font.render()`: 渲染文字
- **实现接口**: 供Game.update()调用（升级时）

#### UI.draw_level_up(self)
- **功能**: 绘制升级选择界面
- **调用接口**:
  - `pygame.Surface.blit()`: 绘制遮罩、Banner、卡片
  - `font.render()`: 渲染文字
  - `card.update()`: 更新卡片
  - `card.draw()`: 绘制卡片
- **实现接口**: 供Game.draw()调用

#### UI.get_level_up_choice(self)
- **功能**: 检测升级界面点击，返回选中的升级选项
- **调用接口**:
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `pygame.mouse.get_pressed()`: 获取鼠标按键
  - `card.check_click()`: 检查点击
- **实现接口**: 供Game.events()调用

#### UI._draw_menu_base(self, banner_img, title_text, buttons)
- **功能**: 通用菜单绘制（暂停、死亡菜单共用）
- **调用接口**:
  - `pygame.Surface.blit()`: 绘制遮罩、Banner
  - `font.render()`: 渲染标题
  - `button.update()`: 更新按钮
  - `button.draw()`: 绘制按钮
- **实现接口**: 内部方法

#### UI.draw_pause(self)
- **功能**: 绘制暂停菜单
- **调用接口**:
  - `self._draw_menu_base()`: 绘制基础菜单
- **实现接口**: 供Game.draw()调用

#### UI.draw_game_over(self)
- **功能**: 绘制死亡菜单
- **调用接口**:
  - `self._draw_menu_base()`: 绘制基础菜单
- **实现接口**: 供Game.draw()调用

#### UI.get_click_action(self, state)
- **功能**: 处理点击事件，返回动作名称
- **调用接口**:
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `pygame.mouse.get_pressed()`: 获取鼠标按键
  - `button.check_click()`: 检查按钮点击
- **实现接口**: 供Game.events()调用

#### UI.draw_tutorial(self)
- **功能**: 绘制新手引导教程
- **调用接口**:
  - `pygame.Surface.blit()`: 绘制遮罩和教程图片
- **实现接口**: 供Game.draw()调用

#### UI.check_tutorial_click(self, mouse_pos)
- **功能**: 检测教程点击（点击图片外关闭）
- **调用接口**:
  - `pygame.Rect.collidepoint()`: 碰撞检测
- **实现接口**: 供Game.events()调用

#### UI._render_text_with_outline(self, font, text, text_color, outline_color, outline_width=2)
- **功能**: 渲染带描边的文字
- **调用接口**:
  - `font.render()`: 渲染文字
  - `pygame.Surface.blit()`: 绘制描边和主文字
- **实现接口**: 供UI.draw_main_menu()调用

#### UI._create_gradient_surface(self, width, height)
- **功能**: 创建渐变Surface
- **调用接口**:
  - `pygame.Surface()`: 创建Surface
  - `pygame.draw.line()`: 绘制渐变线
- **实现接口**: 内部方法

#### UI._render_text_with_gradient(self, font, text, outline_color, outline_width=2)
- **功能**: 渲染带描边和渐变色的文字（悬停时使用）
- **调用接口**:
  - `font.render()`: 渲染文字
  - `self._create_gradient_surface()`: 创建渐变
  - `pygame.Surface.get_at()`, `pygame.Surface.set_at()`: 像素操作
  - `pygame.Surface.blit()`: 绘制文字
- **实现接口**: 供UI.draw_main_menu()调用

#### UI.draw_main_menu(self)
- **功能**: 绘制主菜单
- **调用接口**:
  - `pygame.Surface.blit()`: 绘制背景、标题、选项
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `pygame.Rect.collidepoint()`: 碰撞检测
  - `pygame.transform.scale()`: 缩放选项
  - `self._render_text_with_outline()`: 渲染文字
  - `self._render_text_with_gradient()`: 渲染渐变文字
  - `self.sound_button.update()`: 更新声音按钮
  - `self.sound_button.draw()`: 绘制声音按钮
- **实现接口**: 供Game.draw()调用

#### UI.get_main_menu_click(self, mouse_pos)
- **功能**: 检测主菜单点击位置
- **调用接口**:
  - `pygame.mouse.get_pressed()`: 获取鼠标按键
  - `pygame.Rect.collidepoint()`: 碰撞检测
  - `self.sound_button.check_click()`: 检查声音按钮
- **实现接口**: 供Game.events()调用

---

## 13. game.py - 游戏主控制器

### 功能
游戏核心控制器，管理游戏循环、状态机、子系统协调、事件处理等。

### 类定义
- `Game`: 游戏主类

### 函数列表

#### Game.__init__(self)
- **功能**: 初始化游戏（pygame、资源、地图、玩家、UI、音频等）
- **调用接口**:
  - `pygame.init()`: 初始化pygame
  - `pygame.display.set_mode()`: 创建窗口
  - `pygame.key.set_repeat()`: 禁用按键重复
  - `pygame.key.stop_text_input()`: 禁用文本输入
  - `ResourceManager()`: 创建资源管理器
  - `MapManager()`: 创建地图管理器
  - `Player()`: 创建玩家
  - `UpgradeManager()`: 创建升级管理器
  - `UI()`: 创建UI管理器
  - `AudioManager()`: 创建音频管理器
- **实现接口**: 供main.py调用

#### Game._is_valid_spawn_position(self, x, y, min_distance=400)
- **功能**: 检查敌人生成位置是否有效
- **调用接口**:
  - `pygame.math.Vector2()`: 向量计算
  - `self.map_manager.width`, `self.map_manager.height`: 地图尺寸
  - `self.map_manager.grid`: 地图网格
  - `pygame.Rect.inflate()`: 创建碰撞箱
  - `pygame.Rect.colliderect()`: 碰撞检测
- **实现接口**: 内部方法

#### Game.enemy_spawner(self, dt)
- **功能**: 敌人生成逻辑（定时生成、等级过滤、数量控制）
- **调用接口**:
  - `math.log()`: 对数计算
  - `random.choice()`: 随机选择
  - `random.randint()`: 随机整数
  - `self._is_valid_spawn_position()`: 检查生成位置
  - `Enemy()`: 创建敌人
- **实现接口**: 由Game.update()调用

#### Game.update(self, dt)
- **功能**: 更新游戏逻辑（根据状态）
- **调用接口**:
  - `self.audio_manager.update_music_for_state()`: 更新音乐
  - `pygame.key.stop_text_input()`: 禁用文本输入
  - `self.all_sprites.update()`: 更新所有精灵
  - `self.enemy_spawner()`: 生成敌人
  - `self.player.check_level_up()`: 检查升级
  - `self.upgrade_manager.get_random_options()`: 获取升级选项
  - `self.ui.setup_level_up()`: 设置升级界面
- **实现接口**: 由Game.run()调用

#### Game.cleanup_game(self)
- **功能**: 清理游戏资源（地图、玩家、敌人等）
- **调用接口**:
  - `self.all_sprites.empty()`: 清空精灵组
  - `self.audio_manager.reset()`: 重置音频
- **实现接口**: 供Game.start_new_game()和Game.events()调用

#### Game.start_new_game(self)
- **功能**: 开始新游戏（清理资源并重新生成）
- **调用接口**:
  - `self.cleanup_game()`: 清理资源
  - `self.map_manager.generate_forest()`: 生成地图
  - `Player()`: 创建玩家
- **实现接口**: 供Game.events()调用（主菜单点击开始）

#### Game.reset_game(self)
- **功能**: 快速重置游戏状态（用于游戏中的重新开始）
- **调用接口**:
  - `self.cleanup_game()`: 清理资源
  - `self.map_manager.generate_forest()`: 生成地图
  - `Player()`: 创建玩家
- **实现接口**: 供Game.events()调用（暂停/死亡菜单点击重新开始）

#### Game.draw(self)
- **功能**: 绘制游戏画面（根据状态）
- **调用接口**:
  - `self.ui.draw_main_menu()`: 绘制主菜单
  - `self.screen.fill()`: 填充背景
  - `self.all_sprites.custom_draw()`: 绘制游戏内容
  - `self.ui.draw_hud()`: 绘制HUD
  - `self.ui.draw_tutorial()`: 绘制教程
  - `self.ui.draw_pause()`: 绘制暂停菜单
  - `self.ui.draw_game_over()`: 绘制死亡菜单
  - `self.ui.draw_level_up()`: 绘制升级界面
  - `self.ui.draw_custom_cursor()`: 绘制光标
  - `pygame.display.update()`: 更新显示
- **实现接口**: 由Game.run()调用

#### Game.events(self)
- **功能**: 处理所有pygame事件
- **调用接口**:
  - `pygame.event.get()`: 获取事件
  - `pygame.mouse.get_pos()`: 获取鼠标位置
  - `pygame.mouse.get_pressed()`: 获取鼠标按键
  - `self.ui.get_main_menu_click()`: 主菜单点击检测
  - `self.ui.get_click_action()`: 通用点击检测
  - `self.ui.get_level_up_choice()`: 升级选择检测
  - `self.ui.check_tutorial_click()`: 教程点击检测
  - `self.audio_manager.toggle_mute()`: 切换静音
  - `self.audio_manager.play_sfx()`: 播放音效
  - `self.audio_manager.stop_bgm()`: 停止音乐
  - `self.start_new_game()`: 开始新游戏
  - `self.reset_game()`: 重置游戏
  - `self.cleanup_game()`: 清理游戏
  - `selected_option.apply()`: 应用升级
- **实现接口**: 由Game.run()调用

#### Game.run(self)
- **功能**: 游戏主循环
- **调用接口**:
  - `pygame.time.Clock.tick()`: 控制帧率
  - `self.events()`: 处理事件
  - `self.update()`: 更新逻辑
  - `self.draw()`: 绘制画面
  - `pygame.quit()`: 退出pygame
- **实现接口**: 供main.py调用

---

## 14. main.py - 入口文件

### 功能
程序入口，初始化游戏并启动主循环。

### 函数列表
无函数定义。

### 调用接口（依赖）
- `sys.path.append()`: 添加路径
- `Game()`: 创建游戏实例
- `game.run()`: 启动游戏循环

### 实现接口（对外提供）
- 程序入口点（`if __name__ == '__main__'`）

---

## 总结

### 模块依赖关系
1. **基础层**: settings.py（配置）→ loader.py（资源）
2. **组件层**: components.py（基础组件）→ vfx.py（特效）
3. **实体层**: player.py, enemy.py（依赖components和weapon）
4. **系统层**: weapon.py, map_manager.py, upgrade_system.py, audio_manager.py, ui.py
5. **控制层**: game.py（协调所有系统）
6. **入口层**: main.py

### 关键接口模式
- **资源访问**: 统一通过ResourceManager.get_image()和get_sound()
- **实体更新**: 通过精灵组的update()方法统一调用
- **事件处理**: 集中在Game.events()中，根据状态分发
- **状态驱动**: Game.state控制游戏流程，各系统响应状态变化
