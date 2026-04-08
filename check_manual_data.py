import os
import json
import requests
import time

# 1. 讀取環境變數 (現在只需要 Token，不需要 UID 了)
LINE_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')

# 2. 定義預警標準
THRESHOLDS = {
    'O3': 100, 'PM25': 30, 'PM10': 75, 'CO': 31, 'SO2': 0.065, 'NO2': 100
}

def send_line_broadcast(msg):
    if not LINE_TOKEN:
        print("未設定 LINE Token，跳過發送")
        return
    
    # --- 關鍵修正：改用 broadcast 接口 ---
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    # broadcast 不需要 "to" 參數，會發給所有好友
    payload = {
        "messages": [{"type": "text", "text": msg}]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            print("✅ 群發訊息成功，所有好友應皆已收到")
        else:
            print(f"❌ 群發失敗: {res.text}")
    except Exception as e:
        print(f"網路錯誤: {e}")

def main():
    try:
        with open("air_quality.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"讀取 JSON 失敗: {e}")
        return

    shalu = next((s for s in data["central_data"] if s["station"] == "沙鹿"), None)
    if not shalu:
        print("找不到沙鹿站數據，無法比對")
        return

    alert_msg = ""
    for st in data["tcc_data"]:
        station_name = st["station"]
        if "台電" in station_name: continue
        
        st_alerts = []
        for key, limit in THRESHOLDS.items():
            try:
                val = float(st[key])
                shalu_val = float(shalu[key])
                if val > limit and val > (shalu_val * 1.5):
                    st_alerts.append(f"● {key}: {val} (標準:{limit}, 沙鹿:{shalu_val})")
            except: continue
        
        if st_alerts:
            alert_msg += f"\n📍【{station_name}】異常！\n" + "\n".join(st_alerts) + "\n"

    if alert_msg:
        full_msg = f"🚨 台中港港務測站預警 🚨\n{alert_msg}\n通知時間: {time.strftime('%Y/%m/%d %H:%M')}"
        send_line_broadcast(full_msg)
    else:
        print("數據正常，未觸發預警")

if __name__ == "__main__":
    main()
