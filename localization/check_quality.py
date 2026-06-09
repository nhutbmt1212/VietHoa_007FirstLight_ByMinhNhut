"""
check_quality.py
================
Kiểm tra nghiêm ngặt chất lượng bản dịch dialogue.json và ui.json.

Các lỗi được phát hiện:
  [SPACE]   Khoảng trắng lạ: zero-width, non-breaking, double space
  [CHAR]    Ký tự đặc biệt lạ, control chars, BOM
  [TAG]     Tag [Stage] bị mất so với bản gốc EN
  [PLACEHOLDER] {0}{1} bị mất hoặc sai
  [HTML]    HTML tag không khớp (mở không đóng, đóng không mở)
  [PRONOUN] Lỗi nhân xưng: Bond="anh", villain="tôi", enemy="tôi"
  [UNTRANS] Câu giữ nguyên tiếng Anh (không dịch)
  [EMPTY]   Câu rỗng
  [MIXED]   Lẫn tiếng Anh trong câu dịch (còn từ EN thừa)
  [ROGUE]   Tag {} do AI bịa: {PAUSE} {SPEAKER} v.v.
  [DUPE]    Câu bị lặp lại y hệt nhau > 3 lần liên tiếp
  [LONG]    Bản dịch dài hơn gốc >3x (có thể AI giải thích thừa)

Chạy:
  python check_quality.py               -- kiểm tra cả 2 file
  python check_quality.py --dialogue    -- chỉ dialogue
  python check_quality.py --ui          -- chỉ UI
  python check_quality.py --fix         -- tự động fix những lỗi có thể fix
"""

import json, re, sys, argparse, unicodedata
from pathlib import Path
from collections import defaultdict

DIALOGUE_FILE = r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"
UI_FILE       = r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main\examples\vietnamese\translations\ui.json"
DIALOGUE_SRC  = r"d:\VietHoa_007FirstLight\localization\extracted\dialogue.json"
UI_SRC        = r"d:\VietHoa_007FirstLight\localization\extracted\ui.json"

# ─── PATTERNS ────────────────────────────────────────────────────
WEIRD_SPACES = {
    '\u00a0': 'NBSP', '\u200b': 'ZeroWidth', '\u200c': 'ZWNJ',
    '\u200d': 'ZWJ',  '\u2002': 'EnSpace',   '\u2003': 'EmSpace',
    '\u2009': 'ThinSpace', '\u202f': 'NarrowNBSP', '\u3000': 'IdeographicSpace',
    '\ufeff': 'BOM',
}
CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
TAG_RE        = re.compile(r'\[[^\]]+\]')
PLACEHOLDER_RE = re.compile(r'\{[0-9]+\}')
ROGUE_TAG_RE  = re.compile(r'\{(?:PAUSE|SPEAKER|RESUME|STOP|BREAK|END|START|SPELLER|SPECAUSE)\}', re.I)
HTML_OPEN_RE  = re.compile(r'<([a-zA-Z]+)(?:\s[^>]*)?>(?!</)')
HTML_CLOSE_RE = re.compile(r'</([a-zA-Z]+)>')
VIET_CHAR_RE  = re.compile(r'[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỷỹỵÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯ]')
EN_WORD_RE    = re.compile(r'\b[a-zA-Z]{4,}\b')

BOND_SELF_ERR = re.compile(r'\b(?:Anh phải|anh phải|Chắc anh|chắc anh|Để anh|để anh|Anh cần|anh cần|Anh sẽ|anh sẽ|Anh đã|anh đã|Anh không|anh không|Anh muốn|anh muốn|Mấy tôi|mấy tôi)\b')
VILLAIN_ERR   = re.compile(r'\bTôi\b|\btôi\b')
ENEMY_ERR     = re.compile(r'\bTôi\b|\btôi\b')

