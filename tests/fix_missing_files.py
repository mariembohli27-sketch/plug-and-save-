# fix_missing_files.py
import joblib
import os

os.chdir('c:\\Users\\User\\Desktop\\finaliot')

print("🔧 Création des fichiers manquants...\n")

# Fichier 1: score_par_heure.joblib
# Score d'optimalité par heure (0-1, plus bas = mieux)
score_par_heure = {
    0: 0.2, 1: 0.15, 2: 0.1, 3: 0.1, 4: 0.15, 5: 0.2,  # Nuit = bon
    6: 0.4, 7: 0.5, 8: 0.6, 9: 0.6, 10: 0.5, 11: 0.5,   # Matin = moyen
    12: 0.5, 13: 0.5, 14: 0.6, 15: 0.6, 16: 0.5, 17: 0.7, # Après-midi
    18: 0.9, 19: 1.0, 20: 0.9,  # Pic 18h-20h = mauvais
    21: 0.6, 22: 0.3, 23: 0.2   # Soirée = bon
}
joblib.dump(score_par_heure, 'models/score_par_heure.joblib')
print("✅ score_par_heure.joblib créé")

# Fichier 2: carbon_gco2.joblib (au cas où)
carbon_gco2 = {h: 40 if 22 <= h or h < 6 else (90 if 18 <= h <= 20 else 60) for h in range(24)}
joblib.dump(carbon_gco2, 'models/carbon_gco2.joblib')
print("✅ carbon_gco2.joblib mis à jour")

# Fichier 3: carbon_score.joblib (au cas où)
carbon_score = {h: 0.3 if 22 <= h or h < 6 else (0.8 if 18 <= h <= 20 else 0.5) for h in range(24)}
joblib.dump(carbon_score, 'models/carbon_score.joblib')
print("✅ carbon_score.joblib mis à jour")

print("\n✅ Tous les fichiers manquants sont créés !")
print("\n📁 Vérifie avec : dir models")