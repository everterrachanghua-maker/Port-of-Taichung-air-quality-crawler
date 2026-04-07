import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    options = Options()
    options.add_argument("--headless") # 雲端執行必須
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_data():
    driver = get_driver()
    results = {"tcc_data": [], "central_data": []}

    try:
        # --- 第一部分：港務與台電測站 ---
        url1 = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"進入網址: {url1}")
        driver.get(url1)
        time.sleep(10) # 等網頁開好

        # 1. 篩選：所屬單位 -> 大型事業
        try:
            Select(driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Org']")).select_by_visible_text("大型事業")
            time.sleep(3)
        except: pass

        # 2. 篩選：空品區 -> 中部空品區
        Select(driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Area']")).select_by_visible_text("中部空品區")
        time.sleep(10) # 重要！等測站選單長出來

        # 3. 循環處理 6 個測站
        stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水", "台電龍井"]
        for st in stations:
            print(f"查詢測站: {st}")
            # 點選測站名稱
            Select(driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']")).select_by_visible_text(st)
            time.sleep(2)
            
            # 按下「查詢」按鈕
            driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
            time.sleep(8) # 等數據跳出來

            # 抓數據
            def get_txt(node_id):
                try: return driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
                except: return "N/A"

            results["tcc_data"].append({
                "station": st,
                "time": get_txt("lab_IssueTime").replace("發布時間：", "").strip(),
                "O3": get_txt("lab_O3"), "PM25": get_txt("lab_PM25"), "PM10": get_txt("lab_PM10"),
                "CO": get_txt("lab_CO"), "SO2": get_txt("lab_SO2"), "NO2": get_txt("lab_NO2")
            })

        # --- 第二部分：一般監測站 (沙鹿) ---
        url2 = "https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx"
        print(f"進入網址: {url2}")
        driver.get(url2)
        time.sleep(10)

        # 1. 篩選：區域 -> 中部
        Select(driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Area']")).select_by_visible_text("中部空品區")
        time.sleep(5)
        
        # 2. 篩選：測站 -> 沙鹿
        Select(driver.find_element(By.CSS_SELECTOR, "select[id$='ddl_Station']")).select_by_visible_text("沙鹿")
        time.sleep(2)
        
        # 3. 按下「查詢」
        driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, "input[id$='btn_Query']"))
        time.sleep(10)

        def g_c(node_id):
            try: return driver.find_element(By.CSS_SELECTOR, f"span[id$='{node_id}']").text.strip()
            except: return "N/A"

        results["central_data"].append({
            "station": "沙鹿", "time": g_c("lab_IssueTime").replace("發布時間：", "").strip(),
            "O3": g_c("lab_O3"), "PM25": g_c("lab_PM25"), "PM10": g_c("lab_PM10"),
            "CO": g_c("lab_CO"), "SO2": g_c("lab_SO2"), "NO2": g_c("lab_NO2"),
            "NMHC": g_c("lab_NMHC"), "WindSpeed": g_c("lab_WindSpeed"), 
            "WindDirect": g_c("lab_WindDirect"), "RH": g_c("lab_RH")
        })

    except Exception as e:
        print(f"發生錯誤: {e}")
    
    finally:
        # 只要有抓到東西就存檔，不論多少
        if results["tcc_data"] or results["central_data"]:
            with open("air_quality.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
        driver.quit()

if __name__ == "__main__":
    scrape_data()
