# ============================================================
# MIGRATION SQL SERVER LOCAL → POSTGRESQL RENDER
# APPLICATION BOUTIQUE
# ============================================================

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    Utilisateur,
    Client,
    Produit,
    Service,
    Commande,
    CommandeHasProduit,
    CommandeHasService,
    Notification,
    MessageCommande,
    PhotoAccueil,
    Publicite,
    Paiement,
)


# ============================================================
# 1. CONNEXION À LA BASE SQL SERVER LOCALE
# ============================================================

serveur = r"DESKTOP-9I8V1RP\BASE_APPLI"
base = "Base de boutique"

LOCAL_DATABASE_URL = (
    "mssql+pyodbc://@"
    f"{serveur}/"
    f"{base}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)


# ============================================================
# 2. CONNEXION À POSTGRESQL RENDER
# ============================================================
#
# IMPORTANT :
# La variable RENDER_DATABASE_URL doit être définie
# dans PowerShell avant de lancer le script.
#
# Exemple :
#
# $env:RENDER_DATABASE_URL="...URL RENDER..."
#
# Ne mets jamais cette URL directement dans ce fichier.
# ============================================================

RENDER_DATABASE_URL = os.getenv("RENDER_DATABASE_URL")


if not RENDER_DATABASE_URL:
    raise RuntimeError(
        "\n"
        "ERREUR : la variable RENDER_DATABASE_URL n'est pas définie.\n\n"
        "Dans PowerShell, définis d'abord :\n"
        '$env:RENDER_DATABASE_URL="URL_POSTGRESQL_RENDER"\n'
    )


# ============================================================
# 3. NORMALISATION DE L'URL POSTGRESQL
# ============================================================

if RENDER_DATABASE_URL.startswith("postgres://"):

    RENDER_DATABASE_URL = RENDER_DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg2://",
        1
    )

elif RENDER_DATABASE_URL.startswith("postgresql://"):

    RENDER_DATABASE_URL = RENDER_DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )


# ============================================================
# 4. CRÉATION DES ENGINE
# ============================================================

print("\n" + "=" * 70)
print("MIGRATION DE LA BASE DE DONNÉES")
print("=" * 70)


print("\n[1/8] Connexion à SQL Server local...")

source_engine = create_engine(
    LOCAL_DATABASE_URL
)

print("      SQL Server : OK")


print("\n[2/8] Connexion à PostgreSQL Render...")

destination_engine = create_engine(
    RENDER_DATABASE_URL
)

print("      PostgreSQL Render : OK")


# ============================================================
# 5. TEST DES CONNEXIONS
# ============================================================

print("\n[3/8] Vérification des connexions...")

with source_engine.connect() as connection:

    connection.execute(
        text("SELECT 1")
    )

print("      SQL Server : connexion fonctionnelle")


with destination_engine.connect() as connection:

    connection.execute(
        text("SELECT 1")
    )

print("      PostgreSQL Render : connexion fonctionnelle")


# ============================================================
# 6. CRÉATION DES TABLES SUR POSTGRESQL
# ============================================================

print("\n[4/8] Création des tables PostgreSQL...")

Base.metadata.create_all(
    bind=destination_engine
)

print("      Tables créées/vérifiées avec succès.")


# ============================================================
# 7. CRÉATION DES SESSIONS
# ============================================================

SourceSession = sessionmaker(
    bind=source_engine
)

DestinationSession = sessionmaker(
    bind=destination_engine
)

source_db = SourceSession()
destination_db = DestinationSession()


# ============================================================
# 8. VÉRIFICATION : LA BASE RENDER DOIT ÊTRE VIDE
# ============================================================

print("\n[5/8] Vérification de la base Render...")


modeles = [
    ("UTILISATEUR", Utilisateur),
    ("CLIENT", Client),
    ("PRODUIT", Produit),
    ("SERVICE", Service),
    ("COMMANDE", Commande),
    ("COMMANDE_has_PRODUIT", CommandeHasProduit),
    ("COMMANDE_has_SERVICE", CommandeHasService),
    ("NOTIFICATION", Notification),
    ("MESSAGE_COMMANDE", MessageCommande),
    ("PHOTO_ACCUEIL", PhotoAccueil),
    ("PUBLICITE", Publicite),
    ("PAIEMENT", Paiement),
]


base_destination_vide = True


for nom, modele in modeles:

    nombre = destination_db.query(modele).count()

    print(
        f"      {nom:<30} : {nombre} ligne(s)"
    )

    if nombre > 0:
        base_destination_vide = False


if not base_destination_vide:

    raise RuntimeError(
        "\n"
        "ERREUR : la base PostgreSQL Render contient déjà des données.\n"
        "La migration est donc interrompue afin d'éviter les doublons."
    )


print("\n      Base Render vide : OK")


