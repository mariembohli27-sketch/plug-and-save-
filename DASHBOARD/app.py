# ═══════════════════════════════════════════════════════════════════════════
# app.py — Plug & Save — Serveur Central (VERSION FINALE)
# ═══════════════════════════════════════════════════════════════════════════

from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json, threading, time, joblib, os
import numpy as np
import pandas as pd
from datetime import datetime

app = Flask(__name__)  # ✅ CORRECTION: __name__ avec underscores

# ── Configuration ──────────────────────────────────────────────────────────
MQTT_BROKER = 'localhost'
MQTT_PORT   = 1883

# ✅ CORRECTION: Chemin vers les modèles DANS le dossier dashboard
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'models')  # → dashboard/models/

# ── Chargement modèles IA ──────────────────────────────────────────────────
print("[IA] Chargement des modèles...")
print(f"[IA] Chemin : {MODEL_DIR}")

try:
    rf_heure   = joblib.load(os.path.join(MODEL_DIR, 'rf_heure.joblib'))
    rf_co2     = joblib.load(os.path.join(MODEL_DIR, 'rf_co2.joblib'))
    rf_energie = joblib.load(os.path.join(MODEL_DIR, 'rf_energie.joblib'))
    sc_soc     = joblib.load(os.path.join(MODEL_DIR, 'sc_soc.joblib'))
    sc_temp    = joblib.load(os.path.join(MODEL_DIR, 'sc_temp.joblib'))
    sc_carbon  = joblib.load(os.path.join(MODEL_DIR, 'sc_carbon.joblib'))
    sc_rate    = joblib.load(os.path.join(MODEL_DIR, 'sc_rate.joblib'))
    sc_co2     = joblib.load(os.path.join(MODEL_DIR, 'sc_co2.joblib'))
    score_par_heure   = joblib.load(os.path.join(MODEL_DIR, 'score_par_heure.joblib'))
    co2_par_heure     = joblib.load(os.path.join(MODEL_DIR, 'co2_par_heure.joblib'))
    energie_par_heure = joblib.load(os.path.join(MODEL_DIR, 'energie_par_heure.joblib'))
    CARBON_GCO2       = joblib.load(os.path.join(MODEL_DIR, 'carbon_gco2.joblib'))
    CARBON_SCORE      = joblib.load(os.path.join(MODEL_DIR, 'carbon_score.joblib'))
    MODELE_OK = True
    print("[IA] ✓ Modèles chargés avec succès")
except Exception as e:
    print(f"[IA] ✗ Erreur : {e}")
    MODELE_OK = False

# ── Stockage données temps réel ────────────────────────────────────────────
latest_data = {
    'vehicle':     None,
    'borne':       None,
    'prediction':  None,
    'dashboard':   None,
    'last_update': None,
    'status':      'connected'
}

mqtt_client_global = None

# ── Helpers ────────────────────────────────────────────────────────────────
def get_delai_min(soc):
    if soc < 20:   return 0
    elif soc < 40: return 1
    else:          return 2

def get_zone(lat, lon, lat_ref=36.8065, lon_ref=10.1815):
    dist = np.sqrt((lat - lat_ref)**2 + (lon - lon_ref)**2) * 111
    if dist < 2:   return 2
    elif dist < 8: return 1
    else:          return 0

