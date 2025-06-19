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
        data = response.json()
        logger.info(f"Données récupérées avec succès depuis l'API, type: {type(data)}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API: {e}")
        return {"error": str(e)}

async def fetch_transactions_data(page=1, limit=20):
    """Récupère les données de transactions depuis l'API BCReader"""
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }
    
    try:
        response = requests.get(f"{API_URL}/api/all-transactions?page={page}&limit={limit}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour les transactions: {e}")
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
        # Vérifier si les adresses sont directement dans une clé 'addresses'
        if "addresses" in data and isinstance(data["addresses"], dict):
            for address_id, address_info in data["addresses"].items():
                if isinstance(address_info, dict) and "address" in address_info:
                    csv_data.append({
                        "id": address_id,
                        "address": address_info["address"],
                        "issuer": address_info.get("issuer", "")
                    })
        # Si les données sont dans une propriété 'items' ou similaire
        elif "items" in data and isinstance(data["items"], list):
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

def format_data(data, min_id=170, max_addresses=10):
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
        
        # Limiter le nombre d'adresses pour éviter les messages trop longs
        if len(filtered_data) > max_addresses:
            logger.info(f"Limitation à {max_addresses} adresses sur {len(filtered_data)} détectées")
            filtered_data = filtered_data[:max_addresses]
            
        message = "📊 New Safe Deployed 📊\n\n"
        
        for item in filtered_data:
            message += f"🔹 ID: {item['id']}\n"
            message += f"📍 Address: {item['address']}\n"
            message += f"🏢 Issuer: {item['issuer']}\n\n"
        
        logger.info(f"Formatage de {len(filtered_data)} nouvelles adresses avec ID > {min_id}")
        return message
    except Exception as e:
        logger.error(f"Erreur lors du formatage du message Telegram: {e}")
        return f"❗ Erreur de formatage: {str(e)}"

def format_transactions(transactions_data, last_tx_hash=None):
    """Met en forme les données de transactions pour l'affichage dans Telegram"""
    try:
        if not transactions_data or "data" not in transactions_data or not transactions_data["data"]:
            return "❗ Aucune transaction disponible"
        
        # Récupérer les transactions
        transactions = transactions_data["data"]
        
        # Filtrer les transactions si un hash de dernière transaction est fourni
        # Note: Comme l'API ne fournit pas de hash de transaction, nous utilisons une combinaison de from+to+value comme identifiant unique
        if last_tx_hash:
            # Trouver l'index de la dernière transaction traitée
            try:
                found = False
                filtered_transactions = []
                
                for tx in transactions:
                    tx_hash = f"{tx['from']}_{tx['to']}_{tx['valueFormatted']}"
                    
                    # Si on trouve la transaction déjà traitée, on marque qu'on l'a trouvée
                    # et on ne l'ajoute pas à la liste filtrée
                    if tx_hash == last_tx_hash:
                        found = True
                        logger.info(f"Transaction déjà traitée trouvée: {tx_hash}")
                        break
                    
                    # On ajoute uniquement les transactions qui n'ont pas encore été traitées
                    filtered_transactions.append(tx)
                
                # Remplacer la liste originale par la liste filtrée
                transactions = filtered_transactions
            except Exception as e:
                logger.error(f"Erreur lors du filtrage des transactions: {e}")
        
        if not transactions:
            return "ℹ️ Aucune nouvelle transaction depuis la dernière vérification"
            
        message = "💰 Nouvelles Transactions 💰\n\n"
        
        for tx in transactions:
            # Vérifier si l'adresse d'origine est l'adresse spéciale
            if tx['from'] == "0x74a9b04c7bab3d3BAd1A0a06589A24A67a6f9127":
                message += f"🎁 *GIFT NEW WALLET* 🎁 💸\n"
            else:
                message += f"🔹 De: {tx['from']}\n"
            message += f"📍 À: {tx['to']}\n"
            message += f"💶 Montant: {tx['valueFormatted']} {tx['tokenSymbol']}\n\n"
        
        logger.info(f"Formatage de {len(transactions)} nouvelles transactions")
        return message
    except Exception as e:
        logger.error(f"Erreur lors du formatage des transactions pour Telegram: {e}")
        return f"❗ Erreur de formatage des transactions: {str(e)}"

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
        
        # Vérification si c'est le premier démarrage après une mise à jour du code
        # On continue le traitement même au premier démarrage pour vérifier les nouvelles adresses
        logger.info("Vérification des nouvelles adresses, même au premier démarrage")
            
        # Récupération des données
        data = await fetch_api_data()
        if not data:
            logger.error("Aucune donnée reçue de l'API")
            return False
        
        # Log pour déboguer la structure des données reçues
        logger.info(f"Structure des données reçues: {type(data)}")
        if isinstance(data, dict):
            logger.info(f"Clés dans les données: {list(data.keys())}")
            if "addresses" in data:
                logger.info(f"Type de 'addresses': {type(data['addresses'])}")
                if isinstance(data['addresses'], dict):
                    logger.info(f"Nombre d'adresses: {len(data['addresses'])}")
                    # Afficher quelques exemples d'adresses
                    sample_keys = list(data['addresses'].keys())[:2]
                    for key in sample_keys:
                        logger.info(f"Exemple d'adresse - Clé: {key}, Valeur: {data['addresses'][key]}")
        
        # Extraction des données pour CSV
        csv_data = extract_data_for_csv(data)
        logger.info(f"Nombre d'adresses extraites pour CSV: {len(csv_data) if csv_data else 0}")
        
        if not csv_data:
            logger.error("Aucune donnée extraite pour le CSV")
            return False
        
        # Afficher quelques exemples d'adresses extraites
        for i, item in enumerate(csv_data[:2]):
            logger.info(f"Exemple d'adresse extraite {i+1}: {item}")
        
        # Sauvegarde des données dans un fichier CSV temporaire
        csv_file = save_to_csv(csv_data, keep_file=False)
        
        # Formatage du message avec filtrage par ID
        message = format_data(csv_data, min_id)
        
        # Envoi du message via Telegram seulement s'il y a de nouvelles données
        if "Aucune nouvelle adresse" not in message:
            # Trouver le plus grand ID dans les données filtrées
            filtered_data = [item for item in csv_data if int(item['id']) > int(min_id)]
            logger.info(f"Nombre d'adresses après filtrage (ID > {min_id}): {len(filtered_data)}")
            
            if filtered_data:
                # Afficher quelques exemples d'adresses filtrées
                for i, item in enumerate(filtered_data[:2]):
                    logger.info(f"Exemple d'adresse filtrée {i+1}: {item}")
                
                max_id = max([int(item['id']) for item in filtered_data])
                logger.info(f"Nouvel ID maximum détecté: {max_id}")
                
                # Envoyer le message
                success = await send_telegram_message(message)
                logger.info(f"Résultat de l'envoi du message: {'Succès' if success else 'Échec'}")
                
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

