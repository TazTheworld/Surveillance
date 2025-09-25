# TeklaStructures Productivity Monitor

Un système de monitoring de productivité pour TeklaStructures.

## Installation

1. Téléchargez `monitor.py`
2. Configurez vos webhooks Discord dans le fichier
3. Installez les dépendances : `pip install -r requirements.txt`
4. Lancez : `python monitor.py --install`

## Configuration requise

Modifiez la section `WEBHOOKS` dans `monitor.py` avec vos URLs Discord.

## Utilisation

- `python monitor.py` - Démarrer le monitoring
- `python monitor.py --install` - Installer au démarrage automatique