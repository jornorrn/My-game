import random

class UpgradeOption:
    """
    升级选项的基类。
    所有具体的升级效果（加数值、给武器）都通过继承或实例化此类来实现。
    """
    def __init__(self, u_id, title, description, icon_key, tag):
        self.id = u_id
        self.title = title
        self.description = description
        self.icon_key = icon_key  # 对应 ResourceManager 中的键
        self.tag = tag            # 标签：'stat' 或 'weapon' 或 'special'

    def apply(self, player):
        """虚函数，由子类实现具体效果"""
        raise NotImplementedError

class StatUpgrade(UpgradeOption):
    """数值类升级：如增加血量上限、增加移动速度"""
    def __init__(self, u_id, title, desc, icon, attribute, value, mode='add'):
        super().__init__(u_id, title, desc, icon, 'stat')
        self.attribute = attribute # 例如 'speed'
        self.value = value         # 例如 50 或 1.1
        self.mode = mode           # 'add' (加法) 或 'mult' (乘法)

    def apply(self, player):
        # 获取当前玩家属性
        current = getattr(player, self.attribute, 0)
        
        if self.mode == 'add':
            setattr(player, self.attribute, current + self.value)
        elif self.mode == 'mult':
            setattr(player, self.attribute, current * self.value)
        
        print(f"Applied Stat Upgrade: {self.attribute} changed to {getattr(player, self.attribute)}")

class WeaponUpgrade(UpgradeOption):
    """武器类升级：获得新武器 或 强化现有武器"""
    def __init__(self, u_id, title, desc, icon, weapon_id):
        super().__init__(u_id, title, desc, icon, 'weapon')
        self.weapon_id = weapon_id

    def apply(self, player):
        player.weapon_controller.add_or_upgrade_weapon(self.weapon_id)

# =========================================
# 升级库定义 (Database)
# =========================================
# 这里实例化所有可能的升级卡片
UPGRADE_DATABASE = [
    
]

class UpgradeManager:
    """负责管理随机抽取、卡池过滤"""
    def __init__(self):
        self.available_upgrades = list(UPGRADE_DATABASE) # 浅拷贝
    
    def get_random_options(self, amount=3):
        # TODO: 从 available_upgrades 中随机抽取 amount 个
        # 抽取时需要判断条件（例如：玩家已经有这个武器了吗？如果升满级了就不应该再出现）
        # 返回 UpgradeOption 对象列表
        return random.sample(self.available_upgrades, min(amount, len(self.available_upgrades)))
    