import atexit
import os
import subprocess
import threading
from flask import Flask, jsonify, render_template_string, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXE_PATH = os.path.join(BASE_DIR, "autocomplete_engine.exe")
DATASET_PATH = os.path.join(BASE_DIR, "dataset.txt")

app = Flask(__name__)


class CppEngineBridge:
    def __init__(self, exe_path: str):
        if not os.path.exists(exe_path):
            raise FileNotFoundError(f"Compiled engine not found at: {exe_path}")
        self.proc = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.lock = threading.Lock()

    def send_command(self, cmd_line: str) -> str:
        with self.lock:
            if self.proc.poll() is not None:
                raise RuntimeError("C++ engine process exited unexpectedly.")
            self.proc.stdin.write(cmd_line + "\n")
            self.proc.stdin.flush()
            resp = self.proc.stdout.readline()
            return resp.strip()

    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.stdin.write("QUIT\n")
                self.proc.stdin.flush()
                self.proc.terminate()
        except Exception:
            pass


bridge = CppEngineBridge(EXE_PATH)
atexit.register(bridge.close)


def load_dataset(filepath: str) -> int:
    if not os.path.exists(filepath):
        return 0
    loaded = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line or "\t" not in line:
                continue
            w_str, word = line.split("\t", 1)
            try:
                weight = int(w_str.strip())
            except ValueError:
                weight = 1
            word = word.strip()
            if word:
                bridge.send_command(f"INSERT {weight} {word}")
                loaded += 1
    return loaded


