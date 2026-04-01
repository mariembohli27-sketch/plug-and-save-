// dashboard/static/js/main.js
const API_BASE = '';
const UPDATE_INTERVAL = 2000;

let state = {
    vehicle: null,
    prediction: null,
};

// ── Initialisation ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔋 Dashboard Plug & Save initialisé');
    addLog('Dashboard chargé', 'info');
    setInterval(fetchUpdates, UPDATE_INTERVAL);
    
    const testForm = document.getElementById('testForm');
    if (testForm) {
        testForm.addEventListener('submit', sendTestPrediction);
    }
    
    fetchUpdates();
});

// ── Fetch données API ──────────────────────────────────────────────────────
async function fetchUpdates() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();
        
        updateServerStatus(true);
        updateLastUpdate(data.last_update);

        if (data.vehicle) {
            updateVehicleDisplay(data.vehicle);
        }

        if (data.dashboard) {
            updateBorneDisplay(data.dashboard);
        }

        if (data.prediction && data.prediction.status === 'success') {
            updateRecommendationDisplay(data.prediction);
            if (data.prediction.recommendation?.timeline) {
                updateTimeline(data.prediction.recommendation.timeline);
            }
        }

    } catch (error) {
        console.error('Erreur fetch:', error);
        updateServerStatus(false);
        addLog(`Erreur connexion : ${error.message}`, 'error');
    }
}

// ── Statut serveur ─────────────────────────────────────────────────────────
function updateServerStatus(online) {
    const dot = document.querySelector('.status-dot');
    const text = document.getElementById('serverStatus');
    if (online) {
        dot.className = 'status-dot online';
        text.textContent = 'Serveur: Connecté';
    } else {
        dot.className = 'status-dot offline';
        text.textContent = 'Serveur: Déconnecté';
    }
}

function updateLastUpdate(timestamp) {
    if (!timestamp) return;
    const time = new Date(timestamp).toLocaleTimeString('fr-FR');
    document.getElementById('lastUpdate').textContent = `Dernière mise à jour: ${time}`;
}

// ── Affichage véhicule ─────────────────────────────────────────────────────
function updateVehicleDisplay(vehicle) {
    state.vehicle = vehicle;
    
    const soc = vehicle.soc || 0;
    document.getElementById('socValue').textContent = `${soc}%`;
    document.getElementById('socProgress').style.width = `${soc}%`;

    const temp = vehicle.temperature ?? '--';
    document.getElementById('tempValue').textContent = temp !== '--' ? `${temp}°C` : '--°C';

    const heure = vehicle.heure ?? vehicle.hour ?? '--';
    document.getElementById('hourValue').textContent = heure !== '--' ? `${heure}h` : '--h';

    const zones = { 0: 'Rural', 1: 'Péri-urbain', 2: 'Urbain' };
    const zone_val = vehicle.zone ?? vehicle.location_zone;
    document.getElementById('zoneValue').textContent = zone_val !== undefined ? zones[zone_val] ?? '--' : '--';

    addLog(`Véhicule: SOC=${soc}% Heure=${heure}h`, 'success');
}

// ── Affichage borne ────────────────────────────────────────────────────────
function updateBorneDisplay(borne) {
    if (borne.temperature !== undefined) {
        const current = document.getElementById('tempValue').textContent;
        if (current === '--°C') {
            document.getElementById('tempValue').textContent = `${borne.temperature}°C`;
        }
    }
    if (borne.gas !== undefined) {
        addLog(`Borne: Temp=${borne.temperature}°C Gaz=${borne.gas}`, 'info');
    }
}

