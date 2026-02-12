"""
BIEN CHEZ SOI - Application de soumission vocale
Serveur Flask principal avec historique et signature

Usage:
    python app.py

L'application sera disponible sur http://localhost:5000
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import os
import tempfile
import base64

from config import Config
from voice_processor import transcribe_audio
from ai_parser import parse_voice_input, complete_soumission_data
from pdf_generator import generate_soumission_pdf, calculate_totals
from notion_service import (
    create_soumission, get_or_create_contact,
    update_soumission_status, get_recent_soumissions, search_soumissions
)
from email_service import send_soumission_email

app = Flask(__name__)
CORS(app)

# Stockage temporaire des sessions (en production, utiliser Redis)
sessions = {}


# ============================================================
# ROUTES — PAGES
# ============================================================

@app.route('/')
def index():
    """Page d'accueil - Interface mobile"""
    with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'r', encoding='utf-8') as f:
        return f.read()


# ============================================================
# ROUTES — API
# ============================================================

@app.route('/api/health')
def health():
    """Vérification de l'état du serveur"""
    return jsonify({
        'status': 'ok',
        'app': 'Bien Chez Soi',
        'timestamp': datetime.now().isoformat(),
        'config': {
            'openai': bool(Config.OPENAI_API_KEY),
            'anthropic': bool(Config.ANTHROPIC_API_KEY),
            'notion': bool(Config.NOTION_API_KEY and Config.NOTION_SOUMISSIONS_DB),
            'smtp': bool(Config.SMTP_USER and Config.SMTP_PASSWORD)
        }
    })


@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """
    Transcrit un audio en texte (Whisper)
    Input: multipart/form-data avec fichier 'audio', optionnel 'language'
    """
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier audio'}), 400

    audio_file = request.files['audio']
    language = request.form.get('language', 'fr')
    result = transcribe_audio(audio_file, language)
    return jsonify(result)


@app.route('/api/parse', methods=['POST'])
def parse():
    """
    Parse une transcription en données structurées (Claude)
    Input: {'text': str}
    """
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'success': False, 'error': 'Texte manquant'}), 400

    result = parse_voice_input(data['text'])
    if result['success']:
        totals = calculate_totals(result['data'])
        result['totals'] = totals

    return jsonify(result)


@app.route('/api/process-voice', methods=['POST'])
def process_voice():
    """
    Pipeline complet: audio -> transcription -> parsing -> calculs
    Input: multipart/form-data avec fichier 'audio', optionnel 'language'
    """
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier audio'}), 400

    # 1. Transcrire
    audio_file = request.files['audio']
    language = request.form.get('language', 'fr')
    transcription = transcribe_audio(audio_file, language)

    if not transcription['success']:
        return jsonify(transcription)

    # 2. Parser avec IA
    parsed = parse_voice_input(transcription['text'])
    if not parsed['success']:
        return jsonify(parsed)

    # 3. Calculer totaux
    totals = calculate_totals(parsed['data'])

    # 4. Créer session
    session_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    sessions[session_id] = {
        'transcription': transcription['text'],
        'data': parsed['data'],
        'totals': totals,
        'created_at': datetime.now().isoformat()
    }

    return jsonify({
        'success': True,
        'session_id': session_id,
        'transcription': transcription['text'],
        'data': parsed['data'],
        'totals': totals
    })


