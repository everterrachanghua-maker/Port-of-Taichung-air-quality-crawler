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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_data():
    print("=== [啟動] 雙重偵測穩定版爬蟲 (文字選取修正版) ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入港區網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(15)

        print("   正在選擇區域: 中部空品區...")
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        # 修正點：改用 select_by_visible_text，這比 select_by_value(4) 穩定得多
        Select(area_el).select_by_visible_text("中部空品區")
        
        print("   正在同步港區測站清單...")
        success_sync = False
        for _ in range(20):
            try:
                st_list_text = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
                if "台電梧棲" in st_list_text:
                    success_sync = True
                    print("   [OK] 港區清單同步完成")
                    break
            except: pass
            time.sleep(2)

        if success_sync:
            tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
            for st in tcc_stations:
                try:
                    print(f"   -> 正在抓取: {st}")
                    st_sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                    Select(st_sel).select_by_visible_text(st)
                    time.sleep(3)
                    
                    query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                    driver.execute_script("arguments[0].click();", query_btn)
                    time.sleep(10)

                    def g_v(nid):
                        try:
                            val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                            return val if val else "數據接收中"
                        except: return "N/A"

                    final_results["tcc_data"].append({
                        "station": st,
                        "time": g_v("lab_IssueTime").replace("發布時間：", "").strip(),
                        "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                        "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                    })
                except: print(f"      [!] {st} 抓取失敗")

        # --- 任務 2: 一般監測站 (沙鹿) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(15)

        print("   正在選擇區域: 中部空品區...")
        area_el2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        # 修正點：同樣改用文字選取
        Select(area_el2).select_by_visible_text("中部空品區")
        
        print("   正在同步一般測站清單...")
        success_sync_c = False
        for _ in range(20):
            try:
                st_list_c = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
                if "沙鹿" in st_list_c:
                    success_sync_c = True
                    print("   [OK] 沙鹿清單同步完成")
                    break
            except: pass
            time.sleep(2)

        if success_sync_c:
            try:
                st_el2 = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']")
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
                print("   [OK] 沙鹿抓取完成")
            except: print("   [!] 沙鹿抓取失敗")

    except Exception as e:
        print(f"程序致命錯誤: {traceback.format_exc()}")
    
    finally:
        if len(final_results["tcc_data"]) > 0 or len(final_results["central_data"]) > 0:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，JSON 已成功更新 ===")
        else:
            print("=== [警告] 完全沒抓到數據，不更新 JSON 以保留舊資料 ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
