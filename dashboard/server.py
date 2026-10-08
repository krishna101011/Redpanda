#!/usr/bin/env python3

import json
import os
import shutil
import socket
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765


def get_cpu():
    try:
        load = os.getloadavg()[0]
        cpus = os.cpu_count() or 1
        return min(100, round((load / cpus) * 100))
    except Exception:
        return 0


def get_memory():
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, value = line.split(":", 1)
                mem[key] = int(value.strip().split()[0])

        total = mem["MemTotal"]
        available = mem["MemAvailable"]
        used = total - available

        return {
            "used": round(used / 1024 / 1024, 1),
            "total": round(total / 1024 / 1024, 1),
            "percent": round((used / total) * 100),
        }
    except Exception:
        return {"used": 0, "total": 0, "percent": 0}


def get_disk():
    try:
        total, used, free = shutil.disk_usage(os.path.expanduser("~"))
        return {
            "used": round(used / 1024**3, 1),
            "total": round(total / 1024**3, 1),
            "percent": round((used / total) * 100),
        }
    except Exception:
        return {"used": 0, "total": 0, "percent": 0}


def get_uptime():
    try:
        with open("/proc/uptime") as f:
            seconds = int(float(f.read().split()[0]))

        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes = seconds // 60

        parts = []

        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")

        return " ".join(parts)
    except Exception:
        return "Unknown"


