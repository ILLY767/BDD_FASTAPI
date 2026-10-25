import os
import re
import uuid
import time
import math
from datetime import date

import requests
import threading


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

# Cloudinary est facultatif en local (repli sur le dossier static/).
try:
    import cloudinary
    import cloudinary.uploader
except ImportError:  # pragma: no cover
    cloudinary = None


app = Flask(__name__)


# =========================================================
# ENVIRONNEMENT : LOCAL OU PRODUCTION (RENDER)
# =========================================================
#
# Render définit automatiquement la variable RENDER.
# =========================================================

EN_PRODUCTION = bool(
    os.getenv("RENDER")
    or os.getenv("ENVIRONMENT", "").lower() == "production"
)

# Render place l'application derrière un proxy HTTPS.
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1
)


# =========================================================
# CONFIGURATION DE LA SESSION
# =========================================================

app.secret_key = (
    os.getenv("FLASK_SECRET_KEY")
    or os.getenv("SECRET_KEY")
)

if not app.secret_key:

    if EN_PRODUCTION:
        raise RuntimeError(
            "La variable FLASK_SECRET_KEY doit être configurée "
            "dans les variables d'environnement de Render."
        )

    # Clé de développement local uniquement.
    app.secret_key = "cle-flask-developpement-local-non-securisee"

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=EN_PRODUCTION,
    MAX_CONTENT_LENGTH=(
        int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
    ),
)


# =========================================================
# CONFIGURATION DE L'API FASTAPI
# =========================================================
#
# LOCAL  : http://127.0.0.1:8000 (valeur par défaut)
# RENDER : définir API_URL = https://votre-api.onrender.com
#
# API_PUBLIC_URL : URL appelée directement par le navigateur
# (par défaut identique à API_URL).
#
# API_TIMEOUT : délai maximal d'une requête vers l'API.
# Il doit être assez long pour absorber le démarrage à froid
# d'un service Render gratuit.
# =========================================================

# Adresse de l'API FastAPI
API_URL = (
    os.getenv("API_URL")
    or (
        "https://bdd-fastapi.onrender.com"
        if os.getenv("RENDER")
        else "http://127.0.0.1:8000"
    )
).rstrip("/")

# Adresse publique de l'API, notamment pour les médias
API_PUBLIC_URL = (
    os.getenv("API_PUBLIC_URL") or API_URL
).rstrip("/")

# Délai d'attente par défaut, en secondes
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "90"))


# =========================================================
# CONFIGURATION DE CLOUDINARY
# =========================================================
#
# Option 1 : CLOUDINARY_URL=cloudinary://clé:secret@nom_du_cloud
# Option 2 : CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY,
#            CLOUDINARY_API_SECRET
# =========================================================

def configurer_cloudinary():

    if cloudinary is None:
        return False

    nom = os.getenv("CLOUDINARY_CLOUD_NAME")
    cle = os.getenv("CLOUDINARY_API_KEY")
    secret = os.getenv("CLOUDINARY_API_SECRET")

    if nom and cle and secret:

        cloudinary.config(
            cloud_name=nom,
            api_key=cle,
            api_secret=secret,
            secure=True
        )

        return True

    # CLOUDINARY_URL est lue automatiquement par la bibliothèque.
    return bool(cloudinary.config().cloud_name)


CLOUDINARY_ACTIF = configurer_cloudinary()

app.logger.warning(
    "Diagnostic Cloudinary : actif=%s, cloud_name=%s, api_key=%s, api_secret=%s",
    CLOUDINARY_ACTIF,
    bool(os.getenv("CLOUDINARY_CLOUD_NAME")),
    bool(os.getenv("CLOUDINARY_API_KEY")),
    bool(os.getenv("CLOUDINARY_API_SECRET")),
)


# =========================================================
# DOSSIERS DES MÉDIAS
# =========================================================
#
# Clé       -> sous-dossier de static/ (repli local)
#              et dossier Cloudinary : boutique/<clé>
# =========================================================

DOSSIERS_STATIC = {
    "produits": "images",
    "services_images": "services/images",
    "services_videos": "services/videos",
    "accueil_photos": "accueil/photos",
    "accueil_videos": "accueil/videos",
}

SERVICES_DIR = os.path.join(app.root_path, "static", "services")
SERVICES_IMAGES_DIR = os.path.join(SERVICES_DIR, "images")
SERVICES_VIDEOS_DIR = os.path.join(SERVICES_DIR, "videos")

# Dossiers locaux créés uniquement hors production.
if not EN_PRODUCTION:

    try:
        for dossier in DOSSIERS_STATIC.values():
            os.makedirs(
                os.path.join(
                    app.root_path,
                    "static",
                    *dossier.split("/")
                ),
                exist_ok=True
            )
    except OSError:
        pass


# =========================================================
# EXTENSIONS AUTORISÉES
# =========================================================

EXTENSIONS_IMAGE_SERVICE = {"jpg", "jpeg", "png", "webp"}
EXTENSIONS_VIDEO_SERVICE = {"mp4", "webm", "mov"}
EXTENSIONS_PHOTO_ACCUEIL = {"jpg", "jpeg", "png", "webp", "gif"}
EXTENSIONS_VIDEO_ACCUEIL = {"mp4", "webm", "ogg"}


def extension_autorisee(
    nom_fichier,
    extensions_autorisees
):
    """
    Vérifie si l'extension du fichier est autorisée.
    """

    if not nom_fichier:
        return False

    extension = (
        nom_fichier.rsplit(".", 1)[1].lower()
        if "." in nom_fichier
        else ""
    )

    return extension in extensions_autorisees


def coordonnees_du_formulaire(formulaire):
    """Valide une paire de coordonnées facultatives d'un formulaire."""
    latitude = (formulaire.get("latitude") or "").strip()
    longitude = (formulaire.get("longitude") or "").strip()

    if not latitude and not longitude:
        return {"latitude": None, "longitude": None}, None

    if not latitude or not longitude:
        return None, "Renseignez la latitude et la longitude ensemble."

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return None, "La latitude et la longitude doivent être numériques."

    if (
        not math.isfinite(latitude)
        or not -90 <= latitude <= 90
        or not math.isfinite(longitude)
        or not -180 <= longitude <= 180
    ):
        return None, "Les coordonnées GPS sont hors limites."

    return {"latitude": latitude, "longitude": longitude}, None


# =========================================================
# TÉLÉVERSEMENT / SUPPRESSION DES MÉDIAS
# =========================================================
#
# Valeur enregistrée en base :
#   - Cloudinary configuré : l'URL complète (https://...)
#   - Sinon (local)        : le nom du fichier dans static/
# =========================================================

class ErreurMedia(Exception):
    pass


def televerser_media(fichier, dossier, type_ressource="image"):

    extension = fichier.filename.rsplit(".", 1)[-1].lower()

    # -----------------------------------------------------
    # CLOUDINARY
    # -----------------------------------------------------

    if CLOUDINARY_ACTIF:

        options = {
            "folder": f"boutique/{dossier}",
            "public_id": uuid.uuid4().hex,
            "resource_type": type_ressource,
            "overwrite": False,
        }

        try:

            fichier.stream.seek(0)

            if type_ressource == "video":
                resultat = cloudinary.uploader.upload_large(
                    fichier.stream,
                    chunk_size=6_000_000,
                    **options
                )
            else:
                resultat = cloudinary.uploader.upload(
                    fichier.stream,
                    **options
                )

        except Exception as erreur:
            app.logger.exception("Échec du téléversement Cloudinary")
            raise ErreurMedia(
                f"Échec du téléversement vers Cloudinary : {erreur}"
            )

        return resultat["secure_url"]

    # -----------------------------------------------------
    # PRODUCTION SANS CLOUDINARY : le disque de Render est
    # éphémère, on refuse plutôt que de perdre le fichier.
    # -----------------------------------------------------

    if EN_PRODUCTION:
        raise ErreurMedia(
            "Cloudinary n'est pas configuré sur le serveur "
            "(variable CLOUDINARY_URL manquante)."
        )

    # -----------------------------------------------------
    # LOCAL : enregistrement dans static/
    # -----------------------------------------------------

    nom_fichier = f"{uuid.uuid4().hex}.{extension}"

    dossier_local = os.path.join(
        app.root_path,
        "static",
        *DOSSIERS_STATIC[dossier].split("/")
    )

    os.makedirs(dossier_local, exist_ok=True)

    fichier.save(os.path.join(dossier_local, nom_fichier))

    return nom_fichier


def supprimer_media(valeur, dossier, local=False):
    """
    Suppression « au mieux » : n'interrompt jamais la requête.

    - URL Cloudinary : supprime l'asset.
    - Nom de fichier local : supprimé seulement si local=True.
    """

    if not valeur:
        return

    valeur = str(valeur)

    # -----------------------------------------------------
    # ASSET CLOUDINARY
    # -----------------------------------------------------

    if valeur.startswith(("http://", "https://")):

        if not CLOUDINARY_ACTIF:
            return

        correspondance = re.search(
            r"/(image|video|raw)/upload/(?:v\d+/)?(.+)$",
            valeur
        )

        if not correspondance:
            return

        type_ressource = correspondance.group(1)
        identifiant = correspondance.group(2)

        if type_ressource != "raw":
            identifiant = os.path.splitext(identifiant)[0]

        try:
            cloudinary.uploader.destroy(
                identifiant,
                resource_type=type_ressource,
                invalidate=True
            )
        except Exception:
            app.logger.exception("Suppression Cloudinary impossible")

        return

    # -----------------------------------------------------
    # FICHIER LOCAL
    # -----------------------------------------------------

    if not local or EN_PRODUCTION:
        return

    chemin = os.path.join(
        app.root_path,
        "static",
        *DOSSIERS_STATIC[dossier].split("/"),
        secure_filename(os.path.basename(valeur))
    )

    try:
        if os.path.exists(chemin):
            os.remove(chemin)
    except OSError:
        pass


def media_url(valeur, dossier):
    """
    Retourne l'URL affichable d'un média, qu'il s'agisse
    d'une URL Cloudinary ou d'un ancien nom de fichier local.
    """

    if not valeur:
        return None

    valeur = str(valeur).strip()

    if valeur.startswith(("http://", "https://", "//", "data:", "/")):
        return valeur

    return url_for(
        "static",
        filename=f"{DOSSIERS_STATIC[dossier]}/{valeur}"
    )


# Utilisable dans les templates : {{ media_url(x, "produits") }}
app.jinja_env.globals["media_url"] = media_url


def enrichir_produits(liste):

    if isinstance(liste, list):
        for produit in liste:
            if isinstance(produit, dict):
                produit["image_url"] = media_url(
                    produit.get("image"),
                    "produits"
                )

    return liste


def enrichir_services(liste):

    if isinstance(liste, list):
        for service in liste:
            if isinstance(service, dict):
                service["image_url"] = media_url(
                    service.get("image"),
                    "services_images"
                )
                service["video_url"] = media_url(
                    service.get("video"),
                    "services_videos"
                )

    return liste


def enrichir_photos_accueil(liste):

    if isinstance(liste, list):
        for photo in liste:
            if isinstance(photo, dict):
                photo["url_fichier"] = media_url(
                    photo.get("nom_fichier"),
                    "accueil_photos"
                )

    return liste


def enrichir_publicites(liste):

    if isinstance(liste, list):
        for publicite in liste:
            if isinstance(publicite, dict):
                publicite["url_fichier"] = media_url(
                    publicite.get("nom_fichier"),
                    "accueil_videos"
                )

    return liste


# =========================================================
# VÉRIFICATION DU RÔLE DE L'UTILISATEUR
# =========================================================

def role_autorise(*roles):

    if "id_utilisateur" not in session:
        return False

    role = session.get("role")

    return role in roles


def compter_articles_panier():
    """
    Nombre total d'articles : produits + services.
    """

    total = 0

    for cle in ("panier", "panier_services"):

        for quantite in session.get(cle, {}).values():

            try:
                total += int(quantite)
            except (TypeError, ValueError):
                continue

    return total


# =========================================================
# APPELS VERS FASTAPI
# =========================================================

class SessionExpiree(Exception):
    pass


def url_api(url):
    """
    Construit l'URL complète.
    /services  ->  <API_URL>/services
    """

    if url.startswith(("http://", "https://")):
        return url

    return f"{API_URL}/{url.lstrip('/')}"


def api_headers():

    token = session.get("access_token")

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def appel_api(methode, url, authentifie=True, **kwargs):
    """
    Effectue une requête vers FastAPI.

    - Respecte le délai d'attente demandé par la route.
    - Utilise API_TIMEOUT si aucun délai n'est précisé.
    - Ajoute le JWT pour les requêtes authentifiées.
    - Gère l'expiration du jeton de session.
    """

    # Respecter le timeout donné par l'appelant.
    # Utiliser API_TIMEOUT uniquement s'il est absent.
    kwargs.setdefault("timeout", API_TIMEOUT)

    en_tetes = dict(kwargs.pop("headers", None) or {})

    if authentifie:
        en_tetes = {**api_headers(), **en_tetes}

    reponse = requests.request(
        methode,
        url_api(url),
        headers=en_tetes,
        **kwargs
    )

    # Jeton JWT expiré ou invalide.
    if (
        authentifie
        and reponse.status_code == 401
        and session.get("access_token")
        and reponse.headers.get("WWW-Authenticate")
    ):
        session.clear()
        raise SessionExpiree()

    return reponse


def api_get(url, **kwargs):
    return appel_api("GET", url, **kwargs)


def api_post(url, donnees=None, **kwargs):
    if donnees is not None and "json" not in kwargs:
        kwargs["json"] = donnees

    return appel_api("POST", url, **kwargs)


def api_put(url, donnees=None, **kwargs):
    if donnees is not None and "json" not in kwargs:
        kwargs["json"] = donnees

    return appel_api("PUT", url, **kwargs)


def api_delete(url, **kwargs):
    return appel_api("DELETE", url, **kwargs)


def api_public_get(url, **kwargs):
    return appel_api(
        "GET",
        url,
        authentifie=False,
        **kwargs
    )


def api_public_post(url, **kwargs):
    return appel_api(
        "POST",
        url,
        authentifie=False,
        **kwargs
    )


def valeur_actuelle(chemin, cle_id, identifiant, champ):
    """
    Relit un champ dans l'API (utile si le formulaire
    ne l'a pas renvoyé).
    """

    try:
        reponse = api_get(chemin)

        if reponse.status_code == 200:
            for element in reponse.json():
                if element.get(cle_id) == identifiant:
                    return element.get(champ) or ""

    except requests.RequestException:
        pass

    return ""


# =========================================================
# RÉVEIL AUTOMATIQUE DE L'API EN ARRIÈRE-PLAN
# =========================================================

def reveiller_api_en_arriere_plan():
    """
    Envoie une requête à FastAPI sans bloquer l'affichage
    de la boutique Flask.
    """
    def effectuer_requete():
        try:
            reponse = requests.get(
                API_URL,
                timeout=(10, 90)
            )
            app.logger.info(
                "Réveil API : HTTP %s",
                reponse.status_code
            )
        except requests.RequestException as erreur:
            app.logger.warning(
                "Réveil de l'API en arrière-plan impossible : %s",
                erreur
            )

    thread = threading.Thread(
        target=effectuer_requete,
        daemon=True
    )
    thread.start()



# =========================================================
# GESTION DES ERREURS GLOBALES
# =========================================================

def _reponse_attendue_json():

    return (
        request.is_json
        or request.method in ("PUT", "DELETE")
        or request.accept_mimetypes.best == "application/json"
    )


