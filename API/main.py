from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from urllib.parse import urlparse

from sqlalchemy import func
from pydantic import BaseModel, Field, model_validator


import cloudinary
import cloudinary.uploader



import os
import uuid
import math

from sqlalchemy.orm import Session

import bcrypt

from datetime import date, datetime, timedelta


from auth import (
    creer_token,
    role_autorise
)

from database import get_db

from models import (
    Utilisateur,
    Client,
    Produit,
    Commande,
    CommandeHasProduit,
    Service,
    CommandeHasService,
    MessageCommande,
    PhotoAccueil,
    Publicite,
    Notification,
    Paiement
)

from schemas import (
    UtilisateurLogin,
    UtilisateurCreate,
    UtilisateurClientCreate,

    ClientCreate,
    ClientUpdate,

    # =====================================================
    # PRODUITS
    # =====================================================
    ProduitCreate,
    ProduitUpdate,

    # =====================================================
    # SERVICES
    # =====================================================
    ServiceCreate,
    ServiceUpdate,

    LigneProduitPanier,
    LigneServicePanier,

    # =====================================================
    # COMMANDES
    # =====================================================
    CommandeCreate,
    CommandeUpdate,

    CommandeHasProduitCreate,
    CommandeHasProduitUpdate,

    # =====================================================
    # COMMANDE - SERVICE
    # =====================================================
    CommandeHasServiceCreate,
    CommandeHasServiceUpdate,

    CommandeDepuisPanierCreate,

    # =====================================================
    # MESSAGERIE
    # =====================================================
    MessageCommandeCreate,
    MessageCommandeResponse,
    MessageCommandeLuUpdate
)



# =========================================================
# 👤 SCHÉMAS — ESPACE MON COMPTE
# =========================================================


class MonCompteUpdate(BaseModel):
    """
    Informations modifiables depuis l'espace
    personnel de l'utilisateur.
    """

    nom: str
    prenom: str
    email: str

    telephone: str | None = None

    date_naissance: date | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def verifier_paire_coordonnees(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être renseignées ensemble.")
        return self


class MotDePasseUpdate(BaseModel):
    """
    Données nécessaires pour modifier
    le mot de passe.
    """

    ancien_mot_de_passe: str

    nouveau_mot_de_passe: str

    confirmation_mot_de_passe: str


# =========================================================
# CRÉATION DE L'APPLICATION
# =========================================================

app = FastAPI()

import os

# =========================================================
# DOSSIERS POUR LES FICHIERS AUDIO
# =========================================================

import os
import uuid

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

STATIC_DIR = os.path.join(
    BASE_DIR,
    "static"
)

AUDIO_DIR = os.path.join(
    STATIC_DIR,
    "audio"
)

# Créer automatiquement le dossier static
# s'il n'existe pas
os.makedirs(
    STATIC_DIR,
    exist_ok=True
)

# Créer automatiquement le dossier audio
# s'il n'existe pas
os.makedirs(
    AUDIO_DIR,
    exist_ok=True
)



# =========================================================
# CONFIGURATION CLOUDINARY POUR LE STOCKAGE EN LIGNE
# =========================================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)




# =========================================================
# DOSSIER POUR LES FICHIERS STATIQUES
# =========================================================

os.makedirs(AUDIO_DIR, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

# =========================================================
# CONFIGURATION CORS
# =========================================================

# En local, le front tourne sur 127.0.0.1:5000.
# En production, définir FRONTEND_URL dans les variables Render.
_origines_autorisees = {
    "http://127.0.0.1:5000",
    "http://localhost:5000",
}
_origine_production = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if _origine_production:
    _origines_autorisees.add(_origine_production)
_origines_extra = os.getenv("CORS_ORIGINS", "")
_origines_autorisees.update(
    origine.strip().rstrip("/")
    for origine in _origines_extra.split(",")
    if origine.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_origines_autorisees),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROUTE D'ACCUEIL
# =========================================================

@app.get("/")
def accueil():

    return {
        "message": "Bienvenue dans l'API de gestion de boutique"
    }


# =========================================================
# ROUTE : LISTE DES CLIENTS
# =========================================================

@app.get("/clients")
def lire_clients(
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    clients = db.query(Client).all()

    resultats = []

    for client in clients:

        resultats.append({
            "id_client": client.id_client,
            "nom": client.nom,
            "prenom": client.prenom,
            "date_naissance": client.date_naissance,
            "email": client.email,
            "telephone": client.telephone,
            "latitude": client.latitude,
            "longitude": client.longitude
        })

    return resultats


@app.get("/clients/proches")
def lire_clients_proches(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    rayon_km: float = Query(..., gt=0, le=20038),
    utilisateur=Depends(role_autorise("admin", "vendeur")),
    db: Session = Depends(get_db)
):
    """Liste les clients dans le rayon indiqué, triés par proximité."""
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise HTTPException(status_code=422, detail="Coordonnées GPS invalides.")
    if not math.isfinite(rayon_km):
        raise HTTPException(status_code=422, detail="Le rayon doit être un nombre fini.")

    clients = db.query(Client).filter(
        Client.latitude.isnot(None),
        Client.longitude.isnot(None)
    ).all()

    nombre_commandes = dict(
        db.query(
            Commande.CLIENT_id_client,
            func.count(Commande.id_commande)
        )
        .group_by(Commande.CLIENT_id_client)
        .all()
    )

    totaux_produits = dict(
        db.query(
            Commande.CLIENT_id_client,
            func.sum(
                CommandeHasProduit.quantite
                * CommandeHasProduit.prix_unitaire
            )
        )
        .join(
            Commande,
            Commande.id_commande
            == CommandeHasProduit.COMMANDE_id_commande
        )
        .group_by(Commande.CLIENT_id_client)
        .all()
    )

    totaux_services = dict(
        db.query(
            Commande.CLIENT_id_client,
            func.sum(
                CommandeHasService.quantite
                * CommandeHasService.prix_unitaire
            )
        )
        .join(
            Commande,
            Commande.id_commande
            == CommandeHasService.COMMANDE_id_commande
        )
        .group_by(Commande.CLIENT_id_client)
        .all()
    )

    resultat = []
    latitude_ref = math.radians(latitude)
    longitude_ref = math.radians(longitude)
    rayon_terre_km = 6371.0

    for client in clients:
        latitude_client = float(client.latitude)
        longitude_client = float(client.longitude)
        delta_latitude = math.radians(latitude_client) - latitude_ref
        delta_longitude = math.radians(longitude_client) - longitude_ref
        haversine = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(latitude_ref)
            * math.cos(math.radians(latitude_client))
            * math.sin(delta_longitude / 2) ** 2
        )
        distance = 2 * rayon_terre_km * math.asin(
            min(1.0, math.sqrt(haversine))
        )

        if distance > rayon_km:
            continue

        id_client = client.id_client
        total_achats = float(
            totaux_produits.get(id_client) or 0
        ) + float(
            totaux_services.get(id_client) or 0
        )
        resultat.append({
            "id_client": id_client,
            "nom": client.nom,
            "prenom": client.prenom,
            "date_naissance": client.date_naissance,
            "email": client.email,
            "telephone": client.telephone,
            "latitude": latitude_client,
            "longitude": longitude_client,
            "distance_km": round(distance, 2),
            "nombre_commandes": nombre_commandes.get(id_client, 0),
            "total_achats": round(total_achats, 2),
        })

    resultat.sort(key=lambda client: client["distance_km"])
    return resultat


# =========================================================
# ROUTE : AJOUTER UN CLIENT
# =========================================================

@app.post("/clients")
def ajouter_client(
    client: ClientCreate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    nouveau_client = Client(
        nom=client.nom,
        prenom=client.prenom,
        date_naissance=client.date_naissance,
        email=client.email,
        telephone=client.telephone,
        latitude=client.latitude,
        longitude=client.longitude
    )

    db.add(nouveau_client)

    db.commit()

    db.refresh(nouveau_client)

    return nouveau_client


# =========================================================
# ROUTE : MODIFIER UN CLIENT
# =========================================================

@app.put("/clients/{id_client}")
def modifier_client(
    id_client: int,
    client: ClientUpdate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    client_existant = db.query(Client).filter(
        Client.id_client == id_client
    ).first()

    if client_existant is None:

        return {
            "message": "Client introuvable"
        }

    client_existant.nom = client.nom
    client_existant.prenom = client.prenom
    client_existant.date_naissance = client.date_naissance
    client_existant.email = client.email
    client_existant.telephone = client.telephone
    client_existant.latitude = client.latitude
    client_existant.longitude = client.longitude

    db.commit()

    db.refresh(client_existant)

    return client_existant


# =========================================================
# ROUTE : SUPPRIMER UN CLIENT
# =========================================================

@app.delete("/clients/{id_client}")
def supprimer_client(
    id_client: int,
    utilisateur=Depends(role_autorise("admin", "vendeur")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id_client == id_client).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    commande_existante = db.query(Commande).filter(
        Commande.CLIENT_id_client == id_client
    ).first()
    if commande_existante is not None:
        raise HTTPException(
            status_code=409,
            detail="Ce client possède un historique de commandes et ne peut pas être supprimé.",
        )

    try:
        db.delete(client)
        db.commit()
    except Exception as erreur:
        db.rollback()
        print("Erreur suppression client :", str(erreur))
        raise HTTPException(status_code=500, detail="Impossible de supprimer le client.")
    return {"message": f"Client {id_client} supprimé avec succès."}


# =========================================================
# ROUTE : LISTER LES PRODUITS
# =========================================================

@app.get("/produits")
def liste_produits(
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    produits = db.query(Produit).all()

    return produits



# =========================================================
# ROUTE : AJOUTER UN PRODUIT
# =========================================================

@app.post("/produits")
def ajouter_produit(
    produit: ProduitCreate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):
    """
    Ajoute un produit dans la boutique.

    Accessible à l'administrateur et au vendeur.
    L'image peut être une URL, notamment une URL Cloudinary.
    """

    # -----------------------------------------------------
    # 1. VALIDATION DES DONNÉES
    # -----------------------------------------------------

    designation = (
        produit.designation.strip()
        if produit.designation
        else ""
    )

    if not designation:
        raise HTTPException(
            status_code=422,
            detail="La désignation du produit est obligatoire."
        )

    if produit.prix_unitaire is None or produit.prix_unitaire < 0:
        raise HTTPException(
            status_code=422,
            detail="Le prix doit être positif ou nul."
        )

    if produit.stock is None or produit.stock < 0:
        raise HTTPException(
            status_code=422,
            detail="Le stock doit être positif ou nul."
        )

    # -----------------------------------------------------
    # 2. PRÉPARER LE PRODUIT
    # -----------------------------------------------------

    nouveau_produit = Produit(
        designation=designation,
        prix_unitaire=produit.prix_unitaire,
        description=produit.description,
        image=produit.image,
        stock=produit.stock,
        categorie=produit.categorie,
        actif=produit.actif
    )

    # -----------------------------------------------------
    # 3. ENREGISTRER DANS LA BASE
    # -----------------------------------------------------

    try:
        db.add(nouveau_produit)
        db.commit()
        db.refresh(nouveau_produit)

    except Exception as erreur:
        db.rollback()

        print(
            "Erreur lors de l'ajout du produit :",
            str(erreur)
        )

        raise HTTPException(
            status_code=500,
            detail="Une erreur est survenue lors de l'ajout du produit."
        )

    # -----------------------------------------------------
    # 4. RETOURNER LE PRODUIT CRÉÉ
    # -----------------------------------------------------

    return nouveau_produit




# =========================================================
# ROUTE : MODIFIER UN PRODUIT
# =========================================================

@app.put("/produits/{id_produit}")
def modifier_produit(
    id_produit: int,
    produit: ProduitUpdate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):
    """
    Modifie les informations d'un produit existant.

    - Réservé à l'administrateur et au vendeur.
    - Conserve l'image actuelle si aucune nouvelle image
      n'est transmise.
    - Vérifie les valeurs avant l'enregistrement.
    - Annule la transaction en cas d'erreur.
    """

    # -----------------------------------------------------
    # 1. RECHERCHER LE PRODUIT
    # -----------------------------------------------------

    produit_existant = (
        db.query(Produit)
        .filter(Produit.id_produit == id_produit)
        .first()
    )

    if produit_existant is None:
        raise HTTPException(
            status_code=404,
            detail="Produit introuvable."
        )

    # -----------------------------------------------------
    # 2. RÉCUPÉRER UNIQUEMENT LES CHAMPS FOURNIS
    # -----------------------------------------------------

    # exclude_unset évite d'écraser des champs non transmis.
    if hasattr(produit, "model_dump"):
        donnees = produit.model_dump(exclude_unset=True)
    else:  # Compatibilité Pydantic v1
        donnees = produit.dict(exclude_unset=True)

    # -----------------------------------------------------
    # 3. VÉRIFIER LES DONNÉES
    # -----------------------------------------------------

    if "designation" in donnees:
        designation = donnees["designation"]

        if designation is None or not str(designation).strip():
            raise HTTPException(
                status_code=422,
                detail="La désignation du produit est obligatoire."
            )

        donnees["designation"] = str(designation).strip()

    if "prix_unitaire" in donnees:
        prix = donnees["prix_unitaire"]

        if prix is None or prix < 0:
            raise HTTPException(
                status_code=422,
                detail="Le prix doit être positif ou nul."
            )

    if "stock" in donnees:
        stock = donnees["stock"]

        if stock is None or stock < 0:
            raise HTTPException(
                status_code=422,
                detail="Le stock doit être positif ou nul."
            )

    if "categorie" in donnees and donnees["categorie"] is not None:
        donnees["categorie"] = str(donnees["categorie"]).strip()

    if "description" in donnees and donnees["description"] is not None:
        donnees["description"] = str(donnees["description"]).strip()

    # Si image vaut None, on conserve l'image existante.
    # Une chaîne vide permet, si nécessaire, de supprimer
    # l'URL enregistrée.
    if donnees.get("image") is None:
        donnees.pop("image", None)

    # -----------------------------------------------------
    # 4. APPLIQUER LES MODIFICATIONS
    # -----------------------------------------------------

    champs_autorises = {
        "designation",
        "prix_unitaire",
        "description",
        "image",
        "stock",
        "categorie",
        "actif",
    }

    for champ, valeur in donnees.items():
        if champ in champs_autorises:
            setattr(produit_existant, champ, valeur)

    # -----------------------------------------------------
    # 5. ENREGISTRER LES MODIFICATIONS
    # -----------------------------------------------------

    try:
        db.commit()
        db.refresh(produit_existant)

    except Exception as erreur:
        db.rollback()

        # L'erreur détaillée reste côté serveur.
        print(
            "Erreur lors de la modification du produit :",
            str(erreur)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors de "
                "la modification du produit."
            )
        )

    # -----------------------------------------------------
    # 6. RETOURNER LE PRODUIT MODIFIÉ
    # -----------------------------------------------------

    return produit_existant



# =========================================================
# ROUTE : SUPPRIMER UN PRODUIT
# =========================================================

@app.delete("/produits/{id_produit}")
def supprimer_produit(
    id_produit: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Rechercher le produit
    # -----------------------------------------------------

    produit = db.query(Produit).filter(
        Produit.id_produit == id_produit
    ).first()

    if produit is None:

        raise HTTPException(
            status_code=404,
            detail="Produit introuvable."
        )

    # -----------------------------------------------------
    # 2. Vérifier si le produit est utilisé dans
    #    une commande
    # -----------------------------------------------------

    ligne_commande = db.query(
        CommandeHasProduit
    ).filter(
        CommandeHasProduit.PRODUIT_id_produit
        == id_produit
    ).first()

    # -----------------------------------------------------
    # 3. Si le produit a déjà été commandé
    # -----------------------------------------------------

    if ligne_commande is not None:

        # On ne supprime pas physiquement le produit.
        # On le désactive afin de conserver l'historique
        # des anciennes commandes.

        produit.actif = False

        try:

            db.commit()

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Une erreur est survenue lors "
                    "de la désactivation du produit."
                )
            )

        return {
            "message": (
                f"Le produit {id_produit} a été désactivé "
                "car il est déjà utilisé dans une commande."
            ),
            "action": "desactivation"
        }

    # -----------------------------------------------------
    # 4. Si le produit n'a jamais été commandé
    # -----------------------------------------------------

    db.delete(produit)

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de la suppression du produit."
            )
        )

    # -----------------------------------------------------
    # 5. Réponse
    # -----------------------------------------------------

    return {
        "message": (
            f"Produit {id_produit} supprimé avec succès."
        ),
        "action": "suppression"
    }


# =========================================================
# PRODUITS POUR LA PAGE D'ACCUEIL
# =========================================================

@app.get("/produits-accueil")
def produits_accueil(
    db: Session = Depends(get_db)
):
    """
    Endpoint public utilisé uniquement par la page
    d'accueil.

    Il retourne les 10 produits actifs les plus récents.

    Aucun token n'est nécessaire.
    """

    produits = (
        db.query(Produit)
        .filter(
            Produit.actif == True
        )
        .order_by(
            Produit.id_produit.desc()
        )
        .limit(10)
        .all()
    )

    return [
        {
            "id_produit": produit.id_produit,
            "designation": produit.designation,
            "prix_unitaire": produit.prix_unitaire,
            "description": produit.description,
            "image": produit.image,
            "stock": produit.stock,
            "categorie": produit.categorie,
            "actif": produit.actif
        }
        for produit in produits
    ]




# =========================================================
# =========================================================
# GESTION DES SERVICES
# =========================================================
# =========================================================


# =========================================================
# LISTER LES SERVICES
# =========================================================

@app.get("/services")
def liste_services(
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):
    """
    Retourne la liste des services.

    Les trois rôles peuvent consulter les services :
        - admin
        - vendeur
        - client
    """

    services = db.query(Service).all()

    return services



# =========================================================
# ROUTE : AJOUTER UN SERVICE
# =========================================================

@app.post("/services")
def ajouter_service(
    service: ServiceCreate,
    utilisateur=Depends(
        role_autorise("admin")
    ),
    db: Session = Depends(get_db)
):
    """
    Ajoute un nouveau service dans la boutique.

    - Accessible uniquement à l'administrateur.
    - Vérifie le nom et le prix.
    - Accepte des URL d'image et de vidéo, notamment
      des URL hébergées sur Cloudinary.
    - Annule la transaction en cas d'erreur.
    """

    # -----------------------------------------------------
    # 1. VALIDATION DES DONNÉES
    # -----------------------------------------------------

    nom_service = (
        service.nom_service.strip()
        if service.nom_service
        else ""
    )

    if not nom_service:
        raise HTTPException(
            status_code=422,
            detail="Le nom du service est obligatoire."
        )

    if service.prix is None or service.prix < 0:
        raise HTTPException(
            status_code=422,
            detail="Le prix du service doit être positif ou nul."
        )

    # -----------------------------------------------------
    # 2. CRÉER LE SERVICE
    # -----------------------------------------------------

    nouveau_service = Service(
        nom_service=nom_service,
        prix=service.prix,
        description=service.description,
        categorie=service.categorie,
        image=service.image,
        video=service.video,
        actif=service.actif
    )

    # -----------------------------------------------------
    # 3. ENREGISTRER DANS LA BASE
    # -----------------------------------------------------

    try:
        db.add(nouveau_service)
        db.commit()
        db.refresh(nouveau_service)

    except Exception as erreur:
        db.rollback()

        print(
            "Erreur lors de l'ajout du service :",
            str(erreur)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de l'ajout du service."
            )
        )

    # -----------------------------------------------------
    # 4. RETOURNER LE SERVICE CRÉÉ
    # -----------------------------------------------------

    return nouveau_service



# =========================================================
# ROUTE : MODIFIER UN SERVICE
# =========================================================

@app.put("/services/{id_service}")
def modifier_service(
    id_service: int,
    service: ServiceUpdate,
    utilisateur=Depends(
        role_autorise("admin")
    ),
    db: Session = Depends(get_db)
):
    """
    Modifie un service existant.

    - Réservé à l'administrateur.
    - Conserve les champs non transmis.
    - Conserve les URL de l'image et de la vidéo
      si aucune nouvelle URL n'est fournie.
    - Annule la transaction en cas d'erreur.
    """

    # -----------------------------------------------------
    # 1. RECHERCHER LE SERVICE
    # -----------------------------------------------------

    service_existant = (
        db.query(Service)
        .filter(Service.id_service == id_service)
        .first()
    )

    if service_existant is None:
        raise HTTPException(
            status_code=404,
            detail="Service introuvable."
        )

    # -----------------------------------------------------
    # 2. RÉCUPÉRER LES CHAMPS TRANSMIS
    # -----------------------------------------------------

    if hasattr(service, "model_dump"):
        donnees = service.model_dump(exclude_unset=True)
    else:  # Compatibilité Pydantic v1
        donnees = service.dict(exclude_unset=True)

    # -----------------------------------------------------
    # 3. VALIDER LES DONNÉES
    # -----------------------------------------------------

    if "nom_service" in donnees:
        nom = donnees["nom_service"]

        if nom is None or not str(nom).strip():
            raise HTTPException(
                status_code=422,
                detail="Le nom du service est obligatoire."
            )

        donnees["nom_service"] = str(nom).strip()

    if "prix" in donnees:
        prix = donnees["prix"]

        if prix is None or prix < 0:
            raise HTTPException(
                status_code=422,
                detail="Le prix du service doit être positif ou nul."
            )

    if "categorie" in donnees and donnees["categorie"] is not None:
        donnees["categorie"] = str(donnees["categorie"]).strip()

    if "description" in donnees and donnees["description"] is not None:
        donnees["description"] = str(donnees["description"]).strip()

    # Conserver les médias existants si aucune nouvelle URL
    # n'est fournie ou si la valeur reçue est None.
    if donnees.get("image") is None:
        donnees.pop("image", None)

    if donnees.get("video") is None:
        donnees.pop("video", None)

    # -----------------------------------------------------
    # 4. APPLIQUER LES MODIFICATIONS AUTORISÉES
    # -----------------------------------------------------

    champs_autorises = {
        "nom_service",
        "prix",
        "description",
        "categorie",
        "image",
        "video",
        "actif",
    }

    for champ, valeur in donnees.items():
        if champ in champs_autorises:
            setattr(service_existant, champ, valeur)

    # -----------------------------------------------------
    # 5. ENREGISTRER LES MODIFICATIONS
    # -----------------------------------------------------

    try:
        db.commit()
        db.refresh(service_existant)

    except Exception as erreur:
        db.rollback()

        print(
            "Erreur lors de la modification du service :",
            str(erreur)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de la modification du service."
            )
        )

    # -----------------------------------------------------
    # 6. RETOURNER LE SERVICE MODIFIÉ
    # -----------------------------------------------------

    return service_existant




