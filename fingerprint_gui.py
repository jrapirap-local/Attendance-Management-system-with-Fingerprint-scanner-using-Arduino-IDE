import serial, string, random, json, threading, queue, requests, time, tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from serial.tools import list_ports

# -------------------- CONFIG --------------------
BAUD_RATE = 115200

DJANGO_ENROLL_URL = "http://127.0.0.1:8000/api/fingerprint/enroll/"
DJANGO_VERIFY_URL = "http://127.0.0.1:8000/api/fingerprint/verify/"
DJANGO_COMMAND_URL = "http://127.0.0.1:8000/api/fingerprint/commands/"
DJANGO_LOG_URL = "http://127.0.0.1:8000/api/fingerprint/set/logs/"

device_ready = False
link_id = ""
ser = None
polling_enabled = False

# -------------------- ROOT WINDOW --------------------
root = tk.Tk()
root.title("Fingerprint Device Manager")
root.geometry("540x560")
root.resizable(False, False)
root.configure(bg="#f5f5f5")

# -------------------- LOG AREA --------------------
log_area = scrolledtext.ScrolledText(root, width=65, height=18, state='disabled',
                                     font=("Segoe UI", 10), bg="#ffffff", fg="#333333", bd=1, relief="solid")
log_area.pack(pady=10, padx=10)

def log(msg, level="info", send_remote=True):
    # Update GUI log
    log_area.configure(state='normal')
    log_area.insert(tk.END, msg + "\n")
    log_area.see(tk.END)
    log_area.configure(state='disabled')

    # # Prevent recursion
    # if send_remote:
    #     send_to_django(msg, extra_data={"type": level})

# -------------------- SERIAL PORT UI --------------------
top_frame = tk.Frame(root, bg="#f5f5f5")
top_frame.pack(pady=5)

tk.Label(top_frame, text="Serial Port:", font=("Segoe UI", 10), bg="#f5f5f5").grid(row=0, column=0, padx=5)

port_var = tk.StringVar()
port_dropdown = ttk.Combobox(top_frame, textvariable=port_var, width=20, state="readonly", font=("Segoe UI", 10))
port_dropdown.grid(row=0, column=1, padx=5)

init_btn = tk.Button(top_frame, text="Initialize", width=12, font=("Segoe UI", 10, "bold"),
                     bg="#4a90e2", fg="white", bd=0, relief="flat", activebackground="#357ABD",
                     command=lambda: initialize_serial())
init_btn.grid(row=0, column=2, padx=5)

# -------------------- STATUS BAR --------------------
status_frame = tk.Frame(root, bg="#f5f5f5")
status_frame.pack(pady=5, fill="x", padx=10)

status_canvas = tk.Canvas(status_frame, width=16, height=16, highlightthickness=0, bg="#f5f5f5")
status_dot = status_canvas.create_oval(2, 2, 14, 14, fill="#d9534f")  # red by default
status_canvas.grid(row=0, column=0, padx=5)

status_label = tk.Label(status_frame, text="Disconnected", font=("Segoe UI", 10), bg="#f5f5f5")
status_label.grid(row=0, column=1, padx=5)

device_label = tk.Label(status_frame, text="Device: -", font=("Segoe UI", 9), bg="#f5f5f5")
device_label.grid(row=0, column=2, padx=10)

def update_status(connected=False, device_name=""):
    if connected:
        status_canvas.itemconfig(status_dot, fill="#5cb85c")  # green
        status_label.config(text="Connected")
        device_label.config(text=f"Device: {device_name}")
    else:
        status_canvas.itemconfig(status_dot, fill="#d9534f")  # red
        status_label.config(text="Disconnected")
        device_label.config(text="Device: -")

# -------------------- PORT SCANNING --------------------
def scan_ports():
    return [(p.device, p.description) for p in list_ports.comports()]

def live_port_scanner():
    last_ports = []

    while True:
        try:
            ports = scan_ports()
            port_names = [p[0] for p in ports]

            if ports != last_ports:
                port_dropdown["values"] = port_names
                if port_names and not port_var.get():
                    port_var.set(port_names[0])
                last_ports = ports

        except Exception as e:
            log(f"Port scan error: {e}")

        time.sleep(2)

