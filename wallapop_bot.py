import datetime
import json
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import cloudscraper

# --- CONFIGURAZIONE ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1521502269118615622/2KQEzJpDBs6db1w8sI5XLXdRn9_A_vTkIG85p55QwNWcPyHl220vmvJ9acj8uMxGqBi8"
SEARCH_KEYWORD = "derhy"
SEEN_ITEMS_FILE = "seen_wallapop_items.json"
CHECK_INTERVAL_SECONDS = 30  # Frequenza controllo in secondi

# Dummy Server HTTP per l'healthcheck di Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Wallapop API Bot Active & Running!")

    def log_message(self, format, *args):
        return

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

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
        json.dump(list(seen_set), f)

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
        "DeviceOS": "WEB"
    }

    # API pubblica di ricerca di Wallapop
    api_url = f"https://api.wallapop.com/api/v3/general/search?keywords={SEARCH_KEYWORD}&order_by=newest"

    try:
        resp = scraper.get(api_url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            # Gli oggetti cercati sono dentro l'array "search_objects"
            raw_items = data.get("search_objects", [])
            filtered_items = []

            for item in raw_items:
                item_id = str(item.get("id", ""))
                title = item.get("title", "")
                price = item.get("price")
                web_path = item.get("web_slug", "")
                
                # Generiamo l'URL completo del prodotto
                url = f"https://it.wallapop.com/item/{web_path}" if web_path else f"https://it.wallapop.com/item/{item_id}"
                
                # Immagine copertina
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

def check_for_updates(seen_items):
    now = get_current_time()
    items = get_wallapop_data()

    if items is None:
        print(f"[{now}] Scansione interrotta o fallita.", flush=True)
        return seen_items

    # Primo avvio: salviamo gli articoli attualmente online per non spammare
    if not seen_items:
        print(f"[{now}] Inizializzazione Wallapop: salviamo i {len(items)} articoli correnti...", flush=True)
        for item in items:
            item_id = item.get("id")
            if item_id:
                seen_items.add(item_id)
        save_seen_items(seen_items)
        send_discord_webhook(content=f"🟢 **Wallapop Bot attivo**: Salvati {len(seen_items)} articoli correnti per '{SEARCH_KEYWORD}'. In attesa di nuovi annunci!")
        return seen_items

    new_found = False
    for item in items:
        item_id = item.get("id")
        if item_id and item_id not in seen_items:
            send_discord_alert(item)
            seen_items.add(item_id)
            new_found = True
            print(f"[{now}] 🔔 Nuova notifica inviata per item ID: {item_id}", flush=True)

    if new_found:
        save_seen_items(seen_items)
        
    return seen_items

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    seen_items = load_seen_items()
    print(f"[{get_current_time()}] 🚀 Bot Wallapop API avviato. Controllo ogni {CHECK_INTERVAL_SECONDS} secondi...")
    
    while True:
        try:
            seen_items = check_for_updates(seen_items)
        except Exception as e:
            print(f"[{get_current_time()}] ❌ Errore imprevisto nel ciclo: {e}", flush=True)
            
        time.sleep(CHECK_INTERVAL_SECONDS)