# =========================================================
# TÉLÉVERSER L'IMAGE D'UN PRODUIT (ORDINATEUR / TÉLÉPHONE)
# =========================================================

@app.post("/produits/{id_produit}/image")
def televerser_image_produit(
    id_produit: int,
    fichier: UploadFile = File(...),
    utilisateur=Depends(role_autorise("admin", "vendeur")),
    db: Session = Depends(get_db),
):
    produit = db.query(Produit).filter(Produit.id_produit == id_produit).first()
    if produit is None:
        raise HTTPException(status_code=404, detail="Produit introuvable.")
    if not (fichier.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Veuillez sélectionner un fichier image.")

    resultat = televerser_vers_cloudinary(fichier, "boutique/produits", "image")
    nouvelle_url = resultat.get("secure_url")
    if not nouvelle_url:
        raise HTTPException(status_code=502, detail="Cloudinary n'a pas retourné l'URL de l'image.")
    ancienne_url = produit.image
    try:
        produit.image = nouvelle_url
        db.commit()
        db.refresh(produit)
    except Exception as erreur:
        db.rollback()
        supprimer_media_cloudinary(nouvelle_url, "image")
        print("Erreur sauvegarde image produit :", str(erreur))
        raise HTTPException(status_code=500, detail="Impossible d'enregistrer l'image du produit.")
    if ancienne_url and ancienne_url != nouvelle_url:
        supprimer_media_cloudinary(ancienne_url, "image")
    return {"message": "Image du produit mise à jour.", "id_produit": id_produit, "image": nouvelle_url}


# =========================================================
# TÉLÉVERSER L'IMAGE ET/OU LA VIDÉO D'UN SERVICE
# =========================================================

@app.post("/services/{id_service}/medias")
def televerser_medias_service(
    id_service: int,
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db),
):
    service = db.query(Service).filter(Service.id_service == id_service).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Service introuvable.")
    if image is None and video is None:
        raise HTTPException(status_code=400, detail="Sélectionnez une image et/ou une vidéo.")
    if image is not None and not (image.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier image sélectionné n'est pas une image.")
    if video is not None and not (video.content_type or "").lower().startswith("video/"):
        raise HTTPException(status_code=400, detail="Le fichier vidéo sélectionné n'est pas une vidéo.")

    nouvelles_urls = {}
    anciennes_urls = {"image": service.image, "video": service.video}
    try:
        if image is not None:
            upload_image = televerser_vers_cloudinary(image, "boutique/services/images", "image")
            nouvelles_urls["image"] = upload_image.get("secure_url")
            if not nouvelles_urls["image"]:
                raise HTTPException(status_code=502, detail="Cloudinary n'a pas retourné l'URL de l'image.")
        if video is not None:
            upload_video = televerser_vers_cloudinary(video, "boutique/services/videos", "video")
            nouvelles_urls["video"] = upload_video.get("secure_url")
            if not nouvelles_urls["video"]:
                raise HTTPException(status_code=502, detail="Cloudinary n'a pas retourné l'URL de la vidéo.")
        if "image" in nouvelles_urls:
            service.image = nouvelles_urls["image"]
        if "video" in nouvelles_urls:
            service.video = nouvelles_urls["video"]
        db.commit()
        db.refresh(service)
    except HTTPException:
        db.rollback()
        for cle, url in nouvelles_urls.items():
            supprimer_media_cloudinary(url, "image" if cle == "image" else "video")
        raise
    except Exception as erreur:
        db.rollback()
        for cle, url in nouvelles_urls.items():
            supprimer_media_cloudinary(url, "image" if cle == "image" else "video")
        print("Erreur sauvegarde médias service :", str(erreur))
        raise HTTPException(status_code=500, detail="Impossible d'enregistrer les médias du service.")

    for cle, ancienne_url in anciennes_urls.items():
        if cle in nouvelles_urls and ancienne_url and ancienne_url != nouvelles_urls[cle]:
            supprimer_media_cloudinary(ancienne_url, "image" if cle == "image" else "video")
    return {"message": "Médias du service mis à jour.", "id_service": id_service, "image": service.image, "video": service.video}


# =========================================================
# SUPPRIMER UN SERVICE
# =========================================================

@app.delete("/services/{id_service}")
def supprimer_service(
    id_service: int,
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db),
):
    service = db.query(Service).filter(
        Service.id_service == id_service
    ).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Service introuvable.")

    utilise = db.query(CommandeHasService).filter(
        CommandeHasService.SERVICE_id_service == id_service
    ).first()
    try:
        if utilise:
            service.actif = False
            db.commit()
            return {
                "message": "Le service a été désactivé car il figure dans l'historique des commandes.",
                "action": "desactivation",
                "id_service": id_service,
            }
        db.delete(service)
        db.commit()
    except Exception as erreur:
        db.rollback()
        print("Erreur suppression service :", str(erreur))
        raise HTTPException(status_code=500, detail="Impossible de supprimer le service.")

    return {"message": "Service supprimé avec succès.", "action": "suppression"}


# =========================================================
# ACTIVER / DÉSACTIVER UN SERVICE
# =========================================================

@app.put("/services/{id_service}/actif")
def modifier_statut_service(
    id_service: int,
    actif: bool,
    utilisateur=Depends(
        role_autorise("admin")
    ),
    db: Session = Depends(get_db)
):
    """
    Active ou désactive un service.

    Seul l'administrateur peut modifier ce statut.
    """

    service_existant = db.query(Service).filter(
        Service.id_service == id_service
    ).first()

    if service_existant is None:
        return {
            "message": "Service introuvable"
        }

    service_existant.actif = actif

    db.commit()
    db.refresh(service_existant)

    return {
        "message": (
            "Service activé"
            if actif
            else "Service désactivé"
        ),
        "id_service": id_service,
        "actif": actif
    }





# =========================================================
# ROUTE : CRÉER UNE COMMANDE
# =========================================================

