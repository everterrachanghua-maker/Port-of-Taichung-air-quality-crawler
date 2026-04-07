import time
import json
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
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
    print("=== [開始] 極致穩定版數據抓取 (增加強制等待) ===")
    driver = get_driver()
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 前往港區網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(20) # 強制等 20 秒讓網頁完全跑完

        # 選擇中部空品區
        print("   選擇: 中部空品區")
        try:
            area_el = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Area']")
            Select(area_el).select_by_value("4") # '4' 是中部地區代碼
            print("   等待清單刷新 (20秒)...")
            time.sleep(20) # 這是關鍵：給 ASP.NET 充足時間重整
        except:
            print("   [錯誤] 找不到區域選單，嘗試重新整理網頁")
            driver.refresh()
            time.sleep(15)

        tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        for st in tcc_stations:
            try:
                print(f"   -> 抓取測站: {st}")
                st_sel_el = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']")
                Select(st_sel_el).select_by_visible_text(st)
                time.sleep(5)
                
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                print("      等待數據載入 (12秒)...")
                time.sleep(12) 

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
                print(f"      [OK] {st} 抓取完成")
            except Exception as e:
                print(f"      [FAIL] {st} 出錯: {e}")

        # --- 任務 2: 一般監測站 (沙鹿) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(15)

        try:
            area_el2 = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Area']")
            Select(area_el2).select_by_value("4")
            time.sleep(15)
            
            st_el2 = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']")
            Select(st_el2).select_by_visible_text("沙鹿")
            time.sleep(5)
            
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            print("      等待沙鹿站數據 (15秒)...")
            time.sleep(15)

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
        except Exception as e:
            print(f"   [FAIL] 沙鹿站失敗: {e}")

    except Exception as e:
        print(f"致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 如果這次有抓到任何東西，才存檔，否則不更新(保留上次舊資料)
        if len(final_results["tcc_data"]) > 0 or len(final_results["central_data"]) > 0:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束，JSON 已成功更新 ===")
        else:
            print("=== [警告] 完全沒抓到數據，放棄更新 JSON ===")
            # 建立一個測試用的 JSON，確保前端至少有東西跑 (測試用可刪除)
            # with open("air_quality.json", "w", encoding="utf-8") as f:
            #     json.dump(final_results, f, ensure_ascii=False, indent=4)
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
