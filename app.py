import os
import requests
import logging
import csv
from datetime import datetime
from dotenv import load_dotenv
import asyncio
import json
from fastapi import FastAPI, BackgroundTasks, Response
import uvicorn
import threading
import time

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

# Configuration des API
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialisation de l'application FastAPI
app = FastAPI(title="BCReader Telegram Bot")

# Configuration de l'API Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Variable globale pour stocker le dernier ID traité
last_processed_id = 0

# Verrou pour éviter les problèmes de concurrence
id_lock = threading.Lock()

async def fetch_api_data():
    """Récupère les données de l'API BCReader"""
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }
    
    try:
        response = requests.get(f"{API_URL}/api/config/addresses", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API: {e}")
        return {"error": str(e)}

def extract_data_for_csv(data):
    """Extrait les données pertinentes pour le CSV (id, address, issuer)"""
    csv_data = []
    
    # Vérification si les données sont une liste d'objets (comme dans la réponse de l'API)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and all(k in item for k in ["id", "address"]):
                csv_data.append({
                    "id": item["id"],
                    "address": item["address"],
                    "issuer": item.get("issuer", "")
                })
    # Si les données sont un dictionnaire
    elif isinstance(data, dict) and not "error" in data:
        # Si les données sont dans une propriété 'items' ou similaire
        if "items" in data and isinstance(data["items"], list):
            for item in data["items"]:
                if all(k in item for k in ["id", "address"]):
                    csv_data.append({
                        "id": item["id"],
                        "address": item["address"],
                        "issuer": item.get("issuer", "")
                    })
        # Si les données sont un objet avec des propriétés
        else:
            for key, value in data.items():
                if isinstance(value, dict) and all(k in value for k in ["id", "address"]):
                    csv_data.append({
                        "id": value["id"],
                        "address": value["address"],
                        "issuer": value.get("issuer", "")
                    })
                elif isinstance(value, dict) and "address" in value:
                    # Cas où l'ID est la clé et les autres infos sont dans la valeur
                    csv_data.append({
                        "id": key,
                        "address": value.get("address", ""),
                        "issuer": value.get("issuer", "")
                    })
    
    return csv_data

def save_to_csv(data, keep_file=False):
    """Sauvegarde les données dans un fichier CSV
    
    Args:
        data: Les données à sauvegarder
        keep_file: Si True, conserve le fichier. Si False, le fichier sera temporaire.
        
    Returns:
        Le chemin du fichier CSV créé
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bcreader_data_{timestamp}.csv"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['id', 'address', 'issuer']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for item in data:
                writer.writerow(item)
        
        logger.info(f"Données sauvegardées dans {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du CSV: {e}")
        return None

def delete_csv_file(filepath):
    """Supprime un fichier CSV"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Fichier supprimé: {filepath}")
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du fichier: {e}")

def format_data(data, min_id=170):
    """Met en forme les données pour l'affichage dans Telegram"""
    try:
        if not data:
            return "❗ Aucune donnée disponible"
        
        # S'assurer que min_id est un entier
        min_id = int(min_id) if min_id is not None else 170
        
        # Filtrer les données pour ne garder que celles avec un ID supérieur à min_id
        filtered_data = [item for item in data if int(item['id']) > min_id]
        
        # Trier les données par ID pour s'assurer qu'elles sont dans l'ordre croissant
        filtered_data.sort(key=lambda x: int(x['id']))
        
        if not filtered_data:
            return "ℹ️ Aucune nouvelle adresse depuis le dernier ID"
            
        message = "📊 *New Safe Deployed* 📊\n\n"
        
        for item in filtered_data:
            message += f"🔹 *ID:* {item['id']}\n"
            message += f"📍 *Adresse:* `{item['address']}`\n"
            message += f"🏢 *Émetteur:* {item['issuer']}\n\n"
        
        logger.info(f"Formatage de {len(filtered_data)} nouvelles adresses avec ID > {min_id}")
        return message
    except Exception as e:
        logger.error(f"Erreur lors du formatage du message Telegram: {e}")
        return f"❗ Erreur de formatage: {str(e)}"

