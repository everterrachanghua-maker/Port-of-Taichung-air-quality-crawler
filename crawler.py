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
    print("=== [啟動] 環境監測自動化爬蟲 (極致穩定版) ===")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 60) # 最長等待 60 秒

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 正在打開網頁: {url}")
        driver.get(url)
        time.sleep(10)

        # A. 選擇區域：中部空品區
        print("2. 正在選擇『中部空品區』...")
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_el).select_by_visible_text("中部空品區")
        
        # *** 關鍵偵測：確保測站選單內容已更新 (最多等 40 秒) ***
        print("   等待測站清單同步中...")
        found_list = False
        for i in range(20):
            try:
                st_dropdown_text = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
                if "台電梧棲" in st_dropdown_text:
                    print(f"   [OK] 清單同步成功！(嘗試第 {i+1} 次)")
                    found_list = True
                    break
            except:
                pass
            time.sleep(2)
        
        if not found_list:
            print("   [警告] 測站清單同步超時，嘗試強制抓取...")

        # B. 循環抓取各站數據
        for st in stations:
            print(f"3. 處理測站: {st}")
            try:
                # 重新定位選單 (防止 Stale Element 錯誤)
                st_select_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_select_el).select_by_visible_text(st)
                time.sleep(3)

                # 點擊查詢按鈕 (使用 JS 點擊最穩定)
                btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(10) # 數據載入較慢

                def get_text(node_id):
                    try:
                        val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                        return val if val != "" else "N/A"
                    except: return "N/A"

                issue_time = get_text("lab_IssueTime").replace("發布時間：", "").strip()
                
                if issue_time in ["N/A", "未監測", ""]:
                    print(f"   [跳過] {st} 無法讀取發布時間，可能網頁載入中")
                    continue

                item = {
                    "station": st,
                    "time": issue_time,
                    "O3": get_text("lab_O3"),
                    "PM25": get_text("lab_PM25"),
                    "PM10": get_text("lab_PM10"),
                    "CO": get_text("lab_CO"),
                    "SO2": get_text("lab_SO2"),
                    "NO2": get_text("lab_NO2")
                }
                results.append(item)
                print(f"   [成功] {st} 數據已獲取 ({issue_time})")

            except Exception as e:
                print(f"   [失敗] {st} 發生異常: {str(e)}")

        # C. 存檔
        print(f"4. 抓取結束，成功獲取 {len(results)} 筆資料，準備存檔。")
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"\n致命錯誤發生:\n{traceback.format_exc()}")
        # 即使報錯也要留下一份正確格式的資料，防止網頁出現 undefined
        if not results:
             with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump([{"station": "數據重新整理中", "time": "請稍後", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-"}], f)
    finally:
        driver.quit()
        print("=== 爬蟲程序結束 ===")

if __name__ == "__main__":
    scrape_data()
