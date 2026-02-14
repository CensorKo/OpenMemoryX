#!/usr/bin/env python3
"""
MemoryX Webhook Receiver - Docker Version
接收 GitHub Actions 的部署通知，触发 Docker 部署
"""

import os
import sys
import json
import logging
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 配置
DEPLOY_TOKEN = os.environ.get('DEPLOY_TOKEN', 'your-secret-token')
DEPLOY_SCRIPT = '/data/memoryx/deploy/scripts/deploy-docker.sh'
LOG_FILE = '/var/log/memoryx/webhook.log'
PORT = 9000

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_POST(self):
        try:
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            
            token = query_params.get('token', [''])[0]
            deploy_type = query_params.get('tupe', ['alpha'])[0]
            
            if token != DEPLOY_TOKEN:
                logger.warning(f"Invalid token from {self.client_address}")
                self.send_error(403, "Invalid token")
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                payload = json.loads(body)
                logger.info(f"Webhook received: {payload.get('event', 'unknown')} -> {deploy_type}")
            except json.JSONDecodeError:
                payload = {}
                logger.info(f"Webhook received (no JSON) -> {deploy_type}")
            
            # 触发 Docker 部署
            logger.info(f"Triggering Docker deployment: {deploy_type}")
            subprocess.Popen(
                ['sudo', DEPLOY_SCRIPT, deploy_type],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'success',
                'message': f'Docker deployment triggered for {deploy_type}',
                'deploy_type': deploy_type,
                'sha': payload.get('sha', 'unknown')
            }
            self.wfile.write(json.dumps(response).encode())
            
            logger.info(f"Deployment triggered successfully")
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            self.send_error(500, str(e))
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'MemoryX Webhook Receiver (Docker) is running\n')


def run_server():
    server = HTTPServer(('127.0.0.1', PORT), WebhookHandler)
    logger.info(f"Webhook server starting on port {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    run_server()
