"""
translate_dialogue_v3.py
========================
Dịch dialogue.json với ngữ cảnh liên kết — AI nhớ cả chuỗi hội thoại.

Kiến trúc mới:
  - Nhóm câu theo speaker_code: các câu cùng một cảnh/nhân vật được dịch cùng nhau
  - Window context: 30 câu trước đó luôn được gửi kèm như "đã dịch" để AI nhớ ngữ cảnh
  - Nhân xưng nhất quán: hệ thống rule-based kiểm tra SAU khi AI dịch
  - Post-process: tự động fix lỗi nhân xưng phổ biến
  - Spacing fix: tự động fix khoảng trắng thừa/lỗi character

Chạy: python translate_dialogue_v3.py [--resume] [--from KEY]
"""

import json, os, re, time, sys, argparse, urllib.request
from pathlib import Path
from collections import deque

# ─── CẤU HÌNH ────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/generate"
MODEL         = "gemma3:12b"

SRC_FILE      = r"d:\VietHoa_007FirstLight\localization\extracted\dialogue.json"
OUT_FILE      = r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"
PROGRESS_FILE = r"d:\VietHoa_007FirstLight\localization\dialogue_progress_v3.json"

BATCH_SIZE    = 8      # Nhỏ hơn để AI tập trung hơn
CONTEXT_WINDOW = 25    # Số câu gần nhất gửi kèm làm context
TEMPERATURE   = 0.05   # Rất thấp để nhất quán
TIMEOUT       = 360

# ─── BỐI CẢNH CỐT TRUYỆN ─────────────────────────────────────────
# Gắn vào system prompt để AI luôn biết mình đang dịch game gì,
# nhân vật nào, mối quan hệ ra sao — không cần nhắc lại mỗi batch
STORY_CONTEXT = """
━━━ BỐI CẢNH CỐT TRUYỆN "007 FIRST LIGHT" ━━━
• Đây là game về James Bond (007) — điệp viên MI6 trẻ, còn đang chứng tỏ bản thân
• Bond chưa được cấp số 007 chính thức, đây là nhiệm vụ đầu tiên của anh
• M (nữ) = Giám đốc MI6, người quyết định số phận Bond — lạnh lùng nhưng công bằng
• Moneypenny = thư ký MI6, quen biết Bond, hay trêu đùa nhẹ
• Q = trưởng phòng thiết bị, hay phàn nàn khi Bond làm hỏng đồ
• Valhalla = trùm phản diện chính — kiêu ngạo, lạnh lùng, tin mình sẽ thắng
• Arbiter = phản diện phụ, bí ẩn hơn Valhalla
• Cressida = nhân vật nữ bí ẩn, động cơ chưa rõ ngay từ đầu
• Các Hostile/Mercenary/Security = lính gác, tay sai — không cần tên riêng

MỐI QUAN HỆ XƯNG HÔ:
• Bond ↔ M: Bond gọi "bà" hoặc không gọi, M gọi Bond bằng tên "Bond"
• Bond ↔ Moneypenny: gần gũi hơn, Bond có thể gọi "Moneypenny" trực tiếp
• Bond ↔ Q: chuyên nghiệp, Q hay cằn nhằn, Bond hay phớt lờ
• Bond ↔ kẻ thù: Bond luôn cool, không bao giờ mất bình tĩnh kể cả khi bị đe dọa
• Kẻ thù ↔ Bond: có thể gọi thẳng "Bond", "007", hoặc xúc phạm tùy cấp bậc"""

# ─── NHÂN XƯng TUYỆT ĐỐI ────────────────────────────────────────
# Bond: 007, lạnh lùng, lịch lãm. KHÔNG bao giờ tự gọi mình là "anh"
# Khi nói chuyện với NPC không xác định giới tính -> "bạn"
# Khi nói độc thoại/suy nghĩ -> không cần đại từ

