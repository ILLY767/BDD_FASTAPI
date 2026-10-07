from pydantic import BaseModel, Field
from datetime import date, datetime


# =========================================================
# SCHÉMA CLIENT
# =========================================================

class ClientCreate(BaseModel):

    nom: str
    prenom: str
    date_naissance: date | None = None
    email: str
    telephone: str


# =========================================================
# SCHÉMA POUR MODIFIER UN CLIENT
# =========================================================

class ClientUpdate(BaseModel):

    nom: str
    prenom: str
    date_naissance: date | None = None
    email: str
    telephone: str


# =========================================================
# SCHÉMA POUR CRÉER UN PRODUIT
# =========================================================

class ProduitCreate(BaseModel):

    designation: str
    prix_unitaire: float
    description: str | None = None
    image: str | None = None
    stock: int = 0
    categorie: str | None = None
    actif: bool = True


# =========================================================
# SCHÉMA POUR MODIFIER UN PRODUIT
# =========================================================

class ProduitUpdate(BaseModel):

    designation: str
    prix_unitaire: float
    description: str | None = None
    image: str | None = None
    stock: int = 0
    categorie: str | None = None
    actif: bool = True


# =========================================================
# SCHÉMA POUR CRÉER UNE COMMANDE
# =========================================================

class CommandeCreate(BaseModel):

    # Identifiant du client qui passe la commande
    CLIENT_id_client: int

    # Date de la commande
    date_commande: date

    # Statut initial de la commande
    statut: str = "en_attente"


# =========================================================
# SCHÉMA POUR MODIFIER UNE COMMANDE
# =========================================================

class CommandeUpdate(BaseModel):

    # Nouvel identifiant du client
    CLIENT_id_client: int

    # Nouvelle date de la commande
    date_commande: date

    # Nouveau statut
    statut: str


# =========================================================
# SCHÉMA : AJOUTER UN PRODUIT À UNE COMMANDE
# =========================================================

class CommandeHasProduitCreate(BaseModel):

    # Identifiant du produit
    PRODUIT_id_produit: int

    # Quantité : au minimum 1
    quantite: int = Field(..., ge=1)


# =========================================================
# SCHÉMA : MODIFIER LA QUANTITÉ D'UN PRODUIT
# DANS UNE COMMANDE
# =========================================================

class CommandeHasProduitUpdate(BaseModel):

    # Nouvelle quantité commandée
    # La quantité doit être au minimum égale à 1
    quantite: int = Field(..., ge=1)


# =========================================================
# CONNEXION UTILISATEUR
# =========================================================

class UtilisateurLogin(BaseModel):

    # Adresse email utilisée pour identifier l'utilisateur
    email: str

    # Mot de passe saisi lors de la connexion
    mot_de_passe: str


# =========================================================
# CRÉATION D'UN UTILISATEUR
# =========================================================

class UtilisateurCreate(BaseModel):

    nom: str
    prenom: str
    email: str
    mot_de_passe: str
    role: str = "client"

class UtilisateurClientCreate(BaseModel):
    """
    Schéma utilisé uniquement lors de l'inscription
    publique d'un client.
    """

    nom: str
    prenom: str
    date_naissance: date | None = None
    email: str
    telephone: str
    mot_de_passe: str

# =========================================================
# SCHÉMA : LIGNE DE COMMANDE DEPUIS LE PANIER
# =========================================================

class LigneCommandeCreate(BaseModel):

    id_produit: int
    quantite: int


# =========================================================
# SCHÉMA : CRÉER UNE COMMANDE DEPUIS LE PANIER
# =========================================================

# =========================================================
# LIGNE DE PRODUIT DU PANIER
# =========================================================

class LigneProduitPanier(BaseModel):

    id_produit: int

    quantite: int = Field(
        ...,
        ge=1
    )


# =========================================================
# LIGNE DE SERVICE DU PANIER
# =========================================================

class LigneServicePanier(BaseModel):

    id_service: int

    quantite: int = Field(
        ...,
        ge=1
    )


# =========================================================
# PANIER COMPLET
# =========================================================
#
# Un panier peut maintenant contenir :
#
# - des produits
# - des services
# - ou les deux
#
# Exemple :
#
# {
#     "lignes": [
#         {
#             "id_produit": 5,
#             "quantite": 2
#         }
#     ],
#
#     "services": [
#         {
#             "id_service": 1,
#             "quantite": 1
#         }
#     ]
# }
#
# =========================================================

