# BCReader Telegram Bot

Cette application permet de récupérer des données depuis l'API BCReader Testnet et de les envoyer automatiquement via Telegram.

## Configuration

### Installation locale

1. Assurez-vous d'avoir Python 3.8+ installé sur votre système.

2. Installez les dépendances :
   ```
   pip install -r requirements.txt
   ```

3. Configurez le fichier `.env` avec vos informations :
   - La clé API BCReader est déjà configurée
   - Ajoutez votre token de bot Telegram (obtenu via [@BotFather](https://t.me/botfather))
   - Ajoutez l'ID de chat Telegram où vous souhaitez recevoir les messages

### Installation avec Docker

1. Assurez-vous d'avoir Docker et Docker Compose installés sur votre système.

2. Configurez le fichier `.env` avec vos informations comme indiqué ci-dessus.

3. Construisez et démarrez le conteneur :
   ```
   docker-compose up -d
   ```

## Déploiement sur VPS OVH

### Méthode 1 : Déploiement via GitHub

1. Connectez-vous à votre instance VPS via SSH :
   ```
   ssh debian@vps-7461372a.vps.ovh.net
   ```

2. Installez Docker et Docker Compose si ce n'est pas déjà fait :
   ```
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose
   sudo usermod -aG docker debian
   # Déconnectez-vous et reconnectez-vous pour que les changements de groupe prennent effet
   ```

3. Clonez le dépôt Git :
   ```
   mkdir -p ~/newsafebot
   cd ~/newsafebot
   git clone https://github.com/NicoCP69/newsafecreated.git .
   ```

4. Créez et configurez le fichier `.env` :
   ```
   nano .env
   ```
   Ajoutez les variables d'environnement nécessaires :
   ```
   API_KEY=yOhKL6fIFb7VPc13AHMtCuqQD8Tf2Nkn0mc2a4F6fAc=
   API_URL=https://bcreader-testnet.ibex.fi
   # Token du bot Telegram
   TELEGRAM_BOT_TOKEN=7504795839:AAFHvRE6Nvi422IF6ulCFLsVJ0TypbrOnMo
   # ID du groupe Telegram "NewSafeCreated"
   TELEGRAM_CHAT_ID=-1002827453878
   ```

5. Démarrez l'application avec Docker Compose :
   ```
   docker-compose up -d --build
   ```

6. Vérifiez que l'application fonctionne :
   ```
   docker-compose logs -f
   ```

### Méthode 2 : Déploiement direct depuis votre machine locale

1. Créez une archive des fichiers source :
   ```
   cd /chemin/vers/newsafebot
   tar -czf newsafebot_src.tar.gz --exclude="venv" --exclude="__pycache__" --exclude="*.tar" --exclude="*.tar.gz" .
   ```

2. Transférez les fichiers vers le VPS :
   ```
   ssh debian@vps-7461372a.vps.ovh.net "mkdir -p ~/newsafebot"
   scp newsafebot_src.tar.gz debian@vps-7461372a.vps.ovh.net:~/newsafebot/
   ```

3. Connectez-vous au VPS et déployez l'application :
   ```
   ssh debian@vps-7461372a.vps.ovh.net
   cd ~/newsafebot
   tar -xzf newsafebot_src.tar.gz
   docker-compose up -d --build
   ```

### Statut actuel

L'application est actuellement déployée sur VPS OVH et accessible à l'adresse :

http://vps-7461372a.vps.ovh.net:8000

## Utilisation

### Tester l'API

Pour tester la connexion à l'API BCReader sans utiliser Telegram :

```
python test_api.py
```

### Démarrer le serveur (sans Docker)

Pour démarrer le serveur FastAPI :

```
python app.py
```

Le serveur sera accessible à l'adresse http://localhost:8000

### Endpoints disponibles

- `GET /` : Page d'accueil
- `GET /send-update` : Déclenche manuellement l'envoi d'une mise à jour vers Telegram
- `GET /get-csv` : Télécharge un fichier CSV avec les données actuelles

## Fonctionnalités

- Récupération des données depuis l'API BCReader
- Formatage des données pour une meilleure lisibilité
- Envoi des données formatées via Telegram
- Vérification périodique toutes les 60 secondes pour les nouvelles adresses
- Filtrage intelligent pour n'envoyer que les nouvelles adresses
- API FastAPI pour déclencher des actions manuellement

## Personnalisation

Vous pouvez modifier le fichier `app.py` pour :
- Changer la fréquence des mises à jour
- Modifier le format des messages
- Ajouter d'autres endpoints API
- Intégrer d'autres fonctionnalités
