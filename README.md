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




# Documentation technique — Application de gestion de boutique



Le système distingue trois rôles principaux : **administrateur, vendeur et client**.

## 2. Architecture générale

L'application repose sur trois composants principaux :

1. **Flask** : interface web utilisée par les utilisateurs.
2. **FastAPI** : API qui expose les opérations métier.
3. **SQLAlchemy et la base de données** : couche de persistance des informations.

Les médias peuvent être stockés sur Cloudinary en production. En environnement local, l'application prévoit également un stockage dans les dossiers statiques de l'interface.

### 2.1. Schéma de fonctionnement

```text
                 UTILISATEUR
                      |
                      v
              Navigateur web
                      |
                      v
          +------------------------+
          | Interface Flask        |
          | Projet_Boutique/app.py |
          +------------------------+
             |                  |
             |                  +--------------------+
             |                                       |
             v                                       v
      Sessions Flask                         Templates HTML
      et panier en session                   et fichiers statiques
             |
             | Requêtes HTTP
             | avec authentification
             v
          +------------------------+
          | API FastAPI            |
          | API/main.py            |
          +------------------------+
                      |
                      v
          +------------------------+
          | Couche de données      |
          | SQLAlchemy             |
          +------------------------+
                      |
                      v
               Base de données

          Médias : Cloudinary en production
                   ou fichiers locaux en développement
```

Ce schéma présente les responsabilités générales. Le détail des requêtes SQL, de la gestion des transactions et des dépendances de l'API doit être confirmé dans le code correspondant.

### 2.2. Rôle de Flask

Flask constitue la partie visible de l'application.

Il reçoit les requêtes du navigateur, vérifie certaines conditions d'accès, récupère les données nécessaires auprès de FastAPI et affiche les pages HTML.

Il prend notamment en charge :

- les formulaires de connexion et de création de compte ;
- l'affichage du catalogue ;
- les opérations sur le panier ;
- l'affichage des commandes ;
- les formulaires de gestion ;
- les sessions utilisateurs ;
- l'envoi de messages ;
- la transmission des fichiers multimédias.

Le fichier principal de cette partie est :

`Projet_Boutique/app.py`

### 2.3. Rôle de FastAPI

FastAPI constitue la couche API de l'application.

L'interface Flask lui adresse des requêtes HTTP pour effectuer les opérations sur les données. Les routes Flask ne constituent donc pas nécessairement les opérations finales de la base de données : elles délèguent une grande partie du traitement à l'API.

Les fonctionnalités sollicitées par Flask comprennent notamment :

- l'authentification et la gestion des utilisateurs ;
- la gestion des clients ;
- la consultation et la modification des produits ;
- la gestion des services ;
- la création et la consultation des commandes ;
- la gestion des lignes de commande ;
- les messages et les notifications ;
- les statistiques du tableau de bord ;
- la gestion des photos et des publicités de la page d'accueil.

Le fichier principal de l'API est :

`API/main.py`

### 2.4. Rôle de SQLAlchemy

SQLAlchemy permet de représenter les tables de la base de données sous forme de classes Python.

Chaque modèle définit notamment :

- le nom de la table ;
- ses colonnes ;
- les types de données ;
- les clés primaires ;
- les clés étrangères ;
- certaines contraintes ;
- les valeurs par défaut.

Les modèles transmis dans le projet couvrent les utilisateurs, les clients, les produits, les services, les commandes, les paiements, les messages, les notifications et les contenus multimédias de la page d'accueil.

Le fichier contenant ces modèles doit être identifié dans l'arborescence du projet pour préciser son chemin exact.

---

## 3. Les rôles et les droits d'accès

L'application distingue trois catégories d'utilisateurs.

| Fonctionnalité | Administrateur | Vendeur | Client |
|---|---|---|---|
| Consulter les produits | Oui | Oui | Oui |
| Consulter les services | Oui | Oui | Oui |
| Ajouter et modifier les produits | Oui | Oui | Non |
| Ajouter et modifier les services | Oui | Oui | Non |
| Gérer les clients | Oui | Oui | Non |
| Gérer les commandes de la boutique | Oui | Oui | Non |
| Consulter ses commandes | Selon les routes autorisées | Selon les routes autorisées | Oui |
| Utiliser le panier client | Non prévu par les routes client du panier | Non prévu par les routes client du panier | Oui |
| Gérer les utilisateurs | Oui | Non | Non |
| Administrer les photos et publicités d'accueil | Oui | Non | Non |
| Consulter les statistiques du tableau de bord | Oui | Oui | Accès limité |

