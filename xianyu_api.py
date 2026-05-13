"""
闲鱼自动发货系统 - 闲鱼API封装
基于 WebSocket 和 HTTP API 实现
"""

import json
import time
import hmac
import hashlib
import requests
import websocket
import threading
from typing import Callable, Dict, List, Optional
from urllib.parse import quote

class XianYuAPI:
    """闲鱼API封装类"""
    
    def __init__(self, cookie: str, token: str = None):
        self.cookie = cookie
        self.token = token
        self.user_id = None
        self.ws = None
        self.message_callback = None
        self.running = False
        self.ws_thread = None
        
        # API 基础配置
        self.base_url = "https://www.goofish.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cookie": cookie,
            "Referer": "https://www.goofish.com/",
        }
        
        # 提取用户ID
        self._extract_user_id()
    
    def _extract_user_id(self):
        """从Cookie中提取用户ID"""
        # 尝试从cookie中提取
        for part in self.cookie.split(';'):
            if '_nk_' in part or 'unb=' in part:
                try:
                    import urllib.parse
                    value = part.split('=')[1].strip()
                    self.user_id = urllib.parse.unquote(value)
                    break
                except:
                    pass
    
    def _generate_sign(self, params: Dict, t: str) -> str:
        """生成请求签名"""
        # 简化的签名生成，实际需要根据闲鱼的签名算法调整
        sorted_params = sorted(params.items())
        sign_str = ''.join([f"{k}{v}" for k, v in sorted_params]) + t
        return hashlib.md5(sign_str.encode()).hexdigest()
    
    def get_message_list(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """获取消息列表"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.message.list/1.0/"
            params = {
                "page": page,
                "pageSize": page_size
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {}).get("messages", [])
        except Exception as e:
            print(f"获取消息列表失败: {e}")
        return []
    
    def get_chat_history(self, user_id: str, page: int = 1) -> List[Dict]:
        """获取与指定用户的聊天记录"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.message.history/1.0/"
            params = {
                "userId": user_id,
                "page": page
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {}).get("messages", [])
        except Exception as e:
            print(f"获取聊天记录失败: {e}")
        return []
    
    def send_message(self, user_id: str, content: str, item_id: str = None) -> bool:
        """发送消息给买家"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.message.send/1.0/"
            
            payload = {
                "toUserId": user_id,
                "content": content,
                "msgType": "text"
            }
            if item_id:
                payload["itemId"] = item_id
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"发送消息失败: {e}")
        return False
    
    def get_item_info(self, item_id: str) -> Optional[Dict]:
        """获取商品信息"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.item.detail/1.0/"
            params = {"itemId": item_id}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {})
        except Exception as e:
            print(f"获取商品信息失败: {e}")
        return None
    
    def get_order_info(self, order_id: str) -> Optional[Dict]:
        """获取订单信息"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.order.detail/1.0/"
            params = {"orderId": order_id}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {})
        except Exception as e:
            print(f"获取订单信息失败: {e}")
        return None
    
    def confirm_delivery(self, order_id: str) -> bool:
        """确认发货（点击发货按钮）"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.order.deliver/1.0/"
            payload = {
                "orderId": order_id,
                "deliveryType": "no_logistics"  # 虚拟商品无需物流
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"确认发货失败: {e}")
        return False
    
    def _on_ws_message(self, ws, message):
        """WebSocket消息回调"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "message":
                msg_data = data.get("data", {})
                if self.message_callback:
                    self.message_callback(msg_data)
                    
        except Exception as e:
            print(f"处理WebSocket消息失败: {e}")
    
    def _on_ws_error(self, ws, error):
        """WebSocket错误回调"""
        print(f"WebSocket错误: {error}")
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭回调"""
        print(f"WebSocket连接关闭: {close_status_code} - {close_msg}")
        self.running = False
    
    def _on_ws_open(self, ws):
        """WebSocket连接成功回调"""
        print("WebSocket连接成功，开始监听消息...")
        # 发送认证消息
        auth_msg = {
            "type": "auth",
            "data": {
                "token": self.token,
                "userId": self.user_id
            }
        }
        ws.send(json.dumps(auth_msg))
    
    def start_websocket(self, message_callback: Callable):
        """启动WebSocket监听"""
        if self.running:
            print("WebSocket已经在运行")
            return
        
        self.message_callback = message_callback
        self.running = True
        
        # WebSocket URL（需要根据实际闲鱼WebSocket地址调整）
        ws_url = f"wss://wss.goofish.com/ws?token={self.token}"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
            header=[f"Cookie: {self.cookie}"]
        )
        
        # 在后台线程运行WebSocket
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
    
    def stop_websocket(self):
        """停止WebSocket监听"""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.ws_thread:
            self.ws_thread.join(timeout=5)
        print("WebSocket已停止")
    
    def check_login(self) -> bool:
        """检查登录状态"""
        try:
            url = f"{self.base_url}/awp/mtop.taobao.idle.user.get/1.0/"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"检查登录状态失败: {e}")
        return False