@app.errorhandler(SessionExpiree)
def gerer_session_expiree(erreur):

    if _reponse_attendue_json():
        return jsonify({
            "detail": "Session expirée. Veuillez vous reconnecter."
        }), 401

    flash(
        "Votre session a expiré. Veuillez vous reconnecter.",
        "error"
    )

    return redirect(url_for("login"))


@app.errorhandler(requests.RequestException)
def gerer_api_indisponible(erreur):

    app.logger.error("Erreur de communication avec l'API : %s", erreur)

    message = (
        "Le serveur est momentanément indisponible "
        "(il peut être en cours de démarrage). "
        "Réessayez dans quelques instants."
    )

    if _reponse_attendue_json():
        return jsonify({"detail": message}), 503

    return message, 503


@app.errorhandler(413)
def fichier_trop_volumineux(erreur):

    message = "Fichier trop volumineux."

    if _reponse_attendue_json():
        return jsonify({"detail": message}), 413

    return message, 413


@app.context_processor
def injecter_configuration():

    # URL de l'API utilisable par le JavaScript des templates.
    return {
        "API_URL": API_PUBLIC_URL,
        "API_PUBLIC_URL": API_PUBLIC_URL
    }


# =========================================================
# CONTRÔLE DE SANTÉ (RENDER)
# =========================================================

@app.route("/sante")
def sante():
    return jsonify({"statut": "ok"}), 200



# =========================================================
# PAGE D'ACCUEIL
# =========================================================



# =========================================================
# PAGE D'ACCUEIL
# =========================================================

@app.route("/")
def accueil():
    photos = []
    videos = []
    produits = []

    # Déclenche le réveil de l'API en arrière-plan.
    reveiller_api_en_arriere_plan()

    # Réessaie de récupérer le contenu pendant le démarrage.
    for tentative in range(5):
        try:
            reponse = api_public_get(
                "/accueil/contenu",
                timeout=15
            )

            if reponse.status_code == 200:
                contenu = reponse.json()

                photos = contenu.get("photos", [])
                videos = contenu.get("publicites", [])
                produits = contenu.get("produits", [])

                break

            app.logger.warning(
                "Accueil API : HTTP %s (tentative %s/5)",
                reponse.status_code,
                tentative + 1
            )

        except requests.RequestException as erreur:
            app.logger.warning(
                "API indisponible pour l'accueil "
                "(tentative %s/5) : %s",
                tentative + 1,
                erreur
            )

        # Attend avant la prochaine tentative.
        if tentative < 4:
            time.sleep(3)

    enrichir_photos_accueil(photos)
    enrichir_publicites(videos)
    enrichir_produits(produits)

    return render_template(
        "accueil.html",
        photos=photos,
        videos=videos,
        produits=produits
    )



# =========================================================
# CONNEXION
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    # Ne jamais afficher request.form : il contient le mot de passe.

    email = (request.form.get("email") or "").strip()
    mot_de_passe = request.form.get("mot_de_passe")

    if not email or not mot_de_passe:
        return render_template(
            "login.html",
            erreur="Veuillez renseigner l'email et le mot de passe."
        )

    try:

        reponse = appel_api(
            "POST",
            "/login",
            authentifie=False,
            json={
                "email": email,
                "mot_de_passe": mot_de_passe
            }
        )

    except requests.RequestException:

        return render_template(
            "login.html",
            erreur=(
                "Le serveur est momentanément indisponible "
                "(il peut être en cours de démarrage). "
                "Réessayez dans quelques instants."
            )
        )

    if reponse.status_code != 200:

        return render_template(
            "login.html",
            erreur="Email ou mot de passe incorrect"
        )

    utilisateur = reponse.json()

    session["id_utilisateur"] = utilisateur["id_utilisateur"]
    session["nom"] = utilisateur["nom"]
    session["prenom"] = utilisateur["prenom"]
    session["email"] = utilisateur["email"]
    session["role"] = utilisateur["role"]
    session["access_token"] = utilisateur["access_token"]

    return redirect(url_for("tableau_de_bord"))


# =========================================================
# TABLEAU DE BORD PRINCIPAL
# =========================================================

@app.route("/tableau-de-bord")
def tableau_de_bord():

    # =====================================================
    # VÉRIFICATION DE LA CONNEXION
    # =====================================================

    if "access_token" not in session:
        return redirect(
            url_for("login")
        )


    # =====================================================
    # RÉCUPÉRATION DU RÔLE
    # =====================================================

    role = session.get("role")


    # =====================================================
    # CLIENT
    # =====================================================

    if role == "client":

        return render_template(
            "tableau_de_bord.html",
            statistiques={}
        )


    # =====================================================
    # ADMINISTRATEUR / VENDEUR
    # =====================================================

    if role in ["admin", "vendeur"]:

        try:

            reponse = api_get(
                f"{API_URL}/dashboard/statistiques",
                timeout=5
            )

        except Exception as erreur:

            return (
                "Impossible de communiquer avec "
                f"le serveur : {erreur}",
                500
            )


        # =================================================
        # VÉRIFICATION DE LA RÉPONSE FASTAPI
        # =================================================

        if reponse.status_code != 200:

            try:

                detail = reponse.json().get(
                    "detail",
                    "Impossible de récupérer "
                    "les statistiques."
                )

            except Exception:

                detail = (
                    "Impossible de récupérer "
                    "les statistiques."
                )


            return (
                f"Erreur : {detail}",
                reponse.status_code
            )


        # =================================================
        # RÉCUPÉRATION DES STATISTIQUES
        # =================================================

        statistiques = reponse.json()


        # =================================================
        # AFFICHAGE DU TABLEAU DE BORD
        # =================================================

        return render_template(
            "tableau_de_bord.html",
            statistiques=statistiques
        )


    # =====================================================
    # RÔLE INCONNU
    # =====================================================

    return (
        "Accès refusé.",
        403
    )

# =========================================================
# GESTION DES UTILISATEURS
# =========================================================

@app.route("/utilisateurs")
def utilisateurs():

    if not role_autorise("admin"):
        return (
            "Accès refusé : cette page est réservée à l'administrateur.",
            403
        )

    reponse = api_get(
        f"{API_URL}/utilisateurs"
    )

    if reponse.status_code != 200:
        return (
            "Erreur lors de la récupération des utilisateurs.",
            500
        )

    liste_utilisateurs = reponse.json()

    return render_template(
        "utilisateurs.html",
        utilisateurs=liste_utilisateurs
    )


# =========================================================
# DÉCONNEXION
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("accueil"))


# =========================================================
# CRÉATION D'UN COMPTE
# =========================================================

@app.route("/creer-compte", methods=["GET", "POST"])
def creer_compte():

    # =========================================================
    # AFFICHAGE DU FORMULAIRE
    # =========================================================

    if request.method == "GET":
        return render_template("creer_compte.html")

    # =========================================================
    # RÉCUPÉRATION DES INFORMATIONS DU FORMULAIRE
    # =========================================================

    nom = request.form["nom"]
    prenom = request.form["prenom"]
    date_naissance = request.form.get("date_naissance")
    email = request.form["email"]
    telephone = request.form["telephone"]
    latitude = (request.form.get("latitude") or "").strip()
    longitude = (request.form.get("longitude") or "").strip()
    mot_de_passe = request.form["mot_de_passe"]
    confirmation = request.form["confirmation"]

    # =========================================================
    # VÉRIFICATION DU MOT DE PASSE
    # =========================================================

    if mot_de_passe != confirmation:

        return render_template(
            "creer_compte.html",
            erreur="Les mots de passe ne correspondent pas."
        )

    # =========================================================
    # ENVOI DES INFORMATIONS À FASTAPI
    # =========================================================

    payload = {
        "nom": nom,
        "prenom": prenom,
        "date_naissance": date_naissance if date_naissance else None,
        "email": email,
        "telephone": telephone,
        "mot_de_passe": mot_de_passe
    }

    if latitude:
        try:
            payload["latitude"] = float(latitude)
        except ValueError:
            pass

    if longitude:
        try:
            payload["longitude"] = float(longitude)
        except ValueError:
            pass

    reponse = api_public_post(
        f"{API_URL}/utilisateurs",
        json=payload
    )

    # =========================================================
    # GESTION DES ERREURS
    # =========================================================

    if reponse.status_code not in [200, 201]:

        try:
            erreur_api = reponse.json().get(
                "detail",
                "Impossible de créer le compte."
            )
        except Exception:
            erreur_api = "Impossible de créer le compte."

        return render_template(
            "creer_compte.html",
            erreur=erreur_api
        )

    # =========================================================
    # COMPTE CRÉÉ AVEC SUCCÈS
    # =========================================================

    return redirect(url_for("login"))



# =========================================================
# 👤 MON COMPTE
# =========================================================

@app.route("/mon-compte", methods=["GET"])
def mon_compte():
    """
    Affiche l'espace personnel de l'utilisateur connecté.
    """

    # -----------------------------------------------------
    # Vérification de connexion
    # -----------------------------------------------------

    if "access_token" not in session:
        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Récupération des informations depuis FastAPI
    # -----------------------------------------------------

    reponse = api_get("/mon-compte")

    # -----------------------------------------------------
    # Gestion d'une éventuelle erreur API
    # -----------------------------------------------------

    if reponse.status_code != 200:

        try:
            erreur = reponse.json().get(
                "detail",
                "Impossible de récupérer votre profil."
            )
        except Exception:
            erreur = (
                "Impossible de récupérer votre profil."
            )

        return render_template(
            "mon_compte.html",
            erreur=erreur
        )

    # -----------------------------------------------------
    # Données du compte
    # -----------------------------------------------------

    compte = reponse.json()

    return render_template(
        "mon_compte.html",
        compte=compte,
        erreur=request.args.get("erreur"),
        succes=request.args.get("succes")
    )


# =========================================================
# ✏️ MODIFICATION DU PROFIL
# =========================================================

@app.route(
    "/mon-compte/modifier",
    methods=["POST"]
)
def modifier_mon_compte():

    # -----------------------------------------------------
    # Vérification de connexion
    # -----------------------------------------------------

    if "access_token" not in session:
        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Récupération des données du formulaire
    # -----------------------------------------------------

    nom = request.form.get(
        "nom",
        ""
    ).strip()

    prenom = request.form.get(
        "prenom",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    telephone = request.form.get(
        "telephone",
        ""
    ).strip()

    date_naissance = request.form.get(
        "date_naissance"
    )

    # -----------------------------------------------------
    # Vérifications côté Flask
    # -----------------------------------------------------

    if not nom or not prenom or not email:

        return redirect(
            url_for(
                "mon_compte",
                erreur=(
                    "Le nom, le prénom et "
                    "l'email sont obligatoires."
                )
            )
        )

    coordonnees, erreur_coordonnees = coordonnees_du_formulaire(
        request.form
    )
    if erreur_coordonnees:
        return redirect(
            url_for("mon_compte", erreur=erreur_coordonnees)
        )

    # -----------------------------------------------------
    # Préparation des données pour FastAPI
    # -----------------------------------------------------

    donnees = {
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "telephone": telephone or None,
        "date_naissance": (
            date_naissance
            if date_naissance
            else None
        )
    }

    donnees.update(coordonnees)

    # -----------------------------------------------------
    # Appel de l'API
    # -----------------------------------------------------

    reponse = api_put(
        "/mon-compte",
        donnees
    )

    # -----------------------------------------------------
    # Modification réussie
    # -----------------------------------------------------

    if reponse.status_code == 200:

        resultat = reponse.json()

        # -------------------------------------------------
        # Mise à jour immédiate de la session Flask
        # -------------------------------------------------

        session["nom"] = resultat.get(
            "nom",
            nom
        )

        session["prenom"] = resultat.get(
            "prenom",
            prenom
        )

        session["email"] = resultat.get(
            "email",
            email
        )

        return redirect(
            url_for(
                "mon_compte",
                succes=(
                    "Votre profil a été "
                    "mis à jour avec succès."
                )
            )
        )

    # -----------------------------------------------------
    # Erreur API
    # -----------------------------------------------------

    try:
        erreur = reponse.json().get(
            "detail",
            "Impossible de modifier votre profil."
        )
    except Exception:
        erreur = (
            "Impossible de modifier votre profil."
        )

    return redirect(
        url_for(
            "mon_compte",
            erreur=erreur
        )
    )


# =========================================================
# 🔐 MODIFICATION DU MOT DE PASSE
# =========================================================

@app.route(
    "/mon-compte/mot-de-passe",
    methods=["POST"]
)
def modifier_mot_de_passe():

    # -----------------------------------------------------
    # Vérification de connexion
    # -----------------------------------------------------

    if "access_token" not in session:
        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Récupération du formulaire
    # -----------------------------------------------------

    ancien_mot_de_passe = request.form.get(
        "ancien_mot_de_passe",
        ""
    )

    nouveau_mot_de_passe = request.form.get(
        "nouveau_mot_de_passe",
        ""
    )

    confirmation_mot_de_passe = request.form.get(
        "confirmation_mot_de_passe",
        ""
    )

    # -----------------------------------------------------
    # Vérification côté Flask
    # -----------------------------------------------------

    if (
        not ancien_mot_de_passe
        or not nouveau_mot_de_passe
        or not confirmation_mot_de_passe
    ):

        return redirect(
            url_for(
                "mon_compte",
                erreur=(
                    "Veuillez remplir tous les "
                    "champs du mot de passe."
                )
            )
        )

    # -----------------------------------------------------
    # Préparation des données
    # -----------------------------------------------------

    donnees = {
        "ancien_mot_de_passe":
            ancien_mot_de_passe,

        "nouveau_mot_de_passe":
            nouveau_mot_de_passe,

        "confirmation_mot_de_passe":
            confirmation_mot_de_passe
    }

    # -----------------------------------------------------
    # Appel FastAPI
    # -----------------------------------------------------

    reponse = api_put(
        "/mon-compte/mot-de-passe",
        donnees
    )

    # -----------------------------------------------------
    # Succès
    # -----------------------------------------------------

    if reponse.status_code == 200:

        return redirect(
            url_for(
                "mon_compte",
                succes=(
                    "Votre mot de passe a été "
                    "modifié avec succès."
                )
            )
        )

    # -----------------------------------------------------
    # Erreur
    # -----------------------------------------------------

    try:
        erreur = reponse.json().get(
            "detail",
            "Impossible de modifier le mot de passe."
        )
    except Exception:
        erreur = (
            "Impossible de modifier "
            "le mot de passe."
        )

    return redirect(
        url_for(
            "mon_compte",
            erreur=erreur
        )
    )


# =========================================================
# PAGE : CLIENTS
# =========================================================

@app.route("/clients", methods=["GET", "POST"])
def clients():

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "d'accéder à cette page.",
            403
        )

    # -----------------------------------------------------
    # AJOUTER UN CLIENT
    # -----------------------------------------------------

    if request.method == "POST":

        nom = request.form["nom"]
        prenom = request.form["prenom"]
        date_naissance = request.form["date_naissance"]
        email = request.form["email"]
        telephone = request.form["telephone"]
        coordonnees, erreur_coordonnees = coordonnees_du_formulaire(
            request.form
        )
        if erreur_coordonnees:
            return erreur_coordonnees, 400

        payload = {
            "nom": nom,
            "prenom": prenom,
            "date_naissance": date_naissance or None,
            "email": email,
            "telephone": telephone,
            **coordonnees,
        }

        reponse = api_post(
            f"{API_URL}/clients",
            json=payload
        )

        if reponse.status_code not in [200, 201]:
            return (
                f"Erreur lors de l'ajout du client : "
                f"{reponse.text}",
                reponse.status_code
            )

        return redirect(url_for("clients"))

    # -----------------------------------------------------
    # RÉCUPÉRER LES CLIENTS
    # -----------------------------------------------------

    reponse = api_get(
        f"{API_URL}/clients"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la récupération des clients : "
            f"{reponse.text}",
            reponse.status_code
        )

    liste_clients = reponse.json()
    recherche = request.args.get("recherche", "")
    latitude_recherche = (request.args.get("latitude") or "").strip()
    longitude_recherche = (request.args.get("longitude") or "").strip()
    rayon_km = request.args.get("rayon_km", "5")

    if recherche:
        recherche = recherche.lower()
        liste_clients = [
            client
            for client in liste_clients
            if recherche in str(client["id_client"])
            or recherche in (client.get("nom") or "").lower()
            or recherche in (client.get("prenom") or "").lower()
            or recherche in (client.get("email") or "").lower()
            or recherche in (client.get("telephone") or "").lower()
        ]

    return render_template(
        "clients.html",
        clients=liste_clients,
        recherche=recherche,
        latitude_recherche=latitude_recherche,
        longitude_recherche=longitude_recherche,
        rayon_km=rayon_km
    )