**Important :** ce tableau résume les restrictions observées dans les routes Flask. L'API doit également vérifier les droits d'accès pour empêcher un utilisateur de contourner l'interface en appelant directement ses endpoints.

Les restrictions ne sont pas nécessairement identiques pour toutes les routes. Certaines opérations contrôlent le rôle dans Flask, tandis que d'autres reposent aussi sur les vérifications de FastAPI.

---

## 4. Authentification et gestion des sessions

### 4.1. Connexion

Lorsqu'un utilisateur se connecte :

1. Il ouvre la page de connexion.
2. Il soumet son adresse électronique et son mot de passe.
3. Flask transmet les identifiants à l'API, via la route `/login`.
4. Si l'authentification réussit, Flask récupère les informations du compte et le jeton d'accès.
5. Flask enregistre notamment dans sa session l'identifiant de l'utilisateur, son nom, son adresse électronique, son rôle et son jeton d'accès.
6. L'utilisateur est redirigé vers son espace de navigation.

Le jeton permet à Flask de s'authentifier auprès des routes protégées de l'API.

### 4.2. Appels authentifiés à l'API

Les fonctions utilitaires de `app.py` centralisent les appels HTTP.

Elles permettent notamment de :

- construire les URL de l'API ;
- transmettre le jeton d'accès dans l'en-tête d'autorisation ;
- gérer les délais d'attente ;
- effectuer des requêtes GET, POST, PUT et DELETE ;
- traiter les réponses d'erreur ;
- détecter certains cas d'expiration de session.

Lorsqu'une réponse indique une session expirée selon les conditions prévues par le code, Flask efface les informations de session concernées et redirige l'utilisateur vers la connexion.

### 4.3. Création de compte et profil

La route `/creer-compte` permet à un nouvel utilisateur de soumettre un formulaire d'inscription. Flask vérifie notamment la confirmation du mot de passe avant de transmettre les informations à l'API.

La route `/mon-compte` permet de consulter les informations du compte. D'autres routes permettent de modifier le profil et le mot de passe.

La création de comptes avec attribution de rôles est également disponible dans l'espace d'administration.

### 4.4. Sécurité de la session

Le code configure une clé secrète et des paramètres de cookies, notamment pour distinguer le contexte de production.

Les valeurs sensibles, telles que la clé secrète et les paramètres de connexion, doivent être fournies par des variables d'environnement plutôt que d'être inscrites en dur dans le code.

---

## 5. Fonctionnement du catalogue

### 5.1. Produits

Un produit est un article vendu par la boutique.

Il possède notamment :

- un identifiant ;
- une désignation ;
- un prix unitaire ;
- une description ;
- une image éventuelle ;
- un stock ;
- une catégorie ;
- un indicateur d'activation.

La route `/produits` récupère les produits auprès de l'API, prépare les données nécessaires à l'affichage et transmet la liste au template `produits.html`.

Les administrateurs et les vendeurs peuvent ajouter, modifier et supprimer les produits. Les clients peuvent consulter le catalogue.

Lors de la modification d'un produit, l'application peut conserver l'image existante si aucune nouvelle image n'est fournie. Lorsqu'une nouvelle image remplace l'ancienne, le code prévoit le nettoyage du média précédent après une modification réussie.

### 5.2. Services

Un service correspond à une prestation proposée par la boutique, par exemple une installation ou une intervention technique.

Contrairement à un produit, le modèle `Service` ne comporte pas de champ de stock.

Un service possède notamment :

- un nom ;
- un prix ;
- une description ;
- une catégorie ;
- une image éventuelle ;
- une vidéo éventuelle ;
- un état actif ou inactif.

Les services sont affichés à partir des données récupérées auprès de l'API. Les administrateurs et les vendeurs peuvent gérer leur création, leur modification et leur suppression.

Une route permet également de modifier l'état actif d'un service.

Un service inactif ne doit pas être considéré comme disponible pour une nouvelle commande. L'interface vérifie notamment l'état des services lors de certaines opérations du panier ; la validation définitive doit également être assurée par l'API.

