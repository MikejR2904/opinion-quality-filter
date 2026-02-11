import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

## This is to scrape Google Maps https://www.google.com/maps for reviews and profile information
## We use selenium with ChromeDriver to simulate browser actions.
## The flow is as follows:
## 1. Open Google Maps and load for a while
## 2. Search for the business name and location through the Search Box. After searching, wait for results to load.
## 3. From the search results, there are multiple listings if the location is never specified. 
##    For bulk scraping, we will extract multiple business listings from the search results page.
##    For specific scraping, we will click into the first business listing, although usually this won't happen.
## 4. On the business listing page, we will try to navigate to the reviews section and scroll to load more reviews.
## 5. Extract relevant information from the business listing and reviews. 
##    For example, address, overall rating, review count, category/type, individual reviews, author names, ratings, review texts, timestamps, etc.
##    If official website URL is found, we can also extract that.
## 6. Save the extracted data into CSV files for further processing (e.g. ingestion).

# Simulate a real Chrome browser with anti-detection measures
def get_chrome_driver() -> Optional[webdriver.Chrome]:
    options = Options()
    # Essential anti-detection options
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Updated user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # Window and performance options
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--disable-notifications')
    try:
        driver = webdriver.Chrome(options=options)
        # Further anti-detection JavaScript execution
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        # print("Chrome driver created successfully")
        return driver
    except Exception as e:
        print(f"Error creating Chrome driver: {e}")
        return None

# Open Google Maps and wait for elements to load
def open_google_maps(driver: webdriver.Chrome, wait: int = 3) -> None:
    driver.get("https://www.google.com/maps")
    time.sleep(wait)

# Search for a business/location and wait for results to load
def search_location(driver: webdriver.Chrome, query: str) -> bool:
    try:
        # Get the search box using the cursor/selector
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='q'], #searchboxinput, input[aria-label*='Search']"))
        )
        if not search_box:
            print("Could not find the Google Maps search box. Try to reload the page.")
            return False
        search_box.clear()
        time.sleep(1)
        search_box.send_keys(query) # Enter the search query; this can be business name + location or just either
        time.sleep(2)
        # print(f"Searching for location: {query}")
        search_box.send_keys(Keys.RETURN) # Press enter to retrieve results
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='main']"))
        )
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error searching location '{query}': {e}. Try to reload the page.")
        return False

# Detect specific vs bulk scraping based on presence of multiple business cards
# If multiple business cards are found, we do bulk scraping; else specific scraping
# For example, "Starbucks Singapore" may return multiple locations, while "Starbucks Orchard Road Singapore" may return a single location
def detect_scraping_type(driver: webdriver.Chrome) -> str:
    try:
        listings = driver.find_elements(By.CSS_SELECTOR, "div[role='article'], .Nv2PK")
        if len(listings) >= 2: # If multiple business cards found, do bulk scraping
            return "bulk"
    except Exception as e:
        print(f"Error detecting scraping type: {e}. Defaulting to specific scraping.")
    return "specific"

# Extract business listings from search results for bulk scraping
def get_business_url(driver: webdriver.Chrome, max_locations: int = 20) -> List[str]:
    urls = []
    wait = WebDriverWait(driver, 2)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed'], div[role='main']")))
    links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
    for link in links[:max_locations]:
        url = link.get_attribute("href")
        if url:
            urls.append(url)
    return urls

# Click a business listing to go to its detail page for bulk scrapping
def click_business_listing(driver: webdriver.Chrome, listing: webdriver.remote.webelement.WebElement) -> None:
    try:
        driver.execute_script("arguments[0].click();", listing)
        print("Clicked on business listing...")
        WebDriverWait(driver, 3).until(EC.url_contains("/place/"))
        time.sleep(2)
    except Exception as e:
        print(f"Error clicking business listing: {e}")

