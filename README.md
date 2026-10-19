# 🛍️ Application Web de Gestion de Boutique

**Application de gestion commerciale développée avec Python, FastAPI, Flask et PostgreSQL, puis déployée sur Render.**

## 1. Présentation du projet

Ce projet consiste à concevoir et déployer une application web de gestion de boutique. L'objectif est de proposer une plateforme permettant de gérer les produits, les services, les clients, les commandes et les échanges entre les utilisateurs.

Le projet a été développé progressivement : d'abord en environnement local avec SQL Server, puis adapté à PostgreSQL et déployé sur Internet afin de rendre l'application accessible sans avoir à exécuter le programme sur son propre ordinateur.

### Principales fonctionnalités

- Gestion des produits et des services.
- Gestion des comptes utilisateurs et des rôles : administrateur, vendeur et client.
- Création de comptes et authentification des utilisateurs.
- Gestion du panier et passage des commandes.
- Suivi des commandes et gestion des stocks.
- Gestion des contenus de la page d'accueil.
- Messagerie entre les utilisateurs, avec prise en charge de notifications et de messages audio.
- Gestion des images et autres médias associés aux produits et services.
- Interface d'administration pour les opérations de gestion.

Les fonctionnalités accessibles dépendent du rôle de l'utilisateur connecté.

## 2. Technologies utilisées

| Technologie | Rôle dans le projet |
|---|---|
| Python | Langage de programmation principal |
| FastAPI | Développement de l'API et traitement des opérations métier |
| Flask | Développement de l'interface web |
| HTML | Structure des pages web |
| CSS | Mise en forme et présentation visuelle |
| JavaScript | Interactions dynamiques dans le navigateur |
| SQLAlchemy | Communication entre le code Python et la base de données |
| Pydantic | Validation et structuration des données échangées avec l'API |
| SQL Server | Base de données utilisée au début du développement local |
| PostgreSQL | Base de données utilisée pour le déploiement |
| Git | Gestion de l'historique des modifications du code |
| GitHub | Hébergement du dépôt de code source |
| Render | Hébergement de l'API, de l'interface et de la base PostgreSQL |
| Cloudinary | Stockage distant des images et autres médias |

### 2.1. Python

Python est le langage principal utilisé pour développer la logique de l'application. Il permet notamment de gérer les utilisateurs, les commandes, les produits, les échanges avec la base de données et les requêtes HTTP.

### 2.2. FastAPI

FastAPI constitue la couche backend de l'application. Il expose des points d'accès HTTP, appelés *endpoints*, permettant de consulter, créer, modifier ou supprimer les données.

Par exemple, lorsqu'un client passe une commande, l'interface Flask transmet les informations à l'API. FastAPI vérifie les données, applique les règles de gestion et communique avec la base de données.

La documentation interactive de l'API est accessible à l'adresse suivante :

- En local : http://127.0.0.1:8000/docs
- En production : https://bdd-fastapi.onrender.com/docs

### 2.3. Flask

Flask gère l'interface web visible par l'utilisateur. Il reçoit les requêtes du navigateur, prépare les pages HTML, transmet les opérations nécessaires à l'API et affiche les résultats.

Flask et FastAPI sont deux applications distinctes dans ce projet. Flask ne remplace pas FastAPI : chacun possède un rôle spécifique.

### 2.4. HTML, CSS et JavaScript

Ces trois technologies constituent la partie visible et interactive du site :

- **HTML** organise les éléments des pages : formulaires, tableaux, boutons, images et textes.
- **CSS** définit l'apparence : couleurs, espacements, disposition et adaptation visuelle.
- **JavaScript** gère les interactions côté navigateur, comme l'ouverture de fenêtres de modification, l'aperçu des images et certaines mises à jour dynamiques.

### 2.5. SQLAlchemy et Pydantic

SQLAlchemy est un ORM (*Object-Relational Mapping*). Il permet de représenter les tables de la base de données par des classes Python et d'effectuer des opérations sur les données sans écrire systématiquement des requêtes SQL manuelles.

Pydantic sert à valider et structurer les données reçues ou renvoyées par l'API. Il permet notamment de contrôler les champs obligatoires, les types de données et certaines contraintes avant leur traitement.

## 3. Architecture générale de l'application

Le dépôt est organisé autour de deux applications principales.

