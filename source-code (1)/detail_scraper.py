import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from apify import Actor

async def scrape_profile_details(driver, profile_url, max_posts=12, max_comments=10):
    Actor.log.info(f"🔎 Análisis Profundo: {profile_url}")
    driver.get(profile_url)
    wait = WebDriverWait(driver, 15)
    data = {"url": profile_url, "seguidores": "0", "posts": []}

    try:
        # 1. Seguidores
        f_xpath = "//header//li[contains(., 'seguidores')]//span[@title] | //header//li[contains(., 'followers')]//span"
        follower_elem = wait.until(EC.presence_of_element_located((By.XPATH, f_xpath)))
        data["seguidores"] = follower_elem.get_attribute("title") or follower_elem.text

        # 2. Publicaciones
        time.sleep(4)
        post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
        post_urls = [link.get_attribute("href") for link in post_links[:max_posts]]

        for p_url in post_urls:
            driver.get(p_url)
            time.sleep(random.uniform(3, 5))
            post_info = {"post_url": p_url, "comentarios": []}

            # 3. Comentarios
            c_xpath = "//ul//div[@role='none']//span[not(ancestor::h2)]"
            comment_elems = driver.find_elements(By.XPATH, c_xpath)
            for c in comment_elems[:max_comments]:
                if c.text.strip(): post_info["comentarios"].append(c.text.strip())
            
            data["posts"].append(post_info)
        return data
    except Exception as e:
        Actor.log.error(f"⚠️ Error en detalles: {e}")
        return data