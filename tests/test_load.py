# test_load.py
import sys
import os

# Ajouter src au chemin Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from prediction_engine import PlugAndSavePredictor

print("╔" + "═"*50 + "╗")
print("║" + "TEST DE CHARGEMENT DES MODÈLES".center(50) + "║")
print("╚" + "═"*50 + "╝\n")

print(f"📁 Dossier courant : {os.getcwd()}")
print(f"📁 Dossier modèles : {os.path.abspath('models')}\n")

# Vérifier les fichiers dans models/
print("📋 Fichiers dans models/ :")
if os.path.exists('models'):
    for f in os.listdir('models'):
        print(f"   - {f}")
else:
    print("   ❌ Dossier models/ introuvable !")

print("\n" + "="*50 + "\n")

try:
    print("🔌 Tentative de chargement des modèles...")
    predictor = PlugAndSavePredictor(models_dir='models')
    
    print("\n✅ SUCCÈS : Tous les modèles sont chargés !\n")
    
    # Test de prédiction rapide
    print("🔬 Test de prédiction rapide...")
    result = predictor.predict_all(
        soc=44,
        temperature=22,
        puissance_kw=7.4,
        heure=21,
        is_weekend=1,
        is_night=0,
        location_zone=1
    )
    
    print(f"   Heure optimale : {result['heure_optimale']}h")
    print(f"   CO2 prédit     : {result['co2_predit_g']}g")
    print(f"   Énergie        : {result['energie_predite_kwh']}kWh")
    print("\n🎉 TEST TERMINÉ AVEC SUCCÈS !")
    
except FileNotFoundError as e:
    print(f"\n❌ ÉCHEC : Fichier manquant")
    print(f"   Erreur : {e}")
    print("\n💡 Solution : Vérifie que tous les .joblib sont dans models/")
    
except Exception as e:
    print(f"\n❌ ÉCHEC : {type(e).__name__}")
    print(f"   Erreur : {e}")
    import traceback
    traceback.print_exc()