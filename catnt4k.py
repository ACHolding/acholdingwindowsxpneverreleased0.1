import tkinter as tk
from tkinter import font
import time
import math
import random
import wave
import struct
import tempfile
import subprocess
import platform
import threading
import os

_SAMPLE_RATE = 22050


def _env(i, n, attack=0.06, release=0.18):
    return min(1.0, i / max(1, n * attack), (n - i) / max(1, n * release))


def _samples_beep(freq, ms, volume=0.38):
    """High PC-speaker style beep."""
    n = max(1, int(_SAMPLE_RATE * ms / 1000))
    out = []
    for i in range(n):
        t = i / _SAMPLE_RATE
        e = _env(i, n)
        wave_s = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        s = volume * e * wave_s
        out.append(int(max(-32767, min(32767, s * 32767))))
    return out


def _samples_boop(ms=70, base_freq=220, volume=0.32):
    """Floppy head-step / seek thunk (boop)."""
    n = max(1, int(_SAMPLE_RATE * ms / 1000))
    out = []
    for i in range(n):
        t = i / _SAMPLE_RATE
        e = math.exp(-i / max(1, n * 0.28))
        freq = base_freq - i * 0.35
        thump = math.sin(2 * math.pi * freq * t)
        noise = (random.random() * 2 - 1) * 0.45
        s = volume * e * (thump * 0.55 + noise * 0.45)
        out.append(int(max(-32767, min(32767, s * 32767))))
    return out


def _samples_motor(ms=420, volume=0.2):
    n = max(1, int(_SAMPLE_RATE * ms / 1000))
    out = []
    for i in range(n):
        t = i / _SAMPLE_RATE
        e = _env(i, n, 0.1, 0.3)
        freq = 62 + 18 * math.sin(t * 20)
        s = volume * e * math.sin(2 * math.pi * freq * t)
        out.append(int(max(-32767, min(32767, s * 32767))))
    return out


def _samples_silence(ms):
    return [0] * max(1, int(_SAMPLE_RATE * ms / 1000))


def _build_floppy_beep_boop():
    # beep beep -> motor -> boop boop boop -> beep
    s = []
    s.extend(_samples_beep(1240, 75))
    s.extend(_samples_silence(65))
    s.extend(_samples_beep(1240, 75))
    s.extend(_samples_silence(110))
    s.extend(_samples_motor(400))
    s.extend(_samples_silence(35))
    for f in (280, 240, 200):
        s.extend(_samples_boop(62, f))
        s.extend(_samples_silence(48))
    s.extend(_samples_silence(80))
    s.extend(_samples_beep(880, 140))
    return s


