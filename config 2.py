#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration et moteur de tarification BCS
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration de l'application"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # Email
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'soumissions@bienchez soi.ca')
    
    # Taxes Québec
    TPS_RATE = 0.05      # 5%
    TVQ_RATE = 0.09975   # 9.975%
    
    # ========================================================================
    # TARIFICATION BCS
    # ========================================================================
    
    # Régulier (sans contrat, 1 payeur)
    PRICING_REGULAR = {
        '1h': {'price': 65, 'rate': 65},
        '2h': {'price': 120, 'rate': 60},
        '3h': {'price': 150, 'rate': 50},
        '4h+': {'base': 180, 'additional_rate': 45}
    }
    
    # À la carte (Animation)
    PRICING_ALACARTE = {
        'rate': 50,
        'minimum_hours': 2,
        'minimum_price': 100
    }
    
    # Groupe RPA (Soins ou Animation)
    PRICING_RPA = {
        'rate': 50,
        'base_hours': 4,
        'base_price': 200,
        'min_people': 5,
        'max_people': 20
    }
    
    # Contrats corporatifs
    PRICING_CONTRACTS = {
        'weekly': {
            'rate': 45,
            'description': '4h/semaine',
            'weekly_hours': 4,
            'weekly_price': 180
        },
        'monthly': {
            'rate': 43,
            'description': '16h/mois',
            'monthly_hours': 16,
            'monthly_price': 688
        },
        'annual': {
            'rate': 40,
            'description': '16h/mois × 12',
            'monthly_hours': 16,
            'annual_price': 7680
        }
    }
    
    # Forfaits récurrents
    PRICING_PACKAGES = {
        'essential': {
            'name': 'Essentiel',
            'frequency': '1x/semaine',
            'monthly_price': 360,
            'rate': 45,
            'hours_per_month': 8
        },
        'comfort': {
            'name': 'Confort',
            'frequency': '2x/semaine',
            'monthly_price': 680,
            'rate': 42.50,
            'hours_per_month': 16
        },
        'premium': {
            'name': 'Premium',
            'frequency': '3x/semaine',
            'monthly_price': 960,
            'rate': 40,
            'hours_per_month': 24
        }
    }


class PricingEngine:
    """Moteur de calcul de tarification"""
    
    @staticmethod
    def calculate_regular(duration: float) -> dict:
        """Calcul tarif régulier"""
        if duration <= 0:
            return {'subtotal': 0, 'rate': 0, 'breakdown': 'Durée invalide'}
        
        if duration == 1:
            subtotal = 65
            rate = 65
            breakdown = "1h × 65$/h"
        elif duration == 2:
            subtotal = 120
            rate = 60
            breakdown = "2h × 60$/h"
        elif duration == 3:
            subtotal = 150
            rate = 50
            breakdown = "3h × 50$/h"
        else:  # 4h+
            subtotal = 180 + (duration - 4) * 45
            rate = 45
            breakdown = f"180$ base + {duration - 4}h × 45$/h"
        
        return {
            'subtotal': round(subtotal, 2),
            'rate': rate,
            'breakdown': breakdown
        }
    
    @staticmethod
    def calculate_alacarte(duration: float) -> dict:
        """Calcul tarif à la carte"""
        if duration < 2:
            duration = 2  # Minimum 2h
        
        subtotal = duration * 50
        
        return {
            'subtotal': round(subtotal, 2),
            'rate': 50,
            'breakdown': f"{duration}h × 50$/h (min 2h)"
        }
    
    @staticmethod
    def calculate_rpa(duration: float, num_people: int) -> dict:
        """Calcul tarif groupe RPA"""
        if num_people < 5 or num_people > 20:
            return {
                'error': 'Groupe RPA: 5-20 personnes',
                'subtotal': 0
            }
        
        if duration < 4:
            duration = 4  # Base 4h
        
        subtotal = duration * 50
        
        return {
            'subtotal': round(subtotal, 2),
            'rate': 50,
            'breakdown': f"{duration}h × 50$/h, {num_people} personnes",
            'num_people': num_people
        }
    
    @staticmethod
    def calculate_contract(contract_type: str, duration: float = None) -> dict:
        """Calcul contrat corporatif"""
        contracts = Config.PRICING_CONTRACTS
        
        if contract_type not in contracts:
            return {'error': 'Type de contrat invalide'}
        
        contract = contracts[contract_type]
        rate = contract['rate']
        
        if contract_type == 'weekly':
            subtotal = contract['weekly_price']
            breakdown = f"4h/sem × {rate}$/h = {subtotal}$/sem"
        elif contract_type == 'monthly':
            subtotal = contract['monthly_price']
            breakdown = f"16h/mois × {rate}$/h = {subtotal}$/mois"
        else:  # annual
            subtotal = contract['annual_price']
            breakdown = f"16h/mois × 12 × {rate}$/h = {subtotal}$/an"
        
        return {
            'subtotal': subtotal,
            'rate': rate,
            'breakdown': breakdown,
            'description': contract['description']
        }
    
    @staticmethod
    def calculate_package(package_type: str) -> dict:
        """Calcul forfait récurrent"""
        packages = Config.PRICING_PACKAGES
        
        if package_type not in packages:
            return {'error': 'Type de forfait invalide'}
        
        package = packages[package_type]
        
        return {
            'subtotal': package['monthly_price'],
            'rate': package['rate'],
            'breakdown': f"{package['name']}: {package['frequency']}",
            'monthly_price': package['monthly_price'],
            'hours_per_month': package['hours_per_month']
        }
    
    @staticmethod
    def apply_taxes(subtotal: float) -> dict:
        """Application TPS/TVQ"""
        tps = subtotal * Config.TPS_RATE
        tvq = subtotal * Config.TVQ_RATE
        total = subtotal + tps + tvq
        
        return {
            'subtotal': round(subtotal, 2),
            'tps': round(tps, 2),
            'tvq': round(tvq, 2),
            'total': round(total, 2)
        }
    
    def calculate(self, service_type: str, duration: float = 0, 
                  contract_type: str = None, package_type: str = None,
                  num_people: int = 1) -> dict:
        """
        Calcul complet basé sur le type de service
        
        Args:
            service_type: 'regular', 'alacarte', 'rpa', 'contract', 'package'
            duration: Durée en heures
            contract_type: 'weekly', 'monthly', 'annual'
            package_type: 'essential', 'comfort', 'premium'
            num_people: Nombre de personnes (pour RPA)
        """
        result = {}
        
        if service_type == 'regular':
            result = self.calculate_regular(duration)
        elif service_type == 'alacarte':
            result = self.calculate_alacarte(duration)
        elif service_type == 'rpa':
            result = self.calculate_rpa(duration, num_people)
        elif service_type == 'contract':
            result = self.calculate_contract(contract_type, duration)
        elif service_type == 'package':
            result = self.calculate_package(package_type)
        else:
            return {'error': 'Type de service invalide'}
        
        # Si erreur, retourner directement
        if 'error' in result:
            return result
        
        # Application des taxes
        subtotal = result['subtotal']
        taxes = self.apply_taxes(subtotal)
        
        return {
            **result,
            **taxes,
            'service_type': service_type
        }