---

## 6. Fonctionnement du panier

### 6.1. Stockage du panier

Le panier est conservé dans la session Flask.

Deux clés sont utilisées :

- `panier` : quantités des produits ;
- `panier_services` : quantités des services.

Le panier n'est donc pas, d'après le code Flask fourni, une table dédiée de la base de données.

Cette organisation permet de conserver le panier dans la session de l'utilisateur pendant sa navigation.

### 6.2. Ajout d'un produit

Lorsqu'un client ajoute un produit :

1. Flask vérifie que l'utilisateur possède le rôle client.
2. L'application récupère les informations du produit auprès de l'API.
3. Elle vérifie que le produit existe, qu'il est actif et que son stock permet l'ajout.
4. La quantité est actualisée dans la session.
5. Flask renvoie une réponse JSON permettant notamment de mettre à jour le compteur du panier.

Les quantités peuvent ensuite être augmentées, diminuées ou supprimées.

### 6.3. Ajout d'un service

L'ajout d'un service suit un principe similaire, mais sans contrôle de stock.

Flask vérifie l'existence du service et son état actif avant d'actualiser `panier_services`.

### 6.4. Calcul du total

Lors de l'affichage du panier, Flask récupère les produits et les services depuis l'API. Il prépare les lignes du panier, calcule les sous-totaux et le montant total, puis ajuste certaines quantités si nécessaire, notamment en fonction du stock disponible pour les produits.

Les données du panier ne doivent pas être considérées comme une source de vérité pour les prix ou les droits : au moment de créer une commande, l'API doit valider les références, les quantités, les prix et la disponibilité.

---

## 7. Cycle de vie d'une commande

### 7.1. Création d'une commande à partir du panier

Le parcours général est le suivant :

```text
Client
  |
  v
Ajout de produits et/ou de services
  |
  v
Panier conservé dans la session Flask
  |
  v
Soumission du panier
  |
  v
Flask transmet les lignes à FastAPI
  |
  v
L'API traite la création de la commande
  |
  v
La commande et ses lignes sont enregistrées
  |
  v
Flask affiche la confirmation
```

Les modèles de données prévoient une table `COMMANDE` et deux tables de liaison :

- `COMMANDE_has_PRODUIT` ;
- `COMMANDE_has_SERVICE`.

Une commande peut ainsi contenir des produits, des services ou les deux.

### 7.2. Prix enregistré au moment de la commande

Les tables de liaison comportent un champ `prix_unitaire`.

Ce choix permet de conserver le prix appliqué lors de la commande, indépendamment des modifications ultérieures du catalogue.

Par exemple, si un service coûte 15 000 FCFA au moment de la commande puis passe à 20 000 FCFA, la ligne de commande peut conserver le prix initial de 15 000 FCFA.

Le calcul et l'enregistrement effectifs de ce prix doivent être réalisés par le traitement métier qui crée la commande.

### 7.3. Gestion des commandes par les administrateurs et les vendeurs

Les routes Flask permettent notamment de :

- consulter les commandes ;
- créer une commande ;
- afficher le détail d'une commande ;
- modifier son statut ;
- ajouter ou modifier des produits dans une commande ;
- supprimer des lignes ;
- modifier certaines informations de commande ;
- supprimer une commande.

La page de détail peut récupérer les produits de la commande, les clients et les messages associés.

### 7.4. Espace client

La route `/mes-commandes` récupère les commandes du client auprès de l'API.

Pour chaque commande, Flask récupère également le nombre de messages non lus associés, afin de préparer leur affichage.

Une route permet de demander l'annulation d'une commande. Les conditions d'annulation et la vérification de propriété doivent être contrôlées par l'API.

---

## 8. Paiements et confirmation

L'interface prévoit une page de paiement et un formulaire permettant de sélectionner une méthode parmi :

- livraison ;
- Wave ;
- Orange Money ;
- carte bancaire.

La route `/confirmer-paiement` transmet le panier à l'API, avec la méthode choisie, via `/commandes/depuis-panier`.

Lorsque la réponse est considérée comme réussie et contient un identifiant de commande, Flask vide le panier, enregistre les informations de confirmation dans la session et redirige l'utilisateur vers la page de confirmation.

