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
    # 使用最新偽裝標頭
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_data():
    print("--- [Step 1] 初始化瀏覽器與環境 ---")
    driver = get_driver()
    # 設定智慧等待上限為 45 秒
    wait = WebDriverWait(driver, 45) 
    
    tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
    results = {"tcc_data": [], "central_data": []}

    try:
        # --- [Step 2] 任務 1: 港務與台電專用測站 ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"--- [Step 2] 開啟港區監測網: {url_tcc} ---")
        driver.get(url_tcc)
        
        # 1. 選擇「中部空品區」 (使用 JS 高速驅動)
        print("--- [Step 3] 選擇區域: 中部空品區 ---")
        area_sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        driver.execute_script("arguments[0].value = '4'; arguments[0].dispatchEvent(new Event('change'));", area_sel)
        
        # 智慧等待：偵測測站選單是否已更新（出現台電梧棲）
        print("等待測站清單同步中...")
        for i in range(15):
            st_text = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
            if "台電梧棲" in st_text:
                print(f"清單同步成功！(嘗試第 {i+1} 次)")
                break
            time.sleep(1.5)

        # 2. 循環抓取各站數據
        for st in tcc_stations:
            print(f"--- [Step 4] 正在抓取港區測站: {st} ---")
            try:
                # 重新定位選單，避免頁面局部刷新造成的失效
                st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                # 使用 JavaScript 強制切換測站並觸發網頁更新
                driver.execute_script(f"var s=arguments[0]; for(var i=0;i<s.options.length;i++){{if(s.options[i].text.indexOf('{st}')!=-1){{s.selectedIndex=i;break;}}}} s.dispatchEvent(new Event('change'));", st_el)
                
                time.sleep(2) # 短緩衝確保事件啟動
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)

                # 智慧等待數據刷新：偵測「發布時間」是否出現了年份數字 "202"
                # 這能讓程式在數據跳出的那一秒立刻抓取，不浪費多餘秒數
                wait.until(lambda d: "202" in d.find_element(By.CSS_SELECTOR, "span[id$='lab_IssueTime']").text)

                def g_v(nid):
                    try:
                        val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                        return val if val != "" else "數據接收中"
                    except: return "N/A"

                results["tcc_data"].append({
                    "station": st,
                    "time": g_v("lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                    "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                })
                print(f"抓取成功: {st}")
            except Exception as e:
                print(f"抓取 {st} 出錯或超時，跳過此站。")

        # --- [Step 5] 任務 2: 一般監測站 (沙鹿站詳細數據) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n--- 正在切換網址抓取沙鹿站: {url_central} ---")
        driver.get(url_central)
        
        try:
            # 選擇中部空品區 -> 沙鹿
            area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
            driver.execute_script("arguments[0].value = '4'; arguments[0].dispatchEvent(new Event('change'));", area_el)
            
            time.sleep(3) # 沙鹿站網頁較重，多等一下
            st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
            driver.execute_script("var s=arguments[0]; for(var i=0;i<s.options.length;i++){if(s.options[i].text=='沙鹿'){s.selectedIndex=i;break;}} s.dispatchEvent(new Event('change'));", st_el)
            
            time.sleep(1.5)
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            
            # 智慧等待數據載入完成
            wait.until(lambda d: "202" in d.find_element(By.CSS_SELECTOR, "span[id$='lab_IssueTime']").text)

            def g_c(nid):
                try:
                    val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                    return val if val != "" else "更新中"
                except: return "N/A"

            results["central_data"].append({
                "station": "沙鹿", 
                "time": g_c("lab_IssueTime").replace("發布時間：", "").strip(),
                "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
                "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
                "NMHC": g_c("lab_NMHC"), "WindSpeed": g_c("lab_WindSpeed"), 
                "WindDirect": g_c("lab_WindDirect"), "RH": g_c("lab_RH")
            })
            print("沙鹿站詳細數據抓取成功")
        except Exception as e:
            print(f"沙鹿站抓取失敗: {e}")

    except Exception as e:
        print("\n!!! 致命錯誤發生 !!!")
        print(traceback.format_exc())
    
    finally:
        # --- [Step 5] 最終存檔與保護邏輯 ---
        # 確保如果失敗，JSON 結構依然完整，不破壞前端 index.html 顯示
        if not results["tcc_data"]:
            results["tcc_data"] = [{"station": "數據重新整理中", "time": "請稍後", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-"}]
        
        if not results["central_data"]:
            results["central_data"] = [{"station": "沙鹿", "time": "更新中", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-", "NMHC": "-", "WindSpeed": "-", "WindDirect": "-", "RH": "-"}]

        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        driver.quit()
        print("\n=== 爬蟲程序結束，資料已成功更新 ===")

if __name__ == "__main__":
    scrape_data()
