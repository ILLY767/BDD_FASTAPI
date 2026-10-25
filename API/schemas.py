from datetime import date, datetime
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
)


# =========================================================
# CONFIGURATION COMMUNE PYDANTIC
# =========================================================

class SchemaBase(BaseModel):
    # Compatible avec les objets SQLAlchemy (Pydantic v2).
    model_config = ConfigDict(from_attributes=True)


# =========================================================
# CLIENTS
# =========================================================

class ClientCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    date_naissance: date | None = None
    email: str = Field(..., min_length=3, max_length=255)
    telephone: str = Field(..., min_length=1, max_length=30)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def verifier_paire_coordonnees(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être renseignées ensemble.")
        return self

    @field_validator("nom", "prenom", "email", "telephone")
    @classmethod
    def nettoyer_texte(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("Ce champ ne peut pas être vide.")
        return valeur


class ClientUpdate(ClientCreate):
    pass


# =========================================================
# PRODUITS
# =========================================================

class ProduitCreate(BaseModel):
    designation: str = Field(..., min_length=1, max_length=255)
    prix_unitaire: float = Field(..., ge=0)
    description: str | None = None
    image: str | None = None
    stock: int = Field(default=0, ge=0)
    categorie: str | None = None
    actif: bool = True

    @field_validator("designation")
    @classmethod
    def nettoyer_designation(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("La désignation du produit est obligatoire.")
        return valeur


class ProduitUpdate(ProduitCreate):
    pass


# =========================================================
# COMMANDES
# =========================================================

class CommandeCreate(BaseModel):
    CLIENT_id_client: int = Field(..., gt=0)
    date_commande: date
    statut: str = "en_attente"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def verifier_paire_coordonnees(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être renseignées ensemble.")
        return self


class CommandeUpdate(BaseModel):
    CLIENT_id_client: int = Field(..., gt=0)
    date_commande: date
    statut: str = Field(..., min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def verifier_paire_coordonnees(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être renseignées ensemble.")
        return self


# =========================================================
# LIGNES DE COMMANDE - PRODUITS
# =========================================================

class CommandeHasProduitCreate(BaseModel):
    PRODUIT_id_produit: int = Field(..., gt=0)
    quantite: int = Field(..., ge=1)


class CommandeHasProduitUpdate(BaseModel):
    quantite: int = Field(..., ge=1)


# =========================================================
# UTILISATEURS / AUTHENTIFICATION
# =========================================================

class UtilisateurLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    mot_de_passe: str = Field(..., min_length=1)


class UtilisateurCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    mot_de_passe: str = Field(..., min_length=8)
    role: str = "client"

    @field_validator("nom", "prenom", "email", "role")
    @classmethod
    def nettoyer_champs(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("Ce champ ne peut pas être vide.")
        return valeur


class UtilisateurClientCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    date_naissance: date | None = None
    email: str = Field(..., min_length=3, max_length=255)
    telephone: str = Field(..., min_length=1, max_length=30)
    mot_de_passe: str = Field(..., min_length=8)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def verifier_paire_coordonnees(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être renseignées ensemble.")
        return self

    @field_validator("nom", "prenom", "email", "telephone")
    @classmethod
    def nettoyer_champs(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("Ce champ ne peut pas être vide.")
        return valeur


# =========================================================
# LIGNES DU PANIER
# =========================================================

class LigneCommandeCreate(BaseModel):
    id_produit: int = Field(..., gt=0)
    quantite: int = Field(..., ge=1)


class LigneProduitPanier(BaseModel):
    id_produit: int = Field(..., gt=0)
    quantite: int = Field(..., ge=1)


class LigneServicePanier(BaseModel):
    id_service: int = Field(..., gt=0)
    quantite: int = Field(..., ge=1)


class CommandeDepuisPanierCreate(BaseModel):
    lignes: list[LigneProduitPanier] = Field(default_factory=list)
    services: list[LigneServicePanier] = Field(default_factory=list)
    methode_paiement: str = Field(default="livraison", min_length=1, max_length=50)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def verifier_paire_coordonnees(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être renseignées ensemble.")
        return self

    @field_validator("methode_paiement")
    @classmethod
    def nettoyer_methode_paiement(cls, valeur: str) -> str:
        valeur = valeur.strip().lower()
        if not valeur:
            raise ValueError("Le mode de paiement est obligatoire.")
        return valeur


# =========================================================
# RÉPONSE COMMANDE
# =========================================================

class CommandeResponse(SchemaBase):
    id_commande: int
    CLIENT_id_client: int
    date_commande: date
    statut: str


# =========================================================
# MESSAGERIE DES COMMANDES
# =========================================================

class MessageCommandeCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)

    @field_validator("message")
    @classmethod
    def verifier_message(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("Le message ne peut pas être vide.")
        return valeur


class MessageCommandeResponse(SchemaBase):
    id_message: int
    COMMANDE_id_commande: int
    UTILISATEUR_id_utilisateur: int
    UTILISATEUR_destinataire_id: int | None = None
    message: str | None = None
    date_message: datetime
    lu: bool
    audio_url: str | None = None
    nom_utilisateur: str | None = None
    prenom_utilisateur: str | None = None
    role_utilisateur: str | None = None
    nom_destinataire: str | None = None
    prenom_destinataire: str | None = None
    role_destinataire: str | None = None


class MessageCommandeLuUpdate(BaseModel):
    lu: bool = True


# =========================================================
# PHOTOS D'ACCUEIL ET PUBLICITÉS
# =========================================================

class PhotoAccueilResponse(SchemaBase):
    id_photo: int
    nom_fichier: str
    ordre: int
    actif: bool
    date_ajout: datetime


class PubliciteResponse(SchemaBase):
    id_publicite: int
    nom_fichier: str
    titre: str | None = None
    ordre: int
    actif: bool
    date_ajout: datetime


# =========================================================
# SERVICES
# =========================================================

class ServiceCreate(BaseModel):
    nom_service: str = Field(..., min_length=1, max_length=255)
    prix: float = Field(..., ge=0)
    description: str | None = None
    categorie: str | None = None
    image: str | None = None
    video: str | None = None
    actif: bool = True

    @field_validator("nom_service")
    @classmethod
    def nettoyer_nom_service(cls, valeur: str) -> str:
        valeur = valeur.strip()
        if not valeur:
            raise ValueError("Le nom du service est obligatoire.")
        return valeur


class ServiceUpdate(ServiceCreate):
    pass


# =========================================================
# LIGNES DE COMMANDE - SERVICES
# =========================================================

class CommandeHasServiceCreate(BaseModel):
    SERVICE_id_service: int = Field(..., gt=0)
    quantite: int = Field(..., ge=1)


class CommandeHasServiceUpdate(BaseModel):
    quantite: int = Field(..., ge=1)