VILLAIN_SPEAKERS = {"Valhalla", "Arbiter"}
ENEMY_SPEAKERS   = {"Hostile", "Mercenary", "Bullthorp", "Pirate", "Jealous Boyfriend"}

# ─── INLINE FIX ──────────────────────────────────────────────────
_BOND_FIX = [
    (r'\bAnh phải\b','Tôi phải'),(r'\banh phải\b','tôi phải'),
    (r'\bChắc anh\b','Chắc tôi'),(r'\bchắc anh\b','chắc tôi'),
    (r'\bĐể anh\b',  'Để tôi'),  (r'\bđể anh\b',  'để tôi'),
    (r'\bAnh cần\b', 'Tôi cần'), (r'\banh cần\b', 'tôi cần'),
    (r'\bAnh sẽ\b',  'Tôi sẽ'),  (r'\banh sẽ\b',  'tôi sẽ'),
    (r'\bAnh đã\b',  'Tôi đã'),  (r'\banh đã\b',  'tôi đã'),
    (r'\bAnh không\b','Tôi không'),(r'\banh không\b','tôi không'),
    (r'\bAnh có\b',  'Tôi có'),  (r'\banh có\b',  'tôi có'),
    (r'\bAnh muốn\b','Tôi muốn'),(r'\banh muốn\b','tôi muốn'),
    (r'\bAnh nghĩ\b','Tôi nghĩ'),(r'\banh nghĩ\b','tôi nghĩ'),
    (r'\bAnh là\b',  'Tôi là'),  (r'\banh là\b',  'tôi là'),
    (r'\bCủa anh\b', 'Của tôi'), (r'\bcủa anh\b', 'của tôi'),
    (r'\bMấy tôi\b', 'Các anh'), (r'\bmấy tôi\b', 'các anh'),
]
_VILLAIN_FIX = [
    (r'\bTôi sẽ\b','Ta sẽ'),(r'\btôi sẽ\b','ta sẽ'),
    (r'\bTôi đã\b','Ta đã'),(r'\btôi đã\b','ta đã'),
    (r'\bTôi không\b','Ta không'),(r'\btôi không\b','ta không'),
    (r'\bTôi cần\b','Ta cần'),(r'\btôi cần\b','ta cần'),
    (r'\bTôi muốn\b','Ta muốn'),(r'\btôi muốn\b','ta muốn'),
    (r'\bTôi là\b','Ta là'),(r'\btôi là\b','ta là'),
    (r'\bCủa tôi\b','Của ta'),(r'\bcủa tôi\b','của ta'),
]
_ENEMY_FIX = [
    (r'\bTôi sẽ\b','Tao sẽ'),(r'\btôi sẽ\b','tao sẽ'),
    (r'\bTôi không\b','Tao không'),(r'\btôi không\b','tao không'),
    (r'\bTôi có\b','Tao có'),(r'\btôi có\b','tao có'),
    (r'\bTôi muốn\b','Tao muốn'),(r'\btôi muốn\b','tao muốn'),
    (r'\bCủa tôi\b','Của tao'),(r'\bcủa tôi\b','của tao'),
]

