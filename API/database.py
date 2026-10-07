from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# =========================================================
# CONFIGURATION SQL SERVER
# =========================================================

serveur = r"DESKTOP-9I8V1RP\BASE_APPLI"
base = "Base de boutique"


# =========================================================
# CHAÎNE DE CONNEXION
# =========================================================

DATABASE_URL = (
    "mssql+pyodbc://@"
    f"{serveur}/"
    f"{base}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)


# =========================================================
# MOTEUR SQLALCHEMY
# =========================================================

engine = create_engine(DATABASE_URL)


# =========================================================
# FABRIQUE DE SESSIONS
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =========================================================
# FONCTION DE GESTION DES SESSIONS
# =========================================================

def get_db():

    # Création d'une session de connexion à la base de données
    db = SessionLocal()

    try:
        # Transmettre la session à FastAPI
        yield db

    finally:
        # Fermer la session après utilisation
        db.close()