@app.post("/commandes")
def ajouter_commande(
    commande: CommandeCreate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier que le client existe
    # -----------------------------------------------------

    client = db.query(Client).filter(
        Client.id_client == commande.CLIENT_id_client
    ).first()

    if client is None:

        return {
            "message": "Client introuvable"
        }

    # -----------------------------------------------------
    # 2. Créer la commande
    # -----------------------------------------------------

    nouvelle_commande = Commande(
        CLIENT_id_client=commande.CLIENT_id_client,
        date_commande=commande.date_commande,
        statut=commande.statut
    )

    db.add(nouvelle_commande)

    db.commit()

    db.refresh(nouvelle_commande)

    return nouvelle_commande


# =========================================================
# ROUTE : MODIFIER UNE COMMANDE
# =========================================================

@app.put("/commandes/{id_commande}")
def modifier_commande(
    id_commande: int,
    commande: CommandeUpdate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Rechercher la commande
    # -----------------------------------------------------

    commande_existante = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande_existante is None:

        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # 2. Vérifier le client
    # -----------------------------------------------------

    client = db.query(Client).filter(
        Client.id_client == commande.CLIENT_id_client
    ).first()

    if client is None:

        return {
            "message": "Client introuvable"
        }

    # -----------------------------------------------------
    # 3. Modifier la commande
    # -----------------------------------------------------

    commande_existante.CLIENT_id_client = (
        commande.CLIENT_id_client
    )

    commande_existante.date_commande = (
        commande.date_commande
    )

    commande_existante.statut = commande.statut

    # -----------------------------------------------------
    # 4. Enregistrer
    # -----------------------------------------------------

    db.commit()

    db.refresh(commande_existante)

    return commande_existante


# =========================================================
# ROUTE : SUPPRIMER UNE COMMANDE
# =========================================================

@app.delete("/commandes/{id_commande}")
def supprimer_commande(
    id_commande: int,
    utilisateur=Depends(role_autorise("admin", "vendeur")),
    db: Session = Depends(get_db),
):
    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")

    try:
        # Supprimer les dépendances avant la commande pour respecter
        # les clés étrangères sur PostgreSQL et SQL Server.
        for modele in (CommandeHasProduit, CommandeHasService, MessageCommande, Paiement):
            lignes = db.query(modele).filter(
                modele.COMMANDE_id_commande == id_commande
            ).all()
            for ligne in lignes:
                db.delete(ligne)
        db.delete(commande)
        db.commit()
    except Exception as erreur:
        db.rollback()
        print("Erreur suppression commande :", str(erreur))
        raise HTTPException(status_code=500, detail="Impossible de supprimer la commande et ses éléments associés.")

    return {"message": f"Commande {id_commande} supprimée avec succès."}


# =========================================================
# ROUTE : LISTER LES COMMANDES
# =========================================================

@app.get("/commandes")
def liste_commandes(
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    commandes = db.query(Commande).all()

    return commandes


# =========================================================
# ROUTE : AJOUTER UN PRODUIT À UNE COMMANDE
# =========================================================

@app.post("/commandes/{id_commande}/produits")
def ajouter_produit_commande(
    id_commande: int,
    produit: CommandeHasProduitCreate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier la commande
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:

        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # 2. Vérifier le produit
    # -----------------------------------------------------

    produit_existant = db.query(Produit).filter(
        Produit.id_produit
        == produit.PRODUIT_id_produit
    ).first()

    if produit_existant is None:

        return {
            "message": "Produit introuvable"
        }

    # -----------------------------------------------------
    # 3. Vérifier si le produit existe déjà
    # -----------------------------------------------------

    deja_present = db.query(
        CommandeHasProduit
    ).filter(
        CommandeHasProduit.COMMANDE_id_commande
        == id_commande,

        CommandeHasProduit.PRODUIT_id_produit
        == produit.PRODUIT_id_produit
    ).first()

    if deja_present is not None:

        return {
            "message": (
                "Ce produit est déjà dans "
                "cette commande"
            )
        }

    # -----------------------------------------------------
    # 4. Créer la ligne
    # -----------------------------------------------------

    nouvelle_ligne = CommandeHasProduit(
        COMMANDE_id_commande=id_commande,
        PRODUIT_id_produit=produit.PRODUIT_id_produit,
        quantite=produit.quantite,
        prix_unitaire=produit_existant.prix_unitaire
    )

    db.add(nouvelle_ligne)

    db.commit()

    db.refresh(nouvelle_ligne)

    return {
        "message": (
            "Produit ajouté à la commande "
            "avec succès"
        ),
        "id_commande": id_commande,
        "id_produit": (
            produit.PRODUIT_id_produit
        ),
        "quantite": produit.quantite,
        "prix_unitaire": (
            nouvelle_ligne.prix_unitaire
        )
    }


# =========================================================
# ROUTE : LISTER LES PRODUITS D'UNE COMMANDE
# =========================================================

@app.get("/commandes/{id_commande}/produits")
def liste_produits_commande(
    id_commande: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier la commande
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:

        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # 2. Récupérer les lignes
    # -----------------------------------------------------

    lignes = (
        db.query(
            Produit,
            CommandeHasProduit.quantite,
            CommandeHasProduit.prix_unitaire
        )
        .join(
            CommandeHasProduit,
            Produit.id_produit
            == CommandeHasProduit.PRODUIT_id_produit
        )
        .filter(
            CommandeHasProduit.COMMANDE_id_commande
            == id_commande
        )
        .all()
    )

    # -----------------------------------------------------
    # 3. Vérifier si la commande contient des produits
    # -----------------------------------------------------

    if not lignes:

        return {
            "id_commande": id_commande,
            "produits": [],
            "total_commande": 0,
            "message": (
                "Aucun produit dans cette commande"
            )
        }

    # -----------------------------------------------------
    # 4. Calculer les montants
    # -----------------------------------------------------

    resultats = []

    total_commande = 0

    for produit, quantite, prix_unitaire in lignes:

        montant = prix_unitaire * quantite

        resultats.append({
            "id_produit": produit.id_produit,
            "designation": produit.designation,

            # Image du produit
            "image": produit.image,

            "prix_unitaire": prix_unitaire,
            "quantite": quantite,
            "montant": montant
        })

        total_commande += montant

    # -----------------------------------------------------
    # 5. Retourner le résultat
    # -----------------------------------------------------

    return {
        "id_commande": id_commande,
        "produits": resultats,
        "total_commande": total_commande
    }


# =========================================================
# ROUTE : SUPPRIMER UN PRODUIT D'UNE COMMANDE
# =========================================================

@app.delete(
    "/commandes/{id_commande}/produits/{id_produit}"
)
def supprimer_produit_commande(
    id_commande: int,
    id_produit: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier la commande
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:

        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # 2. Vérifier le produit
    # -----------------------------------------------------

    produit = db.query(Produit).filter(
        Produit.id_produit == id_produit
    ).first()

    if produit is None:

        return {
            "message": "Produit introuvable"
        }

    # -----------------------------------------------------
    # 3. Rechercher la ligne
    # -----------------------------------------------------

    ligne = db.query(
        CommandeHasProduit
    ).filter(
        CommandeHasProduit.COMMANDE_id_commande
        == id_commande,

        CommandeHasProduit.PRODUIT_id_produit
        == id_produit
    ).first()

    if ligne is None:

        return {
            "message": (
                "Ce produit ne fait pas partie "
                "de cette commande"
            )
        }

    # -----------------------------------------------------
    # 4. Supprimer la relation
    # -----------------------------------------------------

    db.delete(ligne)

    db.commit()

    return {
        "message": (
            "Produit retiré de la commande "
            "avec succès"
        ),
        "id_commande": id_commande,
        "id_produit": id_produit
    }


# =========================================================
# ROUTE : MODIFIER LA QUANTITÉ D'UN PRODUIT
# =========================================================

@app.put(
    "/commandes/{id_commande}/produits/{id_produit}"
)
def modifier_quantite_produit_commande(
    id_commande: int,
    id_produit: int,
    modification: CommandeHasProduitUpdate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier la commande
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:

        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # 2. Vérifier le produit
    # -----------------------------------------------------

    produit = db.query(Produit).filter(
        Produit.id_produit == id_produit
    ).first()

    if produit is None:

        return {
            "message": "Produit introuvable"
        }

    # -----------------------------------------------------
    # 3. Rechercher la ligne
    # -----------------------------------------------------

    ligne = db.query(
        CommandeHasProduit
    ).filter(
        CommandeHasProduit.COMMANDE_id_commande
        == id_commande,

        CommandeHasProduit.PRODUIT_id_produit
        == id_produit
    ).first()

    if ligne is None:

        return {
            "message": (
                "Ce produit ne fait pas partie "
                "de cette commande"
            )
        }

    # -----------------------------------------------------
    # 4. Vérifier la quantité
    # -----------------------------------------------------

    if modification.quantite <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "La quantité doit être "
                "supérieure à zéro."
            )
        )

    # -----------------------------------------------------
    # 5. Modifier la quantité
    # -----------------------------------------------------

    ligne.quantite = modification.quantite

    db.commit()

    db.refresh(ligne)

    return {
        "message": (
            "Quantité modifiée avec succès"
        ),
        "id_commande": id_commande,
        "id_produit": id_produit,
        "nouvelle_quantite": ligne.quantite
    }


# =========================================================
# =========================================================
# GESTION DES SERVICES DANS UNE COMMANDE
# =========================================================
# =========================================================


# =========================================================
# AJOUTER UN SERVICE À UNE COMMANDE
# =========================================================

@app.post("/commandes/{id_commande}/services")
def ajouter_service_commande(
    id_commande: int,
    service: CommandeHasServiceCreate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):
    """
    Ajoute un service à une commande existante.

    Le prix enregistré dans la commande est le prix
    du service au moment de l'ajout.
    """

    # -----------------------------------------------------
    # Vérifier que la commande existe
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:
        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # Vérifier que le service existe
    # -----------------------------------------------------

    service_existant = db.query(Service).filter(
        Service.id_service == service.SERVICE_id_service
    ).first()

    if service_existant is None:
        return {
            "message": "Service introuvable"
        }

    # -----------------------------------------------------
    # Vérifier que le service est actif
    # -----------------------------------------------------

    if not service_existant.actif:
        return {
            "message": "Ce service est actuellement indisponible"
        }

    # -----------------------------------------------------
    # Vérifier si le service est déjà présent
    # -----------------------------------------------------

    deja_present = db.query(
        CommandeHasService
    ).filter(
        CommandeHasService.COMMANDE_id_commande == id_commande,
        CommandeHasService.SERVICE_id_service ==
        service.SERVICE_id_service
    ).first()

    if deja_present is not None:
        return {
            "message": (
                "Ce service est déjà présent "
                "dans cette commande"
            )
        }

    # -----------------------------------------------------
    # Créer la ligne de commande
    # -----------------------------------------------------

    nouvelle_ligne = CommandeHasService(
        COMMANDE_id_commande=id_commande,
        SERVICE_id_service=service.SERVICE_id_service,
        quantite=service.quantite,
        prix_unitaire=service_existant.prix
    )

    db.add(nouvelle_ligne)
    db.commit()
    db.refresh(nouvelle_ligne)

    return {
        "message": "Service ajouté à la commande avec succès",
        "id_commande": id_commande,
        "id_service": service.SERVICE_id_service,
        "quantite": service.quantite,
        "prix_unitaire": nouvelle_ligne.prix_unitaire
    }


# =========================================================
# MODIFIER LA QUANTITÉ D'UN SERVICE DANS UNE COMMANDE
# =========================================================

@app.put(
    "/commandes/{id_commande}/services/{id_service}"
)
def modifier_service_commande(
    id_commande: int,
    id_service: int,
    service: CommandeHasServiceUpdate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):
    """
    Modifie la quantité d'un service dans une commande.
    """

    ligne = db.query(CommandeHasService).filter(
        CommandeHasService.COMMANDE_id_commande == id_commande,
        CommandeHasService.SERVICE_id_service == id_service
    ).first()

    if ligne is None:
        return {
            "message": "Service introuvable dans cette commande"
        }

    ligne.quantite = service.quantite

    db.commit()
    db.refresh(ligne)

    return {
        "message": "Quantité du service modifiée avec succès",
        "id_commande": id_commande,
        "id_service": id_service,
        "quantite": ligne.quantite,
        "prix_unitaire": ligne.prix_unitaire
    }



# =========================================================
# CONNEXION UTILISATEUR
# =========================================================

@app.post("/login")
def login_utilisateur(
    identifiants: UtilisateurLogin,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Rechercher l'utilisateur
    # -----------------------------------------------------

    utilisateur = db.query(Utilisateur).filter(
        Utilisateur.email == identifiants.email
    ).first()

    if utilisateur is None:

        raise HTTPException(
            status_code=401,
            detail=(
                "Email ou mot de passe incorrect"
            )
        )

    # -----------------------------------------------------
    # 2. Vérifier le mot de passe
    # -----------------------------------------------------

    mot_de_passe_valide = bcrypt.checkpw(
        identifiants.mot_de_passe.encode("utf-8"),
        utilisateur.mot_de_passe.encode("utf-8")
    )

    if not mot_de_passe_valide:

        raise HTTPException(
            status_code=401,
            detail=(
                "Email ou mot de passe incorrect"
            )
        )

    # -----------------------------------------------------
    # 3. Créer le token
    # -----------------------------------------------------

    token = creer_token(utilisateur)

    # -----------------------------------------------------
    # 4. Retourner les informations
    # -----------------------------------------------------

    return {

        "message": "Connexion réussie",

        "access_token": token,

        "token_type": "bearer",

        "id_utilisateur":
            utilisateur.id_utilisateur,

        "nom":
            utilisateur.nom,

        "prenom":
            utilisateur.prenom,

        "email":
            utilisateur.email,

        "role":
            utilisateur.role
    }


# =========================================================
# INSCRIPTION D'UN NOUVEAU CLIENT
# =========================================================

@app.post("/utilisateurs")
def creer_utilisateur(
    utilisateur: UtilisateurClientCreate,
    db: Session = Depends(get_db)
):
    """
    Création d'un compte client depuis la page
    publique "Créer un compte".
    """

    # ---------------------------------------------------------
    # 1. Vérifier si l'adresse email existe déjà
    # ---------------------------------------------------------

    utilisateur_existant = db.query(Utilisateur).filter(
        func.lower(Utilisateur.email) == utilisateur.email.strip().lower()
    ).first()

    if utilisateur_existant is not None:
        raise HTTPException(
            status_code=400,
            detail="Cette adresse email est déjà utilisée."
        )

    # ---------------------------------------------------------
    # 2. Hasher le mot de passe
    # ---------------------------------------------------------

    mot_de_passe_hash = bcrypt.hashpw(
        utilisateur.mot_de_passe.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    # ---------------------------------------------------------
    # 3. Créer l'utilisateur
    # ---------------------------------------------------------

    nouvel_utilisateur = Utilisateur(
        nom=utilisateur.nom,
        prenom=utilisateur.prenom,
        email=utilisateur.email,
        mot_de_passe=mot_de_passe_hash,
        role="client"
    )

    db.add(nouvel_utilisateur)

    # flush permet d'obtenir l'id_utilisateur
    # avant le commit final
    db.flush()

    # ---------------------------------------------------------
    # 4. Créer la fiche CLIENT correspondante
    # ---------------------------------------------------------

    nouveau_client = Client(
        nom=utilisateur.nom,
        prenom=utilisateur.prenom,
        date_naissance=utilisateur.date_naissance,
        email=utilisateur.email,
        telephone=utilisateur.telephone,
        latitude=utilisateur.latitude,
        longitude=utilisateur.longitude,
        id_utilisateur=nouvel_utilisateur.id_utilisateur
    )

    db.add(nouveau_client)

    # ---------------------------------------------------------
    # 5. Enregistrer définitivement les deux lignes
    # ---------------------------------------------------------

    db.commit()

    # Actualiser les objets après le commit
    db.refresh(nouvel_utilisateur)
    db.refresh(nouveau_client)

    # ---------------------------------------------------------
    # 6. Réponse
    # ---------------------------------------------------------

    return {
        "message": "Compte client créé avec succès.",
        "id_utilisateur": nouvel_utilisateur.id_utilisateur,
        "id_client": nouveau_client.id_client,
        "nom": nouvel_utilisateur.nom,
        "prenom": nouvel_utilisateur.prenom,
        "email": nouvel_utilisateur.email,
        "telephone": nouveau_client.telephone,
        "date_naissance": nouveau_client.date_naissance,
        "role": nouvel_utilisateur.role
    }


# =========================================================
# LISTE DES UTILISATEURS
# =========================================================

@app.get("/utilisateurs")
def liste_utilisateurs(
    utilisateur=Depends(
        role_autorise("admin")
    ),
    db: Session = Depends(get_db)
):

    utilisateurs = db.query(Utilisateur).all()

    return [

        {
            "id_utilisateur":
                utilisateur.id_utilisateur,

            "nom":
                utilisateur.nom,

            "prenom":
                utilisateur.prenom,

            "email":
                utilisateur.email,

            "role":
                utilisateur.role
        }

        for utilisateur in utilisateurs
    ]


# =========================================================
# CRÉATION D'UN UTILISATEUR PAR L'ADMINISTRATEUR
# =========================================================

@app.post("/utilisateurs/admin")
def creer_utilisateur_admin(
    utilisateur: UtilisateurCreate,
    utilisateur_connecte=Depends(role_autorise("admin")),
    db: Session = Depends(get_db),
):
    roles_autorises = {"admin", "vendeur", "client"}
    role = (utilisateur.role or "").strip().lower()
    if role not in roles_autorises:
        raise HTTPException(status_code=400, detail="Rôle invalide.")

    email = utilisateur.email.strip().lower()
    existant = db.query(Utilisateur).filter(
        func.lower(Utilisateur.email) == email
    ).first()
    if existant:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    mot_de_passe_hash = bcrypt.hashpw(
        utilisateur.mot_de_passe.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    nouvel_utilisateur = Utilisateur(
        nom=utilisateur.nom.strip(),
        prenom=utilisateur.prenom.strip(),
        email=email,
        mot_de_passe=mot_de_passe_hash,
        role=role,
    )

    try:
        db.add(nouvel_utilisateur)
        db.flush()
        nouveau_client = None
        if role == "client":
            nouveau_client = Client(
                nom=nouvel_utilisateur.nom,
                prenom=nouvel_utilisateur.prenom,
                email=email,
                telephone=None,
                date_naissance=None,
                id_utilisateur=nouvel_utilisateur.id_utilisateur,
            )
            db.add(nouveau_client)
        db.commit()
        db.refresh(nouvel_utilisateur)
        if nouveau_client is not None:
            db.refresh(nouveau_client)
    except Exception as erreur:
        db.rollback()
        print("Erreur création utilisateur admin :", str(erreur))
        raise HTTPException(status_code=500, detail="Impossible de créer cet utilisateur.")

    resultat = {
        "message": "Utilisateur créé avec succès.",
        "id_utilisateur": nouvel_utilisateur.id_utilisateur,
        "nom": nouvel_utilisateur.nom,
        "prenom": nouvel_utilisateur.prenom,
        "email": nouvel_utilisateur.email,
        "role": nouvel_utilisateur.role,
    }
    if nouveau_client is not None:
        resultat["id_client"] = nouveau_client.id_client
    return resultat


# =========================================================
# 👤 ESPACE MON COMPTE
# =========================================================


# =========================================================
# 1. CONSULTER SON PROPRE PROFIL
# =========================================================

@app.get("/mon-compte")
def obtenir_mon_compte(

    utilisateur=Depends(
        role_autorise(
            "admin",
            "vendeur",
            "client"
        )
    ),

    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Récupérer l'utilisateur connecté
    # -----------------------------------------------------

    utilisateur_existant = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id_utilisateur
            == utilisateur.id_utilisateur
        )
        .first()
    )

    if utilisateur_existant is None:

        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable."
        )


    # -----------------------------------------------------
    # Chercher éventuellement sa fiche client
    # -----------------------------------------------------

    client = (
        db.query(Client)
        .filter(
            Client.id_utilisateur
            == utilisateur_existant.id_utilisateur
        )
        .first()
    )


    # -----------------------------------------------------
    # Retourner uniquement les informations nécessaires
    #
    # IMPORTANT :
    # Le mot de passe n'est jamais retourné.
    # -----------------------------------------------------

    return {

        "id_utilisateur":
            utilisateur_existant.id_utilisateur,

        "nom":
            utilisateur_existant.nom,

        "prenom":
            utilisateur_existant.prenom,

        "email":
            utilisateur_existant.email,

        "role":
            utilisateur_existant.role,

        "telephone":
            client.telephone
            if client
            else None,

        "date_naissance":
            (
                str(client.date_naissance)
                if client
                and client.date_naissance
                else None
            ),

        "latitude":
            client.latitude
            if client
            else None,

        "longitude":
            client.longitude
            if client
            else None
    }


# =========================================================
# 2. MODIFIER SON PROFIL
# =========================================================

@app.put("/mon-compte")
def modifier_mon_compte(

    donnees: MonCompteUpdate,

    utilisateur=Depends(
        role_autorise(
            "admin",
            "vendeur",
            "client"
        )
    ),

    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Récupérer l'utilisateur connecté
    # -----------------------------------------------------

    utilisateur_existant = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id_utilisateur
            == utilisateur.id_utilisateur
        )
        .first()
    )


    if utilisateur_existant is None:

        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable."
        )


    # -----------------------------------------------------
    # Nettoyer l'adresse email
    # -----------------------------------------------------

    email = donnees.email.strip().lower()


    # -----------------------------------------------------
    # Vérifier que l'email n'est pas déjà utilisé
    # par un autre utilisateur
    # -----------------------------------------------------

    autre_utilisateur = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.email == email,
            Utilisateur.id_utilisateur
            != utilisateur_existant.id_utilisateur
        )
        .first()
    )


    if autre_utilisateur is not None:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cette adresse email est déjà "
                "utilisée par un autre compte."
            )
        )


    # -----------------------------------------------------
    # Modifier les informations principales
    # -----------------------------------------------------

    utilisateur_existant.nom = (
        donnees.nom.strip()
    )

    utilisateur_existant.prenom = (
        donnees.prenom.strip()
    )

    utilisateur_existant.email = email


    # -----------------------------------------------------
    # Chercher la fiche CLIENT
    # -----------------------------------------------------

    client = (
        db.query(Client)
        .filter(
            Client.id_utilisateur
            == utilisateur_existant.id_utilisateur
        )
        .first()
    )


    # -----------------------------------------------------
    # Les informations suivantes appartiennent
    # à la fiche CLIENT
    # -----------------------------------------------------

    if client is not None:

        client.telephone = (
            donnees.telephone.strip()
            if donnees.telephone
            else None
        )

        client.date_naissance = (
            donnees.date_naissance
        )

        client.latitude = (
            donnees.latitude
            if donnees.latitude is not None
            else None
        )

        client.longitude = (
            donnees.longitude
            if donnees.longitude is not None
            else None
        )


    # -----------------------------------------------------
    # Enregistrer les modifications
    # -----------------------------------------------------

    try:

        db.commit()

        db.refresh(
            utilisateur_existant
        )

        if client is not None:

            db.refresh(client)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de la modification du profil."
            )
        )


    # -----------------------------------------------------
    # Réponse
    # -----------------------------------------------------

    return {

        "success": True,

        "message":
            "Votre profil a été mis à jour avec succès.",

        "id_utilisateur":
            utilisateur_existant.id_utilisateur,

        "nom":
            utilisateur_existant.nom,

        "prenom":
            utilisateur_existant.prenom,

        "email":
            utilisateur_existant.email,

        "role":
            utilisateur_existant.role,

        "telephone":
            client.telephone
            if client
            else None,

        "date_naissance":
            (
                str(client.date_naissance)
                if client
                and client.date_naissance
                else None
            ),

        "latitude":
            client.latitude
            if client
            else None,

        "longitude":
            client.longitude
            if client
            else None
    }


