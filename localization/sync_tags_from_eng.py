"""
sync_tags_from_eng.py
Bê chính xác các [Tag] stage direction từ bản gốc tiếng Anh sang bản dịch tiếng Việt.

Chiến lược:
- [Tag] ở ĐẦU câu EN  → đặt ở đầu câu VI
- [Tag] ở CUỐI câu EN → đặt ở cuối câu VI
- [Tag] ở GIỮA câu EN → đặt sau ~N% độ dài câu VI tương ứng (vị trí tương đối)
- Xóa các dạng dịch sai: (Thở dài), <i>(Ho khan)</i>, (bằng tiếng nước ngoài)... 
  khi biết tag gốc tương ứng

Chạy: python sync_tags_from_eng.py
"""

import json
import re
import shutil
from pathlib import Path

ORIG_FILE = r"d:\Games\007 First Light\localization\extracted\dialogue.json"
VIET_FILE = r"d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"

TAG_RE = re.compile(r'\[[^\]]+\]')

# Các pattern "dịch sai" phổ biến mà AI tạo ra thay cho [Tag]
# Sẽ bị xóa trước khi chèn tag đúng
FAKE_TRANSLATIONS = re.compile(
    r'<[ib]>\s*\([^)]*\)\s*</[ib]>'   # <i>(mô tả)</i> hoặc <b>(mô tả)</b>
    r'|\([^)]{2,40}\)'                  # (mô tả ngắn trong ngoặc tròn)
    r'|\[[^\]]{2,40}\]',                # [mô tả sai] — không phải tag gốc
    re.IGNORECASE
)


def get_tag_positions(text: str) -> list[dict]:
    """Trả về danh sách {tag, start, end, rel_pos} trong text."""
    results = []
    total = len(text.strip())
    for m in TAG_RE.finditer(text):
        rel = m.start() / total if total > 0 else 0
        results.append({
            "tag": m.group(),
            "start": m.start(),
            "end": m.end(),
            "rel_pos": rel,
        })
    return results


def classify_position(tag_info: dict, text: str) -> str:
    """Phân loại vị trí tag: 'start', 'end', 'middle'."""
    stripped = text.strip()
    tag = tag_info["tag"]
    if stripped.startswith(tag):
        return "start"
    if stripped.endswith(tag):
        return "end"
    return "middle"


def inject_tags(viet_text: str, tag_infos: list[dict], orig_text: str) -> str:
    """
    Chèn lại các [Tag] từ bản gốc vào bản dịch VI theo vị trí tương đối.
    """
    # Trước tiên xóa các tag [..] đã có trong VI (để tránh trùng)
    # Chỉ xóa nếu chúng KHÔNG giống tag gốc
    orig_tags_set = {ti["tag"].lower() for ti in tag_infos}
    
    def remove_wrong_tags(m):
        if m.group().lower() in orig_tags_set:
            return m.group()  # giữ nguyên nếu đúng tag
        return ""
    
    text = TAG_RE.sub(remove_wrong_tags, viet_text)
    text = text.strip()

    # Chèn từng tag theo vị trí
    for ti in tag_infos:
        tag = ti["tag"]
        pos = classify_position(ti, orig_text)

        if pos == "start":
            text = tag + " " + text
        elif pos == "end":
            text = text + " " + tag
        else:
            # Giữa câu: chèn tại vị trí tương đối
            rel = ti["rel_pos"]
            insert_at = int(len(text) * rel)
            # Tìm word boundary gần nhất
            while insert_at < len(text) and text[insert_at] != ' ':
                insert_at += 1
            text = text[:insert_at] + " " + tag + " " + text[insert_at:]

    # Dọn khoảng trắng thừa
    text = re.sub(r'  +', ' ', text).strip()
    return text


def tags_match(orig_tags: list, viet_tags: list) -> bool:
    """Kiểm tra tag đã đúng chưa (so sánh lowercase)."""
    return sorted(t.lower() for t in orig_tags) == sorted(t.lower() for t in viet_tags)


def main():
    orig_path = Path(ORIG_FILE)
    viet_path = Path(VIET_FILE)

    print("=" * 65)
    print("  sync_tags_from_eng.py — Bê [Tag] từ bản EN sang VI")
    print("=" * 65)

    orig_data = json.loads(orig_path.read_text(encoding="utf-8"))
    viet_data = json.loads(viet_path.read_text(encoding="utf-8"))

    # Backup
    backup = viet_path.with_suffix(".json.bak3")
    shutil.copy2(viet_path, backup)
    print(f"[OK] Backup: {backup.name}\n")

    fixed     = 0
    already_ok = 0
    skipped   = 0
    examples  = []

    for key, orig_entry in orig_data.items():
        viet_entry = viet_data.get(key)
        if not viet_entry:
            continue

        orig_segs = orig_entry.get("segments", {})
        viet_segs = viet_entry.get("segments", {})

        for seg_key, orig_text in orig_segs.items():
            orig_tags = TAG_RE.findall(orig_text)
            if not orig_tags:
                continue  # Câu gốc không có tag → skip

            viet_text = viet_segs.get(seg_key, "")
            if not viet_text:
                skipped += 1
                continue

            viet_tags = TAG_RE.findall(viet_text)

            # Đã đúng rồi
            if tags_match(orig_tags, viet_tags):
                already_ok += 1
                continue

            # Cần sync
            tag_infos = get_tag_positions(orig_text)
            new_text = inject_tags(viet_text, tag_infos, orig_text)

            if len(examples) < 15:
                examples.append({
                    "speaker": orig_entry.get("speaker_name", "?"),
                    "orig":    orig_text,
                    "before":  viet_text,
                    "after":   new_text,
                    "tags":    orig_tags,
                })

            viet_data[key]["segments"][seg_key] = new_text
            fixed += 1

    # Lưu
    viet_path.write_text(
        json.dumps(viet_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] Đã sync    : {fixed} entries")
    print(f"[OK] Đã đúng sẵn: {already_ok} entries")
    print(f"[--] Bỏ qua     : {skipped} entries (VI không có text)")
    print(f"[OK] Saved: {viet_path.name}\n")

    if examples:
        print("=" * 65)
        print("Chi tiết các dòng đã được sync:")
        print("=" * 65)
        for ex in examples:
            print(f"\n  [{ex['speaker']}]  tags: {ex['tags']}")
            print(f"  EN    : {ex['orig']}")
            print(f"  Trước : {ex['before']}")
            print(f"  Sau   : {ex['after']}")

    print("\nBước tiếp: chạy inject_all.bat để đưa vào game")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