PRONOUN_RULES = {
    # (speaker, gender) -> (tự xưng, gọi người khác nam, gọi người khác nữ, gọi trung tính)
    # Format: self, to_male, to_female, to_neutral
    "Bond":          ("tôi", "anh ta",  "cô ấy", "họ"),
    "M":             ("tôi", "anh",     "cô",    "bạn"),
    "Q":             ("tôi", "anh",     "cô",    "bạn"),
    "Moneypenny":    ("tôi", "anh",     "cô",    "bạn"),
    "Valhalla":      ("ta",  "ngươi",   "ngươi", "ngươi"),
    "Arbiter":       ("ta",  "ngươi",   "ngươi", "ngươi"),
    "Hostile":       ("tao", "mày",     "mày",   "mày"),
    "Mercenary":     ("tao", "mày",     "mày",   "mày"),
    "Bullthorp":     ("tao", "mày",     "mày",   "mày"),
    "Pirate":        ("tao", "mày",     "mày",   "mày"),
    "Security":      ("tôi", "anh",     "cô",    "bạn"),
    "DEFAULT":       ("tôi", "anh",     "cô",    "bạn"),
}

# Mapping giới tính nhân vật — dùng để AI biết cách xưng hô
CHARACTER_GENDER = {
    "Bond": "male", "M": "female", "Q": "male", "Moneypenny": "female",
    "Nomi": "female", "Cressida": "female", "Selina": "female",
    "Linda": "female", "Miriam": "female", "Bridget": "female",
    "Woman in Red": "female", "Mystery Woman": "female", "PR Lady": "female",
    "Nirmala": "female",
    "Valhalla": "male", "Arbiter": "male", "Bullthorp": "male",
    "Hostile": "male", "Mercenary": "male", "Assassin": "male",
    "Tanner": "male", "Bachchan": "male", "Bancroft": "male",
    "Basil": "male", "Damien": "male", "Ellis": "male",
    "Ferguson": "male", "Gary": "male", "Jonty": "male",
    "Kingsley": "male", "Konjevic": "male", "Lorca": "male",
    "Monroe": "male", "Murto": "male", "Nash": "male",
    "Pike": "male", "Ponsonby": "male", "Ronson": "male",
    "Singh": "male", "Somerset": "male", "Whitlock": "male",
    "Sir Nicholas": "male", "Ramon Hernandez": "male", "Pirate": "male",
    "Jealous Boyfriend": "male", "SAS": "male", "Captain": "male",
    "Pilot": "male", "Security": "neutral",
}

CHARACTER_ROLE = {
    "Bond":     "Điệp viên 007 MI6, lịch lãm, tự tin, cool, đôi khi khô hài",
    "M":        "Giám đốc MI6, quyền uy, cứng rắn, nói ngắn gọn súc tích",
    "Q":        "Trưởng phòng thiết bị MI6, thông minh, hay bực bội khi bị phớt lờ",
    "Moneypenny":"Thư ký MI6, thân thiện, chuyên nghiệp, hay trêu Bond",
    "Valhalla": "Trùm phản diện, lạnh lùng, kiêu ngạo, nói chắc nịch, tự xưng 'ta'",
    "Arbiter":  "Phản diện cấp cao, lạnh lùng, bí ẩn, tự xưng 'ta'",
    "Bullthorp":"Tay chân hung hãn, thô lỗ, hay đe dọa",
    "Hostile":  "Lính gác thù địch, hung hăng, thô lỗ",
    "Mercenary":"Lính đánh thuê, tàn nhẫn, không quan tâm đến mạng người",
    "Assassin": "Sát thủ chuyên nghiệp, lạnh lùng, ít nói",
    "Security": "Nhân viên bảo vệ, tuân thủ quy trình",
}

# ─── SYSTEM PROMPT ───────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là dịch giả chuyên nghiệp cho game hành động gián điệp "007 First Light" (James Bond).
""" + STORY_CONTEXT + """

━━━ NHÂN XƯNG — QUY TẮC TUYỆT ĐỐI ━━━

▌ BẢNG ĐẠI TỪ THEO NHÂN VẬT

  Bond (007):
    • Tự xưng              → "tôi"
    • Gọi 1 nam            → "anh" / "hắn" / tên riêng
    • Gọi 1 nữ             → "cô" / "cô ấy"
    • Gọi nhóm người       → "các anh" / "các vị" / "mọi người"
    • Độc thoại/suy nghĩ   → bỏ đại từ, nói thẳng vào hành động

  M (nữ, giám đốc MI6):
    • Tự xưng              → "tôi"
    • Gọi Bond             → "anh" hoặc "Bond"
    • Gọi nhóm             → "các anh" / "các vị"

  Q (nam, kỹ thuật MI6):
    • Tự xưng              → "tôi"
    • Gọi Bond             → "anh" hoặc "Bond"

  Moneypenny (nữ, thư ký MI6):
    • Tự xưng              → "tôi"
    • Gọi Bond             → "anh" (thân mật hơn M)

  Valhalla, Arbiter (trùm phản diện):
    • Tự xưng              → "ta"
    • Gọi Bond             → "ngươi" / "James Bond"
    • Gọi nhóm             → "bọn ngươi"

  Hostile, Mercenary, Bullthorp, Pirate (kẻ thù cấp thấp):
    • Tự xưng              → "tao"
    • Gọi Bond             → "mày" / "tên đó"
    • Gọi nhóm             → "chúng mày" / "bọn mày"

  Nhân vật trung tính / phụ:
    • Tự xưng              → "tôi"
    • Gọi 1 người          → "anh" / "cô" tùy giới tính
    • Gọi nhóm             → "các anh" / "mọi người"