# =========================================================
# 3. MODIFIER SON MOT DE PASSE
# =========================================================

@app.put("/mon-compte/mot-de-passe")
def modifier_mon_mot_de_passe(

    donnees: MotDePasseUpdate,

    utilisateur=Depends(
        role_autorise(
            "admin",
            "vendeur",
            "client"
        )
    ),

    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Vérifier que les deux nouveaux mots de passe
    # correspondent
    # -----------------------------------------------------

    if (
        donnees.nouveau_mot_de_passe
        != donnees.confirmation_mot_de_passe
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Les nouveaux mots de passe "
                "ne correspondent pas."
            )
        )


    # -----------------------------------------------------
    # Vérifier la longueur minimale
    # -----------------------------------------------------

    if len(
        donnees.nouveau_mot_de_passe
    ) < 8:

        raise HTTPException(
            status_code=400,
            detail=(
                "Le nouveau mot de passe doit "
                "contenir au moins 8 caractères."
            )
        )


    # -----------------------------------------------------
    # Récupérer l'utilisateur connecté
    # -----------------------------------------------------

    utilisateur_existant = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id_utilisateur
            == utilisateur.id_utilisateur
        )
        .first()
    )


    if utilisateur_existant is None:

        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable."
        )


    # -----------------------------------------------------
    # Vérifier l'ancien mot de passe
    # -----------------------------------------------------

    ancien_mot_de_passe_valide = (
        bcrypt.checkpw(
            donnees.ancien_mot_de_passe.encode(
                "utf-8"
            ),
            utilisateur_existant.mot_de_passe.encode(
                "utf-8"
            )
        )
    )


    if not ancien_mot_de_passe_valide:

        raise HTTPException(
            status_code=400,
            detail=(
                "L'ancien mot de passe est incorrect."
            )
        )


    # -----------------------------------------------------
    # Empêcher de réutiliser exactement le même
    # mot de passe
    # -----------------------------------------------------

    if bcrypt.checkpw(
        donnees.nouveau_mot_de_passe.encode(
            "utf-8"
        ),
        utilisateur_existant.mot_de_passe.encode(
            "utf-8"
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Le nouveau mot de passe doit "
                "être différent de l'ancien."
            )
        )


    # -----------------------------------------------------
    # Hasher le nouveau mot de passe
    # -----------------------------------------------------

    nouveau_hash = bcrypt.hashpw(
        donnees.nouveau_mot_de_passe.encode(
            "utf-8"
        ),
        bcrypt.gensalt()
    ).decode("utf-8")


    utilisateur_existant.mot_de_passe = (
        nouveau_hash
    )


    # -----------------------------------------------------
    # Enregistrer
    # -----------------------------------------------------

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de la modification du mot de passe."
            )
        )


    # -----------------------------------------------------
    # Réponse
    # -----------------------------------------------------

    return {

        "success": True,

        "message":
            "Votre mot de passe a été modifié "
            "avec succès."
    }



# =========================================================
# 💳 MÉTHODES DE PAIEMENT AUTORISÉES
# =========================================================

METHODES_PAIEMENT = [

    "livraison",

    "wave",

    "orange_money",

    "carte"
]


# =========================================================
# VALIDER LE PANIER ET CRÉER LA COMMANDE
# =========================================================
#
# Cette route permet maintenant de créer UNE SEULE
# commande contenant :
#
# - des produits
# - des services
# - ou des produits ET des services
#
# Exemple de panier :
#
#   2 × Produit A
#   1 × Produit B
#   1 × Service nettoyage
#
# donnera :
#
#   COMMANDE
#      ├── COMMANDE_has_PRODUIT
#      │       ├── Produit A × 2
#      │       └── Produit B × 1
#      │
#      └── COMMANDE_has_SERVICE
#              └── Service nettoyage × 1
#
# =========================================================

