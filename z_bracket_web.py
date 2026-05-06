"""Local Chinese web UI for the Z bracket generator.

Run:
    .venv\\Scripts\\python.exe z_bracket_web.py

Open:
    http://127.0.0.1:8765
"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from z_bracket_mcp_server import generate_z_bracket, validate_design


HOST = "127.0.0.1"
PORT = 8765


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Z &#22411;&#25346;&#38057;&#25903;&#26550;&#29983;&#25104;&#22120;</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #667085;
      --line: #d7dde7;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --danger: #b42318;
      --ok: #067647;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      min-height: 74px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
    }
    main {
      padding: 28px 0 36px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(320px, 420px) 1fr;
      gap: 20px;
      align-items: start;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h2 {
      margin: 0 0 16px;
      font-size: 16px;
      letter-spacing: 0;
    }
    .field {
      display: grid;
      gap: 8px;
      padding: 12px 0;
      border-top: 1px solid #edf0f5;
    }
    .field:first-of-type { border-top: 0; padding-top: 0; }
    label {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      font-size: 14px;
      font-weight: 600;
    }
    label span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 400;
    }
    .control {
      display: grid;
      grid-template-columns: 1fr 96px;
      gap: 10px;
      align-items: center;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }
    input[type="number"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 14px;
      color: var(--text);
    }
    select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font-size: 14px;
      color: var(--text);
      background: white;
    }
    .switch-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 0 4px;
    }
    .switch-row label {
      display: inline-flex;
      align-items: center;
      justify-content: flex-start;
      gap: 8px;
      font-weight: 500;
    }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }
    button.primary {
      background: var(--accent);
      color: white;
    }
    button.primary:hover { background: var(--accent-strong); }
    button.secondary {
      background: #e9edf3;
      color: var(--text);
    }
    button:disabled {
      opacity: .62;
      cursor: wait;
    }
    .preview {
      min-height: 360px;
      display: grid;
      gap: 18px;
    }
    .diagram {
      width: 100%;
      min-height: 280px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      display: grid;
      place-items: center;
      overflow: hidden;
    }
    svg {
      width: min(720px, 100%);
      height: auto;
      display: block;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      min-width: 0;
    }
    .stat b {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      font-weight: 500;
    }
    .stat span {
      display: block;
      font-size: 15px;
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    pre {
      margin: 0;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #111827;
      color: #e5e7eb;
      min-height: 128px;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 13px;
    }
    .ok { color: var(--ok); }
    .bad { color: var(--danger); }
    @media (max-width: 860px) {
      .layout { grid-template-columns: 1fr; }
      .stats { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; padding: 16px 0; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>Z &#22411;&#25346;&#38057;&#25903;&#26550;&#21442;&#25968;&#21270;&#29983;&#25104;&#22120;</h1>
        <div class="subtitle">&#22312;&#32593;&#39029;&#20013;&#35843;&#25972;&#21442;&#25968;&#65292;&#30452;&#25509;&#29983;&#25104; STEP &#27169;&#22411;</div>
      </div>
      <div class="subtitle">&#21333;&#20301;&#65306;mm</div>
    </div>
  </header>
  <main class="wrap">
    <div class="layout">
      <section>
        <h2>&#35774;&#35745;&#21442;&#25968;</h2>
        <div id="fields"></div>
        <div class="switch-row">
          <label><input id="saveStep" type="checkbox" checked /> &#20445;&#23384; STEP &#25991;&#20214;</label>
        </div>
        <div class="actions">
          <button class="primary" id="generateBtn">&#29983;&#25104;&#27169;&#22411;</button>
          <button class="secondary" id="validateBtn">&#20165;&#39564;&#35777;</button>
          <button class="secondary" id="resetBtn">&#24674;&#22797;&#40664;&#35748;</button>
        </div>
      </section>
      <section class="preview">
        <h2>&#39044;&#35272;&#19982;&#32467;&#26524;</h2>
        <div class="diagram">
          <svg viewBox="0 0 760 360" role="img" aria-label="Z bracket preview">
            <defs>
              <linearGradient id="metal" x1="0" x2="1">
                <stop offset="0" stop-color="#cfd8e3"/>
                <stop offset="1" stop-color="#8795a8"/>
              </linearGradient>
            </defs>
            <ellipse id="base" cx="168" cy="284" rx="94" ry="28" fill="url(#metal)" stroke="#53657a" stroke-width="3"/>
            <rect id="post" x="148" y="118" width="40" height="166" rx="3" fill="#aab6c5" stroke="#53657a" stroke-width="3"/>
            <rect id="arm" x="168" y="105" width="320" height="28" rx="14" fill="#97a6b8" stroke="#53657a" stroke-width="3"/>
            <rect id="pin" x="306" y="52" width="24" height="60" rx="12" fill="#bcc7d4" stroke="#53657a" stroke-width="3"/>
            <path id="fork" d="M486 84 H592 V116 H522 V154 H592 V186 H486 Z" fill="#aab6c5" stroke="#53657a" stroke-width="3"/>
            <text x="152" y="330" fill="#475467" font-size="18">&#24213;&#24231;</text>
            <text x="256" y="91" fill="#475467" font-size="18">&#27700;&#24179;&#33218;</text>
            <text x="590" y="145" fill="#475467" font-size="18">U &#22411;&#25903;&#26550;</text>
          </svg>
        </div>
        <div class="stats">
          <div class="stat"><b>&#39564;&#35777;&#29366;&#24577;</b><span id="status">-</span></div>
          <div class="stat"><b>&#20307;&#31215;</b><span id="volume">-</span></div>
          <div class="stat"><b>STEP &#36335;&#24452;</b><span id="stepPath">-</span></div>
        </div>
        <pre id="output">&#31561;&#24453;&#29983;&#25104;&#25110;&#39564;&#35777;&#32467;&#26524;&#12290;</pre>
      </section>
    </div>
  </main>
  <script>
    const defaults = {
      disk_dia: 60,
      rod_dia: 8,
      post_height: 70,
      arm_length: 90,
      pin_offset: 45,
      process_type: "miter_45"
    };
    const labels = {
      disk_dia: ["\u5e95\u5ea7\u76f4\u5f84", 30, 140, 1],
      rod_dia: ["\u6746\u5f84", 3, 30, 0.5],
      post_height: ["\u5782\u76f4\u6bb5\u9ad8\u5ea6", 20, 180, 1],
      arm_length: ["\u6c34\u5e73\u81c2\u957f\u5ea6", 30, 220, 1],
      pin_offset: ["\u9500\u9489\u4f4d\u7f6e", 5, 200, 1]
    };
    const fields = document.getElementById("fields");

    function renderFields() {
      fields.innerHTML = "";
      for (const [name, meta] of Object.entries(labels)) {
        const [label, min, max, step] = meta;
        const row = document.createElement("div");
        row.className = "field";
        row.innerHTML = `
          <label for="${name}">${label}<span>mm</span></label>
          <div class="control">
            <input id="${name}_range" type="range" min="${min}" max="${max}" step="${step}" value="${defaults[name]}">
            <input id="${name}" type="number" min="${min}" max="${max}" step="${step}" value="${defaults[name]}">
          </div>`;
        fields.appendChild(row);
        const number = document.getElementById(name);
        const range = document.getElementById(`${name}_range`);
        number.addEventListener("input", () => {
          range.value = number.value;
          updatePreview();
        });
        range.addEventListener("input", () => {
          number.value = range.value;
          updatePreview();
        });
      }
      const processRow = document.createElement("div");
      processRow.className = "field";
      processRow.innerHTML = `
        <label for="process_type">\u8fde\u63a5\u5de5\u827a<span>process</span></label>
        <select id="process_type">
          <option value="miter_45">45 \u5ea6\u659c\u5207\u62fc\u63a5</option>
          <option value="butt_joint">\u76f4\u89d2\u5bf9\u63a5</option>
        </select>`;
      fields.appendChild(processRow);
      updatePreview();
    }

    function params() {
      const numeric = Object.fromEntries(Object.keys(labels).map((name) => [name, Number(document.getElementById(name).value)]));
      numeric.process_type = document.getElementById("process_type").value;
      return numeric;
    }

    function setBusy(busy) {
      document.getElementById("generateBtn").disabled = busy;
      document.getElementById("validateBtn").disabled = busy;
    }

    function updatePreview() {
      const p = params();
      document.getElementById("base").setAttribute("rx", Math.max(42, p.disk_dia * 1.35));
      document.getElementById("post").setAttribute("height", Math.max(72, p.post_height * 2));
      document.getElementById("post").setAttribute("y", 284 - Math.max(72, p.post_height * 2));
      document.getElementById("arm").setAttribute("width", Math.max(140, p.arm_length * 3.2));
      document.getElementById("pin").setAttribute("x", 168 + Math.min(p.pin_offset * 3.2, 300));
    }

    async function callApi(path, body) {
      setBusy(true);
      try {
        const response = await fetch(path, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(body)
        });
        return await response.json();
      } finally {
        setBusy(false);
      }
    }

    function showResult(data) {
      const ok = Boolean(data.ok);
      const validation = data.validation || data;
      document.getElementById("status").textContent = ok ? "\u901a\u8fc7" : "\u672a\u901a\u8fc7";
      document.getElementById("status").className = ok ? "ok" : "bad";
      document.getElementById("volume").textContent = data.volume_mm3 || validation.volume_mm3 ? `${data.volume_mm3 || validation.volume_mm3} mm\u00b3` : "-";
      document.getElementById("stepPath").textContent = data.step_path || "-";
      document.getElementById("output").textContent = formatChineseResult(data);
    }

    function formatChineseResult(data) {
      const validation = data.validation || data;
      const lines = [
        `\u72b6\u6001\uff1a${data.ok ? "\u6210\u529f" : "\u5931\u8d25"}`,
        `\u6d41\u5f62\u68c0\u67e5\uff1a${validation.manifold ? "\u901a\u8fc7" : "\u672a\u901a\u8fc7"}`,
        `U \u578b\u94a9\u5e72\u6d89\u68c0\u67e5\uff1a${validation.u_hook_interference_free ? "\u901a\u8fc7" : "\u672a\u901a\u8fc7"}`,
        `\u4f53\u79ef\uff1a${data.volume_mm3 || validation.volume_mm3 || "-"} mm\u00b3`,
        `\u5b9e\u4f53\u6570\u91cf\uff1a${validation.solid_count || "-"}`,
        `STEP \u6587\u4ef6\uff1a${data.step_path || "\u672a\u4fdd\u5b58"}`
      ];
      if (validation.bbox_mm) {
        lines.push(`\u5305\u56f4\u76d2\uff1a${validation.bbox_mm.size.join(" x ")} mm`);
      }
      if (validation.errors && validation.errors.length) {
        lines.push(`\u9519\u8bef\uff1a${validation.errors.join("\uff1b")}`);
      }
      if (validation.warnings && validation.warnings.length) {
        lines.push(`\u63d0\u9192\uff1a${validation.warnings.join("\uff1b")}`);
      }
      if (data.error) {
        lines.push(`\u5931\u8d25\u539f\u56e0\uff1a${data.error}`);
      }
      return lines.join("\n");
    }

    document.getElementById("generateBtn").addEventListener("click", async () => {
      const data = await callApi("/api/generate", {...params(), save_step: document.getElementById("saveStep").checked});
      showResult(data);
    });
    document.getElementById("validateBtn").addEventListener("click", async () => {
      const data = await callApi("/api/validate", params());
      showResult(data);
    });
    document.getElementById("resetBtn").addEventListener("click", () => {
      for (const [name, value] of Object.entries(defaults)) {
        document.getElementById(name).value = value;
        if (labels[name]) {
          document.getElementById(`${name}_range`).value = value;
        }
      }
      updatePreview();
    });

    renderFields();
  </script>
</body>
</html>
"""


class ZBracketWebHandler(BaseHTTPRequestHandler):
    """Serve the static UI and small JSON endpoints."""

    server_version = "ZBracketWeb/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._send_text(HTTPStatus.OK, HTML, "text/html; charset=utf-8")
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/generate":
                result = generate_z_bracket(**payload)
                self._send_json(HTTPStatus.OK, result)
                return
            if path == "/api/validate":
                result = validate_design(**payload)
                self._send_json(HTTPStatus.OK, result)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _send_text(self, status: HTTPStatus, text: str, content_type: str) -> None:
        encoded = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status: HTTPStatus, data: dict[str, Any]) -> None:
        encoded = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ZBracketWebHandler)
    print(f"Z bracket web UI: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
