from flask import Flask, render_template, jsonify, request
import json
import os
from faction_manager import FactionManager
from threading import Thread
import time

app = Flask(__name__)
faction_manager = FactionManager()

@app.route('/')
def index():
    """Affiche le tableau de bord principal"""
    factions = faction_manager._load_factions()
    return render_template('index.html', factions=factions)

@app.route('/api/factions', methods=['GET'])
def get_factions():
    """Point d'API pour obtenir toutes les factions"""
    factions = faction_manager._load_factions()
    return jsonify(factions)

def run():
    """Démarre le serveur Flask"""
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    """Démarre le serveur dans un thread séparé"""
    t = Thread(target=run)
    t.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
    t.start()
    return t

if __name__ == '__main__':
    server_thread = keep_alive()
    try:
        while True:
            time.sleep(1)  # Maintient le thread principal actif
    except KeyboardInterrupt:
        print("Arrêt du serveur...")
