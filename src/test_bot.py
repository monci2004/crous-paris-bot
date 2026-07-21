import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

# Chargement du fichier .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
raw_user_ids = os.getenv("TELEGRAM_USER_IDS", "")
TELEGRAM_USER_IDS = [uid.strip() for uid in raw_user_ids.split(",") if uid.strip()]

async def test_notification():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_IDS:
        print("❌ ERREUR : Clés manquantes dans le fichier .env !")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    print(f"📡 Tentative d'envoi d'un message de test à {len(TELEGRAM_USER_IDS)} destinataire(s)...")

    for user_id in TELEGRAM_USER_IDS:
        try:
            msg = (
                "✅ **TEST BOT CROUS REUSSI !**\n\n"
                "Ce message confirme que ton Token et ton User ID Telegram sont parfaitement configurés.\n"
                "Tu recevras les vraies alertes logement ici !"
            )
            await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
            print(f"✅ Message envoyé avec succès à l'ID : {user_id}")
        except Exception as e:
            print(f"❌ Échec de l'envoi pour l'ID {user_id} : {e}")

if __name__ == "__main__":
    asyncio.run(test_notification())