```text
BDD_FASTAPI/
│
├── API/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   └── requirements.txt
│
├── Projet_Boutique/
│   ├── app.py
│   ├── templates/
│   ├── static/
│   └── requirements_flask.txt
│
└── .gitignore
```

Cette représentation présente les principaux fichiers connus du projet. Elle ne constitue pas nécessairement une liste exhaustive de tous les fichiers présents dans chaque dossier.

### 3.1. Le fonctionnement général

L'architecture repose sur plusieurs composants complémentaires :

1. Le navigateur affiche l'interface de la boutique.
2. L'application Flask traite les requêtes destinées aux pages web.
3. Flask communique avec l'API FastAPI lorsqu'une opération métier est nécessaire.
4. FastAPI valide les données, applique les règles de gestion et interagit avec PostgreSQL par l'intermédiaire de SQLAlchemy.
5. Les images et autres médias sont stockés sur Cloudinary lorsque les fonctions d'envoi de médias sont utilisées.
6. Les résultats reviennent vers Flask, puis sont affichés dans le navigateur.

### 3.2. Schéma simplifié des communications

```text
                 UTILISATEUR
                      |
                      v
             Navigateur web
                      |
                      v
             Interface Flask
             (app.py + HTML)
                      |
                      | Requêtes HTTP
                      v
                API FastAPI
                 (main.py)
                      |
             +--------+--------+
             |                 |
             v                 v
        SQLAlchemy         Cloudinary
             |             Images et médias
             v
          PostgreSQL
```

Cloudinary est un service externe de stockage de médias. Il ne remplace pas PostgreSQL : la base conserve les données métier et les références vers les fichiers lorsque le modèle de données est prévu pour cela.

## 4. Rôle des principaux fichiers

### 4.1. `API/main.py`

C'est le point d'entrée principal de l'application FastAPI.

Il regroupe notamment les routes HTTP, c'est-à-dire les fonctions qui répondent aux requêtes envoyées à l'API.

Ses responsabilités comprennent, selon les fonctionnalités concernées :

- La gestion des utilisateurs et de l'authentification.
- La gestion des produits et des services.
- Le traitement des commandes et des opérations liées au stock.
- La gestion des messages et des notifications.
- La gestion des contenus de la page d'accueil.
- La réception et le traitement des fichiers envoyés à l'API.
- La configuration de certains éléments nécessaires au fonctionnement de l'API, notamment les échanges entre l'interface et le backend.

Une route associe généralement une méthode HTTP et une URL. Par exemple, une requête `GET` sert habituellement à consulter des données, tandis que `POST` sert à transmettre de nouvelles données.

### 4.2. `Projet_Boutique/app.py`

Ce fichier constitue le point d'entrée de l'interface Flask.

Il gère notamment :

- Les routes des pages web.
- Le rendu des templates HTML.
- Les formulaires soumis par les utilisateurs.
- Les appels HTTP vers FastAPI.
- Les sessions et certaines informations nécessaires à la navigation.
- La récupération et l'affichage des réponses de l'API.

Il joue donc le rôle d'intermédiaire entre le navigateur et le backend.

### 4.3. `API/models.py`

Ce fichier contient les modèles SQLAlchemy qui représentent les entités stockées dans la base de données.

Un modèle décrit généralement une table et ses colonnes. Il peut également définir des relations avec d'autres modèles.

Les entités du projet comprennent notamment les utilisateurs, les clients, les produits, les services, les commandes et les messages.

Par exemple, un modèle `Produit` peut représenter les informations d'un produit : son identifiant, son nom, son prix et les autres champs définis dans le code.

**À retenir :** les modèles décrivent la structure des données côté Python et leur correspondance avec les tables de la base.

### 4.4. `API/schemas.py`

Ce fichier contient les schémas Pydantic utilisés pour valider et structurer les données échangées avec l'API.

Un modèle SQLAlchemy et un schéma Pydantic ne remplissent pas exactement le même rôle :

- Le modèle SQLAlchemy décrit la représentation des données persistées dans la base.
- Le schéma Pydantic décrit la forme attendue des données reçues ou renvoyées par l'API.

Par exemple, un schéma de création de produit peut imposer la présence du nom et du prix avant que l'API ne tente d'enregistrer le produit.

