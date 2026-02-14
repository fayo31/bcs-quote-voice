# Bien Chez Soi - Soumission vocale

Application de soumission par **dictée vocale**, **saisie écrite** ou **enregistrement audio** pour services de soins et compagnie à domicile. Soumission en direct affichée côte à côte (vue split).

Les Entreprises REMES Inc. / Fiducie Ramahime

---

## Fonctionnalités

- **Trois modes de saisie** : Dictée (Web Speech API), Écrit (texte + « Analyser et remplir »), Enregistrement (MediaRecorder)
- **Vue split** : panneau gauche = saisie ; panneau droit = soumission en direct (transcription, formulaire, totaux) toujours visible
- Transcription automatique (Whisper) et parsing intelligent (Claude)
- Tarification complète BCS (régulier, groupe RPA, forfaits, contrats)
- Calcul automatique TPS/TVQ Québec, génération PDF, signature client
- Sauvegarde Notion, envoi courriel avec PDF, interface FR/EN, historique

---

## Historique des modifications (état initial → maintenant)

Résumé de tout ce qui a été fait depuis l’état initial jusqu’à la version actuelle.

### 1. Backend (Flask)

- **Nouvel endpoint `POST /api/create-from-text`**  
  Crée une session à partir d’un texte (dictée ou mode écrit). Entrée : `{"text": "..."}`. Sortie : `session_id`, `transcription`, `data`, `totals`. Utilise `secrets.token_urlsafe(16)` pour l’ID de session.
- **Endpoint existant `POST /api/update-session`**  
  Déjà utilisé ; accepte `additional_text` pour compléter une session via le parser IA (`complete_soumission_data`), en plus des mises à jour manuelles (`updates`).
- **Démarrage sans clés API**  
  L’app peut démarrer même si `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` sont absentes : les modules créent le client seulement si la clé est définie ; sinon les appels renvoient un message d’erreur clair au lieu de faire planter l’import.

### 2. Frontend (HTML/JS)

- **Vue split**  
  Deux colonnes sur grand écran (≥ 900px) : gauche = saisie (modes), droite = soumission en direct. Sur mobile : empilage vertical. Panneau droit en `position: sticky`.
- **Trois modes avec boutons**  
  - **Dictée** : Web Speech API, reconnaissance continue, `lang: 'fr-CA'`, debounce ~1,2 s après la dernière phrase, puis `POST /api/create-from-text` ou `POST /api/update-session` selon qu’une session existe ou non. Transcription en direct dans une zone dédiée.
  - **Écrit** : zone de texte + bouton « Analyser et remplir » ; même logique create-from-text / update-session.
  - **Enregistrement** : comportement inchangé (MediaRecorder → `POST /api/process-voice`).
- **Panneau « Soumission en direct »**  
  Titre avec indicateur (point vert pulsant quand une session est active), transcription, formulaire client/service/options, totaux (facture), signature, actions (PDF, Envoyer, Nouvelle soumission).
- **Bouton « Ajouter par dictée »**  
  Affiché quand une session existe ; relance la dictée pour compléter la soumission (utilise `additional_text`).
- **Mise à jour en direct**  
  Après chaque réponse API réussie, `updateFormFromData()` remplit le panneau droit (transcription, champs, totaux).
- **Bouton « Nouvelle soumission »**  
  Réinitialisation complète : session supprimée, tous les champs du formulaire vidés (client, adresse, description, zone écrite, catégorie, type de service, heures, add-ons, etc.), totaux remis aux valeurs par défaut (2 h régulier), signature effacée, panneau droit affichant « — En attente de saisie — ». L’interface revient comme au premier chargement.

### 3. Configuration et chargement du `.env`

- **Chemin du `.env`**  
  Chargement depuis le répertoire du projet (où se trouve `config.py`), et non plus depuis le répertoire courant, pour que l’app trouve le fichier même si elle est lancée depuis un autre dossier (ex. Cursor, autre terminal).
- **Fichier chargé**  
  On tente d’abord `.env`, puis `.env.example` s’il n’existe pas de `.env`.
- **Chargement robuste**  
  Ouverture explicite du fichier en UTF-8, `load_dotenv(stream=f)`, puis secours : lecture ligne par ligne et affectation directe dans `os.environ` pour chaque `CLE=valeur`, afin d’éviter les soucis d’encodage ou de chemin.
- **Débogage au démarrage**  
  Au lancement de l’app, affichage du chemin du fichier chargé et de l’état des clés (OpenAI / Anthropic : OK ou MANQUANT).

### 4. Documentation

- **`docs/GUIDE_REPRODUCTION_APPLICATION_SIMILAIRE.md`**  
  Guide pour reproduire cette architecture (vue split, trois modes, create-from-text, update-session, debounce, structure des données) dans cette app ou une autre.

