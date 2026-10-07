from getpass import getpass
import bcrypt

from database import SessionLocal
from models import Utilisateur


def creer_utilisateur():

    db = SessionLocal()

    try:
        print("====================================")
        print("      CRÉATION D'UN UTILISATEUR")
        print("====================================")

        nom = input("Nom : ")
        prenom = input("Prénom : ")
        email = input("Email : ")

        mot_de_passe = getpass("Mot de passe : ")
        confirmation = getpass("Confirmer le mot de passe : ")

        if mot_de_passe != confirmation:
            print("❌ Les mots de passe ne correspondent pas.")
            return

        print("\nRôles disponibles :")
        print("1 - admin")
        print("2 - vendeur")
        print("3 - client")

        choix = input("Choisir le rôle (1/2/3) : ")

        roles = {
            "1": "admin",
            "2": "vendeur",
            "3": "client"
        }

        if choix not in roles:
            print("❌ Rôle invalide.")
            return

        role = roles[choix]

        # Vérifier si l'email existe déjà
        utilisateur_existant = db.query(Utilisateur).filter(
            Utilisateur.email == email
        ).first()

        if utilisateur_existant:
            print("❌ Cet email est déjà utilisé.")
            return

        # Hachage du mot de passe
        mot_de_passe_hash = bcrypt.hashpw(
            mot_de_passe.encode("utf-8"),
            bcrypt.gensalt()
        )

        nouvel_utilisateur = Utilisateur(
            nom=nom,
            prenom=prenom,
            email=email,
            mot_de_passe=mot_de_passe_hash.decode("utf-8"),
            role=role
        )

        db.add(nouvel_utilisateur)
        db.commit()
        db.refresh(nouvel_utilisateur)

        print("\n✅ Utilisateur créé avec succès !")
        print(f"ID     : {nouvel_utilisateur.id_utilisateur}")
        print(f"Nom    : {nouvel_utilisateur.nom}")
        print(f"Prénom : {nouvel_utilisateur.prenom}")
        print(f"Email  : {nouvel_utilisateur.email}")
        print(f"Rôle   : {nouvel_utilisateur.role}")

    except Exception as e:
        db.rollback()
        print("\n❌ Une erreur est survenue :")
        print(e)

    finally:
        db.close()


if __name__ == "__main__":
    creer_utilisateur()