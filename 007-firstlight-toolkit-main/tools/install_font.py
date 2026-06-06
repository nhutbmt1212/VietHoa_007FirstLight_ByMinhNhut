"""
install_font.py — All-in-one: extract + build + inject font (inplace mode)

Inject/restore không tăng dung lượng file:
  - Ghi đè inplace tại slot gốc
  - Backup chỉ lưu tables + file font gốc (~500KB + ~18MB), không copy chunk
  - Restore chính xác: truncate + ghi lại tables gốc

Usage:
  python tools/install_font.py --config examples/vietnamese/font_config.json
  python tools/install_font.py --config my.json --game-dir "D:/Games/007 First Light"
  python tools/install_font.py --restore --game-dir "D:/Games/007 First Light"
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg, gfxf, steam

FONT_HASH  = "01DD9580958CDC9B"
BACKUP_DIR = "_viet_backup"


def cmd_install(args):
    game = args.game_dir or steam.find_game()
    if not game:
        print("❌ Game not found. Pass the path with --game-dir."); return 2
    chunk0 = os.path.join(game, "Runtime", "chunk0.rpkg")
    if not os.path.isfile(chunk0):
        print(f"❌ chunk0 missing: {chunk0}"); return 2
    if not os.path.isfile(args.config):
        print(f"❌ config not found: {args.config}"); return 2

    print(f"🎮 game:   {game}")
    print(f"📋 config: {args.config}")

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    # Resolve font paths relative to config file
    config_dir = os.path.dirname(os.path.abspath(args.config))
    for k, v in config.get("weights", {}).items():
        if not os.path.isabs(v):
            config["weights"][k] = os.path.join(config_dir, v)

    backup_dir = os.path.join(game, "Runtime", BACKUP_DIR)
    chunk_bak  = os.path.join(backup_dir, "chunk0.rpkg")

    print("\n📖 reading chunk0...")
    header, t1, t2 = rpkg.read_tables(chunk0)
    roff = rpkg.build_record_offsets(t2, header["hashCount"])

    found = rpkg.find_resource(t1, header["hashCount"], FONT_HASH)
    if found is None:
        print(f"❌ font resource not found: {FONT_HASH}"); return 3
    idx, off, sf = found
    rec_off = rpkg.t2_record_offset(t2, idx)
    type_str, _, dsz = rpkg.t2_record_info(t2, rec_off)
    print(f"   type = {type_str} | decompressed = {dsz:,} B")

    # ── Backup sạch lần đầu (chỉ tables, ~18MB) ──────────────────────
    created = rpkg.backup_clean(chunk0, chunk_bak)
    if created:
        print(f"\n💾 clean backup created: {chunk_bak}")
    else:
        print(f"\n💾 clean backup already exists — skip")

    # ── Backup font gốc (1 lần, ~500KB) ──────────────────────────────
    orig_font = os.path.join(backup_dir, "original_font.GFXF")
    if not os.path.isfile(orig_font):
        print("📤 extracting original font (one-time)...")
        raw, _ = rpkg.read_resource(chunk0, t1, t2, idx, roff)
        os.makedirs(backup_dir, exist_ok=True)
        with open(orig_font, "wb") as f:
            f.write(raw)
        print(f"   ✅ saved: {orig_font}")
    else:
        print("💾 original font already backed up")

    # ── Build + inject inplace ────────────────────────────────────────
    print("\n🔨 building new font...")
    src_bytes = open(orig_font, "rb").read()
    new_bytes = gfxf.build(src_bytes, config, verbose=True)
    print(f"✅ built ({len(new_bytes):,} B)")

    print("\n💉 injecting inplace...")
    before = os.path.getsize(chunk0)
    rpkg.write_resource_inplace(chunk0, t1, t2, idx, new_bytes, roff)
    rpkg.commit_tables(chunk0, t1, t2)
    after = os.path.getsize(chunk0)

    # Verify: đọc lại font sau khi inject để đảm bảo không corrupt
    print("🔍 verifying inject...")
    h_v, t1_v, t2_v = rpkg.read_tables(chunk0)
    roff_v = rpkg.build_record_offsets(t2_v, h_v["hashCount"])
    found_v = rpkg.find_resource(t1_v, h_v["hashCount"], FONT_HASH)
    if found_v is None:
        print("❌ VERIFY FAILED: font resource not found after inject!")
        return 4
    idx_v, _, _ = found_v
    raw_v, _ = rpkg.read_resource(chunk0, t1_v, t2_v, idx_v, roff_v)
    if raw_v is None:
        print("❌ VERIFY FAILED: font data corrupt after inject! Restoring original...")
        # Auto-restore font gốc ngay lập tức
        rpkg.write_resource_inplace(chunk0, t1, t2, idx, src_bytes, roff)
        rpkg.commit_tables(chunk0, t1, t2)
        print("   ↩️  Original font restored automatically.")
        return 4
    if raw_v != new_bytes:
        print(f"❌ VERIFY FAILED: data mismatch ({len(raw_v):,} vs {len(new_bytes):,})!")
        return 4
    print(f"   ✅ verify OK ({len(raw_v):,} bytes)")

    print("\n" + "=" * 50)
    print("✅ Font installed successfully! (inplace)")
    print("=" * 50)
    print(f"   chunk0 size: {before/1e9:.3f} GB → {after/1e9:.3f} GB")
    if before == after:
        print("   📦 No size change — perfect inplace inject")
    else:
        print(f"   📦 Size change: {(after-before)/1e6:+.1f} MB (fallback EOF used)")
    print(f"   backup:      {backup_dir}")
    print("\n🎮 Launch the game now.")
    return 0


def cmd_restore(args):
    game = args.game_dir or steam.find_game()
    if not game:
        print("❌ game not found"); return 2
    chunk0     = os.path.join(game, "Runtime", "chunk0.rpkg")
    backup_dir = os.path.join(game, "Runtime", BACKUP_DIR)
    chunk_bak  = os.path.join(backup_dir, "chunk0.rpkg")

    if not os.path.isdir(chunk_bak):
        print(f"❌ no backup at {chunk_bak}"); return 3

    print(f"🔄 restoring chunk0 from clean backup...")
    before = os.path.getsize(chunk0)
    rpkg.restore_clean(chunk0, chunk_bak)
    after = os.path.getsize(chunk0)
    print(f"✅ restored: {before/1e9:.3f} GB → {after/1e9:.3f} GB")
    return 0


def main():
    ap = argparse.ArgumentParser(description="007 First Light — Font Installer (inplace)")
    ap.add_argument("--config",   help="JSON config (TTF mapping + codepoints)")
    ap.add_argument("--game-dir", help="manually specify the game folder")
    ap.add_argument("--restore",  action="store_true", help="restore original font")
    args = ap.parse_args()

    if args.restore:
        return cmd_restore(args)
    if not args.config:
        ap.print_help(); return 1
    return cmd_install(args)


if __name__ == "__main__":
    sys.exit(main())
