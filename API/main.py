from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from sqlalchemy import func
from pydantic import BaseModel


import os
import uuid

from sqlalchemy.orm import Session

import bcrypt

from datetime import date, datetime


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
# DOSSIER POUR LES FICHIERS STATIQUES
# =========================================================

os.makedirs("static/audio", exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# =========================================================
# CONFIGURATION CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5000"
    ],
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
            "telephone": client.telephone
        })

    return resultats


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
        telephone=client.telephone
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

    db.commit()

    db.refresh(client_existant)

    return client_existant


# =========================================================
# ROUTE : SUPPRIMER UN CLIENT
# =========================================================

@app.delete("/clients/{id_client}")
def supprimer_client(
    id_client: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    client = db.query(Client).filter(
        Client.id_client == id_client
    ).first()

    if client is None:

        return {
            "message": "Client introuvable"
        }

    db.delete(client)

    db.commit()

    return {
        "message": f"Client {id_client} supprimé avec succès"
    }


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

    nouveau_produit = Produit(
        designation=produit.designation,
        prix_unitaire=produit.prix_unitaire,
        description=produit.description,
        image=produit.image,
        stock=produit.stock,
        categorie=produit.categorie,
        actif=produit.actif
    )

    db.add(nouveau_produit)

    db.commit()

    db.refresh(nouveau_produit)

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

    # -----------------------------------------------------
    # RECHERCHE DU PRODUIT
    # -----------------------------------------------------

    produit_existant = db.query(Produit).filter(
        Produit.id_produit == id_produit
    ).first()

    if produit_existant is None:

        raise HTTPException(
            status_code=404,
            detail="Produit introuvable."
        )

    # -----------------------------------------------------
    # MODIFICATION DES INFORMATIONS
    # -----------------------------------------------------

    produit_existant.designation = produit.designation

    produit_existant.prix_unitaire = produit.prix_unitaire

    produit_existant.description = produit.description

    produit_existant.image = produit.image

    produit_existant.stock = produit.stock

    produit_existant.categorie = produit.categorie

    produit_existant.actif = produit.actif

    # -----------------------------------------------------
    # ENREGISTREMENT
    # -----------------------------------------------------

    try:

        db.commit()

        db.refresh(produit_existant)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue lors "
                "de la modification du produit."
            )
        )

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
# AJOUTER UN SERVICE
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
    Ajoute un nouveau service.

    Seul l'administrateur peut créer un service.
    """

    nouveau_service = Service(
        nom_service=service.nom_service,
        prix=service.prix,
        description=service.description,
        categorie=service.categorie,
        image=service.image,
        video=service.video,
        actif=service.actif
    )

    db.add(nouveau_service)
    db.commit()
    db.refresh(nouveau_service)

    return nouveau_service


# =========================================================
# MODIFIER UN SERVICE
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

    Seul l'administrateur peut modifier un service.
    """

    service_existant = db.query(Service).filter(
        Service.id_service == id_service
    ).first()

    if service_existant is None:
        return {
            "message": "Service introuvable"
        }

    service_existant.nom_service = service.nom_service
    service_existant.prix = service.prix
    service_existant.description = service.description
    service_existant.categorie = service.categorie
    service_existant.image = service.image
    service_existant.video = service.video
    service_existant.actif = service.actif

    db.commit()
    db.refresh(service_existant)

    return service_existant


# =========================================================
# SUPPRIMER UN SERVICE
# =========================================================