Le code prévoit donc un **parcours de commande associé à un choix de méthode de paiement**.

Toutefois, le code Flask transmis ne démontre pas à lui seul l'existence d'une intégration effective aux prestataires Wave, Orange Money ou à un réseau de cartes bancaires. Il ne faut pas confondre la sélection d'une méthode et l'enregistrement d'un paiement avec la réalisation d'une transaction externe.

Le modèle `Paiement` prévoit les champs suivants :

- identifiant du paiement ;
- identifiant de la commande ;
- identifiant de l'utilisateur ;
- montant ;
- méthode ;
- statut ;
- référence ;
- date du paiement.

Il faudra examiner les endpoints FastAPI associés pour établir précisément comment les paiements sont créés, validés et mis à jour.

### Deux parcours à distinguer

L'application contient deux routes de soumission du panier :

1. `/confirmer-paiement` : transmet également une méthode de paiement et redirige vers la confirmation de commande.
2. `/panier/commander` : transmet les lignes du panier, vide la session après succès et redirige vers une page de succès de commande.

Ces deux parcours ne doivent pas être présentés comme identiques. Leurs différences de traitement doivent être prises en compte lors de l'évolution de l'application.

---

## 9. Messagerie associée aux commandes

L'application prévoit une messagerie permettant aux utilisateurs autorisés de communiquer au sujet d'une commande.

Les fonctionnalités exposées par Flask comprennent :

- la consultation des messages d'une commande ;
- l'envoi de messages texte ;
- l'envoi de messages vocaux ;
- le marquage de messages comme lus ;
- la suppression de messages ;
- la consultation des conversations ;
- le comptage des messages non lus.

### 9.1. Structure d'un message

Le modèle `MessageCommande` contient notamment :

| Champ | Signification |
|---|---|
| `id_message` | Identifiant du message |
| `COMMANDE_id_commande` | Commande concernée |
| `UTILISATEUR_id_utilisateur` | Expéditeur |
| `UTILISATEUR_destinataire_id` | Destinataire |
| `message` | Contenu textuel |
| `date_message` | Date et heure |
| `lu` | État de lecture |
| `audio_url` | URL éventuelle du fichier audio |

Le contenu textuel est nullable, ce qui permet de représenter un message vocal sans texte.

Le champ `lu` est un booléen : `False` correspond à un message non lu et `True` à un message marqué comme lu.

### 9.2. Envoi d'un message texte

Flask reçoit le contenu du formulaire et le transmet à l'API avec l'identifiant de la commande.

L'API doit déterminer le destinataire approprié et vérifier que l'expéditeur est autorisé à participer à cette conversation.

### 9.3. Envoi d'un message vocal

La route dédiée reçoit un fichier envoyé par le navigateur et le transmet à l'API en multipart.

L'URL du fichier audio est ensuite représentée par le champ `audio_url` du modèle. Le mécanisme exact de stockage du fichier vocal doit être confirmé dans le code de l'API et dans sa configuration de stockage.

### 9.4. Lecture et suppression

Des routes permettent de marquer un message comme lu ou de le supprimer.

Les vérifications d'autorisation doivent être effectuées côté serveur. Le simple fait de connaître un identifiant de message ou de commande ne doit pas permettre d'accéder aux messages d'un autre utilisateur.

---

## 10. Notifications

Le modèle `Notification` permet d'associer une notification à un utilisateur.

Les champs principaux sont :

- `id_notification` ;
- `UTILISATEUR_id_utilisateur` ;
- `titre` ;
- `message` ;
- `type_notification` ;
- `lien` ;
- `lu` ;
- `date_notification`.

Flask expose des routes permettant notamment de :

- récupérer le nombre de notifications et les notifications disponibles ;
- marquer une notification comme lue ;
- marquer toutes les notifications comme lues.

La route de consultation renvoie une réponse JSON. En cas d'erreur, le code prévoit un résultat de repli avec un compteur nul et une liste vide.

Le modèle définit la structure des notifications, mais les événements qui les créent doivent être recherchés dans le code de l'API.

---

## 11. Gestion de la page d'accueil

La page d'accueil peut afficher des photos et des publicités vidéo.

Deux modèles sont prévus :

- `PhotoAccueil` ;
- `Publicite`.

