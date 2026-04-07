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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_data():
    print("=== [開始] 依照篩選 -> 查詢邏輯執行程序 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    final_results = {"tcc_data": [], "central_data": []}
    tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]

    try:
        # --- 任務 1: 港務與台電測站 (三項篩選) ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 前往網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(15)

        # Step 1: 選擇大型事業
        print("   -> 篩選 1: 選擇『大型事業』")
        try:
            org_el = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Org')]")))
            Select(org_el).select_by_visible_text("大型事業")
            time.sleep(3)
        except: print("   [!] 單位選單跳過")

        # Step 2: 選擇中部空品區
        print("   -> 篩選 2: 選擇『中部空品區』")
        area_el = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Area')]")))
        Select(area_el).select_by_visible_text("中部空品區")
        
        # 關鍵等待：確保測站清單已經更新成中部地區
        print("      等待測站清單同步中...")
        time.sleep(15)

        for st in tcc_stations:
            try:
                print(f"\n   -> 篩選 3: 選擇測站『{st}』")
                # 重新定位選單，避免網頁重整造成的遺失
                st_dropdown = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Station')]")))
                Select(st_dropdown).select_by_visible_text(st)
                time.sleep(3)

                # Step 4: 點擊查詢按鈕 (關鍵！)
                print(f"      [動作] 點擊『查詢』並等待數據渲染...")
                query_btn = driver.find_element(By.XPATH, "//*[contains(@id, 'btn_Query')]")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 暴力偵測：直到發布時間出現數字 (如 2026) 才抓取
                success_load = False
                for _ in range(10):
                    time.sleep(2)
                    time_text = driver.find_element(By.XPATH, "//*[contains(@id, 'lab_IssueTime')]").text
                    if "202" in time_text:
                        success_load = True
                        break
                
                if not success_load:
                    print(f"      [!] {st} 數據渲染超時，跳過")
                    continue

                def g_v(lab_id):
                    try: return driver.find_element(By.XPATH, f"//*[contains(@id, '{lab_id}')]").text.strip()
                    except: return "N/A"

                res_time = g_v("lab_IssueTime").replace("發布時間：", "").strip()
                final_results["tcc_data"].append({
                    "station": st, "time": res_time,
                    "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                    "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                })
                print(f"      [成功] {st} 資料獲取成功: {res_time}")

            except Exception as e:
                print(f"      [錯誤] {st} 失敗: {e}")

        # --- 任務 2: 一般監測站 (沙鹿) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(10)

        try:
            print("   -> 篩選: 中部 -> 沙鹿 -> 查詢")
            area_el2 = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Area')]")))
            Select(area_el2).select_by_visible_text("中部空品區")
            time.sleep(5)
            st_sel2 = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Station')]")))
            Select(st_sel2).select_by_visible_text("沙鹿")
            time.sleep(2)
            
            query_btn2 = driver.find_element(By.XPATH, "//*[contains(@id, 'btn_Query')]")
            driver.execute_script("arguments[0].click();", query_btn2)
            time.sleep(10)

            def g_c(nid):
                try: return driver.find_element(By.XPATH, f"//*[contains(@id, '{nid}')]").text.strip()
                except: return "N/A"

            final_results["central_data"].append({
                "station": "沙鹿", "time": g_c("lab_IssueTime").replace("發布時間：", "").strip(),
                "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
                "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
                "NMHC": g_c("lab_NMHC"), "WindSpeed": g_c("lab_WindSpeed"), 
                "WindDirect": g_c("lab_WindDirect"), "RH": g_c("lab_RH")
            })
            print("   [成功] 沙鹿站資料獲取成功")
        except: print("   [!] 沙鹿站失敗")

    except Exception as e:
        print(f"\n致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 只要有一站抓到就存檔
        if final_results["tcc_data"] or final_results["central_data"]:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，JSON 已更新完畢 ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
