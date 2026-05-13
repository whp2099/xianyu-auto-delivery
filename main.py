"""
闲鱼自动发货系统 - 简化版入口
用于 Railway 部署
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleHandler(BaseHTTPRequestHandler):
    """简单的 HTTP 处理器"""
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>闲鱼自动发货 - 配置页面</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 30px; border-radius: 10px; }
        h1 { color: #333; }
        .status { padding: 15px; background: #e8f5e9; border-radius: 5px; margin: 20px 0; }
        code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐟 闲鱼自动发货机器人</h1>
        <div class="status">
            <h3>✅ 服务已启动</h3>
            <p>当前时间: """ + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        </div>
        
        <h2>配置信息</h2>
        <p><strong>Cookie 状态:</strong> """ + ("✅ 已配置" if os.environ.get('XIANYU_COOKIE') else "❌ 未配置") + """</p>
        <p><strong>Token 状态:</strong> """ + ("✅ 已配置" if os.environ.get('XIANYU_TOKEN') else "⚪ 未配置（可选）") + """</p>
        
        <h2>使用说明</h2>
        <ol>
            <li>在 Railway Variables 中配置 <code>XIANYU_COOKIE</code></li>
            <li>重新部署服务</li>
            <li>访问此页面查看状态</li>
        </ol>
        
        <p style="margin-top: 30px; color: #666;">
            <strong>提示:</strong> 这是一个简化版本，完整功能需要本地运行 Python 脚本。
        </p>
    </div>
</body>
</html>
            """
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_error(404)

def main():
    """主函数"""
    port = int(os.environ.get("PORT", 8080))
    
    print(f"启动服务，端口: {port}")
    print(f"Cookie 配置: {'已设置' if os.environ.get('XIANYU_COOKIE') else '未设置'}")
    
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    print(f"服务已启动: http://0.0.0.0:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.shutdown()

if __name__ == "__main__":
    main()
