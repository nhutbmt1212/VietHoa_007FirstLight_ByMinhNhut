"""
translate_ui_v2.py
==================
Dịch ui.json với chất lượng cao hơn — fix lỗi spacing và nhân xưng.

Cải thiện so với bản cũ:
  - Fix khoảng trắng character (lỗi encoding black space)
  - Prompt chặt hơn: không dịch ALL CAPS, không dịch proper nouns
  - Post-process: strip khoảng trắng lạ, normalize unicode
  - Fallback dictionary phong phú hơn (từ translate_ui_main.py)
  - Phát hiện câu đã dịch tốt -> không dịch lại

Chạy: python translate_ui_v2.py [--resume] [--fix-spacing-only]
"""

import json, os, re, time, sys, argparse, shutil, unicodedata, urllib.request
from pathlib import Path
from datetime import datetime

# ─── CẤU HÌNH ────────────────────────────────────────────────────
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL          = "qwen/qwen3-next-80b-a3b-instruct"
NVIDIA_API_KEY = "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"

SRC_FILE      = r"d:\VietHoa_007FirstLight\localization\extracted\ui.json"
OUT_FILE      = r"d:\VietHoa_007FirstLight\007-firstlight-toolkit-main\examples\vietnamese\translations\ui.json"
PROGRESS_FILE = r"d:\VietHoa_007FirstLight\localization\ui_progress_v2.json"
LOG_FILE      = r"d:\VietHoa_007FirstLight\localization\ui_translate_log_v2.txt"

BATCH_SIZE    = 40    # UI string ngắn, tăng mạnh batch
TEMPERATURE   = 0.05
TIMEOUT       = 200
MAX_LEN       = 300