def get_network():
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "GENERAL.STATE", "device", "show"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if "connected" in result.stdout.lower():
            return True

        result = subprocess.run(
            ["ip", "route", "get", "1.1.1.1"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        return result.returncode == 0

    except Exception:
        return False


def get_workspace():
    try:
        names = subprocess.check_output(
            ["gsettings", "get",
             "org.cinnamon.desktop.wm.preferences",
             "workspace-names"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        return names

    except Exception:
        return "MAIN / STUDY / BUILD / LAB"


def get_hostname():
    return socket.gethostname()


def get_data():
    memory = get_memory()
    disk = get_disk()

    return {
        "cpu": get_cpu(),
        "memory": memory,
        "disk": disk,
        "network": get_network(),
        "uptime": get_uptime(),
        "hostname": get_hostname(),
        "workspace": get_workspace(),
        "time": time.strftime("%H:%M:%S"),
    }


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>RedPanda Dashboard</title>

<style>
:root {
    --base: #1e1e2e;
    --mantle: #181825;
    --crust: #11111b;
    --surface: #313244;
    --surface2: #45475a;
    --text: #cdd6f4;
    --subtext: #a6adc8;
    --pink: #f38ba8;
    --mauve: #cba6f7;
    --blue: #89b4fa;
    --green: #a6e3a1;
    --yellow: #f9e2af;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    background:
        radial-gradient(circle at 20% 10%, rgba(243,139,168,.08), transparent 30%),
        radial-gradient(circle at 80% 80%, rgba(203,166,247,.07), transparent 30%),
        var(--crust);
    color: var(--text);
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.wrapper {
    width: min(1100px, calc(100% - 40px));
    margin: 0 auto;
    padding: 42px 0;
}

.header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 15px;
}

.panda {
    width: 54px;
    height: 54px;
    display: grid;
    place-items: center;
    border-radius: 17px;
    background: linear-gradient(135deg, #f38ba8, #cba6f7);
    color: #11111b;
    font-size: 28px;
    box-shadow: 0 10px 35px rgba(243,139,168,.18);
}

.title {
    font-size: 27px;
    font-weight: 750;
    letter-spacing: .3px;
}

.subtitle {
    margin-top: 3px;
    color: var(--subtext);
    font-size: 13px;
}

.clock {
    color: var(--subtext);
    font-variant-numeric: tabular-nums;
    font-size: 14px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

.card {
    background: rgba(30,30,46,.78);
    border: 1px solid rgba(205,214,244,.07);
    border-radius: 20px;
    padding: 21px;
    box-shadow: 0 15px 45px rgba(0,0,0,.20);
    backdrop-filter: blur(12px);
}

.card.wide {
    grid-column: span 2;
}

.card.full {
    grid-column: 1 / -1;
}

.label {
    color: var(--subtext);
    text-transform: uppercase;
    letter-spacing: 1.4px;
    font-size: 10px;
    font-weight: 700;
    margin-bottom: 12px;
}

.metric {
    display: flex;
    justify-content: space-between;
    align-items: end;
}

.value {
    font-size: 27px;
    font-weight: 700;
}

.percent {
    color: var(--subtext);
    font-size: 12px;
}

.bar {
    height: 7px;
    margin-top: 13px;
    border-radius: 99px;
    overflow: hidden;
    background: var(--surface);
}

.fill {
    height: 100%;
    width: 0%;
    border-radius: inherit;
    transition: width .5s ease;
}

.cpu { background: var(--pink); }
.ram { background: var(--mauve); }
.disk { background: var(--blue); }

.network {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 650;
}

.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 14px rgba(166,227,161,.45);
}

.dot.off {
    background: var(--pink);
    box-shadow: 0 0 14px rgba(243,139,168,.35);
}

.info {
    display: flex;
    justify-content: space-between;
    padding: 9px 0;
    border-bottom: 1px solid rgba(205,214,244,.06);
}

.info:last-child {
    border-bottom: 0;
}

.info span:first-child {
    color: var(--subtext);
}

.workspace {
    font-size: 17px;
    color: var(--blue);
    margin-top: 4px;
}

.actions {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}

button {
    border: 1px solid rgba(205,214,244,.08);
    background: var(--surface);
    color: var(--text);
    padding: 13px 10px;
    border-radius: 13px;
    cursor: pointer;
    font-weight: 650;
    transition: .18s ease;
}

button:hover {
    transform: translateY(-2px);
    background: var(--surface2);
    border-color: rgba(243,139,168,.35);
}

.footer {
    margin-top: 24px;
    color: #6c7086;
    text-align: center;
    font-size: 11px;
}

@media (max-width: 800px) {
    .grid {
        grid-template-columns: 1fr;
    }

    .card.wide,
    .card.full {
        grid-column: auto;
    }

    .actions {
        grid-template-columns: repeat(2, 1fr);
    }

    .header {
        align-items: flex-start;
        gap: 15px;
        flex-direction: column;
    }
}
</style>
</head>

<body>

<div class="wrapper">

    <div class="header">

        <div class="brand">
            <div class="panda">🐼</div>

            <div>
                <div class="title">REDPANDA</div>
                <div class="subtitle">
                    Personal Linux command center
                </div>
            </div>
        </div>

        <div class="clock" id="clock">--:--:--</div>

    </div>

    <div class="grid">

        <div class="card">

            <div class="label">CPU</div>

            <div class="metric">
                <div class="value" id="cpu">--%</div>
                <div class="percent">usage</div>
            </div>

            <div class="bar">
                <div class="fill cpu" id="cpuBar"></div>
            </div>

        </div>


        <div class="card">

            <div class="label">Memory</div>

            <div class="metric">
                <div class="value" id="ram">--</div>
                <div class="percent" id="ramPercent">--%</div>
            </div>

            <div class="bar">
                <div class="fill ram" id="ramBar"></div>
            </div>

        </div>


        <div class="card">

            <div class="label">Disk</div>

            <div class="metric">
                <div class="value" id="disk">--</div>
                <div class="percent" id="diskPercent">--%</div>
            </div>

            <div class="bar">
                <div class="fill disk" id="diskBar"></div>
            </div>

        </div>


        <div class="card">

            <div class="label">Network</div>

            <div class="network">
                <div class="dot" id="networkDot"></div>
                <span id="networkText">Checking...</span>
            </div>

        </div>


        <div class="card">

            <div class="label">Workspace</div>

            <div class="workspace" id="workspace">
                MAIN
            </div>

        </div>


        <div class="card">

            <div class="label">Uptime</div>

            <div class="value" id="uptime">
                --
            </div>

        </div>


        <div class="card wide">

            <div class="label">System</div>

            <div class="info">
                <span>Host</span>
                <span id="hostname">--</span>
            </div>

            <div class="info">
                <span>Dashboard</span>
                <span>RedPanda v1</span>
            </div>

            <div class="info">
                <span>Refresh</span>
                <span>2 seconds</span>
            </div>

        </div>


        <div class="card">

            <div class="label">Quick Access</div>

            <div class="actions">

                <button onclick="openApp('terminal')">
                    Terminal
                </button>

                <button onclick="openApp('files')">
                    Files
                </button>

                <button onclick="openApp('code')">
                    VS Code
                </button>

                <button onclick="openApp('monitor')">
                    Monitor
                </button>

            </div>

        </div>


        <div class="card full">

            <div class="label">RedPanda</div>

            <div style="color:var(--subtext); line-height:1.7;">
                MAIN • STUDY • BUILD • LAB
                <br>
                Your system. Your workspace. Your command center.
            </div>

        </div>

    </div>

    <div class="footer">
        RedPanda-System • Local dashboard • 127.0.0.1
    </div>

</div>


<script>

function updateClock() {
    document.getElementById("clock").textContent =
        new Date().toLocaleTimeString();
}

function setBar(id, value) {
    document.getElementById(id).style.width =
        Math.max(0, Math.min(100, value)) + "%";
}

async function updateData() {

    try {

        const response = await fetch("/api/status");
        const data = await response.json();

        document.getElementById("cpu").textContent =
            data.cpu + "%";

        setBar("cpuBar", data.cpu);


        document.getElementById("ram").textContent =
            data.memory.used + " / " +
            data.memory.total + " GB";

        document.getElementById("ramPercent").textContent =
            data.memory.percent + "%";

        setBar("ramBar", data.memory.percent);


        document.getElementById("disk").textContent =
            data.disk.used + " / " +
            data.disk.total + " GB";

        document.getElementById("diskPercent").textContent =
            data.disk.percent + "%";

        setBar("diskBar", data.disk.percent);


        const dot =
            document.getElementById("networkDot");

        const networkText =
            document.getElementById("networkText");

        if (data.network) {
            dot.classList.remove("off");
            networkText.textContent = "Connected";
        } else {
            dot.classList.add("off");
            networkText.textContent = "Offline";
        }


        document.getElementById("uptime").textContent =
            data.uptime;

        document.getElementById("hostname").textContent =
            data.hostname;

        document.getElementById("workspace").textContent =
            data.workspace;

    } catch (error) {
        console.error(error);
    }
}


async function openApp(app) {

    await fetch("/api/open/" + app, {
        method: "POST"
    });

}


updateClock();
setInterval(updateClock, 1000);

updateData();
setInterval(updateData, 2000);

</script>

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        payload = json.dumps(data).encode()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()

        self.wfile.write(payload)

    def do_GET(self):

        if self.path == "/":
            payload = HTML.encode()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()

            self.wfile.write(payload)
            return

        if self.path == "/api/status":
            self.send_json(get_data())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):

        if self.path.startswith("/api/open/"):

            app = self.path.split("/")[-1]

            commands = {
                "terminal": ["gnome-terminal"],
                "files": ["nemo"],
                "code": ["code"],
                "monitor": ["gnome-system-monitor"],
            }

            command = commands.get(app)

            if command:
                try:
                    subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.send_json({"ok": True})
                except Exception as exc:
                    self.send_json(
                        {"ok": False, "error": str(exc)},
                        500
                    )
            else:
                self.send_json(
                    {"ok": False, "error": "Unknown application"},
                    404
                )

            return

        self.send_response(404)
        self.end_headers()


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)

    print()
    print("🐼 RedPanda Dashboard")
    print("----------------------")
    print(f"http://{HOST}:{PORT}")
    print()
    print("Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping RedPanda Dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