def is_translated(vi_text: str, en_text: str) -> bool:
    """Trả về True nếu câu đã được dịch sang tiếng Việt.
    Câu chưa dịch = giống hệt EN, hoặc không có ký tự Việt có dấu
    trong khi EN có từ thực sự (không phải tag/token thuần)."""
    if not vi_text or not vi_text.strip():
        return False  # Rỗng -> coi là chưa dịch
    # Giống hệt EN -> chưa dịch
    if vi_text.strip() == en_text.strip():
        return False
    # Không có EN text để so sánh -> coi là đã dịch
    if not en_text or not en_text.strip():
        return True
    # Loại bỏ tags/tokens/HTML khỏi EN để lấy text thuần
    en_clean = TAG_RE.sub('', en_text)
    en_clean = PLACEHOLDER_RE.sub('', en_clean)
    en_clean = re.sub(r'<[^>]+>', '', en_clean)
    en_clean = re.sub(r'\{[^}]+\}', '', en_clean).strip()
    # Nếu EN thuần không có chữ thực sự (chỉ là tag/token) -> bỏ qua
    if not re.search(r'[a-zA-Z]{2,}', en_clean):
        return True
    # Có ký tự Việt có dấu -> đã dịch
    if VIET_CHAR_RE.search(vi_text):
        return True
    # Không có tiếng Việt nhưng cũng khác EN -> có thể là proper noun giữ nguyên
    # Chỉ skip nếu VI hoàn toàn là ASCII ngắn (tên riêng, số, v.v.)
    if len(vi_text.strip()) <= 30 and re.match(r'^[\w\s\-\.\,\!\?\:\;\'\"\(\)]+$', vi_text.strip()):
        return False  # Ngắn và ASCII -> coi là chưa dịch
    return True


def _fix_pronouns_spacing(text: str, speaker: str) -> str:
    rules = []
    if speaker == "Bond":        rules = _BOND_FIX
    elif speaker in VILLAIN_SPEAKERS: rules = _VILLAIN_FIX
    elif speaker in ENEMY_SPEAKERS:   rules = _ENEMY_FIX
    for pat, rep in rules:
        text = re.sub(pat, rep, text)
    # Weird spaces
    for ch in WEIRD_SPACES:
        text = text.replace(ch, ' ')
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r' ([,.:;!?])', r'\1', text)
    return text.strip()

# ─── ISSUE CLASS ─────────────────────────────────────────────────
class Issue:
    def __init__(self, code: str, severity: str, key: str, speaker: str,
                 text: str, detail: str):
        self.code     = code      # [TAG], [SPACE], ...
        self.severity = severity  # ERROR / WARN / INFO
        self.key      = key
        self.speaker  = speaker
        self.text     = text[:120]
        self.detail   = detail

    def __str__(self):
        s = "!" if self.severity == "ERROR" else ("?" if self.severity == "WARN" else "·")
        spk = f"[{self.speaker}]" if self.speaker else ""
        return f"  {s} {self.code:<14} {spk:<16} {self.detail}"


# ─── CHECKS ──────────────────────────────────────────────────────
def check_spaces(text: str) -> list[str]:
    issues = []
    for ch, name in WEIRD_SPACES.items():
        if ch in text:
            issues.append(f"Ký tự khoảng trắng lạ: {name} (U+{ord(ch):04X})")
    if '  ' in text:
        issues.append("Hai dấu cách liên tiếp")
    if CONTROL_CHARS.search(text):
        issues.append("Control character lạ")
    return issues


def check_tags(en_text: str, vi_text: str) -> list[str]:
    en_tags = sorted(t.lower() for t in TAG_RE.findall(en_text))
    vi_tags = sorted(t.lower() for t in TAG_RE.findall(vi_text))
    if en_tags != vi_tags:
        missing = set(en_tags) - set(vi_tags)
        extra   = set(vi_tags) - set(en_tags)
        parts = []
        if missing: parts.append(f"Thiếu: {missing}")
        if extra:   parts.append(f"Thừa: {extra}")
        return [", ".join(parts)]
    return []


def check_placeholders(en_text: str, vi_text: str) -> list[str]:
    en_ph = sorted(PLACEHOLDER_RE.findall(en_text))
    vi_ph = sorted(PLACEHOLDER_RE.findall(vi_text))
    if en_ph != vi_ph:
        return [f"EN có {en_ph}, VI có {vi_ph}"]
    return []


def check_html(text: str) -> list[str]:
    opens  = [m.group(1).lower() for m in HTML_OPEN_RE.finditer(text)]
    closes = [m.group(1).lower() for m in HTML_CLOSE_RE.finditer(text)]
    issues = []
    for tag in set(opens + closes):
        o = opens.count(tag)
        c = closes.count(tag)
        if o != c:
            issues.append(f"<{tag}> mở {o} lần, đóng {c} lần")
    return issues


