"""
BIEN CHEZ SOI - Service d'envoi de courriels
Envoie les soumissions par courriel avec PDF en pièce jointe
Bilingue FR/EN
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import Config
import os


def send_soumission_email(to_email, data, totals, pdf_path, lang='fr'):
    """
    Envoie la soumission par courriel avec le PDF en pièce jointe

    Args:
        to_email: Adresse courriel du destinataire
        data: Données de la soumission
        totals: Totaux calculés
        pdf_path: Chemin vers le fichier PDF
        lang: Langue ('fr' ou 'en')

    Returns:
        dict: {'success': bool, 'message': str}
    """
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        return {
            'success': False,
            'error': 'Configuration SMTP manquante. Ajoutez SMTP_USER et SMTP_PASSWORD dans .env'
        }

    if not to_email:
        return {'success': False, 'error': 'Adresse courriel manquante'}

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{Config.BCS_NAME} <{Config.SMTP_USER}>"
        msg['To'] = to_email

        numero = data.get('numero', 'XXX')

        if lang == 'en':
            msg['Subject'] = f"Bien Chez Soi - Your Quote #{numero}"
            html_body = _build_email_en(data, totals, numero)
            text_body = _build_text_en(data, totals, numero)
        else:
            msg['Subject'] = f"Bien Chez Soi - Votre soumission #{numero}"
            html_body = _build_email_fr(data, totals, numero)
            text_body = _build_text_fr(data, totals, numero)

        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Pièce jointe PDF
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                filename = f"soumission-bcs-{numero}.pdf"
                pdf_attachment.add_header(
                    'Content-Disposition', 'attachment', filename=filename
                )
                msg.attach(pdf_attachment)

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)

        return {'success': True, 'message': f'Courriel envoyé à {to_email}'}

    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'error': 'Erreur authentification SMTP.'}
    except smtplib.SMTPException as e:
        return {'success': False, 'error': f'Erreur SMTP: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _build_email_fr(data, totals, numero):
    return f"""<!DOCTYPE html>