# -------------------- SERIAL INIT --------------------
def delete_all_on_start():
    global polling_enabled

    # Wait for device ready via serial messages only
    while not device_ready:
        set_progress_text("Waiting for device...")
        time.sleep(0.5)

    time.sleep(2)
    set_progress_text("Finalizing setup...")
    time.sleep(0.5)

    # ✅ Keep polling off initially
    polling_enabled = True

    hide_progress()
    set_controls_enabled(True)
    log("=============== Device ready. Polling is On. ===============")
    send_command("VERIFY")

def initialize_serial():
    global ser, device_ready, polling_enabled

    port = port_var.get()
    if not port:
        messagebox.showwarning("Input Required", "Please select a serial port")
        return

    try:
        if ser and ser.is_open:
            ser.close()

        ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        ser.reset_input_buffer()

        device_name = next((p.description for p in list_ports.comports() if p.device == port), "")
        device_ready = True
        polling_enabled = False  # ✅ DISABLE automatic polling on init

        update_status(True, device_name)
        log(f"Connected to {port} ({device_name})")

        # 🔥 SHOW PROGRESS UI
        show_progress("Initializing device...")
        set_controls_enabled(False)

        # ✅ Remove startup polling check
        # startup_check()  <-- removed

        threading.Thread(target=delete_all_on_start, daemon=True).start()

    except Exception as e:
        update_status(False)
        hide_progress()
        set_controls_enabled(True)
        messagebox.showerror("Serial Error", f"Cannot open {port}: {e}")

# -------------------- COMMANDS --------------------
def send_command(cmd):
    if not device_ready or not ser or not ser.is_open:
        log("Device not ready or not connected.")
        return
    try:
        ser.write((cmd + "\n").encode())
        log(f"Sent: {cmd}")
    except Exception as e:
        log(f"Send failed: {e}")

# Thread-safe queue for Django logs
log_queue = queue.Queue()

def send_log_to_django(message, log_type="info", fingerprint_id=None, extra=None):
    payload = {
        "message": message,
        "type": log_type,
        "timestamp": time.time()
    }
    if fingerprint_id is not None:
        payload["fingerprint_id"] = fingerprint_id
    if extra and isinstance(extra, dict):
        payload.update(extra)

    try:
        resp = requests.post(DJANGO_LOG_URL, json=payload, timeout=3)
        if resp.status_code == 200:
            print("Log sent successfully:", payload)
        else:
            print("Failed to send log:", resp.status_code, resp.text)
    except requests.RequestException as e:
        print("Error sending log:", e)

def gui_log(msg):
    def append():
        log_area.configure(state='normal')
        log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {msg}\n")
        log_area.see(tk.END)
        log_area.configure(state='disabled')

    log_area.after(0, append)

def send_log(message, log_type="info", endpoint=None, extra_data=None):
    if extra_data is None:
        extra_data = {}

    payload = {
        "message": message,
        "type": log_type,
        "timestamp": time.time()
    }
    payload.update(extra_data)

    send_to_django_async(
        url=endpoint or DJANGO_LOG_URL,
        payload=payload,
        method="POST",
        log_success=f"Sent to Django: {message}",
        log_error=f"Failed sending: {message}"
    )

def send_to_django(message, endpoint=DJANGO_LOG_URL, extra_data=None, method="POST"):
    if not endpoint or not endpoint.startswith("http"):
        log(f"Invalid URL: {endpoint}")
        return

    gui_log(f"{message} sent to django as post")

    payload = {
        "message": message,
        "timestamp": time.time()
    }

    # Merge extra data if provided
    if extra_data and isinstance(extra_data, dict):
        payload.update(extra_data)

    send_to_django_async({
        "url": endpoint,
        "method": method,
        "payload": payload if method == "POST" else None,
        "log_success": f"Sent to Django: {message}",
        "log_error": "Failed sending to Django"
    })

def send_to_django_async(url, payload=None, method="POST", log_success=None, log_error=None):
    if not url:
        return
    log_queue.put({
        "url": url,
        "method": method.upper(),
        "payload": payload,
        "log_success": log_success,
        "log_error": log_error
    })

