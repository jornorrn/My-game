import pygame

class AudioManager:
    """管理背景音乐和音效播放"""
    
    def __init__(self, resource_manager):
        self.res = resource_manager
        self.current_bgm = None
        self.failed_played = False  # 标记是否已播放死亡音效
        self.is_muted = False  # 静音状态
        
    def play_bgm(self, bgm_key, loops=-1, volume=0.6):
        """
        播放背景音乐
        :param bgm_key: 音频文件名（不含后缀，如 'bgm_home'）
        :param loops: 循环次数，-1 表示无限循环
        :param volume: 音量 (0.0 到 1.0)，默认 0.6 (60%)
        """
        if self.is_muted:
            return  # 静音时不播放
        
        bgm_path = self.res.get_sound(bgm_key)
        if bgm_path and bgm_path != self.current_bgm:
            # 停止当前音乐
            pygame.mixer.music.stop()
            # 加载新音乐
            try:
                pygame.mixer.music.load(bgm_path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(loops)
                self.current_bgm = bgm_path
                print(f"[AUDIO] Playing BGM: {bgm_key} at volume {volume}")
            except Exception as e:
                print(f"[ERROR] Failed to play BGM {bgm_key}: {e}")
    
    def stop_bgm(self):
        """停止背景音乐"""
        pygame.mixer.music.stop()
        self.current_bgm = None
    
    def play_sfx(self, sfx_key, volume=0.9):
        """
        播放音效
        :param sfx_key: 音频文件名（不含后缀，如 'sfx_failed'）
        :param volume: 音量 (0.0 到 1.0)，默认 0.9 (90%)
        """
        if self.is_muted:
            return  # 静音时不播放
        
        sound = self.res.get_sound(sfx_key)
        if sound:
            try:
                sound.set_volume(volume)
                sound.play()
                print(f"[AUDIO] Playing SFX: {sfx_key} at volume {volume}")
            except Exception as e:
                print(f"[ERROR] Failed to play SFX {sfx_key}: {e}")
    
    def update_music_for_state(self, state):
        """
        根据游戏状态更新背景音乐
        :param state: 游戏状态 ('MENU', 'TUTORIAL', 'PLAYING', 'PAUSED', 'GAME_OVER', 'LEVEL_UP')
        """
        # 如果已经播放了死亡音效，保持静默（除非回到主菜单）
        if self.failed_played and state != 'MENU':
            return
        
        # 如果从游戏结束状态回到主菜单，重置标志
        if state == 'MENU' and self.failed_played:
            self.failed_played = False
        
        if state == 'MENU':
            self.play_bgm('bgm_home', loops=-1)
        elif state == 'TUTORIAL':
            # 新手教程状态不播放背景音乐，保持静默
            pass
        elif state in ['PLAYING', 'PAUSED', 'LEVEL_UP']:
            # 游戏过程（包括游戏进行、暂停、升级选择状态）播放 bgm_main
            self.play_bgm('bgm_main', loops=-1)
        elif state == 'GAME_OVER':
            # 死亡时播放一次 sfx_failed，然后保持静默
            if not self.failed_played:
                self.stop_bgm()
                self.play_sfx('sfx_failed', volume=0.7)
                self.failed_played = True
    
    def toggle_mute(self):
        """切换静音状态"""
        self.is_muted = not self.is_muted
        if self.is_muted:
            # 静音：停止所有音频
            pygame.mixer.music.stop()
            pygame.mixer.stop()  # 停止所有音效
            print("[AUDIO] Muted")
        else:
            # 取消静音：清除 current_bgm 标记，让 update_music_for_state 重新播放
            # 这样可以在下次状态更新时自动恢复正确的音乐
            self.current_bgm = None
            print("[AUDIO] Unmuted")
        return self.is_muted
    
    def reset(self):
        """重置音频管理器状态（用于重新开始游戏）"""
        self.failed_played = False
        self.current_bgm = None
