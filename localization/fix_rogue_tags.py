"""
fix_rogue_tags.py
Sửa tất cả tag {…} do AI hallucinate trong file bản dịch tiếng Việt.

Bản gốc tiếng Anh KHÔNG có tag {…} nào — game chỉ dùng [...].
AI đã tự thêm hai loại lỗi:
  1. Tag vô nghĩa hoàn toàn → XÓA:  {PAUSE} {SPEAKER} {SPELLER} {SPECAUSE} {RESUME} {STOP} {0} {1} ...
  2. Tag đúng nội dung nhưng sai format → SỬA: {Laughs} → [Laughs], {sigh} → [sigh] ...

Chạy: python fix_rogue_tags.py
"""

import json
import re
import shutil
from pathlib import Path

VIET_FILE = r"d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"
ORIG_FILE  = r"d:\Games\007 First Light\localization\extracted\dialogue.json"

# ─── Các tag vô nghĩa do AI bịa — XÓA hoàn toàn ─────────────────────────────
DELETE_TAGS = re.compile(
    r'\{(?:'
    r'PAUSE|SPEAKER|SPELLER|SPECAUSE|RESUME|STOP|'
    r'BREAK|END|START|WAIT|NEXT|CONT|DONE|'
    r'\d+'           # {0} {1} {2} placeholder số
    r')\}',
    re.IGNORECASE
)

# ─── Tag đúng nội dung nhưng sai format {X} → [X] — SỬA ─────────────────────
# Chỉ chuyển các stage direction hợp lệ thường gặp trong game
VALID_STAGE_DIRECTIONS = {
    # Tiếng Anh gốc (lowercase và mixed)
    "laughs", "chuckles", "chuckle", "sighs", "sigh",
    "scoffs", "scoff", "coughs", "cough", "gasps", "gasp",
    "grunts", "grunt", "whispers", "whisper", "shouts", "shout",
    "screams", "scream", "groans", "groan", "mutters", "mutter",
    "whistle", "whistles", "snorts", "snort", "yells", "yell",
    "inhales", "exhales", "breathes", "sighing", "laughing",
    # Tiếng Việt hoặc thêm bởi AI
    "cười", "thở dài", "thì thầm",
}

def fix_format_tags(text: str) -> tuple[str, int, int]:
    """
    Xử lý text:
    - Xóa tag vô nghĩa
    - Sửa {ValidTag} → [ValidTag]
    Trả về (text_đã_sửa, số_tag_xóa, số_tag_sửa)
    """
    deleted = 0
    converted = 0

    # Bước 1: Xóa tag vô nghĩa
    new_text, n = DELETE_TAGS.subn('', text)
    deleted += n

    # Bước 2: Sửa {ValidTag} → [ValidTag] nếu là stage direction hợp lệ
    def convert_if_valid(m):
        nonlocal converted
        inner = m.group(1)
        if inner.lower() in VALID_STAGE_DIRECTIONS:
            converted += 1
            return f"[{inner}]"
        # Tag không rõ nhưng không phải vô nghĩa đã xóa → để nguyên (hoặc xóa luôn)
        # Mặc định xóa để an toàn
        nonlocal deleted
        deleted += 1
        return ''

    new_text = re.sub(r'\{([^}]+)\}', convert_if_valid, new_text)

    # Dọn khoảng trắng thừa
    new_text = re.sub(r'  +', ' ', new_text).strip()

    return new_text, deleted, converted


def main():
    viet_path = Path(VIET_FILE)
    orig_path = Path(ORIG_FILE)

    print("=" * 65)
    print("  fix_rogue_tags.py — Sửa tất cả tag {} do AI hallucinate")
    print("=" * 65)

    viet_data = json.loads(viet_path.read_text(encoding="utf-8"))
    orig_data = json.loads(orig_path.read_text(encoding="utf-8"))

    # Backup
    backup_path = viet_path.with_suffix(".json.bak2")
    shutil.copy2(viet_path, backup_path)
    print(f"[OK] Backup: {backup_path.name}")

    total_deleted  = 0
    total_converted = 0
    fixed_entries  = 0
    examples_del   = []
    examples_conv  = []

    for key, entry in viet_data.items():
        segments = entry.get("segments", {})

        for seg_key, seg_text in segments.items():
            if not isinstance(seg_text, str):
                continue
            if '{' not in seg_text:
                continue

            cleaned, n_del, n_conv = fix_format_tags(seg_text)

            if n_del > 0 or n_conv > 0:
                if n_del > 0 and len(examples_del) < 6:
                    examples_del.append({
                        "speaker": entry.get("speaker_name", "?"),
                        "before": seg_text,
                        "after": cleaned,
                    })
                if n_conv > 0 and len(examples_conv) < 6:
                    examples_conv.append({
                        "speaker": entry.get("speaker_name", "?"),
                        "before": seg_text,
                        "after": cleaned,
                    })
                entry["segments"][seg_key] = cleaned
                total_deleted  += n_del
                total_converted += n_conv
                fixed_entries  += 1

    # Lưu
    viet_path.write_text(
        json.dumps(viet_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n[OK] Đã sửa {fixed_entries} entries:")
    print(f"      - Xóa tag vô nghĩa : {total_deleted}  lần")
    print(f"      - Sửa {{X}} → [X]    : {total_converted} lần")
    print(f"[OK] Saved: {viet_path.name}\n")

    if examples_del:
        print("Ví dụ XÓA tag vô nghĩa:")
        print("-" * 50)
        for ex in examples_del:
            print(f"  [{ex['speaker']}]")
            print(f"    Trước: {ex['before']}")
            print(f"    Sau  : {ex['after']}")
        print()

    if examples_conv:
        print("Ví dụ SỬA format {X} → [X]:")
        print("-" * 50)
        for ex in examples_conv:
            print(f"  [{ex['speaker']}]")
            print(f"    Trước: {ex['before']}")
            print(f"    Sau  : {ex['after']}")
        print()

    print("Bước tiếp: chạy inject_all.bat để đưa vào game")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
