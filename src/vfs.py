import pygame
import settings

class VFXManager:
    def __init__(self, all_sprites_group):
        self.groups = all_sprites_group
        # 预加载特效的序列帧 (从 ResourceManager 获取)

    def slice_frames(sheet, frame_count, frame_w):
        frames = []
        sheet_w, sheet_h = sheet.get_size()
        # 如果没指定 frame_w，自动计算
        if frame_w <= 0: frame_w = sheet_w // frame_count
        
        for i in range(frame_count):
            # 简单防越界
            if i * frame_w >= sheet_w: break
            rect = pygame.Rect(i * frame_w, 0, frame_w, sheet_h)
            frames.append(sheet.subsurface(rect))
        return frames

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