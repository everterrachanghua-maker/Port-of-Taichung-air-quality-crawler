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
    print("=== [啟動] 嚴格篩選流程爬蟲程序 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    final_results = {"tcc_data": [], "central_data": []}
    
    # 港務/台電測站清單
    tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]

    try:
        # --- 流程 A: 港務與台電測站頁面 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(10)

        for st in tcc_stations:
            print(f"\n[開始處理測站: {st}]")
            try:
                # 步驟 1: 所屬單位 選擇 『大型事業』
                print("   步驟 1: 選擇『大型事業』")
                unit_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Org']")))
                Select(unit_el).select_by_visible_text("大型事業")
                time.sleep(3) # 等待 Postback

                # 步驟 2: 空品區 選擇 『中部空品區』
                print("   步驟 2: 選擇『中部空品區』")
                area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
                Select(area_el).select_by_visible_text("中部空品區")
                time.sleep(8) # 關鍵：中部測站清單載入較慢

                # 步驟 3: 測站名稱 選擇 對應測站
                print(f"   步驟 3: 選擇測站名稱『{st}』")
                st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_el).select_by_visible_text(st)
                time.sleep(3)

                # 步驟 4: 按下「查詢」按鈕
                print("   步驟 4: 點擊『查詢』按鈕")
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 步驟 5: 等待並抓取數據
                print("   步驟 5: 等待數據渲染並讀取...")
                time.sleep(10) # 點擊查詢後給 10 秒傳輸數據

                def g_v(nid):
                    try:
                        val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                        return val if val else "數據接收中"
                    except: return "N/A"

                res_time = g_v("lab_IssueTime").replace("發布時間：", "").strip()
                
                # 只有抓到時間才存檔
                if "202" in res_time:
                    final_results["tcc_data"].append({
                        "station": st, "time": res_time,
                        "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                        "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                    })
                    print(f"      => {st} 抓取成功: {res_time}")
                else:
                    print(f"      => {st} 數據尚未跳出")

            except Exception as e:
                print(f"      => {st} 執行失敗: {str(e)[:100]}")

        # --- 流程 B: 沙鹿一般測站頁面 ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(10)

        try:
            print("   -> 選擇中部 -> 沙鹿 -> 查詢")
            a_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
            Select(a_el).select_by_visible_text("中部空品區")
            time.sleep(5)
            s_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
            Select(s_el).select_by_visible_text("沙鹿")
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
            print("   => 沙鹿抓取成功")
        except: print("   => 沙鹿抓取失敗")

    except Exception as e:
        print(f"致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 如果有任何數據抓到，才更新 JSON
        if final_results["tcc_data"] or final_results["central_data"]:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
            print("=== 任務結束：JSON 數據已更新 ===")
        
        driver.quit()

if __name__ == "__main__":
    scrape_data()
