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

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_data():
    print("=== [啟動] 多層級篩選穩定版爬蟲 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 (三層篩選) ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入港區網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(10)

        # A. 選擇所屬單位 (預設通常是大型事業，但保險起見我們再選一次)
        print("   -> 步驟 1: 選擇『大型事業』")
        org_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Org']")))
        Select(org_el).select_by_visible_text("大型事業")
        time.sleep(3)

        # B. 選擇中部空品區
        print("   -> 步驟 2: 選擇『中部空品區』")
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_el).select_by_visible_text("中部空品區")
        
        # 關鍵：直到測站清單出現「台電梧棲」
        print("   -> 步驟 3: 等待測站清單同步...")
        for _ in range(20):
            try:
                st_list = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
                if "台電梧棲" in st_list:
                    print("      [OK] 港區清單已更新")
                    break
            except: pass
            time.sleep(2)

        tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        for st in tcc_stations:
            try:
                print(f"      正在抓取: {st}")
                st_sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_sel).select_by_visible_text(st)
                time.sleep(3)
                
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                time.sleep(10)

                def g_v(nid):
                    try: return driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                    except: return "N/A"

                final_results["tcc_data"].append({
                    "station": st,
                    "time": g_v("lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                    "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                })
            except: print(f"         [!] {st} 失敗")

        # --- 任務 2: 一般監測站 (沙鹿) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(8)

        print("   -> 步驟 1: 選擇『中部空品區』")
        area_el2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_el2).select_by_visible_text("中部空品區")
        
        print("   -> 步驟 2: 等待沙鹿站載入...")
        for _ in range(15):
            try:
                if "沙鹿" in driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text:
                    print("      [OK] 沙鹿清單已就緒")
                    break
            except: pass
            time.sleep(2)
        
        try:
            st_el2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
            Select(st_el2).select_by_visible_text("沙鹿")
            time.sleep(3)
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            time.sleep(12)

            def g_c(nid):
                try: return driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                except: return "N/A"

            final_results["central_data"].append({
                "station": "沙鹿", "time": g_c("lab_IssueTime").replace("發布時間：", "").strip(),
                "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
                "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
                "NMHC": g_c("lab_NMHC"), "WindSpeed": g_c("lab_WindSpeed"), 
                "WindDirect": g_c("lab_WindDirect"), "RH": g_c("lab_RH")
            })
            print("      [OK] 沙鹿抓取完成")
        except: print("      [!] 沙鹿抓取失敗")

    except Exception as e:
        print(f"程序致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 只要有抓到任何測站的資料，就更新 JSON，否則不更新(保留舊資料)
        if len(final_results["tcc_data"]) > 0 or len(final_results["central_data"]) > 0:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，JSON 已更新 ===")
        else:
            print("=== [警告] 本次完全沒抓到數據，放棄更新 JSON 以保留最後一次成功的資料 ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
