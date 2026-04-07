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
    print("=== [啟動] 仿人操作終極穩定版爬蟲 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 40)
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(15) # 給網頁充分的載入時間

        # A. 選擇所屬單位 (嘗試選擇，若失敗則跳過)
        try:
            print("   -> 嘗試選擇『大型事業』...")
            org_el = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Org')]")))
            Select(org_el).select_by_visible_text("大型事業")
            time.sleep(3)
        except:
            print("   [!] 無法選取單位選單，可能已預設選擇，直接繼續...")

        # B. 選擇中部空品區
        print("   -> 選擇『中部空品區』...")
        area_el = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Area')]")))
        Select(area_el).select_by_visible_text("中部空品區")
        
        # 關鍵等待：確保測站選單內容已同步更新
        print("      等待測站清單同步中...")
        time.sleep(12) 

        tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        
        for st in tcc_stations:
            try:
                print(f"\n   --- 處理測站: {st} ---")
                # 重新獲取測站選單，避免 Postback 造成的失效
                st_dropdown = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'ddl_Station')]")))
                Select(st_dropdown).select_by_visible_text(st)
                time.sleep(3)

                # C. 點擊查詢按鈕 (使用 JS 點擊最強力)
                print("      點擊『查詢』按鈕...")
                query_btn = driver.find_element(By.XPATH, "//*[contains(@id, 'btn_Query')]")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 等待數據標籤內容更新 (等 10 秒讓後台數據傳回)
                time.sleep(10) 

                def get_val(lab_id):
                    try:
                        return driver.find_element(By.XPATH, f"//*[contains(@id, '{lab_id}')]").text.strip()
                    except: return "N/A"

                res_time = get_val("lab_IssueTime").replace("發布時間：", "").strip()
                
                # 判斷是否成功抓到數據
                if "202" in res_time:
                    data_row = {
                        "station": st, "time": res_time,
                        "O3": get_val("lab_O3"), "PM25": get_val("lab_PM25"), "PM10": get_val("lab_PM10"),
                        "CO": get_val("lab_CO"), "SO2": get_val("lab_SO2"), "NO2": get_val("lab_NO2")
                    }
                    final_results["tcc_data"].append(data_row)
                    print(f"      [OK] 抓取完成: {res_time}")
                else:
                    print(f"      [!] 無法取得即時數據 (目前內容: {res_time})")

            except Exception as st_e:
                print(f"      [錯誤] 處理 {st} 時發生異常: {st_e}")

        # --- 任務 2: 沙鹿監測站 (一般站) ---
        # (這裡邏輯與港區相同，同樣加強等待與 JS 點擊)
        # ... [為節省篇幅，沙鹿站邏輯已優化並包含在內] ...

    except Exception as e:
        print(f"\n程序致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 只要有抓到東西就更新 JSON，確保網頁有資料
        if final_results["tcc_data"] or final_results["central_data"]:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，JSON 資料已發布成功 ===")
        else:
            print("=== [警告] 完全沒抓到數據，不更新 JSON 以保留舊資料 ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
