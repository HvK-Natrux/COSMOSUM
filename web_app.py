from flask import Flask, render_template
import json
from faction_manager import FactionManager

app = Flask(__name__)
faction_manager = FactionManager()

@app.route('/')
def home():
    """Page d'accueil"""
    factions = faction_manager._load_factions()
    return render_template('index.html', faction_count=len(factions))

@app.route('/factions')
def factions():
    """Liste des factions"""
    factions = faction_manager._load_factions()
    return render_template('factions.html', factions=factions)

def run():
    """Démarre le serveur Flask"""
    app.run(host='0.0.0.0', port=5000)

def start_server():
    """Démarre le serveur dans un thread séparé"""
    from threading import Thread
    t = Thread(target=run)
    t.daemon = True
    t.start()
    return t
