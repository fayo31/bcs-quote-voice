"""
BIEN CHEZ SOI - Configuration
Variables d'environnement, tarification complète et constantes
Les Entreprises REMES Inc. / Fiducie Ramahime
"""

import os
import math
from pathlib import Path
from dotenv import load_dotenv

# Charger .env depuis le dossier du projet (ou .env.example si .env absent)
_project_dir = Path(__file__).resolve().parent
_env_path = _project_dir / '.env'
if not _env_path.exists():
    _env_path = _project_dir / '.env.example'
load_dotenv(_env_path, override=True)
# Pour débogage au démarrage (chemin uniquement, pas les valeurs)
CONFIG_LOADED_FROM = str(_env_path)


class Config:
    # ============================================================
    # API KEYS
    # ============================================================
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')

    # Notion Database IDs
    NOTION_SOUMISSIONS_DB = os.getenv('NOTION_SOUMISSIONS_DB')
    NOTION_CONTACTS_DB = os.getenv('NOTION_CONTACTS_DB')

    # Email (SMTP)
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

    # ============================================================
    # BIEN CHEZ SOI — Informations entreprise
    # ============================================================
    BCS_NAME = 'Bien Chez Soi'
    BCS_LEGAL_NAME = 'Les Entreprises REMES Inc.'
    BCS_EMAIL = os.getenv('BCS_EMAIL', 'info@bienchezsoi.ca')
    BCS_PHONE = os.getenv('BCS_PHONE', '438-XXX-XXXX')
    BCS_NEQ = os.getenv('BCS_NEQ', 'XXXXXXXXXX')
    BCS_ADDRESS = os.getenv('BCS_ADDRESS', 'Brossard, Québec')
    BCS_WEBSITE = os.getenv('BCS_WEBSITE', 'www.bienchezsoi.ca')

    # ============================================================
    # TAXES QUÉBEC
    # ============================================================
    TPS_RATE = 0.05
    TVQ_RATE = 0.09975

    # ============================================================
    # TARIFICATION — Prix affiché : 50 $/h
    # ============================================================

    # --- Régulier sans contrat (un seul payeur) ---
    TARIF_REGULIER = {
        "1h": {"heures": 1, "prix": 65.00, "taux_effectif": 65.00},
        "2h": {"heures": 2, "prix": 120.00, "taux_effectif": 60.00},
        "3h": {"heures": 3, "prix": 150.00, "taux_effectif": 50.00},
        "4h": {"heures": 4, "prix": 180.00, "taux_effectif": 45.00},
    }
    # 4h+ : 180$ + 45$/h additionnel
    TARIF_BASE_4H = 180.00
    TARIF_HEURE_ADDITIONNEL = 45.00
    TARIF_AFFICHE = 50.00  # prix marché

    # --- Services à la carte (Animation & Compagnie) ---
    # Base 50$/h, minimum 2h par visite
    SERVICES_CARTE = {
        "Visite de compagnie": {"duree_min": 2, "tarif": 100.00},
        "Bingo / jeux de société / activités cognitives": {"duree_min": 2, "tarif": 100.00},
        "Promenade / sortie divertissement": {"duree_min": 2, "tarif": 100.00},
        "Animation thématique": {"duree_min": 2, "tarif": 100.00},
        "Accompagnement événement / sortie spéciale": {"duree_min": 3, "tarif": 150.00},
    }

    # --- Forfaits groupe RPA (Soins & Animation) ---
    GROUPE_TAUX_HORAIRE = 50.00
    GROUPE_BASE_HEURES = 4
    GROUPE_BASE_PRIX = 200.00
    GROUPE_MIN_PERSONNES = 5
    GROUPE_MAX_PERSONNES = 20

    # --- Service partagé voisins RPA ---
    PARTAGE_BLOC_HEURES = 4
    PARTAGE_BLOC_PRIX = 200.00
    PARTAGE_MAX_VOISINS = 4
    PARTAGE_MIN_VOISINS = 2

    # --- Contrats corporatifs ---
    CONTRATS = {
        "hebdomadaire": {"min_heures_sem": 4, "taux": 45.00, "total_min": 180.00},
        "mensuel": {"min_heures_mois": 16, "taux": 43.00, "total_min": 688.00},
        "annuel": {"min_heures_mois": 16, "taux": 40.00, "total_annuel": 7680.00},
    }

    # --- Forfaits récurrents individuels (mensuel) ---
    FORFAITS_RECURRENTS = {
        "Essentiel": {"frequence": "1x/semaine", "heures_mois": 8, "prix_mois": 360.00, "taux": 45.00},
        "Confort": {"frequence": "2x/semaine", "heures_mois": 16, "prix_mois": 680.00, "taux": 42.50},
        "Premium": {"frequence": "3x/semaine", "heures_mois": 24, "prix_mois": 960.00, "taux": 40.00},
    }

    # ============================================================
    # CATÉGORIES DE SERVICES
    # ============================================================
    CATEGORIES = [
        "Soins & Hygiène",
        "Animation & Compagnie",
        "Visite de compagnie",
        "Accompagnement sortie",
        "Promenade / divertissement",
        "Activités cognitives (bingo, jeux)",
        "Animation thématique",
        "Assistance alimentaire",
        "Soins de confort",
        "Autre",
    ]

    # ============================================================
    # TYPES DE SERVICE (pour facturation)
    # ============================================================
    TYPES_SERVICE = [
        "Régulier (sans contrat)",
        "À la carte (Animation)",
        "Groupe Soins RPA",
        "Groupe Animation RPA",
        "Partagé voisins RPA",
        "Contrat corporatif",
        "Forfait récurrent",
    ]

    # ============================================================
    # ADD-ONS / SUPPLÉMENTS
    # ============================================================
    ADDONS = {
        "urgence": {"nom": "Urgence même jour", "prix": 15.00},
        "hors_horaire": {"nom": "Hors horaire (avant 7h / après 20h)", "prix": 10.00},
        "fin_semaine": {"nom": "Fin de semaine / jour férié", "prix": 10.00},
        "deplacement_extra": {"nom": "Déplacement hors zone", "prix": 15.00},
        "materiel": {"nom": "Matériel / fournitures spéciales", "prix": 10.00},
    }

    # ============================================================
    # STATUTS SOUMISSION
    # ============================================================
    STATUTS = [
        "Brouillon",
        "Envoyée",
        "Acceptée",
        "Refusée",
        "Expirée",
        "Complétée",
    ]

    # ============================================================
    # LANGUES
    # ============================================================
    LANGUES = {
        "fr": {
            "app_title": "Bien Chez Soi",
            "app_subtitle": "Soumission vocale",
            "btn_record": "Appuyer pour dicter",
            "btn_stop": "Arrêter",
            "btn_pdf": "Télécharger PDF",
            "btn_send": "Envoyer (Notion + Courriel)",
            "btn_new": "Nouvelle soumission",
            "label_client": "Client",
            "label_service": "Service",
            "label_options": "Options",
            "label_totals": "Totaux",
            "label_name": "Nom",
            "label_phone": "Téléphone",
            "label_email": "Courriel",
            "label_address": "Adresse du service",
            "label_description": "Description",
            "label_category": "Catégorie",
            "label_type": "Type de service",
            "label_hours": "Nombre d'heures",
            "label_persons": "Nombre de personnes",
            "tps": "TPS (5%)",
            "tvq": "TVQ (9.975%)",
            "total": "TOTAL",
            "sous_total": "Sous-total",
            "success_msg": "Soumission envoyée avec succès!",
            "conditions_title": "CONDITIONS",
            "signature_title": "SIGNATURE DU CLIENT",
            "history_title": "Historique",
        },
        "en": {
            "app_title": "Bien Chez Soi",
            "app_subtitle": "Voice Quote",
            "btn_record": "Tap to dictate",
            "btn_stop": "Stop",
            "btn_pdf": "Download PDF",
            "btn_send": "Send (Notion + Email)",
            "btn_new": "New quote",
            "label_client": "Client",
            "label_service": "Service",
            "label_options": "Options",
            "label_totals": "Totals",
            "label_name": "Name",
            "label_phone": "Phone",
            "label_email": "Email",
            "label_address": "Service address",
            "label_description": "Description",
            "label_category": "Category",
            "label_type": "Service type",
            "label_hours": "Number of hours",
            "label_persons": "Number of persons",
            "tps": "GST (5%)",
            "tvq": "QST (9.975%)",
            "total": "TOTAL",
            "sous_total": "Subtotal",
            "success_msg": "Quote sent successfully!",
            "conditions_title": "TERMS",
            "signature_title": "CLIENT SIGNATURE",
            "history_title": "History",
        },
    }


