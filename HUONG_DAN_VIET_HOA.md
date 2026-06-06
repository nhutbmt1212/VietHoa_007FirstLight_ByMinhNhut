# Hướng dẫn Việt hóa 007 First Light

> **Tác giả toolkit:** Hesham ([@7akeem0](https://github.com/7akeem0))  
> **Toolkit:** [007-firstlight-toolkit](https://github.com/7akeem0/007-firstlight-toolkit)  
> **Game:** 007 First Light (IO Interactive, Glacier Engine, RPKG v2)

---

## Yêu cầu

| Thứ cần | Ghi chú |
|---------|---------|
| Python 3.10+ | Đã cài tại `C:\Users\...\AppData\Local\Programs\Python\Python312\` |
| `lz4`, `fonttools` | Đã cài qua `pip` |
| Game **007 First Light** | Bản FitGirl tại `d:\Games\007 First Light\` |

---

## Cấu trúc thư mục

```
d:\Games\007 First Light\
├── Runtime\
│   ├── chunk0.rpkg          ← file game gốc (19 GB)
│   ├── chunk1.rpkg          ← file game gốc (35 GB)
│   └── _toolkit_backup\     ← backup tự động khi inject
├── 007-firstlight-toolkit-main\
│   ├── tools\
│   │   ├── extract_text.py        ← bước 1: extract
│   │   └── install_translation.py ← bước 3: inject / uninject
│   └── examples\vietnamese\
│       ├── translation_config.json
│       └── translations\          ← file dịch của bạn
└── localization\extracted\
    ├── ui.json          ← bản gốc tiếng Anh (đã extract)
    ├── dialogue.json    ← bản gốc tiếng Anh (đã extract)
    └── speakers.json    ← bản gốc tiếng Anh (đã extract)
```

---

## Bước 1 — Extract text từ game (đã làm)

> File gốc tiếng Anh đã có sẵn tại `localization\extracted\`.  
> **Bỏ qua bước này nếu đã extract rồi.** Chỉ cần chạy lại nếu game được update.

```powershell
cd "d:\Games\007 First Light\007-firstlight-toolkit-main"
$env:PATH = "C:\Users\nhutb\AppData\Local\Programs\Python\Python312;" + $env:PATH
python tools/extract_text.py `
    --game-dir "d:\Games\007 First Light" `
    --out "d:\Games\007 First Light\localization\extracted"
```

Kết quả:
- `ui.json` — 8,435 chuỗi giao diện (menu, HUD, cài đặt...)
- `dialogue.json` — 17,612 dòng thoại
- `speakers.json` — 104 tên nhân vật

---

## Bước 2 — Dịch các file JSON

Copy 3 file gốc vào thư mục dịch:

```powershell
mkdir "d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations"
copy "d:\Games\007 First Light\localization\extracted\*.json" `
     "d:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\"
```

Sau đó mở từng file bằng VSCode hoặc bất kỳ text editor nào và dịch.

### Quy tắc dịch quan trọng

**Chỉ thay đổi phần value (giá trị), KHÔNG đổi key.**

#### ui.json — Chuỗi giao diện

Format:
```json
"019CD7E60D94FC71": {
    "9EE989DD": "In menu",
    "77E54884": "Playing {0} in {1}"
}
```

Sau khi dịch:
```json
"019CD7E60D94FC71": {
    "9EE989DD": "Trong menu",
    "77E54884": "Đang chơi {0} trong {1}"
}
```

**Lưu ý:**
- Giữ nguyên `{0}`, `{1}`, `{2}`... — đây là placeholder sẽ được thay bằng giá trị động
- Giữ nguyên `<br/>`, `<b>`, `</b>` — đây là HTML tag
- Giữ nguyên `\n` — ký tự xuống dòng
- **KHÔNG** đổi key (dãy số hex như `9EE989DD`)
- **KHÔNG** đổi resource hash (dãy hex 16 ký tự như `019CD7E60D94FC71`)

#### dialogue.json — Dòng thoại

Format:
```json
"01C76A08493EEE11": {
    "segments": [
        "Bond. James Bond.",
        "We have a situation."
    ]
}
```

Sau khi dịch:
```json
"01C76A08493EEE11": {
    "segments": [
        "Bond. James Bond.",
        "Chúng ta có tình huống khẩn cấp."
    ]
}
```

**Lưu ý:**
- Giữ nguyên số lượng segment — không thêm, không bớt
- Không dịch các token đặc biệt như `{PAUSE}`, `{SPEAKER}`, `<i>...</i>`

#### speakers.json — Tên nhân vật

Format:
```json
{
    "James Bond": "",
    "M": "",
    "Q": "",
    "Nomi": ""
}
```

Sau khi dịch (hoặc giữ nguyên tên):
```json
{
    "James Bond": "James Bond",
    "M": "M",
    "Q": "Q",
    "Nomi": "Nomi"
}
```

**Lưu ý:** Nếu để value trống `""` thì tên gốc sẽ được giữ nguyên.

---

## Bước 3 — Inject việt hóa vào game

> ⚠️ **Toolkit tự động tạo backup** trước khi ghi. An toàn để thử.

```powershell
cd "d:\Games\007 First Light\007-firstlight-toolkit-main"
$env:PATH = "C:\Users\nhutb\AppData\Local\Programs\Python\Python312;" + $env:PATH
python tools/install_translation.py --config examples/vietnamese/translation_config.json
```

Output mong đợi:
```
🎮 game: d:\Games\007 First Light
🌐 language: none

=== chunk0.rpkg ===
   UI strings: 7,295  |  dialogue: 4,797  |  speakers: 104

=== chunk1.rpkg ===
   UI strings: 1,140  |  dialogue: 12,815  |  speakers: 0

==================================================
✅ Translation installed successfully!
   backup: d:\Games\007 First Light\Runtime\_toolkit_backup
🎮 Launch the game now.
==================================================
```

Sau đó chạy game bình thường — **không cần đổi ngôn ngữ trong Settings**.  
Toolkit ghi thẳng vào slot tiếng Anh nên game hiện tiếng Việt mặc định.

---

## Bước 4 — Uninject (khôi phục bản gốc)

### Cách 1: Dùng lệnh restore (nhanh nhất)

```powershell
cd "d:\Games\007 First Light\007-firstlight-toolkit-main"
$env:PATH = "C:\Users\nhutb\AppData\Local\Programs\Python\Python312;" + $env:PATH
python tools/install_translation.py --restore
```

Lệnh này đọc backup từ `Runtime\_toolkit_backup\` và phục hồi chunk0/chunk1 về bản gốc.

### Cách 2: Verify files qua FitGirl Launcher

Mở `FitGirl-Launcher.exe` → chọn **Verify** → launcher sẽ restore các file bị thay đổi.

---

## Dry run — Kiểm tra trước khi inject

Muốn xem preview mà không ghi gì vào file:

```powershell
python tools/install_translation.py --config examples/vietnamese/translation_config.json --dry
```

---

## Sau khi game update

Khi game được update, các file chunk có thể thay đổi — bản dịch sẽ bị mất.

```powershell
# 1. Restore về bản gốc trước
python tools/install_translation.py --restore

# 2. Extract lại text mới (phòng khi có chuỗi mới)
python tools/extract_text.py --game-dir "d:\Games\007 First Light" --out localization\extracted

# 3. Cập nhật file dịch nếu cần

# 4. Inject lại
python tools/install_translation.py --config examples/vietnamese/translation_config.json
```

---

## Bước 5 — Inject font tiếng Việt có dấu

Glacier Engine dùng **Scaleform GFX** để render font. Font mặc định của game không có ký tự tiếng Việt có dấu — cần inject font mới.

### Tải font Noto Sans

1. Vào **https://fonts.google.com/noto/specimen/Noto+Sans**
2. Click **"Download family"**
3. Giải nén, copy các file TTF sau vào thư mục:  
   `007-firstlight-toolkit-main\examples\vietnamese\fonts\`

| File cần copy | Weight |
|---------------|--------|
| `NotoSans-Regular.ttf` | Thường |
| `NotoSans-Bold.ttf` | Đậm |
| `NotoSans-Medium.ttf` | Vừa |
| `NotoSans-SemiBold.ttf` | Nửa đậm |

> Nếu không có Medium/SemiBold, copy Regular thay thế cũng được.

### Inject font

**Cách nhanh:** Chạy `install_font_viet.bat` (ở thư mục gốc game).

**Hoặc chạy lệnh thủ công:**
```powershell
cd "d:\Games\007 First Light\007-firstlight-toolkit-main"
$env:PATH = "C:\Users\nhutb\AppData\Local\Programs\Python\Python312;" + $env:PATH
python tools/install_font.py --config examples/vietnamese/font_config.json
```

Output mong đợi:
```
🎮 game: d:\Games\007 First Light
📋 config: examples/vietnamese/font_config.json
📖 reading chunk0...
💾 original font already backed up
💾 backing up tables...
🔨 building new font...
   font 1 (NotoSans-Bold.ttf): 170 glyphs prepared
   font 2 (NotoSans-Regular.ttf): 170 glyphs prepared
   ...
✅ Font installed successfully!
```

### Unicode range được inject

| Range | Ký tự | Số lượng |
|-------|-------|---------|
| `U+00C0–U+00FF` | À Á Â Ã È É Ê Ì Í Ò Ó Ô Ù Ú Ý à á â ã... | 64 |
| `U+0102–U+0103` | Ă ă | 2 |
| `U+0110–U+0111` | Đ đ | 2 |
| `U+01A0–U+01B0` | Ơ ơ Ư ư | 17 |
| `U+1EA0–U+1EF9` | ắặềệổộủụ... (Latin Extended Additional) | 90 |
| **Tổng** | | **~175** (giới hạn an toàn ~247) |

### Khôi phục font gốc

```powershell
python tools/install_font.py --restore
```

Hoặc chạy `restore_font_goc.bat`.

---

## Tóm tắt lệnh nhanh

| Tác vụ | Lệnh / File |
|--------|------|
| Extract text | `python tools/extract_text.py --game-dir "d:\Games\007 First Light" --out localization\extracted` |
| Dry run (preview) | `python tools/install_translation.py --config examples/vietnamese/translation_config.json --dry` |
| **Inject bản dịch** | `python tools/install_translation.py --config examples/vietnamese/translation_config.json` |
| **Uninject bản dịch** | `python tools/install_translation.py --restore` |
| **Inject font tiếng Việt** | `install_font_viet.bat` hoặc `python tools/install_font.py --config examples/vietnamese/font_config.json` |
| **Restore font gốc** | `restore_font_goc.bat` hoặc `python tools/install_font.py --restore` |

> Chạy tất cả lệnh từ thư mục `d:\Games\007 First Light\007-firstlight-toolkit-main\`  
> và nhớ set PATH trước: `$env:PATH = "C:\Users\nhutb\AppData\Local\Programs\Python\Python312;" + $env:PATH`
