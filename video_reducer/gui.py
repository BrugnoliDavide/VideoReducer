import base64
import platform
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    tk = None

from .scanner import scan_folder
from .converter import (
    PRESETS, process_files, delete_originals, format_size, set_low_priority,
)
from .state import (
    default_state, default_file_entry, load_state, save_state, recalc_stats,
)

_FONT = "Helvetica"

THEMES = {
    "light": {
        "bg": "#fafafa",
        "fg": "#18181b",
        "frame_bg": "#ffffff",
        "entry_bg": "#ffffff",
        "entry_fg": "#18181b",
        "tree_bg": "#ffffff",
        "tree_fg": "#18181b",
        "tree_sel_bg": "#2563eb",
        "tree_sel_fg": "#ffffff",
        "tree_heading_bg": "#f4f4f5",
        "tree_heading_fg": "#71717a",
        "btn_bg": "#f4f4f5",
        "btn_fg": "#18181b",
        "accent": "#2563eb",
        "muted": "#a1a1aa",
        "border": "#e4e4e7",
        "progress_bg": "#e4e4e7",
        "progress_fg": "#2563eb",
        "status_bg": "#f4f4f5",
        "status_fg": "#3f3f46",
        "dot_idle": "#d4d4d8",
        "dot_success": "#22c55e",
        "dot_working": "#eab308",
        "dot_error": "#ef4444",
    },
    "dark": {
        "bg": "#18181b",
        "fg": "#f4f4f5",
        "frame_bg": "#27272a",
        "entry_bg": "#3f3f46",
        "entry_fg": "#f4f4f5",
        "tree_bg": "#18181b",
        "tree_fg": "#f4f4f5",
        "tree_sel_bg": "#3b82f6",
        "tree_sel_fg": "#ffffff",
        "tree_heading_bg": "#27272a",
        "tree_heading_fg": "#a1a1aa",
        "btn_bg": "#3f3f46",
        "btn_fg": "#f4f4f5",
        "accent": "#60a5fa",
        "muted": "#71717a",
        "border": "#3f3f46",
        "progress_bg": "#27272a",
        "progress_fg": "#4ade80",
        "status_bg": "#27272a",
        "status_fg": "#d4d4d8",
        "dot_idle": "#52525b",
        "dot_success": "#4ade80",
        "dot_working": "#facc15",
        "dot_error": "#f87171",
    },
}


def run_gui():
    if tk is None:
        raise ImportError("tkinter non disponibile")
    app = VideoReducerGUI()
    app.mainloop()


class VideoReducerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Reducer")
        self.geometry("1000x700")
        self.minsize(800, 500)
        self.state_data = None
        self.current_theme = "dark"
        self._iid_to_path = {}
        self._path_to_iid = {}
        self._working = False
        self._sort_col = None
        self._sort_reverse = False
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._status_state = "idle"
        self._set_icon()
        self._build_ui()
        self._apply_theme(self.current_theme)

    def _set_icon(self):
        try:
            from .icon_data import ICON_BASE64
            icon_bytes = base64.b64decode(ICON_BASE64)
            self._icon_photo = tk.PhotoImage(data=icon_bytes)
            self.iconphoto(True, self._icon_photo)
        except Exception:
            ico = Path(__file__).parent.parent / "icon.ico"
            if ico.exists() and platform.system() == "Windows":
                try:
                    self.iconbitmap(str(ico))
                except tk.TclError:
                    pass

    def _apply_theme(self, name):
        self.current_theme = name
        t = THEMES[name]

        self.configure(bg=t["bg"])

        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=t["bg"], foreground=t["fg"],
                         fieldbackground=t["entry_bg"], bordercolor=t["border"],
                         troughcolor=t["progress_bg"], font=(_FONT, 10))

        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"],
                         font=(_FONT, 10))
        style.configure("Muted.TLabel", background=t["bg"], foreground=t["muted"],
                         font=(_FONT, 9))
        style.configure("SelCount.TLabel", background=t["bg"], foreground=t["accent"],
                         font=(_FONT, 9, "bold"))

        style.configure("TLabelframe", background=t["bg"], foreground=t["fg"],
                         bordercolor=t["border"], relief="flat")
        style.configure("TLabelframe.Label", background=t["bg"], foreground=t["accent"],
                         font=(_FONT, 10, "bold"))

        style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
                         insertcolor=t["entry_fg"], bordercolor=t["border"],
                         font=(_FONT, 10), padding=(6, 4))

        style.configure("TButton", background=t["btn_bg"], foreground=t["btn_fg"],
                         bordercolor=t["border"], padding=(12, 6),
                         font=(_FONT, 9), relief="flat")
        style.map("TButton",
                   background=[("active", t["accent"]), ("disabled", t["muted"])],
                   foreground=[("active", "#ffffff"), ("disabled", t["bg"])])

        style.configure("Accent.TButton", background=t["accent"], foreground="#ffffff",
                         bordercolor=t["accent"], padding=(14, 6),
                         font=(_FONT, 9, "bold"), relief="flat")
        style.map("Accent.TButton",
                   background=[("active", t["btn_bg"])],
                   foreground=[("active", t["fg"])])

        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"],
                         font=(_FONT, 9))
        style.map("TCheckbutton", background=[("active", t["bg"])])

        style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
                         background=t["btn_bg"], bordercolor=t["border"],
                         arrowcolor=t["fg"], font=(_FONT, 9), padding=(4, 3))
        style.map("TCombobox", fieldbackground=[("readonly", t["entry_bg"])],
                   foreground=[("readonly", t["entry_fg"])])
        self.option_add("*TCombobox*Listbox.background", t["entry_bg"])
        self.option_add("*TCombobox*Listbox.foreground", t["entry_fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", t["tree_sel_bg"])
        self.option_add("*TCombobox*Listbox.selectForeground", t["tree_sel_fg"])
        self.option_add("*TCombobox*Listbox.font", (_FONT, 9))

        style.configure("Treeview",
                         background=t["tree_bg"], foreground=t["tree_fg"],
                         fieldbackground=t["tree_bg"], bordercolor=t["border"],
                         rowheight=30, font=(_FONT, 9))
        style.configure("Treeview.Heading",
                         background=t["tree_heading_bg"], foreground=t["tree_heading_fg"],
                         bordercolor=t["border"], relief="flat",
                         font=(_FONT, 9, "bold"), padding=(8, 4))
        style.map("Treeview",
                   background=[("selected", t["tree_sel_bg"])],
                   foreground=[("selected", t["tree_sel_fg"])])
        style.map("Treeview.Heading",
                   background=[("active", t["accent"])],
                   foreground=[("active", "#ffffff")])

        style.configure("TScrollbar", background=t["btn_bg"], troughcolor=t["bg"],
                         bordercolor=t["border"], arrowcolor=t["fg"])

        style.configure("Horizontal.TProgressbar",
                         background=t["progress_fg"], troughcolor=t["progress_bg"],
                         bordercolor=t["border"])

        style.configure("Status.TLabel",
                         background=t["status_bg"], foreground=t["status_fg"],
                         padding=(8, 5), font=(_FONT, 9))
        style.configure("StatusBold.TLabel",
                         background=t["status_bg"], foreground=t["status_fg"],
                         padding=(8, 5), font=(_FONT, 9, "bold"))
        style.configure("StatusBar.TFrame", background=t["status_bg"])

        if hasattr(self, "btn_theme"):
            self.btn_theme.config(text="☼ Chiaro" if name == "dark" else "☾ Scuro")
        if hasattr(self, "preset_desc"):
            self.preset_desc.config(style="Muted.TLabel")
        if hasattr(self, "status_dot"):
            self._draw_status_dot(self._status_state)
        if hasattr(self, "status_frame"):
            self.status_frame.config(style="StatusBar.TFrame")

    def _toggle_theme(self):
        new = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new)

    def _draw_status_dot(self, state):
        self._status_state = state
        t = THEMES[self.current_theme]
        color = t.get(f"dot_{state}", t["dot_idle"])
        self.status_dot.configure(bg=t["status_bg"])
        self.status_dot.delete("all")
        self.status_dot.create_oval(3, 3, 13, 13, fill=color, outline="")

    def _set_working(self, working, message=""):
        self._working = working
        if working:
            self.title(f"Video Reducer — {message}")
            for btn in self._all_buttons:
                btn.config(state=tk.DISABLED)
            self._draw_status_dot("working")
            self.stats_label.config(text=message, style="StatusBold.TLabel")
            self.progress_label.config(style="Status.TLabel")
        else:
            self.title("Video Reducer")
            self.conv_controls.pack_forget()
            for btn in self._all_buttons:
                btn.config(state=tk.NORMAL)
            self._draw_status_dot("idle")
            self.stats_label.config(style="Status.TLabel")
            self.progress_label.config(text="", style="Status.TLabel")
            self.progress["value"] = 0

    def _build_ui(self):
        top = ttk.Frame(self, padding=(12, 10))
        top.pack(fill=tk.X)

        ttk.Label(top, text="Cartella:").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(top, textvariable=self.folder_var, width=50)
        self.folder_entry.pack(side=tk.LEFT, padx=6, expand=True, fill=tk.X)
        self.btn_browse = ttk.Button(top, text="Sfoglia…", command=self._browse)
        self.btn_browse.pack(side=tk.LEFT)
        self.btn_scan = ttk.Button(top, text="Scansiona", command=self._scan,
                                    style="Accent.TButton")
        self.btn_scan.pack(side=tk.LEFT, padx=6)

        self.btn_theme = ttk.Button(top, text="☼ Chiaro", command=self._toggle_theme)
        self.btn_theme.pack(side=tk.RIGHT)

        opts = ttk.LabelFrame(self, text="Opzioni", padding=(12, 8))
        opts.pack(fill=tk.X, padx=12, pady=(4, 2))

        row1 = ttk.Frame(opts)
        row1.pack(fill=tk.X)

        ttk.Label(row1, text="Preset:").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value="lossy")
        preset_combo = ttk.Combobox(row1, textvariable=self.preset_var,
                                     values=list(PRESETS.keys()), state="readonly", width=15)
        preset_combo.pack(side=tk.LEFT, padx=6)
        preset_combo.bind("<<ComboboxSelected>>", self._update_preset_desc)

        self.preset_desc = ttk.Label(row1, text=PRESETS["lossy"]["description"],
                                      style="Muted.TLabel")
        self.preset_desc.pack(side=tk.LEFT, padx=10)

        row2 = ttk.Frame(opts)
        row2.pack(fill=tk.X, pady=4)

        ttk.Label(row2, text="Categoria:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value="all")
        cat_combo = ttk.Combobox(row2, textvariable=self.category_var,
                                  values=["all", "heavy_codec", "large_file",
                                          "high_bitrate", "not_efficient"],
                                  state="readonly", width=15)
        cat_combo.pack(side=tk.LEFT, padx=6)
        cat_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_tree())

        self.delete_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Elimina originali dopo conversione",
                         variable=self.delete_var).pack(side=tk.LEFT, padx=20)

        row3 = ttk.Frame(opts)
        row3.pack(fill=tk.X, pady=4)

        self.lowprio_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Lavora in background (priorità bassa CPU)",
                         variable=self.lowprio_var).pack(side=tk.LEFT)

        ttk.Label(row3, text="Soglia (MB):").pack(side=tk.LEFT, padx=(20, 0))
        self.threshold_var = tk.StringVar(value="500")
        ttk.Entry(row3, textvariable=self.threshold_var, width=8).pack(side=tk.LEFT, padx=6)

        btn_row = ttk.Frame(self, padding=(12, 4))
        btn_row.pack(fill=tk.X)
        self.btn_convert = ttk.Button(btn_row, text="Converti selezionati",
                                       command=self._convert, style="Accent.TButton")
        self.btn_convert.pack(side=tk.LEFT)
        self.btn_sel_all = ttk.Button(btn_row, text="Seleziona tutti",
                                       command=self._select_all)
        self.btn_sel_all.pack(side=tk.LEFT, padx=6)
        self.btn_desel_all = ttk.Button(btn_row, text="Deseleziona tutti",
                                         command=self._deselect_all)
        self.btn_desel_all.pack(side=tk.LEFT)
        self.btn_del = ttk.Button(btn_row, text="Elimina originali convertiti",
                                   command=self._delete_originals)
        self.btn_del.pack(side=tk.LEFT, padx=20)

        self.sel_count_label = ttk.Label(btn_row, text="", style="SelCount.TLabel")
        self.sel_count_label.pack(side=tk.LEFT, padx=(6, 0))

        search_frame = ttk.Frame(self, padding=(12, 2, 12, 4))
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="Cerca:", style="Muted.TLabel").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=6)
        self.search_var.trace_add("write", lambda *_: self._refresh_tree())

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        cols = ("sel", "nome", "dimensione", "codec", "categorie", "stato")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  selectmode="extended")
        self.tree.heading("sel", text="✓")
        self.tree.heading("nome", text="Nome file",
                          command=lambda: self._sort_column("nome"))
        self.tree.heading("dimensione", text="Dimensione",
                          command=lambda: self._sort_column("dimensione"))
        self.tree.heading("codec", text="Codec",
                          command=lambda: self._sort_column("codec"))
        self.tree.heading("categorie", text="Categorie",
                          command=lambda: self._sort_column("categorie"))
        self.tree.heading("stato", text="Stato",
                          command=lambda: self._sort_column("stato"))
        self.tree.column("sel", width=30, anchor=tk.CENTER)
        self.tree.column("nome", width=300)
        self.tree.column("dimensione", width=100, anchor=tk.E)
        self.tree.column("codec", width=100)
        self.tree.column("categorie", width=200)
        self.tree.column("stato", width=120)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<ButtonRelease-1>", self._toggle_selection)

        self.selected = set()

        self.status_frame = ttk.Frame(self, style="StatusBar.TFrame", padding=(12, 6))
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_dot = tk.Canvas(self.status_frame, width=16, height=16,
                                     highlightthickness=0, bd=0)
        self.status_dot.pack(side=tk.LEFT)

        self.stats_label = ttk.Label(self.status_frame, text="Nessuna cartella caricata",
                                      style="Status.TLabel")
        self.stats_label.pack(side=tk.LEFT, padx=(6, 0))

        self.progress = ttk.Progressbar(self.status_frame, mode="determinate", length=250)
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress_label = ttk.Label(self.status_frame, text="", style="Status.TLabel")
        self.progress_label.pack(side=tk.RIGHT, padx=(0, 6))

        self.conv_controls = ttk.Frame(self.status_frame, style="StatusBar.TFrame")
        self.preset_indicator = ttk.Label(self.conv_controls, text="",
                                           style="Status.TLabel")
        self.preset_indicator.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_pause = ttk.Button(self.conv_controls, text="⏸ Pausa",
                                     command=self._toggle_pause, width=12)
        self.btn_pause.pack(side=tk.LEFT, padx=2)
        self.btn_stop = ttk.Button(self.conv_controls, text="⏹ Stop",
                                    command=self._stop_conversion, width=8)
        self.btn_stop.pack(side=tk.LEFT, padx=2)

        self._all_buttons = [
            self.btn_browse, self.btn_scan, self.btn_convert,
            self.btn_sel_all, self.btn_desel_all, self.btn_del,
        ]

    def _browse(self):
        folder = filedialog.askdirectory(title="Seleziona cartella video")
        if folder:
            self.folder_var.set(folder)
            existing = load_state(folder)
            if existing:
                self.state_data = existing
                self._refresh_tree()
                self._update_stats()

    def _update_preset_desc(self, _=None):
        name = self.preset_var.get()
        self.preset_desc.config(text=PRESETS.get(name, {}).get("description", ""))

    def _sort_column(self, col):
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False
        self._refresh_tree()

    def _toggle_pause(self):
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.btn_pause.config(text="⏸ Pausa")
            self.stats_label.config(text="Conversione ripresa…")
        else:
            self._pause_event.set()
            self.btn_pause.config(text="▶ Riprendi")
            self.stats_label.config(text="In pausa…")

    def _stop_conversion(self):
        if messagebox.askyesno("Conferma", "Interrompere la conversione in corso?"):
            self._stop_event.set()
            self._pause_event.clear()
            self.stats_label.config(text="Interruzione in corso…")

    def _update_sel_count(self):
        n = len(self.selected)
        if n > 0:
            self.sel_count_label.config(text=f"Selezionate {n} clip")
        else:
            self.sel_count_label.config(text="")

    def _scan(self):
        if self._working:
            return
        folder = self.folder_var.get()
        if not folder or not Path(folder).is_dir():
            messagebox.showerror("Errore", "Seleziona una cartella valida")
            return

        try:
            threshold = int(self.threshold_var.get())
        except ValueError:
            threshold = 500

        self._set_working(True, "Scansione in corso…")

        def do_scan():
            state = load_state(folder)
            if state is None:
                state = default_state(folder)

            found = scan_folder(folder, threshold)
            new_count = 0
            for fpath, info in found.items():
                if fpath not in state["files"]:
                    state["files"][fpath] = default_file_entry(
                        fpath, info["size"], info["codec"], info["duration"],
                        info["resolution"], info["bitrate"], info["categories"],
                    )
                    new_count += 1
                else:
                    state["files"][fpath]["categories"] = info["categories"]

            recalc_stats(state)
            save_state(state)
            self.state_data = state
            self.after(0, self._scan_done, len(state["files"]), new_count)

        threading.Thread(target=do_scan, daemon=True).start()

    def _scan_done(self, total, new_count):
        self._set_working(False)
        self._draw_status_dot("success")
        self._refresh_tree()
        self._update_stats()
        messagebox.showinfo(
            "Scansione completata",
            f"Trovati {total} file video ({new_count} nuovi)")

    def _refresh_tree(self):
        prev_selected = set(self.selected)
        self.tree.delete(*self.tree.get_children())
        self.selected.clear()
        self._iid_to_path.clear()
        self._path_to_iid.clear()
        if not self.state_data:
            self._update_sel_count()
            return

        cat_filter = self.category_var.get()
        search = self.search_var.get().strip().lower()
        filtered = []
        for fpath, entry in self.state_data["files"].items():
            if cat_filter != "all" and cat_filter not in entry["categories"]:
                continue
            if search and search not in Path(fpath).name.lower():
                continue
            filtered.append((fpath, entry))

        if self._sort_col:
            sort_keys = {
                "nome": lambda x: Path(x[0]).name.lower(),
                "dimensione": lambda x: x[1]["original_size"],
                "codec": lambda x: x[1]["codec"].lower(),
                "categorie": lambda x: ", ".join(x[1]["categories"]).lower(),
                "stato": lambda x: x[1]["status"],
            }
            key_func = sort_keys.get(self._sort_col)
            if key_func:
                filtered.sort(key=key_func, reverse=self._sort_reverse)

        heading_texts = {
            "sel": "✓", "nome": "Nome file", "dimensione": "Dimensione",
            "codec": "Codec", "categorie": "Categorie", "stato": "Stato",
        }
        for col, text in heading_texts.items():
            if col == self._sort_col:
                text += " ▼" if self._sort_reverse else " ▲"
            self.tree.heading(col, text=text)

        for idx, (fpath, entry) in enumerate(filtered):
            cats = ", ".join(entry["categories"]) if entry["categories"] else "—"
            status = entry["status"]
            if entry["original_deleted"]:
                status += " [DEL]"
            iid = f"row_{idx}"
            self._iid_to_path[iid] = fpath
            self._path_to_iid[fpath] = iid
            is_sel = fpath in prev_selected
            if is_sel:
                self.selected.add(fpath)
            self.tree.insert("", tk.END, iid=iid, values=(
                "☑" if is_sel else "☐",
                Path(fpath).name, format_size(entry["original_size"]),
                entry["codec"], cats, status,
            ))

        self._update_sel_count()

    def _toggle_selection(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        fpath = self._iid_to_path.get(item)
        if not fpath:
            return

        if fpath in self.selected:
            self.selected.discard(fpath)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☐"
            self.tree.item(item, values=vals)
        else:
            self.selected.add(fpath)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☑"
            self.tree.item(item, values=vals)

        self._update_sel_count()

    def _select_all(self):
        for item in self.tree.get_children():
            fpath = self._iid_to_path.get(item)
            if fpath:
                self.selected.add(fpath)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☑"
            self.tree.item(item, values=vals)
        self._update_sel_count()

    def _deselect_all(self):
        for item in self.tree.get_children():
            fpath = self._iid_to_path.get(item)
            if fpath:
                self.selected.discard(fpath)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☐"
            self.tree.item(item, values=vals)
        self._update_sel_count()

    def _convert(self):
        if self._working:
            return
        if not self.state_data:
            messagebox.showerror("Errore", "Scansiona prima una cartella")
            return

        keys = [fpath for fpath in self.selected
                if self.state_data["files"].get(fpath, {}).get("status")
                in ("pending", "error")]
        if not keys:
            messagebox.showinfo("Info",
                                "Nessun file selezionato (o tutti già convertiti)")
            return

        preset = self.preset_var.get()
        del_orig = self.delete_var.get()
        set_low_priority(self.lowprio_var.get())

        self._stop_event.clear()
        self._pause_event.clear()

        self._set_working(True, f"Conversione di {len(keys)} file…")
        self.progress["maximum"] = len(keys)
        self.progress["value"] = 0

        self.preset_indicator.config(text=f"Preset: {preset}",
                                      style="StatusBold.TLabel")
        self.btn_pause.config(text="⏸ Pausa")
        self.conv_controls.pack(side=tk.LEFT, padx=(10, 0))

        def progress_cb(current, total, fpath, msg):
            self.after(0, lambda: self._update_progress(current, total, fpath, msg))

        def do_convert():
            process_files(self.state_data, keys, preset, del_orig, progress_cb,
                          stop_event=self._stop_event, pause_event=self._pause_event)
            self.after(0, self._conversion_done)

        threading.Thread(target=do_convert, daemon=True).start()

    def _update_progress(self, current, total, fpath, msg):
        self.progress["value"] = current
        pct = int(current / total * 100) if total else 0
        self.progress_label.config(text=f"{current}/{total} ({pct}%)")
        name = Path(fpath).name
        status_text = f"[{current}/{total}] {name}: {msg}"
        self.stats_label.config(text=status_text)
        self.title(f"Video Reducer — {pct}% — {name}")
        entry = self.state_data["files"].get(fpath)
        iid = self._path_to_iid.get(fpath)
        if entry and iid and self.tree.exists(iid):
            status = entry["status"]
            if entry["original_deleted"]:
                status += " [DEL]"
            vals = list(self.tree.item(iid, "values"))
            vals[5] = status
            self.tree.item(iid, values=vals)

    def _conversion_done(self):
        self.conv_controls.pack_forget()
        self._set_working(False)
        self._update_stats()
        self._refresh_tree()
        stopped = self._stop_event.is_set()
        self._stop_event.clear()
        self._pause_event.clear()
        if stopped:
            self._draw_status_dot("error")
            messagebox.showinfo("Interrotto", "Conversione interrotta dall'utente.")
        else:
            has_errors = any(
                e["status"] == "error" for e in self.state_data["files"].values()
            )
            self._draw_status_dot("error" if has_errors else "success")
            messagebox.showinfo(
                "Completato",
                "Conversione terminata!\n"
                f"Spazio risparmiato: {format_size(self.state_data['stats']['space_saved'])}")

    def _delete_originals(self):
        if self._working:
            return
        if not self.state_data:
            messagebox.showerror("Errore", "Scansiona prima una cartella")
            return

        converted = [f for f, e in self.state_data["files"].items()
                      if e["status"] == "converted" and not e["original_deleted"]]
        not_conv = [f for f, e in self.state_data["files"].items()
                     if e["status"] != "converted" and not e["original_deleted"]]

        if not converted:
            if not not_conv:
                messagebox.showinfo("Info", "Nessun file originale da eliminare")
                return
            resp = messagebox.askyesno(
                "Attenzione",
                f"Nessun file è stato convertito!\n"
                f"Ci sono {len(not_conv)} file non convertiti.\n\n"
                f"Vuoi comunque eliminarli?\n"
                f"ATTENZIONE: i dati andranno persi irrevocabilmente!",
                icon="warning",
            )
            if not resp:
                return
            keys = not_conv
        else:
            resp = messagebox.askyesno(
                "Conferma eliminazione",
                f"Eliminare {len(converted)} file originali già convertiti?\n"
                f"Verrà verificata l'integrità prima dell'eliminazione.",
            )
            if not resp:
                return
            keys = converted

        self._set_working(True,
                          f"Eliminazione di {len(keys)} originali…")

        def do_delete():
            d, e, s = delete_originals(self.state_data, keys)
            self.after(0, lambda: self._delete_done(d, e, s))

        threading.Thread(target=do_delete, daemon=True).start()

    def _delete_done(self, deleted, errors, skipped):
        self._set_working(False)
        self._draw_status_dot("error" if errors else "success")
        self._refresh_tree()
        self._update_stats()

        msg = f"Eliminati: {deleted}"
        if errors:
            msg += f"\nErrori: {len(errors)}"
        if skipped:
            msg += f"\nSaltati (non convertiti): {len(skipped)}"
        messagebox.showinfo("Risultato", msg)

    def _update_stats(self):
        if not self.state_data:
            return
        s = self.state_data["stats"]
        total = len(self.state_data["files"])
        conv = sum(1 for e in self.state_data["files"].values()
                   if e["status"] == "converted")
        saved = format_size(s["space_saved"])
        self.stats_label.config(
            text=f"File: {total}  │  Convertiti: {conv}  │  Risparmiati: {saved}"
        )
