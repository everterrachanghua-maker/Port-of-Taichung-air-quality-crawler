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
    print("=== 啟動終極穩定版爬蟲 ===")
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
        print(f"1. 打開網頁: {url}")
        driver.get(url)
        time.sleep(10)

        # 2. 選擇「中部空品區」
        print("2. 嘗試定位區域選單...")
        area_select_el = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@id, 'ddl_Area')]")))
        Select(area_select_el).select_by_visible_text("中部空品區")
        print("   -> 已選擇中部空品區，等待網頁刷新...")
        time.sleep(8) 

        for st in stations:
            print(f"3. 處理測站: {st}")
            try:
                # 每次循環重新找一次選單，避免失效
                station_select_el = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@id, 'ddl_Station')]")))
                Select(station_select_el).select_by_visible_text(st)
                time.sleep(2)

                # 點擊查詢
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@id, 'btn_Query')]")))
                driver.execute_script("arguments[0].click();", btn)
                print(f"   -> 點擊查詢，等待數據...")
                time.sleep(8)

                # 抓取數值函數（增加容錯）
                def get_text(node_id):
                    try:
                        return driver.find_element(By.XPATH, f"//*[contains(@id, '{node_id}')]").text
                    except:
                        return "N/A"

                item = {
                    "station": st,
                    "time": get_text("lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": get_text("lab_O3"),
                    "PM25": get_text("lab_PM25"),
                    "PM10": get_text("lab_PM10"),
                    "CO": get_text("lab_CO"),
                    "SO2": get_text("lab_SO2"),
                    "NO2": get_text("lab_NO2")
                }
                results.append(item)
                print(f"   [成功] {st} 數據抓取完畢")
            except Exception as e:
                print(f"   [失敗] {st} 發生錯誤: {e}")

        # 儲存
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"=== 任務結束，共抓取 {len(results)} 筆資料 ===")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # 即使報錯也產生一個空的 JSON，避免 Actions 第二步崩潰
        if not os.path.exists("air_quality.json"):
            with open("air_quality.json", "w") as f: f.write("[]")
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