@app.route("/clients/proches", methods=["GET"])
def clients_proches():
    """Affiche les clients proches avec leurs indicateurs commerciaux."""
    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "d'accéder à cette page.",
            403
        )

    latitude = (request.args.get("latitude") or "").strip()
    longitude = (request.args.get("longitude") or "").strip()
    rayon_saisi = (request.args.get("rayon_km") or "5").strip()
    recherche = (request.args.get("recherche") or "").strip()
    erreur_geo = None
    clients_proches = []
    rayon_km = rayon_saisi

    if not latitude or not longitude:
        erreur_geo = "Renseignez les deux coordonnées ou utilisez le bouton GPS."
    else:
        try:
            latitude_valeur = float(latitude)
            longitude_valeur = float(longitude)
            rayon_valeur = float(rayon_saisi)
        except ValueError:
            erreur_geo = "Les coordonnées et le rayon doivent être numériques."
        else:
            if (
                not math.isfinite(latitude_valeur)
                or not -90 <= latitude_valeur <= 90
                or not math.isfinite(longitude_valeur)
                or not -180 <= longitude_valeur <= 180
            ):
                erreur_geo = "Les coordonnées GPS sont hors limites."
            elif (
                not math.isfinite(rayon_valeur)
                or rayon_valeur <= 0
                or rayon_valeur > 20038
            ):
                erreur_geo = "Le rayon doit être supérieur à 0 et inférieur ou égal à 20 038 km."
            else:
                rayon_km = rayon_valeur
                try:
                    reponse = api_get(
                        "/clients/proches",
                        params={
                            "latitude": latitude_valeur,
                            "longitude": longitude_valeur,
                            "rayon_km": rayon_valeur,
                        }
                    )
                except requests.RequestException as erreur:
                    app.logger.exception(
                        "API indisponible pendant la recherche de clients proches."
                    )
                    erreur_geo = "Impossible de contacter le serveur. Réessayez."
                else:
                    if reponse.status_code != 200:
                        try:
                            erreur_geo = reponse.json().get(
                                "detail",
                                "La recherche géographique a échoué."
                            )
                        except ValueError:
                            erreur_geo = "La recherche géographique a échoué."
                    else:
                        clients_proches = reponse.json()

    if recherche:
        recherche_minuscule = recherche.lower()
        clients_proches = [
            client
            for client in clients_proches
            if recherche_minuscule in str(client["id_client"])
            or recherche_minuscule in (client.get("nom") or "").lower()
            or recherche_minuscule in (client.get("prenom") or "").lower()
            or recherche_minuscule in (client.get("email") or "").lower()
            or recherche_minuscule in (client.get("telephone") or "").lower()
        ]

    recherche_geo_effectuee = bool(latitude and longitude and not erreur_geo)

    return render_template(
        "clients.html",
        clients=clients_proches,
        recherche=recherche,
        latitude_recherche=latitude,
        longitude_recherche=longitude,
        rayon_km=rayon_km,
        erreur_geo=erreur_geo,
        recherche_geo_effectuee=recherche_geo_effectuee,
    )


# =========================================================
# MODIFIER UN CLIENT
# =========================================================

