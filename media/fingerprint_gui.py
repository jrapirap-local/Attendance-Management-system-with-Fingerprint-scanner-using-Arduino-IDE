import serial, string, random, json, threading, queue, requests, time, tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from serial.tools import list_ports

# -------------------- CONFIG --------------------
BAUD_RATE = 115200

DJANGO_ENROLL_URL = "http://127.0.0.1:8000/api/fingerprint/enroll/"
DJANGO_VERIFY_URL = "http://127.0.0.1:8000/api/fingerprint/verify/"
DJANGO_COMMAND_URL = "http://127.0.0.1:8000/api/fingerprint/commands/"
DJANGO_LOG_URL = "http://127.0.0.1:8000/api/fingerprint/logs/"

device_ready = False
link_id = ""
ser = None

log_queue = queue.Queue()

# -------------------- ROOT WINDOW --------------------
root = tk.Tk()
root.title("Fingerprint Device Manager")
root.geometry("540x460")
root.resizable(False, False)
root.configure(bg="#f5f5f5")

# -------------------- LOG AREA --------------------
log_area = scrolledtext.ScrolledText(root, width=65, height=18, state='disabled',
                                     font=("Segoe UI", 10), bg="#ffffff", fg="#333333")
log_area.pack(pady=10, padx=10)

# -------------------- THREAD SAFE UI --------------------
def safe_gui(callback, *args):
    root.after(0, lambda: callback(*args))

def _append_log(msg):
    log_area.configure(state='normal')
    log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {msg}\n")
    log_area.see(tk.END)
    log_area.configure(state='disabled')

def safe_log(msg):
    safe_gui(_append_log, msg)

# -------------------- STATUS UI --------------------
status_frame = tk.Frame(root, bg="#f5f5f5")
status_frame.pack(pady=5, fill="x", padx=10)

status_canvas = tk.Canvas(status_frame, width=16, height=16, highlightthickness=0, bg="#f5f5f5")
status_dot = status_canvas.create_oval(2, 2, 14, 14, fill="#d9534f")
status_canvas.grid(row=0, column=0, padx=5)

status_label = tk.Label(status_frame, text="Disconnected", font=("Segoe UI", 10), bg="#f5f5f5")
status_label.grid(row=0, column=1)

device_label = tk.Label(status_frame, text="Device: -", font=("Segoe UI", 9), bg="#f5f5f5")
device_label.grid(row=0, column=2, padx=10)

def update_status(connected=False, device_name=""):
    status_canvas.itemconfig(status_dot, fill="#5cb85c" if connected else "#d9534f")
    status_label.config(text="Connected" if connected else "Disconnected")
    device_label.config(text=f"Device: {device_name}" if connected else "Device: -")

def safe_update_status(*args):
    safe_gui(update_status, *args)

# -------------------- SERIAL UI --------------------
top_frame = tk.Frame(root, bg="#f5f5f5")
top_frame.pack(pady=5)

tk.Label(top_frame, text="Serial Port:", bg="#f5f5f5").grid(row=0, column=0)

port_var = tk.StringVar()
port_dropdown = ttk.Combobox(top_frame, textvariable=port_var, width=20, state="readonly")
port_dropdown.grid(row=0, column=1)

def scan_ports():
    return [p.device for p in list_ports.comports()]

def live_port_scanner():
    last = []
    while True:
        ports = scan_ports()
        if ports != last:
            safe_gui(port_dropdown.configure, values=ports)
            if ports and not port_var.get():
                port_var.set(ports[0])
            last = ports
        time.sleep(3)

# -------------------- SERIAL INIT --------------------
def initialize_serial():
    global ser, device_ready

    port = port_var.get()
    if not port:
        messagebox.showwarning("Warning", "Select port")
        return

    try:
        if ser and ser.is_open:
            ser.close()

        ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        ser.reset_input_buffer()

        device_ready = False
        safe_update_status(True, port)
        safe_log(f"Connected to {port}")

    except Exception as e:
        safe_update_status(False)
        messagebox.showerror("Error", str(e))