# ─── DICTIONARY FALLBACK ─────────────────────────────────────────
# Dùng dict này trước — không cần AI cho các chuỗi phổ biến
# Nguồn: translate_ui_main.py đã kiểm chứng thủ công
DICT: dict[str, str] = {
    "story": "Cốt Truyện", "resume game": "Tiếp Tục Chơi",
    "select chapter": "Chọn Chương", "load game": "Tải Game",
    "go online": "Chơi Trực Tuyến", "tactical simulations": "Mô Phỏng Chiến Thuật",
    "customisation": "Tùy Chỉnh", "challenges": "Thử Thách",
    "options": "Tùy Chọn", "quit game": "Thoát Game",
    "start story": "Bắt Đầu Câu Chuyện", "continue story": "Tiếp Tục Câu Chuyện",
    "new campaign game": "Chiến Dịch Mới", "main menu": "Menu Chính",
    "return to main menu": "Quay Về Menu Chính",
    "back": "Quay Lại", "continue": "Tiếp Tục", "confirm": "Xác Nhận",
    "cancel": "Hủy", "close": "Đóng", "play": "Chơi", "skip": "Bỏ Qua",
    "retry": "Thử Lại", "next": "Tiếp Theo", "previous": "Trước Đó",
    "apply": "Áp Dụng", "save": "Lưu", "delete": "Xóa",
    "edit": "Chỉnh Sửa", "select": "Chọn", "assign": "Gán",
    "unassign": "Hủy Gán", "equip": "Trang Bị", "unequip": "Tháo Ra",
    "upgrade": "Nâng Cấp", "purchase": "Mua", "claim": "Nhận",
    "track": "Theo Dõi", "untrack": "Hủy Theo Dõi", "overwrite": "Ghi Đè",
    "reconnect": "Kết Nối Lại", "sign up": "Đăng Ký",
    "yes": "Có", "no": "Không", "ok": "OK",
    "saving": "Đang Lưu", "loading": "Đang Tải",
    "connected": "Đã Kết Nối", "connecting...": "Đang Kết Nối...",
    "synchronizing...": "Đang Đồng Bộ...", "disconnected": "Mất Kết Nối",
    "connecting": "Đang Kết Nối", "autosave": "Tự Động Lưu",
    "manual save": "Lưu Thủ Công", "offline": "Ngoại Tuyến",
    "difficulty": "Độ Khó", "select difficulty": "Chọn Độ Khó",
    "novice": "Người Mới", "casual": "Nhẹ Nhàng", "standard": "Tiêu Chuẩn",
    "master": "Cao Thủ", "purist": "Chuyên Gia",
    "mission failed": "Nhiệm Vụ Thất Bại", "mission success": "Nhiệm Vụ Thành Công",
    "mission briefing": "Tóm Tắt Nhiệm Vụ", "mission exit": "Thoát Nhiệm Vụ",
    "restart mission": "Chơi Lại Từ Đầu", "restart checkpoint": "Chơi Lại Từ Điểm Kiểm Tra",
    "objectives": "Mục Tiêu", "objective": "Mục Tiêu",
    "objective failed": "Mục Tiêu Thất Bại", "completed objective": "Mục Tiêu Hoàn Thành",
    "briefing": "Tóm Tắt", "checkpoints": "Điểm Kiểm Tra",
    "intel": "Tình Báo", "score": "Điểm Số",
    "rewards": "Phần Thưởng", "get rewards": "Nhận Phần Thưởng",
    "accessibility": "Hỗ Trợ Tiếp Cận", "display": "Màn Hình",
    "audio": "Âm Thanh", "controls": "Điều Khiển",
    "subtitles": "Phụ Đề", "off": "Tắt", "on": "Bật",
    "low": "Thấp", "high": "Cao", "default": "Mặc Định",
    "none": "Không Có", "all": "Tất Cả",
    "locked": "Bị Khóa", "unlocked": "Đã Mở Khóa",
    "owned": "Đã Sở Hữu", "equipped": "Đã Trang Bị",
    "completed": "Đã Hoàn Thành", "selected": "Đã Chọn",
    "coming soon": "Sắp Ra Mắt", "new": "Mới",
    "weapons": "Vũ Khí", "gadgets": "Trang Bị", "gadget": "Trang Bị",
    "outfits": "Trang Phục", "loadout": "Trang Bị Chiến Đấu",
    "collectibles": "Vật Sưu Tầm",
    "stealth": "Ẩn Náu", "combat": "Chiến Đấu",
    "campaign": "Chiến Dịch", "operations": "Chiến Dịch",
    "activities": "Hoạt Động", "tacsim": "Mô Phỏng Chiến Thuật",
    "leaderboards": "Bảng Xếp Hạng", "friends": "Bạn Bè",
    "store": "Cửa Hàng", "go to store": "Đến Cửa Hàng",
    "bundles": "Gói", "bundle": "Gói",
    "progression": "Tiến Trình", "challenge": "Thử Thách",
    "delete save": "Xóa Save", "system data": "Dữ Liệu Hệ Thống",
    "profile data": "Dữ Liệu Hồ Sơ", "warning": "Cảnh Báo", "error": "Lỗi",
    "quality": "Chất Lượng", "tutorials": "Hướng Dẫn",
    "dialogue": "Thoại", "items": "Vật Phẩm", "item": "Vật Phẩm",
    "exit to menu": "Thoát Ra Menu", "go back": "Quay Lại",
    "accept": "Đồng Ý", "decline": "Từ Chối",
    "not signed in": "Chưa Đăng Nhập", "go to menu": "Về Menu",
    "connection failed": "Kết Nối Thất Bại",
    "back to title screen": "Về Màn Hình Tiêu Đề",
    "switch to offline mode": "Chuyển Sang Ngoại Tuyến",
    "switch to online mode": "Chuyển Sang Trực Tuyến",
    "fps": "FPS", "max": "Tối Đa", "min": "Tối Thiểu", "avg": "Trung Bình",
    "sprint": "Chạy Bộ", "skip animation": "Bỏ Qua Hoạt Cảnh",
    "replay": "Chơi Lại", "in menu": "Trong Menu",
    "global": "Toàn Cầu", "custom": "Tùy Chỉnh",
    "overview": "Tổng Quan", "summary": "Tóm Tắt", "details": "Chi Tiết",
    "please wait...": "Vui Lòng Chờ...", "loading results": "Đang Tải Kết Quả...",
    "spoiler warning": "Cảnh Báo Tiết Lộ",
    "campaign": "Chiến Dịch", "chapter {0}": "Chương {0}",
    "tier": "Cấp Bậc", "level {0}": "Cấp Độ {0}",
    "story so far": "Câu Chuyện Đến Giờ",
    "mission reward: {0}": "Phần Thưởng Nhiệm Vụ: {0}",
    "xp reward: {0}": "Phần Thưởng XP: {0}",
    "intel reward: {0}": "Phần Thưởng Tình Báo: {0}",
    "playing {0} in {1}": "Đang Chơi {0} trong {1}",
    "current level: {0}": "Cấp Độ Hiện Tại: {0}",
    "total xp gained": "Tổng XP Đạt Được",
    "agent score": "Điểm Điệp Viên",
}

