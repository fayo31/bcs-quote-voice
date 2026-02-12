# Bien Chez Soi - Soumission Vocale

Application de soumission par dictation vocale pour services de soins et compagnie a domicile.

Les Entreprises REMES Inc. / Fiducie Ramahime

## Fonctionnalites

- Enregistrement vocal avec transcription automatique (Whisper)
- Parsing intelligent des donnees (Claude AI)
- Tarification complete BCS (regulier, groupe RPA, forfaits, contrats)
- Calcul automatique TPS/TVQ Quebec
- Generation PDF professionnelle avec signature client
- Sauvegarde Notion (soumissions + contacts)
- Envoi courriel avec PDF en piece jointe
- Interface bilingue FR/EN
- Historique des soumissions

## Tarification

### Regulier (sans contrat, 1 payeur)
| Duree | Prix | Taux effectif |
|-------|------|---------------|
| 1h | 65$ | 65$/h |
| 2h | 120$ | 60$/h |
| 3h | 150$ | 50$/h |
| 4h+ | 180$ + 45$/h | 45$/h |

### A la carte (Animation)
50$/h, minimum 2h = 100$

### Groupe RPA (Soins ou Animation)
50$/h, base 4h = 200$, 5-20 personnes

### Contrats corporatifs
- Hebdomadaire: 45$/h (4h/sem = 180$/sem)
- Mensuel: 43$/h (16h/mois = 688$/mois)
- Annuel: 40$/h (16h/mois x 12 = 7680$/an)

### Forfaits recurrents
- Essentiel: 1x/sem, 360$/mois (45$/h)
- Confort: 2x/sem, 680$/mois (42.50$/h)
- Premium: 3x/sem, 960$/mois (40$/h)

Taxes: TPS 5% + TVQ 9.975%

## Installation

```bash
cd bcs-quote-voice
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editer .env avec vos cles API
python app.py
```

Ouvrir http://localhost:5000

## Structure

```
bcs-quote-voice/
  app.py              # Serveur Flask
  config.py           # Configuration + tarification
  voice_processor.py  # Transcription Whisper
  ai_parser.py        # Parsing Claude
  pdf_generator.py    # Generation PDF
  notion_service.py   # Integration Notion
  email_service.py    # Envoi courriels
  index.html          # Interface mobile
  requirements.txt    # Dependances
  Dockerfile          # Deploiement Docker
  .env.example        # Template config
```

## API

| Endpoint | Methode | Description |
|----------|---------|-------------|
| / | GET | Interface web |
| /api/health | GET | Etat du serveur |
| /api/process-voice | POST | Pipeline complet |
| /api/generate-pdf | POST | Generation PDF |
| /api/submit | POST | Soumission complete |
| /api/history | GET | Historique |
| /api/pricing | GET | Grille tarifaire |
| /api/lang/:lang | GET | Traductions |

## Deploiement Docker

```bash
docker build -t bcs-quote-voice .
docker run -p 5000:5000 --env-file .env bcs-quote-voice
```