def _play_wav_async(path):
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif platform.system() == "Windows":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            subprocess.Popen(
                ["aplay", "-q", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def play_floppy_beep_boop(bell_fallback=None):
    def _run():
        path = None
        try:
            samples = _build_floppy_beep_boop()
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(_SAMPLE_RATE)
                wf.writeframes(struct.pack("<" + "h" * len(samples), *samples))
            _play_wav_async(path)
            time.sleep(len(samples) / _SAMPLE_RATE + 0.1)
        except Exception:
            if bell_fallback:
                pattern = (0, 0.12, 0.24, 0.85, 0.97, 1.09, 1.45)
                for i, wait in enumerate(pattern):
                    if i and wait:
                        time.sleep(wait - pattern[i - 1])
                    try:
                        bell_fallback()
                    except Exception:
                        pass
        finally:
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    threading.Thread(target=_run, daemon=True).start()

# --- Global Color Palette (Windows XP Luna Theme) ---
BG_COLOR = "#004E98"      # Classic XP desktop blue
TASKBAR_BG = "#245EDC"    # XP Blue Taskbar
START_BTN_BG = "#3C8142"  # XP Green Start Button
TITLE_BG = "#0058E6"      # XP Window Title Bar
TITLE_FG = "white"        # XP Window Title Text
WINDOW_BG = "#ECE9D8"     # XP Window Background (Light Beige/Gray)
TEXT_COLOR = "blue"       # Default text color changed to blue
BTN_BG = "#F0F0F0"        # Standard button gray

class AppWindow(tk.Frame):
    """A simulated movable window inside the OS desktop."""
    def __init__(self, parent, title, x, y, width, height):
        super().__init__(parent, bg=TITLE_BG, bd=2, relief="raised")
        self.place(x=x, y=y, width=width, height=height)
        
        # Window Title Bar
        self.title_bar = tk.Frame(self, bg=TITLE_BG)
        self.title_bar.pack(fill="x", side="top")
        
        # Title Text
        self.title_lbl = tk.Label(self.title_bar, text=title, bg=TITLE_BG, fg=TITLE_FG, font=("Tahoma", 10, "bold"))
        self.title_lbl.pack(side="left", padx=5, pady=2)
        
        # Close Button (Red in XP)
        self.close_btn = tk.Button(self.title_bar, text="X", bg="#E34234", fg="blue", 
                                   activebackground="#ff5a4c", activeforeground="blue", highlightbackground=TITLE_BG,
                                   font=("Tahoma", 8, "bold"), bd=1, relief="raised", command=self.destroy)
        self.close_btn.pack(side="right", padx=2, pady=2)
        
        # Content Area
        self.content = tk.Frame(self, bg=WINDOW_BG)
        self.content.pack(fill="both", expand=True)
        
        # Bindings for moving the window
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.on_move)
        self.title_lbl.bind("<ButtonPress-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.on_move)
        
        # Bring to front on click
        self.bind("<ButtonPress-1>", self.lift_window)
        self.content.bind("<ButtonPress-1>", self.lift_window)
        
    def start_move(self, event):
        self.lift()
        self._x = event.x
        self._y = event.y

    def on_move(self, event):
        x = self.winfo_x() + (event.x - self._x)
        y = self.winfo_y() + (event.y - self._y)
        self.place(x=x, y=y)
        
    def lift_window(self, event=None):
        self.lift()


class CatNT(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("[A.C HOLDINGS 1999-2026] CatNT 0.1")
        self.geometry("1024x768")
        self.configure(bg="black") # Start black for BIOS
        
        # --- BIOS Boot Sequence Setup ---
        self.bios_frame = tk.Frame(self, bg="black")
        self.bios_frame.pack(fill="both", expand=True)
        
        # Dell-style BIOS is often white/gray on black, not green
        self.bios_text = tk.Text(self.bios_frame, bg="black", fg="#C0C0C0", 
                                 font=("Courier", 12, "bold"), bd=0, highlightthickness=0, 
                                 state="disabled", cursor="none")
        self.bios_text.pack(fill="both", expand=True, padx=20, pady=20)
        
        # BIOS Script Events (Dell Style + Custom Title)
        self.boot_messages = [
            "CatNT Terminal Systems [C] 1999-2026",
            "Dell System BIOS, Version A04",
            "Copyright 1996-2026 CatNT Inc.",
            "",
            "CPU = Feline-Pro, 2.4 GHz",
            "640K System RAM Passed",
            "1047552K Extended RAM Passed",
            "512K Cache SRAM Passed",
            "",
            "[FLOPPY_BEEP_BOOP]",
            "Floppy disk(s) ... OK",
            "Mouse initialized",
            "Fixed Disk 0: CatNT HD",
            "ATAPI CD-ROM: CatNT CD",
            "",
            "[DELAY]",
            "Booting from hard disk...",
            "[DELAY]",
            "Starting Windows XP Mode..."
        ]
        self.msg_index = 0
        
        # Start BIOS boot process
        self.after(800, self.run_bios)
        
        # --- OS Components (Instantiated but hidden initially) ---
        self.desktop = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.taskbar = tk.Frame(self, bg=TASKBAR_BG, height=35, bd=2, relief="raised")
        self.taskbar.pack_propagate(False)
        
        self.start_btn = tk.Button(self.taskbar, text=" start ", bg=START_BTN_BG, fg="blue", 
                                   activebackground="#4cad55", activeforeground="blue", highlightbackground=TASKBAR_BG,
                                   font=("Tahoma", 12, "bold", "italic"), bd=2, relief="raised",
                                   command=self.toggle_start)
        self.start_btn.pack(side="left", padx=0, pady=0, fill="y")
        
        # Tray Area
        self.tray = tk.Frame(self.taskbar, bg="#0F8EE9", bd=1, relief="sunken", padx=10)
        self.tray.pack(side="right", fill="y")
        self.clock_lbl = tk.Label(self.tray, text="", bg="#0F8EE9", fg="white", font=("Tahoma", 10))
        self.clock_lbl.pack(side="right")
        
        self.start_menu_open = False
        self.start_menu = tk.Frame(self, bg="white", bd=2, relief="raised")
        
        # Start Menu Header
        self.sm_header = tk.Frame(self.start_menu, bg=TITLE_BG, height=40)
        self.sm_header.pack(fill="x")
        tk.Label(self.sm_header, text="CatNT User", bg=TITLE_BG, fg="white", 
                 font=("Tahoma", 11, "bold")).pack(side="left", padx=10, pady=10)
        
        # Start Menu Body (White background like XP)
        self.sm_body = tk.Frame(self.start_menu, bg="white")
        self.sm_body.pack(fill="both", expand=True)
        
        self.add_menu_item("Command Prompt", self.open_terminal)
        self.add_menu_item("Notepad", self.open_notepad)
        self.add_menu_item("Calculator", self.open_calculator)
        tk.Frame(self.sm_body, bg="#D3D3D3", height=1).pack(fill="x", padx=5, pady=2)
        self.add_menu_item("System Properties", self.open_sys_props)
        self.add_menu_item("About", self.open_about)
        
        # Start Menu Footer
        self.sm_footer = tk.Frame(self.start_menu, bg=TASKBAR_BG, height=35)
        self.sm_footer.pack(fill="x", side="bottom")
        tk.Button(self.sm_footer, text="Log Off", bg=TASKBAR_BG, fg="blue", bd=0, font=("Tahoma", 9), command=lambda: None).pack(side="left", padx=10, pady=5)
        tk.Button(self.sm_footer, text="Shut Down", bg=TASKBAR_BG, fg="blue", bd=0, font=("Tahoma", 9), command=self.quit).pack(side="right", padx=10, pady=5)
        
        self.desktop.bind("<Button-1>", self.close_start_menu)

    # --- BIOS Boot Logic ---
    def type_bios_text(self, text):
        self.bios_text.config(state="normal")
        self.bios_text.insert(tk.END, text + "\n")
        self.bios_text.config(state="disabled")
        self.bios_text.see(tk.END)

    def run_bios(self):
        if self.msg_index < len(self.boot_messages):
            msg = self.boot_messages[self.msg_index]
            
            if msg == "[FLOPPY_BEEP_BOOP]":
                self.type_bios_text("Primary Slave:  Floppy 0")
                play_floppy_beep_boop(self.bell)
                delay = 2100
            elif msg == "[DELAY]":
                delay = 1500
            else:
                self.type_bios_text(msg)
                if "RAM Passed" in msg:
                    delay = random.randint(100, 300)
                elif "Starting" in msg:
                    delay = 1000
                else:
                    delay = random.randint(50, 150)

            self.msg_index += 1
            self.after(delay, self.run_bios)
        else:
            self.start_os()

    # --- OS Logic ---
    def start_os(self):
        # Destroy BIOS screen
        self.bios_frame.destroy()
        self.configure(bg=BG_COLOR)
        
        # Pack Desktop Components
        self.desktop.pack(fill="both", expand=True)
        self.taskbar.pack(side="bottom", fill="x")
        
        # Start Clock Update
        self.update_clock()
        
        # Add Desktop Icons (Blue text with no background outline)
        self.create_desktop_icon("My Computer", 20, 20, self.open_sys_props)
        self.create_desktop_icon("Recycle Bin", 20, 80, lambda: None)
        self.create_desktop_icon("Command Prompt", 20, 140, self.open_terminal)
        
        # Welcome App Window
        self.after(500, self.open_about)

    def create_desktop_icon(self, text, x, y, command):
        icon_btn = tk.Button(self.desktop, text=text, bg=BG_COLOR, fg="blue", font=("Tahoma", 9),
                             activebackground=TITLE_BG, activeforeground="blue", highlightthickness=0,
                             bd=0, relief="flat", command=command)
        self.desktop.create_window(x, y, anchor="nw", window=icon_btn)

    def add_menu_item(self, text, command):
        btn = tk.Button(self.sm_body, text=text, bg="white", fg="blue", font=("Tahoma", 10),
                        bd=0, anchor="w", padx=20, pady=5, command=command,
                        activebackground=TITLE_BG, activeforeground="blue")
        btn.pack(fill="x")

    def update_clock(self):
        current_time = time.strftime('%I:%M %p')
        self.clock_lbl.config(text=current_time)
        self.after(1000, self.update_clock)

    def toggle_start(self):
        if self.start_menu_open:
            self.close_start_menu()
        else:
            self.start_menu.place(relx=0, rely=1.0, y=-35, anchor="sw", width=250, height=350)
            self.start_menu.lift()
            self.start_menu_open = True

    def close_start_menu(self, event=None):
        if self.start_menu_open:
            self.start_menu.place_forget()
            self.start_menu_open = False

    # --- Applications ---
    def open_terminal(self):
        self.close_start_menu()
        win = AppWindow(self.desktop, "Command Prompt", 150, 100, 550, 350)
        win.content.config(bg="black")
        
        # Terminal Output Area
        output = tk.Text(win.content, bg="black", fg="#C0C0C0", font=("Consolas", 10), 
                         state="disabled", bd=0, insertbackground="#C0C0C0")
        output.pack(fill="both", expand=True, padx=5, pady=5)
        
        def append_text(text):
            output.config(state="normal")
            output.insert(tk.END, text + "\n")
            output.see(tk.END)
            output.config(state="disabled")
            
        append_text("CatNT Terminal Systems [Version 5.1.2600]")
        append_text("(C) Copyright 1999-2026 CatNT Inc.\n")
        
        # Input Area
        input_frame = tk.Frame(win.content, bg="black")
        input_frame.pack(fill="x", padx=5, pady=2)
        
        prompt = tk.Label(input_frame, text="C:\\>", bg="black", fg="#C0C0C0", font=("Consolas", 10))
        prompt.pack(side="left")
        
        cmd_entry = tk.Entry(input_frame, bg="black", fg="#C0C0C0", font=("Consolas", 10), bd=0, insertbackground="#C0C0C0")
        cmd_entry.pack(side="left", fill="x", expand=True)
        cmd_entry.focus()
        
        def execute_cmd(event):
            cmd = cmd_entry.get().strip()
            append_text(f"C:\\>{cmd}")
            cmd_entry.delete(0, tk.END)
            
            if not cmd: return
            parts = cmd.split()
            base = parts[0].lower()
            
            if base == "help":
                append_text("For more information on a specific command, type HELP command-name\nCLS            Clears the screen.\nDIR            Displays a list of files and subdirectories in a directory.\nECHO           Displays messages.\nEXIT           Quits the CMD.EXE program (command interpreter).")
            elif base == "dir":
                append_text(" Volume in drive C is CATNT_OS\n Volume Serial Number is 1999-2026\n\n Directory of C:\\\n\n05/16/2026  05:26 PM    <DIR>          WINDOWS\n05/16/2026  05:26 PM    <DIR>          Program Files\n05/16/2026  05:26 PM                 0 AUTOEXEC.BAT\n               1 File(s)              0 bytes\n               2 Dir(s)  42,000,000,000 bytes free")
            elif base == "echo":
                append_text(" ".join(parts[1:]))
            elif base == "cls":
                output.config(state="normal")
                output.delete(1.0, tk.END)
                output.config(state="disabled")
            elif base == "exit":
                win.destroy()
            else:
                append_text(f"'{base}' is not recognized as an internal or external command,\noperable program or batch file.")
                
        cmd_entry.bind("<Return>", execute_cmd)

    def open_about(self):
        self.close_start_menu()
        win = AppWindow(self.desktop, "About CatNT", 300, 200, 320, 180)
        
        tk.Label(win.content, text="CatNT Terminal Systems", font=("Tahoma", 14, "bold"), bg=WINDOW_BG, fg="black").pack(pady=(20, 5))
        tk.Label(win.content, text="Version 5.1 (Build 2600.xpsp)\nCopyright (C) 1999-2026 CatNT Inc.", bg=WINDOW_BG, fg="black", font=("Tahoma", 10)).pack(pady=5)
        
        ok_btn = tk.Button(win.content, text="OK", width=10, bg=BTN_BG, fg="blue", command=win.destroy)
        ok_btn.pack(pady=15)

    def open_notepad(self):
        self.close_start_menu()
        win = AppWindow(self.desktop, "Untitled - Notepad", 100, 150, 500, 350)
        
        text_area = tk.Text(win.content, bg="white", fg="black", insertbackground="black",
                            font=("Courier", 12), bd=1, relief="sunken")
        text_area.pack(fill="both", expand=True, padx=2, pady=2)

    def open_calculator(self):
        self.close_start_menu()
        win = AppWindow(self.desktop, "Calculator", 200, 150, 250, 320)
        
        display = tk.Entry(win.content, bg="white", fg="black", font=("Courier", 18, "bold"), 
                           justify="right", bd=2, relief="sunken", insertbackground="black")
        display.pack(fill="x", padx=10, pady=10)
        
        btn_frame = tk.Frame(win.content, bg=WINDOW_BG)
        btn_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2), ('/', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('*', 1, 3),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2), ('-', 2, 3),
            ('C', 3, 0), ('0', 3, 1), ('=', 3, 2), ('+', 3, 3)
        ]
        
        def btn_click(char):
            if char == 'C':
                display.delete(0, tk.END)
            elif char == '=':
                try:
                    result = str(eval(display.get()))
                    display.delete(0, tk.END)
                    display.insert(0, result)
                except Exception:
                    display.delete(0, tk.END)
                    display.insert(0, "Error")
            else:
                display.insert(tk.END, char)

        for (text, row, col) in buttons:
            btn = tk.Button(btn_frame, text=text, bg=BTN_BG, fg="blue", font=("Tahoma", 12, "bold"),
                            command=lambda t=text: btn_click(t))
            btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
            
        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)
            btn_frame.rowconfigure(i, weight=1)

    def open_sys_props(self):
        self.close_start_menu()
        win = AppWindow(self.desktop, "System Properties", 250, 200, 350, 220)
        
        info = (
            "System:\n"
            "  CatNT Terminal Systems\n"
            "  Version 5.1\n\n"
            "Computer:\n"
            "  Feline-Pro CPU 2.40GHz\n"
            "  1.00 GB of RAM\n"
            "  Classic XP Theme Applied\n"
        )
        lbl = tk.Label(win.content, text=info, bg=WINDOW_BG, fg="black", font=("Tahoma", 10), justify="left")
        lbl.pack(padx=20, pady=20, anchor="nw")

if __name__ == "__main__":
    app = CatNT()
    app.mainloop()
