# BCReader Telegram Bot

Cette application permet de récupérer des données depuis l'API BCReader Testnet et de les envoyer automatiquement via Telegram.

## Configuration

1. Assurez-vous d'avoir Python 3.8+ installé sur votre système.

2. Installez les dépendances :
   ```
   pip install -r requirements.txt
   ```

3. Configurez le fichier `.env` avec vos informations :
   - La clé API BCReader est déjà configurée
   - Ajoutez votre token de bot Telegram (obtenu via [@BotFather](https://t.me/botfather))
   - Ajoutez l'ID de chat Telegram où vous souhaitez recevoir les messages

## Utilisation

### Tester l'API

Pour tester la connexion à l'API BCReader sans utiliser Telegram :

```
python test_api.py
```

### Démarrer le serveur

Pour démarrer le serveur FastAPI :

```
python app.py
```

Le serveur sera accessible à l'adresse http://localhost:8000

### Endpoints disponibles

- `GET /` : Page d'accueil
- `GET /send-update` : Déclenche manuellement l'envoi d'une mise à jour vers Telegram

## Fonctionnalités

- Récupération des données depuis l'API BCReader
- Formatage des données pour une meilleure lisibilité
- Envoi des données formatées via Telegram
- API FastAPI pour déclencher des actions manuellement

## Personnalisation

Vous pouvez modifier le fichier `app.py` pour :
- Changer la fréquence des mises à jour
- Modifier le format des messages
- Ajouter d'autres endpoints API
- Intégrer d'autres fonctionnalités