@app.route('/api/update-session', methods=['POST'])
def update_session():
    """Met à jour une session avec des modifications"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({'success': False, 'error': 'Session invalide ou expirée'}), 400

    session = sessions[session_id]

    # Mise à jour manuelle des champs
    if 'updates' in data:
        for key, value in data['updates'].items():
            session['data'][key] = value

    # Ou mise à jour par texte additionnel (parsing IA)
    if 'additional_text' in data and data['additional_text']:
        result = complete_soumission_data(session['data'], data['additional_text'])
        if result['success']:
            session['data'] = result['data']

    # Recalculer totaux
    session['totals'] = calculate_totals(session['data'])

    return jsonify({
        'success': True,
        'data': session['data'],
        'totals': session['totals']
    })


@app.route('/api/calculate', methods=['POST'])
def calculate():
    """Calcule les totaux pour un aperçu"""
    data = request.json
    totals = calculate_totals(data)
    return jsonify({'success': True, 'totals': totals})


@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """Génère et télécharge le PDF de soumission"""
    data = request.json
    session_id = data.get('session_id')
    signature_data = data.get('signature')  # Base64 PNG de la signature

    # Récupérer les données
    if session_id and session_id in sessions:
        session = sessions[session_id]
        soumission_data = session['data'].copy()
        totals = session['totals']
    else:
        soumission_data = data.get('data', {})
        totals = calculate_totals(soumission_data)

    # Numéro et date
    numero = f"BCS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    soumission_data['numero'] = numero
    soumission_data['date'] = datetime.now().strftime('%Y-%m-%d')

    # Sauvegarder la signature si fournie
    signature_path = None
    if signature_data:
        try:
            # Retirer le préfixe data:image/png;base64,
            if ',' in signature_data:
                signature_data = signature_data.split(',')[1]
            sig_bytes = base64.b64decode(signature_data)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_sig:
                tmp_sig.write(sig_bytes)
                signature_path = tmp_sig.name
        except Exception:
            signature_path = None

    # Générer PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        pdf_path = tmp.name

    result = generate_soumission_pdf(soumission_data, pdf_path, signature_path)

    # Nettoyer la signature temporaire
    if signature_path and os.path.exists(signature_path):
        try:
            os.unlink(signature_path)
        except Exception:
            pass

    if result['success']:
        if session_id and session_id in sessions:
            sessions[session_id]['pdf_path'] = pdf_path
            sessions[session_id]['data']['numero'] = numero

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"soumission-bcs-{numero}.pdf"
        )

    return jsonify(result), 500


@app.route('/api/submit', methods=['POST'])
def submit():
    """
    Soumet la soumission complète:
    - Sauvegarde dans Notion
    - Envoie par courriel si email fourni
    """
    data = request.json
    session_id = data.get('session_id')
    signature_data = data.get('signature')

    if not session_id or session_id not in sessions:
        return jsonify({'success': False, 'error': 'Session invalide ou expirée'}), 400

    session = sessions[session_id]
    soumission_data = session['data']
    totals = session['totals']
    pdf_path = session.get('pdf_path')
    lang = soumission_data.get('langue_client', 'fr')

    results = {'notion': None, 'email': None, 'contact': None}

    # 1. Générer PDF si pas déjà fait
    if not pdf_path or not os.path.exists(pdf_path):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_path = tmp.name

        soumission_data['numero'] = soumission_data.get(
            'numero', f"BCS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # Signature
        signature_path = None
        if signature_data:
            try:
                if ',' in signature_data:
                    signature_data = signature_data.split(',')[1]
                sig_bytes = base64.b64decode(signature_data)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_sig:
                    tmp_sig.write(sig_bytes)
                    signature_path = tmp_sig.name
            except Exception:
                pass

        generate_soumission_pdf(soumission_data, pdf_path, signature_path)

        if signature_path and os.path.exists(signature_path):
            try:
                os.unlink(signature_path)
            except Exception:
                pass

        session['pdf_path'] = pdf_path

    # 2. Créer/trouver contact dans Notion
    contact_result = get_or_create_contact(soumission_data)
    results['contact'] = contact_result

    # 3. Créer soumission dans Notion
    notion_result = create_soumission(soumission_data, totals, pdf_path)
    results['notion'] = notion_result

    # 4. Envoyer courriel si email disponible
    if soumission_data.get('client_email'):
        email_result = send_soumission_email(
            soumission_data['client_email'],
            soumission_data, totals, pdf_path, lang
        )
        results['email'] = email_result

        if email_result.get('success') and notion_result.get('notion_id'):
            update_soumission_status(notion_result['notion_id'], 'Envoyée')

    # 5. Nettoyer
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.unlink(pdf_path)
        except Exception:
            pass

    del sessions[session_id]

    return jsonify({'success': True, 'results': results})


# ============================================================
# ROUTES — HISTORIQUE
# ============================================================

@app.route('/api/history')
def history():
    """Récupère les soumissions récentes depuis Notion"""
    limit = request.args.get('limit', 20, type=int)
    soumissions = get_recent_soumissions(limit)
    return jsonify({'success': True, 'soumissions': soumissions})


@app.route('/api/search')
def search():
    """Recherche de soumissions"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'success': False, 'error': 'Requête vide'}), 400

    results = search_soumissions(query)
    return jsonify({'success': True, 'results': results})