▌ QUY TẮC ĐẶC BIỆT — KHÔNG ĐƯỢC VI PHẠM

  1. "Any of you / Have you guys / You all" → "các anh" / "mọi người"
     KHÔNG dịch thành "mấy tôi" / "chúng tôi" / "các bạn tôi"

  2. "We" khi Bond nói với đồng đội → "chúng ta" hoặc bỏ đại từ
     "We" khi kẻ thù đe dọa → "bọn ta" / "chúng ta"

  3. "You" số ít → "anh/cô/mày/ngươi" tùy nhân vật đang nói
     "You" số nhiều → "các anh" / "bọn ngươi" / "chúng mày" tùy ngữ cảnh

  4. Bond KHÔNG BAO GIỜ tự xưng "anh/em/ta/tao/mình"
     Mọi câu Bond tự xưng đều là "tôi"

  5. Valhalla/Arbiter KHÔNG BAO GIỜ dùng "tôi" — luôn là "ta"

  6. Hostile/Mercenary/Bullthorp KHÔNG BAO GIỜ dùng "tôi" — luôn là "tao"

━━━ TONE VÀ VĂN PHONG ━━━
• Bond: cool, tự tin, súc tích, đôi khi châm biếm nhẹ nhàng — KHÔNG hoa mỹ
• M: quyền uy, ngắn gọn, chỉ nói điều cần thiết
• Q: thông minh, đôi khi thở dài/bực bội — dùng ngôn ngữ kỹ thuật khi phù hợp
• Kẻ thù cấp thấp: hung hăng, thô tục nhẹ, ngắn gọn
• Trùm phản diện: chậm rãi, đe dọa, không cần hét to

━━━ QUY TẮC KỸ THUẬT ━━━
• GIỮ NGUYÊN: [Tag] stage directions như [Laughs] [Sighs] [In Serbian] — KHÔNG dịch
• GIỮ NGUYÊN: {0} {1} {2} placeholders
• GIỮ NGUYÊN: <i>text</i> <b>text</b> HTML tags — chỉ dịch phần text bên trong
• GIỮ NGUYÊN: \n ký tự xuống dòng
• KHÔNG thêm tag {} mới nào không có trong bản gốc
• KHÔNG thêm dấu ngoặc kép bao ngoài
• KHÔNG giải thích, chỉ trả về bản dịch
• Trả về ĐÚNG số dòng đánh số: 1. ... 2. ... 3. ...

