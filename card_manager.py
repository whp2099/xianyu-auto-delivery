"""
闲鱼自动发货系统 - 卡密管理模块
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime

class CardManager:
    """卡密管理类"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.records_file = os.path.join(data_dir, "delivery_records.json")
        self.records = self._load_records()
    
    def _load_records(self) -> Dict:
        """加载发货记录"""
        if os.path.exists(self.records_file):
            with open(self.records_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_records(self):
        """保存发货记录"""
        with open(self.records_file, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
    
    def load_cards(self, card_file: str) -> List[str]:
        """从文件加载卡密列表"""
        file_path = os.path.join(self.data_dir, card_file)
        if not os.path.exists(file_path):
            return []
        
        cards = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    cards.append(line)
        return cards
    
    def get_available_card(self, product_id: str, card_file: str) -> Optional[str]:
        """获取一个未使用的卡密"""
        cards = self.load_cards(card_file)
        used_cards = self.records.get(product_id, {}).get("used_cards", [])
        
        for card in cards:
            if card not in used_cards:
                return card
        return None
    
    def mark_card_used(self, product_id: str, card: str, order_info: Dict):
        """标记卡密已使用"""
        if product_id not in self.records:
            self.records[product_id] = {"used_cards": [], "orders": []}
        
        self.records[product_id]["used_cards"].append(card)
        self.records[product_id]["orders"].append({
            "card": card,
            "buyer_id": order_info.get("buyer_id"),
            "buyer_nickname": order_info.get("buyer_nickname"),
            "order_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "item_title": order_info.get("item_title")
        })
        self._save_records()
    
    def get_remaining_count(self, product_id: str, card_file: str) -> int:
        """获取剩余卡密数量"""
        cards = self.load_cards(card_file)
        used_cards = self.records.get(product_id, {}).get("used_cards", [])
        return len(cards) - len(used_cards)
    
    def get_delivery_history(self, product_id: str = None) -> List[Dict]:
        """获取发货历史"""
        if product_id:
            return self.records.get(product_id, {}).get("orders", [])
        
        all_orders = []
        for pid, data in self.records.items():
            for order in data.get("orders", []):
                order["product_id"] = pid
                all_orders.append(order)
        return sorted(all_orders, key=lambda x: x["order_time"], reverse=True)
    
    def add_cards(self, card_file: str, cards: List[str]):
        """批量添加卡密到文件"""
        file_path = os.path.join(self.data_dir, card_file)
        with open(file_path, 'a', encoding='utf-8') as f:
            for card in cards:
                f.write(f"{card}\n")
