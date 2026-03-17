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
    print("--- 啟動爬蟲程序 ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # 模擬真人瀏覽器標頭
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 40) # 延長等待時間到 40 秒

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 正在打開網頁: {url}")
        driver.get(url)

        # 等待網頁初始載入
        time.sleep(10)

        # 2. 選擇「中部空品區」
        print("2. 嘗試定位區域下拉選單...")
        area_select_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        print("找到選單，選擇: 中部空品區")
        Select(area_select_el).select_by_visible_text("中部空品區")
        
        # 關鍵：選擇區域後網頁會 Postback 重整，必須等待
        print("等待區域切換重整 (10秒)...")
        time.sleep(10)

        for st in stations:
            print(f"3. 正在處理測站: {st}")
            try:
                # 重新獲取測站選單（防止 StaleElementReferenceException）
                station_select_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(station_select_el).select_by_visible_text(st)
                time.sleep(2)

                # 點擊查詢按鈕
                print(f"   點擊查詢: {st}")
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 等待數據刷新
                time.sleep(8)

                # 抓取數值 (使用含括選擇器更保險)
                data = {
                    "station": st,
                    "time": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_IssueTime']").text.replace("發布時間：", "").strip(),
                    "O3": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_O3']").text,
                    "PM25": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_PM25']").text,
                    "PM10": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_PM10']").text,
                    "CO": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_CO']").text,
                    "SO2": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_SO2']").text,
                    "NO2": driver.find_element(By.CSS_SELECTOR, "span[id$='lab_NO2']").text
                }
                results.append(data)
                print(f"   [成功] {st} 數據已獲取")

            except Exception as e:
                print(f"   [失敗] {st} 發生錯誤: {str(e)}")
                continue # 繼續下一個測站

        # 4. 儲存結果
        if results:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print("--- 任務完成：air_quality.json 已產生 ---")
        else:
            print("--- 警告：未抓取到任何數據 ---")

    except Exception as e:
        print(f"!!! 程式發生核心錯誤: {str(e)}")
        raise e # 拋出錯誤讓 GitHub Action 顯示紅叉

    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
