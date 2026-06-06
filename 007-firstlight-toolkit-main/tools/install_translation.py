"""
install_translation.py — All-in-one translation installer (inplace mode)

Inject/restore hoàn toàn không tăng dung lượng file:
  - Ghi đè inplace tại slot gốc (không append EOF)
  - Backup chỉ lưu tables (~18MB tổng), không copy file 20-33GB
  - Restore chính xác: truncate + ghi lại tables gốc

Usage:
  python tools/install_translation.py --config examples/vietnamese/translation_config.json
  python tools/install_translation.py --config ... --game-dir "D:/Games/007 First Light"
  python tools/install_translation.py --restore --game-dir "D:/Games/007 First Light"
  python tools/install_translation.py --config ... --dry

Config schema (JSON):
{
  "language": "none",
  "ui":        "path/to/ui.json",
  "dialogue":  "path/to/dialogue.json",
  "speakers":  "path/to/speakers.json",
  "game_dir":  "..."   (optional)
}
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg, locr, dlge, gfxf, shaping, steam

FONT_HASH  = "01DD9580958CDC9B"
BACKUP_DIR = "_viet_backup"   # tên thư mục backup trong Runtime/


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_install(config_path, game_dir_arg=None, dry_run=False):
    if not os.path.isfile(config_path):
        print(f"❌ config not found: {config_path}"); return 2
    config_dir = os.path.dirname(os.path.abspath(config_path))
    config = load_json(config_path)

    def resolve(p):
        if p is None: return None
        return p if os.path.isabs(p) else os.path.join(config_dir, p)

    language     = config.get("language", "none")
    font_cfg_path = resolve(config.get("font"))
    ui_path      = resolve(config.get("ui"))
    dlg_path     = resolve(config.get("dialogue"))
    spk_path     = resolve(config.get("speakers"))
    game         = game_dir_arg or config.get("game_dir") or steam.find_game()

    if not game or not os.path.isfile(os.path.join(game, "Runtime", "chunk0.rpkg")):
        print("❌ game not found. Set game_dir in config or pass --game-dir.")
        return 2

    print(f"🎮 game:      {game}")
    print(f"🌐 language:  {language}")
    print(f"   ui:        {ui_path or '(none)'}")
    print(f"   dialogue:  {dlg_path or '(none)'}")
    print(f"   speakers:  {spk_path or '(none)'}")
    print(f"   font:      {font_cfg_path or '(none)'}")
    if dry_run:
        print("\n*** DRY RUN — no writes ***\n")

    # shaping
    if language in ("arabic", "persian", "urdu", "pashto", "kashmiri", "sindhi"):
        shape_fn       = shaping.shape_line  if shaping.AVAILABLE else shaping.identity
        shape_block_fn = shaping.shape_block if shaping.AVAILABLE else (lambda t: t)
    else:
        shape_fn       = shaping.identity
        shape_block_fn = lambda t: t

    ui_data   = load_json(ui_path)  if ui_path  else {}
    dlg_data  = load_json(dlg_path) if dlg_path else {}
    spk_data  = load_json(spk_path) if spk_path else {}
    spk_clean = {k: v for k, v in spk_data.items() if v}

    chunks = steam.chunk_paths(game)
    if not chunks:
        print(f"❌ no chunks in {game}/Runtime/"); return 3

    backup_root = os.path.join(game, "Runtime", BACKUP_DIR)

    for chunk in chunks:
        name = os.path.basename(chunk)
        print(f"\n=== {name} ===")

        # ── Backup sạch lần đầu (chỉ tables, ~18MB, không bao giờ ghi đè) ──
        if not dry_run:
            chunk_bak = os.path.join(backup_root, name)
            created = rpkg.backup_clean(chunk, chunk_bak)
            if created:
                print(f"   💾 clean backup created ({chunk_bak})")
            else:
                print(f"   💾 clean backup already exists — skip")

        header, t1, t2 = rpkg.read_tables(chunk)
        roff = rpkg.build_record_offsets(t2, header["hashCount"])
        n_ui = n_dlg = n_spk = 0

        # ── 1) LOCR (UI strings) ──────────────────────────────────────────
        if ui_data:
            for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
                if bytes(t2[roff[idx]:roff[idx] + 4]) != rpkg.TYPE_LOCR:
                    continue
                hh = "%016X" % h
                if hh not in ui_data:
                    continue
                raw, _ = rpkg.read_resource(chunk, t1, t2, idx, roff)
                if raw is None: continue
                translations = {k.upper(): shape_block_fn(v)
                                for k, v in ui_data[hh].items()}
                try:
                    new_raw, ginj = locr.rebuild(raw, translations, lang_index=1)
                except Exception:
                    continue
                if ginj == 0: continue
                n_ui += ginj
                if dry_run: continue
                rpkg.write_resource_inplace(chunk, t1, t2, idx, new_raw, roff)

        # ── 2+3) DLGE + speakers ──────────────────────────────────────────
        if dlg_data or spk_clean:
            for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
                if bytes(t2[roff[idx]:roff[idx] + 4]) != rpkg.TYPE_DLGE:
                    continue
                raw, _ = rpkg.read_resource(chunk, t1, t2, idx, roff)
                if raw is None: continue
                hh = "%016X" % h
                changed = False

                if hh in dlg_data:
                    segs = dlg_data[hh].get("segments")
                    if segs:
                        new_raw = dlge.inject_spoken(raw, segs, shape_fn=shape_block_fn)
                        if new_raw is not None:
                            raw = new_raw; changed = True; n_dlg += 1

                if spk_clean:
                    new_raw = dlge.inject_speaker(raw, spk_clean, shape_fn=shape_fn)
                    if new_raw is not None:
                        raw = new_raw; changed = True; n_spk += 1

                if not changed or dry_run: continue
                rpkg.write_resource_inplace(chunk, t1, t2, idx, raw, roff)

        # ── 4) FONT (chunk0 only) ─────────────────────────────────────────
        if font_cfg_path and chunk == chunks[0]:
            found = rpkg.find_resource(t1, header["hashCount"], FONT_HASH)
            if found is not None:
                idx_f, _, _ = found
                font_backup_file = os.path.join(backup_root, "original_font.GFXF")
                if not os.path.isfile(font_backup_file):
                    raw_f, _ = rpkg.read_resource(chunk, t1, t2, idx_f, roff)
                    os.makedirs(backup_root, exist_ok=True)
                    with open(font_backup_file, "wb") as f: f.write(raw_f)
                    print(f"   💾 original font backed up")
                src_bytes  = open(font_backup_file, "rb").read()
                font_config = load_json(font_cfg_path)
                new_font   = gfxf.build(src_bytes, font_config, verbose=False)
                print(f"   🔤 font built: {len(new_font):,} B")
                if not dry_run:
                    rpkg.write_resource_inplace(chunk, t1, t2, idx_f, new_font, roff)

        if not dry_run:
            rpkg.commit_tables(chunk, t1, t2)
        print(f"   ✅ UI: {n_ui:,}  dialogue: {n_dlg:,}  speakers: {n_spk:,}")

    print("\n" + "=" * 50)
    if dry_run:
        print("✅ Dry run complete — no changes written.")
    else:
        size_info = []
        for chunk in chunks:
            sz = os.path.getsize(chunk)
            size_info.append(f"{os.path.basename(chunk)}: {sz/1e9:.3f} GB")
        print("✅ Translation installed! (inplace — file size unchanged)")
        for s in size_info:
            print(f"   {s}")
        print(f"   backup: {backup_root} (~18 MB tables only)")
        print("\n🎮 Launch the game now.")
    print("=" * 50)
    return 0


def cmd_restore(game_dir_arg=None):
    game = game_dir_arg or steam.find_game()
    if not game:
        print("❌ game not found"); return 2
    backup_root = os.path.join(game, "Runtime", BACKUP_DIR)
    if not os.path.isdir(backup_root):
        print(f"❌ no backup at {backup_root}"); return 3

    chunks = steam.chunk_paths(game)
    for chunk in chunks:
        name = os.path.basename(chunk)
        chunk_bak = os.path.join(backup_root, name)
        if os.path.isdir(chunk_bak):
            print(f"🔄 restoring {name}...")
            before = os.path.getsize(chunk)
            rpkg.restore_clean(chunk, chunk_bak)
            after = os.path.getsize(chunk)
            print(f"   {before/1e9:.3f} GB → {after/1e9:.3f} GB")
        else:
            print(f"   ⚠️  no backup for {name} — skip")

    print("✅ Restored to original state.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="007 First Light — Translation Installer (inplace)")
    ap.add_argument("--config",   help="JSON config with paths to ui/dialogue/speakers/font")
    ap.add_argument("--game-dir", help="manually specify the game folder")
    ap.add_argument("--dry",      action="store_true", help="dry run — no writes")
    ap.add_argument("--restore",  action="store_true", help="restore original from backup")
    args = ap.parse_args()

    if args.restore:
        return cmd_restore(args.game_dir)
    if not args.config:
        ap.print_help(); return 1
    return cmd_install(args.config, args.game_dir, dry_run=args.dry)


if __name__ == "__main__":
    sys.exit(main())
