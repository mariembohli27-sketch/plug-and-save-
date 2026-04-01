# create_scalers.py
import joblib
from sklearn.preprocessing import StandardScaler
import os

os.chdir('c:\\Users\\User\\Desktop\\finaliot')

print("🔧 Création des scalers manquants...\n")

# Scaler SOC (0-100%)
sc_soc = StandardScaler()
sc_soc.fit([[0], [100]])
joblib.dump(sc_soc, 'models/sc_soc.joblib')
print("✅ sc_soc.joblib créé")

# Scaler Température (-10 à 50°C)
sc_temp = StandardScaler()
sc_temp.fit([[-10], [50]])
joblib.dump(sc_temp, 'models/sc_temp.joblib')
print("✅ sc_temp.joblib créé")

# Scaler Puissance (3.7 à 50 kW)
sc_rate = StandardScaler()
sc_rate.fit([[3.7], [50]])
joblib.dump(sc_rate, 'models/sc_rate.joblib')
print("✅ sc_rate.joblib créé")

# Scaler CO2 (0 à 5000 g)
sc_co2 = StandardScaler()
sc_co2.fit([[0], [5000]])
joblib.dump(sc_co2, 'models/sc_co2.joblib')
print("✅ sc_co2.joblib créé")

print("\n✅ Tous les scalers sont créés !")
print("\n📁 Vérifie avec : dir models")