━━━ VỀ SPACING ━━━
• Dùng đúng 1 dấu cách giữa các từ
• KHÔNG dùng dấu cách trước dấu phẩy/chấm
• KHÔNG thêm dấu cách thừa đầu/cuối câu"""

# ─── POST-PROCESSING RULES ───────────────────────────────────────
# Các lỗi nhân xưng phổ biến Bond tự gọi mình là "anh"
# Chạy RULE-BASED sau AI để catch những case rõ ràng

def fix_bond_pronouns(text: str, speaker: str) -> str:
    """Fix các lỗi nhân xưng phổ biến cho Bond."""
    if speaker != "Bond":
        return text

    patterns_self_anh = [
        # Bond tự xưng "anh" -> "tôi"
        (r'\bAnh phải\b', 'Tôi phải'),
        (r'\banh phải\b', 'tôi phải'),
        (r'\bChắc anh\b', 'Chắc tôi'),
        (r'\bchắc anh\b', 'chắc tôi'),
        (r'\bĐể anh\b', 'Để tôi'),
        (r'\bđể anh\b', 'để tôi'),
        (r'\bAnh cần\b', 'Tôi cần'),
        (r'\banh cần\b', 'tôi cần'),
        (r'\bAnh sẽ\b', 'Tôi sẽ'),
        (r'\banh sẽ\b', 'tôi sẽ'),
        (r'\bAnh đã\b', 'Tôi đã'),
        (r'\banh đã\b', 'tôi đã'),
        (r'\bAnh không\b', 'Tôi không'),
        (r'\banh không\b', 'tôi không'),
        (r'\bAnh có\b', 'Tôi có'),
        (r'\banh có\b', 'tôi có'),
        (r'\bAnh biết\b', 'Tôi biết'),
        (r'\banh biết\b', 'tôi biết'),
        (r'\bAnh thấy\b', 'Tôi thấy'),
        (r'\banh thấy\b', 'tôi thấy'),
        (r'\bAnh đang\b', 'Tôi đang'),
        (r'\banh đang\b', 'tôi đang'),
        (r'\bAnh muốn\b', 'Tôi muốn'),
        (r'\banh muốn\b', 'tôi muốn'),
        (r'\bAnh nghĩ\b', 'Tôi nghĩ'),
        (r'\banh nghĩ\b', 'tôi nghĩ'),
        (r'\bAnh là\b', 'Tôi là'),
        (r'\banh là\b', 'tôi là'),
        (r'\bCủa anh\b', 'Của tôi'),
        (r'\bcủa anh\b', 'của tôi'),
        # Lỗi AI ghép số nhiều sai
        (r'\bMấy tôi\b', 'Các anh'),
        (r'\bmấy tôi\b', 'các anh'),
        (r'\bCác tôi\b', 'Các anh'),
        (r'\bcác tôi\b', 'các anh'),
        (r'\bChúng tôi\s+thấy\b', 'Các anh thấy'),
        (r'\bchúng tôi\s+thấy\b', 'các anh thấy'),
        (r'\bMình\b', 'Tôi'),
        (r'\bmình\b', 'tôi'),
    ]
    for pattern, replacement in patterns_self_anh:
        text = re.sub(pattern, replacement, text)
    return text


def fix_villain_pronouns(text: str, speaker: str) -> str:
    """Fix Valhalla/Arbiter phải xưng 'ta' không phải 'tôi'."""
    if speaker not in ("Valhalla", "Arbiter"):
        return text
    # Các pattern tự xưng "tôi" -> "ta"
    patterns = [
        (r'\bTôi sẽ\b', 'Ta sẽ'),
        (r'\btôi sẽ\b', 'ta sẽ'),
        (r'\bTôi đã\b', 'Ta đã'),
        (r'\btôi đã\b', 'ta đã'),
        (r'\bTôi không\b', 'Ta không'),
        (r'\btôi không\b', 'ta không'),
        (r'\bTôi cần\b', 'Ta cần'),
        (r'\btôi cần\b', 'ta cần'),
        (r'\bTôi muốn\b', 'Ta muốn'),
        (r'\btôi muốn\b', 'ta muốn'),
        (r'\bTôi biết\b', 'Ta biết'),
        (r'\btôi biết\b', 'ta biết'),
        (r'\bTôi là\b', 'Ta là'),
        (r'\btôi là\b', 'ta là'),
        (r'\bCủa tôi\b', 'Của ta'),
        (r'\bcủa tôi\b', 'của ta'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def fix_enemy_pronouns(text: str, speaker: str) -> str:
    """Fix kẻ thù cấp thấp phải xưng 'tao'."""
    if speaker not in ("Hostile", "Mercenary", "Bullthorp", "Pirate", "Jealous Boyfriend"):
        return text
    patterns = [
        (r'\bTôi sẽ\b', 'Tao sẽ'),
        (r'\btôi sẽ\b', 'tao sẽ'),
        (r'\bTôi không\b', 'Tao không'),
        (r'\btôi không\b', 'tao không'),
        (r'\bTôi có\b', 'Tao có'),
        (r'\btôi có\b', 'tao có'),
        (r'\bTôi muốn\b', 'Tao muốn'),
        (r'\btôi muốn\b', 'tao muốn'),
        (r'\bCủa tôi\b', 'Của tao'),
        (r'\bcủa tôi\b', 'của tao'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def fix_spacing(text: str) -> str:
    """Fix các lỗi khoảng trắng phổ biến."""
    # Nhiều khoảng trắng liên tiếp -> 1
    text = re.sub(r'  +', ' ', text)
    # Khoảng trắng trước dấu câu
    text = re.sub(r' ([,.!?:;])', r'\1', text)
    # Khoảng trắng đầu/cuối
    text = text.strip()
    # Khoảng trắng sau thẻ HTML mở và trước thẻ đóng
    text = re.sub(r'(<[ib]>)\s+', r'\1', text)
    text = re.sub(r'\s+(</[ib]>)', r'\1', text)
    return text


def post_process(text: str, speaker: str) -> str:
    """Áp dụng toàn bộ post-processing."""
    if not text:
        return text
    text = fix_bond_pronouns(text, speaker)
    text = fix_villain_pronouns(text, speaker)
    text = fix_enemy_pronouns(text, speaker)
    text = fix_spacing(text)
    return text


# ─── KIỂM TRA TAGS ───────────────────────────────────────────────
TAG_RE = re.compile(r'\[[^\]]+\]')
PLACEHOLDER_RE = re.compile(r'\{[0-9]+\}')


def extract_preserved(text: str) -> dict:
    """Trích xuất các phần cần giữ nguyên để verify sau."""
    return {
        'tags': TAG_RE.findall(text),
        'placeholders': PLACEHOLDER_RE.findall(text),
    }


def verify_preserved(original: str, translated: str) -> bool:
    """Kiểm tra các tag và placeholder được giữ nguyên."""
    orig = extract_preserved(original)
    trans = extract_preserved(translated)
    return (
        sorted(t.lower() for t in orig['tags']) == sorted(t.lower() for t in trans['tags'])
        and sorted(orig['placeholders']) == sorted(trans['placeholders'])
    )


def should_skip(text: str) -> bool:
    """Text không cần dịch."""
    if not text or not text.strip():
        return True
    t = text.strip()
    if re.match(r'^\[[^\]]+\]$', t):  # Chỉ là [Tag] đơn độc
        return True
    if re.match(r'^[A-Z_]{2,20}$', t):  # TOKEN thuần
        return True
    if len(t) <= 1:
        return True
    return False


# ─── OLLAMA ───────────────────────────────────────────────────────
def is_ollama_running() -> bool:
    try:
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return req.status == 200
    except Exception:
        return False


def ollama_generate(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": 3000,
            "num_ctx": 12288,
            "num_gpu": 99,
            "num_thread": 8,
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("response", "").strip()


# ─── CONTEXT WINDOW ───────────────────────────────────────────────
class ConversationContext:
    """Quản lý cửa sổ ngữ cảnh hội thoại."""

    def __init__(self, window_size: int = CONTEXT_WINDOW):
        self.window = deque(maxlen=window_size)  # (speaker, en, vi)

    def add(self, speaker: str, en: str, vi: str):
        self.window.append((speaker, en, vi))

    def build_context_block(self) -> str:
        """Tạo block ngữ cảnh để gửi cho AI."""
        if not self.window:
            return ""
        lines = []
        for speaker, en, vi in self.window:
            lines.append(f"  [{speaker}] EN: {en}")
            lines.append(f"  [{speaker}] VI: {vi}")
        return "\n".join(lines)


# ─── PARSE RESPONSE ───────────────────────────────────────────────
def parse_numbered_response(response: str, count: int, originals: list) -> list:
    """Parse kết quả đánh số từ AI."""
    parsed = {}
    lines = response.strip().split("\n")
    current_idx = None
    current_parts = []

    for line in lines:
        m = re.match(r'^(\d+)[.\)]\s*(.*)', line.strip())
        if m:
            if current_idx is not None and current_parts:
                parsed[current_idx] = ' '.join(current_parts).strip()
            current_idx = int(m.group(1))
            text = m.group(2).strip().strip('"').strip("'")
            current_parts = [text] if text else []
        elif current_idx is not None and line.strip():
            current_parts.append(line.strip())

    if current_idx is not None and current_parts:
        parsed[current_idx] = ' '.join(current_parts).strip()

    results = []
    for i, orig in enumerate(originals):
        t = parsed.get(i + 1, '').strip().strip('"').strip("'")
        # Bỏ prefix [Speaker] nếu AI trả về
        t = re.sub(r'^\[[^\]]+\]\s*', '', t).strip()
        results.append(t if t else orig)
    return results


# ─── TRANSLATE BATCH VỚI CONTEXT ─────────────────────────────────
def translate_batch_with_context(
    items: list,           # [(entry_key, seg_key, speaker, en_text)]
    context: ConversationContext,
) -> list:
    """Dịch batch với context window, trả về list bản dịch."""
    if not items:
        return []

    context_block = context.build_context_block()
    speakers_in_batch = list(dict.fromkeys(s for _, _, s, _ in items))

    # Build thông tin nhân vật cho batch này
    char_info_lines = []
    for spk in speakers_in_batch:
        role = CHARACTER_ROLE.get(spk, "nhân vật phụ")
        gender = CHARACTER_GENDER.get(spk, "neutral")
        rules = PRONOUN_RULES.get(spk, PRONOUN_RULES["DEFAULT"])
        char_info_lines.append(
            f"  • {spk} ({gender}): {role} — tự xưng '{rules[0]}'"
        )
    char_info = "\n".join(char_info_lines)

    # Build danh sách câu cần dịch
    lines_to_translate = []
    for i, (ek, sk, spk, txt) in enumerate(items):
        lines_to_translate.append(f"{i+1}. [{spk}] {txt}")
    numbered = "\n".join(lines_to_translate)

    # Build prompt
    context_section = ""
    if context_block:
        context_section = f"""
