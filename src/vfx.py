import pygame
import settings

def slice_frames(sheet, frame_count, frame_w=0, spacing=0, margin=0):
    """
    通用工具：将序列帧大图切割为 Surface 列表
    :param spacing: 帧之间的空隙像素
    :param margin: 第一帧左侧的空隙像素
    """
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
            break
            
        rect = pygame.Rect(x, 0, frame_w, sheet_h)
        try:
            frames.append(sheet.subsurface(rect))
        except ValueError:
            break
            
    # 如果切割失败（比如图片太小切不出来），至少返回原图防止崩溃
    if not frames:
        frames.append(sheet)
        
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
        frame_w = data_dict.get('frame_width', 0) # 为什么默认宽度为0？
         # [新增] 读取间距参数
        spacing = data_dict.get('spacing', 0)
        margin = data_dict.get('margin', 0)
        
        # 2. 切割帧
        self.frames = slice_frames(full_image, frame_count, frame_w)
        
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
            self.frame_index += self.animation_speed * dt
            
            if self.frame_index >= len(self.frames):
                if loop:
                    self.frame_index = 0
                else:
                    self.frame_index = len(self.frames) - 1
                    self.finished = True
        
        return self.frames[int(self.frame_index)]
        
    def get_all_frames(self):
        """获取所有原始帧 (用于像子弹那样需要预先旋转的情况)"""
        return self.frames

class VFXManager:
    def __init__(self, all_sprites_group):
        self.groups = all_sprites_group
        # 预加载特效的序列帧 (从 ResourceManager 获取)

    def trigger(self, vfx_id, pos, target_sprite=None):
        """
        统一入口。
        :param vfx_id: 特效编号 (int)
        :param pos: 发生位置
        :param target_sprite: 如果是受击闪烁，需要传入目标对象
        """
        if vfx_id == settings.VFX_HIT_FLASH:
            self._create_flash(target_sprite)
        elif vfx_id == settings.VFX_DEATH_POOF:
            self._create_explosion(pos)
        # ...

    def _create_flash(self, sprite):
        # 逻辑：生成一个纯白色的 mask surface，覆盖在 sprite 上
        # 持续 0.1秒 后自动销毁
        pass

    def _create_explosion(self, pos):
        # 逻辑：实例化一个播放序列帧的 Sprite，播放完自动 kill()
        pass