# Tên riêng / game terms KHÔNG dịch
KEEP_AS_IS = {
    'Bond', 'Q', 'M', 'MI6', 'TacSim', 'Q-Lens', 'Q-Watch', 'Q-Lab',
    'THEIA', 'HYPERION', 'IOI', 'Valhalla', 'Wreckie', 'Caliban',
    'Arrowhead', 'Riptide', 'Aleph', 'Bawma', 'HDR', 'FPS', 'XP',
    'SAS', 'PMC', 'HUD', 'UI', 'V-Sync', '007',
    # Tên nhân vật
    'Moneypenny', 'Nomi', 'Tanner', 'Cressida', 'Selina', 'Monroe',
    'Ferguson', 'Damien', 'Webb', 'Miriam', 'Linda', 'Bridget',
    'Bachchan', 'Bancroft', 'Basil', 'Ellis', 'Gary', 'Jonty',
    'Kingsley', 'Konjevic', 'Lorca', 'Murto', 'Nash', 'Pike',
    'Ponsonby', 'Ronson', 'Singh', 'Somerset', 'Whitlock',
    'Stephen Bright', 'Sir Nicholas', 'Ramon Hernandez',
    'Basim', 'Aadan', 'Nirmala', 'Waters', 'Isola',
    # Weapon names
    'Knight 1', 'DRX', 'SB-10', 'PDR-9', 'Stormer-99', 'REX', 'Osato',
}

# ─── SYSTEM PROMPT UI ─────────────────────────────────────────────
SYSTEM_UI = """Bạn là dịch giả chuyên nghiệp cho game "007 First Light" (James Bond).
Nhiệm vụ: dịch chuỗi giao diện (UI) sang tiếng Việt.

━━━ GIỮ NGUYÊN TUYỆT ĐỐI ━━━
• {0} {1} {2} — placeholder động
• {ES_xxx} {Hold} {Press} {Accept} — game tokens
• <br> <br/> <b> </b> <i> </i> — HTML tags
• \n \r\n — xuống dòng
• Tên riêng: Bond, Q, M, MI6, TacSim, Q-Lens, THEIA, Valhalla, Wreckie
• Từ viết tắt: HDR, FPS, XP, SAS, HUD, RGB, VR, AI, UI
• Tên vũ khí: Knight 1, DRX, SB-10, PDR-9, Stormer-99
• Chuỗi ALL CAPS (tên level/chapter): giữ nguyên KHÔNG dịch

━━━ CÁCH DỊCH ━━━
• Nút/nhãn 1-4 từ: ngắn gọn, Viết Hoa Chữ Cái Đầu
  Save→Lưu | Load→Tải | Quit→Thoát | Resume→Tiếp Tục
  Locked→Bị Khóa | Equipped→Đã Trang Bị | Completed→Đã Hoàn Thành
• Động từ hành động: Pick up→Nhặt | Interact→Tương Tác | Hack→Hack
• Câu mô tả: dịch tự nhiên, giữ {0} đúng vị trí
• Tên item/trang phục: giữ tên gốc, dịch phần mô tả

━━━ SPACING ━━━
• Dùng đúng 1 dấu cách giữa các từ
• KHÔNG có dấu cách trước dấu phẩy/chấm/chấm hỏi
• KHÔNG thêm khoảng trắng thừa đầu/cuối

━━━ FORMAT ĐẦU RA ━━━
• Trả về đúng số dòng đánh số: 1. ... 2. ...
• KHÔNG thêm dấu ngoặc kép bao ngoài
• KHÔNG giải thích"""