async def send_telegram_message(message):
    """Envoie un message via l'API Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Token du bot Telegram non configuré, impossible d'envoyer le message")
        return False
        
    if not TELEGRAM_CHAT_ID:
        logger.error("ID de chat Telegram non configuré, impossible d'envoyer le message")
        return False
    
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    logger.info(f"Envoi du message Telegram à l'URL: {url}")
    logger.info(f"Données: {data}")
    
    try:
        response = requests.post(url, json=data)
        response_json = response.json()
        
        if response.status_code == 200 and response_json.get('ok'):
            logger.info(f"Message envoyé avec succès sur Telegram au chat {TELEGRAM_CHAT_ID}")
            return True
        else:
            logger.error(f"Erreur Telegram: {response.status_code} - {response_json}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de l'envoi du message Telegram: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                logger.error(f"Détails de l'erreur: {error_detail}")
            except:
                logger.error(f"Contenu de la réponse: {e.response.text}")
        return False

async def process_and_send_data(min_id=None):
    """Récupère les données, les formate et les envoie via Telegram"""
    global last_processed_id
    csv_file = None
    
    try:
        # Si min_id n'est pas spécifié, utiliser le dernier ID traité
        if min_id is None:
            with id_lock:
                min_id = last_processed_id
                logger.info(f"Utilisation du dernier ID traité: {min_id}")
        else:
            logger.info(f"Utilisation de l'ID spécifié: {min_id}")
        
        # Récupération des données
        data = await fetch_api_data()
        if not data:
            logger.error("Aucune donnée reçue de l'API")
            return False
        
        # Extraction des données pour CSV
        csv_data = extract_data_for_csv(data)
        if not csv_data:
            logger.error("Aucune donnée extraite pour le CSV")
            return False
        
        # Sauvegarde des données dans un fichier CSV temporaire
        csv_file = save_to_csv(csv_data, keep_file=False)
        
        # Formatage du message avec filtrage par ID
        message = format_data(csv_data, min_id)
        
        # Envoi du message via Telegram seulement s'il y a de nouvelles données
        if "Aucune nouvelle adresse" not in message:
            # Trouver le plus grand ID dans les données filtrées
            filtered_data = [item for item in csv_data if int(item['id']) > int(min_id)]
            if filtered_data:
                max_id = max([int(item['id']) for item in filtered_data])
                logger.info(f"Nouvel ID maximum détecté: {max_id}")
                
                # Envoyer le message
                success = await send_telegram_message(message)
                
                # Mettre à jour le dernier ID traité seulement si l'envoi a réussi
                if success:
                    with id_lock:
                        last_processed_id = max_id
                    logger.info(f"Dernier ID traité mis à jour: {last_processed_id}")
                
                # Supprimer le fichier CSV temporaire après l'envoi du message
                if csv_file:
                    delete_csv_file(csv_file)
                    
                return success
            else:
                logger.info("Aucune nouvelle adresse après filtrage")
                if csv_file:
                    delete_csv_file(csv_file)
                return True
        else:
            logger.info("Aucune nouvelle adresse à envoyer")
            # Supprimer le fichier CSV temporaire s'il n'y a pas de nouvelles données
            if csv_file:
                delete_csv_file(csv_file)
            return True
    except Exception as e:
        logger.error(f"Erreur lors du traitement et de l'envoi des données: {e}")
        # Supprimer le fichier CSV temporaire en cas d'erreur
        if csv_file:
            delete_csv_file(csv_file)
        return False

@app.get("/")
async def root():
    return {"message": "BCReader Telegram Bot API"}

@app.get("/send-update")
async def send_update(background_tasks: BackgroundTasks, min_id: int = None):
    """Déclenche l'envoi d'une mise à jour via Telegram"""
    # Si min_id n'est pas spécifié, on utilisera le dernier ID traité dans process_and_send_data
    background_tasks.add_task(process_and_send_data, min_id)
    
    if min_id is None:
        with id_lock:
            current_id = last_processed_id
        return {"message": f"Mise à jour en cours d'envoi (adresses avec ID > {current_id})"}    
    else:
        return {"message": f"Mise à jour en cours d'envoi (adresses avec ID > {min_id})"}

@app.get("/get-csv")
async def get_csv():
    """Endpoint pour générer et télécharger un fichier CSV des données actuelles"""
    try:
        # Récupération des données
        data = await fetch_api_data()
        if not data:
            return Response(content="Aucune donnée disponible", media_type="text/plain")
            
        # Extraction des données pour CSV
        csv_data = extract_data_for_csv(data)
        if not csv_data:
            return Response(content="Aucune donnée extraite pour le CSV", media_type="text/plain")
        
        # Génération du CSV avec keep_file=True pour conserver le fichier
        csv_file = save_to_csv(csv_data, keep_file=True)
        
        if not csv_file:
            return Response(content="Impossible de générer le fichier CSV", media_type="text/plain", status_code=500)
        
        # Lecture du contenu du fichier CSV
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Création de la réponse avec le contenu CSV
        response = Response(content=csv_content)
        response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(csv_file)}"
        response.headers["Content-Type"] = "text/csv"
        
        return response
    except Exception as e:
        logger.error(f"Erreur lors de la génération du CSV: {e}")
        return Response(content=f"Erreur: {str(e)}", media_type="text/plain", status_code=500)

def periodic_check():
    """Fonction exécutée périodiquement pour vérifier les nouvelles adresses"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            logger.info("Vérification périodique des nouvelles adresses...")
            loop.run_until_complete(process_and_send_data())
        except Exception as e:
            logger.error(f"Erreur lors de la vérification périodique: {e}")
        
        # Attendre 60 secondes avant la prochaine vérification
        time.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Exécuté au démarrage de l'application"""
    logger.info("Application démarrée")
    
    # Initialiser le dernier ID traité à 173 (pour éviter de renvoyer les entrées déjà annoncées)
    global last_processed_id
    last_processed_id = 173  # Mise à jour pour éviter de renvoyer les entrées déjà annoncées
    logger.info(f"Dernier ID traité initialisé à: {last_processed_id}")
    
    # Démarrer la vérification périodique dans un thread séparé
    thread = threading.Thread(target=periodic_check, daemon=True)
    thread.start()
    logger.info("Vérification périodique démarrée (toutes les 60 secondes)")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
