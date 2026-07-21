import os
import re
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from playwright.async_api import async_playwright
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ------------------------------------------------------------------
# CONFIGURATION ET LOGS
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
raw_user_ids = os.getenv("TELEGRAM_USER_IDS", "")
TELEGRAM_USER_IDS = [uid.strip() for uid in raw_user_ids.split(",") if uid.strip()]

bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

known_logement_ids = set()
is_first_run = True

# ------------------------------------------------------------------
# NOTIFICATIONS TELEGRAM
# ------------------------------------------------------------------
async def notify_users(message: str):
    if not bot:
        logging.error("Impossible d'envoyer la notification : Token Telegram absent.")
        return

    for user_id in TELEGRAM_USER_IDS:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
            logging.info(f"Notification envoyée à {user_id}")
        except Exception as e:
            logging.error(f"Erreur d'envoi Telegram ({user_id}) : {e}")

# ------------------------------------------------------------------
# SURVEILLANCE AVEC PLAYWRIGHT
# ------------------------------------------------------------------
async def check_crous_with_browser(playwright):
    global known_logement_ids, is_first_run

    # Lancement d'un Chrome invisible (headless)
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()

    # URL officielle Île-de-France
    url = (
        "https://trouverunlogement.lescrous.fr/tools/47/search?"
        "bounds=1.4462445_48.1201456_3.5592208_49.241431"
        "&locationName=%C3%8Ele-de-France"
    )

    try:
        # Chargement de la page comme un vrai utilisateur
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Récupération du HTML rendu par le JS
        content = await page.content()
        
        # Extraction des IDs de logements (/housing/123456)
        found_ids = set(re.findall(r'/housing/(\d+)', content))

        logging.info(f"Analyse réussie (Playwright) : {len(found_ids)} logement(s) détecté(s).")

        # Premier lancement
        if is_first_run:
            known_logement_ids = found_ids
            is_first_run = False
            logging.info("✅ Bot initialisé avec succès ! Surveillance active sur Telegram.")
            return

        # Nouveaux logements
        new_ids = found_ids - known_logement_ids

        if new_ids:
            logging.info(f"🚨 {len(new_ids)} nouveau(x) logement(s) détecté(s) !")
            for log_id in new_ids:
                link = f"https://trouverunlogement.lescrous.fr/housing/{log_id}"
                msg = (
                    f"🚨 **NOUVEAU LOGEMENT DISPONIBLE CROUS !** 🚨\n\n"
                    f"📍 **Zone :** Île-de-France\n"
                    f"🔗 [Accéder à l'annonce]({link})"
                )
                await notify_users(msg)

            known_logement_ids.update(new_ids)

    except Exception as e:
        logging.error(f"Erreur lors du chargement de la page : {e}")
    finally:
        await browser.close()

# ------------------------------------------------------------------
# MINI SERVEUR HTTP POUR KEEP-ALIVE SUR RENDER
# ------------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot CROUS is running!")

def start_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Serveur Web de santé démarré sur le port {port}")
    server.serve_forever()

# ------------------------------------------------------------------
# BOUCLE PRINCIPALE AVEC DÉLAI DYNAMIQUE
# ------------------------------------------------------------------
async def main():
    # Lancement du serveur Web dans un thread séparé pour Render
    threading.Thread(target=start_health_check_server, daemon=True).start()

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_IDS:
        logging.critical("Variables d'environnement manquantes dans le fichier .env !")
        return
    
    # ... le reste de ton code main() ...
    # Notification de succès au démarrage
    await notify_users("🚀 Bot CROUS démarré avec succès sur Render !")

    logging.info(f"Lancement du Bot Surveillance CROUS avec Playwright (Destinataires : {len(TELEGRAM_USER_IDS)})")

    async with async_playwright() as playwright:
        while True:
            await check_crous_with_browser(playwright)
            
            # Détermination de l'heure actuelle
            current_hour = datetime.now().hour
            
            # De 07h00 à 21h59 (7h à 22h) -> Pause de 30 secondes
            if 7 <= current_hour < 22:
                sleep_time = 30
            # De 22h00 à 06h59 (22h à 7h) -> Pause de 5 minutes (300 secondes)
            else:
                sleep_time = 300
                
            logging.info(f"Prochaine vérification dans {sleep_time} secondes...")
            await asyncio.sleep(sleep_time)

# Point d'entrée obligatoire pour exécuter le script
if __name__ == "__main__":
    asyncio.run(main())