# Variable globale pour stocker le hash de la dernière transaction traitée
last_transaction_hash = None

# Verrou pour éviter les problèmes de concurrence avec les transactions
tx_lock = threading.Lock()

async def process_and_send_transactions():
    """Récupère les transactions, les formate et les envoie via Telegram"""
    global last_transaction_hash
    
    try:
        # Récupération des données de transactions
        with tx_lock:
            current_last_tx_hash = last_transaction_hash
            
        logger.info(f"Vérification des nouvelles transactions depuis le hash: {current_last_tx_hash}")
        
        # Même au premier démarrage, on vérifie les nouvelles transactions
        logger.info("Vérification des nouvelles transactions, même au premier démarrage")
        
        # Récupération des données
        transactions_data = await fetch_transactions_data(page=1, limit=20)
        if not transactions_data or "error" in transactions_data:
            logger.error("Aucune donnée de transaction reçue de l'API")
            return False
        
        # Formatage du message avec filtrage par hash de transaction
        message = format_transactions(transactions_data, current_last_tx_hash)
        
        # Envoi du message via Telegram seulement s'il y a de nouvelles transactions
        if "Aucune nouvelle transaction" not in message:
            # Envoyer le message
            success = await send_telegram_message(message)
            
            # Mettre à jour le dernier hash de transaction traité seulement si l'envoi a réussi
            if success and transactions_data["data"]:
                # Prendre le hash de la première transaction (la plus récente) comme nouveau dernier hash
                # Les transactions sont généralement triées par ordre chronologique inverse (la plus récente en premier)
                first_tx = transactions_data["data"][0]
                new_tx_hash = f"{first_tx['from']}_{first_tx['to']}_{first_tx['valueFormatted']}"
                
                with tx_lock:
                    last_transaction_hash = new_tx_hash
                logger.info(f"Dernier hash de transaction mis à jour: {last_transaction_hash}")
                logger.info(f"Mémorisé pour éviter les doublons: {len(transactions_data['data'])} transactions traitées")
                
                return success
            else:
                logger.info("Aucune nouvelle transaction après filtrage ou échec d'envoi")
                return False
        else:
            logger.info("Aucune nouvelle transaction à envoyer")
            return True
    except Exception as e:
        logger.error(f"Erreur lors du traitement et de l'envoi des transactions: {e}")
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

@app.get("/send-transactions-update")
async def send_transactions_update(background_tasks: BackgroundTasks):
    """Déclenche l'envoi d'une mise à jour des transactions via Telegram"""
    background_tasks.add_task(process_and_send_transactions)
    
    with tx_lock:
        current_hash = last_transaction_hash
    
    if current_hash:
        return {"message": f"Mise à jour des transactions en cours d'envoi (depuis le hash {current_hash[:15]}...)"}    
    else:
        return {"message": "Première mise à jour des transactions en cours d'envoi"}

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
    """Fonction exécutée périodiquement pour vérifier les nouvelles adresses et transactions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            # Vérification des nouvelles adresses
            logger.info("Vérification périodique des nouvelles adresses...")
            loop.run_until_complete(process_and_send_data())
            
            # Vérification des nouvelles transactions
            logger.info("Vérification périodique des nouvelles transactions...")
            loop.run_until_complete(process_and_send_transactions())
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification périodique: {e}")
        
        # Attendre 60 secondes avant la prochaine vérification
        time.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Exécuté au démarrage de l'application"""
    logger.info("Application démarrée")
    
    # Initialiser le dernier ID traité à une valeur qui permettra de détecter les nouvelles adresses
    global last_processed_id, last_transaction_hash
    last_processed_id = 0  # Valeur basse pour détecter les nouvelles adresses
    logger.info(f"Dernier ID traité initialisé à: {last_processed_id}")
    
    # Initialiser le hash de la dernière transaction à None pour détecter les nouvelles transactions
    last_transaction_hash = None
    logger.info("Hash de la dernière transaction initialisé à None pour détecter les nouvelles transactions")
    
    # Démarrer la vérification périodique dans un thread séparé
    thread = threading.Thread(target=periodic_check, daemon=True)
    thread.start()
    logger.info("Vérification périodique démarrée (toutes les 60 secondes)")
    logger.info("Surveillance des nouvelles adresses ET transactions activée")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