@app.delete("/services/{id_service}")
def supprimer_service(
    id_service: int,
    utilisateur=Depends(
        role_autorise("admin")
    ),
    db: Session = Depends(get_db)
):
    """
    Supprime un service.

    Seul l'administrateur peut supprimer un service.
    """

    service_existant = db.query(Service).filter(
        Service.id_service == id_service
    ).first()

    if service_existant is None:
        return {
            "message": "Service introuvable"
        }

    # Vérifier si le service est utilisé dans une commande
    ligne_commande = db.query(
        CommandeHasService
    ).filter(
        CommandeHasService.SERVICE_id_service == id_service
    ).first()

    if ligne_commande is not None:
        return {
            "message": (
                "Impossible de supprimer ce service "
                "car il est déjà associé à une commande."
            )
        }

    db.delete(service_existant)
    db.commit()

    return {
        "message": "Service supprimé avec succès"
    }


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
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Rechercher la commande
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande == id_commande
    ).first()

    if commande is None:

        return {
            "message": "Commande introuvable"
        }

    # -----------------------------------------------------
    # 2. Supprimer les lignes de commande
    # -----------------------------------------------------

    produits_commande = db.query(
        CommandeHasProduit
    ).filter(
        CommandeHasProduit.COMMANDE_id_commande
        == id_commande
    ).all()

    for ligne in produits_commande:

        db.delete(ligne)

    # -----------------------------------------------------
    # 3. Supprimer les messages de la commande
    # -----------------------------------------------------

    messages = db.query(
        MessageCommande
    ).filter(
        MessageCommande.COMMANDE_id_commande
        == id_commande
    ).all()

    for message in messages:

        db.delete(message)

    # -----------------------------------------------------
    # 4. Supprimer la commande
    # -----------------------------------------------------

    db.delete(commande)

    db.commit()

    return {
        "message": (
            f"Commande {id_commande} "
            "supprimée avec succès"
        )
    }


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
        Utilisateur.email == utilisateur.email
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
    utilisateur_connecte=Depends(
        role_autorise("admin")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier le rôle
    # -----------------------------------------------------

    roles_autorises = [
        "admin",
        "vendeur",
        "client"
    ]

    if utilisateur.role not in roles_autorises:

        raise HTTPException(
            status_code=400,
            detail="Rôle invalide."
        )

    # -----------------------------------------------------
    # 2. Vérifier l'email
    # -----------------------------------------------------

    utilisateur_existant = db.query(
        Utilisateur
    ).filter(
        Utilisateur.email == utilisateur.email
    ).first()

    if utilisateur_existant:

        raise HTTPException(
            status_code=400,
            detail="Cet email est déjà utilisé."
        )

    # -----------------------------------------------------
    # 3. Sécuriser le mot de passe
    # -----------------------------------------------------

    mot_de_passe_hash = bcrypt.hashpw(
        utilisateur.mot_de_passe.encode("utf-8"),
        bcrypt.gensalt()
    )

    # -----------------------------------------------------
    # 4. Créer l'utilisateur
    # -----------------------------------------------------

    nouvel_utilisateur = Utilisateur(
        nom=utilisateur.nom,
        prenom=utilisateur.prenom,
        email=utilisateur.email,
        mot_de_passe=(
            mot_de_passe_hash.decode("utf-8")
        ),
        role=utilisateur.role
    )

    db.add(nouvel_utilisateur)

    db.commit()

    db.refresh(nouvel_utilisateur)

    # -----------------------------------------------------
    # 5. Retourner le résultat
    # -----------------------------------------------------

    return {

        "message":
            "Utilisateur créé avec succès",

        "id_utilisateur":
            nouvel_utilisateur.id_utilisateur,

        "nom":
            nouvel_utilisateur.nom,

        "prenom":
            nouvel_utilisateur.prenom,

        "email":
            nouvel_utilisateur.email,

        "role":
            nouvel_utilisateur.role
    }


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
            )
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
            )
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

    utilisateur=Depends(
        role_autorise("client")
    ),

    db: Session = Depends(get_db)
):

    # =====================================================
    # 💳 VÉRIFIER LE MODE DE PAIEMENT
    # =====================================================

    if panier.methode_paiement not in METHODES_PAIEMENT:

        raise HTTPException(
            status_code=400,
            detail=(
                "Mode de paiement invalide."
            )
        )

    # =====================================================
    # 1. VÉRIFIER QUE LE PANIER N'EST PAS VIDE
    # =====================================================

    if not panier.lignes and not panier.services:

        raise HTTPException(
            status_code=400,
            detail="Le panier est vide."
        )


    # =====================================================
    # 2. RETROUVER LE CLIENT CONNECTÉ
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
    # 3. PRÉPARER LES PRODUITS
    # =====================================================

    produits_commandes = []


    # =====================================================
    # 4. VÉRIFIER LES PRODUITS DU PANIER
    # =====================================================

    for ligne in panier.lignes:

        produit = db.query(Produit).filter(

            Produit.id_produit
            == ligne.id_produit

        ).first()


        # -------------------------------------------------
        # Produit inexistant
        # -------------------------------------------------

        if produit is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Le produit "
                    f"{ligne.id_produit} "
                    "n'existe pas."
                )
            )


        # -------------------------------------------------
        # Produit désactivé
        # -------------------------------------------------

        if not produit.actif:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Le produit « "
                    f"{produit.designation} » "
                    "n'est plus disponible."
                )
            )


        # -------------------------------------------------
        # Vérification du stock
        # -------------------------------------------------

        if produit.stock < ligne.quantite:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Stock insuffisant pour "
                    f"« {produit.designation} ». "
                    f"Stock disponible : "
                    f"{produit.stock}."
                )
            )


        # -------------------------------------------------
        # Ajouter le produit à la liste validée
        # -------------------------------------------------

        produits_commandes.append(
            (
                produit,
                ligne.quantite
            )
        )


    # =====================================================
    # 5. PRÉPARER LES SERVICES
    # =====================================================

    services_commandes = []


    # =====================================================
    # 6. VÉRIFIER LES SERVICES DU PANIER
    # =====================================================

    for ligne in panier.services:

        service = db.query(Service).filter(

            Service.id_service
            == ligne.id_service

        ).first()


        # -------------------------------------------------
        # Service inexistant
        # -------------------------------------------------

        if service is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Le service "
                    f"{ligne.id_service} "
                    "n'existe pas."
                )
            )


        # -------------------------------------------------
        # Service désactivé
        # -------------------------------------------------

        if not service.actif:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Le service « "
                    f"{service.nom_service} » "
                    "n'est actuellement "
                    "plus disponible."
                )
            )


        # -------------------------------------------------
        # Ajouter le service à la liste validée
        # -------------------------------------------------

        services_commandes.append(
            (
                service,
                ligne.quantite
            )
        )


    # =====================================================
    # 7. CRÉER UNE SEULE COMMANDE
    # =====================================================

    nouvelle_commande = Commande(

        date_commande=date.today(),

        CLIENT_id_client=client.id_client,

        statut="en_attente"
    )


    db.add(
        nouvelle_commande
    )


    # -----------------------------------------------------
    # IMPORTANT
    # -----------------------------------------------------
    #
    # flush() permet de récupérer immédiatement
    # l'identifiant de la commande avant le commit.
    #
    # Cet identifiant sera utilisé pour :
    #
    # COMMANDE_has_PRODUIT
    #
    # et
    #
    # COMMANDE_has_SERVICE
    #
    # -----------------------------------------------------

    db.flush()


    # =========================================================
    # 🔔 NOTIFICATIONS — NOUVELLE COMMANDE
    # =========================================================

    # ---------------------------------------------------------
    # 1. Notification pour le client
    # ---------------------------------------------------------

    creer_notification(
        db=db,
        id_utilisateur=utilisateur.id_utilisateur,
        titre="Commande confirmée",
        message=(
            f"Votre commande #{nouvelle_commande.id_commande} "
            "a été enregistrée avec succès."
        ),
        type_notification="success",
        lien="/mes-commandes"
    )


    # ---------------------------------------------------------
    # 2. Récupérer tous les administrateurs et vendeurs
    # ---------------------------------------------------------

    destinataires = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.role.in_(
                ["admin", "vendeur"]
            )
        )
        .all()
    )


    # ---------------------------------------------------------
    # 3. Notification pour chaque administrateur/vendeur
    # ---------------------------------------------------------

    for destinataire in destinataires:

        creer_notification(
            db=db,
            id_utilisateur=destinataire.id_utilisateur,
            titre="Nouvelle commande",
            message=(
                f"La commande #{nouvelle_commande.id_commande} "
                "vient d'être passée par un client."
            ),
            type_notification="commande",
            lien="/commandes"
        )


        # =====================================================
        # 8. CALCUL DU TOTAL
        # =====================================================

        total_commande = 0


        # =====================================================
        # 9. CRÉER LES LIGNES PRODUITS
        # =====================================================

        for produit, quantite in produits_commandes:

            prix = produit.prix_unitaire


            ligne_commande = CommandeHasProduit(

                COMMANDE_id_commande=
                    nouvelle_commande.id_commande,

                PRODUIT_id_produit=
                    produit.id_produit,

                quantite=quantite,

                prix_unitaire=prix
            )


            db.add(
                ligne_commande
            )


            # ---------------------------------------------------------
            # Sauvegarder le stock avant la vente
            # ---------------------------------------------------------

            ancien_stock = produit.stock or 0


            # ---------------------------------------------------------
            # Déduire la quantité commandée
            # ---------------------------------------------------------

            produit.stock -= ligne.quantite


            # ---------------------------------------------------------
            # Vérifier si le seuil est franchi
            # ---------------------------------------------------------

            verifier_stock_faible(
                db=db,
                produit=produit,
                ancien_stock=ancien_stock,
                seuil=5
            )

            # -------------------------------------------------
            # Ajouter au total
            # -------------------------------------------------

            total_commande += (
                prix * quantite
            )


        # =====================================================
        # 10. CRÉER LES LIGNES SERVICES
        # =====================================================

        for service, quantite in services_commandes:

            prix = service.prix


            ligne_service = CommandeHasService(

                COMMANDE_id_commande=
                    nouvelle_commande.id_commande,

                SERVICE_id_service=
                    service.id_service,

                quantite=quantite,

                prix_unitaire=prix
            )


            db.add(
                ligne_service
            )


            # -------------------------------------------------
            # Ajouter le service au total
            # -------------------------------------------------

            total_commande += (
                prix * quantite
            )


        # =====================================================
        # 11. CRÉER LE PAIEMENT
        # =====================================================

        # -----------------------------------------------------
        # Vérifier le mode de paiement
        # -----------------------------------------------------

        METHODES_PAIEMENT = [
            "livraison",
            "wave",
            "orange_money",
            "carte"
        ]

        if panier.methode_paiement not in METHODES_PAIEMENT:

            raise HTTPException(
                status_code=400,
                detail="Mode de paiement invalide."
            )


        # -----------------------------------------------------
        # Déterminer le statut initial du paiement
        # -----------------------------------------------------

        # Pour le moment :
        #
        # livraison     → paiement en attente
        # wave          → paiement en attente
        # orange_money  → paiement en attente
        # carte         → paiement en attente
        #
        # Les paiements électroniques ne seront considérés
        # comme réellement payés qu'après confirmation
        # d'un véritable prestataire de paiement.

        statut_paiement = "en_attente"


        # -----------------------------------------------------
        # Créer la ligne PAIEMENT
        # -----------------------------------------------------

        nouveau_paiement = Paiement(

            COMMANDE_id_commande=(
                nouvelle_commande.id_commande
            ),

            UTILISATEUR_id_utilisateur=(
                utilisateur.id_utilisateur
            ),

            montant=total_commande,

            methode=panier.methode_paiement,

            statut=statut_paiement,

            reference=None
        )


        db.add(nouveau_paiement)


        # =====================================================
        # 12. ENREGISTRER COMMANDE + PAIEMENT
        # =====================================================

        try:

            db.commit()

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Une erreur est survenue lors "
                    "de l'enregistrement de la commande "
                    "et du paiement."
                )
            )


        # =====================================================
        # 13. ACTUALISER LES OBJETS
        # =====================================================

        db.refresh(
            nouvelle_commande
        )

        db.refresh(
            nouveau_paiement
        )
        # =====================================================
        # 12. ACTUALISER LA COMMANDE
        # =====================================================

        db.refresh(
            nouvelle_commande
        )


        # =====================================================
        # 14. RÉPONSE FINALE
        # =====================================================

        return {

            "message":
                "Commande et paiement enregistrés avec succès.",

            # -------------------------------------------------
            # Commande
            # -------------------------------------------------

            "id_commande":
                nouvelle_commande.id_commande,

            "id_client":
                client.id_client,

            "date_commande":
                str(
                    nouvelle_commande.date_commande
                ),

            "statut":
                nouvelle_commande.statut,

            # -------------------------------------------------
            # Contenu
            # -------------------------------------------------

            "nombre_produits":
                len(produits_commandes),

            "nombre_services":
                len(services_commandes),

            # -------------------------------------------------
            # Total
            # -------------------------------------------------

            "total":
                total_commande,

            # -------------------------------------------------
            # Paiement
            # -------------------------------------------------

            "id_paiement":
                nouveau_paiement.id_paiement,

            "methode_paiement":
                nouveau_paiement.methode,

            "statut_paiement":
                nouveau_paiement.statut,

            "reference_paiement":
                nouveau_paiement.reference
        }
            



   # =========================================================
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
                f"Le produit « {produit.nom_produit} » "
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

    jours_ecoules = (
        date.today()
        - commande.date_commande
    ).days

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
    utilisateur=Depends(
        role_autorise("admin", "vendeur")
    ),
    db: Session = Depends(get_db)
):

    statuts_autorises = [

        "en_attente",

        "confirmee",

        "en_preparation",

        "prete",

        "livree",

        "annulee"
    ]

    # -----------------------------------------------------
    # 1. Vérifier le statut
    # -----------------------------------------------------

    if nouveau_statut not in statuts_autorises:

        raise HTTPException(
            status_code=400,
            detail="Statut invalide."
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
    # 3. Vérifier si elle est déjà annulée
    # -----------------------------------------------------

    if commande.statut == "annulee":

        raise HTTPException(
            status_code=400,
            detail=(
                "Cette commande est déjà annulée."
            )
        )

    # -----------------------------------------------------
    # 4. Si annulation : restaurer le stock
    # -----------------------------------------------------

    if nouveau_statut == "annulee":

        lignes = db.query(
            CommandeHasProduit
        ).filter(
            CommandeHasProduit.COMMANDE_id_commande
            == id_commande
        ).all()

        for ligne in lignes:

            produit = db.query(Produit).filter(
                Produit.id_produit
                == ligne.PRODUIT_id_produit
            ).first()

            if produit is not None:

                produit.stock += ligne.quantite

    # -----------------------------------------------------
    # 5. Modifier le statut
    # -----------------------------------------------------

    commande.statut = nouveau_statut

    # -----------------------------------------------------
    # 6. Enregistrer
    # -----------------------------------------------------

    try:

        db.commit()

        db.refresh(commande)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de la modification "
                "du statut."
            )
        )

    # -----------------------------------------------------
    # 7. Réponse
    # -----------------------------------------------------

    return {

        "message":
            "Statut de la commande "
            "modifié avec succès.",

        "id_commande":
            commande.id_commande,

        "statut":
            commande.statut
    }



    #=========================================================
    # 🔔 NOTIFICATION — CHANGEMENT DE STATUT
    # =========================================================

    # ---------------------------------------------------------
    # Récupérer le client propriétaire de la commande
    # ---------------------------------------------------------

    client = (
        db.query(Client)
        .filter(
            Client.id_client == commande.CLIENT_id_client
        )
        .first()
    )

    if client and client.id_utilisateur:

        # -----------------------------------------------------
        # Traduction du statut pour une notification agréable
        # -----------------------------------------------------

        statuts_notifications = {

            "en_attente": {
                "titre": "Commande en attente",
                "message": (
                    f"Votre commande #{commande.id_commande} "
                    "est en attente de traitement."
                ),
                "type": "info"
            },

            "en_preparation": {
                "titre": "Commande en préparation",
                "message": (
                    f"Votre commande #{commande.id_commande} "
                    "est maintenant en préparation."
                ),
                "type": "info"
            },

            "en_livraison": {
                "titre": "Commande en livraison",
                "message": (
                    f"Votre commande #{commande.id_commande} "
                    "est maintenant en cours de livraison."
                ),
                "type": "commande"
            },

            "livree": {
                "titre": "Commande livrée",
                "message": (
                    f"Votre commande #{commande.id_commande} "
                    "a été livrée avec succès. "
                    "Merci pour votre confiance !"
                ),
                "type": "success"
            },

            "annulee": {
                "titre": "Commande annulée",
                "message": (
                    f"Votre commande #{commande.id_commande} "
                    "a été annulée."
                ),
                "type": "danger"
            }
        }

        # -----------------------------------------------------
        # Récupérer le contenu correspondant au statut
        # -----------------------------------------------------

        notification = statuts_notifications.get(
            str(nouveau_statut).lower(),
            {
                "titre": "Commande mise à jour",
                "message": (
                    f"Le statut de votre commande "
                    f"#{commande.id_commande} a été mis à jour."
                ),
                "type": "info"
            }
        )

        # -----------------------------------------------------
        # Créer la notification
        # -----------------------------------------------------

        creer_notification(
            db=db,
            id_utilisateur=client.id_utilisateur,
            titre=notification["titre"],
            message=notification["message"],
            type_notification=notification["type"],
            lien="/mes-commandes"
        )




