"""
test_translate_quality.py
=========================
Test AI dịch với các case đặc biệt từ file dialogue thực tế.
Kiểm tra đầy đủ trước khi chạy full overnight.

Chạy: python localization\test_translate_quality.py
"""
import json, re, sys, urllib.request, time
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "gemma3:12b"
SRC_FILE   = r"d:\VietHoa_007FirstLight\localization\extracted\dialogue.json"

# ─── TEST CASES ───────────────────────────────────────────────────
# Format: (speaker, en_text, check_fn_description, check_fn)
# check_fn(vi_text) -> None nếu OK, str nếu lỗi

TAG_RE         = re.compile(r'\[[^\]]+\]')
PLACEHOLDER_RE = re.compile(r'\{[0-9]+\}')
VIET_RE        = re.compile(r'[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỷỹỵ]')
ROGUE_RE       = re.compile(r'\{(?:PAUSE|SPEAKER|RESUME|STOP|BREAK|SPELLER)\}', re.I)

def has_viet(t):      return bool(VIET_RE.search(t))
def no_rogue(t):      return not bool(ROGUE_RE.search(t))
def tags_kept(en, vi):
    et = sorted(x.lower() for x in TAG_RE.findall(en))
    vt = sorted(x.lower() for x in TAG_RE.findall(vi))
    return et == vt
def ph_kept(en, vi):
    return sorted(PLACEHOLDER_RE.findall(en)) == sorted(PLACEHOLDER_RE.findall(vi))

