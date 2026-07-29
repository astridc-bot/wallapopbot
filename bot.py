import json
import random
import requests

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1521502269118615622/2KQEzJpDBs6db1w8sI5XLXdRn9_A_vTkIG85p55QwNWcPyHl220vmvJ9acj8uMxGqBi8"

SEARCH_KEYWORD = "zanotti"
MAX_PRICE = 500
SEEN_ITEMS_FILE = "seen_items.json"

PROXIES_LIST = [
    "http://51.159.65.67:8888",
    "http://163.172.58.140:8888",
    "http://51.15.242.201:8888",
    "http://51.158.123.35:8888",
    "http://135.125.216.71:8080"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def send_test_ping():
    payload = {
        "content": "🟢 **Test Bot Wallapop**: Lo script è partito ed è operativo su GitHub Actions!"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Errore invio ping test: {e}", flush=True)

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
            {"name": "💰 Prezzo", "value": f"{price} {currency}", "inline": True},
            {"name": "🔍 Ricerca", "value": SEARCH_KEYWORD, "inline": True}
        ],
        "footer": {"text": "Wallapop Alert Bot"}
    }

    if photo_url:
        embed["image"] = {"url": photo_url}

    payload = {
        "content": "@everyone Un nuovo articolo è stato appena pubblicato!",
        "embeds": [embed]
    }

    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def get_wallapop_data():
    api_url = f"https://api.wallapop.com/api/v3/general/search?keywords={SEARCH_KEYWORD}&max_sale_price={MAX_PRICE}&order_by=newest"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-DeviceOS": "WEB",
        "Origin": "https://it.wallapop.com",
        "Referer": "https://it.wallapop.com/"
    }

    try:
        print("🌐 Tentativo di connessione diretta...", flush=True)
        resp = requests.get(api_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("search_objects", [])
    except Exception:
        pass

    print("⚠️ Connessione diretta bloccata. Uso rotazione Proxy...", flush=True)
    random.shuffle(PROXIES_LIST)
    for proxy_url in PROXIES_LIST:
        proxies = {"http": proxy_url, "https": proxy_url}
        try:
            print(f"🔄 Prova con Proxy: {proxy_url}", flush=True)
            resp = requests.get(api_url, headers=headers, proxies=proxies, timeout=6)
            if resp.status_code == 200:
                print("✅ Connessione riuscita via Proxy!", flush=True)
                return resp.json().get("search_objects", [])
        except Exception:
            continue
            
    print("❌ Nessun proxy ha risposto. Wallapop ha respinto la richiesta.", flush=True)
    return []

def main():
    # Invia il messaggio di prova appena parte
    send_test_ping()
    
    seen_items = load_seen_items()
    items = get_wallapop_data()

    new_found = False
    for item in items:
        item_id = item.get("id")
        if item_id and item_id not in seen_items:
            send_discord_alert(item)
            seen_items.add(item_id)
            new_found = True

    if new_found:
        save_seen_items(seen_items)
        print("✨ Nuovi articoli inviati su Discord!", flush=True)
    else:
        print("Nessun nuovo annuncio o dati non disponibili.", flush=True)

if __name__ == "__main__":
    main()