@app.post("/commandes/depuis-panier")
def creer_commande_depuis_panier(
    panier: CommandeDepuisPanierCreate,
    utilisateur=Depends(role_autorise("client")),
    db: Session = Depends(get_db)
):
    """Crée une commande unique contenant produits et/ou services."""
    if panier.methode_paiement not in METHODES_PAIEMENT:
        raise HTTPException(status_code=400, detail="Mode de paiement invalide.")

    lignes_panier = list(panier.lignes or [])
    services_panier = list(panier.services or [])
    if not lignes_panier and not services_panier:
        raise HTTPException(status_code=400, detail="Le panier est vide.")

    client = db.query(Client).filter(
        Client.id_utilisateur == utilisateur.id_utilisateur
    ).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Aucun client associé à cet utilisateur.")

    # Regrouper les lignes identiques pour éviter les doublons et valider
    # le stock total demandé pour chaque produit.
    quantites_produits = {}
    for ligne in lignes_panier:
        qte = int(ligne.quantite)
        if qte <= 0:
            raise HTTPException(status_code=400, detail="Chaque quantité doit être supérieure à zéro.")
        quantites_produits[ligne.id_produit] = quantites_produits.get(ligne.id_produit, 0) + qte

    produits_commandes = []
    for id_produit, quantite in quantites_produits.items():
        produit = db.query(Produit).filter(
            Produit.id_produit == id_produit
        ).with_for_update().first()
        if produit is None:
            raise HTTPException(status_code=404, detail=f"Le produit {id_produit} n'existe pas.")
        if not produit.actif:
            raise HTTPException(status_code=400, detail=f"Le produit « {produit.designation} » n'est plus disponible.")
        stock = int(produit.stock or 0)
        if stock < quantite:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant pour « {produit.designation} ». Stock disponible : {stock}.",
            )
        produits_commandes.append((produit, quantite, stock))

    quantites_services = {}
    for ligne in services_panier:
        qte = int(ligne.quantite)
        if qte <= 0:
            raise HTTPException(status_code=400, detail="Chaque quantité de service doit être supérieure à zéro.")
        quantites_services[ligne.id_service] = quantites_services.get(ligne.id_service, 0) + qte

    services_commandes = []
    for id_service, quantite in quantites_services.items():
        service = db.query(Service).filter(
            Service.id_service == id_service
        ).first()
        if service is None:
            raise HTTPException(status_code=404, detail=f"Le service {id_service} n'existe pas.")
        if not service.actif:
            raise HTTPException(status_code=400, detail=f"Le service « {service.nom_service} » n'est plus disponible.")
        services_commandes.append((service, quantite))

    total_commande = 0
    nouvelle_commande = Commande(
        date_commande=date.today(),
        CLIENT_id_client=client.id_client,
        latitude=panier.latitude,
        longitude=panier.longitude,
        statut="en_attente",
    )

    if panier.latitude is not None and panier.longitude is not None:
        client.latitude = panier.latitude
        client.longitude = panier.longitude

    try:
        db.add(nouvelle_commande)
        db.flush()  # Obtient l'identifiant avant de créer les lignes.

        for produit, quantite, ancien_stock in produits_commandes:
            prix = produit.prix_unitaire
            db.add(CommandeHasProduit(
                COMMANDE_id_commande=nouvelle_commande.id_commande,
                PRODUIT_id_produit=produit.id_produit,
                quantite=quantite,
                prix_unitaire=prix,
            ))
            produit.stock = ancien_stock - quantite
            verifier_stock_faible(db, produit, ancien_stock, seuil=5)
            total_commande += float(prix or 0) * quantite

        for service, quantite in services_commandes:
            prix = service.prix
            db.add(CommandeHasService(
                COMMANDE_id_commande=nouvelle_commande.id_commande,
                SERVICE_id_service=service.id_service,
                quantite=quantite,
                prix_unitaire=prix,
            ))
            total_commande += float(prix or 0) * quantite

        nouveau_paiement = Paiement(
            COMMANDE_id_commande=nouvelle_commande.id_commande,
            UTILISATEUR_id_utilisateur=utilisateur.id_utilisateur,
            montant=total_commande,
            methode=panier.methode_paiement,
            statut="en_attente",
            reference=None,
        )
        db.add(nouveau_paiement)

        creer_notification(
            db=db,
            id_utilisateur=utilisateur.id_utilisateur,
            titre="Commande enregistrée",
            message=f"Votre commande #{nouvelle_commande.id_commande} a été enregistrée.",
            type_notification="success",
            lien="/mes-commandes",
        )
        destinataires = db.query(Utilisateur).filter(
            Utilisateur.role.in_(["admin", "vendeur"])
        ).all()
        for destinataire in destinataires:
            creer_notification(
                db=db,
                id_utilisateur=destinataire.id_utilisateur,
                titre="Nouvelle commande",
                message=f"La commande #{nouvelle_commande.id_commande} vient d'être passée.",
                type_notification="commande",
                lien="/commandes",
            )

        db.commit()
        db.refresh(nouvelle_commande)
        db.refresh(nouveau_paiement)

    except HTTPException:
        db.rollback()
        raise
    except Exception as erreur:
        db.rollback()
        print("Erreur création commande depuis panier :", str(erreur))
        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer la commande et son paiement. Réessayez.",
        )

    return {
        "message": "Commande et paiement enregistrés avec succès.",
        "id_commande": nouvelle_commande.id_commande,
        "id_client": client.id_client,
        "date_commande": str(nouvelle_commande.date_commande),
        "statut": nouvelle_commande.statut,
        "nombre_produits": len(produits_commandes),
        "nombre_services": len(services_commandes),
        "total": total_commande,
        "id_paiement": nouveau_paiement.id_paiement,
        "methode_paiement": nouveau_paiement.methode,
        "statut_paiement": nouveau_paiement.statut,
        "reference_paiement": nouveau_paiement.reference,
        "latitude": nouvelle_commande.latitude,
        "longitude": nouvelle_commande.longitude,
    }


# 📦 ALERTE AUTOMATIQUE — STOCK FAIBLE
# =========================================================

def verifier_stock_faible(
    db,
    produit,
    ancien_stock,
    seuil=5
):
    """
    Crée une alerte uniquement lorsque le stock
    passe du-dessus du seuil à un niveau inférieur
    ou égal au seuil.
    """

    if produit is None:
        return

    nouveau_stock = produit.stock or 0

    # -----------------------------------------------------
    # Le stock doit franchir le seuil
    # -----------------------------------------------------

    if not (
        ancien_stock > seuil
        and nouveau_stock <= seuil
    ):
        return

    # -----------------------------------------------------
    # Administrateurs + vendeurs
    # -----------------------------------------------------

    destinataires = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.role.in_(
                ["admin", "vendeur"]
            )
        )
        .all()
    )

    # -----------------------------------------------------
    # Notification
    # -----------------------------------------------------

    for destinataire in destinataires:

        creer_notification(
            db=db,
            id_utilisateur=(
                destinataire.id_utilisateur
            ),
            titre="⚠️ Stock faible",
            message=(
                f"Le produit « {produit.designation} » "
                f"vient de passer à {nouveau_stock} "
                "unité(s) en stock."
            ),
            type_notification="stock",
            lien="/produits"
        )


# =========================================================
# 🧹 NETTOYAGE AUTOMATIQUE DES NOTIFICATIONS
# =========================================================

def nettoyer_notifications(
    db,
    id_utilisateur,
    nombre_a_conserver=30
):
    """
    Conserve uniquement les notifications les plus récentes
    d'un utilisateur.

    Les anciennes notifications sont supprimées
    automatiquement.
    """

    # -----------------------------------------------------
    # Récupérer les notifications de l'utilisateur
    # -----------------------------------------------------

    notifications = (
        db.query(Notification)
        .filter(
            Notification.UTILISATEUR_id_utilisateur
            == id_utilisateur
        )
        .order_by(
            Notification.date_notification.desc()
        )
        .all()
    )

    # -----------------------------------------------------
    # Rien à supprimer si la limite n'est pas dépassée
    # -----------------------------------------------------

    if len(notifications) <= nombre_a_conserver:
        return

    # -----------------------------------------------------
    # Les notifications après les 30 plus récentes
    # doivent être supprimées
    # -----------------------------------------------------

    anciennes_notifications = (
        notifications[nombre_a_conserver:]
    )

    for notification in anciennes_notifications:

        db.delete(notification)


# =========================================================
# COMMANDES DU CLIENT CONNECTÉ
# =========================================================

# =========================================================
# MES COMMANDES - CLIENT
# PRODUITS + SERVICES
# =========================================================

@app.get("/mes-commandes")
def mes_commandes(

    utilisateur=Depends(
        role_autorise("client")
    ),

    db: Session = Depends(get_db)
):

    # =====================================================
    # 1. RECHERCHER LE CLIENT CONNECTÉ
    # =====================================================

    client = db.query(Client).filter(

        Client.id_utilisateur
        == utilisateur.id_utilisateur

    ).first()


    if client is None:

        raise HTTPException(

            status_code=404,

            detail=(
                "Aucun client associé "
                "à cet utilisateur."
            )

        )


    # =====================================================
    # 2. RÉCUPÉRER LES COMMANDES
    # =====================================================

    commandes = (

        db.query(Commande)

        .filter(

            Commande.CLIENT_id_client
            == client.id_client

        )

        .order_by(

            Commande.date_commande.desc()

        )

        .all()

    )


    # =====================================================
    # 3. PRÉPARER LE RÉSULTAT
    # =====================================================

    resultat = []


    # =====================================================
    # 4. PARCOURIR LES COMMANDES
    # =====================================================

    for commande in commandes:


        # =================================================
        # PRODUITS
        # =================================================

        lignes_produits = (

            db.query(CommandeHasProduit)

            .filter(

                CommandeHasProduit
                .COMMANDE_id_commande
                == commande.id_commande

            )

            .all()

        )


        produits = []


        # =================================================
        # SERVICES
        # =================================================

        lignes_services = (

            db.query(CommandeHasService)

            .filter(

                CommandeHasService
                .COMMANDE_id_commande
                == commande.id_commande

            )

            .all()

        )


        services = []


        # =================================================
        # TOTAL DE LA COMMANDE
        # =================================================

        total_commande = 0


        # =================================================
        # 5. TRAITER LES PRODUITS
        # =================================================

        for ligne in lignes_produits:


            produit = db.query(Produit).filter(

                Produit.id_produit
                == ligne.PRODUIT_id_produit

            ).first()


            if produit is None:

                continue


            # ---------------------------------------------
            # Sous-total produit
            # ---------------------------------------------

            sous_total = (

                float(ligne.prix_unitaire)

                * int(ligne.quantite)

            )


            total_commande += sous_total


            # ---------------------------------------------
            # Informations du produit
            # ---------------------------------------------

            produits.append({

                "id_produit":
                    produit.id_produit,

                "designation":
                    produit.designation,

                "image":
                    produit.image,

                "quantite":
                    ligne.quantite,

                "prix_unitaire":
                    ligne.prix_unitaire,

                "sous_total":
                    sous_total

            })


        # =================================================
        # 6. TRAITER LES SERVICES
        # =================================================

        for ligne in lignes_services:


            service = db.query(Service).filter(

                Service.id_service
                == ligne.SERVICE_id_service

            ).first()


            if service is None:

                continue


            # ---------------------------------------------
            # Sous-total service
            # ---------------------------------------------

            sous_total = (

                float(ligne.prix_unitaire)

                * int(ligne.quantite)

            )


            total_commande += sous_total


            # ---------------------------------------------
            # Informations du service
            # ---------------------------------------------

            services.append({

                "id_service":
                    service.id_service,

                "nom_service":
                    service.nom_service,

                "description":
                    service.description,

                "categorie":
                    service.categorie,

                "image":
                    service.image,

                "video":
                    service.video,

                "quantite":
                    ligne.quantite,

                "prix_unitaire":
                    ligne.prix_unitaire,

                "sous_total":
                    sous_total

            })


        # =================================================
        # 7. RÉCUPÉRER LES MESSAGES
        # =================================================

        messages_db = (

            db.query(MessageCommande)

            .filter(

                MessageCommande
                .COMMANDE_id_commande
                == commande.id_commande

            )

            .order_by(

                MessageCommande.date_message.asc()

            )

            .all()

        )


        messages = []


        for msg in messages_db:


            expediteur = db.query(
                Utilisateur
            ).filter(

                Utilisateur.id_utilisateur
                == msg.UTILISATEUR_id_utilisateur

            ).first()


            # ---------------------------------------------
            # Nom de l'expéditeur
            # ---------------------------------------------

            if expediteur:

                nom_expediteur = (

                    expediteur.prenom
                    + " "
                    + expediteur.nom

                )

                role_expediteur = (
                    expediteur.role
                )

            else:

                nom_expediteur = (
                    "Utilisateur inconnu"
                )

                role_expediteur = ""


            messages.append({

                "id_message":
                    msg.id_message,

                "message":
                    msg.message,

                "audio_url":
                    msg.audio_url,

                "date_message":
                    str(msg.date_message),

                "lu":
                    msg.lu,

                "id_expediteur":
                    msg.UTILISATEUR_id_utilisateur,

                "nom_expediteur":
                    nom_expediteur,

                "role_expediteur":
                    role_expediteur

            })


        # =================================================
        # 8. AJOUTER LA COMMANDE AU RÉSULTAT
        # =================================================

        resultat.append({

            "id_commande":
                commande.id_commande,

            "date_commande":
                str(commande.date_commande),

            "statut":
                commande.statut,

            # ---------------------------------------------
            # Produits
            # ---------------------------------------------

            "produits":
                produits,

            # ---------------------------------------------
            # Services
            # ---------------------------------------------

            "services":
                services,

            # ---------------------------------------------
            # Total PRODUITS + SERVICES
            # ---------------------------------------------

            "total":
                total_commande,

            # ---------------------------------------------
            # Messages
            # ---------------------------------------------

            "messages":
                messages

        })


    # =====================================================
    # 9. RETOURNER LES COMMANDES
    # =====================================================

    return resultat


# =========================================================
# ANNULER UNE COMMANDE DU CLIENT CONNECTÉ
# =========================================================

@app.delete("/mes-commandes/{id_commande}/annuler")
def annuler_ma_commande(
    id_commande: int,
    utilisateur=Depends(
        role_autorise("client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Rechercher le client
    # -----------------------------------------------------

    client = db.query(Client).filter(
        Client.id_utilisateur
        == utilisateur.id_utilisateur
    ).first()

    if client is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Aucun client associé "
                "à cet utilisateur."
            )
        )

    # -----------------------------------------------------
    # 2. Rechercher la commande
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:

        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    # -----------------------------------------------------
    # 3. Vérifier l'appartenance
    # -----------------------------------------------------

    if (
        commande.CLIENT_id_client
        != client.id_client
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Vous ne pouvez pas annuler "
                "cette commande."
            )
        )

    # -----------------------------------------------------
    # 4. Vérifier le statut
    # -----------------------------------------------------

    if commande.statut not in [
        "en_attente",
        "confirmee"
    ]:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cette commande ne peut plus "
                "être annulée car son statut est "
                f"« {commande.statut} »."
            )
        )

    # -----------------------------------------------------
    # 5. Vérifier le délai
    # -----------------------------------------------------

    date_commande = commande.date_commande
    if isinstance(date_commande, datetime):
        date_commande = date_commande.date()
    jours_ecoules = (date.today() - date_commande).days

    if jours_ecoules > 2:

        raise HTTPException(
            status_code=400,
            detail=(
                "Le délai de 2 jours pour annuler "
                "cette commande est dépassé."
            )
        )

    # -----------------------------------------------------
    # 6. Récupérer les produits
    # -----------------------------------------------------

    lignes = db.query(
        CommandeHasProduit
    ).filter(
        CommandeHasProduit.COMMANDE_id_commande
        == commande.id_commande
    ).all()

    # -----------------------------------------------------
    # 7. Restaurer le stock
    # -----------------------------------------------------

    for ligne in lignes:

        produit = db.query(Produit).filter(
            Produit.id_produit
            == ligne.PRODUIT_id_produit
        ).first()

        if produit is not None:

            produit.stock += ligne.quantite

    # -----------------------------------------------------
    # 8. Modifier le statut
    # -----------------------------------------------------

    commande.statut = "annulee"

    # -----------------------------------------------------
    # 9. Enregistrer
    # -----------------------------------------------------

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de l'annulation de la commande."
            )
        )

    db.refresh(commande)

    # -----------------------------------------------------
    # 10. Réponse
    # -----------------------------------------------------

    return {

        "message":
            "Commande annulée avec succès. "
            "Le stock a été restauré.",

        "id_commande":
            commande.id_commande,

        "statut":
            commande.statut
    }


# =========================================================
# MODIFIER LE STATUT D'UNE COMMANDE
# =========================================================