Cette séparation facilite la validation et évite de confondre les données envoyées par un utilisateur avec la représentation complète d'un enregistrement en base.

### 4.5. `API/database.py`

Ce fichier centralise la configuration de la connexion à la base de données.

Il définit notamment les éléments nécessaires à SQLAlchemy pour se connecter au système de gestion de base de données et fournir des sessions aux opérations qui en ont besoin.

Dans le projet, la configuration a été adaptée pour distinguer l'environnement local de l'environnement de production :

- En local, la connexion peut utiliser SQL Server.
- Sur Render, la variable d'environnement `DATABASE_URL` permet de configurer la connexion à PostgreSQL.

La fonction de dépendance `get_db()`, lorsqu'elle est utilisée par les routes, permet de fournir une session de base de données aux opérations concernées.

### 4.6. Le dossier `Projet_Boutique/templates/`

Ce dossier contient les templates HTML rendus par Flask.

Chaque template correspond à une page ou à une partie de l'interface. Il peut contenir du HTML, des expressions Jinja et des instructions de présentation de données.

Par exemple :

- `services.html` : affichage et gestion des services.
- `accueil.html` : page d'accueil.
- `produits.html` : affichage et gestion des produits.

Les noms exacts et les responsabilités des autres templates doivent être vérifiés directement dans le dépôt.

Les templates utilisent la syntaxe Jinja, qui permet notamment d'afficher les valeurs transmises par Flask et de parcourir des listes de données.

### 4.7. Le dossier `Projet_Boutique/static/`

Ce dossier contient les ressources statiques utilisées par l'interface : feuilles de style CSS, fichiers JavaScript, icônes et autres ressources locales.

Les fichiers statiques ne sont pas la même chose que les médias téléversés par les utilisateurs. En production, les images et vidéos téléversées sont destinées à être conservées sur Cloudinary plutôt que dépendre uniquement du disque local du serveur.

### 4.8. Les fichiers `requirements.txt` et `requirements_flask.txt`

Ces fichiers listent les bibliothèques Python nécessaires aux applications.

- `API/requirements.txt` sert à installer les dépendances du backend.
- `Projet_Boutique/requirements_flask.txt` sert à installer celles de l'interface Flask.

Cette séparation permet de gérer les dépendances de chaque service indépendamment.

### 4.9. Le fichier `.gitignore`

Ce fichier indique à Git les fichiers ou dossiers qu'il ne doit pas suivre.

Il sert notamment à éviter d'envoyer des fichiers temporaires, des caches Python, certains fichiers locaux ou des informations de configuration confidentielles.

Les secrets, mots de passe et clés d'API ne doivent pas être enregistrés dans le dépôt GitHub.

## 5. Comprendre les connexions entre les composants

### 5.1. Connexion entre Flask et FastAPI

Flask et FastAPI communiquent par HTTP.

L'interface Flask utilise une URL de l'API, configurée selon l'environnement, pour envoyer les requêtes nécessaires.

En local, l'API est accessible à l'adresse :

`http://127.0.0.1:8000`

L'interface Flask est accessible à l'adresse :

`http://127.0.0.1:5000`

En production, l'interface utilise l'adresse publique de l'API :

`https://bdd-fastapi.onrender.com`

Cette séparation permet de modifier l'interface sans devoir réunir tout le code dans l'application FastAPI.

### 5.2. Connexion entre FastAPI et la base de données

FastAPI utilise SQLAlchemy pour communiquer avec la base.

Le fonctionnement est le suivant :

1. Une requête arrive sur une route FastAPI.
2. L'API valide les données nécessaires.
3. Une session SQLAlchemy est obtenue.
4. L'application effectue les opérations de lecture ou d'écriture.
5. La transaction est validée ou annulée selon le résultat de l'opération.
6. L'API renvoie une réponse HTTP.

Cette organisation centralise l'accès aux données et facilite leur gestion.

### 5.3. Connexion avec Cloudinary

Lorsqu'un utilisateur envoie une image, le fichier est transmis à l'application qui gère le téléversement. Lorsque le traitement Cloudinary est configuré et activé, l'application envoie le fichier au service distant.

Cloudinary conserve le média et fournit une URL permettant de le retrouver.

L'application peut ensuite enregistrer cette URL dans la base de données et la réutiliser pour afficher l'image.

Le processus peut être représenté ainsi :