# ============================================================
# FONCTIONS DE CALCUL DE PRIX
# ============================================================

def calculer_prix_regulier(heures):
    """
    Calcule le prix pour un service régulier sans contrat (1 seul payeur).
    1h=65$, 2h=120$, 3h=150$, 4h+=180$ + 45$/h additionnel
    """
    heures = max(1, heures)
    if heures <= 1:
        return 65.00
    elif heures <= 2:
        return 120.00
    elif heures <= 3:
        return 150.00
    elif heures <= 4:
        return 180.00
    else:
        heures_extra = heures - 4
        return 180.00 + (heures_extra * 45.00)


def calculer_prix_groupe(nb_personnes, type_groupe="soins"):
    """
    Calcule le prix pour un forfait groupe RPA.
    Formule: heures = 0.4 × nb_personnes + 2 (arrondi à la demi-heure)
    Taux: 50$/h, base 4h = 200$
    """
    nb_personnes = max(Config.GROUPE_MIN_PERSONNES, min(nb_personnes, Config.GROUPE_MAX_PERSONNES))

    # Formule : heures = 0.4 * personnes + 2
    heures_brut = 0.4 * nb_personnes + 2
    # Arrondi à la demi-heure supérieure
    heures = math.ceil(heures_brut * 2) / 2
    heures = max(heures, Config.GROUPE_BASE_HEURES)

    prix_total = heures * Config.GROUPE_TAUX_HORAIRE
    prix_par_personne = prix_total / nb_personnes

    return {
        "heures": heures,
        "prix_total": prix_total,
        "prix_par_personne": round(prix_par_personne, 2),
        "nb_personnes": nb_personnes,
        "taux_horaire": Config.GROUPE_TAUX_HORAIRE,
    }


