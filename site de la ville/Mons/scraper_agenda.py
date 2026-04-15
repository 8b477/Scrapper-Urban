import json
import os
import time
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.mons.be/fr/que-faire-a-mons/agenda"
BASE_DOMAIN = "https://www.mons.be"


def generate_filename():
    date_str = datetime.now().strftime("%d-%m-%y")
    return f"mons_{date_str}.json"


def scrape_agenda():
    start_time = datetime.now(timezone.utc)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    print("Lancement de Chrome headless...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        print(f"Navigation vers {BASE_URL}")
        driver.get(BASE_URL)

        # Attendre que les événements soient chargés
        print("Attente du chargement des événements...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.r-list-item-group"))
        )
        time.sleep(2)

        items = driver.find_elements(By.CSS_SELECTOR, "li.r-list-item-group")
        print(f"  -> {len(items)} événement(s) chargé(s) initialement")

        # Cliquer sur "Plus de résultats" tant qu'il est visible
        click_count = 0
        while True:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button.btn-grad")
                if btn.is_displayed():
                    prev_count = len(items)
                    driver.execute_script("arguments[0].click();", btn)
                    click_count += 1
                    print(f"  -> Clic #{click_count} sur 'Plus de résultats'...")
                    time.sleep(3)

                    items = driver.find_elements(By.CSS_SELECTOR, "li.r-list-item-group")
                    print(f"     -> {len(items)} événement(s) total")

                    if len(items) == prev_count:
                        print("  -> Aucun nouveau résultat. Fin.")
                        break
                else:
                    print("  -> Bouton 'Plus de résultats' non visible. Fin.")
                    break
            except Exception:
                print("  -> Bouton 'Plus de résultats' non trouvé. Fin.")
                break

        # Extraire toutes les URLs
        all_urls = []
        links = driver.find_elements(By.CSS_SELECTOR, "a.r-list-item-link")
        for link in links:
            href = link.get_attribute("href")
            if href:
                if href.startswith("/"):
                    href = BASE_DOMAIN + href
                all_urls.append(href)

        print(f"\nTotal : {len(all_urls)} URL(s) extraite(s)")
        for i, url in enumerate(all_urls[:5], 1):
            print(f"  {i}. {url}")
        if len(all_urls) > 5:
            print(f"  ...")
            print(f"  {len(all_urls)}. {all_urls[-1]}")

    finally:
        driver.quit()

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    output = {
        "metadata": {
            "region": "Mons",
            "source": "mons.be",
            "scrape_date": start_time.isoformat(),
            "total_events": len(all_urls),
            "total_pages": 1 + click_count,
            "data_completeness": "Phase 1: Extraction des URLs via Selenium. Phase 2: Parsing des détails à venir.",
            "extraction_mode": "selenium",
            "pagination": {
                "load_more_clicks": click_count,
                "total_events_found": len(all_urls)
            },
            "last_execution": {
                "timestamp": end_time.isoformat(),
                "duration_seconds": round(duration, 1),
                "status": "SUCCESS",
                "notes": f"Extraction via Selenium. {len(all_urls)} URLs extraites en {round(duration)}s."
            },
            "events_extracted": 0,
            "extraction_date": None
        },
        "extraction_summary": {
            "method": "selenium_headless_chrome",
            "load_more_clicks": click_count
        },
        "event_urls": all_urls,
        "events": []
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, generate_filename())

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nJSON sauvegardé : {filepath}")
    return filepath


if __name__ == "__main__":
    scrape_agenda()
