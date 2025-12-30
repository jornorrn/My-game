import sys
# 确保能扫描到 src 目录
sys.path.append('./src')
from src.game import Game

if __name__ == '__main__':
    # 实例化游戏并运行
    game = Game()
    game.run()
