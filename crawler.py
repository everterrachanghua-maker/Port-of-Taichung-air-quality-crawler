import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data():
    print("--- 啟動自動化爬蟲 ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30)

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        driver.get(url)
        time.sleep(10)

        # 1. 選擇區域
        print("正在切換區域：中部空品區")
        area_select = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Area")))
        Select(area_select).select_by_visible_text("中部空品區")
        time.sleep(10) # 關鍵：給網站足夠時間刷新測站清單

        for st in stations:
            print(f"正在抓取測站：{st}")
            try:
                # 重新定位測站選單
                station_select_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Station")))
                Select(station_select_el).select_by_visible_text(st)
                time.sleep(2)

                # 點擊查詢
                btn = driver.find_element(By.ID, "cp_content_btn_Query")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(8) # 等待數據表格刷新

                # 獲取數值（使用更寬鬆的定位）
                def get_val(css_id):
                    try: return driver.find_element(By.ID, css_id).text
                    except: return "N/A"

                data = {
                    "station": st,
                    "time": get_val("cp_content_lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": get_val("cp_content_lab_O3"),
                    "PM25": get_val("cp_content_lab_PM25"),
                    "PM10": get_val("cp_content_lab_PM10"),
                    "CO": get_val("cp_content_lab_CO"),
                    "SO2": get_val("cp_content_lab_SO2"),
                    "NO2": get_val("cp_content_lab_NO2")
                }
                results.append(data)
                print(f"-> {st} 抓取成功")
            except Exception as e:
                print(f"-> {st} 跳過，原因：{str(e)}")

    finally:
        # 無論如何都產生檔案，防止 Action 報錯
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"--- 任務結束，共抓取 {len(results)} 筆數據 ---")
        driver.quit()

if __name__ == "__main__":
    scrape_data()
