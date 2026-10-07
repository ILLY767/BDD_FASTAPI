from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from database import get_db
from models import Utilisateur


# =========================================================
# CONFIGURATION JWT
# =========================================================

SECRET_KEY = "ma-cle-secrete-jwt-a-changer-plus-tard"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# SYSTÈME DE LECTURE DU TOKEN
# =========================================================

security = HTTPBearer()


# =========================================================
# CRÉER UN TOKEN JWT
# =========================================================

def creer_token(utilisateur):

    expiration = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    donnees = {
        "sub": str(utilisateur.id_utilisateur),
        "email": utilisateur.email,
        "role": utilisateur.role,
        "exp": expiration
    }

    token = jwt.encode(
        donnees,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# =========================================================
# RÉCUPÉRER L'UTILISATEUR CONNECTÉ
# =========================================================

def utilisateur_connecte(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        id_utilisateur = payload.get("sub")

        if id_utilisateur is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide."
            )

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré."
        )

    utilisateur = db.query(Utilisateur).filter(
        Utilisateur.id_utilisateur == int(id_utilisateur)
    ).first()

    if utilisateur is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable."
        )

    return utilisateur


# =========================================================
# VÉRIFIER LE RÔLE
# =========================================================

def role_autorise(*roles):

    def verification(
        utilisateur: Utilisateur = Depends(utilisateur_connecte)
    ):

        if utilisateur.role not in roles:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas l'autorisation d'effectuer cette action."
            )

        return utilisateur

    return verification