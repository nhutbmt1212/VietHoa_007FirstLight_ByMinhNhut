"""
restore_font_original.py
------------------------
Inject lai font GOC (original_font.GFXF) vao chunk0.rpkg.

Su dung dung luong cua install_font.py nhung inject nguoc lai:
  thay vi build font Viet moi, inject thang original_font.GFXF
  da duoc backup khi lan dau chay install_font.

Khong can backup tables, khong can copy file —
chi inject inplace tai slot cu (dam bao file size khong doi).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '007-firstlight-toolkit-main'))
from glacier import rpkg, steam

FONT_HASH  = "01DD9580958CDC9B"
BACKUP_DIR = "_viet_backup"

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Restore font goc vao chunk0")
    ap.add_argument("--game-dir", help="Thu muc game (tu dong tim neu bo trong)")
    args = ap.parse_args()

    game = args.game_dir or steam.find_game()
    if not game:
        print("LOI: Khong tim thay game. Dung --game-dir de chi ro duong dan.")
        return 2

    chunk0    = os.path.join(game, "Runtime", "chunk0.rpkg")
    orig_font = os.path.join(game, "Runtime", BACKUP_DIR, "original_font.GFXF")

    print("=" * 55)
    print("RESTORE FONT GOC")
    print("=" * 55)
    print(f"  game:       {game}")
    print(f"  chunk0:     {chunk0}")
    print(f"  orig font:  {orig_font}")
    print()

    # ── Kiem tra file ton tai ──────────────────────────────────────
    if not os.path.isfile(chunk0):
        print(f"LOI: Khong tim thay chunk0:\n  {chunk0}")
        return 2

    if not os.path.isfile(orig_font):
        print(f"LOI: Khong tim thay original_font.GFXF tai:\n  {orig_font}")
        print()
        print("Nguyen nhan co the:")
        print("  - Chua tung chay inject font lan nao")
        print("  - Da xoa thu muc _viet_backup")
        print("  - Font game van la ban goc, khong can restore")
        return 3

    orig_bytes = open(orig_font, "rb").read()
    print(f"Font goc: {len(orig_bytes):,} bytes | magic: {orig_bytes[:4].hex()}")

    # ── Doc tables tu chunk0 hien tai ─────────────────────────────
    print("\nDoc tables chunk0...")
    try:
        header, t1, t2 = rpkg.read_tables(chunk0)
        roff = rpkg.build_record_offsets(t2, header["hashCount"])
    except Exception as e:
        print(f"LOI doc tables: {e}")
        return 4

    found = rpkg.find_resource(t1, header["hashCount"], FONT_HASH)
    if found is None:
        print(f"LOI: Khong tim thay font hash {FONT_HASH} trong chunk0!")
        return 4

    idx, off, sf = found
    comp_size = sf & 0x3FFFFFFF
    print(f"Font slot: offset={off:,}  comp={comp_size:,}")

    # ── Kiem tra xem font co phai da la goc chua ─────────────────
    print("Kiem tra font hien tai trong chunk0...")
    try:
        raw_cur, _ = rpkg.read_resource(chunk0, t1, t2, idx, roff)
        if raw_cur == orig_bytes:
            print("Font da la ban goc — khong can restore.")
            print("\nXONG (khong co gi thay doi).")
            return 0
        print(f"  Font hien tai: {len(raw_cur):,} bytes")
        print(f"  Font goc:      {len(orig_bytes):,} bytes")
        print("  -> Khac nhau, tien hanh restore...")
    except Exception as e:
        print(f"  Khong the doc font hien tai: {e}")
        print("  -> Tien hanh restore font goc...")

    # ── Inject font goc vao slot (inplace) ────────────────────────
    print("\nInjecting font goc (inplace)...")
    before = os.path.getsize(chunk0)
    try:
        rpkg.write_resource_inplace(chunk0, t1, t2, idx, orig_bytes, roff)
        rpkg.commit_tables(chunk0, t1, t2)
    except Exception as e:
        print(f"LOI inject: {e}")
        return 4

    after = os.path.getsize(chunk0)
    print(f"  chunk0: {before:,} -> {after:,} bytes", end="")
    if before == after:
        print(" (size khong doi — inplace OK)")
    else:
        print(f" (tang {after-before:+,} bytes — EOF fallback)")

    # ── Verify ────────────────────────────────────────────────────
    print("Verify...")
    try:
        h2, t1_2, t2_2 = rpkg.read_tables(chunk0)
        roff2 = rpkg.build_record_offsets(t2_2, h2["hashCount"])
        raw_v, _ = rpkg.read_resource(chunk0, t1_2, t2_2, idx, roff2)
        if raw_v == orig_bytes:
            print("  OK — font goc da duoc restore chinh xac!")
        else:
            print(f"  CANH BAO: Verify FAIL! ({len(raw_v):,} vs {len(orig_bytes):,})")
            return 5
    except Exception as e:
        print(f"  LOI verify: {e}")
        return 5

    print()
    print("=" * 55)
    print("XONG! Font goc da duoc restore thanh cong.")
    print("=" * 55)
    return 0

if __name__ == "__main__":
    sys.exit(main())