# ─── UNICODE / SPACING FIX ───────────────────────────────────────
# Các ký tự "khoảng trắng đen" (zero-width, non-breaking, weird spaces)
WEIRD_SPACES = {
    '\u00a0',  # Non-breaking space
    '\u200b',  # Zero-width space
    '\u200c',  # Zero-width non-joiner
    '\u200d',  # Zero-width joiner
    '\u2002',  # En space
    '\u2003',  # Em space
    '\u2009',  # Thin space
    '\u202f',  # Narrow no-break space
    '\u3000',  # Ideographic space
    '\ufeff',  # BOM
}


def fix_spacing(text: str) -> str:
    """
    Fix tất cả lỗi khoảng trắng:
    1. Thay thế các ký tự khoảng trắng lạ bằng dấu cách thường
    2. Nhiều dấu cách -> 1
    3. Trim đầu/cuối
    4. Không có khoảng trắng trước dấu câu
    """
    if not text:
        return text

    # 1. Chuẩn hóa unicode (NFC)
    text = unicodedata.normalize('NFC', text)

    # 2. Thay weird spaces -> space thường
    for ws in WEIRD_SPACES:
        text = text.replace(ws, ' ')

    # 3. Nhiều khoảng trắng -> 1
    text = re.sub(r' {2,}', ' ', text)

    # 4. Khoảng trắng trước dấu câu
    text = re.sub(r' ([,.:;!?])', r'\1', text)

    # 5. Khoảng trắng sau HTML open tag và trước close tag
    text = re.sub(r'(<[ib]>)\s+', r'\1', text)
    text = re.sub(r'\s+(</[ib]>)', r'\1', text)

    # 6. Trim
    text = text.strip()

    return text


def normalize_all_spacing(data: dict) -> tuple[dict, int]:
    """Áp dụng fix_spacing cho toàn bộ data."""
    fixed = 0
    for outer_key, strings in data.items():
        for inner_key, text in strings.items():
            if not isinstance(text, str):
                continue
            new = fix_spacing(text)
            if new != text:
                data[outer_key][inner_key] = new
                fixed += 1
    return data, fixed


# ─── SKIP LOGIC ──────────────────────────────────────────────────
_GAME_TOKEN_RE = re.compile(r'\{ES_[^}]+\}|\{[A-Z][A-Za-z_/]+\}')
_PLACEHOLDER_RE = re.compile(r'\{UI_[^}]+\}|\[\'[^\']+\'\]')
_VIETNAMESE_RE = re.compile(r'[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỷỹỵ]')


def is_already_vietnamese(text: str) -> bool:
    """Kiểm tra text đã có chữ Việt có dấu."""
    return bool(_VIETNAMESE_RE.search(text))


def should_skip(text: str) -> bool:
    """Xác định string không cần gửi AI."""
    if not text or not text.strip():
        return True
    t = text.strip()

    if len(t) > MAX_LEN:
        return True
    if t in KEEP_AS_IS:
        return True
    if re.match(r"^\['.+'\]$", t):  # ['UI_xxx']
        return True
    if re.match(r"^[\d\s\.,;:/|•…\-\+\*%\(\)\[\]{}°×÷=#@!?~`^&]+$", t):
        return True
    if len(t) <= 2:
        return True

    # Chỉ có game tokens
    stripped = _GAME_TOKEN_RE.sub('', t).strip()
    stripped = _PLACEHOLDER_RE.sub('', stripped).strip()
    if not stripped or len(stripped) < 2:
        return True

    # Acronym kỹ thuật
    if re.match(r'^[A-Z0-9_\-]{1,12}$', t):
        return True

    # ALL CAPS title (tên level)
    if t.isupper() and len(t) > 3 and not re.search(r'\s', t):
        return True

    # Template số thuần
    if re.match(r'^[\[{]?\{[0-9]+\}[\]},/:%\s]*(\{[0-9]+\}[\]},/:%\s]*)*$', t):
        return True

    return False


