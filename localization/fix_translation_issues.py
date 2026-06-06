"""
fix_translation_issues.py
=========================
Fix các lỗi trong bản dịch hiện có mà không cần dịch lại từ đầu:

  1. Khoảng trắng đen / weird spaces -> space thường
  2. Nhiều khoảng trắng liên tiếp -> 1
  3. Bond tự xưng 'anh' -> 'tôi'
  4. Valhalla/Arbiter dùng 'tôi' -> 'ta'
  5. Kẻ thù cấp thấp dùng 'tôi' -> 'tao'
  6. Khoảng trắng trước dấu câu
  7. HTML tag spacing

Chạy: python fix_translation_issues.py [--ui] [--dialogue] [--dry-run]
"""

import json, re, sys, argparse, shutil, unicodedata
from pathlib import Path

DIALOGUE_FILE = r"d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"
UI_FILE       = r"d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\ui.json"

# ─── SPACING FIX ─────────────────────────────────────────────────
WEIRD_SPACES = {
    '\u00a0', '\u200b', '\u200c', '\u200d',
    '\u2002', '\u2003', '\u2009', '\u202f',
    '\u3000', '\ufeff',
}


def fix_spacing(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize('NFC', text)
    for ws in WEIRD_SPACES:
        text = text.replace(ws, ' ')
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r' ([,.:;!?])', r'\1', text)
    text = re.sub(r'(<[ib]>)\s+', r'\1', text)
    text = re.sub(r'\s+(</[ib]>)', r'\1', text)
    return text.strip()


# ─── PRONOUN RULES ───────────────────────────────────────────────
# Bond (self pronouns)
BOND_SELF_FIXES = [
    (r'\bAnh phải\b', 'Tôi phải'),   (r'\banh phải\b', 'tôi phải'),
    (r'\bChắc anh\b', 'Chắc tôi'),   (r'\bchắc anh\b', 'chắc tôi'),
    (r'\bĐể anh\b',   'Để tôi'),     (r'\bđể anh\b',   'để tôi'),
    (r'\bAnh cần\b',  'Tôi cần'),    (r'\banh cần\b',  'tôi cần'),
    (r'\bAnh sẽ\b',   'Tôi sẽ'),     (r'\banh sẽ\b',   'tôi sẽ'),
    (r'\bAnh đã\b',   'Tôi đã'),     (r'\banh đã\b',   'tôi đã'),
    (r'\bAnh không\b','Tôi không'),  (r'\banh không\b','tôi không'),
    (r'\bAnh có\b',   'Tôi có'),     (r'\banh có\b',   'tôi có'),
    (r'\bAnh biết\b', 'Tôi biết'),   (r'\banh biết\b', 'tôi biết'),
    (r'\bAnh thấy\b', 'Tôi thấy'),   (r'\banh thấy\b', 'tôi thấy'),
    (r'\bAnh đang\b', 'Tôi đang'),   (r'\banh đang\b', 'tôi đang'),
    (r'\bAnh muốn\b', 'Tôi muốn'),   (r'\banh muốn\b', 'tôi muốn'),
    (r'\bAnh nghĩ\b', 'Tôi nghĩ'),   (r'\banh nghĩ\b', 'tôi nghĩ'),
    (r'\bAnh là\b',   'Tôi là'),     (r'\banh là\b',   'tôi là'),
    (r'\bCủa anh\b',  'Của tôi'),    (r'\bcủa anh\b',  'của tôi'),
    (r'\bMình\b',     'Tôi'),        (r'\bmình\b',     'tôi'),
]

# Valhalla/Arbiter: tôi -> ta  
VILLAIN_FIXES = [
    (r'\bTôi sẽ\b',   'Ta sẽ'),    (r'\btôi sẽ\b',   'ta sẽ'),
    (r'\bTôi đã\b',   'Ta đã'),    (r'\btôi đã\b',   'ta đã'),
    (r'\bTôi không\b','Ta không'), (r'\btôi không\b','ta không'),
    (r'\bTôi cần\b',  'Ta cần'),   (r'\btôi cần\b',  'ta cần'),
    (r'\bTôi muốn\b', 'Ta muốn'), (r'\btôi muốn\b', 'ta muốn'),
    (r'\bTôi biết\b', 'Ta biết'), (r'\btôi biết\b', 'ta biết'),
    (r'\bTôi là\b',   'Ta là'),   (r'\btôi là\b',   'ta là'),
    (r'\bTôi có\b',   'Ta có'),   (r'\btôi có\b',   'ta có'),
    (r'\bCủa tôi\b',  'Của ta'),  (r'\bcủa tôi\b',  'của ta'),
    (r'\bMình\b',     'Ta'),       (r'\bmình\b',     'ta'),
]

