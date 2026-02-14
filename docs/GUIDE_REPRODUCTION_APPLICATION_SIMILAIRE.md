# Guide de reproduction — Application de soumission vocale/écrite

Document destiné à reproduire les changements dans cette application ou dans une autre application similaire (agents terrain, saisie multi‑modes, soumission en direct).

---

## 1. Vue d’ensemble

**Objectif** : Application de soumission vocale/écrite pour agents terrain. Trois modes de saisie (dictée, écrit, enregistrement) alimentent une soumission en direct affichée côte à côte.

**Fonctionnalités clés** :
- **Dictée** : reconnaissance vocale continue (Web Speech API), envoi après debounce.
- **Écrit** : zone de texte + bouton « Analyser et remplir », même pipeline que la dictée.
- **Enregistrement** : enregistrement audio (MediaRecorder), envoi du fichier à l’API.
- **Soumission en direct** : panneau toujours visible à droite avec transcription, formulaire, totaux et actions (PDF, envoi).

---

## 2. Architecture backend (Flask)

### 2.1 Nouvel endpoint à ajouter

#### `POST /api/create-from-text`

**Rôle** : Créer une session à partir d’un texte (dictée ou mode écrit), sans audio.

**Entrée** :
```json
{ "text": "chaîne de caractères" }
```

**Sortie** :
```json
{
  "success": true,
  "session_id": "string",
  "transcription": "string",
  "data": { ... },
  "totals": { "prixBase", "addonsTotal", "tps", "tvq", "total" }
}
```

**Logique** :
1. Valider que `text` est fourni et non vide (sinon `400`).
2. Envoyer le texte au parser IA (ex. Claude) pour obtenir les champs structurés : `parse_voice_input(text)`.
3. Calculer les totaux : `calculate_totals(parsed['data'])` (depuis `pdf_generator` ou équivalent).
4. Créer une session : ID avec `secrets.token_urlsafe(16)`.
5. Stocker en mémoire (ou Redis) : `transcription`, `data`, `totals`, `created_at` (ISO 8601).
6. Retourner le tout en JSON.

**Exemple d’implémentation (à insérer dans `app.py`)** :

```python
import secrets

@app.route('/api/create-from-text', methods=['POST'])
def create_from_text():
    data = request.json
    text = (data or {}).get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': 'Texte manquant'}), 400

    parsed = parse_voice_input(text)
    if not parsed['success']:
        return jsonify(parsed), 400

    totals = calculate_totals(parsed['data'])
    session_id = secrets.token_urlsafe(16)
    sessions[session_id] = {
        'transcription': text,
        'data': parsed['data'],
        'totals': totals,
        'created_at': datetime.now().isoformat()
    }
    return jsonify({
        'success': True,
        'session_id': session_id,
        'transcription': text,
        'data': parsed['data'],
        'totals': totals
    })
```

---

### 2.2 Endpoint existant à utiliser / adapter

#### `POST /api/update-session`

**Rôle** : Mettre à jour une session (champs manuels et/ou texte additionnel).

**Entrée** :
```json
{
  "session_id": "string",
  "updates": { "client_nom": "...", ... },
  "additional_text": "texte optionnel"
}
```

**Comportement** :
- Si `updates` est fourni : appliquer chaque clé/valeur sur `session['data']`.
- Si `additional_text` est fourni : appeler le parser IA pour compléter/fusionner (ex. `complete_soumission_data(session['data'], additional_text)`), puis mettre à jour `session['data']`.
- Recalculer les totaux après toute modification.
- Renvoyer : `{ "success": true, "data": {...}, "totals": {...} }`.

**Référence** : Déjà implémenté dans `app.py` (routes `update_session`, avec `additional_text` et `complete_soumission_data`).

---

### 2.3 Endpoint utile pour l’UI

#### `GET /api/config` (optionnel)

**Rôle** : Renvoyer prix, taxes, catégories, etc., pour remplir l’UI dynamiquement.

**Option 1** : Créer un endpoint unique qui agrège tout (ex. `GET /api/config` retournant `pricing` + `categories` + `lang`).

**Option 2** : Utiliser les endpoints existants :
- `GET /api/pricing` — grille tarifaire, add-ons, catégories, types de service, TPS/TVQ (déjà dans `app.py`).
- `GET /api/lang/<lang>` — traductions pour l’interface.

---

## 3. Architecture frontend (HTML/JS)

### 3.1 Mise en page split

- **Desktop** : Deux colonnes (ex. 50 % / 50 % ou 45 % / 55 %).
  - **Gauche** : Saisie (choix du mode + zone dictée/écrit/enregistrement).
  - **Droite** : Soumission en direct (transcription, formulaire, totaux, actions).