# -------------------- PROGRESS UI --------------------
def show_progress(message):
    def update():
        progress_label.config(text=message)
        progress_frame.pack(pady=5, fill="x", padx=10)
        progress_bar.start(10)
    root.after(0, update)

def hide_progress():
    def update():
        progress_bar.stop()
        progress_frame.pack_forget()
    root.after(0, update)

def set_progress_text(message):
    root.after(0, lambda: progress_label.config(text=message))

def set_controls_enabled(enabled):
    state = "normal" if enabled else "disabled"
    enroll_btn.config(state=state)
    verify_btn.config(state=state)
    reset_btn.config(state=state)  # ✅ add this
    init_btn.config(state=state)

progress_frame = tk.Frame(root, bg="#f5f5f5")
progress_frame.pack(pady=5, fill="x", padx=10)

progress_label = tk.Label(progress_frame, text="", font=("Segoe UI", 9), bg="#f5f5f5")
progress_label.pack(anchor="w")

progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
progress_bar.pack(fill="x", pady=3)
progress_bar.stop()
progress_frame.pack_forget()  # hidden by default

# -------------------- WORKER THREAD --------------------
def _django_worker():
    while True:
        task = log_queue.get()
        if task is None:  # stop signal
            break

        url = task.get("url")
        method = task.get("method", "POST")
        payload = task.get("payload")
        log_success = task.get("log_success")
        log_error = task.get("log_error", "Request failed")

        try:
            if method == "POST":
                resp = requests.post(url, json=payload, timeout=5)
            else:
                resp = requests.get(url, params=payload, timeout=5)

            # Log success
            if callable(log_success):
                log_success(resp)
            elif isinstance(log_success, str):
                gui_log(log_success)

        except requests.RequestException as e:
            gui_log(f"{log_error}: {e}")

        finally:
            log_queue.task_done()


# -------------------- SERIAL READER --------------------
def read_serial():
    global device_ready

    while True:
        if not ser or not ser.is_open:
            update_status(False)
            time.sleep(0.5)
            continue

        try:
            raw = ser.readline().decode('utf-8', errors='ignore').strip()
            if not raw:
                time.sleep(0.05)
                continue

            gui_log(raw)

            # ---------------- TRY JSON FIRST ----------------
            try:
                data = json.loads(raw)
                process_serial_event(data)
                continue
            except:
                pass

            # ---------------- FALLBACK: PLAIN TEXT ----------------
            send_to_django_async(
                url=DJANGO_LOG_URL,
                payload={
                    "event": "log",
                    "message": raw
                }
            )

            # ---------------- DEVICE READY ----------------
            if "READY" in raw.upper():
                if not device_ready:
                    device_ready = True
                    gui_log("Device ready")

        except Exception as e:
            gui_log(f"Serial error: {e}")

        time.sleep(0.05)

def process_serial_event(data):
    global link_id

    # ---------------- ENROLL ----------------
    if "main" in data and "backup" in data:
        link_id = generate_random_id()

        gui_log(f"Enroll success: main={data['main']} backup={data['backup']}")

        send_to_django_async(
            url=DJANGO_ENROLL_URL,
            payload={
                "main": data["main"],
                "backup": data["backup"],
                "extra": data.get("extra"),
                "random_id": link_id
            }
        )

    # ---------------- VERIFY ----------------
    elif "match_id" in data:
        send_to_django_async(
            url=DJANGO_VERIFY_URL,
            payload={
                "match_id": data["match_id"]
            }
        )

    # ---------------- LOG ----------------
    elif "log_msg" in data:
        send_to_django_async(
            url=DJANGO_LOG_URL,
            payload={
                "message": data["log_msg"],
                "type": data.get("type", "info")
            }
        )

    # ---------------- DELETE ----------------
    elif data.get("delete_all"):
        send_to_django_async(
            url=DJANGO_LOG_URL,
            payload={"event": "delete_all"}
        )

