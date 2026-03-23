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
    print("=== [啟動] 高速穩定整合版數據抓取 ===")
    driver = get_driver()
    # 設定最大等待時間 30 秒
    wait = WebDriverWait(driver, 30) 
    
    tcc_stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
    results = {"tcc_data": [], "central_data": []}

    try:
        # --- 任務 1: 港務與台電測站 (高速模式) ---
        url_tcc = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"1. 前往港區監測網: {url_tcc}")
        driver.get(url_tcc)
        
        # 使用 JS 快速選擇中部空品區 (value '4')
        area_sel = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
        driver.execute_script("arguments[0].value = '4'; arguments[0].dispatchEvent(new Event('change'));", area_sel)
        
        # 等待測站清單同步偵測 (原有穩定邏輯)
        print("   同步測站選單中...")
        for i in range(15):
            st_text = driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']").text
            if "台電梧棲" in st_text:
                break
            time.sleep(1)

        for st in tcc_stations:
            try:
                print(f"   正在抓取: {st}")
                st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
                # JS 高速切換測站
                driver.execute_script(f"var s=arguments[0]; for(var i=0;i<s.options.length;i++){{if(s.options[i].text.indexOf('{st}')!=-1){{s.selectedIndex=i;break;}}}} s.dispatchEvent(new Event('change'));", st_el)
                
                time.sleep(1) # 短緩衝確保事件觸發
                query_btn = driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']")
                driver.execute_script("arguments[0].click();", query_btn)

                # 智慧等待數據刷新：監測發布時間是否出現當前年份前三碼 "202"
                wait.until(lambda d: "202" in d.find_element(By.CSS_SELECTOR, "span[id$='lab_IssueTime']").text)

                def g_v(nid):
                    val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                    return val if val else "N/A"

                results["tcc_data"].append({
                    "station": st,
                    "time": g_v("lab_IssueTime").replace("發布時間：", "").strip(),
                    "O3": g_v("lab_O3"), "PM25": g_v("lab_PM25"), "PM10": g_v("lab_PM10"),
                    "CO": g_v("lab_CO"), "SO2": g_v("lab_SO2"), "NO2": g_v("lab_NO2")
                })
            except Exception as e:
                print(f"   [!] {st} 抓取超時或異常")

        # --- 任務 2: 沙鹿站 (高速模式) ---
        url_central = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"\n2. 前往一般監測網抓取沙鹿站: {url_central}")
        driver.get(url_central)
        
        try:
            area_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Area']")))
            driver.execute_script("arguments[0].value = '4'; arguments[0].dispatchEvent(new Event('change'));", area_el)
            
            time.sleep(2)
            st_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id$='ddl_Station']")))
            driver.execute_script("var s=arguments[0]; for(var i=0;i<s.options.length;i++){if(s.options[i].text=='沙鹿'){s.selectedIndex=i;break;}} s.dispatchEvent(new Event('change'));", st_el)
            
            time.sleep(1)
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            
            # 智慧等待數據載入
            wait.until(lambda d: "202" in d.find_element(By.CSS_SELECTOR, "span[id$='lab_IssueTime']").text)

            def g_c(nid):
                val = driver.find_element(By.CSS_SELECTOR, f"span[id$='{nid}']").text.strip()
                return val if val else "N/A"

            results["central_data"].append({
                "station": "沙鹿", "time": g_c("lab_IssueTime").replace("發布時間：", "").strip(),
                "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
                "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
                "NMHC": g_c("lab_NMHC"), "WindSpeed": g_c("lab_WindSpeed"), 
                "WindDirect": g_c("lab_WindDirect"), "RH": g_c("lab_RH")
            })
            print("   [成功] 沙鹿站詳細數據獲取完成")
        except Exception as e:
            print(f"   [失敗] 沙鹿站抓取程序錯誤: {e}")

    except Exception as e:
        print(f"\n致命錯誤: {traceback.format_exc()}")
    
    finally:
        # --- 最終檢查與存檔 (確保結構不破壞網頁) ---
        if not results["tcc_data"]:
            results["tcc_data"] = [{"station": "數據重新整理中", "time": "請稍後", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-"}]
        
        if not results["central_data"]:
            results["central_data"] = [{"station": "沙鹿", "time": "更新中", "O3": "-", "PM25": "-", "PM10": "-", "CO": "-", "SO2": "-", "NO2": "-", "NMHC": "-", "WindSpeed": "-", "WindDirect": "-", "RH": "-"}]

        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        driver.quit()
        print("\n=== 程序結束，檔案已更新 ===")

if __name__ == "__main__":
    scrape_data()