@app.route(
    "/clients/modifier/<int:id_client>",
    methods=["POST"]
)
def modifier_client(id_client):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de modifier ce client.",
            403
        )

    nom = request.form["nom"]
    prenom = request.form["prenom"]
    date_naissance = request.form["date_naissance"]
    email = request.form["email"]
    telephone = request.form["telephone"]
    coordonnees, erreur_coordonnees = coordonnees_du_formulaire(
        request.form
    )
    if erreur_coordonnees:
        return erreur_coordonnees, 400

    payload = {
        "nom": nom,
        "prenom": prenom,
        "date_naissance": date_naissance or None,
        "email": email,
        "telephone": telephone
    }
    payload.update(coordonnees)

    reponse = api_put(
        f"{API_URL}/clients/{id_client}",
        json=payload
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la modification du client : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(url_for("clients"))


# =========================================================
# SUPPRIMER UN CLIENT
# =========================================================

@app.route(
    "/clients/supprimer/<int:id_client>",
    methods=["POST"]
)
def supprimer_client(id_client):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de supprimer ce client.",
            403
        )

    reponse = api_delete(
        f"{API_URL}/clients/{id_client}"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la suppression du client : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(url_for("clients"))


# =========================================================
# PAGE : PRODUITS
# =========================================================

@app.route("/produits", methods=["GET", "POST"])
def produits():

    if not role_autorise("admin", "vendeur", "client"):
        return (
            "Accès refusé : vous devez être connecté "
            "pour accéder à cette page.",
            403
        )

    # -----------------------------------------------------
    # AJOUTER UN PRODUIT
    # -----------------------------------------------------

    if request.method == "POST":

        if not role_autorise("admin", "vendeur"):
            return (
                "Accès refusé : vous n'avez pas l'autorisation "
                "d'ajouter un produit.",
                403
            )

        designation = request.form["designation"]
        prix_unitaire = request.form["prix_unitaire"]
        description = request.form.get("description", "")
        stock = request.form.get("stock", 0)
        categorie = request.form.get("categorie", "")

        actif = request.form.get("actif") == "1"

        # -------------------------------------------------
        # GESTION DE L'IMAGE
        # -------------------------------------------------

        try:
            float(prix_unitaire)
            int(stock)
        except (TypeError, ValueError):
            return (
                "Le prix ou le stock est invalide.",
                400
            )

        fichier_image = request.files.get("image")

        nom_image = None

        if fichier_image and fichier_image.filename:

            if not extension_autorisee(
                fichier_image.filename,
                EXTENSIONS_IMAGE_SERVICE
            ):
                return (
                    "Format d'image non autorisé. "
                    "Formats acceptés : JPG, JPEG, PNG et WEBP.",
                    400
                )

            try:
                nom_image = televerser_media(
                    fichier_image,
                    "produits",
                    "image"
                )

            except ErreurMedia as erreur:
                return (str(erreur), 500)

        # -------------------------------------------------
        # ENVOYER LE PRODUIT À FASTAPI
        # -------------------------------------------------

        reponse = api_post(
            f"{API_URL}/produits",
            json={
                "designation": designation,
                "prix_unitaire": float(prix_unitaire),
                "description": description,
                "image": nom_image,
                "stock": int(stock),
                "categorie": categorie,
                "actif": actif
            }
        )

        if reponse.status_code not in [200, 201]:
            supprimer_media(nom_image, "produits", local=True)
            return (
                f"Erreur lors de l'ajout du produit : "
                f"{reponse.text}",
                reponse.status_code
            )

        return redirect(url_for("produits"))

    # -----------------------------------------------------
    # RÉCUPÉRER TOUS LES PRODUITS
    # -----------------------------------------------------

    reponse = api_get(
        f"{API_URL}/produits"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la récupération des produits : "
            f"{reponse.text}",
            reponse.status_code
        )

    liste_produits = enrichir_produits(reponse.json())

    # =========================================================
    # RÉCUPÉRATION DES CATÉGORIES DES PRODUITS
    # =========================================================

    categories_produits = sorted(
        {
            str(produit.get("categorie")).strip()
            for produit in liste_produits
            if produit.get("categorie")
            and str(produit.get("categorie")).strip()
        },
        key=lambda categorie: categorie.lower()
    )


    # -----------------------------------------------------
    # RECHERCHE
    # -----------------------------------------------------

    recherche = request.args.get("recherche", "")

    if recherche:

        recherche = recherche.lower()

        liste_produits = [
            produit
            for produit in liste_produits
            if recherche in produit["designation"].lower()
            or recherche in str(produit["id_produit"])
        ]



    
    # =========================================================
    # CALCUL DU PANIER GLOBAL
    # PRODUITS + SERVICES
    # =========================================================

    # ---------------------------------------------------------
    # PANIER PRODUITS
    # ---------------------------------------------------------

    panier_produits = session.get(
        "panier",
        {}
    )

    nombre_articles_produits = 0

    for quantite in panier_produits.values():

        try:

            nombre_articles_produits += int(
                quantite
            )

        except (TypeError, ValueError):

            continue


    # ---------------------------------------------------------
    # PANIER SERVICES
    # ---------------------------------------------------------

    panier_services = session.get(
        "panier_services",
        {}
    )

    nombre_articles_services = 0

    for quantite in panier_services.values():

        try:

            nombre_articles_services += int(
                quantite
            )

        except (TypeError, ValueError):

            continue


    # ---------------------------------------------------------
    # TOTAL DU PANIER
    # ---------------------------------------------------------

    nombre_articles_panier = (
        nombre_articles_produits
        + nombre_articles_services
    )


    return render_template(
        "produits.html",
        produits=liste_produits,
        recherche=recherche,
        role=session.get("role"),
        nombre_articles_panier=nombre_articles_panier,
        categories_produits=categories_produits
    )


# =========================================================
# MODIFIER UN PRODUIT
# =========================================================

@app.route(
    "/produits/modifier/<int:id_produit>",
    methods=["POST"]
)
def modifier_produit(id_produit):

    # -----------------------------------------------------
    # VÉRIFICATION DU RÔLE
    # -----------------------------------------------------

    if not role_autorise("admin", "vendeur"):

        return (
            "Accès refusé : vous n'avez pas "
            "l'autorisation de modifier un produit.",
            403
        )


    # -----------------------------------------------------
    # RÉCUPÉRATION DES INFORMATIONS
    # -----------------------------------------------------

    designation = request.form.get(
        "designation",
        ""
    ).strip()

    prix_unitaire = request.form.get(
        "prix_unitaire",
        ""
    )

    description = request.form.get(
        "description",
        ""
    ).strip()

    stock = request.form.get(
        "stock",
        "0"
    )

    categorie = request.form.get(
        "categorie",
        ""
    ).strip()

    actif = (
        request.form.get("actif") == "1"
    )


    # -----------------------------------------------------
    # VÉRIFICATIONS
    # -----------------------------------------------------

    if not designation:

        return (
            "La désignation du produit est obligatoire.",
            400
        )

    try:

        prix_unitaire = float(
            prix_unitaire
        )

    except (ValueError, TypeError):

        return (
            "Le prix unitaire est invalide.",
            400
        )


    try:

        stock = int(stock)

    except (ValueError, TypeError):

        return (
            "Le stock est invalide.",
            400
        )


    if prix_unitaire < 0:

        return (
            "Le prix ne peut pas être négatif.",
            400
        )


    if stock < 0:

        return (
            "Le stock ne peut pas être négatif.",
            400
        )


    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

    fichier_image = request.files.get(
        "image"
    )


    # Par défaut, aucune nouvelle image
    image = None


    # -----------------------------------------------------
    # SI UNE NOUVELLE IMAGE A ÉTÉ SÉLECTIONNÉE
    # -----------------------------------------------------

    if fichier_image and fichier_image.filename:

        if not extension_autorisee(
            fichier_image.filename,
            EXTENSIONS_IMAGE_SERVICE
        ):

            return (
                "Format d'image non autorisé. "
                "Formats acceptés : JPG, JPEG, PNG et WEBP.",
                400
            )

        try:

            image = televerser_media(
                fichier_image,
                "produits",
                "image"
            )

        except ErreurMedia as erreur:

            return (str(erreur), 500)


    # -----------------------------------------------------
    # SI AUCUNE NOUVELLE IMAGE
    # -----------------------------------------------------

    else:

        # On récupère le nom de l'image actuelle
        # transmis par le navigateur.

        image = request.form.get(
            "image_actuelle",
            ""
        )

        # Si le formulaire n'a pas renvoyé l'image actuelle,
        # on la relit dans l'API pour ne pas l'effacer.
        if not image:

            image = valeur_actuelle(
                "/produits",
                "id_produit",
                id_produit,
                "image"
            )


    # -----------------------------------------------------
    # ENVOI À FASTAPI
    # -----------------------------------------------------

    donnees = {

        "designation":
            designation,

        "prix_unitaire":
            prix_unitaire,

        "description":
            description,

        "image":
            image,

        "stock":
            stock,

        "categorie":
            categorie,

        "actif":
            actif
    }


    reponse = api_put(
        f"{API_URL}/produits/{id_produit}",
        json=donnees
    )


    # -----------------------------------------------------
    # ERREUR FASTAPI
    # -----------------------------------------------------

    if reponse.status_code != 200:

        # Si on avait enregistré une nouvelle image
        # mais que la modification SQL échoue,
        # on supprime cette nouvelle image.

        if (
            fichier_image
            and fichier_image.filename
            and image
        ):

            supprimer_media(
                image,
                "produits",
                local=True
            )


        return (
            "Erreur lors de la modification "
            f"du produit : {reponse.text}",
            reponse.status_code
        )


    # -----------------------------------------------------
    # SUCCÈS
    # -----------------------------------------------------

    # Une nouvelle image remplace l'ancienne : on supprime
    # l'ancien asset Cloudinary (jamais un fichier local,
    # qui peut être partagé par plusieurs produits).

    ancienne_image = request.form.get("image_actuelle", "")

    if (
        fichier_image
        and fichier_image.filename
        and ancienne_image
        and ancienne_image != image
    ):

        supprimer_media(ancienne_image, "produits")

    return redirect(
        url_for("produits")
    )

# =========================================================
# SUPPRIMER UN PRODUIT
# =========================================================

@app.route(
    "/produits/supprimer/<int:id_produit>",
    methods=["POST"]
)
def supprimer_produit(id_produit):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de supprimer un produit.",
            403
        )

    reponse = api_delete(
        f"{API_URL}/produits/{id_produit}"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la suppression du produit : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(url_for("produits"))


# =========================================================
# PANIER CLIENT
# =========================================================

# =========================================================
# =========================================================
# AFFICHER LE PANIER
# =========================================================
# =========================================================

@app.route(
    "/panier"
)
def panier():

    # =====================================================
    # 1. VÉRIFIER QUE L'UTILISATEUR EST UN CLIENT
    # =====================================================

    if not role_autorise("client"):

        return (
            "Accès refusé : cette page est réservée "
            "aux clients.",
            403
        )


    # =====================================================
    # 2. RÉCUPÉRER LE PANIER DES PRODUITS
    # =====================================================

    panier_produits = session.get(
        "panier",
        {}
    )


    # =====================================================
    # 3. RÉCUPÉRER LE PANIER DES SERVICES
    # =====================================================

    panier_services = session.get(
        "panier_services",
        {}
    )


    # =====================================================
    # =====================================================
    # 4. RÉCUPÉRER LES PRODUITS DEPUIS FASTAPI
    # =====================================================
    # =====================================================

    produits = []

    try:

        reponse_produits = api_get(
            f"{API_URL}/produits",
            timeout=5
        )

    except Exception as erreur:

        return (
            "Impossible de communiquer avec "
            f"le serveur : {erreur}",
            500
        )


    if reponse_produits.status_code != 200:

        try:

            detail = reponse_produits.json().get(
                "detail",
                "Impossible de récupérer les produits."
            )

        except Exception:

            detail = (
                "Impossible de récupérer les produits."
            )

        return (
            f"Erreur : {detail}",
            reponse_produits.status_code
        )


    produits = enrichir_produits(reponse_produits.json())


    # =====================================================
    # =====================================================
    # 5. RÉCUPÉRER LES SERVICES DEPUIS FASTAPI
    # =====================================================
    # =====================================================

    services = []

    try:

        reponse_services = api_get(
            f"{API_URL}/services",
            timeout=5
        )

    except Exception as erreur:

        return (
            "Impossible de communiquer avec "
            f"le serveur : {erreur}",
            500
        )


    if reponse_services.status_code != 200:

        try:

            detail = reponse_services.json().get(
                "detail",
                "Impossible de récupérer les services."
            )

        except Exception:

            detail = (
                "Impossible de récupérer les services."
            )

        return (
            f"Erreur : {detail}",
            reponse_services.status_code
        )


    services = enrichir_services(reponse_services.json())


    # =====================================================
    # =====================================================
    # 6. CONSTRUIRE LES ARTICLES PRODUITS DU PANIER
    # =====================================================
    # =====================================================

    articles_produits = []


    for id_produit, quantite in panier_produits.items():

        # -------------------------------------------------
        # Convertir les valeurs en entiers
        # -------------------------------------------------

        id_produit = int(id_produit)

        quantite = int(quantite)


        # -------------------------------------------------
        # Retrouver le produit
        # -------------------------------------------------

        produit = next(

            (
                p
                for p in produits
                if int(p["id_produit"])
                == id_produit
            ),

            None

        )


        # -------------------------------------------------
        # Si le produit n'existe plus,
        # on l'ignore dans l'affichage
        # -------------------------------------------------

        if produit is None:

            continue


        # -------------------------------------------------
        # Si le produit n'est plus actif,
        # on l'ignore également
        # -------------------------------------------------

        if not produit.get("actif", False):

            continue


        # -------------------------------------------------
        # Vérifier le stock actuel
        # -------------------------------------------------

        stock = int(
            produit.get(
                "stock",
                0
            )
        )


        # -------------------------------------------------
        # Éviter que la quantité du panier dépasse
        # le stock disponible
        # -------------------------------------------------

        if stock <= 0:

            continue


        if quantite > stock:

            quantite = stock

            panier_produits[
                str(id_produit)
            ] = stock


        # -------------------------------------------------
        # Calcul du sous-total
        # -------------------------------------------------

        prix_unitaire = float(
            produit.get(
                "prix_unitaire",
                0
            )
        )


        sous_total = (
            prix_unitaire
            * quantite
        )


        # -------------------------------------------------
        # Préparer l'article
        # -------------------------------------------------

        articles_produits.append({

            "produit":
                produit,

            "quantite":
                quantite,

            "sous_total":
                sous_total

        })


    # =====================================================
    # =====================================================
    # 7. CONSTRUIRE LES ARTICLES SERVICES DU PANIER
    # =====================================================
    # =====================================================

    articles_services = []


    for id_service, quantite in panier_services.items():

        # -------------------------------------------------
        # Convertir les valeurs en entiers
        # -------------------------------------------------

        id_service = int(id_service)

        quantite = int(quantite)


        # -------------------------------------------------
        # Retrouver le service
        # -------------------------------------------------

        service = next(

            (
                s
                for s in services
                if int(s["id_service"])
                == id_service
            ),

            None

        )


        # -------------------------------------------------
        # Service introuvable
        # -------------------------------------------------

        if service is None:

            continue


        # -------------------------------------------------
        # Service désactivé
        # -------------------------------------------------

        if not service.get("actif", False):

            continue


        # -------------------------------------------------
        # Prix du service
        # -------------------------------------------------

        prix_unitaire = float(
            service.get(
                "prix",
                0
            )
        )


        # -------------------------------------------------
        # Calcul du sous-total
        # -------------------------------------------------

        sous_total = (
            prix_unitaire
            * quantite
        )


        # -------------------------------------------------
        # Préparer l'article
        # -------------------------------------------------

        articles_services.append({

            "service":
                service,

            "quantite":
                quantite,

            "sous_total":
                sous_total

        })


    # =====================================================
    # =====================================================
    # 8. CALCULER LE TOTAL DES PRODUITS
    # =====================================================
    # =====================================================

    total_produits = sum(

        article["sous_total"]

        for article in articles_produits

    )


    # =====================================================
    # =====================================================
    # 9. CALCULER LE TOTAL DES SERVICES
    # =====================================================
    # =====================================================

    total_services = sum(

        article["sous_total"]

        for article in articles_services

    )


    # =====================================================
    # =====================================================
    # 10. TOTAL GÉNÉRAL DU PANIER
    # =====================================================
    # =====================================================

    total = (

        total_produits
        + total_services

    )


    # =====================================================
    # =====================================================
    # 11. NOMBRE TOTAL D'ARTICLES
    # =====================================================
    # =====================================================
    # Attention :
    # ici on compte les quantités et non simplement
    # le nombre de lignes.
    # =====================================================

    nombre_articles_produits = sum(

        article["quantite"]

        for article in articles_produits

    )


    nombre_articles_services = sum(

        article["quantite"]

        for article in articles_services

    )


    nombre_articles_panier = (

        nombre_articles_produits
        + nombre_articles_services

    )


    # =====================================================
    # 12. SAUVEGARDER LES QUANTITÉS CORRIGÉES
    # =====================================================

    session["panier"] = panier_produits

    session.modified = True


    # =====================================================
    # =====================================================
    # 13. AFFICHER LE PANIER
    # =====================================================
    # =====================================================

    return render_template(

        "panier.html",

        # -----------------------------------------------
        # Produits
        # -----------------------------------------------

        articles_produits=
            articles_produits,


        # -----------------------------------------------
        # Services
        # -----------------------------------------------

        articles_services=
            articles_services,


        # -----------------------------------------------
        # Totaux
        # -----------------------------------------------

        total_produits=
            total_produits,

        total_services=
            total_services,

        total=
            total,


        # -----------------------------------------------
        # Compteur global
        # -----------------------------------------------

        nombre_articles_panier=
            nombre_articles_panier


        

    )



# =========================================================
# AJOUTER UN PRODUIT AU PANIER
# =========================================================

@app.route(
    "/panier/ajouter/<int:id_produit>",
    methods=["POST"]
)
def ajouter_au_panier(id_produit):

    if not role_autorise("client"):
        return jsonify({
            "message": "Accès refusé."
        }), 403

    reponse = api_get(
        f"{API_URL}/produits"
    )

    if reponse.status_code != 200:
        return jsonify({
            "message": "Impossible de récupérer les produits."
        }), reponse.status_code

    liste_produits = reponse.json()

    produit = next(
        (
            p for p in liste_produits
            if p["id_produit"] == id_produit
        ),
        None
    )

    if produit is None:
        return jsonify({
            "message": "Produit introuvable."
        }), 404

    if not produit.get("actif", True):
        return jsonify({
            "message": "Ce produit n'est plus disponible."
        }), 400

    stock = produit.get("stock", 0)

    if stock <= 0:
        return jsonify({
            "message": (
                "Ce produit est actuellement en rupture de stock."
            )
        }), 400

    panier = session.get("panier", {})

    id_produit_str = str(id_produit)

    quantite_actuelle = int(
        panier.get(id_produit_str, 0)
    )

    if quantite_actuelle >= stock:
        return jsonify({
            "message": (
                "Vous avez déjà atteint la quantité "
                "disponible en stock."
            )
        }), 400

    panier[id_produit_str] = quantite_actuelle + 1

    session["panier"] = panier
    session.modified = True

    nombre_articles = sum(
        int(quantite)
        for quantite in panier.values()
    )

    return jsonify({
        "message": "Produit ajouté au panier.",
        "nombre_articles": nombre_articles
    })


# =========================================================
# =========================================================
# MODIFIER LA QUANTITÉ D'UN SERVICE DANS LE PANIER
# =========================================================
# =========================================================

@app.route(
    "/panier/services/modifier/<int:id_service>",
    methods=["POST"]
)
def modifier_panier_service(id_service):

    # -----------------------------------------------------
    # Vérification du rôle
    # -----------------------------------------------------

    if not role_autorise("client"):
        return (
            "Accès refusé : seuls les clients "
            "peuvent modifier le panier.",
            403
        )

    # -----------------------------------------------------
    # Récupération de l'action
    # -----------------------------------------------------

    action = request.form.get("action")

    # -----------------------------------------------------
    # Récupération du panier des services
    # -----------------------------------------------------

    panier_services = session.get(
        "panier_services",
        {}
    )

    id_service_str = str(id_service)

    # -----------------------------------------------------
    # Vérifier que le service existe dans le panier
    # -----------------------------------------------------

    if id_service_str not in panier_services:
        return (
            "Ce service n'est pas présent dans votre panier.",
            404
        )

    quantite_actuelle = int(
        panier_services[id_service_str]
    )

    # -----------------------------------------------------
    # AUGMENTER
    # -----------------------------------------------------

    if action == "plus":

        quantite_actuelle += 1

        panier_services[id_service_str] = (
            quantite_actuelle
        )

    # -----------------------------------------------------
    # DIMINUER
    # -----------------------------------------------------

    elif action == "moins":

        quantite_actuelle -= 1

        # Si la quantité arrive à zéro,
        # on retire le service du panier.

        if quantite_actuelle <= 0:

            del panier_services[
                id_service_str
            ]

        else:

            panier_services[id_service_str] = (
                quantite_actuelle
            )

    # -----------------------------------------------------
    # Action inconnue
    # -----------------------------------------------------

    else:

        return (
            "Action de panier inconnue.",
            400
        )

    # -----------------------------------------------------
    # Sauvegarde de la session
    # -----------------------------------------------------

    session["panier_services"] = panier_services
    session.modified = True

    # -----------------------------------------------------
    # Retour vers le panier
    # -----------------------------------------------------

    return redirect(
        url_for("panier")
    )

# =========================================================
# =========================================================
# SUPPRIMER UN SERVICE DU PANIER
# =========================================================
# =========================================================

@app.route(
    "/panier/services/supprimer/<int:id_service>",
    methods=["POST"]
)
def supprimer_service_du_panier(id_service):

    # -----------------------------------------------------
    # Vérification du rôle
    # -----------------------------------------------------

    if not role_autorise("client"):
        return (
            "Accès refusé : seuls les clients "
            "peuvent modifier le panier.",
            403
        )

    # -----------------------------------------------------
    # Récupération du panier des services
    # -----------------------------------------------------

    panier_services = session.get(
        "panier_services",
        {}
    )

    id_service_str = str(id_service)

    # -----------------------------------------------------
    # Suppression
    # -----------------------------------------------------

    if id_service_str in panier_services:

        del panier_services[
            id_service_str
        ]

    # -----------------------------------------------------
    # Sauvegarde
    # -----------------------------------------------------

    session["panier_services"] = panier_services
    session.modified = True

    # -----------------------------------------------------
    # Retour au panier
    # -----------------------------------------------------

    return redirect(
        url_for("panier")
    )



# =========================================================
# =========================================================
# VIDER COMPLÈTEMENT LE PANIER
# =========================================================
# =========================================================

@app.route(
    "/panier/vider",
    methods=["POST"]
)
def vider_panier():

    # -----------------------------------------------------
    # Vérification du rôle
    # -----------------------------------------------------

    if not role_autorise("client"):
        return (
            "Accès refusé : seuls les clients "
            "peuvent vider le panier.",
            403
        )

    # -----------------------------------------------------
    # Suppression des produits
    # -----------------------------------------------------

    session.pop(
        "panier",
        None
    )

    # -----------------------------------------------------
    # Suppression des services
    # -----------------------------------------------------

    session.pop(
        "panier_services",
        None
    )

    # -----------------------------------------------------
    # Retour au panier
    # -----------------------------------------------------

    return redirect(
        url_for("panier")
    )


# =========================================================
# =========================================================
# MES SERVICES
# =========================================================
# =========================================================



# =========================================================
# AFFICHER LES SERVICES
# =========================================================

@app.route("/services")
def afficher_services():

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est connecté
    # avec un rôle autorisé
    # -----------------------------------------------------

    if not role_autorise(
        "admin",
        "vendeur",
        "client"
    ):
        return (
            "Accès refusé.",
            403
        )

    # -----------------------------------------------------
    # RÉCUPÉRER LES SERVICES DEPUIS FASTAPI
    # -----------------------------------------------------

    try:

        reponse = api_get("/services")

    except requests.RequestException as erreur:

        return (
            "Impossible de communiquer avec "
            f"le serveur : {erreur}",
            500
        )

    # -----------------------------------------------------
    # Vérifier la réponse de FastAPI
    # -----------------------------------------------------

    if reponse.status_code != 200:

        try:

            detail = reponse.json().get(
                "detail",
                "Impossible de récupérer les services."
            )

        except Exception:

            detail = (
                "Impossible de récupérer les services."
            )

        return (
            f"Erreur : {detail}",
            reponse.status_code
        )

    # -----------------------------------------------------
    # Services + URL des médias (Cloudinary ou local)
    # -----------------------------------------------------

    services = enrichir_services(reponse.json())

    # -----------------------------------------------------
    # Afficher la page
    # (compteur du panier : produits + services)
    # -----------------------------------------------------

    return render_template(
        "services.html",
        services=services,
        role=session.get("role"),
        nombre_articles_panier=compter_articles_panier()
    )


# =========================================================
# AJOUTER UN SERVICE
# =========================================================

@app.route(
    "/services/ajouter",
    methods=["POST"]
)
def ajouter_service():

    # =====================================================
    # VÉRIFICATION DU RÔLE
    # =====================================================

    if not role_autorise("admin", "vendeur"):

        return (
            "Accès refusé : vous n'avez pas "
            "l'autorisation d'ajouter un service.",
            403
        )

    # =====================================================
    # DONNÉES DU FORMULAIRE
    # =====================================================

    nom_service = request.form.get("nom_service", "").strip()
    prix = request.form.get("prix", "").strip()
    description = request.form.get("description", "").strip()
    categorie = request.form.get("categorie", "").strip()
    actif = request.form.get("actif") is not None

    if not nom_service:

        flash("Le nom du service est obligatoire.", "danger")

        return redirect(url_for("afficher_services"))

    try:
        prix = float(prix)

    except (TypeError, ValueError):

        flash("Veuillez saisir un prix valide.", "danger")

        return redirect(url_for("afficher_services"))

    if prix < 0:

        flash("Le prix ne peut pas être négatif.", "danger")

        return redirect(url_for("afficher_services"))

    # =====================================================
    # VÉRIFIER LES FICHIERS AVANT TOUT TÉLÉVERSEMENT
    # =====================================================

    fichier_image = request.files.get("image")
    fichier_video = request.files.get("video")

    avec_image = bool(fichier_image and fichier_image.filename)
    avec_video = bool(fichier_video and fichier_video.filename)

    if avec_image and not extension_autorisee(
        fichier_image.filename,
        EXTENSIONS_IMAGE_SERVICE
    ):

        flash(
            "Format d'image non autorisé. "
            "Utilisez JPG, JPEG, PNG ou WEBP.",
            "danger"
        )

        return redirect(url_for("afficher_services"))

    if avec_video and not extension_autorisee(
        fichier_video.filename,
        EXTENSIONS_VIDEO_SERVICE
    ):

        flash(
            "Format vidéo non autorisé. "
            "Utilisez MP4, WEBM ou MOV.",
            "danger"
        )

        return redirect(url_for("afficher_services"))

    # =====================================================
    # TÉLÉVERSEMENT (Cloudinary en production)
    # =====================================================

    nom_image = None
    nom_video = None

    def nettoyer():
        supprimer_media(nom_image, "services_images", local=True)
        supprimer_media(nom_video, "services_videos", local=True)

    try:

        if avec_image:
            nom_image = televerser_media(
                fichier_image,
                "services_images",
                "image"
            )

        if avec_video:
            nom_video = televerser_media(
                fichier_video,
                "services_videos",
                "video"
            )

    except ErreurMedia as erreur:

        nettoyer()

        flash(str(erreur), "danger")

        return redirect(url_for("afficher_services"))

    # =====================================================
    # ENVOYER LE SERVICE À FASTAPI
    # =====================================================

    donnees = {
        "nom_service": nom_service,
        "prix": prix,
        "description": description or None,
        "categorie": categorie or None,
        "image": nom_image,
        "video": nom_video,
        "actif": actif
    }

    try:

        reponse = api_post("/services", json=donnees)

    except SessionExpiree:

        nettoyer()

        raise

    except requests.RequestException as erreur:

        nettoyer()

        flash(
            f"Erreur de communication avec l'API : {erreur}",
            "danger"
        )

        return redirect(url_for("afficher_services"))

    if reponse.status_code not in [200, 201]:

        nettoyer()

        try:
            erreur_api = reponse.json()

        except Exception:
            erreur_api = {"detail": reponse.text}

        flash(
            "Impossible d'ajouter le service : "
            + str(erreur_api.get("detail", "Erreur inconnue.")),
            "danger"
        )

        return redirect(url_for("afficher_services"))

    flash("Service ajouté avec succès.", "success")

    return redirect(url_for("afficher_services"))


# =========================================================
# MODIFIER UN SERVICE
# =========================================================

@app.route(
    "/services/modifier/<int:id_service>",
    methods=["POST"]
)
def modifier_service(
    id_service
):
    """
    Modifie un service existant.

    Réservé à l'admin et au vendeur.
    """

    if not role_autorise(
        "admin",
        "vendeur"
    ):
        return "Accès refusé.", 403

    # -----------------------------------------------------
    # Récupérer le service actuel
    # -----------------------------------------------------

    reponse_services = api_get("/services")

    if not reponse_services.ok:

        flash("Impossible de récupérer les services.", "error")

        return redirect(url_for("afficher_services"))

    service_actuel = next(
        (
            service
            for service in reponse_services.json()
            if service["id_service"] == id_service
        ),
        None
    )

    if service_actuel is None:

        flash("Service introuvable.", "error")

        return redirect(url_for("afficher_services"))

    # -----------------------------------------------------
    # Données du formulaire
    # -----------------------------------------------------

    nom_service = request.form.get("nom_service", "").strip()
    prix = request.form.get("prix", "0")
    description = request.form.get("description", "").strip()
    categorie = request.form.get("categorie", "").strip()
    actif = request.form.get("actif") == "on"

    if not nom_service:

        flash("Le nom du service est obligatoire.", "error")

        return redirect(url_for("afficher_services"))

    try:
        prix = float(prix)

    except (ValueError, TypeError):

        flash("Le prix est invalide.", "error")

        return redirect(url_for("afficher_services"))

    # -----------------------------------------------------
    # Médias actuels (conservés si aucun nouveau fichier)
    # -----------------------------------------------------

    ancienne_image = service_actuel.get("image")
    ancienne_video = service_actuel.get("video")

    nom_image = ancienne_image
    nom_video = ancienne_video

    fichier_image = request.files.get("image")
    fichier_video = request.files.get("video")

    avec_image = bool(fichier_image and fichier_image.filename)
    avec_video = bool(fichier_video and fichier_video.filename)

    # -----------------------------------------------------
    # Vérifier les formats avant tout téléversement
    # -----------------------------------------------------

    if avec_image and not extension_autorisee(
        fichier_image.filename,
        EXTENSIONS_IMAGE_SERVICE
    ):

        flash("Format d'image non autorisé.", "error")

        return redirect(url_for("afficher_services"))

    if avec_video and not extension_autorisee(
        fichier_video.filename,
        EXTENSIONS_VIDEO_SERVICE
    ):

        flash("Format de vidéo non autorisé.", "error")

        return redirect(url_for("afficher_services"))

    # -----------------------------------------------------
    # Téléversement des nouveaux médias
    # -----------------------------------------------------

    nouvelle_image = None
    nouvelle_video = None

    def nettoyer():
        supprimer_media(nouvelle_image, "services_images", local=True)
        supprimer_media(nouvelle_video, "services_videos", local=True)

    try:

        if avec_image:
            nouvelle_image = televerser_media(
                fichier_image,
                "services_images",
                "image"
            )
            nom_image = nouvelle_image

        if avec_video:
            nouvelle_video = televerser_media(
                fichier_video,
                "services_videos",
                "video"
            )
            nom_video = nouvelle_video

    except ErreurMedia as erreur:

        nettoyer()

        flash(str(erreur), "error")

        return redirect(url_for("afficher_services"))

    # -----------------------------------------------------
    # Mise à jour FastAPI
    # -----------------------------------------------------

    donnees = {
        "nom_service": nom_service,
        "prix": prix,
        "description": description or None,
        "categorie": categorie or None,
        "image": nom_image,
        "video": nom_video,
        "actif": actif
    }

    try:

        reponse = api_put(
            f"/services/{id_service}",
            json=donnees
        )

    except (SessionExpiree, requests.RequestException):

        nettoyer()

        raise

    if not reponse.ok:

        nettoyer()

        flash("Erreur lors de la modification du service.", "error")

        return redirect(url_for("afficher_services"))

    # -----------------------------------------------------
    # Supprimer les anciens médias Cloudinary remplacés
    # -----------------------------------------------------

    if nouvelle_image:
        supprimer_media(ancienne_image, "services_images")

    if nouvelle_video:
        supprimer_media(ancienne_video, "services_videos")

    flash("Service modifié avec succès.", "success")

    return redirect(url_for("afficher_services"))


# =========================================================
# SUPPRIMER UN SERVICE
# =========================================================

@app.route(
    "/services/supprimer/<int:id_service>",
    methods=["POST"]
)
def supprimer_service(
    id_service
):
    """
    Supprime un service.

    Réservé à l'admin et au vendeur.
    """

    if not role_autorise(
        "admin",
        "vendeur"
    ):
        return "Accès refusé.", 403

    reponse = api_delete(
        f"{API_URL}/services/{id_service}"
    )

    if not reponse.ok:

        try:
            message = reponse.json().get(
                "message",
                "Impossible de supprimer le service."
            )

        except Exception:
            message = (
                "Impossible de supprimer le service."
            )

        flash(
            message,
            "error"
        )

        return redirect(
            url_for("afficher_services")
        )

    flash(
        "Service supprimé avec succès.",
        "success"
    )

    return redirect(
        url_for("afficher_services")
    )


# =========================================================
# 💳 PAGE DE PAIEMENT
# =========================================================

@app.route("/paiement", methods=["GET"])
def paiement():

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est connecté
    # -----------------------------------------------------

    if "access_token" not in session:
        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Récupérer le panier actuel
    # -----------------------------------------------------

    panier = session.get("panier", {})
    panier_services = session.get(
        "panier_services",
        {}
    )

    # -----------------------------------------------------
    # Vérifier que le panier n'est pas vide
    # -----------------------------------------------------

    if not panier and not panier_services:

        return redirect(
            url_for("panier")
        )

    # -----------------------------------------------------
    # Envoyer la page de paiement
    # -----------------------------------------------------

    return render_template(
        "paiement.html"
    )


# =========================================================
# 💳 CONFIRMER LE PAIEMENT ET PASSER LA COMMANDE
# =========================================================
@app.route("/confirmer-paiement", methods=["POST"])
def confirmer_paiement():

    # =========================================================
    # 🔐 VÉRIFICATION DE LA CONNEXION
    # =========================================================

    if "access_token" not in session:
        return redirect(url_for("login"))


    # =========================================================
    # 💳 RÉCUPÉRER LE MODE DE PAIEMENT
    # =========================================================

    methode_paiement = request.form.get(
        "methode_paiement"
    )

    latitude = (request.form.get("latitude") or "").strip()
    longitude = (request.form.get("longitude") or "").strip()


    # =========================================================
    # ✅ MODES DE PAIEMENT AUTORISÉS
    # =========================================================

    methodes_autorisees = [
        "livraison",
        "wave",
        "orange_money",
        "carte"
    ]

    if methode_paiement not in methodes_autorisees:

        return redirect(
            url_for("paiement")
        )


    # =========================================================
    # 🛒 RÉCUPÉRER LE PANIER
    # =========================================================

    panier = session.get(
        "panier",
        {}
    )

    panier_services = session.get(
        "panier_services",
        {}
    )


    # =========================================================
    # 🚫 VÉRIFIER QUE LE PANIER N'EST PAS VIDE
    # =========================================================

    if not panier and not panier_services:

        return redirect(
            url_for("panier")
        )


    # =========================================================
    # 📦 PRÉPARER LES PRODUITS
    # =========================================================

    lignes_produits = []

    for id_produit, quantite in panier.items():

        lignes_produits.append({

            "id_produit": int(id_produit),

            "quantite": int(quantite)

        })


    # =========================================================
    # 🛠️ PRÉPARER LES SERVICES
    # =========================================================

    lignes_services = []

    for id_service, quantite in panier_services.items():

        lignes_services.append({

            "id_service": int(id_service),

            "quantite": int(quantite)

        })


    # =========================================================
    # 🧾 PRÉPARER LES DONNÉES DE LA COMMANDE
    # =========================================================

    donnees_commande = {

        "lignes": lignes_produits,

        "services": lignes_services,

        "methode_paiement": methode_paiement

    }

    if latitude:
        try:
            donnees_commande["latitude"] = float(latitude)
        except ValueError:
            pass

    if longitude:
        try:
            donnees_commande["longitude"] = float(longitude)
        except ValueError:
            pass


    # =========================================================
    # 🚀 ENVOYER LA COMMANDE À FASTAPI
    # =========================================================

    try:

        reponse = api_post(
            f"{API_URL}/commandes/depuis-panier",
            json=donnees_commande
        )

    except requests.RequestException as e:

        print(
            "❌ Erreur de communication avec FastAPI :",
            e
        )

        return render_template(
            "paiement.html",
            erreur=(
                "Impossible de contacter le serveur. "
                "Veuillez réessayer."
            )
        )


    # =========================================================
    # 📡 VÉRIFIER LA RÉPONSE HTTP
    # =========================================================

    if reponse.status_code != 200:

        try:

            erreur_api = reponse.json()

        except Exception:

            erreur_api = {}


        message_erreur = erreur_api.get(
            "detail",
            "Une erreur est survenue lors de la création de la commande."
        )


        return render_template(
            "paiement.html",
            erreur=message_erreur
        )


    # =========================================================
    # 📄 CONVERTIR LA RÉPONSE EN JSON
    # =========================================================

    try:

        donnees_reponse = reponse.json()

    except Exception:

        return render_template(
            "paiement.html",
            erreur=(
                "La réponse du serveur est invalide."
            )
        )


    # =========================================================
    # 🔎 RÉCUPÉRER LES INFORMATIONS
    # =========================================================

    id_commande = donnees_reponse.get(
        "id_commande"
    )

    id_paiement = donnees_reponse.get(
        "id_paiement"
    )

    total = donnees_reponse.get(
        "total",
        0
    )

    statut_commande = donnees_reponse.get(
        "statut",
        "en_attente"
    )

    statut_paiement = donnees_reponse.get(
        "statut_paiement",
        "en_attente"
    )


    # =========================================================
    # 🚨 VÉRIFIER QUE LA COMMANDE A BIEN ÉTÉ CRÉÉE
    # =========================================================

    if not id_commande:

        return render_template(
            "paiement.html",
            erreur=(
                "La commande n'a pas pu être créée."
            )
        )


    # =========================================================
    # 🧹 VIDER LE PANIER
    # =========================================================

    session["panier"] = {}

    session["panier_services"] = {}

    session.modified = True


    # =========================================================
    # 💾 SAUVEGARDER LA COMMANDE CONFIRMÉE EN SESSION
    # =========================================================

    session["commande_confirmee"] = {

        "id_commande": id_commande,

        "id_paiement": id_paiement,

        "total": total,

        "methode_paiement": methode_paiement,

        "statut_commande": statut_commande,

        "statut_paiement": statut_paiement

    }

    session.modified = True


    # =========================================================
    # ✅ REDIRECTION VERS LA PAGE DE CONFIRMATION
    # =========================================================

    return redirect(
        url_for(
            "confirmation_commande"
        )
    )




# =========================================================
# ✅ PAGE DE CONFIRMATION DE COMMANDE
# =========================================================

@app.route("/confirmation-commande", methods=["GET"])
def confirmation_commande():

    # -----------------------------------------------------
    # Vérifier la connexion
    # -----------------------------------------------------

    if "access_token" not in session:

        return redirect(
            url_for("login")
        )


    # -----------------------------------------------------
    # Récupérer les informations
    # -----------------------------------------------------

    commande_confirmee = session.get(
        "commande_confirmee"
    )


    # -----------------------------------------------------
    # Si aucune commande récente
    # -----------------------------------------------------

    if not commande_confirmee:

        return redirect(
            url_for("mes_commandes")
        )


    # -----------------------------------------------------
    # Afficher la confirmation
    # -----------------------------------------------------

    return render_template(

        "confirmation_commande.html",

        commande=commande_confirmee
    )



# =========================================================
# ACTIVER / DÉSACTIVER UN SERVICE
# =========================================================

@app.route(
    "/services/<int:id_service>/actif",
    methods=["POST"]
)
def modifier_statut_service(
    id_service
):
    """
    Active ou désactive un service.
    """

    if not role_autorise(
        "admin",
        "vendeur"
    ):
        return "Accès refusé.", 403

    actif = request.form.get(
        "actif"
    ) == "true"

    reponse = api_put(
        f"{API_URL}/services/{id_service}/actif",
        params={
            "actif": actif
        }
    )

    if not reponse.ok:

        flash(
            "Impossible de modifier le statut du service.",
            "error"
        )

        return redirect(
            url_for("afficher_services")
        )

    if actif:

        flash(
            "Service activé avec succès.",
            "success"
        )

    else:

        flash(
            "Service désactivé avec succès.",
            "success"
        )

    return redirect(
        url_for("afficher_services")
    )







# =========================================================
# PAGE : COMMANDES
# =========================================================

@app.route("/commandes")
def commandes():

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "d'accéder à cette page.",
            403
        )

    # =====================================================
    # RÉCUPÉRER LES COMMANDES
    # =====================================================

    reponse = api_get(
        f"{API_URL}/commandes"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la récupération des commandes : "
            f"{reponse.text}"
        ), reponse.status_code

    liste_commandes = reponse.json()

    # =====================================================
    # RÉCUPÉRER LES CLIENTS
    # =====================================================

    reponse_clients = api_get(
        f"{API_URL}/clients"
    )

    if reponse_clients.status_code != 200:
        return (
            f"Erreur lors de la récupération des clients : "
            f"{reponse_clients.text}"
        ), reponse_clients.status_code

    liste_clients = reponse_clients.json()

    return render_template(
        "commandes.html",
        commandes=liste_commandes,
        clients=liste_clients,
        date_aujourdhui=date.today()
    )