@app.put("/commandes/{id_commande}/statut")
def modifier_statut_commande(
    id_commande: int,
    nouveau_statut: str,
    utilisateur=Depends(role_autorise("admin", "vendeur")),
    db: Session = Depends(get_db),
):
    statuts_autorises = {
        "en_attente", "confirmee", "en_preparation", "prete", "livree", "annulee"
    }
    if nouveau_statut not in statuts_autorises:
        raise HTTPException(status_code=400, detail="Statut invalide.")

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    if commande.statut == "annulee":
        raise HTTPException(status_code=400, detail="Cette commande est déjà annulée.")

    ancien_statut = commande.statut
    try:
        if nouveau_statut == "annulee":
            lignes = db.query(CommandeHasProduit).filter(
                CommandeHasProduit.COMMANDE_id_commande == id_commande
            ).all()
            for ligne in lignes:
                produit = db.query(Produit).filter(
                    Produit.id_produit == ligne.PRODUIT_id_produit
                ).with_for_update().first()
                if produit is not None:
                    produit.stock = int(produit.stock or 0) + int(ligne.quantite or 0)

        commande.statut = nouveau_statut
        client = db.query(Client).filter(
            Client.id_client == commande.CLIENT_id_client
        ).first()
        if client and client.id_utilisateur:
            messages_statut = {
                "en_attente": ("Commande en attente", "Votre commande est en attente de traitement.", "info"),
                "confirmee": ("Commande confirmée", "Votre commande a été confirmée.", "success"),
                "en_preparation": ("Commande en préparation", "Votre commande est en préparation.", "info"),
                "prete": ("Commande prête", "Votre commande est prête.", "success"),
                "livree": ("Commande livrée", "Votre commande a été livrée. Merci pour votre confiance !", "success"),
                "annulee": ("Commande annulée", "Votre commande a été annulée.", "danger"),
            }
            titre, message, type_notification = messages_statut[nouveau_statut]
            creer_notification(
                db=db,
                id_utilisateur=client.id_utilisateur,
                titre=titre,
                message=f"Commande #{id_commande} : {message}",
                type_notification=type_notification,
                lien="/mes-commandes",
            )
        db.commit()
        db.refresh(commande)
    except Exception as erreur:
        db.rollback()
        print("Erreur changement statut commande :", str(erreur))
        raise HTTPException(status_code=500, detail="Erreur lors de la modification du statut.")

    return {
        "message": "Statut de la commande modifié avec succès.",
        "id_commande": commande.id_commande,
        "ancien_statut": ancien_statut,
        "statut": commande.statut,
    }




# =========================================================
# OUTILS CLOUDINARY
# =========================================================

def televerser_vers_cloudinary(fichier, dossier, type_ressource):
    """Envoie un fichier vers Cloudinary et journalise l'erreur réelle."""

    limites = {
        "image": 10 * 1024 * 1024,
        "video": 100 * 1024 * 1024,
        "raw": 20 * 1024 * 1024,
    }

    limite = limites.get(type_ressource, 20 * 1024 * 1024)

    try:
        # Revenir au début du fichier avant de le lire.
        fichier.file.seek(0)
        contenu = fichier.file.read(limite + 1)

        if not contenu:
            raise HTTPException(
                status_code=400,
                detail="Le fichier envoyé est vide."
            )

        if len(contenu) > limite:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Fichier trop volumineux. "
                    f"Limite : {limite // (1024 * 1024)} Mo."
                ),
            )

        resultat = cloudinary.uploader.upload(
            contenu,
            resource_type=type_ressource,
            folder=dossier,
            public_id=uuid.uuid4().hex,
            overwrite=False,
        )

        return resultat

    except HTTPException:
        raise

    except Exception as erreur:
        import logging

        logging.exception(
            "Échec Cloudinary : type=%s, dossier=%s, erreur=%s",
            type_ressource,
            dossier,
            str(erreur),
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Échec du téléversement vers Cloudinary. "
                "Consultez les logs de l'API pour le diagnostic."
            ),
        ) from erreur




def supprimer_media_cloudinary(url, type_ressource):
    """Supprime un média Cloudinary si son URL est reconnue."""

    if not url:
        return

    try:
        adresse = urlparse(url)

        if adresse.netloc.lower() != "res.cloudinary.com":
            return

        chemin = adresse.path

        if "/upload/" not in chemin:
            return

        chemin_media = chemin.split("/upload/", 1)[1]
        morceaux = chemin_media.split("/")

        # Retirer le numéro de version Cloudinary, s'il existe.
        if morceaux and morceaux[0].startswith("v"):
            version = morceaux[0][1:]
            if version.isdigit():
                morceaux.pop(0)

        public_id = "/".join(morceaux)

        # Retirer l'extension du dernier élément.
        if "." in public_id:
            public_id = public_id.rsplit(".", 1)[0]

        if public_id:
            cloudinary.uploader.destroy(
                public_id,
                resource_type=type_ressource,
                invalidate=True
            )

    except Exception:
        # Une erreur de suppression du média ne doit pas
        # empêcher la suppression du message en base.
        pass


# =========================================================
# TROUVER LE DESTINATAIRE D'UN MESSAGE
# =========================================================

def trouver_destinataire_message(db, commande, utilisateur_connecte):

    client = db.query(Client).filter(
        Client.id_client == commande.CLIENT_id_client
    ).first()

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client de la commande introuvable."
        )

    utilisateur_client = db.query(Utilisateur).filter(
        Utilisateur.id_utilisateur == client.id_utilisateur
    ).first()

    if not utilisateur_client:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur du client introuvable."
        )

    if utilisateur_connecte.role == "client":
        destinataire = db.query(Utilisateur).filter(
            Utilisateur.role == "vendeur"
        ).order_by(
            Utilisateur.id_utilisateur.asc()
        ).first()

        if destinataire is None:
            destinataire = db.query(Utilisateur).filter(
                Utilisateur.role == "admin"
            ).order_by(
                Utilisateur.id_utilisateur.asc()
            ).first()

        if destinataire is None:
            raise HTTPException(
                status_code=404,
                detail="Aucun vendeur ou administrateur disponible."
            )

        return destinataire

    if utilisateur_connecte.role in ("vendeur", "admin"):
        return utilisateur_client

    raise HTTPException(
        status_code=403,
        detail="Rôle non autorisé pour la messagerie."
    )


# =========================================================
# CRÉER UNE NOTIFICATION
# =========================================================

def creer_notification(
    db,
    id_utilisateur,
    titre,
    message,
    type_notification="info",
    lien=None
):
    notification = Notification(
        UTILISATEUR_id_utilisateur=id_utilisateur,
        titre=titre,
        message=message,
        type_notification=type_notification,
        lien=lien,
        lu=False,
        date_notification=datetime.now()
    )

    db.add(notification)
    return notification


# =========================================================
# NOTIFIER LES PERSONNES CONCERNÉES PAR UN MESSAGE
# =========================================================

def notifier_nouveau_message(
    db,
    commande,
    expediteur,
    id_commande
):
    if expediteur.role == "client":
        # Chaque administrateur et vendeur reçoit une notification.
        destinataires = db.query(Utilisateur).filter(
            Utilisateur.role.in_(["admin", "vendeur"])
        ).all()

        for destinataire in destinataires:
            creer_notification(
                db=db,
                id_utilisateur=destinataire.id_utilisateur,
                titre="Nouveau message",
                message=(
                    f"Un client a envoyé un message "
                    f"concernant la commande #{id_commande}."
                ),
                type_notification="message",
                lien="/commandes"
            )

    else:
        client = db.query(Client).filter(
            Client.id_client == commande.CLIENT_id_client
        ).first()

        if client and client.id_utilisateur:
            creer_notification(
                db=db,
                id_utilisateur=client.id_utilisateur,
                titre="Nouveau message",
                message=(
                    f"Vous avez reçu un nouveau message "
                    f"concernant votre commande #{id_commande}."
                ),
                type_notification="message",
                lien="/mes-commandes"
            )


# =========================================================
# ENVOYER UN MESSAGE TEXTE
# =========================================================

@app.post(
    "/commandes/{id_commande}/messages",
    response_model=MessageCommandeResponse
)
def envoyer_message_commande(
    id_commande: int,
    message_data: MessageCommandeCreate,
    utilisateur=Depends(role_autorise("admin", "vendeur", "client")),
    db: Session = Depends(get_db)
):
    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    if utilisateur.role == "client":
        client = db.query(Client).filter(
            Client.id_utilisateur == utilisateur.id_utilisateur
        ).first()

        if client is None:
            raise HTTPException(
                status_code=404,
                detail="Aucun client associé à cet utilisateur."
            )

        if commande.CLIENT_id_client != client.id_client:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez pas envoyer un message pour cette commande."
            )

    texte = (message_data.message or "").strip()

    if not texte:
        raise HTTPException(
            status_code=400,
            detail="Le message ne peut pas être vide."
        )

    destinataire = trouver_destinataire_message(
        db, commande, utilisateur
    )

    if destinataire.id_utilisateur == utilisateur.id_utilisateur:
        raise HTTPException(
            status_code=400,
            detail="Le destinataire ne peut pas être l'expéditeur."
        )

    nouveau_message = MessageCommande(
        COMMANDE_id_commande=id_commande,
        UTILISATEUR_id_utilisateur=utilisateur.id_utilisateur,
        UTILISATEUR_destinataire_id=destinataire.id_utilisateur,
        message=texte,
        lu=False
    )

    try:
        db.add(nouveau_message)
        db.flush()

        notifier_nouveau_message(
            db, commande, utilisateur, id_commande
        )

        db.commit()
        db.refresh(nouveau_message)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer le message."
        )

    return nouveau_message


# =========================================================
# ENVOYER UN MESSAGE DEPUIS L'ESPACE CLIENT
# =========================================================

@app.post("/mes-commandes/{id_commande}/messages")
def envoyer_message_client(
    id_commande: int,
    message_data: dict,
    utilisateur=Depends(role_autorise("client")),
    db: Session = Depends(get_db)
):
    contenu = str(message_data.get("message") or "").strip()

    if not contenu:
        raise HTTPException(
            status_code=400,
            detail="Le message ne peut pas être vide."
        )

    client = db.query(Client).filter(
        Client.id_utilisateur == utilisateur.id_utilisateur
    ).first()

    if client is None:
        raise HTTPException(
            status_code=404,
            detail="Aucun client associé à cet utilisateur."
        )

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    if commande.CLIENT_id_client != client.id_client:
        raise HTTPException(
            status_code=403,
            detail="Vous n'êtes pas autorisé à contacter cette commande."
        )

    destinataire = trouver_destinataire_message(
        db, commande, utilisateur
    )

    nouveau_message = MessageCommande(
        COMMANDE_id_commande=id_commande,
        UTILISATEUR_id_utilisateur=utilisateur.id_utilisateur,
        UTILISATEUR_destinataire_id=destinataire.id_utilisateur,
        message=contenu,
        lu=False
    )

    try:
        db.add(nouveau_message)
        db.flush()

        notifier_nouveau_message(
            db, commande, utilisateur, id_commande
        )

        db.commit()
        db.refresh(nouveau_message)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer le message."
        )

    return {
        "message": "Votre message a été envoyé.",
        "id_message": nouveau_message.id_message
    }



# =========================================================
# ENVOYER UN MESSAGE VOCAL VERS CLOUDINARY
# =========================================================

@app.post(
    "/commandes/{id_commande}/messages/vocal",
    response_model=MessageCommandeResponse
)
async def envoyer_message_vocal(
    id_commande: int,
    fichier: UploadFile = File(...),
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # 1. VÉRIFIER LA COMMANDE
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    # -----------------------------------------------------
    # 2. VÉRIFIER LES DROITS D'ACCÈS
    # -----------------------------------------------------

    if utilisateur.role == "client":
        client = db.query(Client).filter(
            Client.id_utilisateur == utilisateur.id_utilisateur
        ).first()

        if client is None:
            raise HTTPException(
                status_code=404,
                detail="Aucun client associé à cet utilisateur."
            )

        if commande.CLIENT_id_client != client.id_client:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous ne pouvez pas envoyer un vocal "
                    "pour cette commande."
                )
            )

    # -----------------------------------------------------
    # 3. VÉRIFIER LE FICHIER AUDIO
    # -----------------------------------------------------

    if not fichier.filename:
        raise HTTPException(
            status_code=400,
            detail="Aucun fichier vocal reçu."
        )

    type_fichier = (fichier.content_type or "").lower()

    types_audio_autorises = {
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/webm",
        "audio/aac",
        "audio/3gpp",
        "application/octet-stream",
    }

    if type_fichier not in types_audio_autorises:
        raise HTTPException(
            status_code=400,
            detail="Le format du fichier vocal n'est pas accepté."
        )

    # Limite de sécurité : 20 Mo.
    taille_maximale = 20 * 1024 * 1024
    contenu = await fichier.read(taille_maximale + 1)

    if not contenu:
        raise HTTPException(
            status_code=400,
            detail="Le fichier vocal est vide."
        )

    if len(contenu) > taille_maximale:
        raise HTTPException(
            status_code=413,
            detail="Le fichier vocal dépasse la limite de 20 Mo."
        )

    # Replacer le curseur au début avant l'envoi Cloudinary.
    await fichier.seek(0)

    # -----------------------------------------------------
    # 4. TROUVER LE DESTINATAIRE
    # -----------------------------------------------------

    destinataire = trouver_destinataire_message(
        db,
        commande,
        utilisateur
    )

    if destinataire is None:
        raise HTTPException(
            status_code=404,
            detail="Aucun destinataire disponible pour ce message."
        )

    if (
        destinataire.id_utilisateur
        == utilisateur.id_utilisateur
    ):
        raise HTTPException(
            status_code=400,
            detail="Le destinataire ne peut pas être l'expéditeur."
        )

    # -----------------------------------------------------
    # 5. TÉLÉVERSER LE FICHIER SUR CLOUDINARY
    # -----------------------------------------------------

    try:
        resultat = televerser_vers_cloudinary(
            fichier,
            "boutique/audio",
            "video"
        )

    except Exception as erreur:
        print("Erreur Cloudinary lors de l'envoi audio :", str(erreur))

        raise HTTPException(
            status_code=502,
            detail="Impossible de téléverser le fichier vocal."
        )

    audio_url = resultat.get("secure_url")

    if not audio_url:
        raise HTTPException(
            status_code=502,
            detail="Cloudinary n'a pas retourné l'URL du fichier audio."
        )

    # -----------------------------------------------------
    # 6. ENREGISTRER LE MESSAGE
    # -----------------------------------------------------

    nouveau_message = MessageCommande(
        COMMANDE_id_commande=id_commande,
        UTILISATEUR_id_utilisateur=utilisateur.id_utilisateur,
        UTILISATEUR_destinataire_id=destinataire.id_utilisateur,
        message=None,
        audio_url=audio_url,
        lu=False
    )

    try:
        db.add(nouveau_message)
        db.flush()

        notifier_nouveau_message(
            db,
            commande,
            utilisateur,
            id_commande
        )

        db.commit()
        db.refresh(nouveau_message)

    except Exception as erreur:
        db.rollback()

        print("Erreur d'enregistrement du message vocal :", str(erreur))

        # Essayer de supprimer le média distant si la transaction
        # échoue, sans masquer l'erreur initiale.
        try:
            supprimer_media_cloudinary(audio_url, "video")
        except Exception as erreur_suppression:
            print(
                "Nettoyage Cloudinary impossible :",
                str(erreur_suppression)
            )

        raise HTTPException(
            status_code=500,
            detail=(
                "Le fichier vocal a été téléversé, mais "
                "le message n'a pas pu être enregistré."
            )
        )

    return nouveau_message


