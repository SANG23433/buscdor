import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from apify import Actor

async def scrape_profile_details(driver, profile_url, max_posts=6, max_comments=5):
    Actor.log.info(f"🔎 Análisis Profundo: {profile_url}")
    driver.get(profile_url)
    wait = WebDriverWait(driver, 15)
    data = {"url": profile_url, "seguidores": "N/A", "posts": []}

    try:
        # 1. Seguidores con múltiples fallbacks
        f_xpaths = [
            "//header//li[contains(., 'seguidores')]//span[@title]",
            "//header//li[contains(., 'followers')]//span",
            "//a[contains(@href, 'followers')]//span",
            "//header//section//ul//li[2]//span"
        ]
        
        follower_elem = None
        for xpath in f_xpaths:
            try:
                follower_elem = driver.find_element(By.XPATH, xpath)
                break
            except: continue
            
        if follower_elem:
            data["seguidores"] = follower_elem.get_attribute("title") or follower_elem.text

        # 2. Publicaciones
        time.sleep(3)
        post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reels/')]")
        post_urls = [link.get_attribute("href") for link in post_links[:max_posts]]

        for p_url in post_urls:
            try:
                driver.get(p_url)
                # Espera aleatoria para imitar humano
                await asyncio.sleep(random.uniform(2, 4))
                
                post_info = {"post_url": p_url, "comentarios": []}
                # Intentar capturar comentarios (excluyendo el h2 que suele ser la biografía/caption)
                c_xpath = "//ul//div[@role='none']//span[not(ancestor::h2)]"
                comment_elems = driver.find_elements(By.XPATH, c_xpath)
                
                for c in comment_elems[:max_comments]:
                    text = c.text.strip()
                    if text and len(text) > 1:
                        post_info["comentarios"].append(text)
                
                data["posts"].append(post_info)
            except:
                continue
                
        return data
    except Exception as e:
        Actor.log.warning(f"⚠️ Error parcial en detalles de {profile_url}: {e}")
        return data