# ── Prédiction IA ──────────────────────────────────────────────────────────
def faire_prediction(vehicle_data, borne_data=None):
    if not MODELE_OK:
        return {'error': 'Modèle IA non disponible'}

    try:
        soc          = float(vehicle_data.get('soc', 50))
        temperature  = float(vehicle_data.get('temperature',
                        borne_data.get('temperature', 20) if borne_data else 20))
        energie_kwh  = float(vehicle_data.get('energie_kwh', 20))
        puissance_kw = float(vehicle_data.get('puissance_kw', 7.4))
        heure        = int(vehicle_data.get('heure',
                        vehicle_data.get('hour', datetime.now().hour)))
        is_weekend   = int(vehicle_data.get('is_weekend', 0))
        is_night     = int(vehicle_data.get('is_night',
                        1 if (heure >= 21 or heure < 6) else 0))
        lat          = float(vehicle_data.get('lat', 36.8065))
        lon          = float(vehicle_data.get('lon', 10.1815))

        places_libres = int(borne_data.get('places_libres', 2) if borne_data else 2)
        borne_dispo   = int(borne_data.get('disponible', 1)    if borne_data else 1)
        gas_value     = int(borne_data.get('gas', 0)           if borne_data else 0)

        urgent    = 1 if soc < 20 else 0
        delai_min = get_delai_min(soc)
        zone      = get_zone(lat, lon)
        zone_norm = zone / 2.0
        c_score   = CARBON_SCORE.get(heure, 0.5)
        opt_sc    = score_par_heure.get(heure, 0.5)
        co2_sess  = CARBON_GCO2.get(heure, 300) * energie_kwh

        soc_n    = float(sc_soc.transform([[soc]])[0][0])
        temp_n   = float(sc_temp.transform([[temperature]])[0][0])
        rate_n   = float(sc_rate.transform([[puissance_kw]])[0][0])
        carbon_n = float(sc_carbon.transform([[energie_kwh]])[0][0])
        co2_n    = float(sc_co2.transform([[co2_sess]])[0][0])
        places_n = places_libres / 4.0
        weekday  = 5 if is_weekend else heure % 5

        sample = pd.DataFrame([{
            'soc_norm':         soc_n,
            'temp_norm':        temp_n,
            'rate_norm':        rate_n,
            'co2_norm':         co2_n,
            'h_sin':            np.sin(2 * np.pi * heure / 24),
            'h_cos':            np.cos(2 * np.pi * heure / 24),
            'is_weekend':       is_weekend,
            'is_night':         is_night,
            'weekday':          weekday,
            'urgent':           urgent,
            'carbon_score':     c_score,
            'borne_disponible': borne_dispo,
            'places_norm':      places_n,
            'zone_norm':        zone_norm,
            'score_reel':       opt_sc,
        }])

        heure_opt   = int(rf_heure.predict(sample)[0])
        co2_predit  = float(rf_co2.predict(sample)[0])
        nrj_predite = float(rf_energie.predict(sample)[0])

        delai_reel = (heure_opt - heure) % 24
        if not urgent and delai_reel < delai_min:
            heure_opt   = (heure + delai_min) % 24
            co2_predit  = co2_par_heure.get(heure_opt, co2_predit)
            nrj_predite = energie_par_heure.get(heure_opt, nrj_predite)
            delai_reel  = delai_min

        co2_maintenant = co2_par_heure.get(heure, co2_predit)
        economie_co2   = round(max(0, co2_maintenant - co2_predit), 1)

        if urgent:
            message = "URGENT! Rechargez"
        elif delai_reel == 0:
            message = "Rechargez maint."
        else:
            message = f"A {heure_opt}h ({delai_reel}h att.)"

        timeline = []
        for i in range(12):
            h = (heure + i) % 24
            timeline.append({
                'hour':    h,
                'score':   round(score_par_heure.get(h, 0.5) * 100, 1),
                'co2':     round(co2_par_heure.get(h, 0), 1),
                'energie': round(energie_par_heure.get(h, 0), 2),
            })

        return {
            'status': 'success',
            'input': {
                'soc':           soc,
                'temperature':   temperature,
                'heure':         heure,
                'hour':          heure,
                'gas':           gas_value,
                'zone':          zone,
                'location_zone': zone,
                'urgent':        bool(urgent),
            },
            'recommendation': {
                'best_hour':              f"{heure_opt:02d}:00",
                'delai_heures':           delai_reel,
                'message':                message,
                'co2':                    round(co2_predit, 1),
                'economie_co2':           economie_co2,
                'economie_co2_g':         economie_co2,
                'optimal_score':          round(opt_sc * 100, 1),
                'carbon_reseau_maintenant': CARBON_GCO2.get(heure, 300),
                'carbon_reseau_optimal':    CARBON_GCO2.get(heure_opt, 300),
                'timeline':               timeline,
            },
            'predictions': {
                'heure_optimale':      heure_opt,
                'co2_predit_g':        round(co2_predit, 1),
                'energie_predite_kwh': round(nrj_predite, 2),
            },
            'borne': {
                'places_libres': places_libres,
                'disponible':    bool(borne_dispo),
                'temperature':   temperature,
                'gas':           gas_value,
            },
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[IA] ✗ Erreur prédiction : {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

# ── Publication prédiction MQTT ────────────────────────────────────────────
def publier_prediction(client, prediction):
    payload = json.dumps(prediction)
    client.publish("plugsave/ai/response", payload)
    latest_data['prediction'] = prediction
    rec = prediction.get('recommendation', {})
    print(f"[IA] ✓ Publié → Heure: {rec.get('best_hour')}  "
          f"CO2: {rec.get('co2')}g  "
          f"Délai: {rec.get('delai_heures')}h")

# ── Thread MQTT ────────────────────────────────────────────────────────────
def mqtt_loop():
    global mqtt_client_global

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] ✓ Connecté au broker Mosquitto")
            client.subscribe("plugsave/vehicle/+/data")
            client.subscribe("plugsave/vehicle/data")
            client.subscribe("plugsave/borne/data")
            print("[MQTT] ✓ Abonné : vehicle + borne")
        else:
            print(f"[MQTT] ✗ Échec connexion rc={rc}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            topic   = msg.topic
            print(f"\n[MQTT] ← {topic}")

            if 'borne/data' in topic:
                latest_data['borne']       = payload
                latest_data['last_update'] = datetime.now().isoformat()
                print(f"[Borne] Temp={payload.get('temperature')}°C  "
                      f"Gaz={payload.get('gas')}  "
                      f"Places={payload.get('places_libres')}")

                if latest_data['vehicle']:
                    pred = faire_prediction(latest_data['vehicle'],
                                            latest_data['borne'])
                    if 'error' not in pred:
                        publier_prediction(client, pred)

            elif 'vehicle' in topic:
                latest_data['vehicle']     = payload
                latest_data['last_update'] = datetime.now().isoformat()
                print(f"[Véhicule] SOC={payload.get('soc')}%  "
                      f"Heure={payload.get('heure', payload.get('hour'))}h")

                pred = faire_prediction(latest_data['vehicle'],
                                        latest_data['borne'])
                if 'error' not in pred:
                    publier_prediction(client, pred)

        except Exception as e:
            print(f"[MQTT] ✗ Erreur message : {e}")
            import traceback
            traceback.print_exc()

    client = mqtt.Client(
        client_id=f"plugsave_server_{datetime.now().strftime('%H%M%S')}"
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client_global = client
    client.loop_start()

    while True:
        time.sleep(1)

threading.Thread(target=mqtt_loop, daemon=True).start()

# ── Routes Flask ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify(latest_data)

@app.route('/update', methods=['POST'])
def update_from_borne():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON manquant'}), 400

        latest_data['dashboard']   = data
        latest_data['last_update'] = datetime.now().isoformat()

        print(f"[HTTP /update] Borne → "
              f"Temp={data.get('temperature')}°C  "
              f"Gaz={data.get('gas')}  "
              f"Places={data.get('places_libres')}")

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        print(f"[HTTP] ✗ /update erreur : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type doit être application/json'}), 400

        data = request.get_json()
        print(f"[API /predict] Manuel : SOC={data.get('soc')}%  "
              f"Heure={data.get('hour', data.get('heure'))}h")

        pred = faire_prediction(data, latest_data.get('borne'))

        if 'error' in pred:
            return jsonify(pred), 500

        if mqtt_client_global:
            publier_prediction(mqtt_client_global, pred)

        return jsonify(pred), 200

    except Exception as e:
        print(f"[API] ✗ /predict erreur : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test')
def api_test():
    return jsonify({
        'status':    'ok',
        'modele_ia': MODELE_OK,
        'timestamp': datetime.now().isoformat()
    })

# ── Démarrage ──────────────────────────────────────────────────────────────
if __name__ == '__main__':  # ✅ CORRECTION: __name__ et '__main__'
    print("\n" + "="*55)
    print("   Plug & Save — Serveur Central")
    print("="*55)
    print("   Dashboard  : http://localhost:5000")
    print("   API status : http://localhost:5000/api/status")
    print("   API test   : http://localhost:5000/api/test")
    print(f"   Modèle IA  : {'✓ Chargé' if MODELE_OK else '✗ Non disponible'}")
    print(f"   Chemin modèles : {MODEL_DIR}")
    print("="*55 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)