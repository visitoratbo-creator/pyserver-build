# PyWebHost.pyw

import os
import sys
import json
import threading
import logging
import shutil
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Optional UPnP
try:
    import miniupnpc
    UPNP_AVAILABLE = True
except:
    UPNP_AVAILABLE = False

APP_NAME = "PyWebHost"
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
SERVED_DIR = os.path.join(BASE_DIR, "served")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "mask_extensions": True,
    "enable_upnp": True
}

# ------------------- Setup -------------------

def first_time_setup():
    os.makedirs(SERVED_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

    index_path = os.path.join(SERVED_DIR, "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("<h1>PyWebHost Running</h1>")

# ------------------- Logging -------------------

def setup_logging():
    logging.basicConfig(
        filename=os.path.join(LOG_DIR, "access.log"),
        level=logging.INFO,
        format="%(asctime)s | %(message)s"
    )

# ------------------- Server -------------------

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

class Handler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        config = load_config()
        parsed = urlparse(path)
        clean = parsed.path.lstrip("/")

        if config["mask_extensions"] and "." not in clean:
            clean += ".html"

        return os.path.join(SERVED_DIR, clean)

    def log_message(self, fmt, *args):
        logging.info("%s - %s" % (self.client_address[0], fmt % args))

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.handle_api()
        else:
            super().do_GET()

    def handle_api(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"running"}')

        elif parsed.path == "/api/echo":
            qs = parse_qs(parsed.query)
            msg = qs.get("msg", [""])[0]
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"echo":"{msg}"}}'.encode())

        else:
            self.send_error(404)

class WebServer:
    def __init__(self):
        self.server = None
        self.thread = None
        self.upnp = None

    def start(self):
        config = load_config()
        self.server = ThreadingHTTPServer((config["host"], config["port"]), Handler)

        if config["enable_upnp"] and UPNP_AVAILABLE:
            self.enable_upnp(config["port"])

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
        if self.upnp:
            try:
                config = load_config()
                self.upnp.deleteportmapping(config["port"], "TCP")
            except:
                pass

    def enable_upnp(self, port):
        try:
            self.upnp = miniupnpc.UPnP()
            self.upnp.discover()
            self.upnp.selectigd()
            self.upnp.addportmapping(port, "TCP",
                                     self.upnp.lanaddr, port,
                                     APP_NAME, "")
        except:
            pass

# ------------------- GUI -------------------

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("950x600")
        self.root.resizable(False, False)

        self.server = WebServer()
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.build_ui()

    def build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.tab_dashboard = ttk.Frame(notebook)
        self.tab_settings = ttk.Frame(notebook)
        self.tab_files = ttk.Frame(notebook)
        self.tab_docs = ttk.Frame(notebook)

        notebook.add(self.tab_dashboard, text="Dashboard")
        notebook.add(self.tab_settings, text="Settings")
        notebook.add(self.tab_files, text="File Manager")
        notebook.add(self.tab_docs, text="Documentation")

        self.build_dashboard()
        self.build_settings()
        self.build_files()
        self.build_docs()

    def build_dashboard(self):
        ttk.Button(self.tab_dashboard, text="Start Server",
                   command=self.server.start).pack(pady=20)

        ttk.Button(self.tab_dashboard, text="Stop Server",
                   command=self.server.stop).pack(pady=10)

        ttk.Label(self.tab_dashboard,
                  text="Logs: logs/access.log").pack(pady=20)

    def build_settings(self):
        config = load_config()

        self.port_var = tk.IntVar(value=config["port"])
        self.mask_var = tk.BooleanVar(value=config["mask_extensions"])
        self.upnp_var = tk.BooleanVar(value=config["enable_upnp"])

        ttk.Label(self.tab_settings, text="Port").pack()
        ttk.Entry(self.tab_settings, textvariable=self.port_var).pack()

        ttk.Checkbutton(self.tab_settings,
                        text="Mask .html extensions",
                        variable=self.mask_var).pack(pady=5)

        ttk.Checkbutton(self.tab_settings,
                        text="Enable UPnP",
                        variable=self.upnp_var).pack(pady=5)

        ttk.Button(self.tab_settings,
                   text="Save Settings",
                   command=self.save_settings).pack(pady=20)

    def build_files(self):
        ttk.Button(self.tab_files,
                   text="Add File",
                   command=self.add_file).pack(pady=10)

        ttk.Button(self.tab_files,
                   text="Add Folder",
                   command=self.add_folder).pack(pady=10)

    def build_docs(self):
        text = tk.Text(self.tab_docs)
        text.pack(fill="both", expand=True)

        text.insert("1.0",
"""
PyWebHost Documentation

Access site:
http://YOUR_IP:PORT

Mask extension:
http://IP:PORT/index

API:
GET /api/status
GET /api/echo?msg=hello

Files go in /served
Logs in /logs

UPnP auto-forwards your port.
""")

    def add_file(self):
        path = filedialog.askopenfilename()
        if path:
            shutil.copy(path, SERVED_DIR)
            messagebox.showinfo("Success", "File added.")

    def add_folder(self):
        path = filedialog.askdirectory()
        if path:
            dest = os.path.join(SERVED_DIR,
                                os.path.basename(path))
            shutil.copytree(path, dest, dirs_exist_ok=True)
            messagebox.showinfo("Success", "Folder added.")

    def save_settings(self):
        config = load_config()
        config["port"] = self.port_var.get()
        config["mask_extensions"] = self.mask_var.get()
        config["enable_upnp"] = self.upnp_var.get()

        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)

        messagebox.showinfo("Saved", "Settings saved.")

# ------------------- Run -------------------

if __name__ == "__main__":
    first_time_setup()
    setup_logging()

    root = tk.Tk()
    app = App(root)
    root.mainloop()
