
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# =========================================================
# CONFIGURATION DE LA BASE DE DONNÉES
# =========================================================

# En ligne, Render fournit DATABASE_URL.
# En local, si cette variable n'existe pas, on utilise SQL Server.

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================================================
# CONNEXION LOCALE OU EN LIGNE
# =========================================================

if DATABASE_URL:

    # Adaptation de l'URL PostgreSQL pour SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1
        )

    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1
        )

else:

    # Configuration SQL Server utilisée en local
    serveur = r"DESKTOP-9I8V1RP\BASE_APPLI"
    base = "Base de boutique"

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

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# =========================================================
# FABRIQUE DE SESSIONS
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =========================================================
# GESTION DES SESSIONS
# =========================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

