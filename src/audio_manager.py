import pygame

class AudioManager:
    """管理背景音乐和音效播放"""
    
    def __init__(self, resource_manager):
        self.res = resource_manager
        self.current_bgm = None
        self.failed_played = False  # 标记是否已播放死亡音效
        
    def play_bgm(self, bgm_key, loops=-1):
        """
        播放背景音乐
        :param bgm_key: 音频文件名（不含后缀，如 'bgm_home'）
        :param loops: 循环次数，-1 表示无限循环
        """
        bgm_path = self.res.get_sound(bgm_key)
        if bgm_path and bgm_path != self.current_bgm:
            # 停止当前音乐
            pygame.mixer.music.stop()
            # 加载新音乐
            try:
                pygame.mixer.music.load(bgm_path)
                pygame.mixer.music.play(loops)
                self.current_bgm = bgm_path
                print(f"[AUDIO] Playing BGM: {bgm_key}")
            except Exception as e:
                print(f"[ERROR] Failed to play BGM {bgm_key}: {e}")
    
    def stop_bgm(self):
        """停止背景音乐"""
        pygame.mixer.music.stop()
        self.current_bgm = None
    
    def play_sfx(self, sfx_key, volume=0.5):
        """
        播放音效
        :param sfx_key: 音频文件名（不含后缀，如 'sfx_failed'）
        :param volume: 音量 (0.0 到 1.0)
        """
        sound = self.res.get_sound(sfx_key)
        if sound:
            try:
                sound.set_volume(volume)
                sound.play()
                print(f"[AUDIO] Playing SFX: {sfx_key}")
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
        elif state in ['TUTORIAL', 'PLAYING', 'PAUSED', 'LEVEL_UP']:
            # 游戏过程（包括游戏进行、暂停、新手指引状态）播放 bgm_main
            self.play_bgm('bgm_main', loops=-1)
        elif state == 'GAME_OVER':
            # 死亡时播放一次 sfx_failed，然后保持静默
            if not self.failed_played:
                self.stop_bgm()
                self.play_sfx('sfx_failed', volume=0.7)
                self.failed_played = True
    
    def reset(self):
        """重置音频管理器状态（用于重新开始游戏）"""
        self.failed_played = False
        self.current_bgm = None
