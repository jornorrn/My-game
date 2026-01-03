import pygame
from src.settings import *

def slice_frames(sheet, frame_count, frame_w=0, spacing=0, margin=0):
    """
    通用工具：将序列帧大图切割为 Surface 列表
    :param spacing: 帧之间的空隙像素
    :param margin: 第一帧左侧的空隙像素
    """
    # #region agent log
    import json
    log_data = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "A",
        "location": "vfx.py:slice_frames",
        "message": "Frame slicing start",
        "data": {
            "frame_count": frame_count,
            "frame_w": frame_w,
            "spacing": spacing,
            "margin": margin,
            "sheet_size": sheet.get_size() if sheet else None
        },
        "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
    }
    try:
        with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
    except: pass
    # #endregion
    
    frames = []
    sheet_w, sheet_h = sheet.get_size()
    
    # 1. 自动计算单帧宽度 (如果不含 spacing 的简单情况)
    if frame_w <= 0:
        if frame_count <= 0: frame_count = 1
        # 如果有 spacing，自动计算会很复杂，建议外部传入 frame_w
        available_w = sheet_w - margin - (spacing * (frame_count - 1))
        frame_w = available_w // frame_count
    
    # 2. 切割循环
    for i in range(frame_count):
        # 计算精确坐标
        x = margin + i * (frame_w + spacing)
        
        # [关键修复] 安全检查：如果切片右边缘超出了图片总宽，停止切割
        # 这能防止 ValueError: subsurface rectangle outside surface area
        if x + frame_w > sheet_w:
            print(f"[VFX WARNING] Frame {i} out of bounds. Image W:{sheet_w}, Target X:{x+frame_w}")
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "vfx.py:slice_frames",
                "message": "Frame out of bounds",
                "data": {"frame_index": i, "sheet_w": sheet_w, "target_x": x + frame_w},
                "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
            }
            try:
                with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except: pass
            # #endregion
            break
            
        rect = pygame.Rect(x, 0, frame_w, sheet_h)
        try:
            frames.append(sheet.subsurface(rect))
        except ValueError as e:
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "vfx.py:slice_frames",
                "message": "Subsurface ValueError",
                "data": {"frame_index": i, "error": str(e)},
                "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
            }
            try:
                with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except: pass
            # #endregion
            break
            
    # 如果切割失败（比如图片太小切不出来），至少返回原图防止崩溃
    if not frames:
        frames.append(sheet)
    
    # #region agent log
    log_data = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "A",
        "location": "vfx.py:slice_frames",
        "message": "Frame slicing complete",
        "data": {"expected_frames": frame_count, "actual_frames": len(frames)},
        "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
    }
    try:
        with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
    except: pass
    # #endregion
        
    return frames

