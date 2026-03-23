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
    print("=== [啟動] 雙網站跨站數據抓取 (結構化穩定版) ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    # 定義測站
    tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
    # 初始化結果字典，對應新版 HTML 結構
    results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 抓取港區/台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 前往港區監測網: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(10)

        # 選擇中部空品區
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_el).select_by_visible_text("中部空品區")
        
        # 穩定性偵測：等待測站清單同步
        print("   等待港區測站清單同步...")
        found_list = False
        for i in range(20):
            st_text = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
            if "台電梧棲" in st_text:
                print(f"   [OK] 港區清單同步成功 (嘗試第 {i+1} 次)")
                found_list = True
                break
            time.sleep(2)

        for st in tcc_stations:
            print(f"   處理港區測站: {st}")
            try:
                st_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                Select(st_select).select_by_visible_text(st)
                time.sleep(3)
                driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
                time.sleep(8)

                def g_v(node_id):
                    try: 
                        val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                        return val if val != "" else "N/A"
                    except: return "N/A"

                results["tcc_data"].append({
                    "station": st,
                    "time": g_v("lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                    "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                })
            except Exception as e: 
                print(f"   [跳過] {st} 抓取失敗: {e}")

        # --- 任務 2: 抓取一般監測站 (沙鹿) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"2. 前往一般監測網抓取沙鹿站: {url_central}")
        driver.get(url_central)
        time.sleep(10)

        # 選擇中部空品區 -> 沙鹿
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        Select(area_el).select_by_visible_text("中部空品區")
        time.sleep(5)
        st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
        Select(st_el).select_by_visible_text("沙鹿")
        time.sleep(3)
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
        time.sleep(12) # 沙鹿站數據較多，等待稍長

        def g_c(node_id):
            try: 
                val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                return val if val != "" else "N/A"
            except: return "N/A"

        # 沙鹿站包含額外詳細氣象欄位
        results["central_data"].append({
            "station": "沙鹿",
            "time": g_c("lab_IssueTime").replace("發布時間：", "").strip(),
            "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
            "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
            "NMHC": g_c("lab_NMHC"), 
            "WindSpeed": g_c("lab_WindSpeed"), 
            "WindDirect": g_c("lab_WindDirect"), 
            "RH": g_c("lab_RH")
        })
        print("   [成功] 沙鹿站詳細數據獲取完成")

        # --- 最終存檔 ---
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"=== 任務全部完成，成功更新至 air_quality.json ===")

    except Exception as e:
        print(f"致命錯誤: {traceback.format_exc()}")
        # 發生錯誤時保留基本的資料結構，防止網頁報錯
        error_fallback = {
            "tcc_data": [{"station": "數據重新整理中", "time": "請稍後", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-"}],
            "central_data": [{"station": "沙鹿", "time": "更新中", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-", "NMHC": "-", "WindSpeed": "-", "WindDirect": "-", "RH": "-"}]
        }
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(error_fallback, f, ensure_ascii=False, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()
