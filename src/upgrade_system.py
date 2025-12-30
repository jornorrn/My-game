# --- src/upgrade_system.py ---
import random

class UpgradeOption:
    """升级选项基类"""
    def __init__(self, data):
        self.id = data['id']
        self.title = data['title']
        self.description = data['desc']
        self.icon_key = data['image']
        self.type = data['type'] # 'stat', 'weapon', 'special'
        self.tier = data.get('tier', 1)

    def apply(self, player):
        raise NotImplementedError

class StatUpgrade(UpgradeOption):
    """数值升级"""
    def __init__(self, data):
        super().__init__(data)
        # 解析 data 字段: { "attr": "speed", "value": 1.1, "mode": "mult" }
        self.effect_data = data['data']

    def apply(self, player):
        attr = self.effect_data['attr']
        val = self.effect_data['value']
        mode = self.effect_data['mode']
        
        if hasattr(player, 'stats') and attr in player.stats:
            old_val = player.stats[attr]
            if mode == 'add':
                player.stats[attr] += val
            elif mode == 'mult':
                player.stats[attr] *= val
            print(f"[UPGRADE] {attr} changed from {old_val} to {player.stats[attr]}")
        else:
            print(f"[WARNING] Player has no stat: {attr}")

class WeaponUpgrade(UpgradeOption):
    def __init__(self, data):
        super().__init__(data)
        self.weapon_id = int(self.effect_data.get('weapon_id', 0))

    def apply(self, player):
        print(f"[UPGRADE] Get Weapon ID: {self.weapon_id}")
        # [逻辑] 直接追加 ID，允许持有多个相同武器
        player.weapon_controller.equipped_weapons.append(self.weapon_id)

class UpgradeManager:
    def __init__(self, resource_manager):
        self.res = resource_manager
        self.db = [] # 所有可能的升级对象列表
        self._build_db()

    def _build_db(self):
        """从 Loader 的 JSON 数据构建对象"""
        raw_data = self.res.data['upgrades']
        
        for u_id, item in raw_data.items():
            u_type = item.get('type')
            
            try:
                if u_type == 'stat':
                    self.db.append(StatUpgrade(item))
                elif u_type == 'weapon':
                    # 注意：需要在 upgrades.json 里定义 weapon 类型的结构
                    self.db.append(WeaponUpgrade(item))
                else:
                    # 暂时处理通用类型或未定义类型
                    print(f"[System] Skip unknown upgrade type: {u_type} for ID {u_id}")
            except Exception as e:
                print(f"[ERROR] Failed to parse upgrade {u_id}: {e}")
        
        print(f"[System] Upgrade Database built. Total options: {len(self.db)}")

    def get_random_options(self, level, amount=3):
        """
        随机获取 amount 个升级选项。
        TODO: 可以加入 level 过滤 (tier) 或 前置条件检查
        """
        if not self.db:
            return []
        
        # 简单随机，允许重复吗？通常不允许
        # 如果池子比 amount 小，就全返回
        k = min(amount, len(self.db))
        return random.sample(self.db, k)   