# Extract business profile information from the detail page (single business, applicable to both scrapping types)
def extract_business_profile(driver: webdriver.Chrome) -> Dict:
    profile: Dict = {
        "name": None,
        "address": None,
        "category": None,
        "overall_rating": None,
        "review_count": None,
        "website": None,
        "google_maps_url": driver.current_url,
        "lat": None,
        "lng": None
    }
    # Wait for main content to load; this is essential for bulk scraping after clicking a listing
    wait = WebDriverWait(driver, 10)
    # Business or location name
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        name_elem = driver.find_element(By.CSS_SELECTOR, "h1[class*='DUwDvf'], h1 span[class*='a5H0ec']")
        profile["name"] = name_elem.text.strip()
        # print(f"[DEBUG] Correctly identified: {profile['name']}")
    except:
        pass
    # Address
    try:
        addr_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address'] .fontBodyMedium")
        profile["address"] = addr_elem.text.strip()
    except:
        pass
    # Category / type; for example Restaurant, Cafe, Shopping Mall, etc.
    try:
        category_element = driver.find_element(By.CSS_SELECTOR, "button.DkEaL, button[jsaction*='pane.rating.category']")
        category_text = category_element.text.strip()
        if category_text and not re.match(r'^\d+\.?\d*$', category_text):
            profile["category"] = category_text
    except:
        pass
    # Overall rating and review count
    try:
        rating_elem = driver.find_element(By.CSS_SELECTOR, "span[aria-label*='star'], div.F7nice span[aria-hidden='true']")
        rating_text = rating_elem.text.strip()
        if rating_text and re.match(r'^\d+\.?\d*$', rating_text):
            profile["overall_rating"] = float(rating_text)
        review_count_elem = driver.find_element(By.CSS_SELECTOR, "div.F7nice span[aria-label*='reviews']")
        review_aria = review_count_elem.get_attribute("aria-label")
        count_match = re.search(r'([\d,]+)\s*reviews?', review_aria)
        if count_match:
            profile["review_count"] = int(count_match.group(1).replace(',', ''))
    except:
        pass
    # Official website or menu link
    try:
        website_element = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority'], a[data-item-id='website'], a[href*='http']")
        profile["website"] = website_element.get_attribute("href")
    except:
        pass
    # Latitude and Longitude from URL
    try:
        url = driver.current_url
        lat_lng_match = re.search(r'!3d([-+]?\d+\.\d+)!4d([-+]?\d+\.\d+)', url)
        if lat_lng_match:
            profile["lat"] = float(lat_lng_match.group(1))
            profile["lng"] = float(lat_lng_match.group(2))
    except:
        pass
    return profile

# Extract reviews from the business detail page
def extract_reviews(driver: webdriver.Chrome, max_reviews: int = 10) -> List[Dict]:
    reviews: List[Dict] = []
    try:
        # Try to navigate to reviews section by clicking the reviews tab/button
        # We shall see Google review summary as well as the comment section
        try:
            reviews_button  = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='Reviews']"))
            )
            driver.execute_script("arguments[0].click();", reviews_button)
            time.sleep(3)
        except Exception as e:
            print(f"Could not find reviews tab: {e}")
            return reviews
        # Locate the reviews container and scroll to load more reviews
        try:
            scroll_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.m6QErb.DxyBCb.kA9KIf.dS8AEf"))
            )
        except Exception as e:
            scroll_container = driver.find_element(By.TAG_NAME, "body")
        seen_ids = set() # To avoid duplicates
        stall_count, MAX_STALL = 0, 5 # Avoid stalling when loading new reviews
        scroll_attempts, MAX_SCROLL_ATTEMPTS = 0, 20
        # Scroll and collect reviews until max_reviews reached
        while len(reviews) < max_reviews and scroll_attempts < MAX_SCROLL_ATTEMPTS:
            scroll_attempts += 1
            last_h = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
            containers = driver.find_elements(By.CSS_SELECTOR, "div[data-review-id]")
            new_found = False
            for container in containers:
                review_id = container.get_attribute("data-review-id")
                if review_id in seen_ids:
                    continue
                new_found = True
                # Click "More" button if it exists. This only happens if the review text is long enough.
                try:
                    more_button = container.find_elements(By.CSS_SELECTOR, "button.w8B6B, button[aria-label='See more']")
                    if more_button:
                        driver.execute_script("arguments[0].click();", more_button[0])
                        time.sleep(0.5)
                except:
                    pass
                review_data: Dict = {
                    "author_name": None,
                    "rating": None,
                    "text": None,
                    "relative_time": None,
                    "review_id": review_id
                }
                # Author name
                try:
                    author_elem = container.find_element(By.CSS_SELECTOR, ".d4r55, .TSUbDb a, span[class*='TSUbDb']")
                    review_data["author_name"] = author_elem.text.strip()
                except:
                    pass
                # Rating
                try:
                    rating_elem = container.find_element(By.CSS_SELECTOR, "span[aria-label*='star']")
                    rating_aria = rating_elem.get_attribute("aria-label")
                    rating_match = re.search(r"(\d+)", rating_aria)
                    if rating_match:
                        review_data["rating"] = int(rating_match.group(1))
                except:
                    pass
                # Review text
                try:
                    text_elem = container.find_element(By.CSS_SELECTOR, ".wiI7pd, [data-expandable-section], .MyEned span")
                    review_data["text"] = text_elem.text.strip()
                except:
                    pass
                # Relative time
                try:
                    time_elem = container.find_element(By.CSS_SELECTOR, ".rsqaWe, [class*='time']")
                    review_data["relative_time"] = time_elem.text.strip()
                except:
                    pass
                reviews.append(review_data)
                seen_ids.add(review_id)
                if len(reviews) >= max_reviews:
                    break
            # Scroll down to load more reviews
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
            time.sleep(2)
            new_h = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
            if new_h == last_h and not new_found:
                driver.execute_script("arguments[0].scrollTop += 500", scroll_container)
                time.sleep(0.5)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                stall_count += 1
                if stall_count >= MAX_STALL:
                    break
            else:
                stall_count = 0
    except Exception as e:
        print(f"Error extracting reviews: {e}")
    return reviews