```text
Utilisateur
    |
    v
Interface Flask
    |
    v
API FastAPI
    |
    v
Cloudinary -----> URL du média
                       |
                       v
                  PostgreSQL
                       |
                       v
                Affichage du média
```

Le parcours exact dépend de la route de téléversement utilisée. Le principe essentiel est que le fichier lui-même est stocké à distance et que sa référence peut être conservée dans la base.

## 6. Pourquoi passer de SQL Server à PostgreSQL ?

### 6.1. La première étape : SQL Server en local

Au début du projet, SQL Server était utilisé pour stocker les données de la boutique sur l'environnement local.

Ce choix permettait de développer et de tester les fonctionnalités sur l'ordinateur de développement, en s'appuyant sur une base de données relationnelle.

La connexion locale utilisait notamment le pilote Python `pyodbc` et l'authentification Windows lorsque cette configuration était activée.

### 6.2. Le besoin de déployer l'application

L'objectif a ensuite évolué : il ne suffisait plus que l'application fonctionne sur un ordinateur. Il fallait la rendre accessible sur Internet à travers des adresses publiques.

Pour cela, il fallait disposer d'une base de données accessible depuis les serveurs d'hébergement, avec une configuration adaptée à la production.

### 6.3. Pourquoi PostgreSQL ?

PostgreSQL a été retenu pour la base hébergée sur Render.

Ce choix répondait à plusieurs besoins :

- Disposer d'une base de données distante, accessible par les services déployés.
- Séparer la base de production du poste de développement.
- Configurer la connexion à l'aide d'une variable d'environnement.
- Utiliser un système relationnel compatible avec SQLAlchemy.
- Éviter que le fonctionnement du site en production dépende directement de SQL Server installé sur l'ordinateur du développeur.

SQL Server et PostgreSQL sont tous deux des systèmes relationnels, mais ils ne sont pas identiques. Ils peuvent différer dans leurs types de données, certaines fonctions SQL, la gestion des identifiants et plusieurs détails de syntaxe.

La migration nécessitait donc de vérifier que les modèles, les requêtes, les connexions et les données fonctionnaient correctement avec PostgreSQL.

### 6.4. Comment la connexion a-t-elle été adaptée ?

Le principe retenu est de configurer la connexion selon l'environnement.

En production, la variable `DATABASE_URL` fournit l'adresse de connexion à PostgreSQL. En local, le code peut conserver la configuration SQL Server prévue pour le développement.

Le comportement exact dépend de la logique présente dans `API/database.py`.

**Important :** le fait d'utiliser SQLAlchemy facilite le changement de système de base de données, mais ne garantit pas à lui seul une migration sans adaptation. Les identifiants, les contraintes, les requêtes spécifiques et les données doivent être contrôlés.

## 7. Pourquoi utiliser Git et GitHub ?

Git est un outil de gestion de versions. Il permet de suivre les modifications du code, de créer des commits et de revenir sur des versions précédentes.

GitHub héberge le dépôt distant du projet.

Le dépôt est disponible ici :

https://github.com/ILLY767/BDD_FASTAPI

Le processus de travail est le suivant :

1. Modifier les fichiers en local.
2. Vérifier les changements avec `git status`.
3. Ajouter les fichiers concernés avec `git add`.
4. Enregistrer un commit avec `git commit`.
5. Envoyer les commits sur GitHub avec `git push`.

GitHub sert également de source de code aux services Render configurés pour déployer le projet depuis le dépôt.

Les variables secrètes et les fichiers contenant des mots de passe ne doivent pas être ajoutés au dépôt.

## 8. Rôle de Render

Render est la plateforme d'hébergement utilisée pour rendre l'application accessible sur Internet.

Le projet utilise trois services logiquement distincts :

| Service | Fonction |
|---|---|
| `BDD_FASTAPI` | Hébergement du backend FastAPI |
| `boutique-interface` | Hébergement de l'interface Flask |
| `boutique-db` | Hébergement de la base PostgreSQL |

### 8.1. Hébergement de l'API

Le service `BDD_FASTAPI` exécute l'application FastAPI et expose ses routes sur une adresse publique.

URL :

https://bdd-fastapi.onrender.com

### 8.2. Hébergement de l'interface

Le service `boutique-interface` exécute l'application Flask. Il sert les pages HTML et communique avec l'API pour effectuer les opérations métier.