# =========================================================
# AJOUTER UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/ajouter",
    methods=["POST"]
)
def ajouter_commande():

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "d'ajouter une commande.",
            403
        )

    id_client = request.form["id_client"]
    date_commande = request.form["date_commande"]

    reponse = api_post(
        f"{API_URL}/commandes",
        json={
            "CLIENT_id_client": int(id_client),
            "date_commande": date_commande
        }
    )

    if reponse.status_code not in [200, 201]:
        return (
            f"Erreur lors de l'ajout de la commande : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(url_for("commandes"))


# =========================================================
# DÉTAIL D'UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>"
)
def detail_commande(id_commande):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "d'accéder aux commandes.",
            403
        )

    # =====================================================
    # RÉCUPÉRER LES PRODUITS DE LA COMMANDE
    # =====================================================

    reponse = api_get(
        f"{API_URL}/commandes/{id_commande}/produits"
    )

    if reponse.status_code != 200:
        return (
            "Erreur lors de la récupération des produits "
            "de la commande : "
            f"{reponse.text}"
        ), reponse.status_code

    data = reponse.json()

    if "produits" in data:

        produits_commande = data["produits"]
        total_commande = data["total_commande"]
        message = None

    else:

        produits_commande = []
        total_commande = 0
        message = data.get("message")

    # =====================================================
    # RÉCUPÉRER LES COMMANDES
    # =====================================================

    reponse_commandes = api_get(
        f"{API_URL}/commandes"
    )

    if reponse_commandes.status_code != 200:
        return (
            "Erreur lors de la récupération des commandes : "
            f"{reponse_commandes.text}"
        ), reponse_commandes.status_code

    commandes = reponse_commandes.json()

    commande = next(
        (
            c for c in commandes
            if c["id_commande"] == id_commande
        ),
        None
    )

    if commande is None:
        return "Commande introuvable.", 404

    # =====================================================
    # RÉCUPÉRER LES CLIENTS
    # =====================================================

    reponse_clients = api_get(
        f"{API_URL}/clients"
    )

    if reponse_clients.status_code != 200:
        return (
            "Erreur lors de la récupération des clients : "
            f"{reponse_clients.text}"
        ), reponse_clients.status_code

    clients = reponse_clients.json()

    # =====================================================
    # RÉCUPÉRER LES PRODUITS
    # =====================================================

    reponse_produits = api_get(
        f"{API_URL}/produits"
    )

    if reponse_produits.status_code != 200:
        return (
            "Erreur lors de la récupération des produits : "
            f"{reponse_produits.text}"
        ), reponse_produits.status_code

    liste_produits = reponse_produits.json()

    # =====================================================
    # RÉCUPÉRER LES MESSAGES DE LA COMMANDE
    # =====================================================

    reponse_messages = api_get(
        f"{API_URL}/commandes/{id_commande}/messages"
    )

    if reponse_messages.status_code == 200:
        messages = reponse_messages.json()
    else:
        messages = []

    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render_template(
        "detail_commande.html",
        commande=commande,
        produits=produits_commande,
        clients=clients,
        liste_produits=liste_produits,
        total_commande=total_commande,
        message=message,
        messages=messages
    )


