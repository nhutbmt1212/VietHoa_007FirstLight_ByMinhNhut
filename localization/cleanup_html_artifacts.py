"""
cleanup_html_artifacts.py
Dọn sạch các HTML tag rỗng/lỗi còn sót lại sau quá trình sync tag.
Ví dụ: <b></b>  <i/>  <b style="...">  còn lơ lửng không bọc gì

Chạy: python cleanup_html_artifacts.py
"""

import json
import re
import shutil
from pathlib import Path

VIET_FILE = r"d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\dialogue.json"

# HTML rỗng, mồ côi, hoặc malformed
EMPTY_HTML = re.compile(
    r'<[a-zA-Z][^>]*>\s*</[a-zA-Z]+>'    # <b></b> <i></i>
    r'|<[a-zA-Z][^>]*/>'                   # <i/> <b/>
    r'|<[a-zA-Z<][^>]*>\s*(?=<[a-zA-Z])' # <b<i> malformed
)
# Closing tag mồ côi không có opening tag tương ứng
ORPHAN_CLOSE = re.compile(r'</[a-zA-Z]+>')
# Opening tag malformed (có dấu quote lạc trong tên tag)
MALFORMED_OPEN = re.compile(r'<([a-zA-Z]+)["\'][^>]*>')

def has_matching_open(text: str, close_tag: str) -> bool:
    tag_name = re.search(r'</([a-zA-Z]+)>', close_tag).group(1)
    return bool(re.search(rf'<{tag_name}[\s>]', text))

def fix_mismatched_tags(text: str) -> str:
    """Sửa <b>nội dung</i> → <b>nội dung</b>"""
    # Tìm pattern <X>content</Y> với X ≠ Y
    def fix_close(m):
        open_tag = m.group(1)
        content  = m.group(2)
        return f'<{open_tag}>{content}</{open_tag}>'
    return re.sub(r'<([a-zA-Z]+)>([^<]+)</(?!\1)[a-zA-Z]+>', fix_close, text)

def fix_malformed_open(text: str) -> str:
    """<i">, <b"> → xóa hoàn toàn tag lỗi"""
    return MALFORMED_OPEN.sub(r'', text)

def clean(text: str) -> str:
    # 1. Sửa mismatched tags
    text = fix_mismatched_tags(text)
    # 2. Xóa opening tag malformed
    text = fix_malformed_open(text)
    # 3. Lặp xóa HTML rỗng
    prev = None
    while prev != text:
        prev = text
        text = EMPTY_HTML.sub('', text)
    # 4. Xóa closing tag mồ côi
    for m in list(ORPHAN_CLOSE.finditer(text)):
        if not has_matching_open(text, m.group()):
            text = text.replace(m.group(), '', 1)
    text = re.sub(r'  +', ' ', text).strip()
    return text

def main():
    viet_path = Path(VIET_FILE)
    data = json.loads(viet_path.read_text(encoding="utf-8"))

    backup = viet_path.with_suffix(".json.bak4")
    shutil.copy2(viet_path, backup)

    fixed = 0
    examples = []

    for key, entry in data.items():
        for seg_key, seg_text in entry.get("segments", {}).items():
            if not isinstance(seg_text, str):
                continue
            cleaned = clean(seg_text)
            if cleaned != seg_text:
                if len(examples) < 8:
                    examples.append((entry.get("speaker_name","?"), seg_text, cleaned))
                entry["segments"][seg_key] = cleaned
                fixed += 1

    viet_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] Dọn HTML rác: {fixed} entries")
    for spk, before, after in examples:
        print(f"  [{spk}]")
        print(f"    Trước: {before}")
        print(f"    Sau  : {after}")

if __name__ == "__main__":
    main()