### 5. Sécurité et exemples

- **`.env.example`**  
  Contient uniquement des placeholders pour les clés (pas de vraies clés). Les vraies clés restent dans `.env` (ignoré par Git).

---

## Différence entre la dernière version et maintenant

| Aspect | Avant (dernière version) | Maintenant |
|--------|---------------------------|------------|
| **Interface** | Une colonne : étape 1 = enregistrement, étape 2 = formulaire après traitement | Vue split : gauche = saisie (3 modes), droite = soumission en direct toujours visible |
| **Saisie** | Uniquement enregistrement audio (bouton, puis analyse) | Dictée (Web Speech API), Écrit (texte + Analyser et remplir), Enregistrement (audio) |
| **Création de session depuis du texte** | Aucune | `POST /api/create-from-text` + utilisation en dictée/écrit |
| **Compléter une session** | Modifications manuelles uniquement | `additional_text` dans `update-session` + bouton « Ajouter par dictée » |
| **Affichage des totaux** | Après enregistrement, sur la page « étape 2 » | Panneau droit toujours visible, mis à jour en direct après chaque action |
| **Chargement du `.env`** | `load_dotenv()` depuis le répertoire courant | Chargement depuis le dossier du projet + ouverture explicite du fichier + secours par parsing manuel |
| **Démarrage sans clés API** | Erreur à l’import (client OpenAI/Anthropic) | Démarrage possible ; message clair à l’usage (transcription / analyse) si clé manquante |
| **Port** | 5000 (dans l’ancien README) | 8080 (comme dans `app.py`) |
| **Documentation** | README + structure du repo | + Guide de reproduction dans `docs/` |
| **Nouvelle soumission** | Réinitialisation partielle | Réinitialisation complète : tous les champs vidés, totaux par défaut, signature effacée |

---

## Tarification

### Régulier (sans contrat, 1 payeur)
| Durée | Prix | Taux effectif |
|-------|------|---------------|
| 1h | 65$ | 65$/h |
| 2h | 120$ | 60$/h |
| 3h | 150$ | 50$/h |
| 4h+ | 180$ + 45$/h | 45$/h |

### À la carte (Animation)
50$/h, minimum 2h = 100$

### Groupe RPA (Soins ou Animation)
50$/h, base 4h = 200$, 5–20 personnes

### Contrats corporatifs
- Hebdomadaire : 45$/h (4h/sem = 180$/sem)
- Mensuel : 43$/h (16h/mois = 688$/mois)
- Annuel : 40$/h (16h/mois × 12 = 7680$/an)

### Forfaits récurrents
- Essentiel : 1x/sem, 360$/mois (45$/h)
- Confort : 2x/sem, 680$/mois (42.50$/h)
- Premium : 3x/sem, 960$/mois (40$/h)

Taxes : TPS 5 % + TVQ 9,975 %

---

## Installation

```bash
cd bcs-quote-voice
python -m venv venv
source venv/bin/activate   # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec vos clés API (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
python app.py
```

Ouvrir **http://localhost:8080**

Au démarrage, la console affiche le fichier `.env` chargé et l’état des clés (OK / MANQUANT).

---

## Structure

```
bcs-quote-voice/
  app.py              # Serveur Flask (create-from-text, update-session, process-voice, etc.)
  config.py           # Configuration, tarification, chargement .env
  voice_processor.py  # Transcription Whisper (optionnel si clé absente)
  ai_parser.py        # Parsing Claude (optionnel si clé absente)
  pdf_generator.py    # Génération PDF
  notion_service.py   # Intégration Notion
  email_service.py    # Envoi courriels
  index.html          # Interface (vue split, Dictée / Écrit / Enregistrement)
  requirements.txt
  Dockerfile
  .env.example        # Template (sans vraies clés)
  docs/
    GUIDE_REPRODUCTION_APPLICATION_SIMILAIRE.md
```

---

## API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| / | GET | Interface web |
| /api/health | GET | État du serveur |
| /api/create-from-text | POST | Créer une session depuis un texte (dictée/écrit) |
| /api/update-session | POST | Mettre à jour une session (updates + additional_text) |
| /api/process-voice | POST | Pipeline audio complet (transcription + parsing + session) |
| /api/transcribe | POST | Transcription audio seule |
| /api/parse | POST | Parsing texte seul |
| /api/generate-pdf | POST | Génération PDF |
| /api/submit | POST | Soumission complète (Notion + courriel) |
| /api/history | GET | Historique |
| /api/search | GET | Recherche soumissions |
| /api/pricing | GET | Grille tarifaire |
| /api/lang/:lang | GET | Traductions |