# Parse relative time strings into absolute datetime objects
def parse_relative_time(relative_time: str) -> Optional[datetime]:
    try:
        now = datetime.now()
        pattern = re.compile(r'(\d+|a)\s+(minute|hour|day|week|month|year)s?\s+ago', re.IGNORECASE)
        match = pattern.search(relative_time)
        if match:
            value = int(match.group(1)) if match.group(1) != 'a' else 1 # Handle e.g. a day ago case
            unit = match.group(2)
            if unit == 'minute':
                return now - timedelta(minutes=value)
            elif unit == 'hour':
                return now - timedelta(hours=value)
            elif unit == 'day':
                return now - timedelta(days=value)
            elif unit == 'week':
                return now - timedelta(weeks=value)
            elif unit == 'month':
                return now - timedelta(days=value*30) # Approximation
            elif unit == 'year':
                return now - timedelta(days=value*365) # Approximation
    except Exception as e:
        print(f"Error parsing relative time '{relative_time}': {e}")
    return None

# Save results to CSV on data/raw/google_places/
def save_to_csv(profiles: List[Dict], filename: str) -> None:
    flattened_profiles = []
    for profile in profiles:
        base_info = {k: v for k, v in profile.items() if k != "reviews"}
        for review in profile.get("reviews", []):
            row = base_info.copy()
            row.update({
                "author": review.get("author_name"),
                "review_rating": review.get("rating"),
                "review_text": review.get("text"),
                "relative_time": review.get("relative_time"),
                "date_retrieved": datetime.now().strftime('%Y-%m-%d'),
                "calculated_date": parse_relative_time(review.get("relative_time")),
                "review_id": review.get("review_id")
            })
            flattened_profiles.append(row)
    if not flattened_profiles:
        print("[WARNING] No data to save.")
        return
    df = pd.DataFrame(flattened_profiles)
    df.to_csv(filename, mode="a", header=None, index=False, encoding='utf-8-sig')
    print(f"Saved data to {filename}")

## Overall scrapping logic (query -> scrapper -> data fetched and trigger RAG ingestion to execute)
def scrap_google_maps(query: str, max_locations: int = 10, max_reviews: int = 10) -> None:
    driver = get_chrome_driver()
    open_google_maps(driver)
    search_location(driver, query)
    scraping_type = detect_scraping_type(driver)
    all_results = []
    if scraping_type == "bulk":
        listings = get_business_url(driver, max_locations)
        for url in listings:
            driver.get(url)
            profile = extract_business_profile(driver)
            reviews = extract_reviews(driver, max_reviews)
            profile["reviews"] = reviews
            all_results.append(profile)
            driver.back()
            time.sleep(2)
    else:
        profile = extract_business_profile(driver)
        reviews = extract_reviews(driver, max_reviews)
        profile["reviews"] = reviews
        all_results.append(profile)
    ## TO DO: Trigger RAG data collector system to fetch contexts

    driver.quit()
    save_to_csv(all_results, "data/raw/google_places/google_maps_reviews.csv")

# # Test script
# scrap_google_maps("Starbucks Singapore", 2, 5)