URL :

https://boutique-interface.onrender.com

### 8.3. Hébergement de PostgreSQL

Le service `boutique-db` fournit la base PostgreSQL distante utilisée par l'application déployée.

Cela évite que les données de production soient uniquement présentes sur l'ordinateur du développeur.

Les paramètres de connexion sont gérés dans la configuration du service, sans être inscrits en clair dans le code source.

### 8.4. Pourquoi séparer les services ?

Cette séparation permet :

- De déployer l'interface indépendamment de l'API.
- De configurer séparément les dépendances et les commandes de démarrage.
- De diagnostiquer plus facilement les erreurs.
- De maintenir une base de données distincte des fichiers du code.
- De faire évoluer un composant sans nécessairement redéployer les autres.

Sur une offre gratuite, certains services peuvent être mis en veille ou soumis à des limites de ressources. Le premier chargement peut donc être plus lent, et la disponibilité de la base dépend des conditions de l'offre utilisée.

## 9. Rôle de Cloudinary

Cloudinary est un service externe de gestion et de stockage de médias.

Il est utilisé pour conserver les fichiers téléversés dans le cadre de la boutique, notamment les images des produits et services ainsi que les autres médias pris en charge par les routes de l'application.

### 9.1. Pourquoi ne pas stocker tous les médias uniquement sur Render ?

Le disque local de certains environnements d'hébergement peut être éphémère. Les fichiers enregistrés localement risquent alors de ne pas être conservés après un redéploiement, un remplacement d'instance ou certaines opérations de maintenance.

Cloudinary permet de conserver les médias indépendamment du système de fichiers de l'application.

### 9.2. Fonctionnement

1. L'utilisateur sélectionne un fichier dans un formulaire.
2. Le fichier est envoyé à l'application.
3. L'API traite le téléversement et l'envoie à Cloudinary lorsque la configuration est active.
4. Cloudinary conserve le média et renvoie une URL.
5. L'application conserve cette référence dans les données concernées.
6. Le navigateur utilise l'URL pour afficher le média.

### 9.3. Configuration

La configuration peut utiliser `CLOUDINARY_URL` ou les paramètres séparés suivants, selon la logique de l'application :

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Les noms exacts des variables doivent correspondre à ceux lus par le code déployé.

Ces valeurs doivent être configurées dans les variables d'environnement du service concerné sur Render. **La clé secrète Cloudinary ne doit jamais être publiée dans le README ni dans le dépôt GitHub.**

Cloudinary stocke les médias ; PostgreSQL conserve les données métier et les références nécessaires à leur utilisation.

## 10. Étapes du déploiement

Cette section présente la démarche suivie pour rendre l'application accessible en ligne.

### Étape 1 : préparer le projet

Avant le déploiement, il faut vérifier que le projet fonctionne en local et que les fichiers nécessaires sont présents :

- Le backend FastAPI dans `API/`.
- L'interface Flask dans `Projet_Boutique/`.
- Les fichiers de dépendances de chaque application.
- Les templates HTML et les ressources statiques.
- La configuration de connexion à la base de données.
- Les paramètres nécessaires à l'authentification et aux médias.

Il est également nécessaire de vérifier que les fichiers sont correctement suivis par Git, notamment les templates dont la casse du nom de dossier doit correspondre à celle du système de production.

### Étape 2 : préparer le dépôt GitHub

Le code est versionné localement, puis envoyé sur GitHub.

Commandes habituelles :

```powershell
git status
git add <fichier-ou-dossier>
git commit -m "Description de la modification"
git push origin main
```

La branche `main` constitue la branche de référence utilisée dans le workflow du projet.

### Étape 3 : créer la base PostgreSQL sur Render

Il faut créer une base PostgreSQL sur Render, puis récupérer les paramètres de connexion destinés au service backend.

La variable `DATABASE_URL` doit pointer vers cette base dans l'environnement de production.

Il faut ensuite vérifier que les tables, les relations, les identifiants et les données nécessaires sont présents. La création de la base PostgreSQL ne signifie pas automatiquement que toutes les tables SQL Server et leurs données ont été transférées.

### Étape 4 : déployer l'API FastAPI

Créer ou configurer le service Render correspondant au backend, à partir du dépôt GitHub.

Les paramètres essentiels sont :

