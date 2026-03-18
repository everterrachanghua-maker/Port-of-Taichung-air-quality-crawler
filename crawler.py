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
    print("--- [Step 1] 初始化環境 ---")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    # 設定最長等待時間為 60 秒
    wait = WebDriverWait(driver, 60) 

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"--- [Step 2] 前往網站: {url} ---")
        driver.get(url)
        
        # 等待區域選單出現
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        time.sleep(5)

        # 1. 選擇「中部空品區」
        print("--- [Step 3] 切換區域: 中部空品區 ---")
        Select(area_el).select_by_visible_text("中部空品區")
        
        print("等待測站清單同步中 (使用動態偵測)...")
        # 這裡改用循環檢查，直到測站選單出現「台電梧棲」為止
        found_list = False
        for i in range(20): # 最多等 40 秒
            try:
                st_dropdown = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']")
                if "台電梧棲" in st_dropdown.text:
                    print(f"清單同步成功！(嘗試第 {i+1} 次)")
                    found_list = True
                    break
            except:
                pass
            time.sleep(2)
        
        if not found_list:
            print("警告：測站清單同步超時，嘗試直接抓取...")

        # 2. 循環抓取各站數據
        print("--- [Step 4] 開始抓取測站數據 ---")
        for st in stations:
            try:
                print(f"正在處理: {st}")
                # 每次都要重新抓取下拉選單，防止網頁局部更新導致舊元素失效 (Stale Element)
                st_dropdown_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_dropdown_el).select_by_visible_text(st)
                time.sleep(3)

                # 點擊查詢按鈕 (用 JS 點擊最保險)
                btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", btn)
                
                print(f"   已點擊查詢，等待數據渲染...")
                time.sleep(10) # 數據載入給予 10 秒緩衝

                def get_v(node_id):
                    try:
                        # 抓取包含該 ID 結尾的 span 標籤
                        val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                        return val if val != "" else "未監測"
                    except: return "N/A"

                issue_time = get_v("lab_IssueTime").replace("發布時間：", "").strip()
                
                if issue_time in ["N/A", "未監測", ""]:
                    print(f"   [!] {st} 沒抓到時間，跳過。")
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
                print(f"   [OK] {st} 抓取成功 ({issue_time})")

            except Exception as e:
                print(f"   [!] {st} 抓取過程發生錯誤: {str(e)}")

        # 3. 儲存結果
        print(f"\n--- [Step 5] 存檔處理 (本次共抓取 {len(results)} 筆) ---")
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print("\n!!! 致命錯誤診斷 !!!")
        print(traceback.format_exc())
        # 即使報錯也要留下一份檔案，防止 Actions 報錯
        if not results:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump([{"station": "數據載入中", "time": "請稍後再試"}], f)
    finally:
        driver.quit()
        print("\n=== 爬蟲程序結束 ===")