# ============================================================
# FONCTION DE COPIE GÉNÉRIQUE
# ============================================================

def copier_lignes(
    modele_source,
    modele_destination=None,
    nom_table=None
):

    if modele_destination is None:
        modele_destination = modele_source

    if nom_table is None:
        nom_table = modele_source.__tablename__

    lignes = source_db.query(modele_source).all()

    print(
        f"\n      {nom_table:<30} : "
        f"{len(lignes)} ligne(s)"
    )

    for ligne_source in lignes:

        donnees = {}

        for colonne in modele_source.__table__.columns:

            nom_colonne = colonne.name

            donnees[nom_colonne] = getattr(
                ligne_source,
                nom_colonne
            )

        ligne_destination = modele_destination(
            **donnees
        )

        destination_db.add(
            ligne_destination
        )

    destination_db.flush()

    return len(lignes)


# ============================================================
# 9. MIGRATION
# ============================================================

try:

    print("\n" + "=" * 70)
    print("DÉBUT DE LA MIGRATION")
    print("=" * 70)


    # --------------------------------------------------------
    # 1. UTILISATEUR
    # --------------------------------------------------------

    copier_lignes(
        Utilisateur,
        nom_table="UTILISATEUR"
    )


    # --------------------------------------------------------
    # 2. CLIENT
    # --------------------------------------------------------

    copier_lignes(
        Client,
        nom_table="CLIENT"
    )


    # --------------------------------------------------------
    # 3. PRODUIT
    # --------------------------------------------------------

    copier_lignes(
        Produit,
        nom_table="PRODUIT"
    )


    # --------------------------------------------------------
    # 4. SERVICE
    # --------------------------------------------------------

    copier_lignes(
        Service,
        nom_table="SERVICE"
    )


    # --------------------------------------------------------
    # 5. COMMANDE
    # --------------------------------------------------------

    copier_lignes(
        Commande,
        nom_table="COMMANDE"
    )


    # --------------------------------------------------------
    # 6. COMMANDE_has_PRODUIT
    # --------------------------------------------------------

    copier_lignes(
        CommandeHasProduit,
        nom_table="COMMANDE_has_PRODUIT"
    )


    # --------------------------------------------------------
    # 7. COMMANDE_has_SERVICE
    # --------------------------------------------------------

    copier_lignes(
        CommandeHasService,
        nom_table="COMMANDE_has_SERVICE"
    )


    # --------------------------------------------------------
    # 8. NOTIFICATION
    # --------------------------------------------------------

    copier_lignes(
        Notification,
        nom_table="NOTIFICATION"
    )


    # ========================================================
    # 9. MESSAGE_COMMANDE
    # ========================================================
    #
    # PARTICULARITÉ :
    #
    # Certains anciens messages ont :
    #
    # UTILISATEUR_destinataire_id = NULL
    #
    # PostgreSQL refuse cette valeur car la colonne est NOT NULL.
    #
    # Pour ces anciens messages uniquement, nous déterminons
    # automatiquement le destinataire.
    # ========================================================

    print(
        "\n      MESSAGE_COMMANDE"
    )


    messages = source_db.query(
        MessageCommande
    ).order_by(
        MessageCommande.id_message
    ).all()


    print(
        f"      Nombre de messages : {len(messages)}"
    )


    # --------------------------------------------------------
    # Recherche d'un membre du personnel
    #
    # Priorité :
    # 1. admin
    # 2. vendeur
    # --------------------------------------------------------

    staff_user = source_db.query(
        Utilisateur
    ).filter(
        Utilisateur.role == "admin"
    ).order_by(
        Utilisateur.id_utilisateur
    ).first()


    if staff_user is None:

        staff_user = source_db.query(
            Utilisateur
        ).filter(
            Utilisateur.role == "vendeur"
        ).order_by(
            Utilisateur.id_utilisateur
        ).first()


    if staff_user is None:

        raise RuntimeError(
            "Impossible de déterminer un utilisateur admin/vendeur "
            "pour les anciens messages sans destinataire."
        )


    print(
        "      Utilisateur du personnel utilisé comme "
        f"fallback : {staff_user.id_utilisateur} "
        f"({staff_user.nom} {staff_user.prenom})"
    )


    for message_source in messages:

        # ----------------------------------------------------
        # Si le destinataire existe déjà :
        # on le conserve exactement.
        # ----------------------------------------------------

        destinataire_id = (
            message_source.UTILISATEUR_destinataire_id
        )


        if destinataire_id is not None:

            print(
                f"      Message #{message_source.id_message} : "
                f"destinataire conservé = {destinataire_id}"
            )


        # ----------------------------------------------------
        # Si le destinataire est NULL :
        # on doit le déterminer.
        # ----------------------------------------------------

        else:

            print(
                f"\n      Message #{message_source.id_message} : "
                "destinataire absent → recherche automatique..."
            )


            # ------------------------------------------------
            # Récupération de la commande concernée
            # ------------------------------------------------

            commande = source_db.query(
                Commande
            ).filter(
                Commande.id_commande
                == message_source.COMMANDE_id_commande
            ).first()


            if commande is None:

                raise RuntimeError(
                    "\n"
                    f"Impossible de déterminer le destinataire "
                    f"du message #{message_source.id_message}.\n"
                    f"La commande "
                    f"{message_source.COMMANDE_id_commande} "
                    "n'existe pas."
                )


            # ------------------------------------------------
            # Récupération du client de la commande
            # ------------------------------------------------

            client = source_db.query(
                Client
            ).filter(
                Client.id_client
                == commande.CLIENT_id_client
            ).first()


            if client is None:

                raise RuntimeError(
                    "\n"
                    f"Impossible de déterminer le destinataire "
                    f"du message #{message_source.id_message}.\n"
                    f"Le client "
                    f"{commande.CLIENT_id_client} "
                    "n'existe pas."
                )


            client_user_id = client.id_utilisateur


            # ------------------------------------------------
            # Vérification que le client possède bien
            # un utilisateur associé.
            # ------------------------------------------------

            if client_user_id is None:

                raise RuntimeError(
                    "\n"
                    f"Le client {client.id_client} "
                    f"n'a aucun utilisateur associé.\n"
                    f"Impossible de déterminer le destinataire "
                    f"du message #{message_source.id_message}."
                )


            expediteur_id = (
                message_source.UTILISATEUR_id_utilisateur
            )


            # ------------------------------------------------
            # CAS 1 :
            # l'expéditeur est le client.
            #
            # → destinataire = membre du personnel
            # ------------------------------------------------

            if expediteur_id == client_user_id:

                destinataire_id = staff_user.id_utilisateur

                print(
                    f"          Expéditeur = client "
                    f"{client_user_id}"
                )

                print(
                    f"          → Destinataire automatique = "
                    f"{destinataire_id}"
                )


            # ------------------------------------------------
            # CAS 2 :
            # l'expéditeur est admin/vendeur.
            #
            # → destinataire = client
            # ------------------------------------------------

            else:

                expediteur = source_db.query(
                    Utilisateur
                ).filter(
                    Utilisateur.id_utilisateur
                    == expediteur_id
                ).first()


                if expediteur is None:

                    raise RuntimeError(
                        "\n"
                        f"L'utilisateur expéditeur "
                        f"{expediteur_id} "
                        f"du message #{message_source.id_message} "
                        "n'existe pas."
                    )


                if expediteur.role in (
                    "admin",
                    "vendeur"
                ):

                    destinataire_id = client_user_id

                    print(
                        f"          Expéditeur = "
                        f"{expediteur.role} "
                        f"{expediteur_id}"
                    )

                    print(
                        f"          → Destinataire automatique = "
                        f"client {destinataire_id}"
                    )


                # ------------------------------------------------
                # Cas exceptionnel :
                # l'expéditeur n'est ni le client ni le personnel.
                # ------------------------------------------------

                else:

                    raise RuntimeError(
                        "\n"
                        f"Impossible de déterminer le destinataire "
                        f"du message #{message_source.id_message}.\n"
                        f"Expéditeur : {expediteur_id}\n"
                        f"Rôle : {expediteur.role}\n"
                        f"Client de la commande : {client_user_id}"
                    )


        # ----------------------------------------------------
        # Création du message destination
        # ----------------------------------------------------

        donnees_message = {}

        for colonne in MessageCommande.__table__.columns:

            nom_colonne = colonne.name

            donnees_message[nom_colonne] = getattr(
                message_source,
                nom_colonne
            )


        # ----------------------------------------------------
        # On impose le destinataire déterminé.
        # ----------------------------------------------------

        donnees_message[
            "UTILISATEUR_destinataire_id"
        ] = destinataire_id


        message_destination = MessageCommande(
            **donnees_message
        )


        destination_db.add(
            message_destination
        )


    destination_db.flush()


    # --------------------------------------------------------
    # 10. PHOTO_ACCUEIL
    # --------------------------------------------------------

    copier_lignes(
        PhotoAccueil,
        nom_table="PHOTO_ACCUEIL"
    )


    # --------------------------------------------------------
    # 11. PUBLICITE
    # --------------------------------------------------------

    copier_lignes(
        Publicite,
        nom_table="PUBLICITE"
    )


    # --------------------------------------------------------
    # 12. PAIEMENT
    # --------------------------------------------------------

    copier_lignes(
        Paiement,
        nom_table="PAIEMENT"
    )


    # ========================================================
    # 10. VALIDATION DES DONNÉES AVANT COMMIT
    # ========================================================

    print("\n" + "=" * 70)
    print("VÉRIFICATION AVANT VALIDATION")
    print("=" * 70)


    for nom, modele in modeles:

        nombre_source = source_db.query(
            modele
        ).count()


        nombre_destination = destination_db.query(
            modele
        ).count()


        print(
            f"\n      {nom}"
        )

        print(
            f"          SQL Server : {nombre_source}"
        )

        print(
            f"          PostgreSQL : {nombre_destination}"
        )


        if nombre_source != nombre_destination:

            raise RuntimeError(
                "\n"
                f"ERREUR DE VÉRIFICATION pour {nom} :\n"
                f"SQL Server = {nombre_source}\n"
                f"PostgreSQL = {nombre_destination}"
            )


    # ========================================================
    # 11. COMMIT FINAL
    # ========================================================

    print("\n" + "=" * 70)
    print("VALIDATION DE LA MIGRATION")
    print("=" * 70)


    destination_db.commit()


    print(
        "\n      COMMIT effectué avec succès."
    )


    # ========================================================
    # 12. RÉINITIALISATION DES SÉQUENCES
    # ========================================================

    print(
        "\n[7/8] Réinitialisation des séquences PostgreSQL..."
    )


    # --------------------------------------------------------
    # Colonnes avec identifiants auto-incrémentés
    # --------------------------------------------------------

    sequences = [
        ("UTILISATEUR", "id_utilisateur"),
        ("CLIENT", "id_client"),
        ("PRODUIT", "id_produit"),
        ("SERVICE", "id_service"),
        ("COMMANDE", "id_commande"),
        ("NOTIFICATION", "id_notification"),
        ("MESSAGE_COMMANDE", "id_message"),
        ("PHOTO_ACCUEIL", "id_photo"),
        ("PUBLICITE", "id_publicite"),
        ("PAIEMENT", "id_paiement"),
    ]


    with destination_engine.begin() as connection:

        for table, colonne in sequences:

            try:

                resultat = connection.execute(
                    text(
                        """
                        SELECT pg_get_serial_sequence(
                            :table_name,
                            :column_name
                        )
                        """
                    ),
                    {
                        "table_name": table,
                        "column_name": colonne,
                    }
                ).scalar()


                if resultat:

                    connection.execute(
                        text(
                            f"""
                            SELECT setval(
                                :sequence_name,
                                COALESCE(
                                    (
                                        SELECT MAX("{colonne}")
                                        FROM "{table}"
                                    ),
                                    1
                                ),
                                (
                                    SELECT COUNT(*) > 0
                                    FROM "{table}"
                                )
                            )
                            """
                        ),
                        {
                            "sequence_name": resultat
                        }
                    )


                    print(
                        f"      Séquence {table}.{colonne} : OK"
                    )


                else:

                    print(
                        f"      Séquence {table}.{colonne} : "
                        "non trouvée"
                    )


            except Exception as erreur_sequence:

                print(
                    f"      Attention : séquence "
                    f"{table}.{colonne} non réinitialisée."
                )

                print(
                    f"      Détail : {erreur_sequence}"
                )


    # ========================================================
    # 13. VÉRIFICATION FINALE
    # ========================================================

    print(
        "\n[8/8] Vérification finale..."
    )


    for nom, modele in modeles:

        nombre = destination_db.query(
            modele
        ).count()

        print(
            f"      {nom:<30} : {nombre} ligne(s)"
        )


    print("\n" + "=" * 70)
    print("MIGRATION TERMINÉE AVEC SUCCÈS")
    print("=" * 70)

    print(
        "\nToutes les données ont été transférées de "
        "SQL Server vers PostgreSQL Render."
    )

    print(
        "\nLes anciens messages sans destinataire ont été "
        "traités automatiquement."
    )

    print(
        "\nLa base SQL Server locale n'a pas été modifiée."
    )


except Exception as erreur:

    # ========================================================
    # ROLLBACK EN CAS D'ERREUR
    # ========================================================

    print("\n" + "=" * 70)
    print("ERREUR PENDANT LA MIGRATION")
    print("=" * 70)

    print(
        f"\n{type(erreur).__name__} : {erreur}"
    )


    try:

        destination_db.rollback()

        print(
            "\nRollback effectué."
        )

        print(
            "Aucune donnée partiellement migrée "
            "n'a été conservée."
        )

    except Exception as erreur_rollback:

        print(
            "\nERREUR pendant le rollback :"
        )

        print(
            erreur_rollback
        )


    raise


finally:

    # ========================================================
    # FERMETURE PROPRE DES CONNEXIONS
    # ========================================================

    source_db.close()
    destination_db.close()

    source_engine.dispose()
    destination_engine.dispose()

    print(
        "\nConnexions fermées."
    )