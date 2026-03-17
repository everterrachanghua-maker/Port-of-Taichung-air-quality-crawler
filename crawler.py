import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_data():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20) # 最多等待 20 秒
    
    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []
    
    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        driver.get(url)

        # 1. 等待並選擇「中部空品區」
        area_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Area")))
        Select(area_el).select_by_visible_text("中部空品區")
        time.sleep(3) # 給網頁一點反應時間切換測站清單

        for st in stations:
            print(f"正在抓取: {st}...")
            # 2. 選擇「測站名稱」
            station_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Station")))
            Select(station_el).select_by_visible_text(st)
            
            # 3. 點擊「查詢」
            btn = wait.until(EC.element_to_be_clickable((By.ID, "cp_content_btn_Query")))
            btn.click()
            time.sleep(5) # 等待數據刷新
            
            # 4. 抓取數據
            try:
                data = {
                    "station": st,
                    "time": driver.find_element(By.CSS_SELECTOR, ".header_time").text.replace("發布時間：", "").strip(),
                    "O3": driver.find_element(By.CSS_SELECTOR, ".p_o3").text,
                    "PM25": driver.find_element(By.CSS_SELECTOR, ".p_pm25").text,
                    "PM10": driver.find_element(By.CSS_SELECTOR, ".p_pm10").text,
                    "CO": driver.find_element(By.CSS_SELECTOR, ".p_co").text,
                    "SO2": driver.find_element(By.CSS_SELECTOR, ".p_so2").text,
                    "NO2": driver.find_element(By.CSS_SELECTOR, ".p_no2").text
                }
                results.append(data)
                print(f"{st} 成功")
            except:
                print(f"{st} 抓取某欄位失敗，跳過")

        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print("JSON 檔案已產生成功")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()scrape_data()