def dict_translate(text: str) -> str | None:
    """Tra dictionary trước. None = không có."""
    key = text.strip().lower()
    return DICT.get(key)


# ─── OLLAMA ──────────────────────────────────────────────────────
def is_ollama_running() -> bool:
    return True


def ollama_generate(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_UI},
            {"role": "user", "content": prompt}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": 1500,
    }).encode("utf-8")
    req = urllib.request.Request(
        NVIDIA_API_URL, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {NVIDIA_API_KEY}"
        }, method="POST"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip()


def parse_numbered_response(response: str, originals: list) -> list:
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
        if t:
            # Kiểm tra placeholder vẫn còn (không phân biệt hoa thường)
            orig_ph = set(p.lower() for p in re.findall(r'\{[^}]+\}', orig))
            trans_ph = set(p.lower() for p in re.findall(r'\{[^}]+\}', t))
            if orig_ph and not orig_ph.issubset(trans_ph):
                t = orig  # rollback nếu mất placeholder
            else:
                # Khôi phục chính xác chữ hoa/thường của placeholder
                orig_ph_list = re.findall(r'\{[^}]+\}', orig)
                trans_ph_list = re.findall(r'\{[^}]+\}', t)
                ph_map = {p.lower(): p for p in orig_ph_list}
                for t_ph in trans_ph_list:
                    lower_ph = t_ph.lower()
                    if lower_ph in ph_map and t_ph != ph_map[lower_ph]:
                        t = t.replace(t_ph, ph_map[lower_ph])
                        
        results.append(fix_spacing(t) if t else orig)
    return results


def translate_batch(items: list) -> list:
    """Dịch batch UI strings."""
    texts = [txt for _, _, txt in items]
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    prompt = (
        f"Dịch {len(items)} chuỗi UI game James Bond 007 sau sang tiếng Việt.\n"
        f"Trả về đúng {len(items)} dòng đánh số:\n\n{numbered}"
    )
    try:
        response = ollama_generate(prompt)
    except Exception as e:
        print(f"    [WARN] API lỗi: {e}, thử lại sau 5s...")
        time.sleep(5)
        try:
            response = ollama_generate(prompt)
        except Exception as e2:
            print(f"    [ERR] Lỗi lần 2: {e2} — giữ nguyên")
            return texts
    return parse_numbered_response(response, texts)