# =========================================================
# TROUVER LE DESTINATAIRE D'UN MESSAGE
# =========================================================
#
# Cette fonction détermine automatiquement à qui envoyer
# le message selon l'utilisateur connecté et la commande.
#
# Cas 1 :
#     CLIENT → VENDEUR / ADMIN
#
# Cas 2 :
#     VENDEUR / ADMIN → CLIENT
#
# =========================================================

def trouver_destinataire_message(
    db,
    commande,
    utilisateur_connecte
):

    # -----------------------------------------------------
    # 1. Vérifier que la commande possède un client
    # -----------------------------------------------------

    client = db.query(Client).filter(
        Client.id_client == commande.CLIENT_id_client
    ).first()

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client de la commande introuvable."
        )

    # -----------------------------------------------------
    # 2. Récupérer l'utilisateur associé au client
    # -----------------------------------------------------

    utilisateur_client = db.query(Utilisateur).filter(
        Utilisateur.id_utilisateur == client.id_utilisateur
    ).first()

    if not utilisateur_client:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur du client introuvable."
        )

    # -----------------------------------------------------
    # 3. Si l'utilisateur connecté est le CLIENT
    # -----------------------------------------------------
    #
    # Le message doit aller à un vendeur.
    #
    # On choisit ici un utilisateur ayant le rôle
    # "vendeur".
    #
    # -----------------------------------------------------

    if utilisateur_connecte.role == "client":

        vendeur = db.query(Utilisateur).filter(
            Utilisateur.role == "vendeur"
        ).first()

        if not vendeur:

            # Si aucun vendeur n'existe, on cherche
            # éventuellement un administrateur.

            admin = db.query(Utilisateur).filter(
                Utilisateur.role == "admin"
            ).first()

            if not admin:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Aucun vendeur ou administrateur "
                        "disponible pour recevoir le message."
                    )
                )

            return admin

        return vendeur

    # -----------------------------------------------------
    # 4. Si l'utilisateur connecté est VENDEUR ou ADMIN
    # -----------------------------------------------------
    #
    # Le message doit revenir au client de la commande.
    # -----------------------------------------------------

    if utilisateur_connecte.role in ["vendeur", "admin"]:

        return utilisateur_client

    # -----------------------------------------------------
    # 5. Cas d'un rôle non autorisé
    # -----------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail="Rôle non autorisé pour la messagerie."
    )


