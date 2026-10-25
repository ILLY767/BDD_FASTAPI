from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Float,
    ForeignKey,
    Boolean,
    Text,
    DateTime
)

from sqlalchemy.orm import declarative_base


# =========================================================
# BASE DES MODÈLES
# =========================================================

# Cette base servira de classe mère
# pour tous nos modèles SQLAlchemy.

Base = declarative_base()


# =========================================================
# MODÈLE CLIENT
# =========================================================

class Client(Base):

    __tablename__ = "CLIENT"

    id_client = Column(
        Integer,
        primary_key=True
    )

    nom = Column(
        String(20),
        nullable=False
    )

    prenom = Column(
        String(50),
        nullable=False
    )

    date_naissance = Column(
        Date,
        nullable=True
    )

    email = Column(
        String(100),
        nullable=False
    )

    telephone = Column(
        String(20),
        nullable=False
    )

    latitude = Column(
        Float,
        nullable=True
    )

    longitude = Column(
        Float,
        nullable=True
    )

    # -----------------------------------------------------
    # Lien avec le compte utilisateur
    # -----------------------------------------------------

    id_utilisateur = Column(
        Integer,
        ForeignKey("UTILISATEUR.id_utilisateur"),
        nullable=True,
        unique=True
    )


# =========================================================
# MODÈLE PRODUIT
# =========================================================

class Produit(Base):

    __tablename__ = "PRODUIT"

    id_produit = Column(
        Integer,
        primary_key=True,
        index=True
    )

    designation = Column(
        String,
        nullable=False
    )

    prix_unitaire = Column(
        Float,
        nullable=False
    )

    description = Column(
        String(500),
        nullable=True
    )

    image = Column(
        String(255),
        nullable=True
    )

    stock = Column(
        Integer,
        nullable=False,
        default=0
    )

    categorie = Column(
        String(100),
        nullable=True
    )

    actif = Column(
        Boolean,
        nullable=False,
        default=True
    )


# =========================================================
# MODÈLE COMMANDE
# =========================================================

class Commande(Base):

    __tablename__ = "COMMANDE"

    id_commande = Column(
        Integer,
        primary_key=True,
        index=True
    )

    date_commande = Column(
        Date
    )

    CLIENT_id_client = Column(
        Integer,
        ForeignKey("CLIENT.id_client")
    )

    latitude = Column(
        Float,
        nullable=True
    )

    longitude = Column(
        Float,
        nullable=True
    )

    statut = Column(
        String(60),
        nullable=False,
        default="en_attente"
    )


# =========================================================
# MODÈLE COMMANDE_HAS_PRODUIT
# =========================================================

class CommandeHasProduit(Base):

    __tablename__ = "COMMANDE_has_PRODUIT"

    # -----------------------------------------------------
    # Identifiant de la commande
    # -----------------------------------------------------

    COMMANDE_id_commande = Column(
        Integer,
        ForeignKey("COMMANDE.id_commande"),
        primary_key=True
    )

    # -----------------------------------------------------
    # Identifiant du produit
    # -----------------------------------------------------

    PRODUIT_id_produit = Column(
        Integer,
        ForeignKey("PRODUIT.id_produit"),
        primary_key=True
    )

    # -----------------------------------------------------
    # Quantité commandée
    # -----------------------------------------------------

    quantite = Column(
        Integer,
        nullable=False
    )

    # -----------------------------------------------------
    # Prix du produit au moment de la commande
    # -----------------------------------------------------

    prix_unitaire = Column(
        Float,
        nullable=False
    )


# =========================================================
# MODÈLE UTILISATEUR
# =========================================================

class Utilisateur(Base):

    __tablename__ = "UTILISATEUR"

    id_utilisateur = Column(
        Integer,
        primary_key=True,
        index=True
    )

    nom = Column(
        String(50),
        nullable=False
    )

    prenom = Column(
        String(50),
        nullable=False
    )

    email = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )

    mot_de_passe = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(20),
        nullable=False
    )

# =========================================================
# MODÈLE NOTIFICATION
# =========================================================

class Notification(Base):

    __tablename__ = "NOTIFICATION"

    id_notification = Column(
        Integer,
        primary_key=True,
        index=True
    )

    UTILISATEUR_id_utilisateur = Column(
        Integer,
        ForeignKey(
            "UTILISATEUR.id_utilisateur"
        ),
        nullable=False
    )

    titre = Column(
        String(150),
        nullable=False
    )

    message = Column(
        String(500),
        nullable=False
    )

    type_notification = Column(
        String(50),
        nullable=False
    )

    lien = Column(
        String(255),
        nullable=True
    )

    lu = Column(
        Boolean,
        nullable=False,
        default=False
    )

    date_notification = Column(
        DateTime,
        nullable=False,
        default=datetime.now
    )



