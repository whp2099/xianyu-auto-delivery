#!/usr/bin/env python3
"""极简版闲鱼自动发货服务"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime

PORT = int(os.environ.get("PORT", 8080))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            cookie_set = "是" if os.environ.get("XIANYU_COOKIE") else "否"
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>闲鱼自动发货</title>
    <style>
        body {{ font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
        .ok {{ color: green; }}
        .box {{ background: #f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>🐟 闲鱼自动发货服务</h1>
    <div class="box">
        <p class="ok">✅ 服务运行正常</p>
        <p>时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Cookie 配置: {cookie_set}</p>
    </div>
</body>
</html>
"""
            self.wfile.write(html.encode())
        else:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

print(f"启动服务在端口 {PORT}")
httpd = HTTPServer(("0.0.0.0", PORT), Handler)
httpd.serve_forever()