# =========================================================
# AFFICHER LES MESSAGES D'UNE COMMANDE
# =========================================================

@app.get(
    "/commandes/{id_commande}/messages",
    response_model=list[MessageCommandeResponse]
)
def lire_messages_commande(
    id_commande: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # 1. VÉRIFIER LA COMMANDE
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    # -----------------------------------------------------
    # 2. VÉRIFIER LES DROITS ET MARQUER LES MESSAGES LUS
    # -----------------------------------------------------

    if utilisateur.role == "client":
        client = db.query(Client).filter(
            Client.id_utilisateur == utilisateur.id_utilisateur
        ).first()

        if client is None:
            raise HTTPException(
                status_code=404,
                detail="Aucun client associé à cet utilisateur."
            )

        if commande.CLIENT_id_client != client.id_client:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous ne pouvez pas consulter les messages "
                    "de cette commande."
                )
            )

        # Le client ne marque comme lus que les messages
        # qui lui sont effectivement destinés.
        db.query(MessageCommande).filter(
            MessageCommande.COMMANDE_id_commande == id_commande,
            MessageCommande.UTILISATEUR_destinataire_id
            == utilisateur.id_utilisateur,
            MessageCommande.lu.is_(False)
        ).update(
            {MessageCommande.lu: True},
            synchronize_session=False
        )

    else:
        # Le personnel ne marque comme lus que les messages
        # envoyés par le client propriétaire de la commande.
        client = db.query(Client).filter(
            Client.id_client == commande.CLIENT_id_client
        ).first()

        if client:
            db.query(MessageCommande).filter(
                MessageCommande.COMMANDE_id_commande == id_commande,
                MessageCommande.UTILISATEUR_id_utilisateur
                == client.id_utilisateur,
                MessageCommande.UTILISATEUR_destinataire_id
                == utilisateur.id_utilisateur,
                MessageCommande.lu.is_(False)
            ).update(
                {MessageCommande.lu: True},
                synchronize_session=False
            )

    try:
        db.commit()
    except Exception as erreur:
        db.rollback()

        print("Erreur de mise à jour du statut lu :", str(erreur))

        raise HTTPException(
            status_code=500,
            detail="Impossible de mettre à jour le statut des messages."
        )

    # -----------------------------------------------------
    # 3. RÉCUPÉRER LES MESSAGES
    # -----------------------------------------------------

    messages = db.query(MessageCommande).filter(
        MessageCommande.COMMANDE_id_commande == id_commande
    ).order_by(
        MessageCommande.date_message.asc()
    ).all()

    # -----------------------------------------------------
    # 4. PRÉPARER LA RÉPONSE
    # -----------------------------------------------------

    resultats = []

    for message in messages:
        expediteur = db.query(Utilisateur).filter(
            Utilisateur.id_utilisateur
            == message.UTILISATEUR_id_utilisateur
        ).first()

        resultats.append({
            "id_message": message.id_message,
            "COMMANDE_id_commande": message.COMMANDE_id_commande,
            "UTILISATEUR_id_utilisateur":
                message.UTILISATEUR_id_utilisateur,
            "message": message.message,
            "audio_url": message.audio_url,
            "date_message": message.date_message,
            "lu": message.lu,
            "nom_utilisateur": (
                expediteur.nom if expediteur else None
            ),
            "prenom_utilisateur": (
                expediteur.prenom if expediteur else None
            ),
            "role_utilisateur": (
                expediteur.role if expediteur else None
            )
        })

    return resultats




# =========================================================
# COMPTER LES MESSAGES NON LUS POUR UNE COMMANDE
# =========================================================

@app.get("/commandes/{id_commande}/messages/non-lus")
def compter_messages_non_lus_commande(
    id_commande: int,
    utilisateur=Depends(role_autorise("admin", "vendeur", "client")),
    db: Session = Depends(get_db)
):
    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    if utilisateur.role == "client":
        client = db.query(Client).filter(
            Client.id_utilisateur == utilisateur.id_utilisateur
        ).first()

        if client is None or commande.CLIENT_id_client != client.id_client:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez pas consulter cette commande."
            )

        filtre = (
            MessageCommande.UTILISATEUR_destinataire_id
            == utilisateur.id_utilisateur
        )

    else:
        client = db.query(Client).filter(
            Client.id_client == commande.CLIENT_id_client
        ).first()

        if client is None:
            return {"id_commande": id_commande, "messages_non_lus": 0}

        filtre = (
            MessageCommande.UTILISATEUR_id_utilisateur == client.id_utilisateur,
            MessageCommande.UTILISATEUR_destinataire_id == utilisateur.id_utilisateur,
        )

    nombre = db.query(MessageCommande).filter(
        MessageCommande.COMMANDE_id_commande == id_commande,
        *([filtre] if not isinstance(filtre, tuple) else list(filtre)),
        MessageCommande.lu.is_(False)
    ).count()

    return {
        "id_commande": id_commande,
        "messages_non_lus": nombre
    }


# =========================================================
# SUPPRIMER SON PROPRE MESSAGE
# =========================================================

@app.delete("/commandes/{id_commande}/messages/{id_message}")
def supprimer_message(
    id_commande: int,
    id_message: int,
    utilisateur=Depends(role_autorise("admin", "vendeur", "client")),
    db: Session = Depends(get_db)
):
    message = db.query(MessageCommande).filter(
        MessageCommande.id_message == id_message,
        MessageCommande.COMMANDE_id_commande == id_commande
    ).first()

    if message is None:
        raise HTTPException(
            status_code=404,
            detail="Message introuvable."
        )

    if message.UTILISATEUR_id_utilisateur != utilisateur.id_utilisateur:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez supprimer que vos propres messages."
        )

    # Supprimer le média distant si l'URL appartient à Cloudinary.
    if message.audio_url:
        supprimer_media_cloudinary(message.audio_url, "video")

    db.delete(message)
    db.commit()

    return {"message": "Message supprimé."}


# =========================================================
# MARQUER UN MESSAGE COMME LU / NON LU
# =========================================================

@app.put(
    "/commandes/{id_commande}/messages/{id_message}/lu",
    response_model=MessageCommandeResponse
)
def marquer_message_lu(
    id_commande: int,
    id_message: int,
    message_data: MessageCommandeLuUpdate,
    utilisateur=Depends(role_autorise("admin", "vendeur", "client")),
    db: Session = Depends(get_db)
):
    message = db.query(MessageCommande).filter(
        MessageCommande.id_message == id_message,
        MessageCommande.COMMANDE_id_commande == id_commande
    ).first()

    if message is None:
        raise HTTPException(
            status_code=404,
            detail="Message introuvable."
        )

    if message.UTILISATEUR_destinataire_id != utilisateur.id_utilisateur:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez modifier que les messages qui vous sont destinés."
        )

    message.lu = message_data.lu
    db.commit()
    db.refresh(message)

    return message


# =========================================================
# COMPTER TOUS LES MESSAGES NON LUS DE L'UTILISATEUR
# =========================================================

@app.get("/messages/non-lus")
def compter_tous_messages_non_lus(
    utilisateur=Depends(role_autorise("admin", "vendeur", "client")),
    db: Session = Depends(get_db)
):
    nombre = db.query(MessageCommande).filter(
        MessageCommande.UTILISATEUR_destinataire_id == utilisateur.id_utilisateur,
        MessageCommande.lu.is_(False)
    ).count()

    return {"nombre_non_lus": nombre}


# =========================================================
# RÉCUPÉRER LES CONVERSATIONS
# =========================================================

@app.get("/messages/conversations")
def obtenir_conversations(
    utilisateur=Depends(role_autorise("admin", "vendeur", "client")),
    db: Session = Depends(get_db)
):
    if utilisateur.role == "client":
        client = db.query(Client).filter(
            Client.id_utilisateur == utilisateur.id_utilisateur
        ).first()

        if client is None:
            raise HTTPException(
                status_code=404,
                detail="Aucun client associé à cet utilisateur."
            )

        commandes = db.query(Commande).filter(
            Commande.CLIENT_id_client == client.id_client
        ).all()
    else:
        commandes = db.query(Commande).all()

    conversations = []

    for commande in commandes:
        messages = db.query(MessageCommande).filter(
            MessageCommande.COMMANDE_id_commande == commande.id_commande
        ).order_by(
            MessageCommande.date_message.desc()
        ).all()

        if not messages:
            continue

        dernier = messages[0]

        nombre_non_lus = db.query(MessageCommande).filter(
            MessageCommande.COMMANDE_id_commande == commande.id_commande,
            MessageCommande.UTILISATEUR_destinataire_id == utilisateur.id_utilisateur,
            MessageCommande.lu.is_(False)
        ).count()

        expediteur = db.query(Utilisateur).filter(
            Utilisateur.id_utilisateur == dernier.UTILISATEUR_id_utilisateur
        ).first()

        apercu = (
            "🎤 Message vocal" if dernier.audio_url
            else dernier.message or "Message"
        )

        conversations.append({
            "id_commande": commande.id_commande,
            "statut_commande": commande.statut,
            "nombre_messages": len(messages),
            "nombre_non_lus": nombre_non_lus,
            "dernier_message": apercu,
            "date_dernier_message": dernier.date_message,
            "id_expediteur": dernier.UTILISATEUR_id_utilisateur,
            "nom_expediteur": expediteur.nom if expediteur else None,
            "prenom_expediteur": expediteur.prenom if expediteur else None,
            "role_expediteur": expediteur.role if expediteur else None
        })

    conversations.sort(
        key=lambda c: c["date_dernier_message"],
        reverse=True
    )

    return {
        "nombre_conversations": len(conversations),
        "nombre_non_lus": sum(c["nombre_non_lus"] for c in conversations),
        "conversations": conversations
    }



# =========================================================
# PHOTOS DE LA PAGE D'ACCUEIL
# =========================================================

@app.get("/accueil/photos")
def liste_photos_accueil(
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):
    return db.query(PhotoAccueil).order_by(
        PhotoAccueil.ordre.asc(),
        PhotoAccueil.id_photo.desc()
    ).all()


@app.post("/accueil/photos")
def ajouter_photo_accueil(
    fichier: UploadFile = File(...),
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):
    type_fichier = (fichier.content_type or "").lower()

    if not type_fichier.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Veuillez sélectionner un fichier image."
        )

    resultat = televerser_vers_cloudinary(
        fichier,
        "boutique/photos-accueil",
        "image"
    )

    url_media = resultat.get("secure_url")

    if not url_media:
        raise HTTPException(
            status_code=502,
            detail="Cloudinary n'a pas retourné l'URL de la photo."
        )

    nouvelle_photo = PhotoAccueil(
        nom_fichier=url_media,
        ordre=0,
        actif=True
    )

    try:
        db.add(nouvelle_photo)
        db.commit()
        db.refresh(nouvelle_photo)

    except Exception as erreur:
        db.rollback()

        try:
            supprimer_media_cloudinary(url_media, "image")
        except Exception as erreur_cloudinary:
            print(
                "Erreur de nettoyage Cloudinary :",
                str(erreur_cloudinary)
            )

        print("Erreur ajout photo :", str(erreur))

        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer la photo d'accueil."
        )

    return {
        "message": "Photo d'accueil ajoutée avec succès.",
        "photo": nouvelle_photo
    }


@app.delete("/accueil/photos/{id_photo}")
def supprimer_photo_accueil(
    id_photo: int,
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):
    photo = db.query(PhotoAccueil).filter(
        PhotoAccueil.id_photo == id_photo
    ).first()

    if photo is None:
        raise HTTPException(
            status_code=404,
            detail="Photo introuvable."
        )

    # Supprimer d'abord le média distant.
    # Si cela échoue, conserver la ligne en base.
    try:
        supprimer_media_cloudinary(photo.nom_fichier, "image")
    except Exception as erreur:
        print("Erreur suppression photo Cloudinary :", str(erreur))

        raise HTTPException(
            status_code=502,
            detail=(
                "Impossible de supprimer la photo sur Cloudinary. "
                "L'enregistrement en base a été conservé."
            )
        )

    try:
        db.delete(photo)
        db.commit()
    except Exception as erreur:
        db.rollback()
        print("Erreur suppression photo en base :", str(erreur))

        raise HTTPException(
            status_code=500,
            detail=(
                "Le média a été supprimé, mais l'enregistrement "
                "en base n'a pas pu être supprimé."
            )
        )

    return {"message": "Photo supprimée avec succès."}


# =========================================================
# PUBLICITÉS VIDÉO
# =========================================================

@app.get("/accueil/publicites")
def liste_publicites(
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):
    return db.query(Publicite).order_by(
        Publicite.ordre.asc(),
        Publicite.id_publicite.desc()
    ).all()


@app.post("/accueil/publicites")
def ajouter_publicite(
    fichier: UploadFile = File(...),
    titre: str | None = None,
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):
    # Vérifier la limite avant le téléversement.
    nombre_publicites = db.query(Publicite).filter(
        Publicite.actif.is_(True)
    ).count()

    if nombre_publicites >= 3:
        raise HTTPException(
            status_code=400,
            detail=(
                "Vous ne pouvez avoir que 3 publicités "
                "vidéo actives maximum."
            )
        )

    type_fichier = (fichier.content_type or "").lower()

    if not type_fichier.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Veuillez sélectionner un fichier vidéo."
        )

    resultat = televerser_vers_cloudinary(
        fichier,
        "boutique/publicites",
        "video"
    )

    url_media = resultat.get("secure_url")

    if not url_media:
        raise HTTPException(
            status_code=502,
            detail="Cloudinary n'a pas retourné l'URL de la vidéo."
        )

    nouvelle_publicite = Publicite(
        nom_fichier=url_media,
        titre=titre.strip() if titre else None,
        ordre=nombre_publicites,
        actif=True
    )

    try:
        db.add(nouvelle_publicite)
        db.commit()
        db.refresh(nouvelle_publicite)

    except Exception as erreur:
        db.rollback()

        try:
            supprimer_media_cloudinary(url_media, "video")
        except Exception as erreur_cloudinary:
            print(
                "Erreur de nettoyage Cloudinary :",
                str(erreur_cloudinary)
            )

        print("Erreur ajout publicité :", str(erreur))

        raise HTTPException(
            status_code=500,
            detail="Impossible d'enregistrer la publicité."
        )

    return {
        "message": "Publicité ajoutée avec succès.",
        "publicite": nouvelle_publicite
    }