class AnimationPlayer:
    """
    通用动画控制器。
    职责：管理动画帧序列、播放速度、当前帧索引。
    """
    def __init__(self, full_image, data_dict, default_speed=10):
        """
        :param full_image: 完整的序列帧大图 (Surface)
        :param data_dict: 包含 'frames'(数量), 'frame_width'(宽) 的字典
        :param default_speed: 默认播放速度
        """
        # 1. 解析配置
        # data_dict 通常是 json 里的 "data" 字段
        frame_count = data_dict.get('frames', 1)
        frame_w = data_dict.get('frame_width', 0) 
         # [新增] 读取间距参数
        spacing = data_dict.get('spacing', 0)
        margin = data_dict.get('margin', 0)
        
        # 2. 切割帧
        self.frames = slice_frames(full_image, frame_count, frame_w, spacing, margin)
        
        # 3. 播放状态
        self.frame_index = 0
        self.animation_speed = default_speed
        self.finished = False # 是否播放完毕 (用于非循环动画)

    def update(self, dt, loop=True):
        """
        更新动画进度
        :param dt: 增量时间
        :param loop: 是否循环播放
        :return: 当前应该显示的 Surface
        """
        if not self.frames:
            return None
            
        # 只有多帧才需要计算
        if len(self.frames) > 1:
            old_index = int(self.frame_index)
            self.frame_index += self.animation_speed * dt
            
            if self.frame_index >= len(self.frames):
                if loop:
                    self.frame_index = 0
                else:
                    self.frame_index = len(self.frames) - 1
                    self.finished = True
            
            new_index = int(self.frame_index)
            # #region agent log
            import json
            if old_index != new_index or self.frame_index >= len(self.frames):
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "vfx.py:update",
                    "message": "Frame index changed",
                    "data": {
                        "old_index": old_index,
                        "new_index": new_index,
                        "frame_index_float": self.frame_index,
                        "total_frames": len(self.frames),
                        "animation_speed": self.animation_speed,
                        "dt": dt,
                        "loop": loop
                    },
                    "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
                }
                try:
                    with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except: pass
            # #endregion
        
        frame_idx = int(self.frame_index)
        if frame_idx >= len(self.frames):
            frame_idx = len(self.frames) - 1
        if frame_idx < 0:
            frame_idx = 0
        return self.frames[frame_idx]
    
    # 获取当前帧+缩放函数
    def get_frame_image(self, dt, loop=True, scale=1.0):
        raw_img = self.update(dt, loop)
        # #region agent log
        import json
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "C",
            "location": "vfx.py:get_frame_image",
            "message": "Getting frame image",
            "data": {
                "dt": dt,
                "loop": loop,
                "scale": scale,
                "frame_index": int(self.frame_index) if hasattr(self, 'frame_index') else -1,
                "total_frames": len(self.frames) if hasattr(self, 'frames') else 0,
                "raw_img_is_none": raw_img is None,
                "raw_img_size": raw_img.get_size() if raw_img else None
            },
            "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
        }
        try:
            with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        except: pass
        # #endregion
        if not raw_img: return None
        
        if scale != 1.0:
            w = int(raw_img.get_width() * scale)
            h = int(raw_img.get_height() * scale)
            scaled_img = pygame.transform.scale(raw_img, (w, h))
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "E",
                "location": "vfx.py:get_frame_image",
                "message": "Scaled image",
                "data": {
                    "original_size": raw_img.get_size(),
                    "scaled_size": scaled_img.get_size(),
                    "scale": scale
                },
                "timestamp": pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
            }
            try:
                with open('/Users/aogo/My-game/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except: pass
            # #endregion
            return scaled_img
        return raw_img
        
    def get_all_frames(self):
        """获取所有原始帧 (用于像子弹那样需要预先旋转的情况)"""
        return self.frames

class FlashEffect(pygame.sprite.Sprite):
    """受击闪白/闪红特效"""
    def __init__(self, target_sprite, groups, duration=0.1):
        super().__init__(groups)
        self.target = target_sprite
        self.z_layer = LAYERS['vfx_top']
        self.duration = duration * 1000
        self.start_time = pygame.time.get_ticks()
        
        # 创建初始 mask 和图像
        self.base_mask = pygame.mask.from_surface(self.target.image)
        mask_surf = self.base_mask.to_surface(setcolor=(255, 255, 255, 200), unsetcolor=(0,0,0,0))
        self.image = mask_surf
        self.last_image_size = self.target.image.get_size()
        
        self.rect = self.target.rect.copy()
        self.hitbox = self.rect.copy() 

    def update(self, dt):
        # 跟随目标
        if self.target.alive():
            self.rect.center = self.target.rect.center
            # 只在目标图像大小变化时更新 mask（适配动画）
            current_size = self.target.image.get_size()
            if current_size != self.last_image_size:
                self.base_mask = pygame.mask.from_surface(self.target.image)
                mask_surf = self.base_mask.to_surface(setcolor=(255, 255, 255, 200), unsetcolor=(0,0,0,0))
                self.image = mask_surf
                self.last_image_size = current_size
            self.hitbox = self.rect.copy() # 同步 hitbox
        else:
            self.kill()

        # 计时销毁
        if pygame.time.get_ticks() - self.start_time > self.duration:
            self.kill()

class Explosion(pygame.sprite.Sprite):
    """死亡/爆炸特效"""
    # 类变量：跟踪当前存在的特效数量
    _active_count = 0
    
    def __init__(self, pos, groups, texture, frame_count=12, scale=1.0):
        super().__init__(groups)
        self.z_layer = LAYERS['vfx_top']
        
        # [优化] 检查特效数量限制
        if Explosion._active_count >= MAX_VFX_COUNT:
            # 如果特效过多，直接销毁，不创建新特效
            self.kill()
            return
        
        # [优化] 明确设置每帧大小为 64x64，确保正确裁切
        # 期望每帧大小为 64x64
        frame_width = 64
        frame_height = 64
        
        # 构造 data_dict 给 AnimationPlayer 用
        anim_data = {
            'frames': frame_count,
            'frame_width': frame_width,  # 明确设置为 64
            'spacing': 0,
            'margin': 0
        }
        
        # 使用 AnimationPlayer 进行帧切割
        self.anim_player = AnimationPlayer(texture, anim_data, default_speed=20)
        
        # [关键修复] 确保每帧都是 64x64 大小
        # slice_frames 使用整个图片高度作为帧高度，所以需要后处理确保每帧都是 64x64
        for i, frame in enumerate(self.anim_player.frames):
            frame_w, frame_h = frame.get_size()
            if frame_w != frame_width or frame_h != frame_height:
                # 如果尺寸不匹配，进行裁切或缩放
                if frame_w >= frame_width and frame_h >= frame_height:
                    # 裁切到中心 64x64 区域（从中心裁切）
                    x_offset = (frame_w - frame_width) // 2
                    y_offset = (frame_h - frame_height) // 2
                    rect = pygame.Rect(x_offset, y_offset, frame_width, frame_height)
                    try:
                        self.anim_player.frames[i] = frame.subsurface(rect)
                    except ValueError:
                        # 如果裁切失败，使用缩放
                        self.anim_player.frames[i] = pygame.transform.scale(frame, (frame_width, frame_height))
                else:
                    # 如果更小，则缩放
                    self.anim_player.frames[i] = pygame.transform.scale(frame, (frame_width, frame_height))
        
        self.scale = scale
        
        # 初始化第一帧
        self.image = self.anim_player.get_frame_image(0, loop=False, scale=self.scale)
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.copy()
        
        # [优化] 增加活跃特效计数
        Explosion._active_count += 1

    def update(self, dt):
        # get_frame_image 内部处理了帧更新
        # loop=False: 播放完会停止在最后一帧 (finished=True)
        img = self.anim_player.get_frame_image(dt, loop=False, scale=self.scale)
        
        if self.anim_player.finished:
            # [优化] 减少活跃特效计数
            Explosion._active_count = max(0, Explosion._active_count - 1)
            self.kill()
        elif img:
            self.image = img
            # 保持中心不动
            self.rect = self.image.get_rect(center=self.rect.center)

