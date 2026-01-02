# --- src/upgrade_system.py ---
import random

class UpgradeOption:
    """升级选项基类"""
    def __init__(self, data):
        self.id = data['id']
        self.title = data['title']
        self.description = data['desc']
        self.icon_key = data['image']
        self.type = data['type'] 
        self.tier = data.get('tier', 1)
        self.raw_data = data.get('data', {})

    def apply(self, player):
        """虚函数，由子类实现"""
        raise NotImplementedError

class StatUpgrade(UpgradeOption):   #type: stat
    """数值升级"""
    def __init__(self, data):
        super().__init__(data)

        # 解析 data 字段: { "attr": "speed", "value": 1.1, "mode": "mult" }
    def apply(self, player):
        attr = self.raw_data['attr']
        val = self.raw_data['value']
        mode = self.raw_data['mode']
        
        #if hasattr(player, 'stats') and attr in player.stats:
        if attr in player.stats:
            old_val = player.stats[attr]
            
            if mode == 'add':
                player.stats[attr] += val
            elif mode == 'mult':
                player.stats[attr] *= val
                
            print(f"[UPGRADE] Stat '{attr}' changed: {old_val} -> {player.stats[attr]}")
        else:
            print(f"[WARNING] Player stats missing attribute: {attr}")

class WeaponAddUpgrade(UpgradeOption):  #type: weapon_add
    def __init__(self, data):
        super().__init__(data)
    def apply(self, player):
        w_id = int(self.raw_data['weapon_id'])
        print(f"[UPGRADE] Adding Weapon ID: {w_id}")
        player.weapon_controller.equipped_weapons.append(w_id)

class WeaponBuffUpgrade(UpgradeOption): #type: weapon_upgrade
    def apply(self, player):
        target = self.raw_data.get('target', 'all')
        attr = self.raw_data['attr']
        val = self.raw_data['value']
        mode = self.raw_data['mode']

        # 获取资源管理器引用 (通过 player 获取有点绕，但在当前架构下最方便)
        # 注意：这里我们修改的是 Loader 里的全局数据，这意味着新捡到的同类武器也会变强
        weapon_db = player.weapon_controller.res.data['weapons']
        
        count = 0
        for w_id, w_data in weapon_db.items():
            # 筛选目标：如果不是 'all' 且 ID 不匹配，则跳过
            if target != 'all' and str(w_id) != str(target):
                continue
                
            # [新增] 支持修改 data 内部的字段 (如 scale, radius)
            # Schema 示例: { "attr": "data.scale", "value": 0.5, "mode": "add" }
            if attr.startswith('data.'):
                sub_key = attr.split('.')[1]
                target_dict = w_data.setdefault('data', {})
                if sub_key in target_dict:
                    if mode == 'add': target_dict[sub_key] += val
                    elif mode == 'mult': target_dict[sub_key] *= val
                else:
                    # 如果没有该字段，初始化
                    target_dict[sub_key] = val

            if attr in w_data:
                if mode == 'add':
                    w_data[attr] += val
                elif mode == 'mult':
                    w_data[attr] *= val
                count += 1
                
        print(f"[UPGRADE] Buffed {attr} for {count} weapons.")

class HealUpgrade(UpgradeOption):   #type: heal
    def apply(self, player):
        amount = self.raw_data.get('amount', 0)
        old_hp = player.current_hp
        
        # 回血并限制不超过上限
        player.current_hp = min(player.current_hp + amount, player.stats['max_hp'])
        
        print(f"[UPGRADE] Healed {player.current_hp - old_hp} HP.")

class SpecialUpgrade(UpgradeOption):    #type: special
    def apply(self, player):
        key = self.raw_data['key']
        val = self.raw_data['value']
        
        # 直接设置到 player 身上
        # 例如 player.life_steal = True
        setattr(player, key, val)
        print(f"[UPGRADE] Set special ability '{key}' to {val}")

class UpgradeManager:
    def __init__(self, resource_manager):
        self.res = resource_manager
        self.db = [] # 所有可能的升级对象列表
        self._build_db()

    def _build_db(self):
        """根据 JSON 构建对象池"""
        raw_data = self.res.data.get('upgrades', {})
        self.db = []
        
        for u_id, item in raw_data.items():
            u_type = item.get('type')
            
            try:
                if u_type == 'stat':
                    self.db.append(StatUpgrade(item))
                elif u_type == 'weapon_add' or u_type == 'weapon': # 兼容旧写法
                    self.db.append(WeaponAddUpgrade(item))
                elif u_type == 'weapon_buff':
                    self.db.append(WeaponBuffUpgrade(item))
                elif u_type == 'heal':
                    self.db.append(HealUpgrade(item))
                elif u_type == 'special':
                    self.db.append(SpecialUpgrade(item))
                else:
                    print(f"[System] Skip unknown upgrade type: {u_type} (ID: {u_id})")

            except Exception as e:
                print(f"[ERROR] Failed to parse upgrade {u_id}: {e}")
        
        print(f"[System] Upgrade Database built. Total options: {len(self.db)}")

    def get_random_options(self, level, amount=3):
        """
        抽取不重复的卡片
        逻辑：
        1. Tier <= Level (基本条件)
        2. Level - Tier < Threshold (不显示太低级的)
        """
        threshold = 5 # 等级与tier差距范围
        
        valid_options = []
        for opt in self.db:
            if opt.tier <= level:
                if (level - opt.tier) < threshold:
                    valid_options.append(opt)
        
        # 如果过滤太狠没选项了，就放宽限制
        if not valid_options:
            valid_options = [opt for opt in self.db if opt.tier <= level]
            
        if not valid_options:
            return []
            
        k = min(amount, len(valid_options))
        return random.sample(valid_options, k)