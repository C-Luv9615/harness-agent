"""
Local web server for receiving screenshots via paste/drag-drop in browser.
Auto-opens browser, saves images to temp dir, prints paths to stdout on close.
"""

import http.server
import json
import base64
import tempfile
import webbrowser
import threading
import sys
from pathlib import Path

TEMP_DIR = Path(tempfile.mkdtemp(prefix="kiro-screenshot-"))
saved_paths: list[str] = []

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Screenshot Receiver</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, system-ui, sans-serif; background: #f5f5f7; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
  .container { background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.08); padding: 20px; width: 380px; text-align: center; }
  h2 { font-size: 18px; color: #333; margin-bottom: 8px; }
  .hint { color: #888; font-size: 14px; margin-bottom: 20px; }
  .drop-zone { border: 2px dashed #ccc; border-radius: 12px; padding: 24px 16px; cursor: pointer; transition: all .2s; color: #aaa; font-size: 14px; }
  .drop-zone.over { border-color: #4a90d9; background: #f0f7ff; color: #4a90d9; }
  .list { margin-top: 16px; text-align: left; max-height: 240px; overflow-y: auto; }
  .item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #f9f9f9; border-radius: 8px; margin-bottom: 6px; font-size: 13px; color: #333; }
  .item img { width: 48px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid #eee; }
  .item .info { flex: 1; }
  .item .name { font-weight: 500; }
  .item .size { color: #999; font-size: 12px; }
  .status { margin-top: 12px; font-size: 14px; font-weight: 500; color: #2d7d46; min-height: 20px; }
  .btn { margin-top: 16px; padding: 10px 32px; background: #4a90d9; color: #fff; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; }
  .btn:hover { background: #3a7bc8; }
  input[type=file] { display: none; }
</style>
</head>
<body>
<div class="container">
  <h2>Screenshot Receiver</h2>
  <p class="hint">⌘V paste  ·  drag & drop  ·  click to browse</p>
  <div class="drop-zone" id="drop">Drop or paste image here</div>
  <input type="file" id="file" accept="image/*" multiple>
  <div class="list" id="list"></div>
  <div class="status" id="status"></div>
  <button class="btn" onclick="done()">Done</button>
</div>
<script>
const drop = document.getElementById('drop');
const fileInput = document.getElementById('file');
const list = document.getElementById('list');
const status = document.getElementById('status');
let count = 0;

drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); handleFiles(e.dataTransfer.files); });
fileInput.addEventListener('change', e => handleFiles(e.target.files));

document.addEventListener('paste', e => {
  const items = e.clipboardData?.items;
  if (!items) return;
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      upload(item.getAsFile());
    }
  }
});

function handleFiles(files) {
  for (const f of files) {
    if (f.type.startsWith('image/')) upload(f);
  }
}

function upload(file) {
  const reader = new FileReader();
  reader.onload = async () => {
    const res = await fetch('/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: file.name || 'clipboard.png', data: reader.result })
    });
    const j = await res.json();
    if (j.ok) {
      count++;
      const item = document.createElement('div');
      item.className = 'item';
      item.innerHTML = `<img src="${reader.result}"><div class="info"><div class="name">${j.name}</div><div class="size">${(file.size/1024).toFixed(0)} KB</div></div>`;
      list.appendChild(item);
      status.textContent = '✅ ' + count + ' image(s) received';
    }
  };
  reader.readAsDataURL(file);
}

function done() {
  fetch('/done', { method: 'POST' }).then(() => window.close());
}
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # suppress logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        if self.path == "/upload":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            # data is data:image/png;base64,...
            header, b64 = body["data"].split(",", 1)
            ext = "png"
            if "jpeg" in header or "jpg" in header:
                ext = "jpg"
            elif "gif" in header:
                ext = "gif"
            elif "webp" in header:
                ext = "webp"
            name = f"image_{len(saved_paths)}.{ext}"
            out = TEMP_DIR / name
            out.write_bytes(base64.b64decode(b64))
            saved_paths.append(str(out))
            self._json({"ok": True, "name": name})

        elif self.path == "/done":
            self._json({"ok": True})
            # Shutdown server in background
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def open_app_window(url: str):
    """Open URL in Chrome --app mode (no address bar, no tabs). Fallback to default browser."""
    import subprocess
    # Absolute paths (macOS)
    app_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for p in app_paths:
        if Path(p).exists():
            subprocess.Popen([p, f"--app={url}", "--window-size=400,420"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    # PATH-based lookup (Linux / other)
    for cmd in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]:
        if shutil.which(cmd):
            subprocess.Popen([cmd, f"--app={url}", "--window-size=400,420"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    webbrowser.open(url)


if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    open_app_window(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

    if saved_paths:
        for p in saved_paths:
            print(p)
    else:
        print("NO_IMAGES")