Ils possèdent notamment un identifiant, un nom de fichier, un ordre d'affichage, un état actif et une date d'ajout. La publicité dispose également d'un titre facultatif.

La route publique `/` récupère le contenu d'accueil auprès de l'API, prépare les URL des médias et affiche le template `accueil.html`.

L'administration de ces contenus est accessible par `/gestion-accueil`, réservée à l'administrateur dans le code Flask transmis.

Les opérations disponibles comprennent :

- l'ajout d'une photo ;
- la suppression d'une photo ;
- l'ajout d'une publicité vidéo ;
- la suppression d'une publicité vidéo.

Lors d'un ajout, Flask valide l'extension du fichier, effectue le téléversement du média puis transmet les informations correspondantes à l'API. Si l'enregistrement échoue, le code prévoit un nettoyage du média nouvellement téléversé.

---

## 12. Stockage des images, vidéos et fichiers audio

### 12.1. Cloudinary

L'application prévoit Cloudinary pour le stockage des médias en production.

La configuration accepte notamment les variables d'environnement suivantes :

- `CLOUDINARY_URL` ;
- `CLOUDINARY_CLOUD_NAME` ;
- `CLOUDINARY_API_KEY` ;
- `CLOUDINARY_API_SECRET` ;
- `CLOUDINARY_ACTIF`.

Le code construit des dossiers distincts selon le type de média, par exemple :

- `boutique/produits` ;
- `boutique/services_images` ;
- `boutique/services_videos` ;
- `boutique/accueil_photos` ;
- `boutique/accueil_videos`.

Les vidéos peuvent être envoyées par blocs avec la méthode d'upload adaptée.

En production, le code prévoit de refuser certains téléversements si Cloudinary n'est pas correctement activé, plutôt que de s'appuyer sur un stockage local potentiellement éphémère.

### 12.2. Stockage local

En développement, l'application peut enregistrer les médias dans des dossiers locaux sous `static/`.

Les chemins prévus par le code Flask comprennent notamment :

- les images des produits ;
- les images et vidéos des services ;
- les photos de la page d'accueil ;
- les publicités vidéo.

Les noms exacts des sous-dossiers doivent être vérifiés dans l'arborescence réelle, car le chemin logique de stockage et le chemin utilisé par un template ne sont pas nécessairement identiques.

### 12.3. Résolution des URL

La fonction `media_url` permet de préparer les URL des médias pour les templates.

Les URL complètes peuvent être conservées telles quelles, tandis que les noms de fichiers locaux peuvent être transformés en URL de ressources statiques.

Les fonctions d'enrichissement préparent notamment les champs d'URL utilisés pour les images des produits, les médias des services et les contenus de la page d'accueil.

---

## 13. Tableau de bord et administration

L'application comporte deux routes de tableau de bord dans le code transmis :

- `/tableau-de-bord`, qui affiche `tableau_de_bord.html` ;
- `/dashboard`, qui affiche `dashboard.html`.

Ces routes récupèrent des statistiques depuis l'API pour les administrateurs et les vendeurs. La première prévoit un affichage avec des statistiques vides pour les clients.

La route `/utilisateurs` est réservée à l'administrateur et permet de consulter les utilisateurs.

La route `/utilisateurs/creer` permet également à l'administrateur de créer un compte et de sélectionner un rôle parmi les rôles prévus.

Ces deux routes de tableau de bord doivent être conservées ou unifiées en connaissance de cause : leur coexistence peut correspondre à des pages différentes, mais elle mérite d'être documentée et vérifiée.

---

## 14. Principales routes Flask

Le tableau suivant résume les routes observées dans `Projet_Boutique/app.py`. Les méthodes HTTP sont indiquées lorsqu'elles sont établies par le code transmis.

