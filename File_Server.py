import http.server
import os
import socket
import socketserver
import threading


class File_Server(threading.Thread):

    def __init__(self):
        super().__init__()
        self.port = 80 #port must be 80, other ports will not work, this require admin priviledges to work
        self.daemon = True
        self.host = self.get_active_ip() #binding host ip address

    @staticmethod
    def get_active_ip():
        """Finds the active local network IP address of the machine dynamically."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connects to a non-reachable address to determine outgoing interface IP
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def run(self):
		#Serving the ./config directory
        config_dir = os.path.join(os.getcwd(), "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # Inner class handler scoped exclusively to FileServer
        class CustomHandler(http.server.SimpleHTTPRequestHandler):

            def translate_path(self, path):
                target_zip = os.path.join(config_dir, "config.zip")
                clean_path = path.strip("/")

                if clean_path in ("", "config", "config.zip"):
                    if os.path.exists(target_zip):
                        return target_zip

                rel_path = path.lstrip("/")
                return os.path.join(config_dir, rel_path)
            def log_message(self, format, *args):
                pass  

        socketserver.TCPServer.allow_reuse_address = True

        try:
            with socketserver.TCPServer(
                (self.host, self.port), CustomHandler
            ) as httpd:
                print(f"Serving configuration on http://{self.host}:{self.port}")
                httpd.serve_forever()
        except OSError as e:
            print(f"HTTP Server error: {e}")

