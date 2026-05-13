"""
闲鱼自动发货系统 - 主程序
整合消息监听、自动回复、自动发货功能
"""

import time
import json
import re
import os
from datetime import datetime
from typing import Dict, List
from config import Config
from card_manager import CardManager
from xianyu_api import XianYuAPI

class XianYuBot:
    """闲鱼自动发货机器人"""
    
    def __init__(self):
        self.config = Config()
        self.card_manager = CardManager()
        self.api = None
        self.running = False
        self.processed_messages = set()  # 已处理的消息ID，避免重复处理
        self.last_check_time = 0
        
    def initialize(self) -> bool:
        """初始化机器人"""
        print("=" * 50)
        print("闲鱼自动发货机器人 v1.0")
        print("=" * 50)
        
        # 获取配置
        cookie = self.config.get("xianyu.cookie")
        token = self.config.get("xianyu.token")
        
        if not cookie:
            print("❌ 错误：未配置Cookie")
            print("请先在 config.json 中填写您的闲鱼Cookie")
            return False
        
        # 初始化API
        self.api = XianYuAPI(cookie, token)
        
        # 检查登录状态
        print("正在检查登录状态...")
        if not self.api.check_login():
            print("❌ 登录状态检查失败，请检查Cookie是否有效")
            return False
        
        print("✅ 登录状态正常")
        print(f"✅ 已配置 {len(self.config.config.get('products', {}))} 个商品")
        print("=" * 50)
        return True
    
    def start(self):
        """启动机器人"""
        if not self.initialize():
            return
        
        self.running = True
        print("\n🚀 机器人已启动，正在监听消息...")
        print("按 Ctrl+C 停止运行\n")
        
        try:
            # 方式1：使用WebSocket实时监听（推荐）
            if self.api.token:
                print("使用 WebSocket 模式监听消息...")
                self.api.start_websocket(self._handle_message)
                # 保持主线程运行
                while self.running:
                    time.sleep(1)
            else:
                # 方式2：使用轮询模式（备用）
                print("使用轮询模式监听消息...")
                self._polling_mode()
                
        except KeyboardInterrupt:
            print("\n\n正在停止机器人...")
        finally:
            self.stop()
    
    def stop(self):
        """停止机器人"""
        self.running = False
        if self.api:
            self.api.stop_websocket()
        print("✅ 机器人已停止")
    
    def _polling_mode(self):
        """轮询模式 - 定期检查新消息"""
        check_interval = self.config.get("xianyu.check_interval", 10)
        
        while self.running:
            try:
                messages = self.api.get_message_list(page=1, page_size=20)
                for msg in messages:
                    self._handle_message(msg)
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"轮询出错: {e}")
                time.sleep(check_interval)
    
    def _handle_message(self, message: Dict):
        """处理收到的消息"""
        # 生成消息唯一ID
        msg_id = message.get("id") or f"{message.get('userId')}_{message.get('timestamp')}"
        
        # 避免重复处理
        if msg_id in self.processed_messages:
            return
        self.processed_messages.add(msg_id)
        
        # 限制已处理消息集合大小
        if len(self.processed_messages) > 1000:
            self.processed_messages = set(list(self.processed_messages)[-500:])
        
        # 提取消息信息
        msg_type = message.get("type", "")
        content = message.get("content", "")
        user_id = message.get("userId") or message.get("fromUserId")
        user_nickname = message.get("nickname", "买家")
        item_id = message.get("itemId")
        item_title = message.get("itemTitle", "")
        
        # 只处理收到的消息（不是自己发送的）
        if message.get("isSelf"):
            return
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到消息:")
        print(f"  来自: {user_nickname}")
        print(f"  内容: {content}")
        if item_title:
            print(f"  商品: {item_title}")
        
        # 1. 处理订单相关消息（自动发货）
        if self._is_order_message(message):
            self._handle_order_message(message)
            return
        
        # 2. 处理普通消息（自动回复）
        if self.config.get("auto_reply.enabled", True):
            self._handle_auto_reply(message)
    
    def _is_order_message(self, message: Dict) -> bool:
        """判断是否为订单相关消息"""
        content = message.get("content", "")
        # 检测付款、下单等关键词
        order_keywords = ["已付款", "已下单", "购买了", "拍下", "等待发货"]
        return any(keyword in content for keyword in order_keywords)
    
    def _handle_order_message(self, message: Dict):
        """处理订单消息 - 自动发货"""
        if not self.config.get("auto_delivery.enabled", True):
            return
        
        user_id = message.get("userId") or message.get("fromUserId")
        user_nickname = message.get("nickname", "买家")
        item_id = message.get("itemId")
        item_title = message.get("itemTitle", "")
        
        print(f"  📦 检测到订单消息，准备自动发货...")
        
        # 查找商品配置
        product_config = None
        product_id = None
        
        for pid, config in self.config.config.get("products", {}).items():
            if config.get("name") in item_title or pid in str(item_id):
                product_config = config
                product_id = pid
                break
        
        if not product_config:
            print(f"  ⚠️ 未找到商品配置，跳过自动发货")
            return
        
        if not product_config.get("auto_delivery", True):
            print(f"  ⚠️ 商品未开启自动发货")
            return
        
        # 获取卡密
        card_file = product_config.get("card_file")
        if not card_file:
            print(f"  ⚠️ 商品未配置卡密文件")
            return
        
        card = self.card_manager.get_available_card(product_id, card_file)
        if not card:
            print(f"  ❌ 卡密库存不足！")
            # 发送库存不足提醒
            self.api.send_message(user_id, "抱歉，该商品暂时缺货，请联系客服处理~", item_id)
            return
        
        # 延迟发货（模拟人工操作）
        delivery_delay = self.config.get("auto_delivery.delivery_delay", 3)
        print(f"  ⏳ {delivery_delay}秒后自动发货...")
        time.sleep(delivery_delay)
        
        # 构造发货消息
        message_template = product_config.get("message_template", 
            "感谢您的购买！\n\n{card_content}\n\n如有问题请联系客服~")
        delivery_message = message_template.format(card_content=card)
        
        # 发送卡密
        if self.api.send_message(user_id, delivery_message, item_id):
            # 标记卡密已使用
            self.card_manager.mark_card_used(product_id, card, {
                "buyer_id": user_id,
                "buyer_nickname": user_nickname,
                "item_title": item_title
            })
            print(f"  ✅ 自动发货成功！")
            print(f"  📋 已发送卡密: {card[:10]}...")
            
            # 可选：自动确认发货（点击发货按钮）
            if self.config.get("auto_delivery.confirm_delivery", False):
                order_id = message.get("orderId")
                if order_id:
                    self.api.confirm_delivery(order_id)
                    print(f"  ✅ 已确认发货")
        else:
            print(f"  ❌ 发货消息发送失败")
    
    def _handle_auto_reply(self, message: Dict):
        """处理自动回复"""
        content = message.get("content", "")
        user_id = message.get("userId") or message.get("fromUserId")
        item_id = message.get("itemId")
        
        # 获取回复规则
        rules = self.config.get("auto_reply.rules", [])
        
        for rule in rules:
            keywords = rule.get("keywords", [])
            response = rule.get("response", "")
            match_type = rule.get("match_type", "fuzzy")  # fuzzy, exact, regex
            
            matched = False
            
            if match_type == "exact":
                # 精确匹配
                matched = content in keywords
            elif match_type == "regex":
                # 正则匹配
                matched = any(re.search(kw, content) for kw in keywords)
            else:
                # 模糊匹配（默认）
                matched = any(kw in content for kw in keywords)
            
            if matched:
                # 延迟回复
                reply_delay = self.config.get("xianyu.auto_reply_interval", 5)
                time.sleep(reply_delay)
                
                if self.api.send_message(user_id, response, item_id):
                    print(f"  🤖 自动回复: {response[:50]}...")
                break
    
    def add_product(self, product_id: str, name: str, card_file: str = None):
        """添加商品"""
        self.config.add_product(product_id, name, card_file)
        print(f"✅ 已添加商品: {name}")
    
    def add_cards(self, product_id: str, cards: List[str]):
        """为商品添加卡密"""
        product = self.config.get_product(product_id)
        if not product:
            print(f"❌ 商品 {product_id} 不存在")
            return
        
        card_file = product.get("card_file") or f"cards_{product_id}.txt"
        self.card_manager.add_cards(card_file, cards)
        
        # 更新商品配置
        if not product.get("card_file"):
            self.config.set(f"products.{product_id}.card_file", card_file)
        
        print(f"✅ 已为 {product['name']} 添加 {len(cards)} 个卡密")
    
    def show_status(self):
        """显示当前状态"""
        print("\n" + "=" * 50)
        print("当前状态")
        print("=" * 50)
        
        products = self.config.config.get("products", {})
        print(f"商品数量: {len(products)}")
        
        for pid, config in products.items():
            card_file = config.get("card_file")
            remaining = 0
            if card_file:
                remaining = self.card_manager.get_remaining_count(pid, card_file)
            print(f"  - {config['name']}: 剩余卡密 {remaining} 个")
        
        print("=" * 50)


