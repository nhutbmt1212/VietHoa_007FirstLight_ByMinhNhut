import json
import urllib.request

SYSTEM_PROMPT = """Bạn là dịch giả chuyên nghiệp cho game hành động gián điệp "007 First Light" (James Bond).
━━━ QUY TẮC KỸ THUẬT ━━━
• GIỮ NGUYÊN TUYỆT ĐỐI [Tag] stage directions: [Laughs] [Sighs] [Coughs] [Whispers] [In Serbian] v.v.
• Trả về ĐÚNG số dòng đánh số: 1. ... 2. ... 3. ...
"""

prompt = """Dịch 4 dòng dialogue sang tiếng Việt.
━━━ CÂU CẦN DỊCH ━━━
1. Bond: [In Montenegrin] Relax. I'll be out in a sec.
2. Hostile: [In Montenegrin] There you are! What's taking you so long?
3. Hostile: [Speaking in Serbian] Hey, what the... forget it.
4. Hostile: [Laughs] Nobody's ever really out. You know that, right...

Trả về đúng 4 dòng đánh số, CHỈ phần câu dịch.
KHÔNG viết lại tên nhân vật (Bond:, Hostile:).
TUYỆT ĐỐI KHÔNG xóa hoặc dịch các thẻ trong ngoặc vuông như [Laughs], [In Montenegrin]. Bắt buộc phải giữ nguyên chúng ở đầu câu!"""

payload = json.dumps({
    "model": "qwen/qwen3-next-80b-a3b-instruct",
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.05,
    "max_tokens": 800,
}).encode("utf-8")

req = urllib.request.Request(
    "https://integrate.api.nvidia.com/v1/chat/completions",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer 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"
    }, method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print("RAW RESPONSE:")
        print(result["choices"][0]["message"]["content"])
except Exception as e:
    print("ERROR:", e)