def check_rogue_tags(text: str) -> list[str]:
    found = ROGUE_TAG_RE.findall(text)
    if found:
        return [f"Rogue tags: {found}"]
    return []


def check_untranslated(en_text: str, vi_text: str) -> list[str]:
    if en_text.strip() == vi_text.strip():
        return ["Không được dịch (giữ nguyên EN)"]
    return []


def check_empty(text: str) -> list[str]:
    if not text or not text.strip():
        return ["Câu rỗng"]
    return []


def check_pronouns(text: str, speaker: str) -> list[str]:
    issues = []
    if speaker == "Bond":
        if BOND_SELF_ERR.search(text):
            m = BOND_SELF_ERR.search(text)
            issues.append(f"Bond dùng sai đại từ: '{m.group()}'")
    elif speaker in VILLAIN_SPEAKERS:
        # Villain dùng "tôi" thay vì "ta" — chỉ flag khi câu có "tôi" rõ ràng
        if re.search(r'\btôi\b', text, re.I):
            issues.append(f"{speaker} dùng 'tôi' thay vì 'ta'")
    elif speaker in ENEMY_SPEAKERS:
        if re.search(r'\btôi\b', text, re.I):
            issues.append(f"{speaker} dùng 'tôi' thay vì 'tao'")
    return issues


def check_mixed_language(en_text: str, vi_text: str) -> list[str]:
    """Phát hiện từ tiếng Anh thừa trong bản dịch."""
    if not VIET_CHAR_RE.search(vi_text):
        return []  # Câu không có tiếng Việt -> bỏ qua (có thể là proper noun)
    en_words_orig = set(w.lower() for w in EN_WORD_RE.findall(en_text))
    vi_en_words   = set(w.lower() for w in EN_WORD_RE.findall(vi_text))
    # Các từ EN được giữ nguyên hợp lệ
    VALID_KEEP = {
        'bond', 'mi6', 'sas', 'hdr', 'fps', 'xp', 'vr', 'ai', 'ui',
        'tacsim', 'theia', 'hyperion', 'valhalla', 'wreckie', 'hack',
        'intel', 'laser', 'qwatch', 'qlens', 'qlab', 'bawma', 'aleph',
        'moneypenny', 'cressida', 'tanner', 'greenway', 'isola',
        'james', 'james', 'nomi', 'jonty',
    }
    suspicious = vi_en_words - en_words_orig - VALID_KEEP
    # Lọc thêm: chỉ giữ từ thực sự lạ (không phải tên riêng, không phải viết tắt)
    suspicious = {w for w in suspicious if len(w) > 4 and not w[0].isupper()}
    if suspicious:
        return [f"Từ EN lạ trong VI: {suspicious}"]
    return []


def check_length(en_text: str, vi_text: str) -> list[str]:
    en_len = len(en_text.strip())
    vi_len = len(vi_text.strip())
    if en_len > 0 and vi_len / en_len > 3.5:
        return [f"VI dài hơn EN x{vi_len/en_len:.1f} ({en_len}→{vi_len} chars)"]
    return []


