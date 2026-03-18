import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data():
    print("=== [啟動] 穩定版爬蟲 (優化 ASP.NET 刷新機制) ===")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # 針對雲端環境的額外優化
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 正在載入網頁: {url}")
        driver.get(url)
        time.sleep(12)

        # A. 選擇區域：中部空品區 (使用 JS 觸發 __doPostBack 防止崩潰)
        print("2. 正在切換至『中部空品區』...")
        driver.execute_script("document.getElementById('cp_content_ddl_Area').value = '4';") # '4' 通常是中部的代碼
        driver.execute_script("__doPostBack('ctl00$cp_content$ddl_Area','')")
        
        print("   等待清單刷新 (12秒)...")
        time.sleep(12)

        for st in stations:
            print(f"3. 正在處理測站: {st}")
            try:
                # B. 選擇測站 (直接操作 DOM)
                station_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Station")))
                found = False
                for option in station_el.find_elements(By.TAG_NAME, "option"):
                    if st in option.text:
                        option.click()
                        found = True
                        break
                
                if not found:
                    print(f"   [錯誤] 找不到測站: {st}")
                    continue

                time.sleep(2)

                # C. 點擊查詢 (使用 JS 模擬點擊)
                print(f"   執行查詢...")
                query_btn = driver.find_element(By.ID, "cp_content_btn_Query")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 等待數據回傳
                time.sleep(10)

                # D. 抓取數據
                def safe_get(eid):
                    try:
                        t = driver.find_element(By.ID, eid).text.strip()
                        return t if t else "未監測"
                    except: return "N/A"

                issue_time = safe_get("cp_content_lab_IssueTime").replace("發布時間：", "").strip()
                
                if "N/A" in issue_time or not issue_time:
                    print(f"   [警告] {st} 沒抓到時間，可能數據載入中")
                    continue

                data = {
                    "station": st,
                    "time": issue_time,
                    "O3": safe_get("cp_content_lab_O3"),
                    "PM25": safe_get("cp_content_lab_PM25"),
                    "PM10": safe_get("cp_content_lab_PM10"),
                    "CO": safe_get("cp_content_lab_CO"),
                    "SO2": safe_get("cp_content_lab_SO2"),
                    "NO2": safe_get("cp_content_lab_NO2")
                }
                results.append(data)
                print(f"   [成功] 數據已存入: {issue_time}")

            except Exception as e:
                print(f"   [跳過] {st} 發生異常: {str(e)}")

        # 4. 存檔 (JSON)
        print(f"4. 任務總結: 成功抓取 {len(results)} 筆數據")
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"\n致命錯誤詳情:\n{str(e)}")
        # 即使報錯也要保證有一個空的 JSON 讓 Git Push 不報錯
        if not results:
            with open("air_quality.json", "w", encoding="utf-8") as f: json.dump([], f)
        raise e
    finally:
        driver.quit()
        print("=== 爬蟲程序結束 ===")

if __name__ == "__main__":
    scrape_data()