# =========================================================
# MODIFIER LE STATUT D'UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/statut",
    methods=["POST"]
)
def modifier_statut_commande(id_commande):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de modifier le statut de cette commande.",
            403
        )

    nouveau_statut = request.form.get("nouveau_statut")

    if not nouveau_statut:
        return (
            "Le nouveau statut de la commande est obligatoire.",
            400
        )

    # -----------------------------------------------------
    # Envoyer le nouveau statut à FastAPI
    # -----------------------------------------------------

    reponse = api_put(
        f"{API_URL}/commandes/{id_commande}/statut",
        params={
            "nouveau_statut": nouveau_statut
        }
    )

    # -----------------------------------------------------
    # Vérifier la réponse
    # -----------------------------------------------------

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la modification du statut : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(
        url_for(
            "detail_commande",
            id_commande=id_commande
        )
    )




# =========================================================
# AJOUTER UN PRODUIT À UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/produits/ajouter",
    methods=["POST"]
)
def ajouter_produit_commande(id_commande):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de modifier une commande.",
            403
        )

    id_produit = request.form["id_produit"]
    quantite = request.form["quantite"]

    reponse = api_post(
        f"{API_URL}/commandes/{id_commande}/produits",
        json={
            "PRODUIT_id_produit": int(id_produit),
            "quantite": int(quantite)
        }
    )

    if reponse.status_code not in [200, 201]:
        return (
            f"Erreur lors de l'ajout du produit à la commande : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(
        url_for(
            "detail_commande",
            id_commande=id_commande
        )
    )


# =========================================================
# MODIFIER LA QUANTITÉ D'UN PRODUIT DANS UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/produits/"
    "<int:id_produit>/modifier",
    methods=["POST"]
)
def modifier_quantite_produit(
    id_commande,
    id_produit
):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de modifier une commande.",
            403
        )

    quantite = request.form["quantite"]

    reponse = api_put(
        f"{API_URL}/commandes/"
        f"{id_commande}/produits/{id_produit}",
        json={
            "quantite": int(quantite)
        }
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la modification de la quantité : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(
        url_for(
            "detail_commande",
            id_commande=id_commande
        )
    )


# =========================================================
# SUPPRIMER UN PRODUIT D'UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/produits/"
    "<int:id_produit>/supprimer",
    methods=["POST"]
)
def supprimer_produit_commande(
    id_commande,
    id_produit
):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de modifier une commande.",
            403
        )

    reponse = api_delete(
        f"{API_URL}/commandes/"
        f"{id_commande}/produits/{id_produit}"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la suppression du produit : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(
        url_for(
            "detail_commande",
            id_commande=id_commande
        )
    )


# =========================================================
# MODIFIER UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/modifier",
    methods=["POST"]
)
def modifier_commande(id_commande):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de modifier une commande.",
            403
        )

    id_client = request.form["id_client"]
    date_commande = request.form["date_commande"]

    # Récupérer le statut actuel de la commande
    reponse_commande = api_get(
        f"{API_URL}/commandes"
    )

    if reponse_commande.status_code != 200:
        return (
            f"Erreur lors de la récupération de la commande : "
            f"{reponse_commande.text}",
            reponse_commande.status_code
        )

    commandes = reponse_commande.json()

    commande = next(
        (
            c for c in commandes
            if c["id_commande"] == id_commande
        ),
        None
    )

    if commande is None:
        return "Commande introuvable.", 404

    statut = commande["statut"]

    reponse = api_put(
        f"{API_URL}/commandes/{id_commande}",
        json={
            "CLIENT_id_client": int(id_client),
            "date_commande": date_commande,
            "statut": statut
        }
    )

    if reponse.status_code not in [200, 201]:
        return (
            f"Erreur lors de la modification de la commande : "
            f"{reponse.text}"
        ), reponse.status_code

    return redirect(
        url_for(
            "detail_commande",
            id_commande=id_commande
        )
    )


# =========================================================
# SUPPRIMER UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/supprimer",
    methods=["POST"]
)
def supprimer_commande(id_commande):

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : vous n'avez pas l'autorisation "
            "de supprimer une commande.",
            403
        )

    reponse = api_delete(
        f"{API_URL}/commandes/{id_commande}"
    )

    if reponse.status_code != 200:
        return (
            f"Erreur lors de la suppression de la commande : "
            f"{reponse.text}",
            reponse.status_code
        )

    return redirect(
        url_for("commandes")
    )


# =========================================================
# CRÉATION D'UN UTILISATEUR PAR L'ADMINISTRATEUR
# =========================================================

@app.route(
    "/utilisateurs/creer",
    methods=["GET", "POST"]
)
def creer_utilisateur_admin():

    if not role_autorise("admin"):
        return (
            "Accès refusé : cette page est réservée "
            "à l'administrateur.",
            403
        )

    if request.method == "GET":
        return render_template(
            "creer_utilisateur_admin.html"
        )

    nom = request.form["nom"]
    prenom = request.form["prenom"]
    email = request.form["email"]
    mot_de_passe = request.form["mot_de_passe"]
    confirmation = request.form["confirmation"]
    role = request.form["role"]

    if mot_de_passe != confirmation:
        return render_template(
            "creer_utilisateur_admin.html",
            erreur="Les mots de passe ne correspondent pas."
        )

    roles_autorises = [
        "admin",
        "vendeur",
        "client"
    ]

    if role not in roles_autorises:
        return render_template(
            "creer_utilisateur_admin.html",
            erreur="Rôle invalide."
        )

    reponse = api_post(
        f"{API_URL}/utilisateurs/admin",
        json={
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "mot_de_passe": mot_de_passe,
            "role": role
        }
    )

    if reponse.status_code not in [200, 201]:

        try:
            erreur = reponse.json().get(
                "detail",
                "Impossible de créer l'utilisateur."
            )

        except Exception:
            erreur = (
                "Impossible de créer l'utilisateur."
            )

        return render_template(
            "creer_utilisateur_admin.html",
            erreur=erreur
        )

    return redirect(url_for("utilisateurs"))



# =========================================================
# AJOUTER UN SERVICE AU PANIER
# =========================================================

@app.route(
    "/panier/services/ajouter/<int:id_service>",
    methods=["POST"]
)
def ajouter_service_au_panier(id_service):

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est un client
    # -----------------------------------------------------

    if not role_autorise("client"):

        return jsonify({
            "message": (
                "Accès refusé : seuls les clients "
                "peuvent ajouter un service au panier."
            )
        }), 403


    # -----------------------------------------------------
    # Récupérer la liste des services depuis FastAPI
    # -----------------------------------------------------

    try:

        reponse = api_get(
            f"{API_URL}/services",
            timeout=5
        )

    except Exception as erreur:

        return jsonify({
            "message": (
                "Impossible de communiquer avec "
                "le serveur : "
                f"{erreur}"
            )
        }), 500


    # -----------------------------------------------------
    # Vérifier la réponse de l'API
    # -----------------------------------------------------

    if reponse.status_code != 200:

        try:

            detail = reponse.json().get(
                "detail",
                "Impossible de récupérer les services."
            )

        except Exception:

            detail = (
                "Impossible de récupérer les services."
            )

        return jsonify({
            "message": detail
        }), reponse.status_code


    services = reponse.json()


    # -----------------------------------------------------
    # Rechercher le service demandé
    # -----------------------------------------------------

    service = next(
        (
            s for s in services
            if int(s["id_service"]) == id_service
        ),
        None
    )


    # -----------------------------------------------------
    # Vérifier que le service existe
    # -----------------------------------------------------

    if service is None:

        return jsonify({
            "message": "Service introuvable."
        }), 404


    # -----------------------------------------------------
    # Vérifier que le service est actif
    # -----------------------------------------------------

    if not service.get("actif", False):

        return jsonify({
            "message": (
                "Ce service n'est actuellement "
                "plus disponible."
            )
        }), 400


    # -----------------------------------------------------
    # Récupérer le panier des services
    #
    # Exemple :
    #
    # {
    #     "1": 2,
    #     "3": 1
    # }
    #
    # signifie :
    # service 1 → quantité 2
    # service 3 → quantité 1
    # -----------------------------------------------------

    panier_services = session.get(
        "panier_services",
        {}
    )


    # -----------------------------------------------------
    # Ajouter une unité du service
    # -----------------------------------------------------

    id_service_str = str(id_service)

    panier_services[id_service_str] = (
        int(
            panier_services.get(
                id_service_str,
                0
            )
        )
        + 1
    )


    # -----------------------------------------------------
    # Sauvegarder le panier dans la session
    # -----------------------------------------------------

    session["panier_services"] = panier_services

    # Important pour que Flask sauvegarde immédiatement
    # la modification de la session.

    session.modified = True


    # -----------------------------------------------------
    # Calculer le nombre total d'articles
    #
    # Produits + services
    # -----------------------------------------------------

    panier_produits = session.get(
        "panier",
        {}
    )

    nombre_articles_produits = sum(
        int(quantite)
        for quantite in panier_produits.values()
    )

    nombre_articles_services = sum(
        int(quantite)
        for quantite in panier_services.values()
    )

    nombre_articles_total = (
        nombre_articles_produits
        + nombre_articles_services
    )


    # -----------------------------------------------------
    # Réponse JSON
    # -----------------------------------------------------

    return jsonify({

        "success": True,

        "message": (
            f"Service « "
            f"{service['nom_service']} » "
            "ajouté au panier."
        ),

        "id_service": id_service,

        "nom_service": (
            service["nom_service"]
        ),

        "quantite": (
            panier_services[id_service_str]
        ),

        "nombre_articles": (
            nombre_articles_total
        )

    }), 200





# =========================================================
# =========================================================
# COMMANDER LE PANIER
# =========================================================
# =========================================================

@app.route(
    "/panier/commander",
    methods=["POST"]
)
def commander_panier():

    # =====================================================
    # 1. VÉRIFIER QUE L'UTILISATEUR EST UN CLIENT
    # =====================================================

    if not role_autorise("client"):

        return (
            "Accès refusé : seuls les clients "
            "peuvent commander.",
            403
        )


    # =====================================================
    # 2. RÉCUPÉRER LE PANIER DES PRODUITS
    # =====================================================

    panier_produits = session.get(
        "panier",
        {}
    )


    # =====================================================
    # 3. RÉCUPÉRER LE PANIER DES SERVICES
    # =====================================================

    panier_services = session.get(
        "panier_services",
        {}
    )


    # =====================================================
    # 4. VÉRIFIER QUE LE PANIER COMPLET N'EST PAS VIDE
    # =====================================================

    if not panier_produits and not panier_services:

        return (
            "Votre panier est vide.",
            400
        )


    # =====================================================
    # 5. PRÉPARER LES LIGNES DE PRODUITS
    # =====================================================

    lignes = []


    for id_produit, quantite in panier_produits.items():

        lignes.append({

            "id_produit":
                int(id_produit),

            "quantite":
                int(quantite)

        })


    # =====================================================
    # 6. PRÉPARER LES LIGNES DE SERVICES
    # =====================================================

    services = []


    for id_service, quantite in panier_services.items():

        services.append({

            "id_service":
                int(id_service),

            "quantite":
                int(quantite)

        })


    # =====================================================
    # 7. ENVOYER LE PANIER COMPLET À FASTAPI
    # =====================================================

    reponse = api_post(

        f"{API_URL}/commandes/depuis-panier",

        json={

            # -----------------------------
            # PRODUITS
            # -----------------------------

            "lignes":
                lignes,


            # -----------------------------
            # SERVICES
            # -----------------------------

            "services":
                services

        }
    )


    # =====================================================
    # 8. GÉRER UNE ÉVENTUELLE ERREUR
    # =====================================================

    if reponse.status_code != 200:

        try:

            erreur = reponse.json().get(

                "detail",

                "Impossible de créer la commande."

            )

        except Exception:

            erreur = (
                "Impossible de créer la commande."
            )


        return (

            f"Erreur : {erreur}",

            reponse.status_code

        )


    # =====================================================
    # 9. RÉCUPÉRER LA COMMANDE CRÉÉE
    # =====================================================

    commande = reponse.json()


    # =====================================================
    # 10. VIDER LE PANIER DES PRODUITS
    # =====================================================

    session.pop(
        "panier",
        None
    )


    # =====================================================
    # 11. VIDER LE PANIER DES SERVICES
    # =====================================================

    session.pop(
        "panier_services",
        None
    )


    # =====================================================
    # 12. REDIRIGER VERS LA PAGE DE SUCCÈS
    # =====================================================

    return redirect(

        url_for(

            "commande_succes",

            id_commande=
                commande["id_commande"]

        )

    )



@app.route(
    "/commande/succes/<int:id_commande>"
)
def commande_succes(id_commande):

    if not role_autorise("client"):
        return (
            "Accès refusé.",
            403
        )

    return render_template(
        "commande_succes.html",
        id_commande=id_commande
    )