| Route | Méthode | Fonction |
|---|---|---|
| `/` | GET | Afficher la page d'accueil |
| `/sante` | GET | Vérifier la disponibilité de l'interface |
| `/login` | GET, POST | Afficher le formulaire et connecter un utilisateur |
| `/logout` | GET | Déconnecter l'utilisateur |
| `/creer-compte` | GET, POST | Créer un compte |
| `/mon-compte` | GET | Afficher le profil |
| `/mon-compte/modifier` | POST | Modifier le profil |
| `/mon-compte/mot-de-passe` | POST | Modifier le mot de passe |
| `/tableau-de-bord` | GET | Afficher un tableau de bord |
| `/dashboard` | GET | Afficher l'autre page de tableau de bord |
| `/utilisateurs` | GET | Consulter les utilisateurs |
| `/utilisateurs/creer` | GET, POST | Créer un utilisateur depuis l'administration |
| `/clients` | GET, POST | Consulter et ajouter des clients |
| `/clients/proches` | GET | Rechercher les clients géolocalisés dans un rayon, avec distance, commandes et total des achats |
| `/produits` | GET, POST | Consulter et ajouter des produits |
| `/produits/modifier/<id_produit>` | POST | Modifier un produit |
| `/produits/supprimer/<id_produit>` | POST | Supprimer un produit |
| `/services` | GET | Consulter les services |
| `/services/ajouter` | POST | Ajouter un service |
| `/services/modifier/<id_service>` | POST | Modifier un service |
| `/services/supprimer/<id_service>` | POST | Supprimer un service |
| `/panier` | GET | Afficher le panier |
| `/panier/ajouter/<id_produit>` | POST | Ajouter un produit au panier |
| `/panier/services/ajouter/<id_service>` | POST | Ajouter un service au panier |
| `/panier/modifier/<id_produit>` | POST | Modifier une quantité de produit |
| `/panier/supprimer/<id_produit>` | POST | Supprimer un produit du panier |
| `/panier/services/modifier/<id_service>` | POST | Modifier une quantité de service |
| `/panier/services/supprimer/<id_service>` | POST | Supprimer un service du panier |
| `/panier/vider` | POST | Vider le panier |
| `/paiement` | GET | Afficher le formulaire de paiement |
| `/confirmer-paiement` | POST | Transmettre le panier et la méthode choisie |
| `/confirmation-commande` | GET | Afficher la confirmation |
| `/panier/commander` | POST | Créer une commande à partir du panier |
| `/commande/succes/<id_commande>` | GET | Afficher le succès de commande |
| `/commandes` | GET | Consulter les commandes de la boutique |
| `/commandes/ajouter` | POST | Ajouter une commande |
| `/commandes/<id_commande>` | GET | Afficher le détail d'une commande |
| `/commandes/<id_commande>/statut` | POST | Modifier le statut |
| `/mes-commandes` | GET | Consulter les commandes du client |
| `/mes-commandes/<id_commande>/annuler` | DELETE | Demander l'annulation d'une commande |
| `/commandes/<id_commande>/messages` | GET, POST | Consulter ou envoyer des messages selon la méthode |
| `/commandes/<id_commande>/messages/envoyer` | POST | Envoyer un message texte |
| `/commandes/<id_commande>/messages/vocal` | POST | Envoyer un message vocal |
| `/messages/<id_message>/lu` | PUT | Marquer un message comme lu |
| `/messages/<id_message>` | DELETE | Supprimer un message |
| `/mes-messages` | GET | Consulter les conversations |
| `/messages/non-lus/count` | GET | Récupérer le compteur de messages non lus |
| `/notifications` | GET | Récupérer les notifications |
| `/notifications/<id_notification>/lue` | PUT | Marquer une notification comme lue |
| `/notifications/toutes/lues` | PUT | Marquer toutes les notifications comme lues |
| `/gestion-accueil` | GET | Administrer le contenu de la page d'accueil |
| `/gestion-accueil/photo/ajouter` | POST | Ajouter une photo |
| `/gestion-accueil/photo/<id_photo>/supprimer` | POST | Supprimer une photo |
| `/gestion-accueil/publicite/ajouter` | POST | Ajouter une publicité vidéo |
| `/gestion-accueil/publicite/<id_publicite>/supprimer` | POST | Supprimer une publicité vidéo |

Les routes de modification des clients et des lignes de commande sont également présentes. Pour obtenir un inventaire exhaustif, il faut compléter ce tableau à partir de l'ensemble du fichier et des routes de l'API.

---

## 15. Modèle de données

Les modèles SQLAlchemy transmis définissent les principales tables suivantes.