# =========================================================
# MESSAGERIE DES COMMANDES
# =========================================================


# =========================================================
# ENVOYER UN MESSAGE TEXTE POUR UNE COMMANDE
# =========================================================

@app.post(
    "/commandes/{id_commande}/messages",
    response_model=MessageCommandeResponse
)
def envoyer_message_commande(
    id_commande: int,
    message_data: MessageCommandeCreate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. VÉRIFIER QUE LA COMMANDE EXISTE
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
    # 2. VÉRIFICATION DU CLIENT
    # -----------------------------------------------------
    #
    # Si l'utilisateur connecté est un client, il doit
    # obligatoirement être propriétaire de la commande.
    #
    # Cette sécurité existait déjà dans ton code et nous
    # la conservons.
    # -----------------------------------------------------

    if utilisateur.role == "client":

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

        if (
            commande.CLIENT_id_client
            != client.id_client
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous ne pouvez pas envoyer "
                    "un message pour cette commande."
                )
            )

    # -----------------------------------------------------
    # 3. VÉRIFIER QUE LE MESSAGE N'EST PAS VIDE
    # -----------------------------------------------------

    texte = message_data.message.strip()

    if not texte:

        raise HTTPException(
            status_code=400,
            detail="Le message ne peut pas être vide."
        )

    # -----------------------------------------------------
    # 4. TROUVER LE DESTINATAIRE
    # -----------------------------------------------------
    #
    # Cette fonction a été créée précédemment :
    #
    #     trouver_destinataire_message(...)
    #
    # Elle détermine automatiquement :
    #
    # CLIENT
    #    ↓
    # VENDEUR / ADMIN
    #
    # ou :
    #
    # VENDEUR / ADMIN
    #    ↓
    # CLIENT
    # -----------------------------------------------------

    destinataire = trouver_destinataire_message(
        db=db,
        commande=commande,
        utilisateur_connecte=utilisateur
    )

    # -----------------------------------------------------
    # 5. VÉRIFICATION SUPPLÉMENTAIRE
    # -----------------------------------------------------
    #
    # On évite qu'un utilisateur puisse être son propre
    # destinataire.
    # -----------------------------------------------------

    if (
        destinataire.id_utilisateur
        == utilisateur.id_utilisateur
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Le destinataire du message "
                "ne peut pas être l'expéditeur."
            )
        )

    # -----------------------------------------------------
    # 6. CRÉER LE MESSAGE
    # -----------------------------------------------------

    nouveau_message = MessageCommande(

        # Commande concernée
        COMMANDE_id_commande=id_commande,

        # Expéditeur
        UTILISATEUR_id_utilisateur=
            utilisateur.id_utilisateur,

        # Destinataire
        UTILISATEUR_destinataire_id=
            destinataire.id_utilisateur,

        # Texte
        message=texte,

        # Nouveau message = non lu
        lu=False
    )

    # -----------------------------------------------------
    # 7. ENREGISTRER DANS LA BASE
    # -----------------------------------------------------

    db.add(nouveau_message)

    db.commit()

    db.refresh(nouveau_message)

    # -----------------------------------------------------
    # 8. RETOURNER LE MESSAGE
    # -----------------------------------------------------

    return nouveau_message


    # =========================================================
    # 🔔 NOTIFICATION — NOUVEAU MESSAGE
    # =========================================================

    # ---------------------------------------------------------
    # Identifier l'expéditeur
    # ---------------------------------------------------------

    expediteur = utilisateur


    # ---------------------------------------------------------
    # Identifier le destinataire
    # ---------------------------------------------------------

    commande = (
        db.query(Commande)
        .filter(
            Commande.id_commande == id_commande
        )
        .first()
    )

    if commande:

        # =====================================================
        # CAS 1 : LE CLIENT ENVOIE UN MESSAGE
        # =====================================================

        if expediteur.role == "client":

            # Tous les administrateurs et vendeurs
            # doivent être informés.

            destinataires = (
                db.query(Utilisateur)
                .filter(
                    Utilisateur.role.in_(
                        ["admin", "vendeur"]
                    )
                )
                .all()
            )

            for destinataire in destinataires:

                creer_notification(
                    db=db,
                    id_utilisateur=(
                        destinataire.id_utilisateur
                    ),
                    titre="Nouveau message",
                    message=(
                        f"Un client vous a envoyé "
                        f"un message concernant la "
                        f"commande #{id_commande}."
                    ),
                    type_notification="message",
                    lien="/commandes"
                )

        # =====================================================
        # CAS 2 : ADMIN OU VENDEUR RÉPOND AU CLIENT
        # =====================================================

        else:

            client = (
                db.query(Client)
                .filter(
                    Client.id_client
                    == commande.CLIENT_id_client
                )
                .first()
            )

            if client and client.id_utilisateur:

                creer_notification(
                    db=db,
                    id_utilisateur=(
                        client.id_utilisateur
                    ),
                    titre="Nouveau message",
                    message=(
                        f"Vous avez reçu un nouveau "
                        f"message concernant votre "
                        f"commande #{id_commande}."
                    ),
                    type_notification="message",
                    lien="/mes-commandes"
                )