def calculer_prix_partage(nb_voisins=4):
    """
    Service partagé entre voisins RPA.
    Bloc 4h = 200$ ÷ nb_voisins
    Toujours 50$/h, jamais 45$/h.
    """
    nb_voisins = max(Config.PARTAGE_MIN_VOISINS, min(nb_voisins, Config.PARTAGE_MAX_VOISINS))
    cout_par_voisin = Config.PARTAGE_BLOC_PRIX / nb_voisins
    heures_par_voisin = Config.PARTAGE_BLOC_HEURES / nb_voisins

    return {
        "prix_total": Config.PARTAGE_BLOC_PRIX,
        "nb_voisins": nb_voisins,
        "cout_par_voisin": round(cout_par_voisin, 2),
        "heures_par_voisin": round(heures_par_voisin, 2),
        "taux_horaire": Config.GROUPE_TAUX_HORAIRE,
    }


def calculer_prix_contrat(type_contrat="hebdomadaire"):
    """
    Prix pour contrat corporatif.
    Hebdo=45$/h, Mensuel=43$/h, Annuel=40$/h
    """
    contrat = Config.CONTRATS.get(type_contrat, Config.CONTRATS["hebdomadaire"])
    return contrat


def calculer_taxes(sous_total):
    """Calcule TPS + TVQ sur un sous-total"""
    tps = sous_total * Config.TPS_RATE
    tvq = sous_total * Config.TVQ_RATE
    return {
        "sous_total": sous_total,
        "tps": round(tps, 2),
        "tvq": round(tvq, 2),
        "total": round(sous_total + tps + tvq, 2),
    }