- **Répertoire du service :** `API`
- **Fichier principal :** `main.py`
- **Dépendances :** `requirements.txt`
- **Commande de démarrage utilisée :**

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

La commande doit être exécutée depuis le répertoire `API`. Si le service utilise une autre commande dans sa configuration actuelle, c'est cette configuration qui doit être conservée.

Configurer ensuite les variables d'environnement nécessaires, notamment la connexion PostgreSQL, les paramètres de sécurité et les éventuelles variables Cloudinary.

Après le déploiement, vérifier que l'API répond correctement :

https://bdd-fastapi.onrender.com/docs

### Étape 5 : déployer l'interface Flask

Créer ou configurer un deuxième service Render pour l'interface web.

Les paramètres utilisés dans le projet sont :

- **Répertoire du service :** `Projet_Boutique`
- **Fichier principal :** `app.py`
- **Dépendances :** `requirements_flask.txt`
- **Commande de démarrage utilisée :**

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

La variable qui définit l'adresse de l'API doit pointer vers l'adresse publique du backend. Elle ne doit pas conserver une adresse locale telle que `http://127.0.0.1:8000` en production.

Le nom exact de cette variable dépend de la configuration du code Flask. Dans le projet, `API_URL` et `API_PUBLIC_URL` ont notamment été utilisés dans la logique de configuration.

Une fois le déploiement terminé, ouvrir :

https://boutique-interface.onrender.com

### Étape 6 : configurer les variables d'environnement

Les variables d'environnement permettent de séparer la configuration du code source.

Les principales catégories de paramètres sont :

| Variable ou catégorie | Utilité |
|---|---|
| `DATABASE_URL` | Connexion à PostgreSQL |
| `API_URL` / `API_PUBLIC_URL` | Adresse de l'API utilisée par l'interface, selon la logique du code |
| `FRONTEND_URL` | Adresse publique de l'interface, notamment pour la configuration des échanges entre origines |
| `CLOUDINARY_URL` ou paramètres séparés | Accès au service Cloudinary |
| Clés et secrets d'authentification | Protection des mécanismes de connexion, selon la configuration de l'application |

Il faut consulter les fichiers de configuration pour confirmer les variables réellement lues par chaque service. Les noms ci-dessus ne signifient pas que toutes ces variables sont obligatoires dans toutes les applications.

Les valeurs doivent être renseignées dans les paramètres du service Render correspondant, sans les inscrire dans les fichiers publics.

### Étape 7 : vérifier les communications

Après le déploiement, il faut s'assurer que :

- L'interface Flask est accessible.
- L'API FastAPI répond.
- Flask utilise l'URL publique de l'API.
- L'API peut accéder à PostgreSQL.
- Les paramètres CORS, lorsque nécessaires, autorisent les échanges entre l'interface et l'API.
- Les médias téléversés sur Cloudinary sont accessibles.
- Les routes de l'application renvoient les réponses attendues.

Une API accessible ne garantit pas, à elle seule, que l'ensemble des fonctionnalités de l'interface fonctionne. Les communications entre les trois services doivent être testées.

### Étape 8 : effectuer les tests fonctionnels

Les tests de validation doivent couvrir les principales fonctionnalités :

- Création de compte et connexion.
- Gestion des produits et des services.
- Affichage des images.
- Ajout d'articles au panier.
- Passage et consultation des commandes.
- Mise à jour des stocks.
- Messagerie et notifications.
- Accès aux fonctionnalités selon les rôles.
- Téléversement et récupération des médias.

Les tests doivent être réalisés sur la version réellement déployée, et pas seulement en local.

### Étape 9 : maintenir l'application

Pour mettre à jour l'application :

1. Modifier et tester le code en local.
2. Enregistrer les modifications avec Git.
3. Envoyer les commits sur GitHub.
4. Laisser Render effectuer le déploiement automatique si cette option est activée, ou lancer le déploiement manuellement.
5. Consulter les journaux du service en cas d'erreur.
6. Tester à nouveau les fonctionnalités importantes.

Le déploiement ne dispense pas de surveiller la base de données, les erreurs, les dépendances et les paramètres de sécurité.

## 11. Exécution de l'application en local

Le développement local permet de modifier le code et de tester les fonctionnalités avant de les publier.

### Prérequis