// ── Affichage recommandation IA ────────────────────────────────────────────
function updateRecommendationDisplay(prediction) {
    state.prediction = prediction;
    const rec = prediction.recommendation;
    const input = prediction.input;

    if (!rec) return;

    const display = document.getElementById('recommendationDisplay');
    const icon = display.querySelector('.recommendation-icon');
    const message = document.getElementById('recMessage');
    const subtitle = document.getElementById('recSubtitle');
    const details = document.getElementById('recDetails');

    details.style.display = 'grid';

    const heureActuelle = input?.heure ?? input?.hour ?? new Date().getHours();
    const heureOptStr = rec.best_hour || '--:--';
    const heureOpt = parseInt(heureOptStr.split(':')[0]);
    const isNow = (heureOpt === heureActuelle) || input?.urgent;

    if (isNow) {
        icon.className = 'recommendation-icon ready';
        icon.innerHTML = '<i class="fas fa-bolt"></i>';
        message.textContent = 'Chargez maintenant !';
        display.style.background = 'rgba(46, 204, 113, 0.2)';
        subtitle.textContent = `SOC critique ou heure optimale maintenant`;
    } else {
        icon.className = 'recommendation-icon wait';
        icon.innerHTML = '<i class="fas fa-clock"></i>';
        message.textContent = `Attendez ${heureOptStr}`;
        display.style.background = 'rgba(243, 156, 18, 0.2)';
        subtitle.textContent = `Dans ${rec.delai_heures}h — Économie: ${rec.economie_co2}g CO₂`;
    }

    document.getElementById('bestHour').textContent = heureOptStr;
    document.getElementById('co2Saving').textContent = `${rec.economie_co2 ?? rec.economie_co2_g ?? '--'}g`;
    document.getElementById('optimalScore').textContent = rec.optimal_score ?? '--';
    document.getElementById('energyEstimate').textContent = `${prediction.predictions?.energie_predite_kwh ?? '--'}kWh`;

    addLog(`IA: ${rec.message} (${heureOptStr})`, 'success');
}

// ── Timeline 12h ───────────────────────────────────────────────────────────
function updateTimeline(timeline) {
    if (!timeline || timeline.length === 0) return;
    
    const container = document.getElementById('timeline');
    container.innerHTML = '';

    const heureActuelle = state.vehicle?.heure ?? state.vehicle?.hour ?? new Date().getHours();
    const bestHourStr = state.prediction?.recommendation?.best_hour ?? '';
    const bestHour = parseInt(bestHourStr.split(':')[0]);

    timeline.forEach(item => {
        const el = document.createElement('div');
        el.className = 'timeline-item';

        if (item.hour === bestHour) {
            el.classList.add('optimal');
        }
        if (item.hour === heureActuelle) {
            el.classList.add('current');
        }

        const scoreColor = getScoreColor(item.score);

        el.innerHTML = `
            <span class="timeline-hour">${item.hour}h</span>
            <span class="timeline-score" style="color:${scoreColor}">${item.score}</span>
        `;

        el.title = `Score: ${item.score}\nCO₂: ${item.co2}g\nÉnergie: ${item.energie}kWh`;
        container.appendChild(el);
    });
}

function getScoreColor(score) {
    if (score >= 70) return '#2ecc71';
    if (score >= 40) return '#f39c12';
    return '#e74c3c';
}

// ── Envoi test manuel ──────────────────────────────────────────────────────
async function sendTestPrediction(e) {
    e.preventDefault();
    
    const heure = parseInt(document.getElementById('testHour').value);
    const is_weekend = [5, 6].includes(new Date().getDay()) ? 1 : 0;
    const is_night = (heure >= 21 || heure < 6) ? 1 : 0;

    const data = {
        vehicle_id: 'VEH_001',
        soc: parseInt(document.getElementById('testSoc').value),
        temperature: parseFloat(document.getElementById('testTemp').value),
        energie_kwh: 20,
        puissance_kw: 7.4,
        heure: heure,
        hour: heure,
        is_weekend: is_weekend,
        is_night: is_night,
        lat: 36.8065,
        lon: 10.1815,
        location_zone: parseInt(document.getElementById('testZone').value),
    };

    addLog(`Test: SOC=${data.soc}% Heure=${data.heure}h`, 'info');

    try {
        const response = await fetch(`${API_BASE}/api/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();

        if (result.status === 'success') {
            addLog(`✅ Prédiction: ${result.recommendation?.best_hour} — CO2: ${result.recommendation?.co2}g`, 'success');
            updateRecommendationDisplay(result);
            if (result.recommendation?.timeline) {
                updateTimeline(result.recommendation.timeline);
            }
        } else {
            addLog(`❌ Erreur: ${result.error || result.message}`, 'error');
        }
    } catch (error) {
        addLog(`❌ Erreur envoi: ${error.message}`, 'error');
    }
}

// ── Logs ───────────────────────────────────────────────────────────────────
function addLog(message, type = 'info') {
    const logs = document.getElementById('logs');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString('fr-FR');
    entry.textContent = `[${time}] ${message}`;
    logs.appendChild(entry);
    logs.scrollTop = logs.scrollHeight;
    
    while (logs.children.length > 50) {
        logs.removeChild(logs.firstChild);
    }
}