| Table | Rôle |
|---|---|
| `UTILISATEUR` | Comptes, coordonnées et rôles |
| `CLIENT` | Informations propres au client et lien éventuel avec un utilisateur |
| `PRODUIT` | Catalogue de produits |
| `SERVICE` | Catalogue de services |
| `COMMANDE` | Informations générales sur les commandes |
| `COMMANDE_has_PRODUIT` | Produits, quantités et prix par commande |
| `COMMANDE_has_SERVICE` | Services, quantités et prix par commande |
| `PAIEMENT` | Informations relatives aux paiements |
| `MESSAGE_COMMANDE` | Messages texte et vocaux liés aux commandes |
| `NOTIFICATION` | Notifications destinées aux utilisateurs |
| `PHOTO_ACCUEIL` | Photos de la page d'accueil |
| `PUBLICITE` | Publicités vidéo |

### 15.1. Relations principales

- Un client peut être associé à un compte utilisateur via `CLIENT.id_utilisateur`.
- Une commande référence un client via `COMMANDE.CLIENT_id_client`.
- Les tables `COMMANDE_has_PRODUIT` et `COMMANDE_has_SERVICE` relient une commande à ses articles.
- Un paiement référence une commande et un utilisateur.
- Un message référence une commande, un expéditeur et un destinataire.
- Une notification référence un utilisateur.

Les deux tables de liaison utilisent une clé primaire composée des identifiants de la commande et du produit ou du service. Cette structure permet de distinguer les différentes lignes d'une commande.

Les modèles transmis utilisent des clés étrangères SQLAlchemy, mais ne déclarent pas explicitement de relations ORM avec `relationship()`. Les données associées peuvent donc être récupérées par des requêtes et des jointures définies ailleurs dans le code.

### 15.2. Géolocalisation des clients

Lorsqu'un client confirme une commande, le navigateur peut transmettre sa position GPS avec son autorisation. Chaque commande conserve son propre instantané de coordonnées ; la fiche `CLIENT` conserve la dernière position GPS reçue et n'est remplacée que lorsqu'une nouvelle commande fournit une position complète. Si l'accès GPS est refusé ou indisponible, la commande peut être créée sans coordonnées et la dernière position connue du client reste inchangée. Les administrateurs et vendeurs peuvent consulter la carte de la position propre à chaque commande depuis sa fiche ou la liste des commandes.

Les administrateurs et vendeurs peuvent utiliser `/clients/proches` depuis la gestion des clients. La recherche accepte latitude, longitude et rayon en kilomètres, calcule les distances sur le serveur avec la formule de Haversine, puis trie les résultats par proximité. Le tableau affiche aussi le nombre de commandes et le total calculé à partir des lignes historiques de produits et services. La route est protégée par le rôle admin/vendeur.

Les colonnes `latitude` et `longitude` des tables `CLIENT` et `COMMANDE` doivent exister dans PostgreSQL avant le déploiement du code ; le script fourni est `API/migration_geo.sql`.

---

## 16. Configuration et lancement

### 16.1. Configuration de l'interface Flask

Le code Flask utilise notamment les variables d'environnement suivantes :

| Variable | Fonction |
|---|---|
| `API_URL` | Adresse principale de l'API |
| `API_PUBLIC_URL` | Adresse de l'API exposée aux pages ou aux clients |
| `API_TIMEOUT` | Délai d'attente des requêtes vers l'API |
| `SECRET_KEY` | Clé secrète de Flask |
| `FLASK_SECRET_KEY` | Autre variable prévue pour la clé secrète |
| `MAX_UPLOAD_MB` | Limite de taille des fichiers téléversés |
| `CLOUDINARY_URL` | URL de configuration Cloudinary |
| `CLOUDINARY_CLOUD_NAME` | Nom du cloud |
| `CLOUDINARY_API_KEY` | Clé API Cloudinary |
| `CLOUDINARY_API_SECRET` | Secret API Cloudinary |
| `CLOUDINARY_ACTIF` | Activation de Cloudinary selon la configuration |

En environnement local, l'API est configurée par défaut sur `http://127.0.0.1:8000`, et l'interface Flask utilise le port `5000` par défaut.

Ces valeurs par défaut ne doivent pas être reprises en production si les services sont hébergés à des adresses différentes.

### 16.2. Lancement local

Le projet utilise deux processus distincts.

**Terminal 1 — API FastAPI**