- Python installé.
- Git installé.
- Les dépendances du backend et de l'interface.
- Une base de données locale correctement configurée ou une connexion à la base distante autorisée.
- Les paramètres nécessaires aux fonctionnalités utilisées.

### 11.1. Lancer l'API

Dans un premier terminal PowerShell :

```powershell
cd "C:\Users\ANSD\Desktop\Actualité\Base_donnée\BDD_FASTAPI\API"
python -m uvicorn main:app --reload --port 8000
```

Cette commande lance FastAPI en mode développement.

### 11.2. Lancer l'interface Flask

Dans un deuxième terminal :

```powershell
cd "C:\Users\ANSD\Desktop\Actualité\Base_donnée\BDD_FASTAPI\Projet_Boutique"
python app.py
```

Cette commande suppose que `app.py` contient bien le point d'entrée permettant de lancer Flask.

### 11.3. Accéder aux applications

- Interface web : http://127.0.0.1:5000
- Documentation FastAPI : http://127.0.0.1:8000/docs

**Attention :** le fonctionnement local dépend de la configuration effective de la base de données. Si l'application utilise PostgreSQL sur Render, une connexion Internet et les autorisations correspondantes peuvent être nécessaires.

## 12. Sécurité et bonnes pratiques

Les précautions suivantes sont importantes pour une application accessible sur Internet :

- Ne jamais publier les mots de passe, clés API ou secrets d'authentification.
- Utiliser les variables d'environnement pour les paramètres confidentiels.
- Vérifier les droits associés aux rôles administrateur, vendeur et client.
- Valider les données reçues avant de les enregistrer.
- Contrôler les fichiers téléversés et les opérations qui les manipulent.
- Vérifier les règles d'accès aux routes sensibles.
- Conserver des sauvegardes de la base de données selon les besoins du projet.
- Contrôler les journaux Render pour détecter les erreurs.
- Vérifier régulièrement les dépendances et les paramètres de déploiement.

## 13. Difficultés rencontrées et solutions apportées

Le développement et le déploiement ont nécessité plusieurs adaptations.

### 13.1. Passage de l'environnement local à la production

Le projet fonctionnait initialement avec une base SQL Server locale. Le déploiement a conduit à adapter la configuration de connexion afin de pouvoir utiliser PostgreSQL sur Render.

### 13.2. Séparation de l'interface et du backend

L'application a été organisée en deux services : FastAPI pour les opérations métier et Flask pour l'interface web. Cette séparation nécessite une configuration correcte des URL et des communications entre les services.

### 13.3. Gestion des fichiers médias

Le stockage local des fichiers n'était pas une solution suffisamment fiable pour la production. Cloudinary a donc été intégré pour conserver les médias à distance.

### 13.4. Gestion des templates

Les fichiers HTML doivent se trouver dans le répertoire attendu par Flask. La casse du nom du dossier est importante en production, car les systèmes Linux distinguent les majuscules et les minuscules.

### 13.5. Diagnostic des erreurs en production

Les journaux Render permettent d'identifier les problèmes de démarrage, de connexion à la base, de configuration des variables d'environnement ou de communication entre services.

## 14. Liens du projet

- **Dépôt GitHub :** https://github.com/ILLY767/BDD_FASTAPI
- **Interface de la boutique :** https://boutique-interface.onrender.com
- **API FastAPI :** https://bdd-fastapi.onrender.com
- **Documentation interactive de l'API :** https://bdd-fastapi.onrender.com/docs

## 15. Conclusion

Ce projet illustre la conception d'une application web structurée en plusieurs composants complémentaires.

FastAPI assure le traitement des opérations métier, Flask gère l'interface utilisateur, SQLAlchemy facilite les interactions avec la base de données, PostgreSQL conserve les données en production, Git et GitHub assurent le suivi du code source, Render héberge les services et Cloudinary permet de conserver les médias à distance.

L'un des principaux enseignements du projet est que le développement d'une application ne s'arrête pas à la programmation de ses fonctionnalités. Il faut également organiser le code, gérer les connexions, adapter l'environnement de production, sécuriser la configuration et tester les communications entre les différents services.

Cette documentation constitue une présentation de l'architecture et du processus de réalisation de la boutique. Les commandes, noms de variables et détails de configuration doivent rester cohérents avec les versions effectivement présentes dans le dépôt.
