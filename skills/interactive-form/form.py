"""
Interactive form: renders a JSON form spec as a web page,
collects user input, prints JSON result to stdout.

Usage: python3 form.py /path/to/form.json
       python3 form.py '{"title":"Pick","fields":[...]}'
"""

import http.server
import json
import sys
import os
import base64
import tempfile
import webbrowser
import threading
import shutil
from pathlib import Path

TEMP_DIR = Path(tempfile.mkdtemp(prefix="kiro-form-"))
result_data = None


def build_html(spec: dict) -> str:
    """Build the form HTML from a JSON spec."""
    title = spec.get("title", "Form")
    description = spec.get("description", "")
    fields = spec.get("fields", [])
    submit_text = spec.get("submitText", "Submit")
    cancel_text = spec.get("cancelText", "Cancel")

    field_html = ""
    for f in fields:
        fid = f["id"]
        ftype = f["type"]
        label = f.get("label", fid)
        required = f.get("required", False)
        req_mark = ' <span style="color:#ef4444">*</span>' if required else ""

        if ftype == "markdown":
            field_html += f'<div class="field"><div class="md-content">{f.get("content", "")}</div></div>'
            continue

        if ftype == "display_image":
            url = f.get("url", "")
            field_html += f'<div class="field"><label>{label}</label><img src="{url}" class="preview-img"></div>'
            continue

        field_html += f'<div class="field"><label>{label}{req_mark}</label>'

        if ftype == "text":
            ph = f.get("placeholder", "")
            val = f.get("default", "")
            field_html += f'<input type="text" data-id="{fid}" placeholder="{ph}" value="{val}" class="input">'

        elif ftype == "textarea":
            rows = f.get("rows", 3)
            val = f.get("default", "")
            field_html += f'<textarea data-id="{fid}" rows="{rows}" class="input">{val}</textarea>'

        elif ftype == "number":
            val = f.get("default", 0)
            mn = f.get("min", "")
            mx = f.get("max", "")
            field_html += f'<input type="number" data-id="{fid}" value="{val}" min="{mn}" max="{mx}" class="input">'

        elif ftype == "radio":
            opts = f.get("options", [])
            default = f.get("default", "")
            field_html += '<div class="radio-group">'
            for o in opts:
                checked = " checked" if o == default else ""
                field_html += f'<label class="radio-item"><input type="radio" name="{fid}" value="{o}"{checked}><span>{o}</span></label>'
            field_html += "</div>"

        elif ftype == "checkbox":
            opts = f.get("options", [])
            defaults = f.get("default", [])
            field_html += '<div class="checkbox-group">'
            for o in opts:
                checked = " checked" if o in defaults else ""
                field_html += f'<label class="checkbox-item"><input type="checkbox" data-id="{fid}" value="{o}"{checked}><span>{o}</span></label>'
            field_html += "</div>"

        elif ftype == "select":
            opts = f.get("options", [])
            default = f.get("default", "")
            field_html += f'<select data-id="{fid}" class="input">'
            for o in opts:
                sel = " selected" if o == default else ""
                field_html += f'<option value="{o}"{sel}>{o}</option>'
            field_html += "</select>"

        elif ftype == "slider":
            mn = f.get("min", 0)
            mx = f.get("max", 100)
            val = f.get("default", mn)
            field_html += f'<div class="slider-wrap"><input type="range" data-id="{fid}" min="{mn}" max="{mx}" value="{val}" oninput="this.nextElementSibling.textContent=this.value"><span class="slider-val">{val}</span></div>'

        elif ftype == "toggle":
            checked = " checked" if f.get("default", False) else ""
            field_html += f'<label class="toggle-wrap"><input type="checkbox" data-id="{fid}"{checked} data-toggle="1"><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'

        elif ftype == "image":
            field_html += f'''<div class="image-drop" data-id="{fid}" tabindex="0">
              <div class="image-hint">⌘V paste or drag image here</div>
              <img class="image-preview" style="display:none">
              <input type="hidden" data-id="{fid}">
            </div>'''

        elif ftype == "file":
            accept = f.get("accept", "*")
            field_html += f'<input type="file" data-id="{fid}" accept="{accept}" class="file-input">'

        elif ftype == "code":
            val = f.get("value", "")
            rows = f.get("rows", 6)
            field_html += f'<textarea data-id="{fid}" rows="{rows}" class="input code">{val}</textarea>'

        elif ftype == "confirm":
            danger = "danger" if f.get("danger", False) else ""
            field_html += f'<label class="toggle-wrap"><input type="checkbox" data-id="{fid}" data-toggle="1"><span class="toggle-track {danger}"><span class="toggle-thumb"></span></span><span class="confirm-label">{label}</span></label>'

        elif ftype == "tags":
            defaults = f.get("default", [])
            field_html += f'<div class="tags-wrap" data-id="{fid}"><div class="tags-list"></div><input type="text" class="tags-input input" placeholder="Type and press Enter"></div>'
            field_html += f'<script>initTags("{fid}", {json.dumps(defaults)})</script>'

        elif ftype == "color":
            val = f.get("default", "#4a90d9")
            field_html += f'<input type="color" data-id="{fid}" value="{val}" class="color-input">'

        elif ftype == "date":
            val = f.get("default", "")
            field_html += f'<input type="date" data-id="{fid}" value="{val}" class="input">'

        field_html += "</div>"

    # Auto-append _extra textarea for custom user input
    if not any(f["id"] == "_extra" for f in fields):
        field_html += '<div class="field extra-field"><label>还有别的想说的吗？</label>'
        field_html += '<textarea data-id="_extra" rows="2" class="input" placeholder="补充想法、备注、吐槽……"></textarea></div>'
        fields.append({"id": "_extra", "type": "textarea"})

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,system-ui,sans-serif; background:#f5f5f7; min-height:100vh; display:flex; justify-content:center; padding:24px; }}
  .container {{ background:#fff; border-radius:16px; box-shadow:0 4px 24px rgba(0,0,0,.08); padding:28px; width:520px; max-width:100%; }}
  h2 {{ font-size:18px; color:#333; margin-bottom:4px; }}
  .desc {{ color:#888; font-size:13px; margin-bottom:20px; }}
  .field {{ margin-bottom:16px; }}
  .field > label {{ display:block; font-size:13px; font-weight:600; color:#555; margin-bottom:6px; }}
  .input {{ width:100%; padding:8px 12px; border:1px solid #ddd; border-radius:8px; font-size:14px; outline:none; transition:border-color .2s; }}
  .input:focus {{ border-color:#4a90d9; }}
  .input.code {{ font-family:'SF Mono',Menlo,monospace; font-size:13px; tab-size:2; }}
  .radio-group, .checkbox-group {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .radio-item, .checkbox-item {{ display:flex; align-items:center; gap:4px; padding:6px 12px; background:#f9f9f9; border-radius:8px; font-size:13px; cursor:pointer; transition:background .15s; }}
  .radio-item:hover, .checkbox-item:hover {{ background:#eef; }}
  .slider-wrap {{ display:flex; align-items:center; gap:12px; }}
  .slider-wrap input {{ flex:1; }}
  .slider-val {{ font-size:14px; font-weight:600; color:#4a90d9; min-width:2em; text-align:center; }}
  .toggle-wrap {{ display:inline-flex; align-items:center; gap:8px; cursor:pointer; }}
  .toggle-track {{ display:inline-block; width:44px; height:24px; min-width:44px; background:#ccc; border-radius:12px; position:relative; transition:background .2s; }}
  .toggle-track.danger {{ background:#ccc; }}
  input:checked + .toggle-track {{ background:#22c55e; }}
  input:checked + .toggle-track.danger {{ background:#ef4444; }}
  .toggle-thumb {{ width:20px; height:20px; background:#fff; border-radius:50%; position:absolute; top:2px; left:2px; transition:transform .2s; box-shadow:0 1px 3px rgba(0,0,0,.2); }}
  input:checked + .toggle-track .toggle-thumb {{ transform:translateX(20px); }}
  input[data-toggle] {{ position:absolute; opacity:0; pointer-events:none; }}
  .confirm-label {{ font-size:13px; color:#555; }}
  .image-drop {{ border:2px dashed #ccc; border-radius:12px; padding:24px; text-align:center; cursor:pointer; transition:border-color .2s; }}
  .image-drop:hover, .image-drop.over {{ border-color:#4a90d9; background:#f0f7ff; }}
  .image-hint {{ color:#aaa; font-size:14px; }}
  .image-preview {{ max-width:100%; max-height:200px; border-radius:8px; margin-top:8px; }}
  .preview-img {{ max-width:100%; border-radius:8px; }}
  .file-input {{ font-size:13px; }}
  .color-input {{ width:48px; height:36px; border:none; border-radius:8px; cursor:pointer; }}
  .tags-wrap {{ display:flex; flex-wrap:wrap; gap:4px; padding:6px 8px; border:1px solid #ddd; border-radius:8px; align-items:center; }}
  .tags-list {{ display:flex; flex-wrap:wrap; gap:4px; }}
  .tag-chip {{ display:flex; align-items:center; gap:2px; padding:2px 8px; background:#e8f0fe; border-radius:6px; font-size:12px; }}
  .tag-chip button {{ background:none; border:none; cursor:pointer; color:#888; font-size:14px; }}
  .tags-input {{ border:none!important; outline:none; flex:1; min-width:80px; padding:4px; font-size:13px; }}
  .md-content {{ font-size:13px; color:#555; line-height:1.6; }}
  .actions {{ display:flex; gap:10px; justify-content:flex-end; margin-top:20px; padding-top:16px; border-top:1px solid #eee; }}
  .btn {{ padding:8px 24px; border:none; border-radius:8px; font-size:14px; cursor:pointer; transition:all .15s; }}
  .btn-primary {{ background:#4a90d9; color:#fff; }}
  .btn-primary:hover {{ background:#3a7bc8; }}
  .btn-cancel {{ background:#f0f0f0; color:#666; }}
  .btn-cancel:hover {{ background:#e0e0e0; }}
</style></head><body>
<div class="container">
  <h2>{title}</h2>
  {"<p class='desc'>" + description + "</p>" if description else ""}
  <form id="form">{field_html}</form>
  <div class="actions">
    <button class="btn btn-cancel" onclick="cancel()">{cancel_text}</button>
    <button class="btn btn-primary" onclick="submit()">{submit_text}</button>
  </div>
</div>
<script>
const tagsData = {{}};
function initTags(id, defaults) {{
  tagsData[id] = [...defaults];
  renderTags(id);
  const wrap = document.querySelector(`.tags-wrap[data-id="${{id}}"] .tags-input`);
  if (wrap) wrap.addEventListener('keydown', e => {{
    if (e.key === 'Enter' || e.key === ',') {{
      e.preventDefault();
      const v = e.target.value.trim();
      if (v && !tagsData[id].includes(v)) {{ tagsData[id].push(v); renderTags(id); }}
      e.target.value = '';
    }}
  }});
}}
function renderTags(id) {{
  const list = document.querySelector(`.tags-wrap[data-id="${{id}}"] .tags-list`);
  if (!list) return;
  list.innerHTML = tagsData[id].map((t,i) => `<span class="tag-chip">${{t}}<button onclick="removeTag('${{id}}', ${{i}})">&times;</button></span>`).join('');
}}
function removeTag(id, i) {{ tagsData[id].splice(i, 1); renderTags(id); }}

// Image paste/drop
document.querySelectorAll('.image-drop').forEach(drop => {{
  const id = drop.dataset.id;
  const preview = drop.querySelector('.image-preview');
  const hidden = drop.querySelector('input[type=hidden]');
  const hint = drop.querySelector('.image-hint');
  function setImage(dataUrl) {{
    preview.src = dataUrl; preview.style.display = 'block';
    hint.style.display = 'none'; hidden.value = dataUrl;
  }}
  drop.addEventListener('paste', e => {{
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {{
      if (item.type.startsWith('image/')) {{
        const reader = new FileReader();
        reader.onload = () => setImage(reader.result);
        reader.readAsDataURL(item.getAsFile());
      }}
    }}
  }});
  drop.addEventListener('dragover', e => {{ e.preventDefault(); drop.classList.add('over'); }});
  drop.addEventListener('dragleave', () => drop.classList.remove('over'));
  drop.addEventListener('drop', e => {{
    e.preventDefault(); drop.classList.remove('over');
    const file = e.dataTransfer.files[0];
    if (file?.type.startsWith('image/')) {{
      const reader = new FileReader();
      reader.onload = () => setImage(reader.result);
      reader.readAsDataURL(file);
    }}
  }});
}});

function collect() {{
  const result = {{}};
  const fields = {json.dumps(fields)};
  for (const f of fields) {{
    const id = f.id;
    if (f.type === 'markdown' || f.type === 'display_image') continue;
    if (f.type === 'radio') {{
      const el = document.querySelector(`input[name="${{id}}"]:checked`);
      result[id] = el ? el.value : null;
    }} else if (f.type === 'checkbox') {{
      result[id] = [...document.querySelectorAll(`input[data-id="${{id}}"]:checked`)].map(e => e.value);
    }} else if (f.type === 'toggle' || f.type === 'confirm') {{
      result[id] = document.querySelector(`input[data-id="${{id}}"]`)?.checked || false;
    }} else if (f.type === 'slider' || f.type === 'number') {{
      result[id] = Number(document.querySelector(`[data-id="${{id}}"]`)?.value || 0);
    }} else if (f.type === 'tags') {{
      result[id] = tagsData[id] || [];
    }} else if (f.type === 'file') {{
      const el = document.querySelector(`input[data-id="${{id}}"]`);
      result[id] = el?.files?.[0]?.name || null;
    }} else if (f.type === 'image') {{
      result[id] = document.querySelector(`input[type=hidden][data-id="${{id}}"]`)?.value || null;
    }} else {{
      result[id] = document.querySelector(`[data-id="${{id}}"]`)?.value || '';
    }}
  }}
  return result;
}}

function submit() {{
  const data = JSON.stringify(collect());
  document.body.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100vh;color:#888;font-size:16px">Submitting...</div>';
  fetch('/submit', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: data }})
    .then(() => setTimeout(() => window.close(), 200))
    .catch(() => setTimeout(() => window.close(), 200));
}}
function cancel() {{
  fetch('/cancel', {{ method: 'POST' }})
    .then(() => setTimeout(() => window.close(), 200))
    .catch(() => setTimeout(() => window.close(), 200));
}}
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(build_html(form_spec).encode())

    def do_POST(self):
        global result_data
        if self.path == "/submit":
            length = int(self.headers.get("Content-Length", 0))
            result_data = json.loads(self.rfile.read(length))
            self._ok()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        elif self.path == "/cancel":
            result_data = None
            self._ok()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self._ok()

    def _ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def open_app_window(url: str):
    """Open URL in Chrome --app mode. Fallback to default browser."""
    import subprocess
    app_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for p in app_paths:
        if Path(p).exists():
            subprocess.Popen([p, f"--app={url}", "--window-size=560,700"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    for cmd in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]:
        if shutil.which(cmd):
            subprocess.Popen([cmd, f"--app={url}", "--window-size=560,700"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    webbrowser.open(url)


form_spec = {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 form.py <form.json or JSON string>", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    if arg.startswith("{"):
        form_spec = json.loads(arg)
    else:
        with open(arg) as f:
            form_spec = json.load(f)

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    open_app_window(f"http://127.0.0.1:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

    # Save image data to temp files, replace data URLs with paths
    if result_data:
        for k, v in result_data.items():
            if isinstance(v, str) and v.startswith("data:image/"):
                header, b64 = v.split(",", 1)
                ext = "png"
                if "jpeg" in header or "jpg" in header:
                    ext = "jpg"
                elif "gif" in header:
                    ext = "gif"
                elif "webp" in header:
                    ext = "webp"
                path = TEMP_DIR / f"{k}.{ext}"
                path.write_bytes(base64.b64decode(b64))
                result_data[k] = str(path)

        print(json.dumps(result_data, ensure_ascii=False))
    else:
        print("NO_SUBMIT")