- **Mobile** (largeur &lt; 900 px) : Empilage vertical (saisie en haut, soumission en bas).
- **Panneau droit** : `position: sticky` pour rester visible au scroll.
- **Titre** du panneau droit : ex. « Soumission en direct » avec indicateur (point pulsant) quand une session est active.

**Exemple structure** :

```html
<div class="split-layout">
  <aside class="panel-input">
    <h2>Saisie</h2>
    <!-- Boutons mode: Dictée | Écrit | Enregistrement -->
    <!-- Zone selon mode -->
  </aside>
  <main class="panel-live">
    <h2>Soumission en direct <span class="live-dot"></span></h2>
    <div class="transcription">— En attente de saisie —</div>
    <div class="form-fields">...</div>
    <div class="totals">...</div>
    <div class="actions">PDF, Envoyer, Nouvelle soumission</div>
  </main>
</div>
```

```css
@media (min-width: 900px) {
  .split-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
}
@media (max-width: 899px) {
  .split-layout { display: flex; flex-direction: column; }
}
.panel-live { position: sticky; top: 16px; }
```

---

### 3.2 Modes de saisie (boutons dans le panneau gauche)

| Mode            | Bouton / Label      | Comportement |
|-----------------|---------------------|--------------|
| **Dictée**      | « Dictée »          | Web Speech API, reconnaissance continue, langue `fr-CA`. |
| **Écrit**       | « Écrit »           | Zone texte + bouton « Analyser et remplir ». |
| **Enregistrement** | « Enregistrement » | MediaRecorder, envoi du fichier audio à l’API. |

---

### 3.3 Mode dictée (Web Speech API)

- **Détection** : `window.SpeechRecognition || window.webkitSpeechRecognition`. Si absent, désactiver le mode dictée et le bouton « Ajouter par dictée ».
- **Options** : `continuous: true`, `interimResults: true`, `lang: 'fr-CA'`.
- **Debounce** : environ 1,2 s après la dernière phrase finale avant d’envoyer au backend (éviter envois multiples).
- **Flux** :
  - **Pas de session** : `POST /api/create-from-text` avec le texte dicté.
  - **Session existante** : `POST /api/update-session` avec `additional_text`.
- **Affichage** : Mettre à jour en direct une zone `liveTranscript` avec le texte reconnu (interim + final).

**Exemple squelette** :

```javascript
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) { /* désactiver dictée */ }

const recognition = new SpeechRecognition();
recognition.continuous = true;
recognition.interimResults = true;
recognition.lang = 'fr-CA';

let debounceTimer;
const DEBOUNCE_MS = 1200;

recognition.onresult = (e) => {
  let transcript = '';
  for (const r of e.results) transcript += r[0].transcript;
  liveTranscriptEl.textContent = transcript;
  if (e.results[e.results.length - 1].isFinal) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => sendTranscript(transcript), DEBOUNCE_MS);
  }
};

function sendTranscript(text) {
  if (!text.trim()) return;
  if (sessionId) {
    fetch('/api/update-session', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, additional_text: text }) });
  } else {
    fetch('/api/create-from-text', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }) });
  }
  // puis traiter la réponse et mettre à jour le panneau droit (updateFormFromData)
}
```

---

### 3.4 Mode écrit

- **Éléments** : `<textarea>` + bouton « Analyser et remplir ».
- **Comportement** :
  - Pas de session : `POST /api/create-from-text` avec le contenu du textarea.
  - Session existante : `POST /api/update-session` avec `additional_text`.
- Après succès : vider le textarea, mettre à jour la transcription affichée et le formulaire (même `updateFormFromData()` que pour la dictée).

---

### 3.5 Panneau droit (soumission en direct)

- Toujours visible (sticky sur desktop).
- Contenu : transcription, formulaire (client, service, options), totaux, actions (PDF, email, etc.).
- Mise à jour : après chaque réponse API réussie, appeler `updateFormFromData(session)` (ou équivalent) pour remplir transcription, champs et totaux.

---

### 3.6 Bouton « Ajouter par dictée » (étape 2)

- Quand une session existe déjà : relancer la dictée en mode « compléter ».
- Utiliser `additional_text` pour enrichir la session existante via `POST /api/update-session`.

---

## 4. Structure des données de session

Modèle générique (à adapter aux champs métier de l’autre application) :

```json
{
  "transcription": "texte brut",
  "data": {
    "client_nom": "...",
    "client_telephone": "...",
    "client_email": "...",
    "adresse_service": "...",
    "description_service": "...",
    "categorie": "...",
    "tranche_temps": "...",
    "addon_urgence": false,
    "addon_hors_horaire": false,
    "addon_materiel": false,
    "addon_deuxieme_arret": false
  },
  "totals": {
    "prixBase": 0,
    "addonsTotal": 0,
    "tps": 0,
    "tvq": 0,
    "total": 0
  },
  "created_at": "2025-02-13T12:00:00.000Z"
}
```