# =========================================================
# MODÈLE : MESSAGE D'UNE COMMANDE
# =========================================================

# =========================================================
# MODÈLE : MESSAGE D'UNE COMMANDE
# =========================================================

class MessageCommande(Base):

    __tablename__ = "MESSAGE_COMMANDE"

    # -----------------------------------------------------
    # IDENTIFIANT DU MESSAGE
    # -----------------------------------------------------

    id_message = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # -----------------------------------------------------
    # COMMANDE CONCERNÉE
    # -----------------------------------------------------

    COMMANDE_id_commande = Column(
        Integer,
        ForeignKey("COMMANDE.id_commande"),
        nullable=False
    )

    # -----------------------------------------------------
    # EXPÉDITEUR DU MESSAGE
    # -----------------------------------------------------
    # C'est l'utilisateur qui envoie le message.
    #
    # Exemple :
    # CLIENT Jacques → VENDEUR
    #
    # Ici, UTILISATEUR_id_utilisateur = Jacques
    # -----------------------------------------------------

    UTILISATEUR_id_utilisateur = Column(
        Integer,
        ForeignKey("UTILISATEUR.id_utilisateur"),
        nullable=False
    )

    # -----------------------------------------------------
    # DESTINATAIRE DU MESSAGE
    # -----------------------------------------------------
    # C'est l'utilisateur qui doit recevoir le message.
    #
    # Exemple :
    # CLIENT Jacques → VENDEUR
    #
    # UTILISATEUR_id_utilisateur
    #       = Jacques
    #
    # UTILISATEUR_destinataire_id
    #       = vendeur
    # -----------------------------------------------------

    UTILISATEUR_destinataire_id = Column(
        Integer,
        ForeignKey("UTILISATEUR.id_utilisateur"),
        nullable=False
    )

    # -----------------------------------------------------
    # CONTENU TEXTUEL
    # -----------------------------------------------------
    # Peut être NULL lorsqu'il s'agit d'un message vocal.
    # -----------------------------------------------------

    message = Column(
        Text,
        nullable=True
    )

    # -----------------------------------------------------
    # DATE ET HEURE DU MESSAGE
    # -----------------------------------------------------

    date_message = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )

    # -----------------------------------------------------
    # MESSAGE LU OU NON LU
    # -----------------------------------------------------
    #
    # False = message non lu
    # True  = message lu
    #
    # Ce champ correspondra au destinataire.
    # -----------------------------------------------------

    lu = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # -----------------------------------------------------
    # MESSAGE VOCAL
    # -----------------------------------------------------
    #
    # Contient l'URL du fichier audio lorsqu'il existe.
    # Pour un message texte, cette valeur est NULL.
    # -----------------------------------------------------

    audio_url = Column(
        String(500),
        nullable=True
    )
    
# =========================================================
# MODÈLE : PHOTO DE LA PAGE D'ACCUEIL
# =========================================================

class PhotoAccueil(Base):

    __tablename__ = "PHOTO_ACCUEIL"

    # Identifiant de la photo
    id_photo = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Nom du fichier enregistré dans static/accueil/photos/
    nom_fichier = Column(
        String(255),
        nullable=False
    )

    # Permet de contrôler l'ordre d'affichage
    ordre = Column(
        Integer,
        nullable=False,
        default=0
    )

    # Photo active ou non
    actif = Column(
        Boolean,
        nullable=False,
        default=True
    )

    # Date d'ajout
    date_ajout = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )


# =========================================================
# MODÈLE : PUBLICITÉ VIDÉO
# =========================================================

class Publicite(Base):

    __tablename__ = "PUBLICITE"

    # Identifiant de la publicité
    id_publicite = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Nom du fichier vidéo
    nom_fichier = Column(
        String(255),
        nullable=False
    )

    # Titre facultatif de la publicité
    titre = Column(
        String(200),
        nullable=True
    )

    # Ordre d'affichage
    ordre = Column(
        Integer,
        nullable=False,
        default=0
    )

    # Publicité active ou non
    actif = Column(
        Boolean,
        nullable=False,
        default=True
    )

    # Date d'ajout
    date_ajout = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )


# =========================================================
# MODÈLE SERVICE
# =========================================================
#
# Un service est différent d'un produit :
#
# - il n'a pas de stock ;
# - il peut être activé ou désactivé ;
# - il peut avoir une image ;
# - il peut avoir une vidéo ;
# - il possède un prix ;
# - il peut être ajouté à une commande.
#
# =========================================================