def main():
    """主函数"""
    bot = XianYuBot()
    
    # 命令行交互
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            bot.start()
        elif command == "status":
            bot.show_status()
        elif command == "add-product":
            if len(sys.argv) < 4:
                print("用法: python xianyu_bot.py add-product <商品ID> <商品名称>")
                return
            bot.add_product(sys.argv[2], sys.argv[3])
        elif command == "add-cards":
            if len(sys.argv) < 4:
                print("用法: python xianyu_bot.py add-cards <商品ID> <卡密1> [卡密2] ...")
                return
            cards = sys.argv[3:]
            bot.add_cards(sys.argv[2], cards)
        else:
            print(f"未知命令: {command}")
            show_help()
    else:
        # 默认启动
        bot.start()


def show_help():
    """显示帮助信息"""
    print("""
闲鱼自动发货机器人

用法:
  python xianyu_bot.py [命令] [参数]

命令:
  start                    启动机器人（默认）
  status                   查看当前状态
  add-product <ID> <名称>   添加商品
  add-cards <ID> <卡密...>  为商品添加卡密

示例:
  python xianyu_bot.py start
  python xianyu_bot.py add-product prod001 "激活码"
  python xianyu_bot.py add-cards prod001 "ABC123" "DEF456"
""")


if __name__ == "__main__":
    main()
