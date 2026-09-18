import argparse
import sys
from pathlib import Path

from . import __version__
from .scanner import scan_folder
from .converter import (
    PRESETS, process_files, delete_originals, format_size,
)
from .state import (
    default_state, default_file_entry, load_state, save_state, recalc_stats,
)


def main():
    parser = argparse.ArgumentParser(
        prog="video_reducer",
        description="Video Reducer — riduce le dimensioni dei file video tramite codec ad alta efficienza",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", help="Comandi disponibili")

    # --- scan ---
    p_scan = sub.add_parser("scan", help="Scansiona una cartella e mappa tutti i video")
    p_scan.add_argument("folder", help="Cartella da scansionare")
    p_scan.add_argument("--size-threshold", type=int, default=500,
                        help="Soglia in MB per la categoria 'large_file' (default: 500)")
    p_scan.add_argument("--no-recursive", action="store_true",
                        help="Non scansionare le sottocartelle")

    # --- list ---
    p_list = sub.add_parser("list", help="Mostra i file mappati")
    p_list.add_argument("folder", help="Cartella mappata")
    p_list.add_argument("--category", choices=["heavy_codec", "large_file", "high_bitrate", "not_efficient", "all"],
                        default="all", help="Filtra per categoria")
    p_list.add_argument("--status", choices=["pending", "converted", "error", "converting", "all"],
                        default="all", help="Filtra per stato")

    # --- convert ---
    p_conv = sub.add_parser("convert", help="Converti i file video")
    p_conv.add_argument("folder", help="Cartella mappata")
    p_conv.add_argument("--preset", choices=list(PRESETS.keys()), default="lossy",
                        help="Preset di conversione (default: lossy)")
    p_conv.add_argument("--category", choices=["heavy_codec", "large_file", "high_bitrate", "not_efficient", "all"],
                        default="all", help="Converti solo file di questa categoria")
    p_conv.add_argument("--files", nargs="+", help="Converti solo questi file specifici")
    p_conv.add_argument("--delete-originals", action="store_true",
                        help="Elimina gli originali dopo la conversione (con verifica)")

    # --- delete-originals ---
    p_del = sub.add_parser("delete-originals", help="Elimina i file originali già convertiti")
    p_del.add_argument("folder", help="Cartella mappata")
    p_del.add_argument("--force", action="store_true",
                        help="Elimina anche file non convertiti (ATTENZIONE)")

    # --- stats ---
    p_stats = sub.add_parser("stats", help="Mostra statistiche sullo spazio risparmiato")
    p_stats.add_argument("folder", help="Cartella mappata")

    # --- presets ---
    sub.add_parser("presets", help="Mostra i preset di conversione disponibili")

    # --- gui ---
    sub.add_parser("gui", help="Avvia l'interfaccia grafica")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "presets":
        cmd_presets()
    elif args.command == "gui":
        cmd_gui()
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "convert":
        cmd_convert(args)
    elif args.command == "delete-originals":
        cmd_delete_originals(args)
    elif args.command == "stats":
        cmd_stats(args)


def cmd_presets():
    print("Preset di conversione disponibili:\n")
    for name, p in PRESETS.items():
        print(f"  {name:15s} — {p['description']}")
    print()


def cmd_gui():
    try:
        from .gui import run_gui
        run_gui()
    except ImportError as e:
        print(f"Errore: tkinter non disponibile ({e})")
        print("Installa python3-tk (Debian: apt install python3-tk)")
        sys.exit(1)


def cmd_scan(args):
    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"Errore: '{folder}' non è una cartella valida")
        sys.exit(1)

    state = load_state(folder)
    if state is None:
        state = default_state(folder)
        print(f"Nuova scansione di: {folder}")
    else:
        print(f"Aggiornamento scansione esistente di: {folder}")

    print("Scansione in corso...", flush=True)
    found = scan_folder(folder, args.size_threshold, not args.no_recursive)

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

    total = len(state["files"])
    print(f"\nScansione completata:")
    print(f"  File totali mappati: {total}")
    print(f"  Nuovi file trovati:  {new_count}")
    print(f"  Dimensione totale:   {format_size(state['stats']['total_original_size'])}")

    cats = {}
    for e in state["files"].values():
        for c in e["categories"]:
            cats[c] = cats.get(c, 0) + 1
    if cats:
        print(f"\nCategorie:")
        for c, n in sorted(cats.items()):
            print(f"  {c:20s}: {n} file")


def cmd_list(args):
    folder = Path(args.folder).resolve()
    state = load_state(folder)
    if not state:
        print("Errore: cartella non ancora scansionata. Esegui prima 'scan'.")
        sys.exit(1)

    entries = []
    for fpath, entry in state["files"].items():
        if args.category != "all" and args.category not in entry["categories"]:
            continue
        if args.status != "all" and entry["status"] != args.status:
            continue
        entries.append((fpath, entry))

    if not entries:
        print("Nessun file corrisponde ai criteri.")
        return

    print(f"\n{'#':>4}  {'Stato':10s}  {'Dimensione':>12s}  {'Codec':12s}  {'Categorie':30s}  File")
    print("-" * 120)
    for i, (fpath, e) in enumerate(entries, 1):
        cats = ", ".join(e["categories"]) if e["categories"] else "-"
        status = e["status"]
        if e["original_deleted"]:
            status += " [DEL]"
        print(f"{i:4d}  {status:10s}  {format_size(e['original_size']):>12s}  {e['codec']:12s}  {cats:30s}  {Path(fpath).name}")

    print(f"\nTotale: {len(entries)} file")


