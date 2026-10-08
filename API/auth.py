
import os
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

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# En production, la clé doit impérativement être configurée.
if not SECRET_KEY:
    if (
        os.getenv("RENDER")
        or os.getenv("ENVIRONMENT", "").lower() == "production"
    ):
        raise RuntimeError(
            "La variable JWT_SECRET_KEY doit être configurée "
            "dans les variables d'environnement."
        )

    # Clé de développement local uniquement.
    # Ne jamais utiliser cette clé en production.
    SECRET_KEY = "cle-de-developpement-local-non-securisee"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer(auto_error=False)


# =========================================================
# RÉPONSE STANDARD EN CAS D'AUTHENTIFICATION INVALIDE
# =========================================================

def erreur_authentification(
    detail="Token invalide ou expiré."
):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


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
        "exp": expiration,
    }

    return jwt.encode(
        donnees,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# =========================================================
# RÉCUPÉRER L'UTILISATEUR CONNECTÉ
# =========================================================

def utilisateur_connecte(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    # Vérifier que le client a fourni un jeton Bearer.
    if credentials is None:
        raise erreur_authentification(
            "Authentification requise."
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        id_utilisateur = payload.get("sub")

        # L'identifiant doit être une chaîne numérique valide.
        if (
            not isinstance(id_utilisateur, str)
            or not id_utilisateur.isdigit()
        ):
            raise erreur_authentification()

    except JWTError:
        raise erreur_authentification()

    # Vérifier que l'utilisateur existe toujours en base.
    utilisateur = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.id_utilisateur == int(id_utilisateur)
        )
        .first()
    )

    if utilisateur is None:
        raise erreur_authentification(
            "Utilisateur introuvable."
        )

    return utilisateur


# =========================================================
# VÉRIFIER LE RÔLE DE L'UTILISATEUR
# =========================================================

def role_autorise(*roles):
    def verification(
        utilisateur: Utilisateur = Depends(utilisateur_connecte),
    ):
        if utilisateur.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Vous n'avez pas l'autorisation "
                    "d'effectuer cette action."
                ),
            )

        return utilisateur

    return verification