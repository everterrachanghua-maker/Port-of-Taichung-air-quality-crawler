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
    print("=== 啟動數據校正抓取程序 ===")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # 偽裝成真人瀏覽器
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 40) # 最長等待 40 秒

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"正在打開網頁: {url}")
        driver.get(url)
        time.sleep(10) # 讓初始頁面載入完全

        # 1. 選擇「中部空品區」
        print("1. 嘗試選擇『中部空品區』...")
        area_select_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Area")))
        Select(area_select_el).select_by_visible_text("中部空品區")
        print("   -> 區域已切換，等待測站清單更新 (10秒)...")
        time.sleep(10) 

        for st in stations:
            print(f"2. 處理測站: {st}")
            try:
                # 重新定位測站下拉選單
                station_select_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Station")))
                Select(station_select_el).select_by_visible_text(st)
                time.sleep(3)

                # 點擊查詢按鈕
                search_btn = wait.until(EC.element_to_be_clickable((By.ID, "cp_content_btn_Query")))
                driver.execute_script("arguments[0].click();", search_btn)
                print("   -> 查詢已點擊，等待數據載入 (8秒)...")
                time.sleep(8) 

                # 抓取數據 (直接使用標籤 ID)
                def get_val(element_id):
                    try:
                        return driver.find_element(By.ID, element_id).text.strip()
                    except:
                        return "N/A"

                issue_time = get_val("cp_content_lab_IssueTime").replace("發布時間：", "").strip()
                
                if issue_time == "" or issue_time == "N/A":
                    print(f"   [警告] {st} 抓取到的時間為空，可能網頁尚未更新")
                    continue

                data = {
                    "station": st,
                    "time": issue_time,
                    "O3": get_val("cp_content_lab_O3"),
                    "PM25": get_val("cp_content_lab_PM25"),
                    "PM10": get_val("cp_content_lab_PM10"),
                    "CO": get_val("cp_content_lab_CO"),
                    "SO2": get_val("cp_content_lab_SO2"),
                    "NO2": get_val("cp_content_lab_NO2")
                }
                results.append(data)
                print(f"   [成功] {st} 數據已獲取: {issue_time}")

            except Exception as e:
                print(f"   [錯誤] {st} 處理失敗: {str(e)}")

        # 寫入 JSON
        print(f"3. 準備儲存檔案，總計抓取到 {len(results)} 筆數據")
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
    except Exception as e:
        print(f"!!! 核心程序報錯: {str(e)}")
        # 確保即使報錯也留下一個空的 JSON 讓後續動作不崩潰
        if not results:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump([], f)
        raise e
    finally:
        driver.quit()
        print("=== 爬蟲程序結束 ===")

if __name__ == "__main__":
    scrape_data()

if __name__ == "__main__":
    scrape_data()
