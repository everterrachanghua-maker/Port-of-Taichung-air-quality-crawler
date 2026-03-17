import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []
    
    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        driver.get(url)
        time.sleep(10) # 初始載入給久一點

        # 1. 選擇「中部空品區」
        area_select = Select(driver.find_element(By.ID, "cp_content_ddl_Area"))
        area_select.select_by_visible_text("中部空品區")
        time.sleep(3)

        for st in stations:
            print(f"正在抓取: {st}...")
            # 2. 選擇「測站名稱」
            station_select = Select(driver.find_element(By.ID, "cp_content_ddl_Station"))
            station_select.select_by_visible_text(st)
            time.sleep(2)
            
            # 3. 點擊「查詢」
            driver.find_element(By.ID, "cp_content_btn_Query").click()
            time.sleep(5) # 等待數據刷新
            
            # 4. 抓取數據 (使用 class 定位)
            try:
                data = {
                    "station": st,
                    "time": driver.find_element(By.CSS_SELECTOR, ".header_time").text.replace("發布時間：", "").strip(),
                    "O3": driver.find_element(By.CSS_SELECTOR, ".p_o3").text,
                    "PM25": driver.find_element(By.CSS_SELECTOR, ".p_pm25").text,
                    "PM10": driver.find_element(By.CSS_SELECTOR, ".p_pm10").text,
                    "CO": driver.find_element(By.CSS_SELECTOR, ".p_co").text,
                    "SO2": driver.find_element(By.CSS_SELECTOR, ".p_so2").text,
                    "NO2": driver.find_element(By.CSS_SELECTOR, ".p_no2").text
                }
                results.append(data)
                print(f"{st} 抓取完成")
            except Exception as e:
                print(f"{st} 抓取失敗: {e}")

        # 儲存結果為 JSON
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
