from flask import Flask, render_template, jsonify, request
import json
import os
from faction_manager import FactionManager

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