# ─── DIALOGUE CHECK ───────────────────────────────────────────────
def check_dialogue(fix_mode: bool) -> tuple[list[Issue], int]:
    src_path  = Path(DIALOGUE_SRC)
    viet_path = Path(DIALOGUE_FILE)

    if not viet_path.exists():
        print(f"[ERR] Không tìm thấy: {viet_path}")
        return [], 0

    viet: dict = json.loads(viet_path.read_text(encoding="utf-8"))
    src:  dict = {}
    if src_path.exists():
        src = json.loads(src_path.read_text(encoding="utf-8"))

    issues: list[Issue] = []
    fixed = 0
    last_texts: list[str] = []  # Để check duplicate liên tiếp

    for key, entry in viet.items():
        speaker = entry.get("speaker_name", "")
        segs    = entry.get("segments", {})
        en_segs = src.get(key, {}).get("segments", {}) if src else {}

        for seg_key, vi_text in segs.items():
            if not isinstance(vi_text, str):
                continue
            en_text = en_segs.get(seg_key, "") if en_segs else ""

            # Bỏ qua câu chưa dịch (còn tiếng Anh)
            if not is_translated(vi_text, en_text):
                continue

            def add(code, sev, detail):
                issues.append(Issue(code, sev, key, speaker, vi_text, detail))

            # Empty
            for d in check_empty(vi_text):
                add("[EMPTY]", "ERROR", d)

            # Spaces
            for d in check_spaces(vi_text):
                add("[SPACE]", "WARN", d)
                if fix_mode:
                    for ch in WEIRD_SPACES:
                        vi_text = vi_text.replace(ch, ' ')
                    vi_text = re.sub(r' {2,}', ' ', vi_text).strip()
                    viet[key]["segments"][seg_key] = vi_text
                    fixed += 1

            # Rogue tags
            for d in check_rogue_tags(vi_text):
                add("[ROGUE]", "ERROR", d)
                if fix_mode:
                    vi_text = ROGUE_TAG_RE.sub('', vi_text).strip()
                    viet[key]["segments"][seg_key] = vi_text
                    fixed += 1

            if en_text:
                # Tags
                for d in check_tags(en_text, vi_text):
                    add("[TAG]", "ERROR", d)

                # Placeholders
                for d in check_placeholders(en_text, vi_text):
                    add("[PLACEHOLDER]", "ERROR", d)

                # Length
                for d in check_length(en_text, vi_text):
                    add("[LONG]", "WARN", d)

                # Mixed language
                for d in check_mixed_language(en_text, vi_text):
                    add("[MIXED]", "WARN", d)

            # HTML
            for d in check_html(vi_text):
                add("[HTML]", "WARN", d)

            # Pronouns
            for d in check_pronouns(vi_text, speaker):
                add("[PRONOUN]", "WARN", d)
                if fix_mode:
                    new = _fix_pronouns_spacing(vi_text, speaker)
                    if new != vi_text:
                        viet[key]["segments"][seg_key] = new
                        fixed += 1

            # Duplicate liên tiếp
            last_texts.append(vi_text)
            if len(last_texts) > 4:
                last_texts.pop(0)
            if len(last_texts) == 4 and len(set(last_texts)) == 1:
                add("[DUPE]", "WARN", f"Câu lặp lại 4 lần liên tiếp: '{vi_text[:40]}'")

    if fix_mode and fixed > 0:
        viet_path.write_text(
            json.dumps(viet, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    return issues, fixed


# ─── UI CHECK ─────────────────────────────────────────────────────
def check_ui(fix_mode: bool) -> tuple[list[Issue], int]:
    src_path  = Path(UI_SRC)
    viet_path = Path(UI_FILE)

    if not viet_path.exists():
        print(f"[ERR] Không tìm thấy: {viet_path}")
        return [], 0

    viet: dict = json.loads(viet_path.read_text(encoding="utf-8"))
    src:  dict = {}
    if src_path.exists():
        src = json.loads(src_path.read_text(encoding="utf-8"))

    issues: list[Issue] = []
    fixed = 0

    for outer_key, strings in viet.items():
        for inner_key, vi_text in strings.items():
            if not isinstance(vi_text, str):
                continue
            en_text = src.get(outer_key, {}).get(inner_key, "") if src else ""

            # Bỏ qua câu chưa dịch (còn tiếng Anh)
            if not is_translated(vi_text, en_text):
                continue

            def add(code, sev, detail):
                issues.append(Issue(code, sev, f"{outer_key}/{inner_key}", "",
                                    vi_text, detail))

            # Empty
            for d in check_empty(vi_text):
                add("[EMPTY]", "ERROR", d)

            # Spaces
            for d in check_spaces(vi_text):
                add("[SPACE]", "WARN", d)
                if fix_mode:
                    for ch in WEIRD_SPACES:
                        vi_text = vi_text.replace(ch, ' ')
                    vi_text = re.sub(r' {2,}', ' ', vi_text).strip()
                    viet[outer_key][inner_key] = vi_text
                    fixed += 1

            # Rogue tags
            for d in check_rogue_tags(vi_text):
                add("[ROGUE]", "ERROR", d)

            if en_text:
                # Placeholders
                for d in check_placeholders(en_text, vi_text):
                    add("[PLACEHOLDER]", "ERROR", d)

            # HTML
            for d in check_html(vi_text):
                add("[HTML]", "WARN", d)

    if fix_mode and fixed > 0:
        viet_path.write_text(
            json.dumps(viet, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    return issues, fixed


# ─── REPORT ──────────────────────────────────────────────────────
def print_report(issues: list[Issue], title: str, fixed: int, show_all: bool):
    errors   = [i for i in issues if i.severity == "ERROR"]
    warns    = [i for i in issues if i.severity == "WARN"]

    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    print(f"  Tổng lỗi  : {len(issues)}  (ERROR: {len(errors)}  WARN: {len(warns)})")
    if fixed:
        print(f"  Đã tự fix : {fixed}")

    # Thống kê theo loại
    by_code: dict[str, int] = defaultdict(int)
    for i in issues:
        by_code[i.code] += 1
    print(f"\n  Phân loại:")
    for code, count in sorted(by_code.items(), key=lambda x: -x[1]):
        print(f"    {code:<16} {count:>5}")

    # In chi tiết
    limit = len(issues) if show_all else 50
    if errors:
        print(f"\n  ── ERRORS ({len(errors)}) ──")
        for i in errors[:limit]:
            print(str(i))
            print(f"               └─ {i.text[:100]}")
    if warns:
        print(f"\n  ── WARNINGS ({min(len(warns), limit)}/{len(warns)}) ──")
        for i in warns[:limit]:
            print(str(i))
    if not show_all and len(issues) > limit:
        print(f"\n  ... và {len(issues)-limit} lỗi khác. Dùng --all để xem đủ.")


# ─── MAIN ────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Kiểm tra chất lượng bản dịch")
    ap.add_argument("--dialogue", action="store_true", help="Chỉ kiểm tra dialogue")
    ap.add_argument("--ui",       action="store_true", help="Chỉ kiểm tra UI")
    ap.add_argument("--fix",      action="store_true", help="Tự fix lỗi có thể fix")
    ap.add_argument("--all",      action="store_true", help="In toàn bộ lỗi (không giới hạn 50)")
    args = ap.parse_args()

    do_dlg = args.dialogue or (not args.dialogue and not args.ui)
    do_ui  = args.ui       or (not args.dialogue and not args.ui)

    print("=" * 70)
    print("  007 First Light — Quality Check")
    if args.fix:
        print("  [FIX MODE] Sẽ tự sửa những lỗi có thể fix")
    print("=" * 70)

    total_issues = 0

    if do_dlg:
        issues, fixed = check_dialogue(args.fix)
        print_report(issues, "DIALOGUE", fixed, args.all)
        total_issues += len(issues)

    if do_ui:
        issues, fixed = check_ui(args.fix)
        print_report(issues, "UI", fixed, args.all)
        total_issues += len(issues)

    print(f"\n{'='*70}")
    print(f"  TỔNG: {total_issues} vấn đề cần xem xét")
    if total_issues == 0:
        print("  ✅ Không tìm thấy lỗi!")
    else:
        print("  Chạy với --fix để tự sửa những lỗi có thể sửa tự động.")
        print("  Lỗi [TAG] [PLACEHOLDER] [PRONOUN] cần xem lại thủ công.")
    print("=" * 70)
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