# =========================================================
# AFFICHER LES MESSAGES D'UNE COMMANDE
# =========================================================
#
# Cette route :
#
# - vérifie que la commande existe ;
# - vérifie que le client possède bien la commande ;
# - marque automatiquement comme LUS les messages reçus
#   lorsque la conversation est ouverte ;
# - retourne ensuite tous les messages.
#
# LOGIQUE :
#
# CLIENT
#   -> ouvre la conversation
#   -> ses messages reçus deviennent lus
#
# VENDEUR / ADMIN
#   -> ouvre la conversation
#   -> les messages envoyés par le client deviennent lus
#
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
    # 1. Vérifier que la commande existe
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
    # 2. Vérifier les droits du client
    # -----------------------------------------------------

    if utilisateur.role == "client":

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

        # Le client ne peut consulter que ses commandes.

        if (
            commande.CLIENT_id_client
            != client.id_client
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous ne pouvez pas consulter "
                    "les messages de cette commande."
                )
            )

    # -----------------------------------------------------
    # 3. MARQUER LES MESSAGES COMME LUS
    # -----------------------------------------------------
    #
    # CAS 1 :
    # CLIENT ouvre la conversation
    #
    # On marque comme lus uniquement les messages
    # qui lui sont destinés.
    #
    # CAS 2 :
    # VENDEUR ou ADMIN ouvre la conversation
    #
    # On considère que la conversation est prise en charge
    # par le personnel de la boutique.
    #
    # On marque donc comme lus les messages envoyés
    # par le client.
    #
    # -----------------------------------------------------

    if utilisateur.role == "client":

        # -------------------------------------------------
        # Le client lit les réponses du vendeur/admin.
        # -------------------------------------------------

        db.query(MessageCommande).filter(

            MessageCommande.COMMANDE_id_commande
            == id_commande,

            MessageCommande.UTILISATEUR_destinataire_id
            == utilisateur.id_utilisateur,

            MessageCommande.lu == False

        ).update(

            {
                MessageCommande.lu: True
            },

            synchronize_session=False
        )

    else:

        # -------------------------------------------------
        # Admin ou vendeur lit les messages du client.
        #
        # On identifie le client propriétaire de la commande.
        # -------------------------------------------------

        client = db.query(Client).filter(
            Client.id_client
            == commande.CLIENT_id_client
        ).first()

        if client is not None:

            db.query(MessageCommande).filter(

                MessageCommande.COMMANDE_id_commande
                == id_commande,

                MessageCommande.UTILISATEUR_id_utilisateur
                == client.id_utilisateur,

                MessageCommande.lu == False

            ).update(

                {
                    MessageCommande.lu: True
                },

                synchronize_session=False
            )

    # -----------------------------------------------------
    # 4. Enregistrer les changements de statut LU
    # -----------------------------------------------------

    db.commit()

    # -----------------------------------------------------
    # 5. Récupérer tous les messages de la conversation
    # -----------------------------------------------------

    messages = db.query(
        MessageCommande
    ).filter(

        MessageCommande.COMMANDE_id_commande
        == id_commande

    ).order_by(

        MessageCommande.date_message.asc()

    ).all()

    # -----------------------------------------------------
    # 6. Préparer la réponse
    # -----------------------------------------------------

    resultats = []

    for message in messages:

        # -------------------------------------------------
        # Rechercher l'expéditeur
        # -------------------------------------------------

        expediteur = db.query(
            Utilisateur
        ).filter(

            Utilisateur.id_utilisateur
            == message.UTILISATEUR_id_utilisateur

        ).first()

        # -------------------------------------------------
        # Construire le résultat
        # -------------------------------------------------

        resultats.append({

            "id_message":
                message.id_message,

            "COMMANDE_id_commande":
                message.COMMANDE_id_commande,

            "UTILISATEUR_id_utilisateur":
                message.UTILISATEUR_id_utilisateur,

            "message":
                message.message,

            "audio_url":
                message.audio_url,

            "date_message":
                message.date_message,

            "lu":
                message.lu,

            "nom_utilisateur":
                expediteur.nom
                if expediteur
                else None,

            "prenom_utilisateur":
                expediteur.prenom
                if expediteur
                else None,

            "role_utilisateur":
                expediteur.role
                if expediteur
                else None
        })

    return resultats


# =========================================================
# NOMBRE DE MESSAGES NON LUS POUR UNE COMMANDE
# =========================================================

@app.get(
    "/commandes/{id_commande}/messages/non-lus"
)
def compter_messages_non_lus(
    id_commande: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier que la commande existe
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
    # 2. CLIENT
    # -----------------------------------------------------

    if utilisateur.role == "client":

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

        # Le client ne peut consulter que ses commandes.

        if (
            commande.CLIENT_id_client
            != client.id_client
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous ne pouvez pas consulter "
                    "cette commande."
                )
            )

        # -------------------------------------------------
        # Pour le client :
        #
        # on compte uniquement les messages qui lui sont
        # destinés et qui ne sont pas lus.
        # -------------------------------------------------

        nombre_non_lus = db.query(
            MessageCommande
        ).filter(

            MessageCommande.COMMANDE_id_commande
            == id_commande,

            MessageCommande.UTILISATEUR_destinataire_id
            == utilisateur.id_utilisateur,

            MessageCommande.lu == False

        ).count()

    # -----------------------------------------------------
    # 3. ADMIN / VENDEUR
    # -----------------------------------------------------

    else:

        # -------------------------------------------------
        # Pour le personnel :
        #
        # on compte les messages envoyés par le client
        # qui ne sont pas encore lus.
        #
        # Cela permet à l'admin ET au vendeur de voir
        # le badge rouge.
        # -------------------------------------------------

        client = db.query(Client).filter(
            Client.id_client
            == commande.CLIENT_id_client
        ).first()

        if client is None:

            nombre_non_lus = 0

        else:

            nombre_non_lus = db.query(
                MessageCommande
            ).filter(

                MessageCommande.COMMANDE_id_commande
                == id_commande,

                MessageCommande.UTILISATEUR_id_utilisateur
                == client.id_utilisateur,

                MessageCommande.lu == False

            ).count()

    # -----------------------------------------------------
    # 4. Retourner le résultat
    # -----------------------------------------------------

    return {

        "id_commande":
            id_commande,

        "messages_non_lus":
            nombre_non_lus
    }

