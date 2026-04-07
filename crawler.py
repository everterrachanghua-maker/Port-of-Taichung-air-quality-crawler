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
    print("=== [啟動] 依照嚴格篩選邏輯抓取程序 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入港區網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(10)

        # A. 選擇所屬單位：大型事業
        print("   -> [Step 1] 選擇所屬單位: 大型事業")
        org_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Org']")))
        Select(org_el).select_by_visible_text("大型事業")
        time.sleep(5) # 等待網頁 Postback

        # B. 選擇空品區：中部空品區
        print("   -> [Step 2] 選擇空品區: 中部空品區")
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_el).select_by_visible_text("中部空品區")
        time.sleep(10) # 關鍵：中部測站較多，給網頁多點時間同步清單

        tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        
        for st in tcc_stations:
            try:
                print(f"   -> [Step 3] 選擇測站: {st}")
                # 重新獲取下拉選單避免失效
                st_dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_dropdown).select_by_visible_text(st)
                time.sleep(3)

                # C. 點擊「查詢」按鈕
                print(f"   -> [Step 4] 點擊查詢按鈕並等待數據...")
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 智慧等待：直到數據區塊的時間標籤出現實際日期
                time.sleep(10) 

                def g_v(node_id):
                    try:
                        return driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                    except: return "N/A"

                issue_time = g_v("lab_IssueTime").replace("發布時間：", "").strip()
                
                # 只有抓到時間(代表查詢成功)才存入結果
                if "202" in issue_time:
                    final_results["tcc_data"].append({
                        "station": st, "time": issue_time,
                        "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                        "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                    })
                    print(f"      [OK] {st} 抓取成功 ({issue_time})")
                else:
                    print(f"      [!] {st} 數據尚未跳出，請檢查網頁狀態")

            except Exception as e:
                print(f"      [錯誤] {st} 過程失敗: {e}")

        # --- 任務 2: 沙鹿監測站 (一般測站) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(10)

        try:
            print("   -> 選擇中部空品區與沙鹿站")
            area_el2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
            Select(area_el2).select_by_visible_text("中部空品區")
            time.sleep(5)
            st_sel2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
            Select(st_sel2).select_by_visible_text("沙鹿")
            
            print("   -> 點擊沙鹿查詢...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            time.sleep(12)

            def g_c(nid):
                try: return driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                except: return "N/A"

            s_time = g_c("lab_IssueTime").replace("發布時間：", "").strip()
            if "202" in s_time:
                final_results["central_data"].append({
                    "station": "沙鹿", "time": s_time,
                    "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
                    "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
                    "NMHC": g_c("lab_NMHC"), "WindSpeed": g_c("lab_WindSpeed"), 
                    "WindDirect": g_c("lab_WindDirect"), "RH": g_c("lab_RH")
                })
                print("      [OK] 沙鹿數據抓取成功")
        except: print("      [!] 沙鹿抓取失敗")

    except Exception as e:
        print(f"致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 只要有抓到東西就存檔
        if len(final_results["tcc_data"]) > 0 or len(final_results["central_data"]) > 0:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，資料已發布 ===")
        else:
            print("=== [警告] 完全沒抓到數據，不更新 JSON ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
