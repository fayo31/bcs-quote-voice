"""
BIEN CHEZ SOI - Intégration Notion
Adapté au schéma BCS pour bases SOUMISSIONS et CONTACTS
"""

from notion_client import Client
from config import Config
from datetime import datetime

# Initialisation conditionnelle
notion = None
if Config.NOTION_API_KEY:
    notion = Client(auth=Config.NOTION_API_KEY)


def create_soumission(data, totals, pdf_path=None):
    """
    Crée une entrée dans la base Notion SOUMISSIONS BCS

    Schéma Notion attendu:
    - Titre (title): "BCS-20260211... - Nom Client"
    - Description service (rich_text)
    - Adresse service (rich_text)
    - Catégorie (select): Soins & Hygiène, Animation & Compagnie, etc.
    - Type service (select): Régulier, À la carte, Groupe, etc.
    - Nombre heures (number)
    - Nombre personnes (number)
    - Prix base (number)
    - Sous-total (number)
    - TPS (number)
    - TVQ (number)
    - Total (number)
    - Add-on urgence (checkbox)
    - Add-on hors horaire (checkbox)
    - Add-on fin semaine (checkbox)
    - Add-on déplacement (checkbox)
    - Add-on matériel (checkbox)
    - Statut (select): Brouillon, Envoyée, Acceptée, Refusée, Expirée, Complétée
    - Client (relation to CONTACTS)
    - Date envoi (date)
    - Langue (select): fr, en
    - Notes internes (rich_text)

    Returns:
        dict: {'success': bool, 'numero': str, 'notion_id': str}
    """
    if not notion or not Config.NOTION_SOUMISSIONS_DB:
        return {
            'success': False,
            'error': 'Notion non configuré. Ajoutez NOTION_API_KEY et NOTION_SOUMISSIONS_DB dans .env'
        }

    try:
        numero = data.get('numero', f"BCS-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        client_nom = data.get('client_nom', 'Client')
        titre = f"{numero} — {client_nom}"

        properties = {
            "Titre": {
                "title": [{"text": {"content": titre}}]
            },
            "Description service": {
                "rich_text": [{"text": {"content": (data.get('description_service') or '')[:2000]}}]
            },
            "Type service": {
                "select": {"name": totals.get('type_service', 'Régulier (sans contrat)')}
            },
            "Nombre heures": {
                "number": totals.get('heures', 0)
            },
            "Prix base": {
                "number": totals.get('prix_base', 0)
            },
            "Sous-total": {
                "number": totals.get('sous_total', 0)
            },
            "TPS": {
                "number": totals.get('tps', 0)
            },
            "TVQ": {
                "number": totals.get('tvq', 0)
            },
            "Total": {
                "number": totals.get('total', 0)
            },
            "Statut": {
                "select": {"name": "Brouillon"}
            },
        }

        # Adresse
        if data.get('adresse_service'):
            properties["Adresse service"] = {
                "rich_text": [{"text": {"content": data['adresse_service'][:2000]}}]
            }

        # Catégorie
        if data.get('categorie') and data['categorie'] in Config.CATEGORIES:
            properties["Catégorie"] = {"select": {"name": data['categorie']}}

        # Nombre de personnes
        if data.get('nombre_personnes') and data['nombre_personnes'] > 0:
            properties["Nombre personnes"] = {"number": data['nombre_personnes']}

        # Add-ons (checkboxes)
        properties["Add-on urgence"] = {"checkbox": bool(data.get('addon_urgence'))}
        properties["Add-on hors horaire"] = {"checkbox": bool(data.get('addon_hors_horaire'))}
        properties["Add-on fin semaine"] = {"checkbox": bool(data.get('addon_fin_semaine'))}
        properties["Add-on déplacement"] = {"checkbox": bool(data.get('addon_deplacement_extra'))}
        properties["Add-on matériel"] = {"checkbox": bool(data.get('addon_materiel'))}

        # Langue
        properties["Langue"] = {
            "select": {"name": data.get('langue_client', 'fr')}
        }

        # Notes internes
        notes_parts = [f"Total calculé: {totals.get('total', 0):.2f}$ CAD"]
        if data.get('notes'):
            notes_parts.append(f"Notes: {data['notes']}")
        properties["Notes internes"] = {
            "rich_text": [{"text": {"content": "\n".join(notes_parts)}}]
        }

        # Créer la page
        response = notion.pages.create(
            parent={"database_id": Config.NOTION_SOUMISSIONS_DB},
            properties=properties
        )

        return {
            'success': True,
            'numero': numero,
            'notion_id': response['id'],
            'notion_url': response.get('url')
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def update_soumission_status(page_id, status, date_envoi=None):
    """Met à jour le statut d'une soumission"""
    if not notion:
        return {'success': False, 'error': 'Notion non configuré'}

    try:
        properties = {
            "Statut": {"select": {"name": status}}
        }

        if status == "Envoyée":
            properties["Date envoi"] = {
                "date": {"start": date_envoi or datetime.now().isoformat()[:10]}
            }

        notion.pages.update(page_id=page_id, properties=properties)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_or_create_contact(data):
    """
    Trouve ou crée un contact dans Notion CONTACTS

    Returns:
        dict: {'success': bool, 'contact_id': str, 'is_new': bool}
    """
    if not notion or not Config.NOTION_CONTACTS_DB:
        return {'success': False, 'error': 'Base contacts Notion non configurée'}

    try:
        filters = []

        if data.get('client_telephone'):
            filters.append({
                "property": "Téléphone",
                "phone_number": {"equals": data['client_telephone']}
            })

        if data.get('client_email'):
            filters.append({
                "property": "Email",
                "email": {"equals": data['client_email']}
            })

        if not filters:
            return {'success': True, 'contact_id': None, 'is_new': False}

        filter_query = {"or": filters} if len(filters) > 1 else filters[0]

        response = notion.databases.query(
            database_id=Config.NOTION_CONTACTS_DB,
            filter=filter_query
        )

        if response['results']:
            return {
                'success': True,
                'contact_id': response['results'][0]['id'],
                'is_new': False
            }

        # Créer nouveau contact
        properties = {
            "Nom complet": {
                "title": [{"text": {"content": data.get('client_nom', 'Client BCS')}}]
            },
            "Type": {
                "multi_select": [{"name": "Client"}]
            },
            "Statut": {
                "select": {"name": "Actif"}
            },
            "Source": {
                "select": {"name": "Soumission vocale"}
            }
        }

        if data.get('client_telephone'):
            properties["Téléphone"] = {"phone_number": data['client_telephone']}
        if data.get('client_email'):
            properties["Email"] = {"email": data['client_email']}
        if data.get('adresse_service'):
            properties["Adresse"] = {
                "rich_text": [{"text": {"content": data['adresse_service'][:2000]}}]
            }

        new_contact = notion.pages.create(
            parent={"database_id": Config.NOTION_CONTACTS_DB},
            properties=properties
        )

        return {
            'success': True,
            'contact_id': new_contact['id'],
            'is_new': True
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_recent_soumissions(limit=20):
    """
    Récupère les soumissions récentes pour l'historique

    Returns:
        list: Liste de soumissions récentes
    """
    if not notion or not Config.NOTION_SOUMISSIONS_DB:
        return []

    try:
        response = notion.databases.query(
            database_id=Config.NOTION_SOUMISSIONS_DB,
            sorts=[{"timestamp": "created_time", "direction": "descending"}],
            page_size=limit
        )

        soumissions = []
        for page in response['results']:
            props = page['properties']
            soumissions.append({
                'id': page['id'],
                'titre': _get_title(props.get('Titre')),
                'statut': _get_select(props.get('Statut')),
                'total': props.get('Total', {}).get('number', 0),
                'type_service': _get_select(props.get('Type service')),
                'categorie': _get_select(props.get('Catégorie')),
                'created': page.get('created_time', ''),
                'url': page.get('url', ''),
            })

        return soumissions

    except Exception as e:
        print(f"Erreur récupération historique: {e}")
        return []


def search_soumissions(query):
    """Recherche de soumissions par titre"""
    if not notion or not Config.NOTION_SOUMISSIONS_DB:
        return []

    try:
        response = notion.databases.query(
            database_id=Config.NOTION_SOUMISSIONS_DB,
            filter={
                "property": "Titre",
                "title": {"contains": query}
            },
            page_size=10
        )

        results = []
        for page in response['results']:
            props = page['properties']
            results.append({
                'id': page['id'],
                'titre': _get_title(props.get('Titre')),
                'statut': _get_select(props.get('Statut')),
                'total': props.get('Total', {}).get('number', 0),
                'created': page.get('created_time', ''),
            })
        return results

    except Exception as e:
        print(f"Erreur recherche: {e}")
        return []


# === Helpers ===

def _get_title(prop):
    if not prop or not prop.get('title'):
        return ''
    return ''.join([t.get('plain_text', '') for t in prop['title']])


def _get_rich_text(prop):
    if not prop or not prop.get('rich_text'):
        return ''
    return ''.join([t.get('plain_text', '') for t in prop['rich_text']])


def _get_select(prop):
    if not prop or not prop.get('select'):
        return ''
    return prop['select'].get('name', '')
