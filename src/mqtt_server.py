## dashboard/app.py - VERSION PROPRE ET UNIQUE
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json
import threading
from datetime import datetime
import time  # ← Ajouter en haut de app.py
app = Flask(__name__)

# ── Configuration MQTT ────────────────────────────────────────────────────
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883

# ── Stockage des données ──────────────────────────────────────────────────
latest_data = {
    'vehicle': None,
    'prediction': None,
    'last_update': None,
    'status': 'connected'
}

# ── Thread MQTT ───────────────────────────────────────────────────────────
def mqtt_loop():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Dashboard MQTT connecté")
            client.subscribe("plugsave/vehicle/+/data")
            client.subscribe("plugsave/ai/response")
        else:
            print(f"❌ Échec connexion MQTT (rc={rc})")
    
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            if 'vehicle' in msg.topic:
                latest_data['vehicle'] = payload
            elif 'ai/response' in msg.topic:
                latest_data['prediction'] = payload
            latest_data['last_update'] = datetime.now().isoformat()
        except Exception as e:
            print(f"❌ Erreur MQTT : {e}")
    
    client = mqtt.Client(client_id=f"dash_{datetime.now().strftime('%H%M%S')}")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()  # ← Non-bloquant, parfait pour thread
    # Garder le thread actif
    while True:
        time.sleep(1)
# Démarrer MQTT en arrière-plan
threading.Thread(target=mqtt_loop, daemon=True).start()

# ── ROUTE 1 : Page d'accueil ──────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── ROUTE 2 : Statut API ──────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    return jsonify(latest_data)

# ── ROUTE 3 : Envoyer Prédiction (Formulaire Manuel) ─────────────────────
@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type doit être application/json'}), 400
        
        data = request.get_json()
        print(f"📤 Données reçues : {data}")
        
        client = mqtt.Client(client_id=f"dash_{datetime.now().strftime('%H%M%S')}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish("plugsave/vehicle/VEH_001/data", json.dumps(data))
        client.disconnect()
        
        return jsonify({'status': 'success', 'message': 'Données envoyées'}), 200
        
    except Exception as e:
        print(f"❌ Erreur api_predict : {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ── ROUTE 4 : Test (Optionnel) ────────────────────────────────────────────
@app.route('/api/test')
def api_test():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

# ── Démarrage ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Dashboard Plug & Save")
    print("="*50)
    print("📡 Accueil  : http://localhost:5000")
    print("🧪 Test API : http://localhost:5000/api/test")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)