Depuis le dossier `BDD_FASTAPI`, activer l'environnement Python approprié, installer les dépendances de l'API si nécessaire, puis lancer le serveur selon la commande prévue par le projet. Par exemple, si le module expose bien `app` :

```powershell
cd API
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — interface Flask**

```powershell
cd Projet_Boutique
python app.py
```

L'interface est alors normalement accessible sur :

`http://127.0.0.1:5000`

L'API est normalement accessible sur :

`http://127.0.0.1:8000`

Ces commandes supposent que les dépendances sont installées, que les variables d'environnement sont correctement définies et que la configuration de la base de données est fonctionnelle.

### 16.3. Déploiement

Le projet dispose de services hébergés sur Render. L'interface Flask peut être lancée avec Gunicorn, tandis que l'API fonctionne comme un service distinct.

Les paramètres de production doivent notamment inclure :

- les URL publiques des services ;
- la configuration de la base de données ;
- les clés et secrets nécessaires ;
- les paramètres de stockage des médias ;
- les dépendances Python appropriées.

Les secrets ne doivent pas être intégrés au README ni au dépôt Git.

---

## 17. Gestion des erreurs et limites de configuration

Le code Flask prévoit plusieurs mécanismes de gestion des erreurs :

- traitement de l'expiration de session ;
- gestion des erreurs de requêtes HTTP vers l'API ;
- prise en charge de la limite de taille des fichiers ;
- affichage de messages d'erreur et de confirmation ;
- nettoyage de certains médias en cas d'échec d'enregistrement.

Le bon fonctionnement de l'interface dépend toutefois de la disponibilité de l'API. Une page qui attend une réponse de l'API peut donc être lente si celle-ci ne répond pas dans le délai prévu.

Le stockage local des fichiers ne doit pas être considéré comme persistant dans un environnement de déploiement où le système de fichiers est éphémère. Le stockage distant doit être correctement configuré pour conserver les médias après redémarrage ou redéploiement.

Enfin, les opérations critiques — autorisations, prix, stock, création de commande et paiement — doivent être validées côté serveur et non uniquement par les formulaires Flask.

---

## 18. Points de vigilance pour la maintenance

Lorsqu'un développeur intervient sur le projet, il doit vérifier les points suivants.

1. **API et interface :** une modification de contrat API peut nécessiter une adaptation dans Flask.
2. **Authentification :** les routes sensibles doivent contrôler les rôles et les droits sur les ressources.
3. **Commandes :** la validation du stock, des prix et des quantités doit être cohérente au moment de l'enregistrement.
4. **Paiements :** le choix d'une méthode ne suffit pas à confirmer qu'un paiement externe a été réalisé.
5. **Médias :** le téléversement, la génération d'URL et la suppression doivent fonctionner avec le stockage effectivement utilisé.
6. **Messagerie :** les droits de lecture, de suppression et de marquage comme lu doivent être vérifiés côté API.
7. **Routes du tableau de bord :** les deux parcours `/dashboard` et `/tableau-de-bord` doivent être documentés et leur utilité clarifiée.
8. **Base de données :** toute évolution des modèles doit être coordonnée avec le schéma réellement déployé et les éventuelles migrations.
9. **Données sensibles :** les mots de passe doivent être stockés sous forme de hachages sécurisés et les secrets conservés dans des variables d'environnement.
10. **Tests :** les changements doivent être vérifiés sur les parcours client, vendeur et administrateur.

---

## 19. Conclusion

L'application repose sur une séparation des responsabilités entre l'interface Flask, l'API FastAPI et la couche de données SQLAlchemy.

Flask gère principalement les interactions avec le navigateur, les sessions, les formulaires et l'affichage des pages. FastAPI expose les opérations métier auxquelles l'interface fait appel. SQLAlchemy définit les modèles de données qui structurent les informations persistantes de la boutique.

Cette architecture permet de faire évoluer séparément l'interface et les traitements métier, à condition de conserver des contrats API cohérents et de vérifier les autorisations, la cohérence des données et la gestion des erreurs à chaque niveau.

Ce document constitue une présentation technique du fonctionnement déduit des fichiers transmis. Pour une documentation entièrement exhaustive, il doit être complété par l'arborescence exacte des templates et des fichiers statiques, ainsi que par l'examen des endpoints FastAPI, de la configuration de la base de données et du mécanisme de migration ou de création des tables.
