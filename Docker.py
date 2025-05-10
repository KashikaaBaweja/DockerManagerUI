import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import shutil

# --- Utility Function ---

def run_docker_command(command):
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT)
        return result.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output.decode('utf-8')}"

# --- Container Tab Functions ---

def view_containers():
    for row in container_tree.get_children():
        container_tree.delete(row)
    try:
        containers = subprocess.check_output([
            "docker", "ps", "-a", "--format", "{{.ID}}|{{.Image}}|{{.Status}}|{{.Names}}"
        ]).decode("utf-8")
        if not containers:
            messagebox.showwarning("No Containers", "No containers found.")
        else:
            for container in containers.strip().split("\n"):
                values = container.split("|")
                container_tree.insert("", "end", values=values)
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "Error fetching container list.")

def start_container():
    selection = container_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select a container to start.")
        return
    container_id = container_tree.item(selection[0])['values'][0]
    # messagebox.showinfo("Start", run_docker_command(["docker", "start","-a", container_id]))
    messagebox.showinfo("Start", f'started container  {container_id}')
    print(run_docker_command(["docker", "start","-a", container_id]))

    view_containers()

def stop_container():
    selection = container_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select a container to stop.")
        return
    container_id = container_tree.item(selection[0])['values'][0]
    messagebox.showinfo("Stop", run_docker_command(["docker", "stop", container_id]))
    view_containers()

def remove_container():
    selection = container_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select a container to remove.")
        return
    container_id = container_tree.item(selection[0])['values'][0]
    messagebox.showinfo("Remove", run_docker_command(["docker", "rm", container_id]))
    view_containers()

def view_logs():
    selection = container_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select a container to view logs.")
        return
    container_id = container_tree.item(selection[0])['values'][0]
    output = run_docker_command(["docker", "logs", container_id])
    log_window = tk.Toplevel(root)
    log_window.title(f"Logs - {container_id}")
    text = tk.Text(log_window, wrap="word", bg="#1e1e1e", fg="white")
    text.insert("1.0", output)
    text.pack(expand=True, fill="both")

def view_container_usage():
    selection = container_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select a container to view usage.")
        return

    container_id = container_tree.item(selection[0])['values'][0]
    usage_window = tk.Toplevel(root)
    usage_window.title(f"Usage - {container_id}")
    usage_window.geometry("850x500")

    fig, ax = plt.subplots(facecolor="#121212")
    cpu_data, mem_data = [], []
    sys_cpu_data, sys_mem_data = [], []
    x_data = []

    line_cpu, = ax.plot([], [], label="Container CPU %", color="cyan")
    line_mem, = ax.plot([], [], label="Container Mem %", color="magenta")
    line_sys_cpu, = ax.plot([], [], label="System CPU %", color="orange", linestyle="dashed")
    line_sys_mem, = ax.plot([], [], label="System Mem %", color="lime", linestyle="dashed")

    ax.set_facecolor("#1e1e1e")
    ax.set_title(f"Live Usage - {container_id}", color="white", fontsize=16)
    ax.tick_params(colors='white')
    ax.legend(loc="upper right", facecolor="#1e1e1e", edgecolor="white", labelcolor="white", fontsize=10)

    canvas = FigureCanvasTkAgg(fig, master=usage_window)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    def update(frame):
        try:
            stats = subprocess.check_output([
                "docker", "stats", "--no-stream", "--format", "{{.CPUPerc}};{{.MemPerc}}", container_id
            ]).decode().strip().replace('%', '')
            cpu_str, mem_str = stats.split(";")
            cpu, mem = float(cpu_str), float(mem_str)
        except:
            cpu, mem = 0.0, 0.0

        sys_cpu = psutil.cpu_percent()
        sys_mem = psutil.virtual_memory().percent

        if len(cpu_data) >= 60:
            for data_list in [cpu_data, mem_data, sys_cpu_data, sys_mem_data, x_data]:
                data_list.pop(0)

        cpu_data.append(cpu)
        mem_data.append(mem)
        sys_cpu_data.append(sys_cpu)
        sys_mem_data.append(sys_mem)
        x_data.append(len(x_data))

        line_cpu.set_data(x_data, cpu_data)
        line_mem.set_data(x_data, mem_data)
        line_sys_cpu.set_data(x_data, sys_cpu_data)
        line_sys_mem.set_data(x_data, sys_mem_data)

        ax.relim()
        ax.autoscale_view()
        return line_cpu, line_mem, line_sys_cpu, line_sys_mem

    ani = animation.FuncAnimation(fig, update, interval=1000, frames=60, cache_frame_data=False)
    canvas.draw()

# --- Image Tab Functions ---

