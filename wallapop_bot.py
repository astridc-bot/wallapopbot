import datetime
import json
import os
import cloudscraper

# --- CONFIGURAZIONE ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1521502269118615622/2KQEzJpDBs6db1w8sI5XLXdRn9_A_vTkIG85p55QwNWcPyHl220vmvJ9acj8uMxGqBi8"
SEARCH_KEYWORD = "derhy"
SEEN_ITEMS_FILE = "seen_wallapop_items.json"

def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

def send_discord_webhook(content=None, embed=None):
    payload = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]
    try:
        scraper = cloudscraper.create_scraper()
        scraper.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[{get_current_time()}] Errore invio Discord: {e}", flush=True)

def load_seen_items():
    if os.path.exists(SEEN_ITEMS_FILE):
        try:
            with open(SEEN_ITEMS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_items(seen_set):
    with open(SEEN_ITEMS_FILE, "w") as f:
        json.dump(list(seen_set), f, indent=2)

def send_discord_alert(item):
    title = item.get("title", "Senza titolo")
    price = f"{item.get('price')} €" if item.get('price') else "N/A"
    item_url = item.get("url", "https://it.wallapop.com")
    photo_url = item.get("photo")

    embed = {
        "title": f"🟢 Nuovo articolo Wallapop: {title}",
        "url": item_url,
        "color": 3066993,  # Verde Wallapop
        "fields": [
            {"name": "💰 Prezzo", "value": price, "inline": True},
            {"name": "🔍 Keyword", "value": SEARCH_KEYWORD.capitalize(), "inline": True}
        ],
        "footer": {"text": "Wallapop API Monitor Bot"}
    }

    if photo_url:
        embed["image"] = {"url": photo_url}

    send_discord_webhook(content=f"@everyone Trovato un nuovo articolo per '{SEARCH_KEYWORD}' su Wallapop!", embed=embed)

def get_wallapop_data():
    now = get_current_time()
    print(f"[{now}] 🔍 Avvio scansione Wallapop per keyword: '{SEARCH_KEYWORD}'...", flush=True)

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://it.wallapop.com",
        "Referer": "https://it.wallapop.com/",
        "DeviceOS": "WEB"
    }

    api_url = f"https://api.wallapop.com/api/v3/general/search?keywords={SEARCH_KEYWORD}&order_by=newest"

    try:
        resp = scraper.get(api_url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            raw_items = data.get("search_objects", [])
            filtered_items = []

            for item in raw_items:
                item_id = str(item.get("id", ""))
                title = item.get("title", "")
                price = item.get("price")
                web_path = item.get("web_slug", "")
                
                url = f"https://it.wallapop.com/item/{web_path}" if web_path else f"https://it.wallapop.com/item/{item_id}"
                images = item.get("images", [])
                photo_url = images[0].get("original") if images else None

                filtered_items.append({
                    "id": item_id,
                    "title": title,
                    "price": price,
                    "url": url,
                    "photo": photo_url
                })
                
            print(f"[{now}] ✅ Scansione Wallapop completata. Trovati {len(filtered_items)} articoli.", flush=True)
            return filtered_items

        elif resp.status_code in (403, 406, 429):
            print(f"[{now}] ⚠️ ATTENZIONE: Blocco anti-bot Wallapop! (HTTP {resp.status_code})", flush=True)
            return None
        else:
            print(f"[{now}] ❌ Errore Wallapop HTTP {resp.status_code}", flush=True)
            return None

    except Exception as e:
        print(f"[{now}] ❌ Errore durante la richiesta a Wallapop: {e}", flush=True)
        return None

def main():
    seen_items = load_seen_items()
    items = get_wallapop_data()

    if items is None:
        return

    if not seen_items:
        print(f"[{get_current_time()}] Inizializzazione: salvataggio dei primi {len(items)} articoli...", flush=True)
        for item in items:
            if item.get("id"):
                seen_items.add(item.get("id"))
        save_seen_items(seen_items)
        send_discord_webhook(content=f"🟢 **Wallapop Bot attivo**: Inizializzati {len(seen_items)} articoli per '{SEARCH_KEYWORD}'.")
        return

    new_found = False
    for item in items:
        item_id = item.get("id")
        if item_id and item_id not in seen_items:
            send_discord_alert(item)
            seen_items.add(item_id)
            new_found = True

    if new_found:
        save_seen_items(seen_items)

if __name__ == "__main__":
    main()