class Service(Base):

    __tablename__ = "SERVICE"

    # -----------------------------------------------------
    # IDENTIFIANT DU SERVICE
    # -----------------------------------------------------

    id_service = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # -----------------------------------------------------
    # NOM DU SERVICE
    # -----------------------------------------------------

    nom_service = Column(
        String(150),
        nullable=False
    )

    # -----------------------------------------------------
    # PRIX DU SERVICE
    # -----------------------------------------------------

    prix = Column(
        Float,
        nullable=False
    )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    description = Column(
        String(500),
        nullable=True
    )

    # -----------------------------------------------------
    # CATÉGORIE
    # -----------------------------------------------------

    categorie = Column(
        String(100),
        nullable=True
    )

    # -----------------------------------------------------
    # IMAGE DU SERVICE
    # -----------------------------------------------------
    #
    # Contient uniquement le nom du fichier.
    #
    # Exemple :
    # service_installation.jpg
    #
    # Le fichier sera enregistré côté Flask dans :
    #
    # static/images/services/
    #
    # -----------------------------------------------------

    image = Column(
        String(255),
        nullable=True
    )

    # -----------------------------------------------------
    # VIDÉO DU SERVICE
    # -----------------------------------------------------
    #
    # Contient uniquement le nom du fichier.
    #
    # Exemple :
    # installation.mp4
    #
    # -----------------------------------------------------

    video = Column(
        String(255),
        nullable=True
    )

    # -----------------------------------------------------
    # SERVICE ACTIF OU NON
    # -----------------------------------------------------
    #
    # True  = service disponible
    # False = service désactivé
    #
    # Contrairement aux produits, un service n'a pas
    # de stock.
    #
    # -----------------------------------------------------

    actif = Column(
        Boolean,
        nullable=False,
        default=True
    )


# =========================================================
# MODÈLE COMMANDE_HAS_SERVICE
# =========================================================
#
# Cette table fait le lien entre une commande et un service.
#
# Une commande pourra donc contenir :
#
#   - des produits
#   - des services
#   - ou les deux.
#
# Exemple :
#
# COMMANDE #25
#     ├── Produit : Ordinateur × 1
#     ├── Produit : Souris × 2
#     └── Service : Installation × 1
#
# =========================================================

class CommandeHasService(Base):

    __tablename__ = "COMMANDE_has_SERVICE"

    # -----------------------------------------------------
    # IDENTIFIANT DE LA COMMANDE
    # -----------------------------------------------------

    COMMANDE_id_commande = Column(
        Integer,
        ForeignKey("COMMANDE.id_commande"),
        primary_key=True
    )

    # -----------------------------------------------------
    # IDENTIFIANT DU SERVICE
    # -----------------------------------------------------

    SERVICE_id_service = Column(
        Integer,
        ForeignKey("SERVICE.id_service"),
        primary_key=True
    )

    # -----------------------------------------------------
    # QUANTITÉ DU SERVICE
    # -----------------------------------------------------
    #
    # Généralement 1 pour un service.
    #
    # Mais nous autorisons plusieurs unités afin de garder
    # le même fonctionnement que les produits.
    #
    # Exemple :
    #
    # Installation × 2
    #
    # -----------------------------------------------------

    quantite = Column(
        Integer,
        nullable=False
    )

    # -----------------------------------------------------
    # PRIX DU SERVICE AU MOMENT DE LA COMMANDE
    # -----------------------------------------------------
    #
    # Très important :
    #
    # Si le service coûte aujourd'hui 15 000 F et que son
    # prix passe ensuite à 20 000 F, une ancienne commande
    # doit continuer à afficher 15 000 F.
    #
    # -----------------------------------------------------

    prix_unitaire = Column(
        Float,
        nullable=False
    )


    # =========================================================
# 💳 PAIEMENT
# =========================================================

class Paiement(Base):

    __tablename__ = "PAIEMENT"

    id_paiement = Column(
        Integer,
        primary_key=True,
        index=True
    )

    COMMANDE_id_commande = Column(
        Integer,
        ForeignKey(
            "COMMANDE.id_commande"
        ),
        nullable=False
    )

    UTILISATEUR_id_utilisateur = Column(
        Integer,
        ForeignKey(
            "UTILISATEUR.id_utilisateur"
        ),
        nullable=False
    )

    montant = Column(
        Float,
        nullable=False
    )

    methode = Column(
        String(50),
        nullable=False
    )

    statut = Column(
        String(50),
        nullable=False,
        default="en_attente"
    )

    reference = Column(
        String(150),
        nullable=True
    )

    date_paiement = Column(
        DateTime,
        nullable=False,
        default=datetime.now
    )