---

## Déploiement Docker

```bash
docker build -t bcs-quote-voice .
docker run -p 8080:8080 --env-file .env bcs-quote-voice
```

---

## Partir de zéro ou pour un autre client

Guide pour lancer cette application from scratch ou l’adapter pour un autre client : ce qu’il faut, les coûts, les étapes et le résultat final.

### Ce qu’il vous faut (prix / coûts)

| Élément | Rôle | Coût indicatif |
|--------|------|----------------|
| **OpenAI (Whisper)** | Transcription audio → texte | Facturation à l’usage (quelques $ / million de caractères). Compte sur platform.openai.com. |
| **Anthropic (Claude)** | Analyse du texte → champs structurés (client, service, options) | Facturation à l’usage. Compte sur console.anthropic.com. |
| **Notion** (optionnel) | Base de données soumissions + contacts | Gratuit jusqu’à un certain volume ; puis forfait par utilisateur. |
| **SMTP / email** (optionnel) | Envoi du PDF au client | Gratuit avec Gmail (mot de passe d’application) ou fournisseur email. |
| **Hébergement** (optionnel) | Servir l’app en production | Variable (ex. Railway, Render, VPS). Peut rester en local (localhost) pour usage interne. |

**Minimum pour faire tourner l’app (dictée + écrit + enregistrement + formulaire + PDF)** : OpenAI + Anthropic. Le reste (Notion, email, déploiement) est optionnel.

### Prérequis

1. **Compte OpenAI** : créer une clé API (Whisper).
2. **Compte Anthropic** : créer une clé API (Claude).
3. **Fichier `.env`** : copier `.env.example` en `.env` et y mettre les clés (jamais commiter `.env`).
4. **Python 3** et `pip` (ou environnement virtuel recommandé).

### Étapes : ce qui manque (partir de zéro ou autre client)

Si vous **partez de zéro** (nouveau projet) :

1. Cloner ou copier ce dépôt.
2. Créer un environnement virtuel : `python -m venv venv` puis activer.
3. Installer les dépendances : `pip install -r requirements.txt`.
4. Créer `.env` à la racine avec au minimum `OPENAI_API_KEY` et `ANTHROPIC_API_KEY`.
5. Lancer : `python app.py` puis ouvrir http://localhost:8080.
6. (Optionnel) Renseigner Notion et SMTP dans `.env` si vous voulez historique et envoi d’emails.

Si vous **adaptez pour un autre client** (autre domaine métier) :

1. **Backend**  
   - Garder la structure (Flask, `create-from-text`, `update-session`, `process-voice`).  
   - Dans `config.py` : adapter les constantes (tarifs, catégories, types de service, add-ons).  
   - Dans `ai_parser.py` : modifier le prompt système et la structure JSON pour les nouveaux champs.  
   - Dans `pdf_generator.py` / `calculate_totals` : adapter les calculs aux nouveaux tarifs.

2. **Frontend**  
   - Garder la vue split, les trois modes (Dictée, Écrit, Enregistrement) et le debounce.  
   - Dans `index.html` : adapter les libellés, les listes déroulantes (catégories, types, heures), les add-ons et les champs du formulaire pour qu’ils correspondent aux nouveaux `data` renvoyés par l’API.

3. **Données**  
   - La structure de session reste du type : `transcription`, `data` (champs métier), `totals`, `created_at`. Seuls les clés dans `data` et la logique des totaux changent.

4. **Documentation**  
   - Utiliser `docs/GUIDE_REPRODUCTION_APPLICATION_SIMILAIRE.md` comme checklist (endpoints, flux, structure des données).

### Résultat final

À la fin vous avez :

- Une app qui démarre (avec ou sans Notion/SMTP).
- Trois façons de saisir : **dictée** (navigateur), **écrit** (texte + Analyser et remplir), **enregistrement** (audio).
- Un **panneau droit** avec la soumission en direct (transcription, formulaire, totaux, signature).
- Création de session depuis le texte (`create-from-text`) et complétion avec « Ajouter par dictée » ou nouveau texte (`update-session` + `additional_text`).
- **Nouvelle soumission** qui remet tout à zéro (formulaire vide, totaux par défaut).
- Génération PDF, envoi par email et synchro Notion si configurés.

Pour une autre app / un autre client : même expérience utilisateur, avec vos propres champs, tarifs et libellés.

---

## Reproduction dans une autre application

Voir **`docs/GUIDE_REPRODUCTION_APPLICATION_SIMILAIRE.md`** pour adapter cette architecture (vue split, trois modes, create-from-text, update-session, debounce) à un autre domaine en gardant la même logique.