init_btn = tk.Button(top_frame, text="Initialize", command=initialize_serial)
init_btn.grid(row=0, column=2, padx=5)

# -------------------- LOGGING --------------------
def send_log(message, log_type="info", endpoint=None, extra=None):
    payload = {
        "message": message,
        "type": log_type,
        "timestamp": time.time()
    }
    if extra:
        payload.update(extra)

    log_queue.put({
        "url": endpoint or DJANGO_LOG_URL,
        "payload": payload
    })

def django_worker():
    while True:
        task = log_queue.get()
        if task is None:
            break

        for _ in range(3):
            try:
                requests.post(task["url"], json=task["payload"], timeout=5)
                break
            except:
                time.sleep(1)

        log_queue.task_done()

threading.Thread(target=django_worker, daemon=True).start()

# -------------------- SERIAL COMMAND --------------------
def send_command(cmd):
    if not ser or not ser.is_open:
        safe_log("Device not connected")
        return
    try:
        ser.write((cmd + "\n").encode())
        safe_log(f"Sent: {cmd}")
    except Exception as e:
        safe_log(str(e))

# -------------------- SERIAL READER --------------------
def process_serial_event(data):
    global link_id

    if "main" in data and "backup" in data:
        link_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        safe_log("Enrollment detected")

        send_log(
            "Enrollment",
            "json",
            DJANGO_ENROLL_URL,
            {
                "main": data["main"],
                "backup": data["backup"],
                "random_id": link_id
            }
        )

    elif "match_id" in data:
        try:
            match_id = int(data["match_id"])
            safe_log(f"Verify ID: {match_id}")

            send_log(
                "Verification",
                "json",
                DJANGO_VERIFY_URL,
                {"match_id": match_id}
            )
        except:
            safe_log("Invalid match_id")

    elif data.get("delete_all"):
        safe_log("All fingerprints deleted")
        send_log("DELETE_ALL", "status")

def read_serial():
    global device_ready

    while True:
        if not ser or not ser.is_open:
            safe_update_status(False)
            time.sleep(1)
            continue

        try:
            line = ser.readline().decode(errors='ignore').strip()
            if not line:
                time.sleep(0.05)
                continue

            if "READY" in line.upper():
                if not device_ready:
                    device_ready = True
                    safe_log("Device ready")
                    send_log("READY", "status")
                continue

            if line.startswith("{"):
                try:
                    process_serial_event(json.loads(line))
                except:
                    pass
            else:
                safe_log(line)

        except Exception as e:
            safe_log(f"Serial error: {e}")

# -------------------- COMMAND POLLING --------------------
def poll_commands():
    while True:
        if not device_ready:
            time.sleep(1)
            continue

        try:
            resp = requests.get(DJANGO_COMMAND_URL, timeout=3)
            if resp.status_code != 200:
                time.sleep(1)
                continue

            cmd = resp.json()
            if not cmd:
                time.sleep(1)
                continue

            action = cmd.get("cmd", "").upper()
            cmd_id = cmd.get("id")

            safe_log(f"CMD: {action}")

            if action == "ENROLL":
                send_command("ENROLL")
            elif action == "VERIFY":
                send_command("VERIFY")
            elif action == "DELETE_ALL":
                send_command("DELETE")

            requests.delete(f"{DJANGO_COMMAND_URL}{cmd_id}/", timeout=2)

        except Exception as e:
            safe_log(f"Poll error: {e}")

        time.sleep(1)

# -------------------- BUTTONS --------------------
btn_frame = tk.Frame(root, bg="#f5f5f5")
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Enroll", width=20, command=lambda: send_command("ENROLL")).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Verify", width=20, command=lambda: send_command("VERIFY")).grid(row=0, column=1, padx=5)

# -------------------- START THREADS --------------------
safe_update_status(False)

threading.Thread(target=read_serial, daemon=True).start()
threading.Thread(target=poll_commands, daemon=True).start()
threading.Thread(target=live_port_scanner, daemon=True).start()

root.mainloop()