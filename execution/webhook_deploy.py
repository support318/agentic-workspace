#!/usr/bin/env python3
"""
Simple webhook receiver for GitHub deployments.
When GitHub sends a push event, this script pulls latest code and restarts services.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import os
import hmac
import hashlib

SECRET = os.environ.get('WEBHOOK_SECRET', 'default-secret-change-me')
SERVER_DIR = '/home/candid/webhooks'

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/webhook/deploy':
            # Get the signature
            signature = self.headers.get('X-Hub-Signature-256', '')

            # Read the payload
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            # Verify signature (optional but recommended)
            if SECRET != 'default-secret-change-me':
                expected_sig = 'sha256=' + hmac.new(SECRET.encode(), post_data, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected_sig, signature):
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'Forbidden')
                    return

            try:
                payload = json.loads(post_data)
                ref = payload.get('ref', '')

                # Only deploy on push to main branch
                if 'refs/heads/main' in ref:
                    print("Received push to main - deploying...")
                    self.deploy()

                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'Deployment started')
                else:
                    print(f"Ignoring push to: {ref}")
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'Ignored - not main branch')

            except Exception as e:
                print(f"Error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Error: {str(e)}'.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def deploy(self):
        """Pull latest code and restart services"""
        try:
            os.chdir(SERVER_DIR)

            # Pull latest changes
            subprocess.run(['git', 'fetch', 'origin'], check=True, capture_output=True)
            subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True, capture_output=True)

            # Install dependencies
            subprocess.run(['pip3', 'install', '-r', 'requirements.txt', '--user'],
                          check=True, capture_output=True)

            # Restart services (requires passwordless sudo for systemctl)
            try:
                subprocess.run(['sudo', 'systemctl', 'restart', 'agentic-webhooks'],
                              check=True, capture_output=True)
            except:
                pass

            try:
                subprocess.run(['sudo', 'systemctl', 'restart', 'email-processor'],
                              check=True, capture_output=True)
            except:
                pass

            print("Deployment completed successfully")

        except Exception as e:
            print(f"Deployment error: {e}")
            raise

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

def run_server(port=8083):
    server_address = ('', port)
    httpd = HTTPServer(server_address, WebhookHandler)
    print(f"Webhook server running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
