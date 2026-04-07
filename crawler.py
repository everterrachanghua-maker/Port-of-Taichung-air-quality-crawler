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
    print("=== [啟動] 精準點擊與數據偵測爬蟲 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 40)
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入港區網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(10)

        # 確實選擇「大型事業」與「中部空品區」
        try:
            org_sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Org']")))
            Select(org_sel).select_by_visible_text("大型事業")
            time.sleep(3)
            area_sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
            Select(area_sel).select_by_visible_text("中部空品區")
            time.sleep(10) # 等待測站清單同步
        except:
            print("   [!] 預設篩選失敗，嘗試繼續...")

        tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        
        for st in tcc_stations:
            try:
                print(f"   -> 正在處理: {st}")
                # 重新抓取選單，確保選單沒有失效
                st_dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_dropdown).select_by_visible_text(st)
                time.sleep(2)

                # *** 關鍵動作：點擊查詢按鈕 ***
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # *** 關鍵等待：等候數據 Label 刷新 ***
                # 我們等候「發布時間」這個欄位出現當前年份的數字
                time.sleep(8) 

                def get_val(lab_id):
                    try:
                        # 這是數據顯示在網頁上的真正位置 (Label ID)
                        return driver.find_element(By.CSS_SELECTOR, f"span[id$='{lab_id}']").text.strip()
                    except: return "N/A"

                res_time = get_val("lab_IssueTime").replace("發布時間：", "").strip()
                
                if res_time == "" or res_time == "N/A":
                    print(f"      [!] {st} 查詢後無數據響應")
                    continue

                final_results["tcc_data"].append({
                    "station": st,
                    "time": res_time,
                    "O3": get_val("lab_O3"), "PM25": get_val("lab_PM25"), "PM10": get_val("lab_PM10"),
                    "CO": get_val("lab_CO"), "SO2": get_val("lab_SO2"), "NO2": get_val("lab_NO2")
                })
                print(f"      [OK] {st} 數據抓取完成: {res_time}")

            except Exception as e:
                print(f"      [錯誤] {st} 失敗: {e}")

        # --- 任務 2: 沙鹿監測站 ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(8)

        area_sel2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_sel2).select_by_visible_text("中部空品區")
        time.sleep(5)
        st_sel2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
        Select(st_sel2).select_by_visible_text("沙鹿")
        
        # 點擊查詢
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
        time.sleep(10)

        def get_c(lab_id):
            try: return driver.find_element(By.CSS_SELECTOR, f"span[id$='{lab_id}']").text.strip()
            except: return "N/A"

        final_results["central_data"].append({
            "station": "沙鹿", "time": get_c("lab_IssueTime").replace("發布時間：", "").strip(),
            "O3": get_c("lab_O3"), "PM25": get_c("lab_PM25"), "PM10": get_c("lab_PM10"),
            "CO": get_c("lab_CO"), "SO2": get_c("lab_SO2"), "NO2": get_c("lab_NO2"),
            "NMHC": get_c("lab_NMHC"), "WindSpeed": get_c("lab_WindSpeed"), 
            "WindDirect": get_c("lab_WindDirect"), "RH": get_c("lab_RH")
        })
        print("   [OK] 沙鹿數據抓取成功")

    except Exception as e:
        print(f"致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 如果這次有抓到任何東西，就更新
        if len(final_results["tcc_data"]) > 0 or len(final_results["central_data"]) > 0:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，資料已發布 ===")
        else:
            print("=== [警告] 完全沒抓到數據，不更新 JSON 以保留舊資料 ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
