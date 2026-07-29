import json
import time
import requests
from playwright.sync_api import sync_playwright

# Webhook Discord
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1521502269118615622/2KQEzJpDBs6db1w8sI5XLXdRn9_A_vTkIG85p55QwNWcPyHl220vmvJ9acj8uMxGqBi8"

# Parametri di ricerca Wallapop
SEARCH_KEYWORD = "zanotti"
MAX_PRICE = 500

SEEN_ITEMS_FILE = "seen_items.json"

def load_seen_items():
    try:
        with open(SEEN_ITEMS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen_items(seen_set):
    with open(SEEN_ITEMS_FILE, "w") as f:
        json.dump(list(seen_set), f)

def send_discord_alert(item):
    title = item.get("title", "Senza titolo")
    price = item.get("price", "N/A")
    currency = item.get("currency", "EUR")
    web_slug = item.get("web_slug", "")
    item_url = f"https://it.wallapop.com/item/{web_slug}"
    
    images = item.get("images", [])
    photo_url = images[0].get("original") if images else None

    embed = {
        "title": f"🚨 Nuovo annuncio: {title}",
        "url": item_url,
        "color": 3066993,
        "fields": [
            {
                "name": "💰 Prezzo",
                "value": f"{price} {currency}",
                "inline": True
            },
            {
                "name": "🔍 Ricerca",
                "value": SEARCH_KEYWORD,
                "inline": True
            }
        ],
        "footer": {
            "text": "Wallapop Alert Bot"
        }
    }

    if photo_url:
        embed["image"] = {"url": photo_url}

    payload = {
        "content": "@everyone Un nuovo articolo è stato appena pubblicato!",
        "embeds": [embed]
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"Errore invio Discord: {response.status_code}, {response.text}")

def check_wallapop(page):
    seen_items = load_seen_items()
    
    search_url = f"https://it.wallapop.com/app/search?keywords={SEARCH_KEYWORD}&max_publication_date=any&max_sale_price={MAX_PRICE}&order_by=newest"
    
    try:
        api_data = []

        def handle_response(response):
            if "search" in response.url and response.status == 200:
                try:
                    data = response.json()
                    if "search_objects" in data:
                        api_data.extend(data["search_objects"])
                except Exception:
                    pass

        page.on("response", handle_response)
        # Carica la pagina senza attendere l'infinita rete idle
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        page.remove_listener("response", handle_response)

        new_found = False
        for item in api_data:
            item_id = item.get("id")
            if item_id and item_id not in seen_items:
                send_discord_alert(item)
                seen_items.add(item_id)
                new_found = True

        if new_found:
            save_seen_items(seen_items)
            print("✨ Nuovi articoli trovati e inviati su Discord!")
        else:
            print("Nessun nuovo annuncio trovato al momento.")

    except Exception as e:
        print(f"Errore durante il caricamento della pagina: {e}")

if __name__ == "__main__":
    print(f"🤖 Avvio controllo singolo per '{SEARCH_KEYWORD}'...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        check_wallapop(page)
        
        browser.close()