def list_images():
    for row in image_tree.get_children():
        image_tree.delete(row)
    try:
        images = subprocess.check_output([
            "docker", "images", "--format", "{{.Repository}}|{{.Tag}}|{{.ID}}|{{.Size}}"
        ]).decode("utf-8")
        if not images:
            messagebox.showwarning("No Images", "No images found.")
        else:
            for image in images.strip().split("\n"):
                values = image.split("|")
                image_tree.insert("", "end", values=values)
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "Failed to fetch Docker images.")

def remove_image():
    selection = image_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select an image to remove.")
        return
    image_id = image_tree.item(selection[0])['values'][2]
    messagebox.showinfo("Remove Image", run_docker_command(["docker", "rmi", image_id]))
    list_images()

def run_image():
    selection = image_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select an image to run.")
        return
    image_name = image_tree.item(selection[0])['values'][0]
    try:
        subprocess.run(["docker", "run", "-d", image_name], check=True)
        messagebox.showinfo("Run Image", f"Image '{image_name}' is now running.")
        view_containers()
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "Failed to run the selected image.")

def run_image_interactive():
    selection = image_tree.selection()
    if not selection:
        messagebox.showerror("Error", "Please select an image to run in interactive mode.")
        return
    image_name = image_tree.item(selection[0])['values'][0]
    try:
        terminal = shutil.which("gnome-terminal") or shutil.which("x-terminal-emulator") or shutil.which("xterm")
        if not terminal:
            messagebox.showerror("Error", "No terminal emulator found (gnome-terminal, xterm, etc.).")
            return
        subprocess.Popen([terminal, "--", "docker", "run", "-it", image_name, "bash"])
        messagebox.showinfo("Interactive Run", f"Interactive session started for '{image_name}'.")
        view_containers()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to run the image interactively.\n{e}")

# --- GUI Setup ---

root = tk.Tk()
root.title("Docker Manager UI")
root.geometry("1050x800")
root.configure(bg="#121212")

style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#1e1e1e",
                rowheight=30, font=("Arial", 14))
style.configure("Treeview.Heading", font=("Arial", 16, "bold"))
style.map("Treeview", background=[("selected", "#3a3a3a")], foreground=[("selected", "dark grey")])
style.configure("TLabel", background="#121212", foreground="white", font=("Arial", 12))
style.configure("TFrame", background="#121212")
style.configure("TNotebook", background="#1e1e1e")
style.configure("TNotebook.Tab", background="#3a3a3a", foreground="white", font=("Arial", 14, "bold"))
style.configure("TButton", padding=10, font=("Arial", 12, "bold"))

tab_control = ttk.Notebook(root)

# --- Container Tab ---

container_tab = ttk.Frame(tab_control)
tab_control.add(container_tab, text='Containers')

container_tree = ttk.Treeview(container_tab, columns=("ID", "Image", "Status", "Name"), show="headings")
for col in ("ID", "Image", "Status", "Name"):
    container_tree.heading(col, text=col, anchor="w")
    container_tree.column(col, anchor="w", width=300)
container_tree.pack(expand=True, fill="both", padx=10, pady=10)

container_btn_frame = ttk.Frame(container_tab)
container_btn_frame.pack(side="bottom", pady=10)

ttk.Button(container_btn_frame, text="Start Container", command=start_container).pack(side="left", padx=6)
ttk.Button(container_btn_frame, text="Stop Container", command=stop_container).pack(side="left", padx=6)
ttk.Button(container_btn_frame, text="Remove Container", command=remove_container).pack(side="left", padx=6)
ttk.Button(container_btn_frame, text="View Logs", command=view_logs).pack(side="left", padx=6)
ttk.Button(container_btn_frame, text="View Usage", command=view_container_usage).pack(side="left", padx=6)
ttk.Button(container_btn_frame, text="Refresh List", command=view_containers).pack(side="left", padx=6)

# --- Image Tab ---

image_tab = ttk.Frame(tab_control)
tab_control.add(image_tab, text='Images')

image_tree = ttk.Treeview(image_tab, columns=("Repository", "Tag", "ID", "Size"), show="headings")
for col in ("Repository", "Tag", "ID", "Size"):
    image_tree.heading(col, text=col, anchor="w")
    image_tree.column(col, anchor="w", width=300)
image_tree.pack(expand=True, fill="both", padx=10, pady=10)

image_btn_frame = ttk.Frame(image_tab)
image_btn_frame.pack(side="bottom", pady=10)

ttk.Button(image_btn_frame, text="Run Image", command=run_image).pack(side="left", padx=6)
ttk.Button(image_btn_frame, text="Run Image (Interactive)", command=run_image_interactive).pack(side="left", padx=6)
ttk.Button(image_btn_frame, text="Remove Image", command=remove_image).pack(side="left", padx=6)
ttk.Button(image_btn_frame, text="Refresh List", command=list_images).pack(side="left", padx=6)

tab_control.pack(expand=1, fill="both")

# --- Initial Population ---

view_containers()
list_images()

root.mainloop()
