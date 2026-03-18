import time
import json
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data():
    print("--- [Step 1] 初始化瀏覽器 ---")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # 增加穩定性參數
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 45) # 增加等待上限至 45 秒

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"--- [Step 2] 開啟網頁: {url} ---")
        driver.get(url)
        time.sleep(15) # 初始載入給足時間

        # 1. 選擇「中部空品區」
        print("--- [Step 3] 選擇區域: 中部空品區 ---")
        # 使用 id$= 的 CSS 選擇器，能自動匹配結尾為 ddl_Area 的元素，防止 ASP.NET 前綴變動
        area_select_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_select_el).select_by_visible_text("中部空品區")
        
        # 關鍵：監測測站選單是否真的更新了
        print("等待測站清單同步中...")
        for i in range(15):
            station_list_html = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").get_attribute("innerHTML")
            if "台電梧棲" in station_list_html:
                print(f"清單同步成功！(嘗試第 {i+1} 次)")
                break
            time.sleep(2)
        else:
            print("警告：測站清單似乎未及時更新，嘗試強制執行...")

        # 2. 循環抓取各站數據
        for st in stations:
            print(f"\n--- [Step 4] 抓取測站: {st} ---")
            try:
                # 重新定位選單，避免頁面局部刷新（Postback）造成的失效
                st_dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_dropdown).select_by_visible_text(st)
                time.sleep(3)

                # 點擊查詢按鈕 (使用 JavaScript 點擊可避免被其他元素遮擋)
                btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", btn)
                print("點擊查詢按鈕成功，等待數據渲染...")
                time.sleep(10) # 數據載入較慢，等 10 秒

                # 抓取數據函數 (封裝定位邏輯)
                def get_v(node_id):
                    try:
                        # 使用 id$= 匹配，能精準抓到數值標籤
                        val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                        return val if val != "" else "未監測"
                    except: 
                        return "N/A"

                issue_time = get_v("lab_IssueTime").replace("發布時間：", "").strip()
                
                # 如果連發布時間都抓不到，這筆資料就是失敗的
                if issue_time == "N/A" or issue_time == "":
                    print(f"數據解析失敗: {st} 無法讀取發布時間，跳過此站。")
                    continue

                item = {
                    "station": st,
                    "time": issue_time,
                    "O3": get_v("lab_O3"),
                    "PM25": get_v("lab_PM25"),
                    "PM10": get_v("lab_PM10"),
                    "CO": get_v("lab_CO"),
                    "SO2": get_v("lab_SO2"),
                    "NO2": get_v("lab_NO2")
                }
                results.append(item)
                print(f"抓取成功: {st} ({issue_time})")

            except Exception as e:
                print(f"{st} 過程出錯: {str(e)}")

        # 3. 儲存結果
        if len(results) > 0:
            print(f"\n--- [Step 5] 儲存 JSON 檔案 (共 {len(results)} 筆) ---")
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
        else:
            print("\n警告：完全沒有抓取到任何有效數據，請檢查網頁是否變更。")
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump([], f)

    except Exception as e:
        print("\n!!! 致命錯誤發生 !!!")
        print(traceback.format_exc())
        # 如果失敗了，存一個標示錯誤的 JSON 檔，讓前端能顯示錯誤狀態
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump([{"station": "系統更新中", "time": "請稍後再試"}], f)
        raise e
    finally:
        driver.quit()
        print("\n=== 爬蟲程序結束 ===")

if __name__ == "__main__":
    scrape_data()
