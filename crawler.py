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

def scrape_data():
    print("=== [開始執行] 空氣品質爬蟲程序 ===")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)

    stations = ["台電梧棲", "港務工作船渠", "港務南突堤", "港務中泊渠", "台電清水"]
    results = []

    try:
        url = "https://airtw.moenv.gov.tw/cht/EnvMonitoring/Local/LocalMonitoring.aspx?Type=Tcc"
        print(f"[1/4] 前往網址: {url}")
        driver.get(url)
        time.sleep(10)

        # 1. 選擇「中部空品區」
        print("[2/4] 正在切換區域至『中部空品區』...")
        area_el = wait.until(EC.presence_of_element_located((By.ID, "cp_content_ddl_Area")))
        Select(area_el).select_by_visible_text("中部空品區")
        
        # 關鍵等待：直到測站下拉選單包含我們想要的測站
        print("      等待測站清單刷新中...")
        for _ in range(10):
            st_html = driver.find_element(By.ID, "cp_content_ddl_Station").get_attribute("innerHTML")
            if "台電梧棲" in st_html:
                print("      清單更新完成！")
                break
            time.sleep(2)
        else:
            print("      [錯誤] 測站清單似乎沒更新，嘗試繼續...")

        for st in stations:
            print(f"[3/4] 抓取測站數據: {st}")
            try:
                # 選擇測站
                st_select_el = wait.until(EC.element_to_be_clickable((By.ID, "cp_content_ddl_Station")))
                Select(st_select_el).select_by_visible_text(st)
                time.sleep(2)

                # 點擊查詢
                query_btn = driver.find_element(By.ID, "cp_content_btn_Query")
                driver.execute_script("arguments[0].click();", query_btn)
                
                # 等待數據標籤內容發生變化或出現
                time.sleep(10) # 增加等待數據回傳的時間

                def get_v(eid):
                    try:
                        t = driver.find_element(By.ID, eid).text.strip()
                        return t if t else "未監測"
                    except: return "N/A"

                issue_time = get_v("cp_content_lab_IssueTime").replace("發布時間：", "").strip()
                
                if not issue_time or issue_time == "N/A":
                    print(f"      [警告] {st} 抓取不到發布時間，可能數據尚未載入。")
                    continue

                data = {
                    "station": st,
                    "time": issue_time,
                    "O3": get_v("cp_content_lab_O3"),
                    "PM25": get_v("cp_content_lab_PM25"),
                    "PM10": get_v("cp_content_lab_PM10"),
                    "CO": get_v("cp_content_lab_CO"),
                    "SO2": get_v("cp_content_lab_SO2"),
                    "NO2": get_v("cp_content_lab_NO2")
                }
                results.append(data)
                print(f"      [成功] 已抓取: {st} ({issue_time})")

            except Exception as inner_e:
                print(f"      [跳過] {st} 發生錯誤: {inner_e}")

        # 4. 存檔
        print(f"[4/4] 任務結束，共抓取 {len(results)} 筆有效數據。")
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print("\n" + "="*50)
        print("!!! 程式執行發生致命錯誤 !!!")
        print(f"錯誤類型: {type(e).__name__}")
        print(f"詳細訊息: {str(e)}")
        print("="*50 + "\n")
        # 即使報錯也存下一個空的 JSON，避免下一動失敗
        with open("air_quality.json", "w", encoding="utf-8") as f:
            json.dump([], f)
        raise e # 重新拋出錯誤讓 Action 知道失敗

    finally:
        driver.quit()
        print("=== 爬蟲程序結束 ===")

if __name__ == "__main__":
    scrape_data()
