from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import random
import re

# ======= CONFIGURATION =======
USERNAME = 'YOUR_ACCOUNT_USERNAME'
PASSWORD = 'YOUR_ACCOUNT_PASSSWORD'
TARGET_PROFILE = 'TARGET'
POST_LIMIT = 5  # Number of posts to scrape
HEADLESS_MODE = False  # Set True for no browser UI
PROXY = None  # e.g., 'http://username:password@host:port' or None

# ======= SETUP WEBDRIVER =======
options = webdriver.ChromeOptions()
if HEADLESS_MODE:
    options.add_argument('--headless=new')  # Modern headless mode
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
if PROXY:
    options.add_argument(f'--proxy-server={PROXY}')

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options)
wait = WebDriverWait(driver, 15)  # Increased timeout

# ======= LOGIN TO INSTAGRAM =======
try:
    driver.get('https://www.instagram.com/accounts/login/')
    wait.until(EC.presence_of_element_located((By.NAME, 'username')))
    driver.find_element(By.NAME, 'username').send_keys(USERNAME)
    driver.find_element(By.NAME, 'password').send_keys(PASSWORD)
    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    time.sleep(random.uniform(4, 6))  # Random delay to mimic human
    print("✅ Logged in successfully")
except Exception as e:
    print(f"✘ Login failed: {e}")
    driver.quit()
    exit()

# ======= NAVIGATE TO TARGET PROFILE =======
try:
    driver.get(f'https://www.instagram.com/{TARGET_PROFILE}/')
    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'main')))
    print(f"✅ Loaded profile: {TARGET_PROFILE}")
except Exception as e:
    print(f"✘ Failed to load profile: {e}")
    driver.quit()
    exit()

# ======= EXTRACT PROFILE DATA =======
profile_data = {'username': TARGET_PROFILE}
try:
    # Extract followers, following, posts from meta or JSON
    script_tag = driver.find_element(By.XPATH, '//script[contains(text(),"user")]')
    json_data = re.search(r'({"user":.+?})\s*</script>', script_tag.get_attribute('innerHTML'))
    if json_data:
        data = json.loads(json_data.group(1))
        user = data['user']
        profile_data.update({
            'followers': user.get('edge_followed_by', {}).get('count', 0),
            'following': user.get('edge_follow', {}).get('count', 0),
            'posts': user.get('edge_owner_to_timeline_media', {}).get('count', 0),
            'bio': user.get('biography', 'N/A'),
            'full_name': user.get('full_name', 'N/A')
        })
    else:
        # Fallback to meta description
        meta_desc = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
        profile_data['description'] = meta_desc
    print(f"Profile Data: {profile_data}")
except Exception as e:
    print(f"✘ Error extracting profile data: {e}")

# ======= SCROLL AND COLLECT POST LINKS =======
post_links = set()
try:
    while len(post_links) < POST_LIMIT:
        post_elements = driver.find_elements(By.XPATH, '//a[contains(@href,"/p/")]')
        for post in post_elements:
            post_url = post.get_attribute('href')
            if post_url and '/p/' in post_url:
                post_links.add(post_url)
            if len(post_links) >= POST_LIMIT:
                break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
    print(f"✅ Found {len(post_links)} post URLs")
except Exception as e:
    print(f"✘ Error collecting post links: {e}")

# ======= SCRAPE EACH POST =======
posts_data = []
for url in post_links:
    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
        time.sleep(random.uniform(1, 3))

        # Extract likes
        likes ="Disembunyikan"
        try:
            likes_element = driver.find_element(By.XPATH, '//section//span[contains(text()," likes") or contains(text(),"like")]')
            likes = likes_element.text
        except:
            pass

        # Extract comments (up to 3)
        comments = []
        try:
            comment_elements = driver.find_elements(By.XPATH, '//ul/ul//span[@class=""]')
            comments = [c.text for c in comment_elements[:3] if c.text.strip()]
        except:
            pass

        # Extract caption
        caption ="N/A"
        try:
            caption_element = driver.find_element(By.XPATH, '//div/h1')
            caption = caption_element.text
        except:
            pass

        posts_data.append({
            'url': url,
            'likes': likes,
            'comments': comments,
            'caption': caption
        })
        print(f"✔ Scraped post: {url}")
    except Exception as e:
        print(f"✘ Failed to scrape post {url}: {e}")

# ======= CALCULATE ENGAGEMENT (if possible) =======
try:
    if profile_data.get('followers', 0) > 0:
        total_likes = sum(int(post['likes'].split()[0].replace(',', '')) for post in posts_data if post['likes'] !="Disembunyikan")
        total_comments = sum(len(post['comments']) for post in posts_data)
        engagement_rate = ((total_likes + total_comments) / profile_data['followers']) * 100
        profile_data['engagement_rate'] = f"{engagement_rate:.2f}%"
except Exception as e:
    print(f"✘ Error calculating engagement: {e}")

# ======= SAVE DATA TO JSON =======
output = {
    'profile': profile_data,
    'posts': posts_data}
try:
    with open(f'{TARGET_PROFILE}_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"✅ Data saved to {TARGET_PROFILE}_data.json")
except Exception as e:
    print(f"✘ Error saving data: {e}")

# ======= CLEANUP =======
driver.quit()
