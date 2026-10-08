
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# =========================================================
# CONFIGURATION DE LA BASE DE DONNÉES
# =========================================================
#
# LOCAL :
#   SQL Server
#
# RENDER :
#   PostgreSQL via DATABASE_URL
#
# La base existante n'est ni recréée ni migrée ici.
# =========================================================


DATABASE_URL = os.getenv("DATABASE_URL")


# =========================================================
# 1. CONFIGURATION POSTGRESQL (RENDER)
# =========================================================

if DATABASE_URL:

    # Compatibilité avec les anciennes URL PostgreSQL.
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

    # Vérification du type de base configuré.
    if not DATABASE_URL.startswith(
        "postgresql+psycopg2://"
    ):
        raise ValueError(
            "DATABASE_URL doit contenir une URL PostgreSQL "
            "valide pour l'environnement Render."
        )


# =========================================================
# 2. CONFIGURATION SQL SERVER (LOCAL)
# =========================================================

else:

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
# 3. CRÉATION DU MOTEUR SQLALCHEMY
# =========================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# =========================================================
# 4. FABRIQUE DE SESSIONS
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# =========================================================
# 5. DÉPENDANCE FASTAPI
# =========================================================

def get_db():
    """
    Fournit une session SQLAlchemy à une route FastAPI,
    puis la ferme systématiquement.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

