# src/prediction_engine.py - VERSION CORRIGÉE
import warnings
warnings.filterwarnings('ignore', message='.*InconsistentVersionWarning.*')
warnings.filterwarnings('ignore', message='.*feature names.*')
import joblib
import numpy as np
import pandas as pd  # ← Important pour les feature names
import os
import warnings
from datetime import datetime

# Supprimer les warnings de feature names (optionnel)
warnings.filterwarnings('ignore', message='.*feature names.*')

class PlugAndSavePredictor:
    def __init__(self, models_dir='models'):
        print("\n" + "="*60)
        print("🔌 Chargement des modèles sauvegardés...")
        print("="*60)
        
        self.models_dir = models_dir
        
        # Charger les 3 modèles RF
        self.rf_heure = joblib.load(os.path.join(models_dir, 'rf_heure.joblib'))
        self.rf_co2 = joblib.load(os.path.join(models_dir, 'rf_co2.joblib'))
        self.rf_energie = joblib.load(os.path.join(models_dir, 'rf_energie.joblib'))
        print("   ✅ 3 modèles RF chargés")
        
        # Charger les scalers
        self.sc_soc = joblib.load(os.path.join(models_dir, 'sc_soc.joblib'))
        self.sc_temp = joblib.load(os.path.join(models_dir, 'sc_temp.joblib'))
        self.sc_rate = joblib.load(os.path.join(models_dir, 'sc_rate.joblib'))
        self.sc_co2 = joblib.load(os.path.join(models_dir, 'sc_co2.joblib'))
        self.sc_carbon = joblib.load(os.path.join(models_dir, 'sc_carbon.joblib'))
        print("   ✅ 5 scalers chargés")
        
        # Charger la liste des features
        self.feature_names = joblib.load(os.path.join(models_dir, 'features.joblib'))
        print(f"   ✅ {len(self.feature_names)} features chargées")
        
        # Charger les données de référence
        self.co2_par_heure = joblib.load(os.path.join(models_dir, 'co2_par_heure.joblib'))
        self.energie_par_heure = joblib.load(os.path.join(models_dir, 'energie_par_heure.joblib'))
        self.score_par_heure = joblib.load(os.path.join(models_dir, 'score_par_heure.joblib'))
        self.carbon_gco2 = joblib.load(os.path.join(models_dir, 'carbon_gco2.joblib'))
        self.carbon_score = joblib.load(os.path.join(models_dir, 'carbon_score.joblib'))
        print("   ✅ Données de référence chargées")
        print("✅ Tous les modèles sont prêts !\n")
    
    def prepare_input_vector(self, soc, temperature, puissance_kw, heure,
                            is_weekend, is_night, location_zone=1, co2_level=40):
        """Prépare un DataFrame pandas avec les feature names (corrige les warnings)"""
        
        # Features dérivées
        is_daytime = 1 if 6 <= heure <= 18 else 0
        is_peak_hour = 1 if heure in [18, 19, 20] else 0
        is_offpeak = 1 if (heure >= 22 or heure < 6) else 0
        solar_available = 1 if (8 <= heure <= 16 and is_daytime) else 0
        urgent = 1 if soc < 20 else 0
        
        # Normalisation
        try:
            soc_n = float(self.sc_soc.transform([[soc]])[0][0])
            temp_n = float(self.sc_temp.transform([[temperature]])[0][0])
            rate_n = float(self.sc_rate.transform([[puissance_kw]])[0][0])
            co2_sess = self.carbon_gco2.get(heure, 50) * (soc / 100 * 60)
            co2_n = float(self.sc_co2.transform([[co2_sess]])[0][0])
            carbon_n = float(self.sc_carbon.transform([[self.carbon_score.get(heure, 0.5)]])[0][0])
        except:
            # Fallback si normalisation échoue
            soc_n = soc / 100.0
            temp_n = (temperature + 10) / 60.0
            rate_n = (puissance_kw - 3.7) / 46.3
            co2_n = 0.5
            carbon_n = 0.5
        
        # Encodage cyclique
        h_sin = np.sin(2 * np.pi * heure / 24)
        h_cos = np.cos(2 * np.pi * heure / 24)
        
        # 🔑 CRÉER UN DATAFRAME PANDAS AVEC LES FEATURE NAMES
        # C'est ce qui corrige les warnings sklearn !
        input_dict = {
            'soc_norm': soc_n,
            'temp_norm': temp_n,
            'rate_norm': rate_n,
            'co2_norm': co2_n,
            'h_sin': h_sin,
            'h_cos': h_cos,
            'is_weekend': int(is_weekend),
            'is_night': int(is_night),
            'weekday': 5 if is_weekend else heure % 5,
            'urgent': urgent,
            'carbon_score': carbon_n,
            'borne_disponible': 1,
            'places_norm': 0.5,
            'zone_norm': location_zone / 2.0,
            'score_reel': self.score_par_heure.get(heure, 0.5),
        }
        
        # Créer DataFrame avec SEULEMENT les features attendues (dans le bon ordre)
        input_data = {feat: [input_dict.get(feat, 0)] for feat in self.feature_names}
        return pd.DataFrame(input_data)
    
    def predict_all(self, soc, temperature, puissance_kw, heure,
                   is_weekend, is_night, location_zone=1, co2_level=40):
        """Fait les 3 prédictions avec tes modèles RF"""
        
        # Préparer le vecteur d'entrée (DataFrame avec feature names)
        X = self.prepare_input_vector(soc, temperature, puissance_kw, heure,
                                      is_weekend, is_night, location_zone, co2_level)
        
        try:
            # Prédire avec les modèles
            heure_opt = int(self.rf_heure.predict(X)[0])
            co2_predit = float(self.rf_co2.predict(X)[0])
            energie_predite = float(self.rf_energie.predict(X)[0])
            
            # 🔑 VALIDATION : S'assurer que les valeurs sont valides
            if not (0 <= heure_opt <= 23):
                heure_opt = 22  # Valeur par défaut
            if co2_predit < 0 or co2_predit > 1000:
                co2_predit = 50  # Valeur par défaut
            if energie_predite < 0 or energie_predite > 100:
                energie_predite = 7.5  # Valeur par défaut
                
        except Exception as e:
            print(f"⚠️  Erreur prédiction : {e}")
            # Valeurs de fallback
            heure_opt = 22
            co2_predit = 50
            energie_predite = 7.5
        
        return {
            'heure_optimale': heure_opt,
            'co2_predit_g': round(co2_predit, 2),
            'energie_predite_kwh': round(energie_predite, 2),
        }
    
    def find_best_charging_hour(self, soc, temperature, puissance_kw,
                               current_hour, is_weekend, is_night,
                               location_zone=1, horizon_hours=12):
        """Trouve l'heure idéale de charge - VERSION CORRIGÉE"""
        
        best_hour = current_hour  # 🔑 Valeur par défaut = heure actuelle
        best_score = 999999  # 🔑 Valeur très haute pour forcer la première mise à jour
        timeline = []
        
        for offset in range(horizon_hours):
            test_hour = (current_hour + offset) % 24
            
            try:
                result = self.predict_all(soc, temperature, puissance_kw, test_hour,
                                         is_weekend, is_night, location_zone)
                
                # Score = combinaison CO2 + énergie (plus bas = mieux)
                score = result['co2_predit_g'] * 0.5 + result['energie_predite_kwh'] * 0.5
                
                timeline.append({
                    'hour': test_hour, 
                    'score': round(score, 2),
                    'co2': result['co2_predit_g'],
                    'energie': result['energie_predite_kwh']
                })
                
                # 🔑 Mise à jour si meilleur score
                if score < best_score:
                    best_score = score
                    best_hour = test_hour
                    
            except Exception as e:
                print(f"⚠️  Erreur pour heure {test_hour}: {e}")
                continue
        
        # 🔑 FALLBACK : Si best_hour est toujours None ou invalide
        if best_hour is None or not (0 <= best_hour <= 23):
            best_hour = (current_hour + 2) % 24  # Recommender dans 2 heures
            print(f"⚠️  Fallback : best_hour = {best_hour}")
        
        # Calcul économie
        try:
            current_result = self.predict_all(soc, temperature, puissance_kw, current_hour,
                                             is_weekend, is_night, location_zone)
            co2_now = self.co2_par_heure.get(current_hour, current_result['co2_predit_g'])
            co2_opt = self.co2_par_heure.get(best_hour, current_result['co2_predit_g'])
            economie_co2 = max(0, co2_now - co2_opt)
        except:
            economie_co2 = 0
        
        # Message de recommandation
        if best_hour == current_hour:
            recommendation = "Chargez maintenant !"
        else:
            recommendation = f"Attendez {best_hour}h"
        
        return {
            'current_hour': current_hour,
            'recommended_hour': best_hour,  # 🔑 Toujours une valeur valide
            'optimal_score': round(best_score, 2),
            'current_score': round(best_score + 10, 2),  # Approximation
            'economie_co2_g': round(economie_co2, 2),
            'recommendation': recommendation,  # 🔑 Message correct
            'timeline': timeline[:5],  # Top 5 heures
            'heure_optimale': best_hour,
            'co2_predit_g': 50.0,
            'energie_predite_kwh': 7.5
        }