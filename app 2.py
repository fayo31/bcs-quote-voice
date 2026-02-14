#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bien Chez Soi - Application de soumission vocale
Serveur Flask avec support dictée et mode écrit
"""

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import os
import json
from datetime import datetime
import logging
from pathlib import Path

# Imports des modules internes
from config import Config, PricingEngine
from voice_processor import VoiceProcessor
from ai_parser import AIParser

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config.from_object(Config)

# Initialisation des services
voice_processor = VoiceProcessor()
ai_parser = AIParser()
pricing_engine = PricingEngine()

# Dossier pour sauvegarder les fichiers
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

HISTORY_FILE = Path('history.json')
if not HISTORY_FILE.exists():
    HISTORY_FILE.write_text('[]')


# ============================================================================
# ROUTES PRINCIPALES
# ============================================================================

@app.route('/')
def index():
    """Interface principale"""
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()


@app.route('/api/health', methods=['GET'])
def health():
    """Vérification de l'état du serveur"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'whisper': voice_processor.is_ready(),
            'ai_parser': ai_parser.is_ready(),
            'pricing': True
        }
    })


# ============================================================================
# TRAITEMENT VOCAL TEMPS RÉEL
# ============================================================================

@app.route('/api/transcribe-chunk', methods=['POST'])
def transcribe_chunk():
    """
    Transcription d'un chunk audio en temps réel
    Utilisé pour le mode dictée avec remplissage continu
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'Aucun fichier audio'}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'fr')
        
        # Sauvegarde temporaire
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        temp_path = UPLOAD_FOLDER / f'chunk_{timestamp}.wav'
        audio_file.save(temp_path)
        
        # Transcription
        transcription = voice_processor.transcribe(temp_path, language)
        
        # Nettoyage
        temp_path.unlink()
        
        logger.info(f"Transcription chunk: {transcription[:100]}...")
        
        return jsonify({
            'success': True,
            'text': transcription,
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.error(f"Erreur transcription: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/parse-incremental', methods=['POST'])
def parse_incremental():
    """
    Parse incrémental du texte pour remplissage en temps réel
    Utilisé pour mettre à jour le formulaire pendant la dictée
    """
    try:
        data = request.json
        text = data.get('text', '')
        current_data = data.get('currentData', {})
        language = data.get('language', 'fr')
        
        if not text:
            return jsonify({'error': 'Texte vide'}), 400
        
        # Parse avec contexte des données actuelles
        parsed = ai_parser.parse_incremental(text, current_data, language)
        
        return jsonify({
            'success': True,
            'data': parsed,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur parsing incrémental: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# TRAITEMENT MODE ÉCRIT
# ============================================================================

@app.route('/api/parse-text', methods=['POST'])
def parse_text():
    """
    Parse du texte en mode écrit
    Analyse le texte tapé pour extraire les informations
    """
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'fr')
        
        if not text:
            return jsonify({'error': 'Texte vide'}), 400
        
        # Parse complet
        parsed = ai_parser.parse_full(text, language)
        
        return jsonify({
            'success': True,
            'data': parsed,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur parsing texte: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CALCUL DE PRIX
# ============================================================================

@app.route('/api/calculate-price', methods=['POST'])
def calculate_price():
    """
    Calcul du prix basé sur les paramètres de la soumission
    """
    try:
        data = request.json
        
        service_type = data.get('serviceType', 'regular')
        duration = float(data.get('duration', 0))
        contract_type = data.get('contractType')
        package_type = data.get('packageType')
        num_people = int(data.get('numPeople', 1))
        
        # Calcul via le moteur de tarification
        result = pricing_engine.calculate(
            service_type=service_type,
            duration=duration,
            contract_type=contract_type,
            package_type=package_type,
            num_people=num_people
        )
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Erreur calcul prix: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pricing', methods=['GET'])
def get_pricing():
    """
    Retourne la grille tarifaire complète
    """
    return jsonify({
        'regular': Config.PRICING_REGULAR,
        'alacarte': Config.PRICING_ALACARTE,
        'rpa': Config.PRICING_RPA,
        'contracts': Config.PRICING_CONTRACTS,
        'packages': Config.PRICING_PACKAGES,
        'taxes': {
            'tps': Config.TPS_RATE,
            'tvq': Config.TVQ_RATE,
            'total': Config.TPS_RATE + Config.TVQ_RATE
        }
    })


# ============================================================================
# GÉNÉRATION PDF
# ============================================================================

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Génération du PDF de soumission
    """
    try:
        data = request.json
        
        # Importation différée pour éviter les erreurs si module manquant
        try:
            from pdf_generator import PDFGenerator
            pdf_gen = PDFGenerator()
        except ImportError:
            logger.warning("Module PDF non disponible, création d'un placeholder")
            return jsonify({
                'success': True,
                'message': 'PDF généré (placeholder)',
                'filename': 'soumission_placeholder.pdf'
            })
        
        # Génération du PDF
        pdf_path = pdf_gen.generate(data)
        
        return jsonify({
            'success': True,
            'filename': pdf_path.name,
            'path': str(pdf_path)
        })
        
    except Exception as e:
        logger.error(f"Erreur génération PDF: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SOUMISSION ET HISTORIQUE
# ============================================================================

@app.route('/api/submit', methods=['POST'])
def submit_quote():
    """
    Soumission complète: sauvegarde, PDF, email, Notion
    """
    try:
        data = request.json
        
        # Ajout timestamp et ID
        data['timestamp'] = datetime.now().isoformat()
        data['id'] = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Sauvegarde dans l'historique
        history = json.loads(HISTORY_FILE.read_text())
        history.append(data)
        HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))
        
        # TODO: Générer PDF
        # TODO: Envoyer email
        # TODO: Sauvegarder dans Notion
        
        logger.info(f"Soumission {data['id']} sauvegardée")
        
        return jsonify({
            'success': True,
            'id': data['id'],
            'message': 'Soumission enregistrée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur soumission: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Récupération de l'historique des soumissions
    """
    try:
        history = json.loads(HISTORY_FILE.read_text())
        
        # Filtres optionnels
        limit = request.args.get('limit', type=int)
        if limit:
            history = history[-limit:]
        
        return jsonify({
            'success': True,
            'count': len(history),
            'data': history
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération historique: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# TRADUCTIONS
# ============================================================================

@app.route('/api/lang/<lang>', methods=['GET'])
def get_translations(lang):
    """
    Retourne les traductions pour la langue demandée
    """
    translations = {
        'fr': {
            'appTitle': 'Bien Chez Soi - Soumission Vocale',
            'modeDictation': 'Mode Dictée',
            'modeText': 'Mode Écrit',
            'startRecording': 'Démarrer l\'enregistrement',
            'stopRecording': 'Arrêter l\'enregistrement',
            'processing': 'Traitement en cours...',
            'clientInfo': 'Informations Client',
            'clientName': 'Nom du client',
            'clientEmail': 'Courriel',
            'clientPhone': 'Téléphone',
            'serviceInfo': 'Informations Service',
            'serviceType': 'Type de service',
            'duration': 'Durée (heures)',
            'numPeople': 'Nombre de personnes',
            'pricing': 'Tarification',
            'subtotal': 'Sous-total',
            'tps': 'TPS (5%)',
            'tvq': 'TVQ (9.975%)',
            'total': 'Total',
            'submit': 'Soumettre',
            'clear': 'Effacer',
            'history': 'Historique'
        },
        'en': {
            'appTitle': 'Bien Chez Soi - Voice Quote',
            'modeDictation': 'Dictation Mode',
            'modeText': 'Text Mode',
            'startRecording': 'Start Recording',
            'stopRecording': 'Stop Recording',
            'processing': 'Processing...',
            'clientInfo': 'Client Information',
            'clientName': 'Client Name',
            'clientEmail': 'Email',
            'clientPhone': 'Phone',
            'serviceInfo': 'Service Information',
            'serviceType': 'Service Type',
            'duration': 'Duration (hours)',
            'numPeople': 'Number of People',
            'pricing': 'Pricing',
            'subtotal': 'Subtotal',
            'tps': 'GST (5%)',
            'tvq': 'QST (9.975%)',
            'total': 'Total',
            'submit': 'Submit',
            'clear': 'Clear',
            'history': 'History'
        }
    }
    
    return jsonify(translations.get(lang, translations['fr']))


# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Démarrage serveur BCS sur port {port}")
    logger.info(f"📱 Interface disponible sur http://localhost:{port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
