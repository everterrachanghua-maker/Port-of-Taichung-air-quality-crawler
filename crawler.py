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
    print("=== [啟動] 最終穩定整合版爬蟲 ===")
    driver = get_driver()
    wait = WebDriverWait(driver, 45)
    
    final_results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 進入港區網頁: {url_tcc}")
        driver.get(url_tcc)
        time.sleep(10)

        # 選擇中部空品區
        print("   正在選擇: 中部空品區...")
        area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        driver.execute_script("arguments[0].value = '4'; arguments[0].dispatchEvent(new Event('change'));", area_el)
        
        # 關鍵：直到測站選單內容更新才繼續
        print("   等待港區測站清單同步...")
        for _ in range(20):
            try:
                st_list = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
                if "台電梧棲" in st_list:
                    print("   [OK] 港區清單載入成功")
                    break
            except: pass
            time.sleep(2)

        tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        for st in tcc_stations:
            try:
                print(f"   -> 正在處理: {st}")
                # 每次重新定位測站選單，防止 StaleElement 錯誤
                st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                driver.execute_script(f"var s=arguments[0]; for(var i=0;i<s.options.length;i++){{if(s.options[i].text.indexOf('{st}')!=-1){{s.selectedIndex=i;break;}}}} s.dispatchEvent(new Event('change'));", st_el)
                time.sleep(3)
                
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)
                time.sleep(10) # 數據載入給予充足時間

                def g_v(nid):
                    try: 
                        t = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                        return t if t else "數據接收中"
                    except: return "N/A"

                final_results["tcc_data"].append({
                    "station": st,
                    "time": g_v("lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                    "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                })
            except: print(f"      [!] {st} 失敗")

        # --- 任務 2: 沙鹿監測站 (一般測站) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"2. 進入沙鹿網頁: {url_central}")
        driver.get(url_central)
        time.sleep(8)

        area_el2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        driver.execute_script("arguments[0].value = '4'; arguments[0].dispatchEvent(new Event('change'));", area_el2)
        
        print("   等待沙鹿清單同步...")
        for _ in range(15):
            try:
                st_list2 = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
                if "沙鹿" in st_list2:
                    print("   [OK] 沙鹿清單載入成功")
                    break
            except: pass
            time.sleep(2)
        
        try:
            st_el2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
            driver.execute_script("var s=arguments[0]; for(var i=0;i<s.options.length;i++){if(s.options[i].text=='沙鹿'){s.selectedIndex=i;break;}} s.dispatchEvent(new Event('change'));", st_el2)
            time.sleep(3)
            
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            time.sleep(10)

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
        print(f"\n致命錯誤: {traceback.format_exc()}")
    
    finally:
        # 修正保護邏輯：若沒抓到任何東西，存入「更新中」而非「異常」
        if not final_results["tcc_data"]:
             final_results["tcc_data"] = [{"station": "數據更新中", "time": "請稍後"}]
        
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(final_results, f, ensure_ascii=False, indent=4)
        driver.quit()
        print("=== 任務結束，資料已發布 ===")

if __name__ == "__main__":
    scrape_data()
