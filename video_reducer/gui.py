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

        if hasattr(self, "btn_theme"):
            self.btn_theme.config(text="Chiaro" if name == "dark" else "Scuro")
        if hasattr(self, "preset_desc"):
            self.preset_desc.config(style="Muted.TLabel")

    def _toggle_theme(self):
        new = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new)

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Cartella:").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(top, textvariable=self.folder_var, width=50)
        self.folder_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(top, text="Sfoglia...", command=self._browse).pack(side=tk.LEFT)
        ttk.Button(top, text="Scansiona", command=self._scan, style="Accent.TButton").pack(side=tk.LEFT, padx=5)

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
        ttk.Combobox(row2, textvariable=self.category_var,
                      values=["all", "heavy_codec", "large_file", "high_bitrate", "not_efficient"],
                      state="readonly", width=15).pack(side=tk.LEFT, padx=5)

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
        ttk.Button(btn_row, text="Seleziona tutti", command=self._select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="Deseleziona tutti", command=self._deselect_all).pack(side=tk.LEFT)
        self.btn_del = ttk.Button(btn_row, text="Elimina originali convertiti",
                                   command=self._delete_originals)
        self.btn_del.pack(side=tk.LEFT, padx=20)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("sel", "nome", "dimensione", "codec", "categorie", "stato")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("sel", text="✓")
        self.tree.heading("nome", text="Nome file")
        self.tree.heading("dimensione", text="Dimensione")
        self.tree.heading("codec", text="Codec")
        self.tree.heading("categorie", text="Categorie")
        self.tree.heading("stato", text="Stato")
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

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill=tk.X)

        self.stats_label = ttk.Label(bottom, text="Nessuna cartella caricata")
        self.stats_label.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(bottom, mode="determinate", length=200)
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress_label = ttk.Label(bottom, text="")
        self.progress_label.pack(side=tk.RIGHT)

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

    def _scan(self):
        folder = self.folder_var.get()
        if not folder or not Path(folder).is_dir():
            messagebox.showerror("Errore", "Seleziona una cartella valida")
            return

        try:
            threshold = int(self.threshold_var.get())
        except ValueError:
            threshold = 500

        self.stats_label.config(text="Scansione in corso...")
        self.update_idletasks()

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
            self.after(0, self._refresh_tree)
            self.after(0, self._update_stats)
            self.after(0, lambda: messagebox.showinfo(
                "Scansione completata",
                f"Trovati {len(state['files'])} file video ({new_count} nuovi)"))

        threading.Thread(target=do_scan, daemon=True).start()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.selected.clear()
        if not self.state_data:
            return

        cat_filter = self.category_var.get()
        for fpath, entry in self.state_data["files"].items():
            if cat_filter != "all" and cat_filter not in entry["categories"]:
                continue
            cats = ", ".join(entry["categories"]) if entry["categories"] else "-"
            status = entry["status"]
            if entry["original_deleted"]:
                status += " [DEL]"
            self.tree.insert("", tk.END, iid=fpath, values=(
                "☐", Path(fpath).name, format_size(entry["original_size"]),
                entry["codec"], cats, status,
            ))

    def _toggle_selection(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item or col != "#1":
            return

        if item in self.selected:
            self.selected.discard(item)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☐"
            self.tree.item(item, values=vals)
        else:
            self.selected.add(item)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☑"
            self.tree.item(item, values=vals)

    def _select_all(self):
        for item in self.tree.get_children():
            self.selected.add(item)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☑"
            self.tree.item(item, values=vals)

    def _deselect_all(self):
        for item in self.tree.get_children():
            self.selected.discard(item)
            vals = list(self.tree.item(item, "values"))
            vals[0] = "☐"
            self.tree.item(item, values=vals)

    def _convert(self):
        if not self.state_data:
            messagebox.showerror("Errore", "Scansiona prima una cartella")
            return

        keys = [k for k in self.selected if self.state_data["files"].get(k, {}).get("status") in ("pending", "error")]
        if not keys:
            messagebox.showinfo("Info", "Nessun file selezionato (o tutti già convertiti)")
            return

        preset = self.preset_var.get()
        del_orig = self.delete_var.get()
        set_low_priority(self.lowprio_var.get())

        self.btn_convert.config(state=tk.DISABLED)
        self.progress["maximum"] = len(keys)
        self.progress["value"] = 0

        def progress_cb(current, total, fpath, msg):
            self.after(0, lambda: self._update_progress(current, total, fpath, msg))

        def do_convert():
            process_files(self.state_data, keys, preset, del_orig, progress_cb)
            self.after(0, self._conversion_done)

        threading.Thread(target=do_convert, daemon=True).start()

    def _update_progress(self, current, total, fpath, msg):
        self.progress["value"] = current
        self.progress_label.config(text=f"{current}/{total}")
        name = Path(fpath).name
        self.stats_label.config(text=f"{name}: {msg}")
        entry = self.state_data["files"].get(fpath)
        if entry and self.tree.exists(fpath):
            status = entry["status"]
            if entry["original_deleted"]:
                status += " [DEL]"
            vals = list(self.tree.item(fpath, "values"))
            vals[5] = status
            self.tree.item(fpath, values=vals)

    def _conversion_done(self):
        self.btn_convert.config(state=tk.NORMAL)
        self._update_stats()
        self._refresh_tree()
        messagebox.showinfo("Completato", "Conversione terminata!\n"
                            f"Spazio risparmiato: {format_size(self.state_data['stats']['space_saved'])}")

    def _delete_originals(self):
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

        deleted, errors, skipped = delete_originals(self.state_data, keys)
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