def cmd_convert(args):
    folder = Path(args.folder).resolve()
    state = load_state(folder)
    if not state:
        print("Errore: cartella non ancora scansionata. Esegui prima 'scan'.")
        sys.exit(1)

    if args.files:
        keys = []
        for f in args.files:
            p = str(Path(f).resolve())
            if p in state["files"]:
                keys.append(p)
            else:
                print(f"Attenzione: '{f}' non trovato nella mappa, ignorato.")
    else:
        keys = [
            fpath for fpath, e in state["files"].items()
            if e["status"] in ("pending", "error")
            and (args.category == "all" or args.category in e["categories"])
        ]

    if not keys:
        print("Nessun file da convertire.")
        return

    preset = PRESETS[args.preset]
    print(f"\nConversione di {len(keys)} file con preset '{args.preset}'")
    print(f"  {preset['description']}")
    if args.delete_originals:
        print("  ⚠ Gli originali verranno eliminati dopo la conversione")
    print()

    def progress(current, total, fpath, msg):
        name = Path(fpath).name
        pct = current / total * 100
        print(f"  [{current}/{total} {pct:5.1f}%] {name}: {msg}")

    process_files(state, keys, args.preset, args.delete_originals, progress)

    recalc_stats(state)
    save_state(state)
    print(f"\nSpazio risparmiato totale: {format_size(state['stats']['space_saved'])}")


def cmd_delete_originals(args):
    folder = Path(args.folder).resolve()
    state = load_state(folder)
    if not state:
        print("Errore: cartella non ancora scansionata. Esegui prima 'scan'.")
        sys.exit(1)

    not_converted = [
        fpath for fpath, e in state["files"].items()
        if e["status"] != "converted" and not e["original_deleted"]
    ]
    converted = [
        fpath for fpath, e in state["files"].items()
        if e["status"] == "converted" and not e["original_deleted"]
    ]

    if not converted and not args.force:
        print("⚠ ATTENZIONE: Nessun file è stato convertito!")
        print(f"   Ci sono {len(not_converted)} file non convertiti.")
        resp = input("   Vuoi comunque eliminare tutti gli originali? (s/N): ").strip().lower()
        if resp != "s":
            print("Operazione annullata.")
            return
        keys = not_converted
    elif converted:
        keys = converted
        if not_converted:
            print(f"ℹ {len(not_converted)} file non ancora convertiti verranno mantenuti.")
    else:
        print("Nessun file originale da eliminare.")
        return

    print(f"\nEliminazione di {len(keys)} file originali convertiti...")
    deleted, errors, skipped = delete_originals(state, keys)

    print(f"\n  Eliminati: {deleted}")
    if errors:
        print(f"  Errori:    {len(errors)}")
        for fpath, err in errors:
            print(f"    {Path(fpath).name}: {err}")
    if skipped:
        print(f"  Saltati (non convertiti): {len(skipped)}")


def cmd_stats(args):
    folder = Path(args.folder).resolve()
    state = load_state(folder)
    if not state:
        print("Errore: cartella non ancora scansionata. Esegui prima 'scan'.")
        sys.exit(1)

    recalc_stats(state)

    total = len(state["files"])
    pending = sum(1 for e in state["files"].values() if e["status"] == "pending")
    converted = sum(1 for e in state["files"].values() if e["status"] == "converted")
    errors = sum(1 for e in state["files"].values() if e["status"] == "error")
    deleted = sum(1 for e in state["files"].values() if e["original_deleted"])
    converting = sum(1 for e in state["files"].values() if e["status"] == "converting")

    s = state["stats"]
    print(f"\n=== Statistiche Video Reducer ===")
    print(f"  Cartella:             {state['scan_root']}")
    print(f"  Data scansione:       {state['scan_date']}")
    print(f"  File totali:          {total}")
    print(f"  In attesa:            {pending}")
    if converting:
        print(f"  In conversione:       {converting}")
    print(f"  Convertiti:           {converted}")
    if errors:
        print(f"  Errori:               {errors}")
    print(f"  Originali eliminati:  {deleted}")
    print(f"\n  Dim. originali:       {format_size(s['total_original_size'])}")
    print(f"  Dim. dopo conversione:{format_size(s['total_converted_size'])}")
    print(f"  Spazio risparmiato:   {format_size(s['space_saved'])}")
    if s["total_original_size"] > 0:
        pct = s["space_saved"] / s["total_original_size"] * 100
        print(f"  Riduzione:            {pct:.1f}%")
    print()
