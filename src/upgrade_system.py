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
        player.weapon_controller.add_weapon(w_id)

class WeaponBuffUpgrade(UpgradeOption):
    """
    武器强化升级
    支持在一个选项中同时修改多个属性 (如: 伤害+5 且 范围+20%)
    
    JSON data 格式示例:
    {
        "effects": {
            "damage": 5,           // 顶层属性
            "data.scale": 0.2,     // 嵌套属性: 视觉/判定箱缩放
            "data.radius": 20      // 嵌套属性: 光环/环绕半径
        },
        "mode": "add",             // 计算模式: add, mult, set
        "target": "all"            // 目标: all 或 特定ID
    }
    """
    def apply(self, player):
        target = self.raw_data.get('target', 'all')
        mode = self.raw_data.get('mode', 'add')
        
        # 1. 解析要修改的属性列表
        # 优先读取 'effects' 字典；如果不存在，尝试兼容旧的 'attr'/'value' 写法
        changes = {}
        if 'effects' in self.raw_data:
            changes = self.raw_data['effects']
        elif 'attr' in self.raw_data and 'value' in self.raw_data:
            changes = {self.raw_data['attr']: self.raw_data['value']}
            
        # 获取全局武器数据库
        weapon_db = player.weapon_controller.res.data['weapons']
        
        count = 0
        for w_id, w_data in weapon_db.items():
            # 筛选目标
            if target != 'all' and str(w_id) != str(target):
                continue
            
            # 应用所有变更项
            for key, val in changes.items():
                
                # A. 处理嵌套属性 (如 data.scale, data.radius)
                if key.startswith('data.'):
                    sub_key = key.split('.')[1]
                    
                    # 确保 data 字典存在
                    if 'data' not in w_data:
                        w_data['data'] = {}
                    
                    # 获取当前值 (提供合理的默认值)
                    # scale 默认为 1.0, radius 默认为 0 (或者是之前配置的值), frames 等其他值为 0
                    default_val = 1.0 if sub_key == 'scale' else 0
                    current_val = w_data['data'].get(sub_key, default_val)
                    
                    # 计算新值
                    new_val = current_val
                    if mode == 'add': new_val += val
                    elif mode == 'mult': new_val *= val
                    elif mode == 'set': new_val = val
                    
                    # 写回数据
                    w_data['data'][sub_key] = new_val
                    
                # B. 处理常规顶层属性 (damage, cooldown, speed)
                elif key in w_data:
                    current_val = w_data[key]
                    new_val = current_val
                    
                    if mode == 'add': new_val += val
                    elif mode == 'mult': new_val *= val
                    elif mode == 'set': new_val = val
                    
                    w_data[key] = new_val
            
            count += 1
            
        print(f"[UPGRADE] Applied {len(changes)} buffs to {count} weapons. Changes: {changes}")

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