━━━ NGỮ CẢNH HỘI THOẠI VỪA QUA ━━━
(Đã dịch — dùng để nhớ nhân xưng và mạch truyện)
{context_block}

"""

    prompt = f"""Dịch {len(items)} dòng dialogue sang tiếng Việt.
{context_section}
━━━ NHÂN VẬT TRONG BATCH NÀY ━━━
{char_info}

━━━ CÂU CẦN DỊCH ━━━
{numbered}

Trả về đúng {len(items)} dòng đánh số, chỉ phần dịch (không cần giữ phần [Tên nhân vật]):"""

    try:
        response = ollama_generate(prompt)
    except Exception as e:
        print(f"    [WARN] Lỗi API lần 1: {e}, thử lại sau 5s...")
        time.sleep(5)
        try:
            response = ollama_generate(prompt)
        except Exception as e2:
            print(f"    [ERR] Lỗi lần 2: {e2} — giữ nguyên bản gốc")
            return [txt for _, _, _, txt in items]

    originals = [txt for _, _, _, txt in items]
    raw_results = parse_numbered_response(response, len(items), originals)

    # Post-process từng câu
    final = []
    for (ek, sk, spk, orig), trans in zip(items, raw_results):
        # Nếu AI không dịch được (trả về giống gốc) -> giữ nguyên gốc
        if trans == orig:
            final.append(orig)
            continue

        # Verify tag/placeholder
        if not verify_preserved(orig, trans):
            # Mất tag -> giữ nguyên gốc
            print(f"    [WARN] Tag mất [{spk}]: {orig!r} -> {trans!r}")
            final.append(orig)
            continue

        # Post-process nhân xưng + spacing
        trans = post_process(trans, spk)
        final.append(trans)

    return final


# ─── MAIN ────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Dịch dialogue với context AI")
    ap.add_argument("--from", dest="from_key", help="Bắt đầu từ key cụ thể")
    ap.add_argument("--fix-only", action="store_true",
                    help="Chỉ chạy post-process fix (không gọi AI)")
    ap.add_argument("--fresh", action="store_true",
                    help="Xóa progress + output cũ, dịch lại từ đầu")
    args = ap.parse_args()

    print("=" * 65)
    print("  007 First Light — Dialogue Translator v3 (Context-Aware)")
    print(f"  Model: {MODEL}  |  Batch: {BATCH_SIZE}  |  Context: {CONTEXT_WINDOW}")
    print("=" * 65)

    # Load source
    src: dict = json.loads(Path(SRC_FILE).read_text(encoding="utf-8"))

    # --fresh: xóa sạch để dịch lại từ đầu
    if args.fresh:
        if Path(PROGRESS_FILE).exists():
            Path(PROGRESS_FILE).unlink()
            print("[FRESH] Đã xóa progress cũ")
        if Path(OUT_FILE).exists():
            Path(OUT_FILE).unlink()
            print("[FRESH] Đã xóa output cũ")
        print("[FRESH] Bắt đầu dịch lại từ đầu...\n")

    # Load output hiện tại
    out_data: dict = {}
    if Path(OUT_FILE).exists():
        try:
            out_data = json.loads(Path(OUT_FILE).read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load progress — LUÔN load, không cần --resume
    progress: dict = {}
    if Path(PROGRESS_FILE).exists():
        try:
            progress = json.loads(Path(PROGRESS_FILE).read_text(encoding="utf-8"))
            print(f"[OK] Resume: {len(progress)} segments đã xong")
        except Exception:
            pass

    if args.fix_only:
        # Chế độ chỉ fix post-process — không gọi AI
        print("[MODE] Fix-only: chỉ áp dụng post-process rules")
        fixed = 0
        for key, entry in out_data.items():
            spk = entry.get("speaker_name", "")
            for sk, txt in entry.get("segments", {}).items():
                if not isinstance(txt, str):
                    continue
                new = post_process(txt, spk)
                if new != txt:
                    out_data[key]["segments"][sk] = new
                    fixed += 1
        Path(OUT_FILE).write_text(
            json.dumps(out_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] Fixed {fixed} entries -> {OUT_FILE}")
        return 0

    # Kiểm tra Ollama
    if not is_ollama_running():
        print("\n[LỖI] Ollama chưa chạy!")
        print(f"  Mở terminal và chạy: ollama serve")
        print(f"  (Nếu chưa có model: ollama pull {MODEL})")
        return 1

    print(f"[OK] Ollama đang chạy")
    print(f"[OK] {len(src)} entries tổng cộng\n")

    # Xây dựng danh sách cần dịch
    todo = []
    start_found = args.from_key is None
    for key, entry in src.items():
        if args.from_key and not start_found:
            if key == args.from_key:
                start_found = True
            else:
                continue
        segs = entry.get("segments", {})
        for sk, txt in segs.items():
            seg_id = f"{key}::{sk}"
            if seg_id in progress:
                continue
            if not should_skip(txt):
                todo.append((key, sk, entry.get("speaker_name", ""), txt))

    print(f"[OK] Cần dịch: {len(todo)} segments\n")

    # Context window
    ctx = ConversationContext(CONTEXT_WINDOW)

    # Khởi tạo out_data từ src
    for k, v in src.items():
        if k not in out_data:
            out_data[k] = dict(v)

    start_time = time.time()
    batch_buf = []
    processed = 0
    last_save_time = time.time()

    def flush_batch():
        nonlocal processed
        if not batch_buf:
            return
        results = translate_batch_with_context(batch_buf, ctx)

        for (ek, sk, spk, orig), trans in zip(batch_buf, results):
            out_data[ek]["segments"][sk] = trans
            ctx.add(spk, orig, trans)
            processed += 1
            # In kết quả
            orig_short = (orig[:55] + "…") if len(orig) > 55 else orig
            trans_short = (trans[:55] + "…") if len(trans) > 55 else trans
            print(f"  [{spk}]")
            print(f"    EN: {orig_short}")
            print(f"    VI: {trans_short}")

        # Mark từng segment riêng biệt là done
        for ek, sk, _, _ in batch_buf:
            progress[f"{ek}::{sk}"] = True

        batch_buf.clear()

    def save():
        nonlocal last_save_time
        Path(OUT_FILE).write_text(
            json.dumps(out_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Path(PROGRESS_FILE).write_text(
            json.dumps(progress, ensure_ascii=False),
            encoding="utf-8"
        )
        last_save_time = time.time()

    total = len(todo)
    for i, item in enumerate(todo):
        batch_buf.append(item)

        if len(batch_buf) >= BATCH_SIZE:
            flush_batch()

            # Tiến độ
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0.001
            remain = (total - i) / rate if rate > 0 else 0
            pct = i / total * 100
            print(f"\n  ── [{i}/{total}] {pct:.1f}%"
                  f" | {rate:.1f} seg/s"
                  f" | còn ~{remain/60:.0f} phút ──\n")

            # Lưu mỗi 1 batch (sau mỗi 8 câu)
            save()
            print("  [SAVE] Đã lưu tiến độ")

    flush_batch()
    save()

    elapsed = time.time() - start_time
    print()
    print("=" * 65)
    print(f"  XONG! {processed} segments trong {elapsed/60:.1f} phút")
    print(f"  Output: {OUT_FILE}")
    print("=" * 65)
    print("\nBước tiếp:")
    print("  1. Chạy: python localization\\fix_rogue_tags.py")
    print("  2. Chạy: python localization\\sync_tags_from_eng.py")
    print("  3. Chạy: inject_all.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
