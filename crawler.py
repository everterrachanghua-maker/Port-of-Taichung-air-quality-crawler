import os
import time
import json
import requests
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 1. 讀取 LINE 密鑰
LINE_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')
LINE_UID = os.environ.get('LINE_USER_ID')

# 2. 定義預警標準 (依據您的表格)
THRESHOLDS = {
    'O3': 100, 'PM25': 30, 'PM10': 75, 'CO': 31, 'SO2': 0.065, 'NO2': 100
}

# 3. 座標資料庫 (TWD97)
STATION_COORDS = {
    "港務中泊渠": {"x": 201305.6, "y": 2683862},
    "港務南突堤": {"x": 199602.4, "y": 2681284},
    "港務工作船渠": {"x": 201144.2, "y": 2687122},
    "台電清水": {"x": 206991.9, "y": 2684871},
    "台電梧棲": {"x": 202298.9, "y": 2683072},
    "台電龍井": {"x": 199067.2, "y": 2677251},
    "沙鹿": {"x": 206367.6, "y": 2680337}
}

def send_line_alert(msg):
    if not LINE_TOKEN or not LINE_UID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_UID, "messages": [{"type": "text", "text": msg}]}
    try: requests.post(url, headers=headers, json=payload)
    except: print("LINE發送失敗")

def scrape_data():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 45)
    
    final_res = {"tcc_data": [], "central_data": []}

    try:
        # --- 抓取港區 ---
        driver.get("https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc")
        time.sleep(10)
        area = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area).select_by_visible_text("中部空品區")
        time.sleep(10)
        
        for name in ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]:
            try:
                sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(sel).select_by_visible_text(name)
                time.sleep(3)
                driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
                time.sleep(10)
                def g(nid): return driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                final_res["tcc_data"].append({
                    "station": name, "time": g("lab_IssueTime").replace("發布時間：","").strip(),
                    "O3": g("lab_O3"), "PM25": g("lab_PM25"), "PM10": g("lab_PM10"),
                    "CO": g("lab_CO"), "SO2": g("lab_SO2"), "NO2": g("lab_NO2"),
                    "x": STATION_COORDS[name]["x"], "y": STATION_COORDS[name]["y"]
                })
            except: pass

        # --- 抓取沙鹿 ---
        driver.get("https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx")
        time.sleep(10)
        area2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area2).select_by_visible_text("中部空品區")
        time.sleep(5)
        st2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
        Select(st2).select_by_visible_text("沙鹿")
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
        time.sleep(12)
        def gc(nid): return driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
        shalu_item = {
            "station": "沙鹿", "time": gc("lab_IssueTime").replace("發布時間：","").strip(),
            "O3": gc("lab_O3"), "PM25": gc("lab_PM25"), "PM10": gc("lab_PM10"),
            "CO": gc("lab_CO"), "SO2": gc("lab_SO2"), "NO2": gc("lab_NO2"),
            "x": STATION_COORDS["沙鹿"]["x"], "y": STATION_COORDS["沙鹿"]["y"]
        }
        final_res["central_data"].append(shalu_item)

        # --- LINE 預警比對 ---
        alert_msg = ""
        for st in final_res["tcc_data"]:
            st_alerts = []
            for k, limit in THRESHOLDS.items():
                try:
                    v, s_v = float(st[k]), float(shalu_item[k])
                    if v > limit and v > (s_v * 1.5):
                        st_alerts.append(f"● {k}: {v} (標準:{limit}, 沙鹿:{s_v})")
                except: continue
            if st_alerts:
                alert_msg += f"\n📍【{st['station']}】異常！\n" + "\n".join(st_alerts) + "\n"
        
        if alert_msg:
            send_line_alert(f"🚨 台中港空氣異常預警 🚨\n{alert_msg}\n時間: {time.strftime('%m/%d %H:%M')}")

        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(final_res, f, ensure_ascii=False, indent=4)

    except: print(traceback.format_exc())
    finally: driver.quit()

if __name__ == "__main__":
    scrape_data()

if __name__ == "__main__":
    scrape_data()