LOADED_COUNT = load_dataset(DATASET_PATH)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DSA2-P011 Search Autocomplete Engine</title>
  <style>
    body {
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      margin: 0;
      padding: 24px;
    }
    .container {
      max-width: 1080px;
      margin: 0 auto;
      display: grid;
      gap: 18px;
    }
    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 18px;
    }
    h1 { margin: 0 0 6px; font-size: 1.4rem; color: #f8fafc; }
    .sub { color: #94a3b8; font-size: 0.9rem; margin-bottom: 14px; }
    .stats { display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.88rem; }
    .pill {
      background: #0f172a;
      border: 1px solid #334155;
      padding: 6px 12px;
      border-radius: 999px;
      color: #38bdf8;
      font-weight: 600;
    }
    .search-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }
    input, select, button {
      background: #0f172a;
      color: #f8fafc;
      border: 1px solid #475569;
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.95rem;
    }
    input.search-box { flex: 1; min-width: 240px; }
    button {
      background: #0284c7;
      border-color: #0284c7;
      cursor: pointer;
      font-weight: 600;
    }
    button:hover { background: #0369a1; }
    button.secondary { background: #334155; border-color: #475569; }
    button.danger { background: #b91c1c; border-color: #b91c1c; }
    .grid-2 {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 18px;
    }
    @media (max-width: 820px) { .grid-2 { grid-template-columns: 1fr; } }
    .results-list {
      list-style: none;
      padding: 0;
      margin: 10px 0 0;
      max-height: 340px;
      overflow-y: auto;
    }
    .result-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 12px;
      border-bottom: 1px solid #334155;
      font-size: 0.92rem;
    }
    .weight { color: #34d399; font-family: monospace; }
    .path-wrap {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
    }
    .node-box {
      background: #0f172a;
      border: 1px solid #38bdf8;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.82rem;
      min-width: 72px;
    }
    .node-box.end { border-color: #34d399; }
    .node-box.fail { border-color: #f87171; color: #fca5a5; }
    .arrow { color: #94a3b8; font-weight: bold; }
    .branches {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }
    .branch-chip {
      background: #0f172a;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 0.8rem;
      font-family: monospace;
    }
    .crud-form {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .status-msg { font-size: 0.85rem; color: #38bdf8; min-height: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>DSA2-P011 Search Autocomplete Engine</h1>
      <div class="sub">C++ Trie + Min-Heap Top-K Engine with Python Interface</div>
      <div class="stats">
        <span class="pill" id="statRecords">Records Loaded: {{ loaded_count }}</span>
        <span class="pill" id="statNodes">Trie Nodes: -</span>
        <span class="pill" id="statMatches">Prefix Matches: 0</span>
      </div>
    </div>

    <div class="card">
      <div class="search-row">
        <input id="prefixInput" class="search-box" type="text" placeholder="Type a prefix (e.g., app, aarav, data)..." oninput="runSearch()" />
        <select id="modeSelect" onchange="runSearch()">
          <option value="topk">Top-K Ranked</option>
          <option value="all">All Matches</option>
        </select>
        <input id="kInput" type="number" min="1" max="200" value="10" style="width: 78px;" onchange="runSearch()" title="K value" />
        <button class="secondary" onclick="runSearch()">Search</button>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <strong>Suggestions</strong>
        <ul id="resultsList" class="results-list"></ul>
      </div>

      <div class="card">
        <strong>Prefix Traversal &amp; Subtree Branches</strong>
        <div id="traversalPath" class="path-wrap"></div>
        <div style="margin-top: 14px; font-size: 0.85rem; color: #94a3b8;">Next Characters at Current Prefix Node:</div>
        <div id="branchList" class="branches"></div>
      </div>
    </div>

    <div class="card">
      <strong>Dynamic CRUD Operations (Insert / Update / Delete)</strong>
      <div class="sub" style="margin-bottom: 10px;">Changes apply directly to the live C++ Trie.</div>

      <div class="crud-form">
        <input id="insWord" type="text" placeholder="Word / contact to insert" />
        <input id="insWeight" type="number" min="1" value="85" style="width: 90px;" />
        <button onclick="doInsert()">Insert</button>
      </div>

      <div class="crud-form">
        <input id="updWord" type="text" placeholder="Existing word to update" />
        <input id="updWeight" type="number" min="0" value="95" style="width: 90px;" />
        <button class="secondary" onclick="doUpdate()">Update Weight</button>
      </div>

      <div class="crud-form">
        <input id="delWord" type="text" placeholder="Word to delete (prunes dead nodes)" />
        <button class="danger" onclick="doDelete()">Delete</button>
      </div>

      <div id="crudStatus" class="status-msg"></div>
    </div>
  </div>

  <script>
    async function runSearch() {
      const prefix = document.getElementById("prefixInput").value;
      const mode = document.getElementById("modeSelect").value;
      const k = document.getElementById("kInput").value || 10;

      const params = new URLSearchParams({ prefix, mode, k });
      const res = await fetch(`/api/search?${params.toString()}`);
      const data = await res.json();

      document.getElementById("statRecords").textContent = `Records in Trie: ${data.totalRecords}`;
      document.getElementById("statNodes").textContent = `Trie Nodes: ${data.totalNodes}`;
      document.getElementById("statMatches").textContent = `Total Prefix Matches: ${data.totalMatches}`;

      // Render Traversal Path
      const pathEl = document.getElementById("traversalPath");
      pathEl.innerHTML = "";
      (data.traversal || []).forEach((step, idx) => {
        if (idx > 0) {
          const arr = document.createElement("span");
          arr.className = "arrow";
          arr.textContent = "->";
          pathEl.appendChild(arr);
        }
        const box = document.createElement("div");
        box.className = "node-box" + (step.isEnd ? " end" : "");
        box.innerHTML = `<div><strong>${step.node}</strong></div><div>pass: ${step.passCount}</div><div>ch: ${step.children}</div>`;
        pathEl.appendChild(box);
      });

      if (!data.found && data.failedAt) {
        const arr = document.createElement("span");
        arr.className = "arrow";
        arr.textContent = "->";
        pathEl.appendChild(arr);
        const failBox = document.createElement("div");
        failBox.className = "node-box fail";
        failBox.textContent = `Miss '${data.failedAt}'`;
        pathEl.appendChild(failBox);
      }

      // Render Next Branches
      const branchEl = document.getElementById("branchList");
      branchEl.innerHTML = "";
      (data.branches || []).slice(0, 24).forEach((b) => {
        const chip = document.createElement("span");
        chip.className = "branch-chip";
        chip.textContent = `'${b.char}' (pass:${b.passCount}${b.isEnd ? ", END" : ""})`;
        branchEl.appendChild(chip);
      });

      // Render Suggestions
      const listEl = document.getElementById("resultsList");
      listEl.innerHTML = "";
      if (!prefix.trim()) {
        listEl.innerHTML = `<li class="result-item"><span style="color:#94a3b8;">Type a prefix above to search across ${data.totalRecords} entries.</span></li>`;
        return;
      }
      if (!data.found || data.results.length === 0) {
        listEl.innerHTML = `<li class="result-item"><span style="color:#f87171;">No matches found for "${prefix}".</span></li>`;
        return;
      }
      data.results.forEach((item, i) => {
        const li = document.createElement("li");
        li.className = "result-item";
        li.innerHTML = `<span><strong>#${i + 1}</strong> ${item.word}</span><span class="weight">w: ${item.weight}</span>`;
        listEl.appendChild(li);
      });
    }

    async function doInsert() {
      const word = document.getElementById("insWord").value.trim();
      const weight = document.getElementById("insWeight").value || 1;
      if (!word) return;
      const res = await fetch("/api/insert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word, weight: Number(weight) })
      });
      const data = await res.json();
      document.getElementById("crudStatus").textContent = data.ok ? `Inserted/updated "${word}" (weight ${weight}).` : "Insert failed.";
      runSearch();
    }

    async function doUpdate() {
      const word = document.getElementById("updWord").value.trim();
      const weight = document.getElementById("updWeight").value || 0;
      if (!word) return;
      const res = await fetch("/api/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word, weight: Number(weight) })
      });
      const data = await res.json();
      document.getElementById("crudStatus").textContent = data.ok ? `Updated "${word}" weight to ${weight}.` : `"${word}" not found.`;
      runSearch();
    }

    async function doDelete() {
      const word = document.getElementById("delWord").value.trim();
      if (!word) return;
      const res = await fetch("/api/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word })
      });
      const data = await res.json();
      document.getElementById("crudStatus").textContent = data.ok
        ? `Deleted "${word}" (pruned ${data.prunedNodes ?? 0} unused Trie nodes).`
        : `"${word}" not found.`;
      runSearch();
    }

    runSearch();
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE, loaded_count=LOADED_COUNT)


@app.route("/api/search")
def api_search():
    prefix = request.args.get("prefix", "")
    mode = request.args.get("mode", "topk")
    try:
        k = int(request.args.get("k", "10"))
    except ValueError:
        k = 10
    raw_json = bridge.send_command(f"SEARCH {mode} {k} {prefix}")
    return raw_json, 200, {"Content-Type": "application/json"}


@app.route("/api/insert", methods=["POST"])
def api_insert():
    body = request.get_json(force=True)
    word = str(body.get("word", "")).strip()
    weight = int(body.get("weight", 1))
    raw_json = bridge.send_command(f"INSERT {weight} {word}")
    return raw_json, 200, {"Content-Type": "application/json"}


@app.route("/api/update", methods=["POST"])
def api_update():
    body = request.get_json(force=True)
    word = str(body.get("word", "")).strip()
    weight = int(body.get("weight", 0))
    raw_json = bridge.send_command(f"UPDATE {weight} {word}")
    return raw_json, 200, {"Content-Type": "application/json"}


@app.route("/api/delete", methods=["POST"])
def api_delete():
    body = request.get_json(force=True)
    word = str(body.get("word", "")).strip()
    raw_json = bridge.send_command(f"DELETE {word}")
    return raw_json, 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)