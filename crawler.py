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
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 偽裝成一般瀏覽器，避免被擋
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30) # 增加等待時間到 30 秒

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"正在前往網頁: {url}")
        driver.get(url)

        # 等待區域選單出現
        area_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Area")))
        
        # 1. 選擇「中部空品區」
        print("選擇: 中部空品區")
        Select(area_el).select_by_visible_text("中部空品區")
        
        # *** 重要：切換區域後，測站選單會重整，這裡強制等待 5 秒 ***
        time.sleep(5)

        for st in stations:
            try:
                print(f"正在處理測站: {st}")
                
                # 重新抓取測站下拉選單（避免頁面重新整理後的失效問題）
                station_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Station")))
                Select(station_el).select_by_visible_text(st)
                time.sleep(1)

                # 點擊查詢
                btn = driver.find_element(By.ID, "cp_content_btn_Query")
                driver.execute_script("arguments[0].click();", btn) # 改用 JS 點擊更穩定
                
                # 等待數據表格刷新（等待時間標籤更新）
                time.sleep(5)

                # 抓取數據
                data = {
                    "station": st,
                    "time": driver.find_element(By.ID, "cp_content_lab_IssueTime").text.replace("發布時間：", "").strip(),
                    "O3": driver.find_element(By.ID, "cp_content_lab_O3").text,
                    "PM25": driver.find_element(By.ID, "cp_content_lab_PM25").text,
                    "PM10": driver.find_element(By.ID, "cp_content_lab_PM10").text,
                    "CO": driver.find_element(By.ID, "cp_content_lab_CO").text,
                    "SO2": driver.find_element(By.ID, "cp_content_lab_SO2").text,
                    "NO2": driver.find_element(By.ID, "cp_content_lab_NO2").text
                }
                results.append(data)
                print(f"-> {st} 抓取成功")
            except Exception as e:
                print(f"-> {st} 發生錯誤: {str(e)}")

        # 寫入 JSON 檔案
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print("任務完成，檔案已產生。")

    except Exception as e:
        print(f"主要程序錯誤: {str(e)}")
        # 即使失敗也回報錯誤，讓 Actions 知道
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