# Kẻ thù: tôi -> tao
ENEMY_FIXES = [
    (r'\bTôi sẽ\b',   'Tao sẽ'),   (r'\btôi sẽ\b',   'tao sẽ'),
    (r'\bTôi không\b','Tao không'),(r'\btôi không\b','tao không'),
    (r'\bTôi có\b',   'Tao có'),   (r'\btôi có\b',   'tao có'),
    (r'\bTôi muốn\b', 'Tao muốn'),(r'\btôi muốn\b', 'tao muốn'),
    (r'\bTôi đã\b',   'Tao đã'),   (r'\btôi đã\b',   'tao đã'),
    (r'\bCủa tôi\b',  'Của tao'),  (r'\bcủa tôi\b',  'của tao'),
    (r'\bMình\b',     'Tao'),       (r'\bmình\b',     'tao'),
]

VILLAIN_SPEAKERS  = {"Valhalla", "Arbiter"}
ENEMY_SPEAKERS    = {"Hostile", "Mercenary", "Bullthorp", "Pirate", "Jealous Boyfriend"}
BOND_SPEAKERS     = {"Bond"}


def apply_rules(text: str, rules: list) -> str:
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text)
    return text


def fix_segment(text: str, speaker: str) -> str:
    """Áp dụng tất cả fix cho một câu."""
    if not isinstance(text, str) or not text:
        return text

    # 1. Spacing
    text = fix_spacing(text)

    # 2. Nhân xưng theo speaker
    if speaker in BOND_SPEAKERS:
        text = apply_rules(text, BOND_SELF_FIXES)
    elif speaker in VILLAIN_SPEAKERS:
        text = apply_rules(text, VILLAIN_FIXES)
    elif speaker in ENEMY_SPEAKERS:
        text = apply_rules(text, ENEMY_FIXES)

    # 3. Spacing sau khi fix pronoun (có thể tạo ra khoảng trắng mới)
    text = fix_spacing(text)
    return text


# ─── MAIN ────────────────────────────────────────────────────────
def fix_dialogue(dry_run: bool) -> int:
    path = Path(DIALOGUE_FILE)
    if not path.exists():
        print(f"[ERR] Không tìm thấy: {path}")
        return 0

    data: dict = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    examples = []

    for key, entry in data.items():
        speaker = entry.get("speaker_name", "")
        for seg_key, text in entry.get("segments", {}).items():
            new = fix_segment(text, speaker)
            if new != text:
                fixed += 1
                if len(examples) < 20:
                    examples.append((speaker, text, new))
                if not dry_run:
                    data[key]["segments"][seg_key] = new

    if not dry_run and fixed > 0:
        backup = path.with_suffix(".json.fix_bak")
        shutil.copy2(path, backup)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] dialogue.json: {fixed} segments đã fix (backup: {backup.name})")
    else:
        print(f"[DRY] dialogue.json: {fixed} segments cần fix")

    if examples:
        print("\nVí dụ đã fix:")
        for spk, before, after in examples[:10]:
            print(f"  [{spk}]")
            print(f"    Trước: {before}")
            print(f"    Sau  : {after}")
    return fixed


def fix_ui(dry_run: bool) -> int:
    path = Path(UI_FILE)
    if not path.exists():
        print(f"[ERR] Không tìm thấy: {path}")
        return 0

    data: dict = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0

    for outer_key, strings in data.items():
        for inner_key, text in strings.items():
            if not isinstance(text, str):
                continue
            new = fix_spacing(text)
            if new != text:
                fixed += 1
                if not dry_run:
                    data[outer_key][inner_key] = new

    if not dry_run and fixed > 0:
        backup = path.with_suffix(".json.fix_bak")
        shutil.copy2(path, backup)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] ui.json: {fixed} strings spacing đã fix (backup: {backup.name})")
    else:
        print(f"[DRY] ui.json: {fixed} strings cần fix spacing")
    return fixed


def main():
    ap = argparse.ArgumentParser(description="Fix lỗi dịch hiện có")
    ap.add_argument("--ui",        action="store_true", help="Fix ui.json")
    ap.add_argument("--dialogue",  action="store_true", help="Fix dialogue.json")
    ap.add_argument("--dry-run",   action="store_true", help="Chỉ đếm, không ghi")
    args = ap.parse_args()

    # Nếu không chỉ định thì fix cả hai
    do_ui  = args.ui or (not args.ui and not args.dialogue)
    do_dlg = args.dialogue or (not args.ui and not args.dialogue)

    print("=" * 60)
    print("  Fix lỗi bản dịch hiện có")
    if args.dry_run:
        print("  [DRY RUN — không ghi file]")
    print("=" * 60)
    print()

    total = 0
    if do_dlg:
        total += fix_dialogue(args.dry_run)
    if do_ui:
        total += fix_ui(args.dry_run)

    print()
    if args.dry_run:
        print(f"[DRY] Tổng cần fix: {total}")
    else:
        print(f"[OK] Tổng đã fix: {total}")
    print("\nBước tiếp: chạy inject_all.bat để đưa vào game")
    return 0


if __name__ == "__main__":
    sys.exit(main())