# -------------------- DJANGO COMMAND POLLING --------------------
def generate_random_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def poll_django_commands():
    global link_id, polling_enabled

    last_cmd_id = None  # ✅ ADD HERE (outside loop, so it remembers)

    while True:
        if not device_ready or not polling_enabled:
            time.sleep(1)
            continue

        try:
            resp = requests.get(DJANGO_COMMAND_URL, timeout=2)
            if resp.status_code != 200:
                time.sleep(1)
                continue

            commands = resp.json()
            if not commands:
                time.sleep(1)
                continue

            cmd = commands[0]
            cmd_id = cmd.get("id")
            action = cmd.get("cmd", "").upper()

            # ✅ PREVENT DUPLICATE EXECUTION
            if cmd_id == last_cmd_id:
                time.sleep(0.5)
                continue

            last_cmd_id = cmd_id  # ✅ UPDATE AFTER CHECK

            # ---------------- EXECUTE COMMAND ----------------
            link_id = generate_random_id()
            log(f"Request ID: {link_id}")

            if action == "ENROLL":
                send_command("ENROLL")

            elif action == "VERIFY":
                send_command("VERIFY")

            elif action == "DELETE_ALL":
                send_command("DELETE")

            # ---------------- DELETE COMMAND FROM DJANGO ----------------
            try:
                requests.delete(f"{DJANGO_COMMAND_URL}{cmd_id}/", timeout=2)
                log(f"Command {action} removed")
            except Exception as e:
                log(f"Delete failed: {e}")

        except Exception as e:
            log(f"Poll error: {e}")

        time.sleep(0.5)  # faster polling
        
# -------------------- STARTUP --------------------
def startup_check():
    global device_ready
    def check_loop():
        global device_ready
        while not device_ready:
            try:
                if ser and ser.is_open:
                    ser.write(b"TEST\n")
                    time.sleep(0.1)
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        device_ready = True
                        log(f"Fingerprint detected: {line}")
                        break
                    else: log("Scanner not responding...")
                else: log("Serial not open")
            except Exception as e:
                log(f"Detection error: {e}")
            time.sleep(2)
    threading.Thread(target=check_loop, daemon=True).start()

def confirm_reset():
    if messagebox.askyesno("Confirm Reset", "This will delete ALL fingerprints. Continue?"):
        send_command("DELETE")
        log("Delete all command sent.")

    reset_btn = tk.Button(
        btn_frame,
        text="Reset (Delete All)",
        command=confirm_reset,
        width=42
    )

# -------------------- BUTTONS --------------------
def enroll_action():
    global polling_enabled
    polling_enabled = False  # stop any polling while enrolling
    send_command("ENROLL")

def verify_action():
    global polling_enabled
    polling_enabled = False  # stop any polling while verifying
    send_command("VERIFY")
    
btn_frame = tk.Frame(root, bg="#f5f5f5")
btn_frame.pack(pady=10)

def style_button(btn):
    btn.configure(bg="#4a90e2", fg="white", bd=0, relief="flat", font=("Segoe UI", 10, "bold"),
                  activebackground="#357ABD", activeforeground="white")
    btn.bind("<Enter>", lambda e: btn.configure(bg="#357ABD"))
    btn.bind("<Leave>", lambda e: btn.configure(bg="#4a90e2"))



enroll_btn = tk.Button(btn_frame, text="Enroll", command=lambda: send_command("ENROLL"), width=20)
verify_btn = tk.Button(btn_frame, text="Verify", command=lambda: send_command("VERIFY"), width=20)
reset_btn = tk.Button(btn_frame, text="Reset", command=lambda: send_command("DELETE"), width=20)
style_button(enroll_btn)
style_button(verify_btn)
style_button(reset_btn)
enroll_btn.grid(row=0, column=0, padx=5)
verify_btn.grid(row=0, column=1, padx=5)
reset_btn.grid(row=1, column=0, columnspan=2, pady=8)

# -------------------- INIT THREADS --------------------
update_status(False)
threading.Thread(target=read_serial, daemon=True).start()
threading.Thread(target=poll_django_commands, daemon=True).start()
threading.Thread(target=live_port_scanner, daemon=True).start()
threading.Thread(target=_django_worker, daemon=True).start()

root.mainloop()