# =========================================================
# ENVOYER UN MESSAGE CONCERNANT UNE COMMANDE
# CLIENT
# =========================================================

@app.post("/mes-commandes/{id_commande}/messages")
def envoyer_message_client(
    id_commande: int,
    message_data: dict,
    utilisateur=Depends(
        role_autorise("client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier que le message n'est pas vide
    # -----------------------------------------------------

    contenu = message_data.get("message", "").strip()

    if not contenu:

        raise HTTPException(
            status_code=400,
            detail="Le message ne peut pas être vide."
        )

    # -----------------------------------------------------
    # 2. Rechercher le client connecté
    # -----------------------------------------------------

    client = db.query(Client).filter(
        Client.id_utilisateur
        == utilisateur.id_utilisateur
    ).first()

    if client is None:

        raise HTTPException(
            status_code=404,
            detail="Aucun client associé à cet utilisateur."
        )

    # -----------------------------------------------------
    # 3. Vérifier que la commande existe
    # -----------------------------------------------------

    commande = db.query(Commande).filter(
        Commande.id_commande
        == id_commande
    ).first()

    if commande is None:

        raise HTTPException(
            status_code=404,
            detail="Commande introuvable."
        )

    # -----------------------------------------------------
    # 4. Vérifier que la commande appartient au client
    # -----------------------------------------------------

    if commande.CLIENT_id_client != client.id_client:

        raise HTTPException(
            status_code=403,
            detail=(
                "Vous n'êtes pas autorisé "
                "à envoyer un message concernant "
                "cette commande."
            )
        )

    # -----------------------------------------------------
    # 5. Trouver le destinataire
    # -----------------------------------------------------

    destinataire = trouver_destinataire_message(
        db=db,
        commande=commande,
        utilisateur_connecte=utilisateur
    )

    # -----------------------------------------------------
    # 6. Empêcher l'envoi à soi-même
    # -----------------------------------------------------

    if (
        destinataire.id_utilisateur
        == utilisateur.id_utilisateur
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Le destinataire du message "
                "ne peut pas être l'expéditeur."
            )
        )

    # -----------------------------------------------------
    # 7. Créer le message
    # -----------------------------------------------------

    nouveau_message = MessageCommande(

        COMMANDE_id_commande=id_commande,

        UTILISATEUR_id_utilisateur=
            utilisateur.id_utilisateur,

        UTILISATEUR_destinataire_id=
            destinataire.id_utilisateur,

        message=contenu,

        # Le destinataire n'a pas encore lu le message
        lu=False
    )

    # -----------------------------------------------------
    # 8. Enregistrer le message
    # -----------------------------------------------------

    db.add(nouveau_message)

    db.commit()

    db.refresh(nouveau_message)

    # -----------------------------------------------------
    # 9. Retourner une confirmation
    # -----------------------------------------------------

    return {

        "message":
            "Votre message a été envoyé.",

        "id_message":
            nouveau_message.id_message
    }

# =========================================================
# ENVOYER UN MESSAGE VOCAL POUR UNE COMMANDE
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
    # 1. VÉRIFIER QUE LA COMMANDE EXISTE
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
    # 2. VÉRIFICATION DU CLIENT
    # -----------------------------------------------------
    #
    # Un client ne peut envoyer un vocal que pour
    # sa propre commande.
    # -----------------------------------------------------

    if utilisateur.role == "client":

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

        if (
            commande.CLIENT_id_client
            != client.id_client
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous ne pouvez pas envoyer "
                    "un message vocal pour cette commande."
                )
            )

    # -----------------------------------------------------
    # 3. VÉRIFIER LE FICHIER
    # -----------------------------------------------------

    if fichier is None:

        raise HTTPException(
            status_code=400,
            detail="Aucun fichier vocal reçu."
        )

    # -----------------------------------------------------
    # 4. VÉRIFIER LE NOM DU FICHIER
    # -----------------------------------------------------

    if not fichier.filename:

        raise HTTPException(
            status_code=400,
            detail="Le fichier vocal n'a pas de nom."
        )

    # -----------------------------------------------------
    # 5. TROUVER LE DESTINATAIRE
    # -----------------------------------------------------
    #
    # Même logique que pour les messages texte.
    #
    # CLIENT
    #    ↓
    # VENDEUR / ADMIN
    #
    # VENDEUR / ADMIN
    #    ↓
    # CLIENT
    # -----------------------------------------------------

    destinataire = trouver_destinataire_message(
        db=db,
        commande=commande,
        utilisateur_connecte=utilisateur
    )

    # -----------------------------------------------------
    # 6. EMPÊCHER L'ENVOI À SOI-MÊME
    # -----------------------------------------------------

    if (
        destinataire.id_utilisateur
        == utilisateur.id_utilisateur
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Le destinataire du message "
                "ne peut pas être l'expéditeur."
            )
        )

    # -----------------------------------------------------
    # 7. VÉRIFIER LE DOSSIER AUDIO
    # -----------------------------------------------------

    if not os.path.exists(AUDIO_DIR):

        os.makedirs(
            AUDIO_DIR,
            exist_ok=True
        )

    # -----------------------------------------------------
    # 8. CRÉER UN NOM UNIQUE POUR LE FICHIER
    # -----------------------------------------------------

    extension = os.path.splitext(
        fichier.filename
    )[1]

    # Si le navigateur n'envoie pas d'extension,
    # on utilise .webm car MediaRecorder produit
    # généralement ce format.

    if not extension:

        extension = ".webm"

    nom_fichier = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    chemin_fichier = os.path.join(
        AUDIO_DIR,
        nom_fichier
    )

    # -----------------------------------------------------
    # 9. SAUVEGARDER LE FICHIER AUDIO
    # -----------------------------------------------------

    contenu = await fichier.read()

    if not contenu:

        raise HTTPException(
            status_code=400,
            detail="Le fichier vocal est vide."
        )

    with open(
        chemin_fichier,
        "wb"
    ) as fichier_audio:

        fichier_audio.write(contenu)

    # -----------------------------------------------------
    # 10. URL PUBLIQUE DU FICHIER
    # -----------------------------------------------------

    audio_url = (
        f"/static/audio/{nom_fichier}"
    )

    # -----------------------------------------------------
    # 11. CRÉER LE MESSAGE VOCAL
    # -----------------------------------------------------
    #
    # message = None
    # car il n'y a pas de texte.
    #
    # audio_url contient le chemin du vocal.
    #
    # lu = False
    # car le destinataire ne l'a pas encore écouté.
    # -----------------------------------------------------

    nouveau_message = MessageCommande(

        # Commande concernée
        COMMANDE_id_commande=id_commande,

        # Expéditeur
        UTILISATEUR_id_utilisateur=
            utilisateur.id_utilisateur,

        # Destinataire
        UTILISATEUR_destinataire_id=
            destinataire.id_utilisateur,

        # Aucun texte
        message=None,

        # Fichier vocal
        audio_url=audio_url,

        # Nouveau message = non lu
        lu=False
    )

    # -----------------------------------------------------
    # 12. ENREGISTRER LE MESSAGE
    # -----------------------------------------------------

    db.add(nouveau_message)

    db.commit()

    db.refresh(nouveau_message)

    # -----------------------------------------------------
    # 13. RETOURNER LE MESSAGE
    # -----------------------------------------------------

    return nouveau_message


