import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data():
    # 設定 Chrome 為無頭模式 (Headless)，GitHub Actions 必須開啟
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # 初始化瀏覽器
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        driver.get(url)
        time.sleep(5) # 等待網頁載入

        # 1. 選擇「所屬單位」: 大型事業
        unit_select = Select(driver.find_element(By.ID, "cp_content_ddl_Org"))
        unit_select.select_by_visible_text("大型事業")
        time.sleep(2) # 等待測站選單更新

        # 2. 選擇「測站名稱」: 台電協和宿舍
        station_select = Select(driver.find_element(By.ID, "cp_content_ddl_Station"))
        station_select.select_by_visible_text("台電協和宿舍")
        time.sleep(1)

        # 3. 點擊「查詢」
        driver.find_element(By.ID, "cp_content_btn_Query").click()
        time.sleep(5) # 等待數據出爐

        # 4. 抓取數據 (這裡抓取 PM2.5 作為範例，需視網頁結構調整 class)
        # 注意：實際 class 名稱需根據網頁 F12 檢查，以下為常見結構模擬
        try:
            pm25 = driver.find_element(By.CSS_SELECTOR, ".p_pm25").text
            pm10 = driver.find_element(By.CSS_SELECTOR, ".p_pm10").text
            update_time = driver.find_element(By.CSS_SELECTOR, ".header_time").text
            
            print(f"抓取成功！時間：{update_time}, PM2.5: {pm25}, PM10: {pm10}")
            
            # 存成 CSV
            df = pd.DataFrame([{ "Time": update_time, "PM25": pm25, "PM10": pm10 }])
            df.to_csv("air_quality.csv", index=False)
            
        except Exception as e:
            print(f"抓取數據失敗: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
