"""
BIEN CHEZ SOI - Parser IA pour extraire les données structurées
Utilise Claude pour interpréter la transcription vocale
Adapté à la tarification BCS complète
"""

import anthropic
from config import Config
import json

client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY) if Config.ANTHROPIC_API_KEY else None

SYSTEM_PROMPT = """Tu es un assistant Bien Chez Soi (BCS) qui extrait les informations de soumission à partir d'une demande vocale transcrite.

BIEN CHEZ SOI offre des services de soins à domicile, animation et compagnie dans la région de Brossard et environs (Québec).

TYPES DE SERVICE:
1. Régulier (sans contrat) — Un seul payeur:
   - 1h = 65$, 2h = 120$, 3h = 150$, 4h = 180$, 4h+ = 180$ + 45$/h additionnel

2. À la carte (Animation & Compagnie) — Base 50$/h, minimum 2h:
   - Visite de compagnie (jeux, cartes, discussion) — 2h min = 100$
   - Bingo / jeux de société / activités cognitives — 2h min = 100$
   - Promenade / sortie divertissement — 2h min = 100$
   - Animation thématique (musique, bricolage, atelier) — 2h min = 100$
   - Accompagnement événement / sortie spéciale — 3h min = 150$

3. Groupe Soins & Hygiène RPA — 50$/h, base 4h = 200$, 5-20 personnes
   Formule: heures = 0.4 × personnes + 2

4. Groupe Animation RPA — Même tarification que Soins

5. Service partagé voisins RPA — 4h × 50$/h = 200$ ÷ 4 voisins = 50$ chacun

6. Contrat corporatif:
   - Hebdomadaire: 4h/sem, 45$/h = 180$/sem
   - Mensuel: 16h/mois, 43$/h = 688$/mois
   - Annuel: 16h/mois × 12, 40$/h = 7680$/an

7. Forfait récurrent individuel:
   - Essentiel: 1x/sem, 8h/mois = 360$/mois (45$/h)
   - Confort: 2x/sem, 16h/mois = 680$/mois (42.50$/h)
   - Premium: 3x/sem, 24h/mois = 960$/mois (40$/h)

CATÉGORIES:
- Soins & Hygiène
- Animation & Compagnie
- Visite de compagnie
- Accompagnement sortie
- Promenade / divertissement
- Activités cognitives (bingo, jeux)
- Animation thématique
- Assistance alimentaire
- Soins de confort
- Autre

SUPPLÉMENTS (Add-ons):
- Urgence même jour (+15$)
- Hors horaire avant 7h / après 20h (+10$)
- Fin de semaine / jour férié (+10$)
- Déplacement hors zone (+15$)
- Matériel / fournitures spéciales (+10$)

RÈGLES D'EXTRACTION:
1. Extrais les informations explicitement mentionnées
2. Déduis le type de service selon le contexte:
   - "RPA", "résidence", "groupe" = Groupe RPA
   - "voisins", "partagé" = Partagé voisins
   - "contrat", "corporatif" = Contrat corporatif
   - "forfait", "récurrent", "mensuel" = Forfait récurrent
   - "animation", "bingo", "jeux", "compagnie" = À la carte
   - Sinon = Régulier
3. Déduis les suppléments selon le contexte:
   - "urgent", "aujourd'hui", "maintenant" = urgence
   - "6h du matin", "21h", "soir tard" = hors_horaire
   - "samedi", "dimanche", "férié" = fin_semaine
   - "loin", "hors zone", "Longueuil" = deplacement_extra
4. Si une info n'est pas mentionnée, mets null

Retourne UNIQUEMENT un JSON valide avec cette structure exacte:
{
  "client_nom": "string ou null",
  "client_telephone": "string ou null",
  "client_email": "string ou null",
  "adresse_service": "string ou null",
  "description_service": "string",
  "categorie": "string (une des catégories ci-dessus)",
  "type_service": "Régulier (sans contrat) | À la carte (Animation) | Groupe Soins RPA | Groupe Animation RPA | Partagé voisins RPA | Contrat corporatif | Forfait récurrent",
  "nombre_heures": number ou null,
  "nombre_personnes": number ou null,
  "forfait_recurrent": "Essentiel | Confort | Premium | null",
  "type_contrat": "hebdomadaire | mensuel | annuel | null",
  "addon_urgence": boolean,
  "addon_hors_horaire": boolean,
  "addon_fin_semaine": boolean,
  "addon_deplacement_extra": boolean,
  "addon_materiel": boolean,
  "date_service": "string (YYYY-MM-DD) ou null",
  "heure_service": "string (HH:MM) ou null",
  "notes": "string ou null",
  "langue_client": "fr | en"
}
"""


def parse_voice_input(transcription):
    """
    Parse une transcription vocale en données structurées BCS

    Args:
        transcription: Texte transcrit de l'audio

    Returns:
        dict: {'success': bool, 'data': dict} ou {'success': False, 'error': str}
    """
    if not client:
        return {'success': False, 'error': 'ANTHROPIC_API_KEY non configurée. Ajoutez-la dans .env pour l\'analyse du texte.'}
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Transcription de la demande:\n\n{transcription}"
                }
            ]
        )

        response_text = message.content[0].text

        # Extraire le JSON
        start = response_text.find('{')
        end = response_text.rfind('}') + 1

        if start == -1 or end == 0:
            return {
                'success': False,
                'error': 'Aucun JSON trouvé dans la réponse IA'
            }

        json_str = response_text[start:end]
        data = json.loads(json_str)

        # Validation et défauts
        if 'description_service' not in data or not data['description_service']:
            data['description_service'] = transcription

        if 'categorie' not in data or not data['categorie']:
            data['categorie'] = 'Autre'

        if 'type_service' not in data or not data['type_service']:
            data['type_service'] = 'Régulier (sans contrat)'

        if 'nombre_heures' not in data or data['nombre_heures'] is None:
            data['nombre_heures'] = 2  # Défaut 2h

        if 'langue_client' not in data:
            data['langue_client'] = 'fr'

        # S'assurer que les booleans existent
        for addon in ['addon_urgence', 'addon_hors_horaire', 'addon_fin_semaine',
                       'addon_deplacement_extra', 'addon_materiel']:
            if addon not in data:
                data[addon] = False

        return {
            'success': True,
            'data': data
        }

    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f'Erreur parsing JSON: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def complete_soumission_data(partial_data, follow_up_text):
    """
    Complète les données manquantes avec des informations additionnelles

    Args:
        partial_data: Données partielles existantes
        follow_up_text: Texte additionnel du client

    Returns:
        dict: Données mises à jour
    """
    prompt = f"""Données actuelles de la soumission Bien Chez Soi:
{json.dumps(partial_data, indent=2, ensure_ascii=False)}

Information additionnelle du client:
{follow_up_text}

Mets à jour le JSON avec les nouvelles informations.
Retourne UNIQUEMENT le JSON complet mis à jour, même structure que ci-dessus."""

    if not client:
        return {'success': False, 'error': 'ANTHROPIC_API_KEY non configurée. Ajoutez-la dans .env.'}
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        json_str = response_text[start:end]

        return {
            'success': True,
            'data': json.loads(json_str)
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