# =========================================================
# SUPPRIMER SON PROPRE MESSAGE
# =========================================================

@app.delete("/commandes/{id_commande}/messages/{id_message}")
def supprimer_message(
    id_commande: int,
    id_message: int,
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Rechercher le message
    # -----------------------------------------------------

    message = db.query(MessageCommande).filter(
        MessageCommande.id_message == id_message,
        MessageCommande.COMMANDE_id_commande == id_commande
    ).first()

    if message is None:

        raise HTTPException(
            status_code=404,
            detail="Message introuvable."
        )

    # -----------------------------------------------------
    # 2. Vérifier que l'utilisateur est l'auteur
    # -----------------------------------------------------

    if (
        message.UTILISATEUR_id_utilisateur
        != utilisateur.id_utilisateur
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Vous ne pouvez supprimer "
                "que vos propres messages."
            )
        )

    # -----------------------------------------------------
    # 3. Supprimer éventuellement le fichier vocal
    # -----------------------------------------------------

    if message.audio_url:

        chemin = message.audio_url.lstrip("/")

        if os.path.exists(chemin):
            os.remove(chemin)

    # -----------------------------------------------------
    # 4. Supprimer le message de la base
    # -----------------------------------------------------

    db.delete(message)

    db.commit()

    return {
        "message": "Message supprimé."
    }


# =========================================================
# MARQUER UN MESSAGE COMME LU / NON LU
# =========================================================

@app.put(
    "/commandes/{id_commande}/messages/"
    "{id_message}/lu",
    response_model=MessageCommandeResponse
)
def marquer_message_lu(
    id_commande: int,
    id_message: int,
    message_data: MessageCommandeLuUpdate,
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Vérifier que la commande existe
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
    # 2. Chercher le message
    # -----------------------------------------------------

    message = db.query(MessageCommande).filter(
        MessageCommande.id_message == id_message,
        MessageCommande.COMMANDE_id_commande == id_commande
    ).first()

    if message is None:
        raise HTTPException(
            status_code=404,
            detail="Message introuvable."
        )

    # -----------------------------------------------------
    # 3. Vérifier que le message est destiné
    #    à l'utilisateur connecté
    # -----------------------------------------------------

    if (
        message.UTILISATEUR_destinataire_id
        != utilisateur.id_utilisateur
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Vous ne pouvez modifier que "
                "les messages qui vous sont destinés."
            )
        )

    # -----------------------------------------------------
    # 4. Modifier le statut
    # -----------------------------------------------------

    message.lu = message_data.lu

    # -----------------------------------------------------
    # 5. Sauvegarder
    # -----------------------------------------------------

    db.commit()

    db.refresh(message)

    # -----------------------------------------------------
    # 6. Retourner le message
    # -----------------------------------------------------

    return message



# =========================================================
# COMPTER LES MESSAGES NON LUS
# =========================================================