# =========================================================
# MES COMMANDES - CLIENT
# =========================================================

@app.route("/mes-commandes")
def mes_commandes():

    # ---------------------------------------------------------
    # Vérifier que l'utilisateur est bien un client
    # ---------------------------------------------------------

    if not role_autorise("client"):

        return (
            "Accès refusé : cette page est réservée aux clients.",
            403
        )


    # ---------------------------------------------------------
    # Récupérer les commandes du client depuis FastAPI
    # ---------------------------------------------------------

    reponse = api_get(
        f"{API_URL}/mes-commandes"
    )


    # ---------------------------------------------------------
    # Vérifier la réponse de l'API
    # ---------------------------------------------------------

    if reponse.status_code != 200:

        try:

            erreur = reponse.json().get(
                "detail",
                "Impossible de récupérer vos commandes."
            )

        except Exception:

            erreur = (
                "Impossible de récupérer vos commandes."
            )

        return (
            f"Erreur : {erreur}",
            reponse.status_code
        )


    # ---------------------------------------------------------
    # Convertir la réponse en liste Python
    # ---------------------------------------------------------

    commandes = reponse.json()


    # =========================================================
    # RÉCUPÉRER LE NOMBRE DE MESSAGES NON LUS
    # POUR CHAQUE COMMANDE
    # =========================================================

    for commande in commandes:

        # -----------------------------------------------------
        # Par défaut :
        # aucun message non lu
        # -----------------------------------------------------

        commande["messages_non_lus"] = 0


        # -----------------------------------------------------
        # Identifiant de la commande
        # -----------------------------------------------------

        id_commande = commande.get(
            "id_commande"
        )


        # -----------------------------------------------------
        # Si l'identifiant est disponible,
        # interroger FastAPI
        # -----------------------------------------------------

        if id_commande is not None:

            try:

                reponse_messages = api_get(

                    f"{API_URL}/commandes/"
                    f"{id_commande}/messages/non-lus"

                )


                # -------------------------------------------------
                # Vérifier que FastAPI a répondu correctement
                # -------------------------------------------------

                if reponse_messages.status_code == 200:

                    donnees_messages = (
                        reponse_messages.json()
                    )


                    # ---------------------------------------------
                    # Récupérer le nombre de messages non lus
                    # ---------------------------------------------

                    commande["messages_non_lus"] = int(

                        donnees_messages.get(
                            "messages_non_lus",
                            0
                        )

                    )


            except Exception as erreur:

                # -------------------------------------------------
                # Une erreur sur une commande ne doit pas
                # empêcher l'affichage de toutes les commandes.
                # -------------------------------------------------

                print(

                    "Erreur lors de la récupération des "
                    f"messages non lus de la commande "
                    f"{id_commande} : {erreur}"

                )

                commande["messages_non_lus"] = 0


    # =========================================================
    # AFFICHER LA PAGE
    # =========================================================

    return render_template(

        "mes_commandes.html",

        commandes=commandes

    )

# =========================================================
# ANNULER UNE COMMANDE DU CLIENT
# =========================================================

@app.route(
    "/mes-commandes/<int:id_commande>/annuler",
    methods=["DELETE"]
)
def annuler_commande(id_commande):

    if "access_token" not in session:
        return {
            "detail": "Utilisateur non connecté."
        }, 401

    token = session["access_token"]

    reponse = api_delete(
        f"{API_URL}/mes-commandes/"
        f"{id_commande}/annuler",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    try:
        resultat = reponse.json()

    except Exception:
        resultat = {
            "detail": "Réponse invalide du serveur."
        }

    return resultat, reponse.status_code


# =========================================================
# ENVOYER UN MESSAGE SUR UNE COMMANDE - CLIENT
# =========================================================

@app.route(
    "/mes-commandes/<int:id_commande>/messages",
    methods=["POST"]
)
def envoyer_message_client(id_commande):

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est bien un client
    # -----------------------------------------------------

    if not role_autorise("client"):
        return jsonify({
            "detail": (
                "Accès refusé : cette action est réservée "
                "aux clients."
            )
        }), 403

    # -----------------------------------------------------
    # Récupérer les données envoyées par JavaScript
    # -----------------------------------------------------

    donnees = request.get_json()

    if not donnees:
        return jsonify({
            "detail": "Aucune donnée reçue."
        }), 400

    message = donnees.get("message", "").strip()

    # -----------------------------------------------------
    # Vérifier que le message n'est pas vide
    # -----------------------------------------------------

    if not message:
        return jsonify({
            "detail": "Le message ne peut pas être vide."
        }), 400

    # -----------------------------------------------------
    # Envoyer le message à FastAPI
    # -----------------------------------------------------

    reponse = api_post(
        f"{API_URL}/mes-commandes/"
        f"{id_commande}/messages",
        json={
            "message": message
        }
    )

    # -----------------------------------------------------
    # Récupérer la réponse de FastAPI
    # -----------------------------------------------------

    try:
        resultat = reponse.json()

    except Exception:
        resultat = {
            "detail": (
                "Réponse invalide du serveur."
            )
        }

    return jsonify(resultat), reponse.status_code



# =========================================================
# MARQUER UN MESSAGE COMME LU - CLIENT
# =========================================================

@app.route(
    "/messages/<int:id_message>/lu",
    methods=["PUT"]
)
def marquer_message_lu_client(id_message):

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est bien un client
    # -----------------------------------------------------

    if not role_autorise("client"):
        return jsonify({
            "detail": (
                "Accès refusé : cette action est réservée "
                "aux clients."
            )
        }), 403

    # -----------------------------------------------------
    # Envoyer la demande à FastAPI
    # -----------------------------------------------------

    reponse = api_put(
        f"{API_URL}/messages/{id_message}/lu"
    )

    # -----------------------------------------------------
    # Récupérer la réponse
    # -----------------------------------------------------

    try:
        resultat = reponse.json()

    except Exception:
        resultat = {
            "detail": (
                "Réponse invalide du serveur."
            )
        }

    return jsonify(resultat), reponse.status_code



# =========================================================
# SUPPRIMER UN MESSAGE - CLIENT
# =========================================================

@app.route(
    "/messages/<int:id_message>",
    methods=["DELETE"]
)
def supprimer_message_client(id_message):

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est bien un client
    # -----------------------------------------------------

    if not role_autorise("client"):
        return jsonify({
            "detail": (
                "Accès refusé : cette action est réservée "
                "aux clients."
            )
        }), 403

    # -----------------------------------------------------
    # Envoyer la demande à FastAPI
    # -----------------------------------------------------

    reponse = api_delete(
        f"{API_URL}/messages/{id_message}"
    )

    # -----------------------------------------------------
    # Récupérer la réponse
    # -----------------------------------------------------

    try:
        resultat = reponse.json()

    except Exception:
        resultat = {
            "detail": (
                "Réponse invalide du serveur."
            )
        }

    return jsonify(resultat), reponse.status_code



# =========================================================
# PAGE ADMIN : GESTION DE LA PAGE D'ACCUEIL
# =========================================================

@app.route("/gestion-accueil")
def gestion_accueil():

    # Seul l'administrateur peut accéder à cette page
    if not role_autorise("admin"):
        return "Accès refusé : vous n'avez pas l'autorisation d'accéder à cette page.", 403


    # -----------------------------------------------------
    # RÉCUPÉRER LES PHOTOS
    # -----------------------------------------------------

    photos = []

    try:

        response = api_get(
            f"{API_URL}/accueil/photos",
            timeout=5
        )

        if response.status_code == 200:
            photos = response.json()

    except requests.RequestException:

        photos = []


    # -----------------------------------------------------
    # RÉCUPÉRER LES PUBLICITÉS
    # -----------------------------------------------------

    publicites = []

    try:

        response = api_get(
            f"{API_URL}/accueil/publicites",
            timeout=5
        )

        if response.status_code == 200:
            publicites = response.json()

    except requests.RequestException:

        publicites = []


    enrichir_photos_accueil(photos)
    enrichir_publicites(publicites)

    return render_template(
        "gestion_accueil.html",
        photos=photos,
        publicites=publicites
    )



# =========================================================
# AJOUTER UNE PHOTO D'ACCUEIL
# =========================================================

@app.route(
    "/gestion-accueil/photo/ajouter",
    methods=["POST"]
)
def ajouter_photo_accueil():

    if not role_autorise("admin"):
        return "Accès refusé.", 403

    fichier = request.files.get("photo")

    if not fichier or fichier.filename == "":
        return redirect(url_for("gestion_accueil"))

    if not extension_autorisee(
        fichier.filename,
        EXTENSIONS_PHOTO_ACCUEIL
    ):
        return (
            "Format de photo non autorisé.",
            400
        )

    # -----------------------------------------------------
    # TÉLÉVERSEMENT (Cloudinary en production)
    # -----------------------------------------------------

    try:

        nom_image = televerser_media(
            fichier,
            "accueil_photos",
            "image"
        )

    except ErreurMedia as erreur:

        return (str(erreur), 500)

    # -----------------------------------------------------
    # ENREGISTRER DANS LA BASE VIA FASTAPI
    # -----------------------------------------------------

    try:

        response = api_post(
            "/accueil/photos",
            params={
                "nom_fichier": nom_image
            }
        )

    except SessionExpiree:

        supprimer_media(nom_image, "accueil_photos", local=True)

        raise

    except requests.RequestException:

        supprimer_media(nom_image, "accueil_photos", local=True)

        return (
            "Impossible de contacter le serveur. "
            "Réessayez dans quelques instants.",
            503
        )

    if response.status_code not in [200, 201]:

        # Si l'API échoue, supprimer le fichier
        supprimer_media(nom_image, "accueil_photos", local=True)

        return (
            f"Erreur lors de l'enregistrement : "
            f"{response.text}",
            500
        )

    return redirect(url_for("gestion_accueil"))


# =========================================================
# SUPPRIMER UNE PHOTO D'ACCUEIL
# =========================================================

@app.route(
    "/gestion-accueil/photo/<int:id_photo>/supprimer",
    methods=["POST"]
)
def supprimer_photo_accueil(id_photo):

    if not role_autorise("admin"):
        return "Accès refusé.", 403

    # -----------------------------------------------------
    # Récupérer les informations avant suppression
    # -----------------------------------------------------

    photos = []

    try:

        response = api_get("/accueil/photos")

        if response.status_code == 200:
            photos = response.json()

    except requests.RequestException:

        pass

    photo = next(
        (
            p for p in photos
            if p["id_photo"] == id_photo
        ),
        None
    )

    # -----------------------------------------------------
    # Supprimer dans l'API
    # -----------------------------------------------------

    response = api_delete(f"/accueil/photos/{id_photo}")

    if response.status_code != 200:

        return (
            "Erreur lors de la suppression.",
            500
        )

    # -----------------------------------------------------
    # Supprimer également le fichier (Cloudinary ou local)
    # -----------------------------------------------------

    if photo:

        supprimer_media(
            photo.get("nom_fichier"),
            "accueil_photos",
            local=True
        )

    return redirect(url_for("gestion_accueil"))


# =========================================================
# AJOUTER UNE PUBLICITÉ VIDÉO
# =========================================================

@app.route(
    "/gestion-accueil/publicite/ajouter",
    methods=["POST"]
)
def ajouter_publicite():

    if not role_autorise("admin"):
        return "Accès refusé.", 403

    fichier = request.files.get("video")

    titre = request.form.get(
        "titre",
        ""
    ).strip()

    if not fichier or fichier.filename == "":
        return redirect(url_for("gestion_accueil"))

    if not extension_autorisee(
        fichier.filename,
        EXTENSIONS_VIDEO_ACCUEIL
    ):
        return (
            "Format vidéo non autorisé.",
            400
        )

    # -----------------------------------------------------
    # TÉLÉVERSEMENT (Cloudinary en production)
    # -----------------------------------------------------

    try:

        nom_video = televerser_media(
            fichier,
            "accueil_videos",
            "video"
        )

    except ErreurMedia as erreur:

        return (str(erreur), 500)

    # -----------------------------------------------------
    # ENREGISTRER DANS LA BASE VIA FASTAPI
    # -----------------------------------------------------

    try:

        response = api_post(
            "/accueil/publicites",
            params={
                "nom_fichier": nom_video,
                "titre": titre or None
            }
        )

    except SessionExpiree:

        supprimer_media(nom_video, "accueil_videos", local=True)

        raise

    except requests.RequestException:

        supprimer_media(nom_video, "accueil_videos", local=True)

        return (
            "Impossible de contacter le serveur. "
            "Réessayez dans quelques instants.",
            503
        )

    if response.status_code not in [200, 201]:

        supprimer_media(nom_video, "accueil_videos", local=True)

        return (
            f"Erreur : {response.text}",
            500
        )

    return redirect(url_for("gestion_accueil"))


# =========================================================
# SUPPRIMER UNE PUBLICITÉ
# =========================================================

@app.route(
    "/gestion-accueil/publicite/<int:id_publicite>/supprimer",
    methods=["POST"]
)
def supprimer_publicite(id_publicite):

    if not role_autorise("admin"):
        return "Accès refusé.", 403

    # -----------------------------------------------------
    # Récupérer la publicité
    # -----------------------------------------------------

    publicites = []

    try:

        response = api_get("/accueil/publicites")

        if response.status_code == 200:
            publicites = response.json()

    except requests.RequestException:

        pass

    publicite = next(
        (
            p for p in publicites
            if p["id_publicite"] == id_publicite
        ),
        None
    )

    # -----------------------------------------------------
    # Supprimer de la base
    # -----------------------------------------------------

    response = api_delete(f"/accueil/publicites/{id_publicite}")

    if response.status_code != 200:

        return (
            "Erreur lors de la suppression.",
            500
        )

    # -----------------------------------------------------
    # Supprimer le fichier (Cloudinary ou local)
    # -----------------------------------------------------

    if publicite:

        supprimer_media(
            publicite.get("nom_fichier"),
            "accueil_videos",
            local=True
        )

    return redirect(url_for("gestion_accueil"))


# =========================================================
# =========================================================
# MESSAGERIE D'UNE COMMANDE
# =========================================================
# =========================================================


# =========================================================
# AFFICHER LA MESSAGERIE D'UNE COMMANDE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/messages"
)
def messages_commande(id_commande):
    """
    Affiche la messagerie associée à une commande.

    Cette page peut être utilisée par :
        - le client propriétaire de la commande
        - le vendeur
        - l'administrateur

    Lors de l'ouverture de la conversation, FastAPI
    marque automatiquement comme lus les messages
    destinés à l'utilisateur connecté.
    """

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est connecté
    # -----------------------------------------------------

    if "access_token" not in session:

        return redirect(
            url_for("login")
        )


    # -----------------------------------------------------
    # Récupérer les messages depuis FastAPI
    #
    # IMPORTANT :
    # L'endpoint FastAPI GET /commandes/{id_commande}/messages
    # doit automatiquement marquer comme lus les messages
    # destinés à l'utilisateur connecté.
    # -----------------------------------------------------

    try:

        reponse = api_get(
            f"{API_URL}/commandes/"
            f"{id_commande}/messages"
        )

    except Exception as erreur:

        print(
            "Erreur lors de la récupération "
            "des messages :",
            erreur
        )

        return (
            "Impossible de contacter FastAPI.",
            500
        )


    # -----------------------------------------------------
    # Vérifier la réponse de FastAPI
    # -----------------------------------------------------

    if reponse.status_code != 200:

        try:

            erreur = reponse.json().get(
                "detail",
                "Impossible de charger les messages."
            )

        except Exception:

            erreur = (
                "Impossible de charger les messages."
            )

        return (
            f"Erreur lors du chargement des messages : "
            f"{erreur}",
            reponse.status_code
        )


    # -----------------------------------------------------
    # Transformer la réponse en JSON
    # -----------------------------------------------------

    messages = reponse.json()


    # -----------------------------------------------------
    # Afficher la page de messagerie
    # -----------------------------------------------------

    return render_template(
        "messages.html",
        messages=messages,
        id_commande=id_commande,
        API_URL=API_PUBLIC_URL
    )