@app.delete("/accueil/publicites/{id_publicite}")
def supprimer_publicite(
    id_publicite: int,
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):
    publicite = db.query(Publicite).filter(
        Publicite.id_publicite == id_publicite
    ).first()

    if publicite is None:
        raise HTTPException(
            status_code=404,
            detail="Publicité introuvable."
        )

    try:
        supprimer_media_cloudinary(publicite.nom_fichier, "video")
    except Exception as erreur:
        print(
            "Erreur suppression vidéo Cloudinary :",
            str(erreur)
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Impossible de supprimer la vidéo sur Cloudinary. "
                "L'enregistrement en base a été conservé."
            )
        )

    try:
        db.delete(publicite)
        db.commit()
    except Exception as erreur:
        db.rollback()
        print("Erreur suppression publicité en base :", str(erreur))

        raise HTTPException(
            status_code=500,
            detail=(
                "La vidéo a été supprimée, mais l'enregistrement "
                "en base n'a pas pu être supprimé."
            )
        )

    return {"message": "Publicité supprimée avec succès."}


# =========================================================
# CONTENU PUBLIC DE LA PAGE D'ACCUEIL
# =========================================================

@app.get("/accueil/contenu")
def contenu_accueil(db: Session = Depends(get_db)):
    photos = db.query(PhotoAccueil).filter(
        PhotoAccueil.actif.is_(True)
    ).order_by(
        PhotoAccueil.ordre.asc(),
        PhotoAccueil.id_photo.desc()
    ).all()

    publicites = db.query(Publicite).filter(
        Publicite.actif.is_(True)
    ).order_by(
        Publicite.ordre.asc(),
        Publicite.id_publicite.desc()
    ).limit(3).all()

    produits = db.query(Produit).filter(
        Produit.actif.is_(True)
    ).order_by(
        Produit.id_produit.desc()
    ).limit(10).all()

    return {
        "photos": [
            {
                "id_photo": p.id_photo,
                "nom_fichier": p.nom_fichier
            }
            for p in photos
        ],
        "publicites": [
            {
                "id_publicite": p.id_publicite,
                "nom_fichier": p.nom_fichier,
                "titre": p.titre
            }
            for p in publicites
        ],
        "produits": [
            {
                "id_produit": p.id_produit,
                "designation": p.designation,
                "prix_unitaire": p.prix_unitaire,
                "description": p.description,
                "image": p.image,
                "stock": p.stock,
                "categorie": p.categorie
            }
            for p in produits
        ]
    }



# =========================================================
# DASHBOARD ADMIN / VENDEUR
# STATISTIQUES GENERALES DE LA BOUTIQUE
# =========================================================

@app.get("/dashboard/statistiques")
def statistiques_dashboard(
    granularite: str = Query(
        default="mois",
        pattern="^(jour|mois)$"
    ),
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):
    """
    Retourne les principales statistiques
    nécessaires au tableau de bord.

    Accessible uniquement à :
        - administrateur
        - vendeur
    """

    # =====================================================
    # 1. NOMBRE DE CLIENTS
    # =====================================================

    nombre_clients = db.query(Client).count()

    # =====================================================
    # 2. NOMBRE DE COMMANDES
    # =====================================================

    nombre_commandes = db.query(Commande).count()

    # =====================================================
    # 3. NOMBRE DE PRODUITS
    # =====================================================

    nombre_produits = db.query(Produit).count()

    # =====================================================
    # 4. NOMBRE DE SERVICES
    # =====================================================

    nombre_services = db.query(Service).count()

    # =====================================================
    # 5. CHIFFRE D'AFFAIRES
    #
    # On additionne :
    #    produits = quantité × prix_unitaire
    #    services = quantité × prix_unitaire
    #
    # Les commandes annulées ne sont pas comptabilisées.
    # =====================================================

    commandes_annulees = (
        db.query(Commande.id_commande)
        .filter(
            func.lower(Commande.statut) == "annulee"
        )
        .subquery()
    )

    chiffre_affaires_produits = (
        db.query(
            func.coalesce(
                func.sum(
                    CommandeHasProduit.quantite
                    * CommandeHasProduit.prix_unitaire
                ),
                0
            )
        )
        .filter(
            ~CommandeHasProduit.COMMANDE_id_commande.in_(
                commandes_annulees
            )
        )
        .scalar()
    )

    chiffre_affaires_services = (
        db.query(
            func.coalesce(
                func.sum(
                    CommandeHasService.quantite
                    * CommandeHasService.prix_unitaire
                ),
                0
            )
        )
        .filter(
            ~CommandeHasService.COMMANDE_id_commande.in_(
                commandes_annulees
            )
        )
        .scalar()
    )

    chiffre_affaires = (
        float(chiffre_affaires_produits or 0)
        + float(chiffre_affaires_services or 0)
    )

    # =====================================================
    # 6. COMMANDES PAR STATUT
    # =====================================================

    commandes_statuts = (
        db.query(
            Commande.statut,
            func.count(Commande.id_commande)
        )
        .group_by(Commande.statut)
        .all()
    )

    repartition_statuts = []

    for statut, nombre in commandes_statuts:

        repartition_statuts.append({
            "statut": statut or "Non défini",
            "nombre": nombre
        })

    # =====================================================
    # 7. EVOLUTION DES COMMANDES ET DU CHIFFRE D'AFFAIRES
    # =====================================================

    aujourd_hui = date.today()

    if granularite == "jour":
        date_debut = aujourd_hui - timedelta(days=29)
        date_fin = aujourd_hui
        periodes = []
        jour_courant = date_debut

        while jour_courant <= date_fin:
            cle_periode = jour_courant.isoformat()
            periodes.append({
                "cle": cle_periode,
                "libelle": jour_courant.strftime("%d/%m")
            })
            jour_courant += timedelta(days=1)

        def obtenir_cle_periode(date_commande):
            return date_commande.isoformat()

        libelle_periode = "30 derniers jours"

    else:
        premier_mois = aujourd_hui.replace(day=1)
        mois_debut = premier_mois

        for _ in range(11):
            if mois_debut.month == 1:
                mois_debut = mois_debut.replace(
                    year=mois_debut.year - 1,
                    month=12
                )
            else:
                mois_debut = mois_debut.replace(
                    month=mois_debut.month - 1
                )

        date_debut = mois_debut
        date_fin = aujourd_hui
        periodes = []
        mois_courant = mois_debut
        noms_mois = (
            "janv.", "févr.", "mars", "avr.", "mai", "juin",
            "juil.", "août", "sept.", "oct.", "nov.", "déc."
        )

        while mois_courant <= aujourd_hui.replace(day=1):
            periodes.append({
                "cle": mois_courant.strftime("%Y-%m"),
                "libelle": (
                    f"{noms_mois[mois_courant.month - 1]} "
                    f"{mois_courant.year}"
                )
            })
            if mois_courant.month == 12:
                mois_courant = mois_courant.replace(
                    year=mois_courant.year + 1,
                    month=1
                )
            else:
                mois_courant = mois_courant.replace(
                    month=mois_courant.month + 1
                )

        def obtenir_cle_periode(date_commande):
            return date_commande.strftime("%Y-%m")

        libelle_periode = "12 derniers mois"

    commandes_par_date = (
        db.query(
            Commande.date_commande,
            func.count(Commande.id_commande)
        )
        .filter(
            Commande.date_commande >= date_debut,
            Commande.date_commande <= date_fin
        )
        .group_by(Commande.date_commande)
        .all()
    )

    chiffre_affaires_par_date = {}

    for lignes_commande, expression_total in (
        (CommandeHasProduit, CommandeHasProduit.quantite
         * CommandeHasProduit.prix_unitaire),
        (CommandeHasService, CommandeHasService.quantite
         * CommandeHasService.prix_unitaire)
    ):
        totaux = (
            db.query(
                Commande.date_commande,
                func.sum(expression_total)
            )
            .join(
                lignes_commande,
                lignes_commande.COMMANDE_id_commande
                == Commande.id_commande
            )
            .filter(
                Commande.date_commande >= date_debut,
                Commande.date_commande <= date_fin,
                func.lower(Commande.statut) != "annulee"
            )
            .group_by(Commande.date_commande)
            .all()
        )

        for date_commande, total in totaux:
            cle_periode = obtenir_cle_periode(date_commande)
            chiffre_affaires_par_date[cle_periode] = (
                chiffre_affaires_par_date.get(cle_periode, 0)
                + float(total or 0)
            )

    commandes_par_periode = {}

    for date_commande, nombre in commandes_par_date:
        cle_periode = obtenir_cle_periode(date_commande)
        commandes_par_periode[cle_periode] = (
            commandes_par_periode.get(cle_periode, 0) + nombre
        )

    evolution = [
        {
            "periode": periode["cle"],
            "libelle": periode["libelle"],
            "nombre_commandes": commandes_par_periode.get(
                periode["cle"],
                0
            ),
            "chiffre_affaires": chiffre_affaires_par_date.get(
                periode["cle"],
                0
            )
        }
        for periode in periodes
    ]

    produits_par_categorie = (
        db.query(
            func.coalesce(
                func.nullif(func.trim(Produit.categorie), ""),
                "Sans catégorie"
            ).label("categorie"),
            func.sum(CommandeHasProduit.quantite).label("quantite")
        )
        .join(
            CommandeHasProduit,
            CommandeHasProduit.PRODUIT_id_produit
            == Produit.id_produit
        )
        .join(
            Commande,
            Commande.id_commande
            == CommandeHasProduit.COMMANDE_id_commande
        )
        .filter(
            Commande.date_commande >= date_debut,
            Commande.date_commande <= date_fin,
            func.lower(Commande.statut) != "annulee"
        )
        .group_by("categorie")
        .order_by(func.sum(CommandeHasProduit.quantite).desc())
        .all()
    )

    liste_produits_par_categorie = [
        {
            "categorie": categorie,
            "quantite": int(quantite or 0)
        }
        for categorie, quantite in produits_par_categorie
    ]

    # =====================================================
    # 8. DERNIERES COMMANDES
    # =====================================================

    dernieres_commandes = (
        db.query(Commande)
        .order_by(
            Commande.date_commande.desc()
        )
        .limit(10)
        .all()
    )

    liste_commandes = []

    for commande in dernieres_commandes:

        # -------------------------------------------------
        # TOTAL PRODUITS
        # -------------------------------------------------

        total_produits = (
            db.query(
                func.coalesce(
                    func.sum(
                        CommandeHasProduit.quantite
                        * CommandeHasProduit.prix_unitaire
                    ),
                    0
                )
            )
            .filter(
                CommandeHasProduit.COMMANDE_id_commande
                == commande.id_commande
            )
            .scalar()
        )

        # -------------------------------------------------
        # TOTAL SERVICES
        # -------------------------------------------------

        total_services = (
            db.query(
                func.coalesce(
                    func.sum(
                        CommandeHasService.quantite
                        * CommandeHasService.prix_unitaire
                    ),
                    0
                )
            )
            .filter(
                CommandeHasService.COMMANDE_id_commande
                == commande.id_commande
            )
            .scalar()
        )

        total_commande = (
            float(total_produits or 0)
            + float(total_services or 0)
        )

        liste_commandes.append({
            "id_commande": commande.id_commande,
            "date_commande": (
                commande.date_commande.isoformat()
                if commande.date_commande
                else None
            ),
            "statut": (
                commande.statut
                or "Non défini"
            ),
            "total": total_commande
        })

    # =====================================================
    # 8. REPONSE
    # =====================================================

    return {
        "nombre_clients": nombre_clients,
        "nombre_commandes": nombre_commandes,
        "nombre_produits": nombre_produits,
        "nombre_services": nombre_services,
        "chiffre_affaires": chiffre_affaires,
        "repartition_statuts": repartition_statuts,
        "dernieres_commandes": liste_commandes,
        "granularite": granularite,
        "libelle_periode": libelle_periode,
        "evolution": evolution,
        "produits_par_categorie": liste_produits_par_categorie
    }


# =========================================================
# CRÉER UNE NOTIFICATION
# =========================================================

def creer_notification(

    db,
    id_utilisateur,
    titre,
    message,
    type_notification="info",
    lien=None
):

    notification = Notification(

        UTILISATEUR_id_utilisateur=
            id_utilisateur,

        titre=titre,

        message=message,

        type_notification=
            type_notification,

        lien=lien,

        lu=False,

        date_notification=datetime.now()
    )

    db.add(notification)


    return notification



# =========================================================
# NOTIFICATIONS
# =========================================================


# =========================================================
# RÉCUPÉRER LES NOTIFICATIONS DE L'UTILISATEUR CONNECTÉ
# =========================================================

@app.get("/notifications")
def liste_notifications(

    utilisateur=Depends(
        role_autorise(
            "admin",
            "vendeur",
            "client"
        )
    ),

    db: Session = Depends(get_db)
):

    notifications = (
        db.query(Notification)
        .filter(
            Notification.UTILISATEUR_id_utilisateur
            == utilisateur.id_utilisateur
        )
        .order_by(
            Notification.date_notification.desc()
        )
        .limit(30)
        .all()
    )

    nombre_non_lues = (
        db.query(Notification)
        .filter(
            Notification.UTILISATEUR_id_utilisateur
            == utilisateur.id_utilisateur,

            Notification.lu.is_(False)
        )
        .count()
    )

    return {

        "nombre_non_lues": nombre_non_lues,

        "notifications": [

            {
                "id_notification":
                    notification.id_notification,

                "titre":
                    notification.titre,

                "message":
                    notification.message,

                "type_notification":
                    notification.type_notification,

                "lien":
                    notification.lien,

                "lu":
                    notification.lu,

                "date_notification":
                    (
                        notification.date_notification.isoformat()
                        if notification.date_notification
                        else None
                    )
            }

            for notification in notifications
        ]
    }


# =========================================================
# MARQUER UNE NOTIFICATION COMME LUE
# =========================================================

@app.put(
    "/notifications/{id_notification}/lue"
)
def marquer_notification_lue(

    id_notification: int,

    utilisateur=Depends(
        role_autorise(
            "admin",
            "vendeur",
            "client"
        )
    ),

    db: Session = Depends(get_db)
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id_notification
            == id_notification,

            Notification.UTILISATEUR_id_utilisateur
            == utilisateur.id_utilisateur
        )
        .first()
    )

    if notification is None:

        raise HTTPException(
            status_code=404,
            detail="Notification introuvable."
        )

    notification.lu = True

    db.commit()

    return {
        "success": True,
        "message": "Notification marquée comme lue."
    }


# =========================================================
# MARQUER TOUTES LES NOTIFICATIONS COMME LUES
# =========================================================

@app.put(
    "/notifications/toutes/lues"
)
def marquer_toutes_notifications_lues(

    utilisateur=Depends(
        role_autorise(
            "admin",
            "vendeur",
            "client"
        )
    ),

    db: Session = Depends(get_db)
):

    (
        db.query(Notification)
        .filter(
            Notification.UTILISATEUR_id_utilisateur
            == utilisateur.id_utilisateur,

            Notification.lu.is_(False)
        )
        .update(
            {
                Notification.lu: True
            },

            synchronize_session=False
        )
    )

    db.commit()

    return {
        "success": True,
        "message": (
            "Toutes les notifications "
            "ont été marquées comme lues."
        )
    }