@app.get(
    "/messages/non-lus"
)
def compter_messages_non_lus(
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # On compte uniquement les messages :
    #
    # - destinés à l'utilisateur connecté
    # - qui ne sont pas encore lus
    #
    # -----------------------------------------------------

    nombre_non_lus = db.query(
        MessageCommande
    ).filter(
        MessageCommande.UTILISATEUR_destinataire_id
        == utilisateur.id_utilisateur,

        MessageCommande.lu == False
    ).count()

    # -----------------------------------------------------
    # Retourner le nombre
    # -----------------------------------------------------

    return {
        "nombre_non_lus": nombre_non_lus
    }


# =========================================================
# RÉCUPÉRER TOUTES LES CONVERSATIONS DE L'UTILISATEUR
# =========================================================
#
# Une conversation correspond à une commande.
#
# Pour chaque commande contenant au moins un message,
# on retourne :
#
# - le numéro de la commande
# - le nombre de messages non lus
# - le dernier message
# - la date du dernier message
# - l'expéditeur du dernier message
#
# =========================================================

@app.get(
    "/messages/conversations"
)
def obtenir_conversations(
    utilisateur=Depends(
        role_autorise("admin", "vendeur", "client")
    ),
    db: Session = Depends(get_db)
):

    # ---------------------------------------------------------
    # Récupérer tous les messages accessibles à l'utilisateur
    # ---------------------------------------------------------

    if utilisateur.role == "client":

        # Le client ne doit voir que ses propres commandes.

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

        commandes = db.query(Commande).filter(
            Commande.CLIENT_id_client
            == client.id_client
        ).all()

    else:

        # -----------------------------------------------------
        # Admin et vendeur :
        # pour le moment, ils peuvent voir les conversations
        # de toutes les commandes.
        # -----------------------------------------------------

        commandes = db.query(Commande).all()


    conversations = []


    # =========================================================
    # PARCOURIR LES COMMANDES
    # =========================================================

    for commande in commandes:

        messages = db.query(
            MessageCommande
        ).filter(
            MessageCommande.COMMANDE_id_commande
            == commande.id_commande
        ).order_by(
            MessageCommande.date_message.desc()
        ).all()


        # -----------------------------------------------------
        # Si aucune conversation n'existe pour cette commande,
        # on ne l'affiche pas.
        # -----------------------------------------------------

        if not messages:

            continue


        # -----------------------------------------------------
        # Dernier message
        # -----------------------------------------------------

        dernier_message = messages[0]


        # -----------------------------------------------------
        # Nombre de messages non lus destinés
        # à l'utilisateur connecté
        # -----------------------------------------------------

        nombre_non_lus = db.query(
            MessageCommande
        ).filter(

            MessageCommande.COMMANDE_id_commande
            == commande.id_commande,

            MessageCommande.UTILISATEUR_destinataire_id
            == utilisateur.id_utilisateur,

            MessageCommande.lu == False

        ).count()


        # -----------------------------------------------------
        # Récupérer l'expéditeur du dernier message
        # -----------------------------------------------------

        expediteur = db.query(
            Utilisateur
        ).filter(
            Utilisateur.id_utilisateur
            == dernier_message.UTILISATEUR_id_utilisateur
        ).first()


        # -----------------------------------------------------
        # Déterminer le contenu à afficher dans l'aperçu
        # -----------------------------------------------------

        if dernier_message.audio_url:

            apercu = "🎤 Message vocal"

        elif dernier_message.message:

            apercu = dernier_message.message

        else:

            apercu = "Message"


        # -----------------------------------------------------
        # Informations de l'expéditeur
        # -----------------------------------------------------

        nom_expediteur = None
        prenom_expediteur = None
        role_expediteur = None

        if expediteur:

            nom_expediteur = expediteur.nom
            prenom_expediteur = expediteur.prenom
            role_expediteur = expediteur.role


        # -----------------------------------------------------
        # Ajouter la conversation à la liste
        # -----------------------------------------------------

        conversations.append({

            "id_commande":
                commande.id_commande,

            "statut_commande":
                commande.statut,

            "nombre_messages":
                len(messages),

            "nombre_non_lus":
                nombre_non_lus,

            "dernier_message":
                apercu,

            "date_dernier_message":
                dernier_message.date_message,

            "id_expediteur":
                dernier_message.UTILISATEUR_id_utilisateur,

            "nom_expediteur":
                nom_expediteur,

            "prenom_expediteur":
                prenom_expediteur,

            "role_expediteur":
                role_expediteur
        })


    # =========================================================
    # TRI
    # =========================================================
    #
    # Les conversations les plus récentes apparaissent
    # en premier.
    #
    # =========================================================

    conversations.sort(
        key=lambda conversation:
            conversation["date_dernier_message"],
        reverse=True
    )


    return {
        "nombre_conversations":
            len(conversations),

        "nombre_non_lus":
            sum(
                conversation["nombre_non_lus"]
                for conversation
                in conversations
            ),

        "conversations":
            conversations
    }


# =========================================================
# PHOTOS DE LA PAGE D'ACCUEIL
# =========================================================


# ---------------------------------------------------------
# LISTER LES PHOTOS
# ---------------------------------------------------------

@app.get("/accueil/photos")
def liste_photos_accueil(
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):

    photos = (
        db.query(PhotoAccueil)
        .order_by(
            PhotoAccueil.ordre.asc(),
            PhotoAccueil.id_photo.desc()
        )
        .all()
    )

    return photos


# ---------------------------------------------------------
# AJOUTER UNE PHOTO
# ---------------------------------------------------------

@app.post("/accueil/photos")
def ajouter_photo_accueil(
    nom_fichier: str,
    db: Session = Depends(get_db),
    utilisateur=Depends(role_autorise("admin"))
):

    nouvelle_photo = PhotoAccueil(
        nom_fichier=nom_fichier,
        ordre=0,
        actif=True
    )

    db.add(nouvelle_photo)
    db.commit()
    db.refresh(nouvelle_photo)

    return {
        "message": "Photo d'accueil ajoutée avec succès.",
        "photo": nouvelle_photo
    }


# ---------------------------------------------------------
# SUPPRIMER UNE PHOTO
# ---------------------------------------------------------

@app.delete("/accueil/photos/{id_photo}")
def supprimer_photo_accueil(
    id_photo: int,
    db: Session = Depends(get_db),
    utilisateur=Depends(role_autorise("admin"))
):

    photo = (
        db.query(PhotoAccueil)
        .filter(
            PhotoAccueil.id_photo == id_photo
        )
        .first()
    )

    if photo is None:

        raise HTTPException(
            status_code=404,
            detail="Photo introuvable."
        )

    db.delete(photo)
    db.commit()

    return {
        "message": "Photo supprimée avec succès."
    }



# =========================================================
# PUBLICITÉS VIDÉO
# =========================================================


# ---------------------------------------------------------
# LISTER LES PUBLICITÉS
# ---------------------------------------------------------

@app.get("/accueil/publicites")
def liste_publicites(
    utilisateur=Depends(role_autorise("admin")),
    db: Session = Depends(get_db)
):

    publicites = (
        db.query(Publicite)
        .order_by(
            Publicite.ordre.asc(),
            Publicite.id_publicite.desc()
        )
        .all()
    )

    return publicites


# ---------------------------------------------------------
# AJOUTER UNE PUBLICITÉ
# ---------------------------------------------------------

@app.post("/accueil/publicites")
def ajouter_publicite(
    nom_fichier: str,
    titre: str | None = None,
    db: Session = Depends(get_db),
    utilisateur=Depends(role_autorise("admin"))
):

    nombre_publicites = (
        db.query(Publicite)
        .filter(
            Publicite.actif == True
        )
        .count()
    )

    if nombre_publicites >= 3:

        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez avoir que 3 publicités vidéo actives maximum."
        )

    nouvelle_publicite = Publicite(
        nom_fichier=nom_fichier,
        titre=titre,
        ordre=nombre_publicites,
        actif=True
    )

    db.add(nouvelle_publicite)
    db.commit()
    db.refresh(nouvelle_publicite)

    return {
        "message": "Publicité ajoutée avec succès.",
        "publicite": nouvelle_publicite
    }


# ---------------------------------------------------------
# SUPPRIMER UNE PUBLICITÉ
# ---------------------------------------------------------

@app.delete("/accueil/publicites/{id_publicite}")
def supprimer_publicite(
    id_publicite: int,
    db: Session = Depends(get_db),
    utilisateur=Depends(role_autorise("admin"))
):

    publicite = (
        db.query(Publicite)
        .filter(
            Publicite.id_publicite == id_publicite
        )
        .first()
    )

    if publicite is None:

        raise HTTPException(
            status_code=404,
            detail="Publicité introuvable."
        )

    db.delete(publicite)
    db.commit()

    return {
        "message": "Publicité supprimée avec succès."
    }

# =========================================================
# CONTENU PUBLIC DE LA PAGE D'ACCUEIL
# =========================================================

@app.get("/accueil/contenu")
def contenu_accueil(
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # PHOTOS
    # -----------------------------------------------------

    photos = (
        db.query(PhotoAccueil)
        .filter(
            PhotoAccueil.actif == True
        )
        .order_by(
            PhotoAccueil.ordre.asc(),
            PhotoAccueil.id_photo.desc()
        )
        .all()
    )


    # -----------------------------------------------------
    # PUBLICITÉS
    # -----------------------------------------------------

    publicites = (
        db.query(Publicite)
        .filter(
            Publicite.actif == True
        )
        .order_by(
            Publicite.ordre.asc(),
            Publicite.id_publicite.desc()
        )
        .limit(3)
        .all()
    )


    # -----------------------------------------------------
    # PRODUITS
    # -----------------------------------------------------

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


    return {

        "photos": [
            {
                "id_photo": photo.id_photo,
                "nom_fichier": photo.nom_fichier
            }
            for photo in photos
        ],

        "publicites": [
            {
                "id_publicite": pub.id_publicite,
                "nom_fichier": pub.nom_fichier,
                "titre": pub.titre
            }
            for pub in publicites
        ],

        "produits": [
            {
                "id_produit": produit.id_produit,
                "designation": produit.designation,
                "prix_unitaire": produit.prix_unitaire,
                "description": produit.description,
                "image": produit.image,
                "stock": produit.stock,
                "categorie": produit.categorie
            }
            for produit in produits
        ]
    }



# =========================================================
# DASHBOARD ADMIN / VENDEUR
# STATISTIQUES GENERALES DE LA BOUTIQUE
# =========================================================

@app.get("/dashboard/statistiques")
def statistiques_dashboard(
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
    # 7. DERNIERES COMMANDES
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
        "dernieres_commandes": liste_commandes
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

            Notification.lu == False
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

            Notification.lu == False
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