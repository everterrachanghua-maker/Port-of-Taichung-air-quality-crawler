import os
import json
import requests
import time

# 1. 讀取環境變數
LINE_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')
LINE_UID = os.environ.get('LINE_USER_ID')

# 2. 定義預警標準 (依據您的圖片)
THRESHOLDS = {
    'O3': 100, 'PM25': 30, 'PM10': 75, 'CO': 31, 'SO2': 0.065, 'NO2': 100
}

def send_line(msg):
    if not LINE_TOKEN or not LINE_UID:
        print("未設定 LINE 密鑰，跳過發送")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_UID, "messages": [{"type": "text", "text": msg}]}
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            print("LINE 訊息發送成功")
        else:
            print(f"LINE 發送失敗: {res.text}")
    except Exception as e:
        print(f"網路錯誤: {e}")

def main():
    # 讀取數據檔案
    try:
        with open("air_quality.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"讀取 JSON 失敗: {e}")
        return

    # 取得沙鹿站數據作為基準
    shalu = next((s for s in data["central_data"] if s["station"] == "沙鹿"), None)
    if not shalu:
        print("找不到沙鹿站數據，無法比對")
        return

    alert_msg = ""
    # 遍歷所有測站
    for st in data["tcc_data"]:
        station_name = st["station"]

        # --- 關鍵修正：排除台電測站 ---
        if "台電" in station_name:
            print(f"跳過不檢查: {station_name}")
            continue
        
        st_alerts = []
        for key, limit in THRESHOLDS.items():
            try:
                # 取得數值並轉為數字
                val = float(st[key])
                shalu_val = float(shalu[key])
                
                # 預警判定：1. 大於圖片標準 且 2. 大於沙鹿 1.5 倍
                if val > limit and val > (shalu_val * 1.5):
                    st_alerts.append(f"● {key}: {val} (標準:{limit}, 沙鹿:{shalu_val})")
            except:
                continue
        
        if st_alerts:
            alert_msg += f"\n📍【{station_name}】異常！\n" + "\n".join(st_alerts) + "\n"

    # 如果有異常，則發送 LINE
    if alert_msg:
        full_msg = f"🚨 台中港港務測站預警 🚨\n{alert_msg}\n通知時間: {time.strftime('%Y/%m/%d %H:%M')}"
        send_line(full_msg)
        print("已發送港務預警通知")
    else:
        print("港務測站數據皆正常或未達警示門檻")

if __name__ == "__main__":
    main()
