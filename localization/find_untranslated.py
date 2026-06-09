"""
find_untranslated.py
====================
Tìm tất cả text tiếng Anh chưa dịch trong game:
  1. So sánh extracted/ (bản gốc) với translations/ (bản dịch)
  2. Liệt kê các chunk chưa được extract (chunk2, chunk3patch...)
  3. Tìm LOCR entries dài (email/note/intel) chưa dịch

Chạy: python localization\find_untranslated.py
"""
import json, re, sys, os
from pathlib import Path

sys.path.insert(0, r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main")
from glacier import rpkg, locr, dlge, steam

GAME_DIR      = r"d:\Games\007 First Light"
VIET_DIALOGUE = r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"
VIET_UI       = r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main\examples\vietnamese\translations\ui.json"
SRC_DIALOGUE  = r"d:\VietHoa_007FirstLight\localization\extracted\dialogue.json"
SRC_UI        = r"d:\VietHoa_007FirstLight\localization\extracted\ui.json"
OUT_DIR       = r"d:\VietHoa_007FirstLight\localization\found_untranslated"

VIET_RE = re.compile(r"[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỷỹỵ]")

def is_translated(vi: str, en: str) -> bool:
    if not vi or vi.strip() == en.strip():
        return False
    if VIET_RE.search(vi):
        return True
    # Proper noun / số giữ nguyên
    if len(vi.strip()) < 30:
        return True
    return False

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=" * 65)
    print("  Tìm text chưa dịch trong game")
    print("=" * 65)

    # ── 1. Liệt kê tất cả chunks ────────────────────────────────
    chunks = steam.chunk_paths(GAME_DIR)
    print(f"\n[CHUNKS trong Runtime/]")
    for c in chunks:
        sz = os.path.getsize(c) / 1e9
        print(f"  {os.path.basename(c):<30} {sz:.3f} GB")

    # Chunks chưa được extract (không phải chunk0, chunk1)
    extracted_chunks = {"chunk0.rpkg", "chunk1.rpkg"}
    unknown_chunks = [c for c in chunks
                      if os.path.basename(c) not in extracted_chunks]
    if unknown_chunks:
        print(f"\n[!] {len(unknown_chunks)} chunk chưa được extract:")
        for c in unknown_chunks:
            print(f"     {os.path.basename(c)}")

    # ── 2. Dialogue chưa dịch (so sánh src vs translations) ─────
    print(f"\n[DIALOGUE chưa dịch]")
    src_dlg  = json.loads(Path(SRC_DIALOGUE).read_text(encoding="utf-8"))
    viet_dlg = {}
    if Path(VIET_DIALOGUE).exists():
        viet_dlg = json.loads(Path(VIET_DIALOGUE).read_text(encoding="utf-8"))

    untrans_dlg = []
    for key, entry in src_dlg.items():
        ventry = viet_dlg.get(key, {})
        spk = entry.get("speaker_name", "")
        for sk, en_text in entry.get("segments", {}).items():
            vi_text = ventry.get("segments", {}).get(sk, en_text)
            if not is_translated(vi_text, en_text):
                untrans_dlg.append({
                    "key": key, "seg": sk, "speaker": spk,
                    "en": en_text, "vi": vi_text
                })

    print(f"  Chưa dịch: {len(untrans_dlg):,} / {sum(len(e.get('segments',{})) for e in src_dlg.values()):,} segments")
    if untrans_dlg[:20]:
        print("  20 ví dụ đầu:")
        for x in untrans_dlg[:20]:
            print(f"    [{x['speaker']}] {x['en'][:70]}")

    # Lưu file
    out_dlg = os.path.join(OUT_DIR, "untranslated_dialogue.json")
    with open(out_dlg, "w", encoding="utf-8") as f:
        json.dump(untrans_dlg, f, ensure_ascii=False, indent=2)
    print(f"  → Lưu: {out_dlg}")

    # ── 3. UI dài chưa dịch (email/note/intel) ──────────────────
    print(f"\n[UI dài chưa dịch — email/note/intel (>100 ký tự)]")
    src_ui  = json.loads(Path(SRC_UI).read_text(encoding="utf-8"))
    viet_ui = {}
    if Path(VIET_UI).exists():
        viet_ui = json.loads(Path(VIET_UI).read_text(encoding="utf-8"))

    untrans_ui_long = []
    for ok, strings in src_ui.items():
        for ik, en_text in strings.items():
            if len(en_text) < 100:
                continue  # Chỉ quan tâm text dài
            vi_text = viet_ui.get(ok, {}).get(ik, en_text)
            if not is_translated(vi_text, en_text):
                untrans_ui_long.append({
                    "outer_key": ok, "inner_key": ik,
                    "en": en_text, "vi": vi_text,
                    "len": len(en_text)
                })

    untrans_ui_long.sort(key=lambda x: -x["len"])
    print(f"  Text dài chưa dịch: {len(untrans_ui_long):,}")
    if untrans_ui_long[:10]:
        print("  10 text dài nhất:")
        for x in untrans_ui_long[:10]:
            print(f"    [{x['len']} chars] {x['en'][:80]}...")

    out_ui = os.path.join(OUT_DIR, "untranslated_ui_long.json")
    with open(out_ui, "w", encoding="utf-8") as f:
        json.dump(untrans_ui_long, f, ensure_ascii=False, indent=2)
    print(f"  → Lưu: {out_ui}")

    # ── 4. Scan các chunk chưa extract để tìm text EN ───────────
    if unknown_chunks:
        print(f"\n[SCAN chunks chưa extract]")
        for chunk_path in unknown_chunks:
            name = os.path.basename(chunk_path)
            print(f"\n  Đọc {name}...")
            try:
                header, t1, t2 = rpkg.read_tables(chunk_path)
                roff = rpkg.build_record_offsets(t2, header["hashCount"])
                found_locr = found_dlge = 0
                samples = []

                for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
                    type_rev = bytes(t2[roff[idx]:roff[idx]+4])

                    if type_rev == rpkg.TYPE_LOCR:
                        raw, _ = rpkg.read_resource(chunk_path, t1, t2, idx, roff)
                        if raw is None: continue
                        strings = locr.extract_strings(raw, 1)
                        for k, v in strings.items():
                            if len(v) > 80 and not VIET_RE.search(v):
                                samples.append(("LOCR", "%016X"%h, v[:120]))
                                found_locr += 1

                    elif type_rev == rpkg.TYPE_DLGE:
                        raw, _ = rpkg.read_resource(chunk_path, t1, t2, idx, roff)
                        if raw is None: continue
                        text = dlge.get_base_text(raw)
                        if not text: continue
                        segs = dlge.parse_segments(text)
                        for sk, sv in segs.items():
                            if len(sv) > 50 and not VIET_RE.search(sv):
                                found_dlge += 1

                print(f"    LOCR text dài EN: {found_locr}")
                print(f"    DLGE text dài EN: {found_dlge}")
                if samples[:5]:
                    print(f"    Ví dụ LOCR dài:")
                    for typ, hh, txt in samples[:5]:
                        print(f"      {hh}: {txt}")

                # Lưu samples
                out_chunk = os.path.join(OUT_DIR, f"untranslated_{name}.json")
                with open(out_chunk, "w", encoding="utf-8") as f:
                    json.dump(samples, f, ensure_ascii=False, indent=2)
                print(f"    → Lưu: {out_chunk}")

            except Exception as e:
                print(f"  [LỖI] {e}")

    print()
    print("=" * 65)
    print(f"  Kết quả lưu tại: {OUT_DIR}")
    print("=" * 65)
    return 0

if __name__ == "__main__":
    sys.exit(main())
