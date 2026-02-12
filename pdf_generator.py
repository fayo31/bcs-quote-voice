"""
BIEN CHEZ SOI - Générateur de PDF pour soumissions
Crée des PDF professionnels avec calcul automatique des taxes Québec
Supporte tous les types de tarification BCS
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime, timedelta
from config import Config, calculer_prix_regulier, calculer_prix_groupe, calculer_prix_partage, calculer_taxes

# Couleurs BCS
BCS_NAVY = HexColor('#1B2A4A')
BCS_GOLD = HexColor('#C8A96E')
BCS_LIGHT = HexColor('#F4F1EC')
BCS_GREEN = HexColor('#2D6A4F')
BCS_GRAY = HexColor('#6B7280')
BCS_WHITE = HexColor('#FFFFFF')


def calculate_totals(data):
    """
    Calcule les totaux avec taxes TPS/TVQ selon le type de service BCS

    Args:
        data: Données de la soumission

    Returns:
        dict: Détail des prix et totaux
    """
    type_service = data.get('type_service', 'Régulier (sans contrat)')
    heures = data.get('nombre_heures', 2) or 2
    nb_personnes = data.get('nombre_personnes', 0) or 0

    prix_base = 0.00
    description_prix = ""
    details_lignes = []

    # --- Calcul selon le type ---
    if type_service == 'Régulier (sans contrat)':
        prix_base = calculer_prix_regulier(heures)
        taux = prix_base / heures if heures > 0 else 0
        description_prix = f"Service régulier — {heures}h"
        details_lignes.append((description_prix, prix_base))

    elif type_service == 'À la carte (Animation)':
        prix_base = heures * Config.TARIF_AFFICHE
        prix_base = max(prix_base, 100.00)  # minimum 2h = 100$
        description_prix = f"Animation & Compagnie — {heures}h × {Config.TARIF_AFFICHE:.0f}$/h"
        details_lignes.append((description_prix, prix_base))

    elif type_service in ('Groupe Soins RPA', 'Groupe Animation RPA'):
        if nb_personnes >= Config.GROUPE_MIN_PERSONNES:
            groupe = calculer_prix_groupe(nb_personnes)
            prix_base = groupe['prix_total']
            description_prix = f"{type_service} — {nb_personnes} pers. × {groupe['heures']}h"
            details_lignes.append((description_prix, prix_base))
            details_lignes.append((f"  ({groupe['prix_par_personne']:.2f}$/personne)", 0))
        else:
            # Fallback: tarif horaire groupe
            heures = max(heures, 4)
            prix_base = heures * Config.GROUPE_TAUX_HORAIRE
            description_prix = f"{type_service} — {heures}h × {Config.GROUPE_TAUX_HORAIRE:.0f}$/h"
            details_lignes.append((description_prix, prix_base))

    elif type_service == 'Partagé voisins RPA':
        nb_voisins = data.get('nombre_personnes', 4) or 4
        partage = calculer_prix_partage(nb_voisins)
        prix_base = partage['prix_total']
        description_prix = f"Bloc partagé {partage['nb_voisins']} voisins — {Config.PARTAGE_BLOC_HEURES}h"
        details_lignes.append((description_prix, prix_base))
        details_lignes.append((f"  ({partage['cout_par_voisin']:.2f}$/voisin)", 0))

    elif type_service == 'Contrat corporatif':
        type_contrat = data.get('type_contrat', 'hebdomadaire') or 'hebdomadaire'
        contrat = Config.CONTRATS.get(type_contrat, Config.CONTRATS['hebdomadaire'])
        if heures:
            prix_base = heures * contrat['taux']
        else:
            prix_base = contrat['total_min']
        description_prix = f"Contrat {type_contrat} — {heures}h × {contrat['taux']:.0f}$/h"
        details_lignes.append((description_prix, prix_base))

    elif type_service == 'Forfait récurrent':
        forfait_nom = data.get('forfait_recurrent', 'Essentiel') or 'Essentiel'
        forfait = Config.FORFAITS_RECURRENTS.get(forfait_nom, Config.FORFAITS_RECURRENTS['Essentiel'])
        prix_base = forfait['prix_mois']
        description_prix = f"Forfait {forfait_nom} — {forfait['heures_mois']}h/mois ({forfait['frequence']})"
        details_lignes.append((description_prix, prix_base))

    else:
        prix_base = calculer_prix_regulier(heures)
        description_prix = f"Service — {heures}h"
        details_lignes.append((description_prix, prix_base))

    # --- Add-ons ---
    addons_total = 0.00
    addon_details = []

    for addon_key, addon_info in Config.ADDONS.items():
        if data.get(f'addon_{addon_key}', False):
            addons_total += addon_info['prix']
            addon_details.append((addon_info['nom'], addon_info['prix']))
            details_lignes.append((f"+ {addon_info['nom']}", addon_info['prix']))

    # --- Calculs finaux ---
    sous_total = prix_base + addons_total
    taxes = calculer_taxes(sous_total)

    return {
        'prix_base': prix_base,
        'description_prix': description_prix,
        'details_lignes': details_lignes,
        'addons_total': addons_total,
        'addon_details': addon_details,
        'sous_total': sous_total,
        'tps': taxes['tps'],
        'tvq': taxes['tvq'],
        'total': taxes['total'],
        'type_service': type_service,
        'heures': heures,
        'nb_personnes': nb_personnes,
    }


def generate_soumission_pdf(data, output_path, signature_path=None):
    """
    Génère un PDF de soumission Bien Chez Soi

    Args:
        data: Données de la soumission (dict)
        output_path: Chemin du fichier PDF à créer
        signature_path: Chemin vers l'image de la signature (optionnel)

    Returns:
        dict: {'success': bool, 'path': str, 'totals': dict}
    """
    try:
        totals = calculate_totals(data)
        lang = data.get('langue_client', 'fr')
        t = Config.LANGUES.get(lang, Config.LANGUES['fr'])

        numero = data.get('numero', f"BCS-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        date_soumission = datetime.now()
        date_expiration = date_soumission + timedelta(days=14)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        # Styles
        style_title = ParagraphStyle(
            'Title', fontSize=30, textColor=BCS_NAVY,
            spaceAfter=4, alignment=TA_CENTER, fontName='Helvetica-Bold'
        )
        style_subtitle = ParagraphStyle(
            'Subtitle', fontSize=13, textColor=BCS_GOLD,
            spaceAfter=20, alignment=TA_CENTER, fontName='Helvetica'
        )
        style_section = ParagraphStyle(
            'Section', fontSize=12, textColor=BCS_NAVY,
            spaceBefore=15, spaceAfter=8, fontName='Helvetica-Bold'
        )
        style_normal = ParagraphStyle(
            'BodyText', fontSize=10, leading=14
        )
        style_small = ParagraphStyle(
            'Small', fontSize=9, textColor=BCS_GRAY, alignment=TA_CENTER
        )
        style_conditions = ParagraphStyle(
            'Conditions', fontSize=9, leading=13, textColor=BCS_GRAY
        )

        story = []

        # === EN-TÊTE ===
        story.append(Paragraph("Bien Chez Soi", style_title))
        story.append(Paragraph("Soins &amp; Compagnie à domicile — Brossard", style_subtitle))

        # Numéro et date
        date_label = "Date" if lang == 'fr' else "Date"
        valid_label = "Valide jusqu'au" if lang == 'fr' else "Valid until"
        soumission_label = "Soumission" if lang == 'fr' else "Quote"

        header_data = [
            [f"{soumission_label}: {numero}", f"{date_label}: {date_soumission.strftime('%Y-%m-%d')}"],
            ["", f"{valid_label}: {date_expiration.strftime('%Y-%m-%d')}"]
        ]
        header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), BCS_GRAY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 20))

        # === CLIENT ===
        story.append(Paragraph(t['label_client'].upper(), style_section))

        client_data = [
            [f"{t['label_name']}:", data.get('client_nom') or '—'],
            [f"{t['label_phone']}:", data.get('client_telephone') or '—'],
            [f"{t['label_email']}:", data.get('client_email') or '—'],
            [f"{t['label_address']}:", data.get('adresse_service') or '—'],
        ]
        client_table = Table(client_data, colWidths=[1.8 * inch, 5.2 * inch])
        client_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), BCS_GRAY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(client_table)

        # === SERVICE ===
        service_label = "SERVICE DEMANDÉ" if lang == 'fr' else "REQUESTED SERVICE"
        story.append(Paragraph(service_label, style_section))

        type_label = t['label_type']
        cat_label = t['label_category']
        desc_label = t['label_description']
        hrs_label = t['label_hours']

        service_rows = [
            [f"{type_label}:", totals['type_service']],
            [f"{cat_label}:", data.get('categorie') or '—'],
            [f"{hrs_label}:", f"{totals['heures']}h"],
            [f"{desc_label}:", data.get('description_service') or '—'],
        ]
        if totals['nb_personnes'] and totals['nb_personnes'] > 0:
            pers_label = t['label_persons']
            service_rows.insert(3, [f"{pers_label}:", str(totals['nb_personnes'])])

        service_table = Table(service_rows, colWidths=[1.8 * inch, 5.2 * inch])
        service_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), BCS_GRAY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(service_table)

        # === PRIX ===
        prix_label = "DÉTAIL DES PRIX" if lang == 'fr' else "PRICE DETAILS"
        story.append(Paragraph(prix_label, style_section))

        desc_col = "Description"
        montant_col = "Montant" if lang == 'fr' else "Amount"
        prix_rows = [[desc_col, montant_col]]

        for desc, montant in totals['details_lignes']:
            if montant > 0:
                prix_rows.append([desc, f"{montant:.2f} $"])
            else:
                prix_rows.append([desc, ""])

        prix_rows.append(["", ""])
        prix_rows.append([t['sous_total'], f"{totals['sous_total']:.2f} $"])
        prix_rows.append([t['tps'], f"{totals['tps']:.2f} $"])
        prix_rows.append([t['tvq'], f"{totals['tvq']:.2f} $"])
        prix_rows.append([t['total'], f"{totals['total']:.2f} $"])

        prix_table = Table(prix_rows, colWidths=[5 * inch, 2 * inch])
        prix_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BCS_LIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 13),
            ('TEXTCOLOR', (0, -1), (-1, -1), BCS_NAVY),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, BCS_NAVY),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BCS_GRAY),
        ]))
        story.append(prix_table)

        # === SIGNATURE CLIENT ===
        story.append(Spacer(1, 20))
        story.append(Paragraph(t['signature_title'], style_section))

        if signature_path:
            try:
                sig_img = Image(signature_path, width=3 * inch, height=1 * inch)
                story.append(sig_img)
            except Exception:
                story.append(Paragraph("_" * 50, style_normal))
        else:
            # Ligne de signature vide
            sig_data = [
                ["Signature: ________________________", f"Date: ________________________"],
            ]
            sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
            sig_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 20),
            ]))
            story.append(sig_table)

        # === CONDITIONS ===
        story.append(Spacer(1, 15))
        story.append(Paragraph(t['conditions_title'], style_section))

        if lang == 'fr':
            conditions_text = """
            &bull; Paiement dû à la complétion du service<br/>
            &bull; Annulation sans frais 24h avant le service<br/>
            &bull; Cette soumission est valide pour 14 jours<br/>
            &bull; Les taxes TPS/TVQ sont calculées selon les taux en vigueur au Québec<br/>
            &bull; Services fournis par Les Entreprises REMES Inc.
            """
        else:
            conditions_text = """
            &bull; Payment due upon service completion<br/>
            &bull; Free cancellation 24h before service<br/>
            &bull; This quote is valid for 14 days<br/>
            &bull; GST/QST taxes calculated per Quebec rates<br/>
            &bull; Services provided by Les Entreprises REMES Inc.
            """
        story.append(Paragraph(conditions_text, style_conditions))

        # === PIED DE PAGE ===
        story.append(Spacer(1, 25))

        footer_data = [
            [f"{Config.BCS_NAME} — Soins & Compagnie à domicile"],
            [Config.BCS_LEGAL_NAME],
            [Config.BCS_ADDRESS],
            [f"{Config.BCS_EMAIL} | {Config.BCS_PHONE}"],
            [f"NEQ: {Config.BCS_NEQ}"],
        ]
        footer_table = Table(footer_data, colWidths=[7 * inch])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), BCS_GRAY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(footer_table)

        doc.build(story)

        return {
            'success': True,
            'path': output_path,
            'totals': totals,
            'numero': numero
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
