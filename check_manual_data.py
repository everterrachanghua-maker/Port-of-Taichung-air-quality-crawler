import os
import json
import requests

LINE_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')
LINE_UID = os.environ.get('LINE_USER_ID')
THRESHOLDS = {'O3': 100, 'PM25': 30, 'PM10': 75, 'CO': 31, 'SO2': 0.065, 'NO2': 100}

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_UID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, headers=headers, json=payload)

def check_json():
    # 讀取剛剛手動上傳到 GitHub 的檔案
    with open("air_quality.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    shalu = data["central_data"][0]
    alert_msg = ""
    
    for st in data["tcc_data"]:
        st_alerts = []
        for k, limit in THRESHOLDS.items():
            try:
                v, s_v = float(st[k]), float(shalu[k])
                if v > limit and v > (s_v * 1.5):
                    st_alerts.append(f"● {k}: {v} (標準:{limit}, 沙鹿:{s_v})")
            except: continue
        if st_alerts:
            alert_msg += f"\n📍【{st['station']}】異常！\n" + "\n".join(st_alerts) + "\n"
    
    if alert_msg:
        send_line(f"🚨 手動數據預警測試 🚨\n{alert_msg}")
        print("偵測到異常，已發送 LINE")
    else:
        print("數據正常，未發送 LINE")

if __name__ == "__main__":
    check_json()