# =========================================================
# ENVOYER UN MESSAGE TEXTE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/messages/envoyer",
    methods=["POST"]
)
def envoyer_message(id_commande):
    """
    Envoie un message texte à propos d'une commande.
    """

    # -----------------------------------------------------
    # Récupérer le texte
    # -----------------------------------------------------

    texte = request.form.get(
        "message",
        ""
    ).strip()

    # -----------------------------------------------------
    # Vérifier que le message n'est pas vide
    # -----------------------------------------------------

    if not texte:

        return redirect(
            url_for(
                "messages_commande",
                id_commande=id_commande
            )
        )

    # -----------------------------------------------------
    # Envoyer le message à FastAPI
    # -----------------------------------------------------

    reponse = api_post(
        f"{API_URL}/commandes/{id_commande}/messages",
        json={
            "message": texte
        },
        headers=api_headers()
    )

    # -----------------------------------------------------
    # Vérifier la réponse
    # -----------------------------------------------------

    if reponse.status_code not in [200, 201]:

        return (
            f"Erreur lors de l'envoi du message : "
            f"{reponse.text}",
            reponse.status_code
        )

    # -----------------------------------------------------
    # Retourner à la messagerie
    # -----------------------------------------------------

    return redirect(
        url_for(
            "messages_commande",
            id_commande=id_commande
        )
    )


# =========================================================
# ENVOYER UN MESSAGE VOCAL
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/messages/vocal",
    methods=["POST"]
)
def envoyer_message_vocal(id_commande):

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est connecté
    # -----------------------------------------------------

    if "access_token" not in session:

        return (
            "Utilisateur non connecté",
            401
        )


    # -----------------------------------------------------
    # Vérifier que le fichier existe
    #
    # IMPORTANT :
    # Le JavaScript envoie maintenant le fichier sous
    # le nom "fichier".
    # -----------------------------------------------------

    if "fichier" not in request.files:

        return (
            "Aucun fichier vocal reçu par Flask.",
            400
        )


    fichier_audio = request.files["fichier"]


    # -----------------------------------------------------
    # Vérifier le nom du fichier
    # -----------------------------------------------------

    if not fichier_audio.filename:

        return (
            "Le fichier vocal n'a pas de nom.",
            400
        )


    # -----------------------------------------------------
    # Préparer le fichier pour FastAPI
    # -----------------------------------------------------

    fichiers = {

        "fichier": (
            fichier_audio.filename,
            fichier_audio.stream,
            fichier_audio.mimetype
        )

    }


    # -----------------------------------------------------
    # Envoyer le fichier à FastAPI
    # -----------------------------------------------------

    try:

        reponse = api_post(

            f"{API_URL}/commandes/"
            f"{id_commande}/messages/vocal",

            files=fichiers,

            headers=api_headers()

        )


    except requests.exceptions.RequestException as erreur:

        print(
            "ERREUR DE CONNEXION FASTAPI :",
            erreur
        )

        return (
            "Impossible de contacter FastAPI : "
            + str(erreur),
            500
        )


    # -----------------------------------------------------
    # Afficher la réponse dans le terminal Flask
    # -----------------------------------------------------

    print(
        "Réponse FastAPI vocal :",
        reponse.status_code,
        reponse.text
    )


    # -----------------------------------------------------
    # Vérifier la réponse
    # -----------------------------------------------------

    if reponse.status_code not in [200, 201]:

        return (
            "Erreur lors de l'envoi du message vocal : "
            + reponse.text,
            reponse.status_code
        )


    # -----------------------------------------------------
    # Succès
    # -----------------------------------------------------

    return (
        "Message vocal envoyé avec succès.",
        200
    )


# =========================================================
# MARQUER UN MESSAGE COMME LU
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/messages/"
    "<int:id_message>/lu",
    methods=["POST"]
)
def marquer_message_lu(id_commande, id_message):
    """
    Marque un message comme lu.

    Le contrôle des droits est effectué par FastAPI.
    """

    # -----------------------------------------------------
    # Envoyer la demande à FastAPI
    # -----------------------------------------------------

    reponse = api_put(
        f"{API_URL}/commandes/"
        f"{id_commande}/messages/"
        f"{id_message}/lu",
        json={
            "lu": True
        },
        headers=api_headers()
    )

    # -----------------------------------------------------
    # Vérifier la réponse
    # -----------------------------------------------------

    if reponse.status_code not in [200, 201]:

        print(
            "Erreur lors du marquage du message :",
            reponse.text
        )

    # -----------------------------------------------------
    # Retourner à la messagerie
    # -----------------------------------------------------

    return redirect(
        url_for(
            "messages_commande",
            id_commande=id_commande
        )
    )


# =========================================================
# SUPPRIMER UN MESSAGE
# =========================================================

@app.route(
    "/commandes/<int:id_commande>/messages/"
    "<int:id_message>/supprimer",
    methods=["POST"]
)
def supprimer_message(id_commande, id_message):
    """
    Supprime un message.

    FastAPI vérifie que l'utilisateur a le droit
    de supprimer ce message.
    """

    # -----------------------------------------------------
    # Envoyer la demande à FastAPI
    # -----------------------------------------------------

    reponse = api_delete(
        f"{API_URL}/commandes/"
        f"{id_commande}/messages/"
        f"{id_message}",
        headers=api_headers()
    )

    # -----------------------------------------------------
    # Vérifier la réponse
    # -----------------------------------------------------

    if reponse.status_code != 200:

        print(
            "Erreur lors de la suppression du message :",
            reponse.text
        )

    # -----------------------------------------------------
    # Retourner à la messagerie
    # -----------------------------------------------------

    return redirect(
        url_for(
            "messages_commande",
            id_commande=id_commande
        )
    )

# =========================================================
# NOMBRE DE MESSAGES NON LUS
# =========================================================

@app.route(
    "/messages/non-lus/count",
    methods=["GET"]
)
def nombre_messages_non_lus():

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est connecté
    # -----------------------------------------------------

    if "access_token" not in session:

        return jsonify({
            "nombre_non_lus": 0
        })


    try:

        # -------------------------------------------------
        # Demander le nombre à FastAPI
        # -------------------------------------------------

        reponse = api_get(
            f"{API_URL}/messages/non-lus",
            headers=api_headers()
        )


        # -------------------------------------------------
        # FastAPI a répondu correctement
        # -------------------------------------------------

        if reponse.status_code == 200:

            return jsonify(
                reponse.json()
            )


        # -------------------------------------------------
        # En cas d'erreur FastAPI
        # -------------------------------------------------

        print(
            "Erreur FastAPI messages non lus :",
            reponse.status_code,
            reponse.text
        )


        return jsonify({
            "nombre_non_lus": 0
        })


    except requests.exceptions.RequestException as erreur:

        print(
            "Erreur connexion FastAPI "
            "messages non lus :",
            erreur
        )


        return jsonify({
            "nombre_non_lus": 0
        })


# =========================================================
# FIN DE LA MESSAGERIE
# =========================================================


# =========================================================
# PAGE : TOUTES LES CONVERSATIONS
# =========================================================

@app.route(
    "/mes-messages",
    methods=["GET"]
)
def mes_messages():

    # ---------------------------------------------------------
    # Vérifier que l'utilisateur est connecté
    # ---------------------------------------------------------

    if "access_token" not in session:

        return redirect(
            url_for("login")
        )


    # ---------------------------------------------------------
    # Appeler FastAPI
    # ---------------------------------------------------------

    try:

        reponse = api_get(
            f"{API_URL}/messages/conversations",
            headers=api_headers()
        )

    except requests.exceptions.RequestException as erreur:

        print(
            "Erreur connexion FastAPI conversations :",
            erreur
        )

        return (
            "Impossible de contacter FastAPI : "
            + str(erreur),
            500
        )


    # ---------------------------------------------------------
    # Vérifier la réponse
    # ---------------------------------------------------------

    if reponse.status_code != 200:

        print(
            "Erreur FastAPI conversations :",
            reponse.status_code,
            reponse.text
        )

        return (
            "Erreur lors du chargement "
            "des conversations : "
            + reponse.text,
            reponse.status_code
        )


    # ---------------------------------------------------------
    # Récupérer les données
    # ---------------------------------------------------------

    donnees = reponse.json()


    # ---------------------------------------------------------
    # Afficher la page
    # ---------------------------------------------------------

    return render_template(
        "mes_messages.html",
        conversations=
            donnees.get(
                "conversations",
                []
            ),
        nombre_non_lus=
            donnees.get(
                "nombre_non_lus",
                0
            )
    )

# =========================================================
# MODIFIER LA QUANTITÉ D'UN PRODUIT DANS LE PANIER
# =========================================================

@app.route(
    "/panier/modifier/<int:id_produit>",
    methods=["POST"]
)
def modifier_panier(id_produit):

    # -----------------------------------------------------
    # Vérification du rôle
    # -----------------------------------------------------

    if not role_autorise("client"):
        return (
            "Accès refusé : seuls les clients "
            "peuvent modifier le panier.",
            403
        )

    # -----------------------------------------------------
    # Récupération du panier des produits
    # -----------------------------------------------------

    panier = session.get(
        "panier",
        {}
    )

    id_produit_str = str(
        id_produit
    )

    # -----------------------------------------------------
    # Vérifier que le produit existe dans le panier
    # -----------------------------------------------------

    if id_produit_str not in panier:
        return (
            "Ce produit n'est pas présent "
            "dans votre panier.",
            404
        )

    # -----------------------------------------------------
    # Récupérer l'action
    # -----------------------------------------------------

    action = request.form.get(
        "action"
    )

    # -----------------------------------------------------
    # Quantité actuelle
    # -----------------------------------------------------

    quantite_actuelle = int(
        panier[id_produit_str]
    )

    # -----------------------------------------------------
    # AUGMENTER
    # -----------------------------------------------------

    if action == "plus":

        quantite_actuelle += 1

        panier[id_produit_str] = (
            quantite_actuelle
        )

    # -----------------------------------------------------
    # DIMINUER
    # -----------------------------------------------------

    elif action == "moins":

        quantite_actuelle -= 1

        # Si la quantité arrive à zéro,
        # on retire le produit du panier.

        if quantite_actuelle <= 0:

            del panier[
                id_produit_str
            ]

        else:

            panier[
                id_produit_str
            ] = quantite_actuelle

    # -----------------------------------------------------
    # Action inconnue
    # -----------------------------------------------------

    else:

        return (
            "Action de panier inconnue.",
            400
        )

    # -----------------------------------------------------
    # Sauvegarde du panier
    # -----------------------------------------------------

    session["panier"] = panier
    session.modified = True

    # -----------------------------------------------------
    # Retour vers le panier
    # -----------------------------------------------------

    return redirect(
        url_for("panier")
    )


# =========================================================
# SUPPRIMER UN PRODUIT DU PANIER
# =========================================================

@app.route(
    "/panier/supprimer/<int:id_produit>",
    methods=["POST"]
)
def supprimer_du_panier(id_produit):

    # -----------------------------------------------------
    # Vérification du rôle
    # -----------------------------------------------------

    if not role_autorise("client"):
        return (
            "Accès refusé : seuls les clients "
            "peuvent modifier le panier.",
            403
        )

    # -----------------------------------------------------
    # Récupération du panier des produits
    # -----------------------------------------------------

    panier = session.get(
        "panier",
        {}
    )

    # -----------------------------------------------------
    # Identifiant sous forme de chaîne
    # -----------------------------------------------------

    id_produit_str = str(
        id_produit
    )

    # -----------------------------------------------------
    # Suppression du produit
    # -----------------------------------------------------

    if id_produit_str in panier:

        del panier[
            id_produit_str
        ]

    # -----------------------------------------------------
    # Sauvegarde du panier
    # -----------------------------------------------------

    session["panier"] = panier
    session.modified = True

    # -----------------------------------------------------
    # Retour vers le panier
    # -----------------------------------------------------

    return redirect(
        url_for("panier")
    )






# =========================================================
# DASHBOARD ADMIN / VENDEUR
# =========================================================

@app.route("/dashboard")
def dashboard():

    # -----------------------------------------------------
    # Vérification du rôle
    # -----------------------------------------------------

    if not role_autorise("admin", "vendeur"):
        return (
            "Accès refusé : le tableau de bord "
            "est réservé aux administrateurs "
            "et aux vendeurs.",
            403
        )

    # -----------------------------------------------------
    # Appel de l'API FastAPI
    # -----------------------------------------------------

    try:

        reponse = api_get(
            f"{API_URL}/dashboard/statistiques",
            timeout=5
        )

    except Exception as erreur:

        return (
            "Impossible de communiquer avec "
            f"le serveur : {erreur}",
            500
        )

    # -----------------------------------------------------
    # Vérification de la réponse
    # -----------------------------------------------------

    if reponse.status_code != 200:

        try:

            detail = reponse.json().get(
                "detail",
                "Impossible de récupérer "
                "les statistiques."
            )

        except Exception:

            detail = (
                "Impossible de récupérer "
                "les statistiques."
            )

        return (
            f"Erreur : {detail}",
            reponse.status_code
        )

    # -----------------------------------------------------
    # Récupération des statistiques
    # -----------------------------------------------------

    statistiques = reponse.json()

    # -----------------------------------------------------
    # Affichage
    # -----------------------------------------------------

    return render_template(
        "dashboard.html",
        statistiques=statistiques
    )


# =========================================================
# NOTIFICATIONS - FLASK
# =========================================================

@app.route("/notifications")
def notifications():

    if "access_token" not in session:
        return jsonify({
            "nombre_non_lues": 0,
            "notifications": []
        })


    try:

        reponse = api_get(
            f"{API_URL}/notifications",
            timeout=5
        )

    except Exception:

        return jsonify({
            "nombre_non_lues": 0,
            "notifications": []
        })


    if reponse.status_code != 200:

        return jsonify({
            "nombre_non_lues": 0,
            "notifications": []
        })


    return jsonify(
        reponse.json()
    )


# =========================================================
# MARQUER UNE NOTIFICATION COMME LUE
# =========================================================

@app.route(
    "/notifications/<int:id_notification>/lue",
    methods=["PUT"]
)
def notification_lue(id_notification):

    if "access_token" not in session:

        return jsonify({
            "success": False
        }), 401


    reponse = api_put(

        f"{API_URL}/notifications/"
        f"{id_notification}/lue",

        headers=api_headers(),

        timeout=5
    )


    return (
        jsonify(reponse.json()),
        reponse.status_code
    )


# =========================================================
# TOUT MARQUER COMME LU
# =========================================================

@app.route(
    "/notifications/toutes/lues",
    methods=["PUT"]
)
def notifications_toutes_lues():

    if "access_token" not in session:

        return jsonify({
            "success": False
        }), 401


    reponse = api_put(

        f"{API_URL}/notifications/toutes/lues",

        headers=api_headers(),

        timeout=5
    )


    return (
        jsonify(reponse.json()),
        reponse.status_code
    )


# =========================================================
# LANCEMENT DE L'APPLICATION
# =========================================================

if __name__ == "__main__":

    # En production, Render lance l'application avec gunicorn :
    #     gunicorn app:app
    app.run(
        host="0.0.0.0" if EN_PRODUCTION else "127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=not EN_PRODUCTION
    )
