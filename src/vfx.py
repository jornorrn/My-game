import pygame
import settings
from src.settings import *

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
        frame_w = data_dict.get('frame_width', 0) 
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
    
    # 获取当前帧+缩放函数
    def get_frame_image(self, dt, loop=True, scale=1.0):
        raw_img = self.update(dt, loop)
        if not raw_img: return None
        
        if scale != 1.0:
            w = int(raw_img.get_width() * scale)
            h = int(raw_img.get_height() * scale)
            return pygame.transform.scale(raw_img, (w, h))
        return raw_img
        
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

class FlashEffect(pygame.sprite.Sprite):
    """受击闪白/闪红特效"""
    def __init__(self, target_sprite, groups, duration=0.1):
        super().__init__(groups)
        self.target = target_sprite
        self.z_layer = LAYERS['vfx_top']
        self.duration = duration * 1000
        self.start_time = pygame.time.get_ticks()
        
        # 复制图像, 创建mask，填充白色
        self.image = pygame.Surface(self.target.image.get_size(), pygame.SRCALPHA)
        mask = pygame.mask.from_surface(self.target.image)
        mask_surf = mask.to_surface(setcolor=(255, 255, 255, 200), unsetcolor=(0,0,0,0))
        self.image = mask_surf
        
        self.rect = self.target.rect.copy()
        self.hitbox = self.rect.copy() 

    def update(self, dt):
        # 跟随目标
        if self.target.alive():
            self.rect.center = self.target.rect.center
            # 实时更新形状（适配动画）
            self.image = pygame.Surface(self.target.image.get_size(), pygame.SRCALPHA)
            mask = pygame.mask.from_surface(self.target.image)
            self.image = mask.to_surface(setcolor=(255, 255, 255, 200), unsetcolor=(0,0,0,0))
            self.hitbox = self.rect.copy() # 同步 hitbox
        else:
            self.kill()

        # 计时销毁
        if pygame.time.get_ticks() - self.start_time > self.duration:
            self.kill()

class Explosion(pygame.sprite.Sprite):
    """死亡/爆炸特效"""
    def __init__(self, pos, groups, texture, frame_count=5, scale=2.0):
        super().__init__(groups)
        self.z_layer = LAYERS['vfx_top']
        self.frames = slice_frames(texture, frame_count)
        
        # [修改] 构造一个临时的 data_dict 给 AnimationPlayer 用
        # 这样我们就不需要手动写 slice_frames 和 update 逻辑了
        anim_data = {
            'frames': frame_count,
            'frame_width': 0, # 0 = 自动计算
            'spacing': 0,
            'margin': 0
        }
        
        # 使用 AnimationPlayer
        self.anim_player = AnimationPlayer(texture, anim_data, default_speed=20)
        self.scale = scale
        
        # 初始化第一帧
        self.image = self.anim_player.get_frame_image(0, loop=False, scale=self.scale)
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.copy()

    def update(self, dt):
        # get_frame_image 内部处理了帧更新
        # loop=False: 播放完会停止在最后一帧 (finished=True)
        img = self.anim_player.get_frame_image(dt, loop=False, scale=self.scale)
        
        if self.anim_player.finished:
            self.kill()
        elif img:
            self.image = img
            # 保持中心不动
            self.rect = self.image.get_rect(center=self.rect.center)

