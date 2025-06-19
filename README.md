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

## Déploiement sur Amazon EC2

1. Connectez-vous à votre instance EC2 via SSH :
   ```
   ssh ec2-user@ec2-35-180-247-109.eu-west-3.compute.amazonaws.com
   ```

2. Installez Docker et Docker Compose si ce n'est pas déjà fait :
   ```
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. Clonez le dépôt Git :
   ```
   git clone https://github.com/NicoCP69/newsafecreated.git
   cd newsafecreated
   ```

4. Créez et configurez le fichier `.env` :
   ```
   nano .env
   ```
   Ajoutez les variables d'environnement nécessaires.

5. Démarrez l'application avec Docker Compose :
   ```
   docker-compose up -d
   ```

6. Vérifiez que l'application fonctionne :
   ```
   docker-compose logs -f
   ```

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