<html>
<head><style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1B2A4A; line-height: 1.6; }}
    .header {{ background: linear-gradient(135deg, #1B2A4A, #2d4a7c); color: white; padding: 30px; text-align: center; border-radius: 0 0 12px 12px; }}
    .header h1 {{ margin: 0; font-size: 28px; letter-spacing: 2px; }}
    .header p {{ margin: 5px 0 0; color: #C8A96E; }}
    .content {{ padding: 25px; }}
    .summary {{ background: #F4F1EC; padding: 20px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #C8A96E; }}
    .total {{ font-size: 26px; color: #2D6A4F; font-weight: bold; }}
    .footer {{ color: #6B7280; font-size: 12px; text-align: center; padding: 20px; border-top: 1px solid #e2e8f0; }}
</style></head>
<body>
    <div class="header">
        <h1>Bien Chez Soi</h1>
        <p>Soins &amp; Compagnie à domicile</p>
    </div>
    <div class="content">
        <p>Bonjour {data.get('client_nom') or ''},</p>
        <p>Merci de votre confiance envers Bien Chez Soi!</p>
        <p>Vous trouverez ci-joint votre soumission pour le service demandé.</p>
        <div class="summary">
            <h3 style="margin-top:0; color:#1B2A4A;">Résumé</h3>
            <p><strong>Numéro:</strong> {numero}</p>
            <p><strong>Service:</strong> {data.get('description_service', '—')}</p>
            <p><strong>Type:</strong> {totals.get('type_service', '—')}</p>
            <p class="total">Total: {totals['total']:.2f} $ CAD</p>
            <p style="font-size:12px; color:#6B7280;">(Taxes TPS/TVQ incluses)</p>
        </div>
        <p>Cette soumission est valide pour <strong>14 jours</strong>.</p>
        <p>Pour confirmer, répondez à ce courriel ou appelez-nous au {Config.BCS_PHONE}.</p>
        <p>Cordialement,<br><strong>L'équipe Bien Chez Soi</strong></p>
    </div>
    <div class="footer">
        <p>{Config.BCS_NAME} — {Config.BCS_LEGAL_NAME}<br>
        {Config.BCS_ADDRESS}<br>
        {Config.BCS_EMAIL} | {Config.BCS_PHONE}<br>
        NEQ: {Config.BCS_NEQ}</p>
    </div>
</body></html>"""


def _build_email_en(data, totals, numero):
    return f"""<!DOCTYPE html>
<html>
<head><style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1B2A4A; line-height: 1.6; }}
    .header {{ background: linear-gradient(135deg, #1B2A4A, #2d4a7c); color: white; padding: 30px; text-align: center; border-radius: 0 0 12px 12px; }}
    .header h1 {{ margin: 0; font-size: 28px; letter-spacing: 2px; }}
    .header p {{ margin: 5px 0 0; color: #C8A96E; }}
    .content {{ padding: 25px; }}
    .summary {{ background: #F4F1EC; padding: 20px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #C8A96E; }}
    .total {{ font-size: 26px; color: #2D6A4F; font-weight: bold; }}
    .footer {{ color: #6B7280; font-size: 12px; text-align: center; padding: 20px; border-top: 1px solid #e2e8f0; }}
</style></head>
<body>
    <div class="header">
        <h1>Bien Chez Soi</h1>
        <p>Home Care &amp; Companionship</p>
    </div>
    <div class="content">
        <p>Hello {data.get('client_nom') or ''},</p>
        <p>Thank you for choosing Bien Chez Soi!</p>
        <p>Please find attached your quote for the requested service.</p>
        <div class="summary">
            <h3 style="margin-top:0; color:#1B2A4A;">Summary</h3>
            <p><strong>Quote #:</strong> {numero}</p>
            <p><strong>Service:</strong> {data.get('description_service', '—')}</p>
            <p><strong>Type:</strong> {totals.get('type_service', '—')}</p>
            <p class="total">Total: {totals['total']:.2f} $ CAD</p>
            <p style="font-size:12px; color:#6B7280;">(GST/QST included)</p>
        </div>
        <p>This quote is valid for <strong>14 days</strong>.</p>
        <p>To confirm, reply to this email or call us at {Config.BCS_PHONE}.</p>
        <p>Best regards,<br><strong>The Bien Chez Soi Team</strong></p>
    </div>
    <div class="footer">
        <p>{Config.BCS_NAME} — {Config.BCS_LEGAL_NAME}<br>
        {Config.BCS_ADDRESS}<br>
        {Config.BCS_EMAIL} | {Config.BCS_PHONE}<br>
        NEQ: {Config.BCS_NEQ}</p>
    </div>
</body></html>"""


def _build_text_fr(data, totals, numero):
    return f"""Bonjour {data.get('client_nom') or ''},

Merci de votre confiance envers Bien Chez Soi!

RÉSUMÉ
------
Numéro: {numero}
Service: {data.get('description_service', '—')}
Type: {totals.get('type_service', '—')}
Total: {totals['total']:.2f} $ CAD (taxes incluses)

Cette soumission est valide pour 14 jours.

Pour confirmer, répondez à ce courriel ou appelez-nous au {Config.BCS_PHONE}.

Cordialement,
L'équipe Bien Chez Soi

---
{Config.BCS_NAME} — {Config.BCS_LEGAL_NAME}
{Config.BCS_ADDRESS}
{Config.BCS_EMAIL} | {Config.BCS_PHONE}
NEQ: {Config.BCS_NEQ}"""


def _build_text_en(data, totals, numero):
    return f"""Hello {data.get('client_nom') or ''},

Thank you for choosing Bien Chez Soi!

SUMMARY
-------
Quote #: {numero}
Service: {data.get('description_service', '—')}
Type: {totals.get('type_service', '—')}
Total: {totals['total']:.2f} $ CAD (taxes included)

This quote is valid for 14 days.

To confirm, reply to this email or call us at {Config.BCS_PHONE}.

Best regards,
The Bien Chez Soi Team

---
{Config.BCS_NAME} — {Config.BCS_LEGAL_NAME}
{Config.BCS_ADDRESS}
{Config.BCS_EMAIL} | {Config.BCS_PHONE}
NEQ: {Config.BCS_NEQ}"""


def send_notification_email(subject, body_text):
    """Envoie une notification interne à l'équipe BCS"""
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        return {'success': False, 'error': 'SMTP non configuré'}

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{Config.BCS_NAME} <{Config.SMTP_USER}>"
        msg['To'] = Config.BCS_EMAIL
        msg['Subject'] = f"[BCS] {subject}"
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}
