"""
闲鱼自动发货系统 - Web 管理界面版本
支持通过网页配置 Cookie 和查看状态
"""

import time
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import Config
from card_manager import CardManager
from xianyu_api import XianYuAPI
from xianyu_bot import XianYuBot

class WebHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理"""
    
    bot = None
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path == "/" or self.path == "/index.html":
            self.send_html()
        elif self.path == "/status":
            self.send_status()
        elif self.path == "/config":
            self.send_config()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理 POST 请求"""
        if self.path == "/update-config":
            self.update_config()
        elif self.path == "/start":
            self.start_bot()
        elif self.path == "/stop":
            self.stop_bot()
        else:
            self.send_error(404)
    
    def send_html(self):
        """发送 HTML 页面"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>闲鱼自动发货 - 管理后台</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        textarea { height: 150px; font-family: monospace; }
        .btn { padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 5px; }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .btn:hover { opacity: 0.8; }
        .status { padding: 15px; background: #e8f5e9; border-radius: 5px; margin-bottom: 20px; }
        .error { background: #ffebee; color: #c62828; }
        .success { background: #e8f5e9; color: #2e7d32; }
        .info { background: #e3f2fd; color: #1565c0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐟 闲鱼自动发货机器人</h1>
        
        <div class="status" id="status">
            状态: 加载中...
        </div>
        
        <div class="form-group">
            <label>Cookie 配置</label>
            <textarea id="cookie" placeholder="请粘贴您的闲鱼 Cookie..."></textarea>
        </div>
        
        <div class="form-group">
            <label>Token（可选）</label>
            <input type="text" id="token" placeholder="留空则使用轮询模式">
        </div>
        
        <button class="btn btn-primary" onclick="saveConfig()">💾 保存配置</button>
        <button class="btn btn-primary" onclick="startBot()">▶️ 启动机器人</button>
        <button class="btn btn-danger" onclick="stopBot()">⏹️ 停止机器人</button>
        
        <div id="message" style="margin-top: 20px;"></div>
    </div>
    
    <script>
        async function loadStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('status').innerHTML = '状态: ' + (data.running ? '🟢 运行中' : '🔴 已停止');
                document.getElementById('cookie').value = data.cookie || '';
                document.getElementById('token').value = data.token || '';
            } catch (e) {
                console.log(e);
            }
        }
        
        async function saveConfig() {
            const cookie = document.getElementById('cookie').value;
            const token = document.getElementById('token').value;
            
            const res = await fetch('/update-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({cookie, token})
            });
            
            const msg = await res.json();
            showMessage(msg.message, msg.success ? 'success' : 'error');
        }
        
        async function startBot() {
            const res = await fetch('/start', {method: 'POST'});
            const msg = await res.json();
            showMessage(msg.message, msg.success ? 'success' : 'error');
            loadStatus();
        }
        
        async function stopBot() {
            const res = await fetch('/stop', {method: 'POST'});
            const msg = await res.json();
            showMessage(msg.message, msg.success ? 'success' : 'error');
            loadStatus();
        }
        
        function showMessage(text, type) {
            document.getElementById('message').innerHTML = '<div class="' + type + '">' + text + '</div>';
        }
        
        loadStatus();
        setInterval(loadStatus, 3000);
    </script>
</body>
</html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def send_status(self):
        """发送状态信息"""
        config = self.bot.config if self.bot else None
        status = {
            "running": self.bot.running if self.bot else False,
            "cookie": config.get("xianyu.cookie", "") if config else "",
            "token": config.get("xianyu.token", "") if config else "",
            "products_count": len(config.config.get("products", {})) if config else 0
        }
        self.send_json(status)
    
    def send_config(self):
        """发送配置信息"""
        config = self.bot.config if self.bot else None
        self.send_json(config.config if config else {})
    
    def update_config(self):
        """更新配置"""
        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length)
        data = json.loads(post_data.decode('utf-8'))
        
        if self.bot:
            if data.get('cookie'):
                self.bot.config.set("xianyu.cookie", data['cookie'])
            if 'token' in data:
                self.bot.config.set("xianyu.token", data.get('token', ''))
        
        self.send_json({"success": True, "message": "配置已保存"})
    
    def start_bot(self):
        """启动机器人"""
        if self.bot:
            if self.bot.running:
                self.send_json({"success": False, "message": "机器人已经在运行"})
            else:
                threading.Thread(target=self.bot.start, daemon=True).start()
                self.send_json({"success": True, "message": "机器人已启动"})
        else:
            self.send_json({"success": False, "message": "机器人未初始化"})
    
    def stop_bot(self):
        """停止机器人"""
        if self.bot:
            self.bot.stop()
            self.send_json({"success": True, "message": "机器人已停止"})
        else:
            self.send_json({"success": False, "message": "机器人未初始化"})
    
    def send_json(self, data):
        """发送 JSON 响应"""
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


class WebApp:
    """Web 应用"""
    
    def __init__(self, bot: XianYuBot, port: int = 8080):
        self.bot = bot
        self.port = int(os.environ.get("PORT", port))
        self.server = None
    
    def start(self):
        """启动 Web 服务器"""
        WebHandler.bot = self.bot
        self.server = HTTPServer(("0.0.0.0", self.port), WebHandler)
        print(f"🌐 Web 管理界面已启动: http://0.0.0.0:{self.port}")
        print(f"📱 访问 http://localhost:{self.port} 进行配置")
        self.server.serve_forever()


def main():
    """主函数"""
    bot = XianYuBot()
    app = WebApp(bot)
    
    print("=" * 50)
    print("闲鱼自动发货机器人 - Web 版本")
    print("=" * 50)
    print("正在启动 Web 服务...")
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        if bot.running:
            bot.stop()


if __name__ == "__main__":
    main()
