import time
import random
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from apify import Actor
from vision_service import VisionService
from detail_scraper import scrape_profile_details

async def main():
    async with Actor:
        Actor.log.info("🚀 [INICIO] Scraper V22 Optimizado + Análisis Profundo >93%")
        
        actor_input = await Actor.get_input() or {}
        keywords = actor_input.get('keywords', [])
        session_cookies = actor_input.get('sessionCookies', [])
        max_results = actor_input.get('maxResults', 20)
        api_key = actor_input.get("googleApiKey")
        reference_url = actor_input.get("referenceImageUrl")

        # Configuración IA
        vision_tool = VisionService(api_key) if api_key else None
        emb_ref = None
        if vision_tool and reference_url:
            desc_ref = await vision_tool.get_image_description(reference_url)
            emb_ref = await vision_tool.get_text_embedding(desc_ref)

        chrome_options = Options()
        chrome_options.add_argument("--headless=new") 
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        stealth(driver, languages=["es-ES", "es"], vendor="Google Inc.", platform="Win32", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

        global_seen_profiles = set()
        all_potential_matches = []
        blacklist = ["reels", "explore", "direct", "stories", "accounts", "home", "about", "blog"]

        try:
            driver.get("https://www.instagram.com/")
            if session_cookies:
                for cookie in session_cookies:
                    try: driver.add_cookie({"name": cookie["name"], "value": cookie["value"], "domain": ".instagram.com", "path": "/"})
                    except: pass
                driver.refresh()
                time.sleep(7)

            wait = WebDriverWait(driver, 20)
            xpath_lupa = "//*[name()='svg' and (@aria-label='Buscar' or @aria-label='Busca' or @aria-label='Búsqueda')]/ancestor::a"
            boton_lupa = wait.until(EC.presence_of_element_located((By.XPATH, xpath_lupa)))
            driver.execute_script("arguments[0].click();", boton_lupa)
            time.sleep(3)

            for keyword in keywords:
                Actor.log.info(f"🔍 PROCESANDO: '{keyword}'")
                try:
                    search_xpath = "//input[@aria-label='Buscar entrada' or @placeholder='Busca']"
                    search_input = wait.until(EC.presence_of_element_located((By.XPATH, search_xpath)))
                    
                    # LIMPIEZA V22 (Botón X)
                    try:
                        clear_btn = driver.find_element(By.XPATH, "//*[name()='svg' and (@aria-label='Borrar' or @aria-label='Clear')]")
                        driver.execute_script("arguments[0].click();", clear_btn)
                        time.sleep(1.5)
                    except: search_input.clear()

                    for char in keyword:
                        search_input.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.1))
                    
                    time.sleep(8)
                    result_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/')]")
                    
                    for link in result_links:
                        try:
                            href = link.get_attribute("href")
                            path = href.split("instagram.com/")[1].strip("/")
                            if path and "/" not in path and path not in blacklist and path not in global_seen_profiles:
                                img_src = link.find_element(By.TAG_NAME, "img").get_attribute("src")
                                
                                sim_score = 0
                                if vision_tool and emb_ref:
                                    desc_p = await vision_tool.get_image_description(img_src)
                                    emb_p = await vision_tool.get_text_embedding(desc_p)
                                    sim_score = vision_tool.calculate_cosine_similarity(emb_ref, emb_p)

                                global_seen_profiles.add(path)
                                Actor.log.info(f"✅ VISTO: @{path} | Similitud: {round(sim_score*100, 1)}%")
                                all_potential_matches.append({"usuario": path, "url_perfil": href, "similitud": sim_score, "icono": img_src})
                        except: continue
                except Exception as e: Actor.log.error(f"⚠️ Error: {e}")

            # --- ANÁLISIS FINAL (> 93%) ---
            valid_matches = [m for m in all_potential_matches if m["similitud"] > 0.93]
            valid_matches = sorted(valid_matches, key=lambda x: x["similitud"], reverse=True)[:3]

            if not valid_matches:
                Actor.log.warning("🚫 AVISO: NO existe instagram")
                await Actor.push_data({"status": "NO existe instagram"})
            else:
                for match in valid_matches:
                    details = await scrape_profile_details(driver, match["url_perfil"])
                    await Actor.push_data({**match, **details})

        finally:
            driver.quit()
            Actor.log.info("🏁 FIN.")

if __name__ == "__main__":
    asyncio.run(main())