# ─── MAIN ────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Dịch UI với quality cao hơn")
    ap.add_argument("--resume", action="store_true", help="Tiếp tục từ lần trước")
    ap.add_argument("--fix-spacing-only", action="store_true",
                    help="Chỉ fix khoảng trắng trong file hiện tại, không gọi AI")
    args = ap.parse_args()

    print("=" * 65)
    print("  007 First Light — UI Translator v2 (Quality+Spacing fix)")
    print(f"  Model: {MODEL}  |  Batch: {BATCH_SIZE}")
    print("=" * 65)

    # Load files
    src: dict = json.loads(Path(SRC_FILE).read_text(encoding="utf-8"))
    out_data: dict = {}
    if Path(OUT_FILE).exists():
        try:
            out_data = json.loads(Path(OUT_FILE).read_text(encoding="utf-8"))
        except Exception:
            pass

    # Chế độ chỉ fix spacing
    if args.fix_spacing_only:
        print("[MODE] Fix spacing only — không gọi AI")
        if not out_data:
            print("[ERR] Không có file output để fix")
            return 1
        out_data, fixed = normalize_all_spacing(out_data)
        Path(OUT_FILE).write_text(
            json.dumps(out_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] Fixed {fixed} strings spacing -> {OUT_FILE}")
        return 0

    # Backup
    if Path(OUT_FILE).exists():
        shutil.copy2(OUT_FILE, OUT_FILE + ".bak")
        print(f"[OK] Backup: ui.json.bak")

    # Progress — LUÔN load, không cần --resume
    progress: dict = {}
    if Path(PROGRESS_FILE).exists():
        try:
            progress = json.loads(Path(PROGRESS_FILE).read_text(encoding="utf-8"))
            print(f"[OK] Resume: {len(progress)} blocks đã xong")
        except Exception:
            pass

    if not is_ollama_running():
        print("\n[LỖI] Ollama chưa chạy! Chạy: ollama serve")
        return 1
    print("[OK] Ollama đang chạy\n")

    # Khởi tạo out_data
    for ok, ov in src.items():
        if ok not in out_data:
            out_data[ok] = dict(ov)

    # Xây danh sách cần dịch
    total_src = sum(len(v) for v in src.values())
    todo = []
    dict_hits = 0
    skip_count = 0
    already_vi = 0

    for outer_key, strings in src.items():
        for inner_key, text in strings.items():
            if should_skip(text):
                skip_count += 1
                continue

            # Thử dict trước
            d = dict_translate(text)
            if d:
                out_data[outer_key][inner_key] = fix_spacing(d)
                dict_hits += 1
                continue

            # Nếu bản dịch hiện tại đã là tiếng Việt và không giống gốc
            existing = out_data.get(outer_key, {}).get(inner_key, text)
            if (existing != text and is_already_vietnamese(existing)
                    and outer_key in progress):
                already_vi += 1
                continue

            todo.append((outer_key, inner_key, text))

    print(f"[INFO] Tổng: {total_src:,} | Dict hit: {dict_hits:,}"
          f" | Đã VI: {already_vi:,} | Skip: {skip_count:,}"
          f" | Cần AI: {len(todo):,}\n")

    if not todo:
        # Vẫn fix spacing cho toàn bộ
        out_data, sp_fixed = normalize_all_spacing(out_data)
        Path(OUT_FILE).write_text(
            json.dumps(out_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] Tất cả đã dịch! Fix spacing: {sp_fixed} strings")
        print(f"[OK] Saved: {OUT_FILE}")
        return 0

    # Dịch với AI
    start_time = time.time()
    translated = 0
    log_lines = []

    def save():
        # Fix spacing toàn bộ trước khi lưu
        normalize_all_spacing(out_data)
        Path(OUT_FILE).write_text(
            json.dumps(out_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Path(PROGRESS_FILE).write_text(
            json.dumps(progress, ensure_ascii=False),
            encoding="utf-8"
        )

    batch_buf = []
    last_save = time.time()

    def flush():
        nonlocal translated
        if not batch_buf:
            return
        results = translate_batch(batch_buf)
        for (ok, ik, orig), trans in zip(batch_buf, results):
            out_data[ok][ik] = trans
            translated += 1
            if trans != orig:
                orig_s = orig[:50] + ("…" if len(orig) > 50 else "")
                trans_s = trans[:50] + ("…" if len(trans) > 50 else "")
                print(f"  EN: {orig_s}")
                print(f"  VI: {trans_s}")
        done_keys = set(ok for ok, _, _ in batch_buf)
        for ok in done_keys:
            progress[ok] = True
        batch_buf.clear()

    total = len(todo)
    for i, item in enumerate(todo, 1):
        batch_buf.append(item)
        if len(batch_buf) >= BATCH_SIZE:
            flush()
            save()
            elapsed = time.time() - start_time
            rate = translated / elapsed if elapsed > 0 else 0.001
            remain = (total - i) / rate
            pct = i / total * 100
            print(f"\n  [{i}/{total}] {pct:.1f}% | {rate:.1f} str/s"
                  f" | còn ~{remain/60:.0f} phút\n")

    flush()
    save()

    elapsed = time.time() - start_time
    print()
    print("=" * 65)
    print(f"  XONG! {translated:,} strings AI + {dict_hits:,} dict"
          f" trong {elapsed/60:.1f} phút")
    print(f"  Output: {OUT_FILE}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
