import os
import requests
import json
import csv
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration des API
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")

def fetch_api_data():
    """Récupère les données de l'API BCReader"""
    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }
    
    try:
        print(f"Envoi de la requête à {API_URL}/api/config/addresses")
        print(f"Avec la clé API: {API_KEY}")
        
        response = requests.get(f"{API_URL}/api/config/addresses", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête API: {e}")
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

def save_to_csv(data, filename="bcreader_data.csv"):
    """Sauvegarde les données dans un fichier CSV"""
    csv_data = extract_data_for_csv(data)
    
    if not csv_data:
        print("Aucune donnée appropriée trouvée pour le CSV")
        return False
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["id", "address", "issuer"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in csv_data:
                writer.writerow(row)
        
        print(f"Données sauvegardées dans {filename}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du CSV: {e}")
        return False

def main():
    print("Test de l'API BCReader...")
    data = fetch_api_data()
    print("\nRéponse de l'API:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Sauvegarde des données dans un CSV
    save_to_csv(data)

if __name__ == "__main__":
    main()
