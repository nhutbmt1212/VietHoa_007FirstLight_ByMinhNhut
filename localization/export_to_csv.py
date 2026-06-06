"""
export_to_csv.py
----------------
Đọc tất cả file JSON LOCR đã extract, lấy chuỗi English (hoặc ngôn ngữ gốc)
và xuất ra file CSV để dịch sang tiếng Việt.

Cách dùng:
    python export_to_csv.py
Kết quả: translation_export.csv
"""

import json
import csv
import os
import glob

LOCR_DIR = os.path.join(os.path.dirname(__file__), "LOCR")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "translation_export.csv")

# Ưu tiên lấy từ ngôn ngữ nào (theo thứ tự)
SOURCE_LANG_PRIORITY = ["english", "en", "en_us"]

def find_source_lang(localization: dict) -> tuple[str, list] | tuple[None, None]:
    """Tìm ngôn ngữ nguồn có sẵn trong file LOCR."""
    for lang in SOURCE_LANG_PRIORITY:
        if lang in localization and localization[lang]:
            return lang, localization[lang]
    # Fallback: lấy ngôn ngữ đầu tiên có dữ liệu
    for lang, entries in localization.items():
        if entries:
            return lang, entries
    return None, None


def main():
    json_files = glob.glob(os.path.join(LOCR_DIR, "**", "*.JSON"), recursive=True)
    json_files += glob.glob(os.path.join(LOCR_DIR, "**", "*.json"), recursive=True)
    # Loại trùng
    json_files = list(set(json_files))

    if not json_files:
        print(f"[!] Không tìm thấy file JSON nào trong: {LOCR_DIR}")
        print("    Hãy chắc chắn đã chạy rpkg-cli extract trước.")
        return

    print(f"[+] Tìm thấy {len(json_files)} file JSON LOCR")

    rows = []
    for json_path in sorted(json_files):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[!] Lỗi đọc {json_path}: {e}")
                continue

        file_hash = data.get("hash", os.path.basename(json_path))
        localization = data.get("localization", {})

        source_lang, entries = find_source_lang(localization)
        if not entries:
            continue

        for entry in entries:
            string_hash = entry.get("hash", "")
            text = entry.get("string", "")
            if text.strip():
                rows.append({
                    "file_hash": file_hash,
                    "string_hash": string_hash,
                    "source_lang": source_lang,
                    "original": text,
                    "vietnamese": "",   # Cột để điền bản dịch
                })

    if not rows:
        print("[!] Không có chuỗi nào để export.")
        return

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file_hash", "string_hash", "source_lang", "original", "vietnamese"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Đã xuất {len(rows)} chuỗi ra: {OUTPUT_CSV}")
    print("    Mở file CSV, điền cột 'vietnamese', rồi chạy import_from_csv.py")


if __name__ == "__main__":
    main()
