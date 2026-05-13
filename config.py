"""
闲鱼自动发货系统 - 配置文件
"""

import json
import os
from typing import Dict, List, Any

class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "xianyu": {
                "cookie": "",
                "token": "",
                "user_id": "",
                "auto_reply_interval": 5,
                "check_interval": 10
            },
            "auto_delivery": {
                "enabled": True,
                "delivery_delay": 3,
                "confirm_delivery": False
            },
            "auto_reply": {
                "enabled": True,
                "rules": [
                    {
                        "keywords": ["在吗", "在么", "在不在"],
                        "response": "您好，商品还在的，可以直接下单购买，付款后自动发货~"
                    },
                    {
                        "keywords": ["怎么买", "怎么下单"],
                        "response": "点击商品页面的【我想要】或【立即购买】即可下单，付款后系统会自动发货~"
                    }
                ]
            },
            "products": {}
        }
    
    def save(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()
    
    def add_product(self, product_id: str, name: str, card_file: str = None, 
                    message_template: str = None):
        """添加商品配置"""
        self.config["products"][product_id] = {
            "name": name,
            "card_file": card_file,
            "message_template": message_template or "感谢您的购买！\n\n{card_content}\n\n如有问题请联系客服~",
            "auto_delivery": True,
            "auto_reply": True
        }
        self.save()
    
    def get_product(self, product_id: str) -> Dict:
        """获取商品配置"""
        return self.config["products"].get(product_id, {})
