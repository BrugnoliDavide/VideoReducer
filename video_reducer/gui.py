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

THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "fg": "#1a1a1a",
        "frame_bg": "#ffffff",
        "entry_bg": "#ffffff",
        "entry_fg": "#1a1a1a",
        "tree_bg": "#ffffff",
        "tree_fg": "#1a1a1a",
        "tree_sel_bg": "#0078d4",
        "tree_sel_fg": "#ffffff",
        "tree_heading_bg": "#e0e0e0",
        "tree_heading_fg": "#333333",
        "btn_bg": "#e0e0e0",
        "btn_fg": "#1a1a1a",
        "accent": "#0078d4",
        "muted": "#666666",
        "border": "#cccccc",
        "progress_bg": "#e0e0e0",
        "progress_fg": "#0078d4",
        "status_working_bg": "#fff3cd",
        "status_working_fg": "#664d03",
        "status_idle_bg": "#e0e0e0",
        "status_idle_fg": "#333333",
    },
    "dark": {
        "bg": "#1e1e2e",
        "fg": "#cdd6f4",
        "frame_bg": "#282840",
        "entry_bg": "#313244",
        "entry_fg": "#cdd6f4",
        "tree_bg": "#1e1e2e",
        "tree_fg": "#cdd6f4",
        "tree_sel_bg": "#585b70",
        "tree_sel_fg": "#ffffff",
        "tree_heading_bg": "#313244",
        "tree_heading_fg": "#bac2de",
        "btn_bg": "#45475a",
        "btn_fg": "#cdd6f4",
        "accent": "#89b4fa",
        "muted": "#6c7086",
        "border": "#45475a",
        "progress_bg": "#313244",
        "progress_fg": "#a6e3a1",
        "status_working_bg": "#f9e2af",
        "status_working_fg": "#1e1e2e",
        "status_idle_bg": "#313244",
        "status_idle_fg": "#cdd6f4",
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
                         troughcolor=t["progress_bg"])

        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("Muted.TLabel", background=t["bg"], foreground=t["muted"])

        style.configure("TLabelframe", background=t["bg"], foreground=t["fg"],
                         bordercolor=t["border"])
        style.configure("TLabelframe.Label", background=t["bg"], foreground=t["accent"])

        style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
                         insertcolor=t["entry_fg"], bordercolor=t["border"])

        style.configure("TButton", background=t["btn_bg"], foreground=t["btn_fg"],
                         bordercolor=t["border"], padding=(8, 4))
        style.map("TButton",
                   background=[("active", t["accent"]), ("disabled", t["muted"])],
                   foreground=[("active", "#ffffff"), ("disabled", t["bg"])])

        style.configure("Accent.TButton", background=t["accent"], foreground="#ffffff",
                         bordercolor=t["accent"], padding=(10, 5))
        style.map("Accent.TButton",
                   background=[("active", t["btn_bg"])],
                   foreground=[("active", t["fg"])])

        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        style.map("TCheckbutton", background=[("active", t["bg"])])

        style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
                         background=t["btn_bg"], bordercolor=t["border"],
                         arrowcolor=t["fg"])
        style.map("TCombobox", fieldbackground=[("readonly", t["entry_bg"])],
                   foreground=[("readonly", t["entry_fg"])])
        self.option_add("*TCombobox*Listbox.background", t["entry_bg"])
        self.option_add("*TCombobox*Listbox.foreground", t["entry_fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", t["tree_sel_bg"])
        self.option_add("*TCombobox*Listbox.selectForeground", t["tree_sel_fg"])

        style.configure("Treeview",
                         background=t["tree_bg"], foreground=t["tree_fg"],
                         fieldbackground=t["tree_bg"], bordercolor=t["border"],
                         rowheight=26)
        style.configure("Treeview.Heading",
                         background=t["tree_heading_bg"], foreground=t["tree_heading_fg"],
                         bordercolor=t["border"], relief="flat")
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

        style.configure("StatusIdle.TLabel",
                         background=t["status_idle_bg"], foreground=t["status_idle_fg"],
                         padding=(8, 4), font=("", 9))
        style.configure("StatusWorking.TLabel",
                         background=t["status_working_bg"], foreground=t["status_working_fg"],
                         padding=(8, 4), font=("", 9, "bold"))
        style.configure("StatusBar.TFrame", background=t["status_idle_bg"])
        style.configure("StatusBarWorking.TFrame", background=t["status_working_bg"])

        if hasattr(self, "btn_theme"):
            self.btn_theme.config(text="Chiaro" if name == "dark" else "Scuro")
        if hasattr(self, "preset_desc"):
            self.preset_desc.config(style="Muted.TLabel")
        if hasattr(self, "status_frame"):
            if self._working:
                self.status_frame.config(style="StatusBarWorking.TFrame")
            else:
                self.status_frame.config(style="StatusBar.TFrame")

    def _toggle_theme(self):
        new = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new)

    def _set_working(self, working, message=""):
        self._working = working
        if working:
            self.title(f"Video Reducer - {message}")
            for btn in self._all_buttons:
                btn.config(state=tk.DISABLED)
            self.status_frame.config(style="StatusBarWorking.TFrame")
            self.status_icon.config(text=">>", style="StatusWorking.TLabel")
            self.stats_label.config(text=message, style="StatusWorking.TLabel")
            self.progress_label.config(style="StatusWorking.TLabel")
        else:
            self.title("Video Reducer")
            self.conv_controls.pack_forget()
            for btn in self._all_buttons:
                btn.config(state=tk.NORMAL)
            self.status_frame.config(style="StatusBar.TFrame")
            self.status_icon.config(text="", style="StatusIdle.TLabel")
            self.stats_label.config(style="StatusIdle.TLabel")
            self.progress_label.config(text="", style="StatusIdle.TLabel")
            self.progress["value"] = 0

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Cartella:").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(top, textvariable=self.folder_var, width=50)
        self.folder_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.btn_browse = ttk.Button(top, text="Sfoglia...", command=self._browse)
        self.btn_browse.pack(side=tk.LEFT)
        self.btn_scan = ttk.Button(top, text="Scansiona", command=self._scan, style="Accent.TButton")
        self.btn_scan.pack(side=tk.LEFT, padx=5)

        self.btn_theme = ttk.Button(top, text="Chiaro", command=self._toggle_theme)
        self.btn_theme.pack(side=tk.RIGHT)

        opts = ttk.LabelFrame(self, text="Opzioni", padding=10)
        opts.pack(fill=tk.X, padx=10, pady=5)

        row1 = ttk.Frame(opts)
        row1.pack(fill=tk.X)

        ttk.Label(row1, text="Preset:").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value="lossy")
        preset_combo = ttk.Combobox(row1, textvariable=self.preset_var,
                                     values=list(PRESETS.keys()), state="readonly", width=15)
        preset_combo.pack(side=tk.LEFT, padx=5)
        preset_combo.bind("<<ComboboxSelected>>", self._update_preset_desc)

        self.preset_desc = ttk.Label(row1, text=PRESETS["lossy"]["description"], style="Muted.TLabel")
        self.preset_desc.pack(side=tk.LEFT, padx=10)

        row2 = ttk.Frame(opts)
        row2.pack(fill=tk.X, pady=5)

        ttk.Label(row2, text="Categoria:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value="all")
        cat_combo = ttk.Combobox(row2, textvariable=self.category_var,
                                  values=["all", "heavy_codec", "large_file", "high_bitrate", "not_efficient"],
                                  state="readonly", width=15)
        cat_combo.pack(side=tk.LEFT, padx=5)
        cat_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_tree())

        self.delete_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Elimina originali dopo conversione",
                         variable=self.delete_var).pack(side=tk.LEFT, padx=20)

        row3 = ttk.Frame(opts)
        row3.pack(fill=tk.X, pady=5)

        self.lowprio_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Lavora in background (priorità bassa CPU)",
                         variable=self.lowprio_var).pack(side=tk.LEFT)

        ttk.Label(row3, text="Soglia (MB):").pack(side=tk.LEFT, padx=(20, 0))
        self.threshold_var = tk.StringVar(value="500")
        ttk.Entry(row3, textvariable=self.threshold_var, width=8).pack(side=tk.LEFT, padx=5)

        btn_row = ttk.Frame(self, padding=(10, 5))
        btn_row.pack(fill=tk.X)
        self.btn_convert = ttk.Button(btn_row, text="Converti selezionati",
                                       command=self._convert, style="Accent.TButton")
        self.btn_convert.pack(side=tk.LEFT)
        self.btn_sel_all = ttk.Button(btn_row, text="Seleziona tutti", command=self._select_all)
        self.btn_sel_all.pack(side=tk.LEFT, padx=5)
        self.btn_desel_all = ttk.Button(btn_row, text="Deseleziona tutti", command=self._deselect_all)
        self.btn_desel_all.pack(side=tk.LEFT)
        self.btn_del = ttk.Button(btn_row, text="Elimina originali convertiti",
                                   command=self._delete_originals)
        self.btn_del.pack(side=tk.LEFT, padx=20)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("sel", "nome", "dimensione", "codec", "categorie", "stato")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
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

        self.status_frame = ttk.Frame(self, style="StatusBar.TFrame", padding=(10, 6))
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_icon = ttk.Label(self.status_frame, text="", style="StatusIdle.TLabel")
        self.status_icon.pack(side=tk.LEFT)

        self.stats_label = ttk.Label(self.status_frame, text="Nessuna cartella caricata",
                                      style="StatusIdle.TLabel")
        self.stats_label.pack(side=tk.LEFT, padx=(6, 0))

        self.progress = ttk.Progressbar(self.status_frame, mode="determinate", length=250)
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress_label = ttk.Label(self.status_frame, text="", style="StatusIdle.TLabel")
        self.progress_label.pack(side=tk.RIGHT, padx=(0, 6))

        self.conv_controls = ttk.Frame(self.status_frame, style="StatusBar.TFrame")
        self.preset_indicator = ttk.Label(self.conv_controls, text="", style="StatusIdle.TLabel")
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
            self.stats_label.config(text="Conversione ripresa...")
        else:
            self._pause_event.set()
            self.btn_pause.config(text="▶ Riprendi")
            self.stats_label.config(text="In pausa...")

    def _stop_conversion(self):
        if messagebox.askyesno("Conferma", "Interrompere la conversione in corso?"):
            self._stop_event.set()
            self._pause_event.clear()
            self.stats_label.config(text="Interruzione in corso...")

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

        self._set_working(True, "Scansione in corso...")

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
            return

        cat_filter = self.category_var.get()
        filtered = []
        for fpath, entry in self.state_data["files"].items():
            if cat_filter != "all" and cat_filter not in entry["categories"]:
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
            cats = ", ".join(entry["categories"]) if entry["categories"] else "-"
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

    def _select_all(self):
        for item in self.tree.get_children():
            fpath = self._iid_to_path.get(item)
            if fpath:
                self.selected.add(fpath)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☑"
            self.tree.item(item, values=vals)

    def _deselect_all(self):
        for item in self.tree.get_children():
            fpath = self._iid_to_path.get(item)
            if fpath:
                self.selected.discard(fpath)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☐"
            self.tree.item(item, values=vals)

    def _convert(self):
        if self._working:
            return
        if not self.state_data:
            messagebox.showerror("Errore", "Scansiona prima una cartella")
            return

        keys = [fpath for fpath in self.selected
                if self.state_data["files"].get(fpath, {}).get("status") in ("pending", "error")]
        if not keys:
            messagebox.showinfo("Info", "Nessun file selezionato (o tutti già convertiti)")
            return

        preset = self.preset_var.get()
        del_orig = self.delete_var.get()
        set_low_priority(self.lowprio_var.get())

        self._stop_event.clear()
        self._pause_event.clear()

        self._set_working(True, f"Conversione di {len(keys)} file...")
        self.progress["maximum"] = len(keys)
        self.progress["value"] = 0

        self.conv_controls.config(style="StatusBarWorking.TFrame")
        self.preset_indicator.config(text=f"Preset: {preset}", style="StatusWorking.TLabel")
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
        self.title(f"Video Reducer - {pct}% - {name}")
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
            messagebox.showinfo("Interrotto", "Conversione interrotta dall'utente.")
        else:
            messagebox.showinfo("Completato", "Conversione terminata!\n"
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

        self._set_working(True, f"Eliminazione di {len(keys)} originali (verifica integrita')...")

        def do_delete():
            d, e, s = delete_originals(self.state_data, keys)
            self.after(0, lambda: self._delete_done(d, e, s))

        threading.Thread(target=do_delete, daemon=True).start()

    def _delete_done(self, deleted, errors, skipped):
        self._set_working(False)
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
        conv = sum(1 for e in self.state_data["files"].values() if e["status"] == "converted")
        saved = format_size(s["space_saved"])
        self.stats_label.config(
            text=f"File: {total} | Convertiti: {conv} | Spazio risparmiato: {saved}"
        )
