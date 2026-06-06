# Hướng dẫn Việt hóa 007 First Light

## Công cụ cần có
- **rpkg-cli.exe** (đã có trong `tools\rpkg\`)
- **Python 3.x** — tải tại https://python.org
- **Excel / Google Sheets / LibreOffice** — để dịch file CSV

---

## Quy trình đầy đủ

### Bước 1: Extract LOCR (đã chạy tự động)
```bat
cd "d:\Games\007 First Light\tools\rpkg"
rpkg-cli.exe -output_path "d:\Games\007 First Light\localization\LOCR" -extract_locr_to_json_from "d:\Games\007 First Light\Runtime"
```
> File rpkg ~55GB nên bước này mất khá lâu. Chờ cho đến khi xuất hiện file JSON trong thư mục `localization\LOCR`.

---

### Bước 2: Export chuỗi ra CSV
```bat
cd "d:\Games\007 First Light\localization"
python export_to_csv.py
```
Tạo ra file: `translation_export.csv`

---

### Bước 3: Dịch file CSV
Mở `translation_export.csv` bằng Excel hoặc Google Sheets.  
Điền bản dịch tiếng Việt vào **cột `vietnamese`**.

Cột `original` là văn bản gốc (English) — **không chỉnh sửa**.  
Cột `file_hash` và `string_hash` — **không chỉnh sửa**.

> **Mẹo:** Dùng Google Translate hoặc DeepL để dịch nhanh hàng loạt,
> sau đó chỉnh sửa thủ công các đoạn quan trọng như tên nhân vật, nhiệm vụ.

---

### Bước 4: Import bản dịch vào JSON
Mở file `import_from_csv.py` và chú ý dòng:
```python
TARGET_LANG = "schinese"
```
Đây là ngôn ngữ sẽ bị thay thế bằng tiếng Việt.  
Chọn một ngôn ngữ bạn không cần (ví dụ: `schinese`, `polish`, `russian`).

Sau đó chạy:
```bat
python import_from_csv.py
```

---

### Bước 5: Rebuild và Patch
```bat
rebuild_and_patch.bat
```
Hoặc thủ công:
```bat
cd "d:\Games\007 First Light\tools\rpkg"
rpkg-cli.exe -rebuild_locr_from_json_from "d:\Games\007 First Light\localization\LOCR"
```
Sau đó copy file `.rpkg` kết quả vào `Runtime\` với tên `chunk0patch1.rpkg`.

---

### Bước 6: Cài đặt trong game
- Chạy game → vào **Settings → Language**
- Chọn ngôn ngữ tương ứng với `TARGET_LANG` bạn đã chọn ở Bước 4

---

## Cấu trúc file JSON LOCR

```json
{
  "hash": "00A1B2C3D4E5F678",
  "type": "LOCR",
  "localization": {
    "english": [
      { "hash": "deadbeef", "string": "Agent Bond" },
      { "hash": "cafebabe", "string": "Mission Complete" }
    ],
    "schinese": [
      { "hash": "deadbeef", "string": "Điệp viên Bond" },
      { "hash": "cafebabe", "string": "Hoàn thành nhiệm vụ" }
    ]
  }
}
```

---

## Ghi chú kỹ thuật

| Ngôn ngữ key   | Tên hiển thị trong game |
|----------------|-------------------------|
| `english`      | English                 |
| `french`       | Français                |
| `italian`      | Italiano                |
| `german`       | Deutsch                 |
| `spanish`      | Español                 |
| `russian`      | Русский                 |
| `polish`       | Polski                  |
| `schinese`     | 简体中文                |
| `tchinese`     | 繁體中文                |
| `japanese`     | 日本語                  |
| `korean`       | 한국어                  |

Chọn `schinese` hoặc `polish` là an toàn nhất vì ít người dùng nhất.

---

## Lưu ý về font chữ tiếng Việt

Nếu game không hiển thị đúng dấu tiếng Việt (à, ắ, ể, ọ...):
- Thử dùng ký tự **không dấu** (Viet) hoặc font fallback
- Hoặc tìm cách inject font tiếng Việt vào game (cần nghiên cứu thêm với tool GLTF/texture)
