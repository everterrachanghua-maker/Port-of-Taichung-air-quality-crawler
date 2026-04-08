import os
import requests

def test_send():
    token = os.environ.get('LINE_ACCESS_TOKEN')
    uid = os.environ.get('LINE_USER_ID')
    
    if not token or not uid:
        print("❌ 錯誤：找不到環境變數，請檢查 GitHub Secrets 設定。")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {
        "to": uid,
        "messages": [{"type": "text", "text": "✅ 台中港預警系統：LINE 連通測試成功！"}]
    }
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("✅ 訊息已成功發送至您的 LINE！")
    else:
        print(f"❌ 發送失敗，錯誤碼：{res.status_code}")
        print(res.text)

if __name__ == "__main__":
    test_send()