# =========================================================
# 🛒 COMMANDE DEPUIS LE PANIER
# =========================================================

class CommandeDepuisPanierCreate(BaseModel):

    lignes: list[LigneProduitPanier] = []

    services: list[LigneServicePanier] = []

    # -----------------------------------------------------
    # 💳 MODE DE PAIEMENT
    # -----------------------------------------------------

    methode_paiement: str = "livraison"
    
# =========================================================
# SCHÉMA : RÉPONSE COMMANDE
# =========================================================

class CommandeResponse(BaseModel):

    id_commande: int
    CLIENT_id_client: int
    date_commande: date
    statut: str

    class Config:
        from_attributes = True


# =========================================================
# SCHÉMA : CRÉER UN MESSAGE POUR UNE COMMANDE
# =========================================================

class MessageCommandeCreate(BaseModel):

    # Contenu du message
    message: str = Field(..., min_length=1)


# =========================================================
# RÉPONSE : MESSAGE D'UNE COMMANDE
# =========================================================

class MessageCommandeResponse(BaseModel):

    # -----------------------------------------------------
    # IDENTIFIANT DU MESSAGE
    # -----------------------------------------------------

    id_message: int

    # -----------------------------------------------------
    # COMMANDE CONCERNÉE
    # -----------------------------------------------------

    COMMANDE_id_commande: int

    # -----------------------------------------------------
    # EXPÉDITEUR
    # -----------------------------------------------------

    UTILISATEUR_id_utilisateur: int

    # -----------------------------------------------------
    # DESTINATAIRE
    # -----------------------------------------------------

    UTILISATEUR_destinataire_id: int | None = None

    # -----------------------------------------------------
    # MESSAGE TEXTUEL
    # -----------------------------------------------------
    # NULL lorsqu'il s'agit uniquement d'un vocal.

    message: str | None = None

    # -----------------------------------------------------
    # DATE DU MESSAGE
    # -----------------------------------------------------

    date_message: datetime

    # -----------------------------------------------------
    # MESSAGE LU OU NON LU
    # -----------------------------------------------------

    lu: bool

    # -----------------------------------------------------
    # MESSAGE VOCAL
    # -----------------------------------------------------

    audio_url: str | None = None

    # -----------------------------------------------------
    # INFORMATIONS SUR L'EXPÉDITEUR
    # -----------------------------------------------------

    nom_utilisateur: str | None = None

    prenom_utilisateur: str | None = None

    role_utilisateur: str | None = None

    # -----------------------------------------------------
    # INFORMATIONS SUR LE DESTINATAIRE
    # -----------------------------------------------------

    nom_destinataire: str | None = None

    prenom_destinataire: str | None = None

    role_destinataire: str | None = None

    # -----------------------------------------------------
    # CONFIGURATION PYDANTIC
    # -----------------------------------------------------

    class Config:
        from_attributes = True

# =========================================================
# SCHÉMA : MARQUER UN MESSAGE COMME LU
# =========================================================

class MessageCommandeLuUpdate(BaseModel):

    lu: bool = True


# =========================================================
# SCHEMAS : PHOTOS D'ACCUEIL
# =========================================================

class PhotoAccueilResponse(BaseModel):

    id_photo: int
    nom_fichier: str
    ordre: int
    actif: bool
    date_ajout: datetime

    class Config:
        from_attributes = True


# =========================================================
# SCHEMAS : PUBLICITÉS
# =========================================================

class PubliciteResponse(BaseModel):

    id_publicite: int
    nom_fichier: str
    titre: str | None = None
    ordre: int
    actif: bool
    date_ajout: datetime

    class Config:
        from_attributes = True



# =========================================================
# SCHÉMAS SERVICE
# =========================================================

class ServiceCreate(BaseModel):
    nom_service: str
    prix: float
    description: str | None = None
    categorie: str | None = None
    image: str | None = None
    video: str | None = None
    actif: bool = True


class ServiceUpdate(BaseModel):
    nom_service: str
    prix: float
    description: str | None = None
    categorie: str | None = None
    image: str | None = None
    video: str | None = None
    actif: bool = True


# =========================================================
# SCHÉMAS COMMANDE - SERVICE
# =========================================================

class CommandeHasServiceCreate(BaseModel):
    SERVICE_id_service: int
    quantite: int = Field(..., ge=1)


class CommandeHasServiceUpdate(BaseModel):
    quantite: int = Field(..., ge=1)