# ============================================================
# ROUTES — CONFIG / PRIX
# ============================================================

@app.route('/api/pricing')
def pricing():
    """Retourne la grille tarifaire pour le frontend"""
    return jsonify({
        'tarif_regulier': Config.TARIF_REGULIER,
        'tarif_affiche': Config.TARIF_AFFICHE,
        'services_carte': Config.SERVICES_CARTE,
        'contrats': Config.CONTRATS,
        'forfaits': Config.FORFAITS_RECURRENTS,
        'addons': Config.ADDONS,
        'categories': Config.CATEGORIES,
        'types_service': Config.TYPES_SERVICE,
        'tps': Config.TPS_RATE,
        'tvq': Config.TVQ_RATE,
    })


@app.route('/api/lang/<lang>')
def get_lang(lang):
    """Retourne les traductions pour une langue"""
    translations = Config.LANGUES.get(lang, Config.LANGUES['fr'])
    return jsonify({'success': True, 'lang': lang, 'translations': translations})


# ============================================================
# SESSIONS DEBUG
# ============================================================

@app.route('/api/sessions')
def list_sessions():
    """Liste les sessions actives (debug)"""
    return jsonify({
        'count': len(sessions),
        'sessions': [
            {'id': sid, 'created': s.get('created_at')}
            for sid, s in sessions.items()
        ]
    })


# ============================================================
# NETTOYAGE
# ============================================================

def cleanup_old_sessions():
    """Supprime les sessions de plus de 1 heure"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=1)

    expired = [
        sid for sid, session in sessions.items()
        if datetime.fromisoformat(session['created_at']) < cutoff
    ]

    for sid in expired:
        if sessions[sid].get('pdf_path') and os.path.exists(sessions[sid]['pdf_path']):
            try:
                os.unlink(sessions[sid]['pdf_path'])
            except Exception:
                pass
        del sessions[sid]

    return len(expired)


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("BIEN CHEZ SOI - Soumission vocale")
    print("Les Entreprises REMES Inc.")
    print("=" * 60)
    print()
    print(f"Démarrage sur http://localhost:8080")
    print()
    print("Configuration:")
    print(f"  OpenAI (Whisper):    {'OK' if Config.OPENAI_API_KEY else 'MANQUANT'}")
    print(f"  Anthropic (Claude):  {'OK' if Config.ANTHROPIC_API_KEY else 'MANQUANT'}")
    print(f"  Notion:              {'OK' if Config.NOTION_API_KEY and Config.NOTION_SOUMISSIONS_DB else 'MANQUANT'}")
    print(f"  Email (SMTP):        {'OK' if Config.SMTP_USER and Config.SMTP_PASSWORD else 'MANQUANT'}")
    print()
    print("=" * 60)

    # SSL pour permettre le micro sur mobile (HTTPS requis)
    ssl_cert = os.path.join(os.path.dirname(__file__), 'cert.pem')
    ssl_key = os.path.join(os.path.dirname(__file__), 'key.pem')

    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print("  Mode HTTPS (micro mobile activé)")
        print()
        print("  Sur mobile: https://192.168.x.x:8080")
        print("  Acceptez l'avertissement de sécurité du certificat")
        app.run(debug=True, host='0.0.0.0', port=8080, ssl_context=(ssl_cert, ssl_key))
    else:
        print("  Mode HTTP (micro localhost seulement)")
        app.run(debug=True, host='0.0.0.0', port=8080)