Dans BCS, les champs `data` incluent aussi : `type_service`, `nombre_heures`, `nombre_personnes`, `forfait_recurrent`, `type_contrat`, `addon_fin_semaine`, `addon_deplacement_extra`, `date_service`, `heure_service`, `notes`, `langue_client`. Adapter selon le domaine.

---

## 5. Styles et UX

- **Couleur principale** : `#1a365d` (bleu marine) — ou `#1B2A4A` comme dans l’app actuelle.
- **Fond** : `#f7fafc` (ou équivalent clair).
- **Cartes** : fond blanc, coins arrondis (ex. `16px`).
- **Bouton micro** : rond, style gradient (ex. bleu marine → bleu clair).
- **États visuels** :
  - `.listening` : dictée en cours (ex. bordure ou fond pulsant).
  - `.recording` : enregistrement audio en cours (ex. rouge, animation pulse).
- **Libellés** : français canadien (Transcription, Nom du client, etc.).

---

## 6. Points d’attention

- **Compatibilité Web Speech API** : surtout Chrome/Edge. Si absent, désactiver le mode dictée et « Ajouter par dictée ».
- **Debounce** : éviter les envois multiples pendant la dictée (ex. 1,2 s après la dernière phrase finale).
- **Session** : vérifier `sessionId` avant tout appel à `update-session`; sinon utiliser `create-from-text` (ou équivalent).
- **Loading** : overlay ou indicateur pendant les appels API (transcription, parsing).
- **Restart** : réinitialiser `sessionId`, formulaires, zone de transcription et `liveTranscript`.

---

## 7. Fichiers concernés

| Fichier                | Modifications principales |
|------------------------|---------------------------|
| **app.py**             | Ajouter `POST /api/create-from-text`; s’assurer que la logique des sessions utilise un ID robuste (`secrets.token_urlsafe(16)`); exposer `GET /api/config` si souhaité. |
| **templates/index.html** ou **index.html** | Vue split; onglets ou boutons Dictée / Écrit / Enregistrement; Web Speech API + debounce; intégration formulaires et `updateFormFromData()`. |
| **ai_parser.py**       | `parse_voice_input(text)` et `complete_soumission_data(partial_data, follow_up_text)` (déjà présents dans BCS). Adapter les prompts pour les champs du nouveau domaine. |

---

## 8. Flux utilisateur résumé

```
[Démarrage]
  → Panneau gauche : choix mode (Dictée | Écrit | Enregistrement)
  → Panneau droit : formulaire vide + "— En attente de saisie —"

[Dictée]
  → Clic "Parler" → reconnaissance → debounce
  → POST /api/create-from-text ou /api/update-session
  → Panneau droit mis à jour

[Écrit]
  → Saisie texte → Clic "Analyser et remplir"
  → POST /api/create-from-text ou /api/update-session
  → Panneau droit mis à jour

[Enregistrement]
  → Enregistrement audio → POST /api/process-voice
  → Panneau droit mis à jour

[Compléter]
  → Bouton "Ajouter par dictée" ou nouveau texte en mode écrit
  → POST /api/update-session avec additional_text
```

---

## 9. Adaptation à une autre application

- **Champs métier** : Remplacer les champs dans `data` (client, service, options, etc.) par ceux du nouveau domaine.
- **Parser IA** : Ajuster les prompts dans `ai_parser.py` (ou équivalent) pour les nouveaux champs et règles métier.
- **Totaux** : Adapter `calculate_totals()` (ou équivalent) au modèle de tarification (taxes, suppléments, etc.).
- **À conserver** : Structure split, trois modes (Dictée / Écrit / Enregistrement), Web Speech API, debounce, logique create-from-text vs update-session, et pattern « panneau droit toujours à jour ».

---

## 10. Référence rapide des endpoints

| Méthode | Route                  | Rôle |
|---------|------------------------|------|
| POST    | `/api/create-from-text` | Créer une session à partir d’un texte (à ajouter). |
| POST    | `/api/update-session`  | Mettre à jour une session (updates + additional_text). |
| POST    | `/api/process-voice`   | Audio → transcription → parsing → création de session (existant). |
| GET     | `/api/config` ou `/api/pricing` | Config / prix pour l’UI. |
| POST    | `/api/generate-pdf`    | Générer le PDF. |
| POST    | `/api/submit`         | Soumettre (Notion, email, etc.). |

Ce guide permet de reproduire l’architecture et les flux dans cette codebase ou dans une autre application similaire en adaptant uniquement les champs et les règles métier.
