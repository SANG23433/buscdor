import asyncio
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium_stealth import stealth
from apify import Actor
from vision_service import VisionService
from detail_scraper import scrape_profile_details

async def main():
    async with Actor:
        Actor.log.info("🚀 [V23.3] Scraper Ultra-Resiliente: Fix de Contenedor + Limpieza Dual")
        
        # 1. VALIDACIÓN DE INPUT
        actor_input = await Actor.get_input() or {}
        keywords = actor_input.get('keywords', [])
        session_cookies = actor_input.get('sessionCookies', [])
        max_results = actor_input.get('maxResults', 20)
        api_key = actor_input.get("googleApiKey")
        reference_url = actor_input.get("referenceImageUrl")

        # 2. CONFIGURACIÓN IA
        vision_tool = VisionService(api_key) if api_key else None
        emb_ref = None
        if vision_tool and reference_url:
            try:
                desc_ref = await vision_tool.get_image_description(reference_url)
                emb_ref = await vision_tool.get_text_embedding(desc_ref)
                Actor.log.info("🎯 Imagen de referencia procesada correctamente.")
            except Exception as e:
                Actor.log.error(f"❌ Error configurando IA: {e}")

        # 3. NAVEGADOR
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(options=chrome_options)
        stealth(driver, 
                languages=["es-ES", "es"], 
                vendor="Google Inc.", 
                platform="Win32", 
                renderer="Intel Iris OpenGL Engine", 
                fix_hairline=True)

        # --- MEMORIA Y FILTROS ---
        global_seen_profiles = set()
        blacklist = ["reels", "explore", "direct", "stories", "accounts", "home", "about", "blog"]
        my_user_id = "76440184081" 
        all_potential_matches = []

        try:
            # 4. INICIO Y COOKIES
            driver.get("https://www.instagram.com/")
            if session_cookies:
                for cookie in session_cookies:
                    try:
                        driver.add_cookie({
                            "name": cookie["name"], 
                            "value": cookie["value"], 
                            "domain": ".instagram.com",
                            "path": "/"
                        })
                    except: pass
                driver.refresh()
                await asyncio.sleep(7)

            wait = WebDriverWait(driver, 20)

            # LÓGICA V22: ABRIR LUPA UNA SOLA VEZ
            xpath_lupa = "//*[name()='svg' and (@aria-label='Buscar' or @aria-label='Busca' or @aria-label='Búsqueda')]/ancestor::a"
            boton_lupa = wait.until(EC.presence_of_element_located((By.XPATH, xpath_lupa)))
            driver.execute_script("arguments[0].click();", boton_lupa)
            await asyncio.sleep(3)

            # 5. BÚCLE DE KEYWORDS
            for keyword in keywords:
                Actor.log.info(f"🔍 PROCESANDO: '{keyword}'")
                try:
                    search_input_xpath = "//input[@aria-label='Buscar entrada' or @placeholder='Busca']"
                    search_input = wait.until(EC.presence_of_element_located((By.XPATH, search_input_xpath)))
                    
                    # --- LIMPIEZA RESILIENTE (FIX JS ERROR) ---
                    try:
                        # Opción A: Intentar con el CONTENEDOR que tiene role="button"
                        clear_btn_xpath = "//div[@role='button' and (contains(@aria-label, 'Borrar') or contains(@aria-label, 'Clear'))]"
                        clear_btn = driver.find_element(By.XPATH, clear_btn_xpath)
                        driver.execute_script("arguments[0].click();", clear_btn)
                        Actor.log.info("🧹 Limpieza exitosa mediante botón de interfaz.")
                        await asyncio.sleep(1)
                    except Exception:
                        # Opción B (Fallback): Si falla el botón o no existe, usamos teclado
                        Actor.log.info("⌨️ Botón X no disponible. Usando limpieza por teclado.")
                        search_input.send_keys(Keys.CONTROL + "a")
                        search_input.send_keys(Keys.BACKSPACE)
                        await asyncio.sleep(0.5)

                    # ESCRITURA HUMANA
                    for char in keyword:
                        search_input.send_keys(char)
                        await asyncio.sleep(random.uniform(0.06, 0.14))
                    
                    await asyncio.sleep(7)

                    # EXTRACCIÓN
                    result_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/')]")
                    keyword_count = 0
                    
                    for link in result_links:
                        try:
                            href = link.get_attribute("href")
                            if not href or "instagram.com" not in href: continue

                            path = href.split("instagram.com/")[1].strip("/")
                            label = link.get_attribute("aria-label") or link.text or ""
                            
                            if path and "/" not in path and path not in blacklist:
                                if my_user_id in href or "perfil" in label.lower(): continue
                                
                                if path not in global_seen_profiles:
                                    try:
                                        img_src = link.find_element(By.TAG_NAME, "img").get_attribute("src")
                                    except:
                                        img_src = "No disponible"

                                    score = 0
                                    if vision_tool and emb_ref and img_src != "No disponible":
                                        desc = await vision_tool.get_image_description(img_src)
                                        emb = await vision_tool.get_text_embedding(desc)
                                        score = vision_tool.calculate_cosine_similarity(emb_ref, emb)

                                    global_seen_profiles.add(path)
                                    Actor.log.info(f"✅ @{path} | Similitud: {round(score*100, 1)}%")
                                    
                                    all_potential_matches.append({
                                        "keyword": keyword,
                                        "usuario": path,
                                        "url_perfil": href,
                                        "url_icono": img_src,
                                        "similitud": score
                                    })
                                    keyword_count += 1
                                    
                        except StaleElementReferenceException:
                            continue

                    Actor.log.info(f"📊 Keyword '{keyword}' finalizada: {keyword_count} perfiles.")

                except Exception as err:
                    Actor.log.error(f"❌ Error en keyword '{keyword}': {err}")

            # --- ANÁLISIS PROFUNDO FINAL ---
            best_globals = sorted([m for m in all_potential_matches if m["similitud"] > 0.90], 
                                 key=lambda x: x["similitud"], reverse=True)[:3]

            if not best_globals and all_potential_matches:
                # Si no hay excelentes, subimos los básicos para no perder el trabajo
                for m in all_potential_matches:
                    await Actor.push_data(m)
            elif best_globals:
                for match in best_globals:
                    details = await scrape_profile_details(driver, match["url_perfil"])
                    await Actor.push_data({**match, **details})

        finally:
            driver.quit()
            Actor.log.info(f"🏁 FIN. Perfiles totales: {len(global_seen_profiles)}")

if __name__ == "__main__":
    asyncio.run(main())