TEST_CASES = [
    # ── Bond độc thoại đơn giản ────────────────────────────────
    {
        "id": "T01", "speaker": "Bond",
        "en": "Over here.",
        "checks": [
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
            ("Bond không xưng anh", lambda vi: None if not re.search(r'\banh\b', vi) else f"Bond tự xưng 'anh': {vi}"),
        ]
    },
    {
        "id": "T02", "speaker": "Bond",
        "en": "Be cool, James... be cool.",
        "checks": [
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
            ("Giữ tên James", lambda vi: None if "James" in vi else "Mất tên 'James'"),
            ("Bond không xưng anh", lambda vi: None if not re.search(r'\bAnh\b|\banh\b(?!\s+ta)', vi) else f"Bond tự xưng 'anh'"),
        ]
    },
    # ── Bond hỏi nhóm người ────────────────────────────────────
    {
        "id": "T03", "speaker": "Bond",
        "en": "Any of you seen Saunders? He may have slipped past you.",
        "checks": [
            ("Không dịch 'Any of you' thành 'Mấy tôi'",
             lambda vi: None if "mấy tôi" not in vi.lower() else f"Lỗi 'mấy tôi': {vi}"),
            ("Dùng 'các anh' hoặc 'ai' cho nhóm",
             lambda vi: None if re.search(r'các anh|ai đó|có ai|chưa ai', vi.lower()) else f"Cần 'các anh/ai': {vi}"),
        ]
    },
    # ── Tag [Laughs] phải giữ nguyên ───────────────────────────
    {
        "id": "T04", "speaker": "Bond",
        "en": "[Laughs] Nobody's ever really out. You know that, right?",
        "checks": [
            ("Giữ tag [Laughs]",
             lambda vi: None if tags_kept("[Laughs] Nobody's ever really out. You know that, right?", vi)
             else f"Mất tag [Laughs]: {vi}"),
            ("Có tiếng Việt sau tag",
             lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
        ]
    },
    {
        "id": "T05", "speaker": "Bond",
        "en": "Cressida Bright. [Laughs] I never did like to leave a job half-finished.",
        "checks": [
            ("Giữ tag [Laughs]", lambda vi: None if "[Laughs]" in vi or "[laughs]" in vi else f"Mất tag: {vi}"),
            ("Giữ tên Cressida Bright", lambda vi: None if "Cressida" in vi else f"Mất tên: {vi}"),
        ]
    },
    # ── Tên riêng không được dịch ──────────────────────────────
    {
        "id": "T06", "speaker": "Bond",
        "en": "Give me a second, Moneypenny.",
        "checks": [
            ("Giữ tên Moneypenny", lambda vi: None if "Moneypenny" in vi else f"Mất tên Moneypenny: {vi}"),
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
        ]
    },
    # ── Dấu nháy kép trong câu ─────────────────────────────────
    {
        "id": "T07", "speaker": "Bond",
        "en": '"M" is that a codename?',
        "checks": [
            ("Giữ tên 'M' trong dấu nháy",
             lambda vi: None if re.search(r'["\u201c\u201d\u2018\u2019]?M["\u201c\u201d\u2018\u2019]?', vi)
             else f"Mất 'M': {vi}"),
            ("Không dịch M thành từ khác",
             lambda vi: None if not re.search(r'\b(?:mẹ|mềm|mà)\b', vi.lower()) else f"Dịch sai 'M': {vi}"),
        ]
    },
    # ── M nói với Bond ─────────────────────────────────────────
    {
        "id": "T08", "speaker": "M",
        "en": "Get back to London immediately.",
        "checks": [
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
            ("M xưng tôi nếu có đại từ",
             lambda vi: None if not re.search(r'\bTa\b|\bta\b|\bTao\b|\btao\b', vi)
             else f"M dùng sai đại từ: {vi}"),
        ]
    },
    # ── Valhalla xưng 'ta' ─────────────────────────────────────
    {
        "id": "T09", "speaker": "Valhalla",
        "en": "You think you can stop me?",
        "checks": [
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
            ("Valhalla không xưng 'tôi'",
             lambda vi: None if not re.search(r'\btôi\b', vi.lower()) else f"Valhalla xưng 'tôi': {vi}"),
        ]
    },
    # ── Hostile xưng 'tao' ─────────────────────────────────────
    {
        "id": "T10", "speaker": "Hostile",
        "en": "Drop the weapon. Now.",
        "checks": [
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
        ]
    },
    {
        "id": "T11", "speaker": "Hostile",
        "en": "You have no idea what you've gotten yourself into.",
        "checks": [
            ("Hostile không xưng 'tôi'",
             lambda vi: None if not re.search(r'\btôi\b', vi.lower()) else f"Hostile xưng 'tôi': {vi}"),
            ("Hostile dùng mày/ngươi gọi Bond (không xưng hô lịch sự)",
             lambda vi: None if re.search(r'\bmày\b|\bngươi\b|\banh ta\b', vi.lower())
                              or not re.search(r'\banh\b', vi.lower())
             else f"Hostile xưng hô quá lịch sự 'anh': {vi}"),
        ]
    },
    # ── Placeholder {0} phải giữ ───────────────────────────────
    {
        "id": "T12", "speaker": "Bond",
        "en": "Playing {0} in {1}",
        "checks": [
            ("Giữ placeholder {0}",
             lambda vi: None if "{0}" in vi else f"Mất {{0}}: {vi}"),
            ("Giữ placeholder {1}",
             lambda vi: None if "{1}" in vi else f"Mất {{1}}: {vi}"),
        ]
    },
    # ── Không thêm tag {} mới ──────────────────────────────────
    {
        "id": "T13", "speaker": "Bond",
        "en": "Not good.",
        "checks": [
            ("Không có rogue tag {}",
             lambda vi: None if no_rogue(vi) else f"Có rogue tag: {vi}"),
            ("Có tiếng Việt", lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
        ]
    },
    # ── Multi-segment ──────────────────────────────────────────
    {
        "id": "T14", "speaker": "Bond",
        "en": "Sorry, of course.",
        "checks": [
            ("Không dịch thành tiếng Anh",
             lambda vi: None if vi.lower() != "sorry, of course." else "Giữ nguyên EN"),
        ]
    },
    # ── Câu ngắn cảm thán ─────────────────────────────────────
    {
        "id": "T15", "speaker": "Bond",
        "en": "Oh, shit.",
        "checks": [
            ("Có tiếng Việt hoặc dịch sang VN",
             lambda vi: None if has_viet(vi) or vi.lower() != "oh, shit." else "Giữ nguyên EN"),
        ]
    },
    # ── Dấu nháy kép quanh tên — không đổi thành [] ───────────
    {
        "id": "T16", "speaker": "Bond",
        "en": '"M" is that a codename?',
        "checks": [
            ("Dấu nháy kép quanh M giữ nguyên — không đổi thành [M]",
             lambda vi: None if "[M]" not in vi and "[m]" not in vi
             else f"Đổi dấu nháy thành []: {vi}"),
            ("Giữ dấu nháy kép quanh M hoặc chữ M rõ ràng",
             lambda vi: None if re.search(r'["\u201c\u201d]M["\u201c\u201d]|\"M\"|\'M\'', vi) or "M" in vi
             else f"Mất chữ M: {vi}"),
            ("Có tiếng Việt",
             lambda vi: None if has_viet(vi) else "Không có tiếng Việt"),
        ]
    },
    # ── Dấu nháy kép escaped trong JSON ───────────────────────
    {
        "id": "T17", "speaker": "Bond",
        "en": 'Bond. James Bond.',
        "checks": [
            ("Giữ cả hai tên Bond và James",
             lambda vi: None if "Bond" in vi and "James" in vi else f"Mất tên: {vi}"),
        ]
    },
]

# ─── SYSTEM PROMPT (lấy từ translate_dialogue_v3.py) ────────────
def get_system_prompt():
    v3 = Path(r"d:\VietHoa_007FirstLight\localization\translate_dialogue_v3.py")
    if not v3.exists():
        return ""
    src = v3.read_text(encoding="utf-8")
    m = re.search(r'SYSTEM_PROMPT\s*=\s*"""(.*?)"""', src, re.DOTALL)
    if m:
        # Eval STORY_CONTEXT nếu có
        prompt = m.group(1)
        m2 = re.search(r'STORY_CONTEXT\s*=\s*"""(.*?)"""', src, re.DOTALL)
        if m2:
            prompt = prompt.replace('""" + STORY_CONTEXT + """', m2.group(1))
        return prompt.strip()
    return ""

SYSTEM_PROMPT = get_system_prompt() or "Bạn là dịch giả tiếng Việt cho game 007 First Light."

# ─── OLLAMA ──────────────────────────────────────────────────────
def is_running():
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except:
        return False

def translate_one(speaker: str, en: str, context_pairs: list) -> str:
    """Dịch 1 câu với context 5 câu trước."""
    ctx = ""
    if context_pairs:
        lines = []
        for spk, e, v in context_pairs[-5:]:
            lines.append(f"  [{spk}] EN: {e}")
            lines.append(f"  [{spk}] VI: {v}")
        ctx = "━━━ NGỮ CẢNH VỪA QUA ━━━\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"{ctx}"
        f"━━━ NHÂN VẬT ━━━\n"
        f"  {speaker}\n\n"
        f"━━━ DỊCH ━━━\n"
        f"[{speaker}] {en}\n\n"
        f"Trả về bản dịch tiếng Việt (1 dòng, không giải thích):"
    )
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.05,
            "num_predict": 512,
            "num_ctx": 8192,
            "num_gpu": 99,
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    vi = result.get("response", "").strip()
    # Bỏ prefix [Speaker] nếu AI trả về
    vi = re.sub(r'^\[[^\]]+\]\s*', '', vi).strip()
    vi = vi.strip('"').strip("'")
    return vi

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print(f"  TEST AI TRANSLATE — {MODEL}")
    print(f"  {len(TEST_CASES)} test cases từ dialogue thực tế")
    print("=" * 65)

    if not is_running():
        print("\n[LỖI] Ollama chưa chạy!")
        return 1

    passed = 0
    failed = 0
    errors = []
    context_pairs = []  # Lưu (speaker, en, vi) để build context

    for tc in TEST_CASES:
        tid     = tc["id"]
        speaker = tc["speaker"]
        en      = tc["en"]
        checks  = tc["checks"]

        print(f"\n  {tid} [{speaker}]")
        print(f"       EN: {en}")

        try:
            t0 = time.time()
            vi = translate_one(speaker, en, context_pairs)
            elapsed = time.time() - t0
            print(f"       VI: {vi}  [{elapsed:.1f}s]")
        except Exception as e:
            print(f"       [API ERROR] {e}")
            failed += 1
            continue

        # Chạy checks
        case_ok = True
        for check_name, check_fn in checks:
            result = check_fn(vi)
            if result is None:
                print(f"       ✅ {check_name}")
            else:
                print(f"       ❌ {check_name}: {result}")
                errors.append(f"{tid} — {check_name}: {result}")
                case_ok = False

        if case_ok:
            passed += 1
            context_pairs.append((speaker, en, vi))
        else:
            failed += 1

    # ── Tóm tắt ─────────────────────────────────────────────────
    print()
    print("=" * 65)
    print(f"  KẾT QUẢ: {passed}/{len(TEST_CASES)} PASS  |  {failed} FAIL")
    print("=" * 65)

    if errors:
        print("\n  CÁC LỖI CẦN SỬA TRƯỚC KHI CHẠY FULL:")
        for e in errors:
            print(f"    ✗ {e}")
        print()
        print("  → Sửa SYSTEM_PROMPT trong translate_dialogue_v3.py")
        print("    rồi chạy lại test này cho đến khi tất cả PASS.")
    else:
        print()
        print("  ✅ Tất cả PASS! Prompt đã sẵn sàng.")
        print("  → Chạy translate_fresh.bat hoặc translate_resume.bat")

    pct = passed / len(TEST_CASES) * 100
    return 0 if pct >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())
