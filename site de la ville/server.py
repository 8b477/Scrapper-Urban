"""
server.py: Serveur Flask pour le centre de contrôle du scraper "site de la ville"
Miroir de l'architecture quefaire.be — mêmes endpoints, même logique.
"""
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

# ── Configuration ────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent

# Noms affichés → identifiant interne (slug)
CITIES_DISPLAY = {
    "charleroi": "Charleroi",
    "lalouviere": "La Louvière",
    "liege": "Liège",
    "mons": "Mons",
    "namur": "Namur",
}
CITIES = list(CITIES_DISPLAY.keys())

# Slug → dossier réel sur disque
CITY_DIRS = {
    "charleroi": PROJECT_ROOT / "Charleroi",
    "lalouviere": PROJECT_ROOT / "La Louvière",
    "liege": PROJECT_ROOT / "Liège",
    "mons": PROJECT_ROOT / "Mons",
    "namur": PROJECT_ROOT / "Namur",
}

# Slug → préfixe des fichiers JSON (tel que généré par les scrapers)
CITY_JSON_PREFIX = {
    "charleroi": "charleroi",
    "lalouviere": "lalouviere",
    "liege": "liege",
    "mons": "mons",
    "namur": "namur",
}

# Slug → chemin du script agenda
CITY_AGENDA_SCRIPT = {slug: f"{CITY_DIRS[slug].name}/scraper_agenda.py" for slug in CITIES}
CITY_DETAILS_SCRIPT = {slug: f"{CITY_DIRS[slug].name}/scraper_event_details.py" for slug in CITIES}

app = Flask(__name__, template_folder="templates", static_folder="static")

# Stockage des tâches en cours
tasks = {}
tasks_lock = threading.Lock()

# File d'attente : 1 seule tâche à la fois, les autres attendent
task_queue_lock = threading.Semaphore(1)
task_durations = []            # historique des durées pour estimation

CACHE_DURATION_HOURS = 12


# ── Helpers ──────────────────────────────────────────────────

def _find_json(city: str):
    """Retourne la liste des JSON triés (plus récent d'abord) pour une ville."""
    city_dir = CITY_DIRS.get(city)
    if not city_dir or not city_dir.exists():
        return []
    prefix = CITY_JSON_PREFIX.get(city, city)
    return sorted(city_dir.glob(f"{prefix}_*.json"), reverse=True)


def get_city_data(city: str) -> dict:
    """Récupère les données existantes pour une ville (format identique à quefaire.be)."""
    json_files = _find_json(city)

    result = {
        "city": city,
        "has_data": bool(json_files),
        "json_files": [f.name for f in json_files],
        "metadata": None,
        "events_count": 0,
        "urls_count": 0,
    }

    if json_files:
        try:
            with open(json_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            result["metadata"] = data.get("metadata", {})
            result["events_count"] = len(data.get("events", []))
            result["urls_count"] = len(data.get("event_urls", []))
        except (json.JSONDecodeError, OSError):
            pass

    return result


def check_cache(city: str, action: str = "urls") -> dict:
    """Vérifie le cache (< CACHE_DURATION_HOURS). Compatible quefaire.be."""
    json_files = _find_json(city)
    if not json_files:
        return {"cached": False}

    try:
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        metadata = data.get("metadata", {})

        if action == "urls":
            ts_str = metadata.get("last_execution", {}).get("timestamp")
        else:
            ts_str = metadata.get("extraction_date")

        if not ts_str:
            return {"cached": False}

        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = now - ts
        age_minutes = int(age.total_seconds() / 60)
        age_hours = age_minutes / 60

        return {
            "cached": age_hours < CACHE_DURATION_HOURS,
            "age_minutes": age_minutes,
            "age_hours": round(age_hours, 1),
            "timestamp": ts_str,
            "max_hours": CACHE_DURATION_HOURS,
        }
    except (json.JSONDecodeError, OSError, ValueError):
        return {"cached": False}


def _get_queue_position():
    """Retourne le nombre de tâches en attente ou en cours."""
    with tasks_lock:
        return sum(1 for t in tasks.values() if t["status"] in ("waiting", "running"))


def _format_eta(seconds):
    """Formate une durée en min:sec lisible."""
    if seconds < 60:
        return f"{int(seconds)}s"
    return f"{int(seconds // 60)}min {int(seconds % 60)}s"


def _avg_duration():
    """Retourne la durée moyenne des tâches terminées (ou 30s par défaut)."""
    if not task_durations:
        return 30
    return sum(task_durations) / len(task_durations)


def run_script_task(task_id: str, script: str, args: list):
    """Exécute un script Python dans un thread séparé (1 à la fois)."""
    queue_pos = _get_queue_position()
    eta = _avg_duration() * max(queue_pos, 1)

    with tasks_lock:
        tasks[task_id]["status"] = "waiting"
        tasks[task_id]["output"] = [
            f"⏳ En file d'attente — position {queue_pos} "
            f"(estimé dans ~{_format_eta(eta)})"
        ]

    task_queue_lock.acquire()

    cmd = [sys.executable, str(PROJECT_ROOT / script)] + args
    start_time = time.time()

    with tasks_lock:
        tasks[task_id]["status"] = "running"
        tasks[task_id]["started_at"] = datetime.now().isoformat()
        tasks[task_id]["output"] = [f"▶ Démarrage de {script}..."]

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
            env=env,
            close_fds=True,
        )

        output_lines = []
        for line in process.stdout:
            output_lines.append(line.rstrip())
            with tasks_lock:
                tasks[task_id]["output"] = output_lines.copy()

        process.wait()
        duration = round(time.time() - start_time, 1)

        task_durations.append(duration)
        if len(task_durations) > 20:
            task_durations.pop(0)

        with tasks_lock:
            tasks[task_id]["status"] = "success" if process.returncode == 0 else "error"
            tasks[task_id]["return_code"] = process.returncode
            tasks[task_id]["finished_at"] = datetime.now().isoformat()
            tasks[task_id]["duration"] = duration
            tasks[task_id]["output"] = output_lines
            tasks[task_id]["output"].append(f"⏱ Durée réelle : {_format_eta(duration)}")

    except Exception as e:
        duration = round(time.time() - start_time, 1)
        with tasks_lock:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)
            tasks[task_id]["finished_at"] = datetime.now().isoformat()
            tasks[task_id]["duration"] = duration
    finally:
        task_queue_lock.release()


# ── Routes HTML ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


# ── API : Villes ─────────────────────────────────────────────

@app.route("/api/cities")
def api_cities():
    """Liste toutes les villes avec leurs données (même format que quefaire.be)."""
    return jsonify([get_city_data(city) for city in CITIES])


@app.route("/api/city/<city>/events")
def api_city_events(city: str):
    """Retourne les événements d'une ville."""
    city = city.lower().strip()
    if city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 404

    json_files = _find_json(city)
    if not json_files:
        return jsonify({"events": [], "total": 0})

    try:
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        events = data.get("events", [])
        return jsonify({"events": events, "total": len(events), "file": json_files[0].name})
    except (json.JSONDecodeError, OSError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/city/<city>/json")
def api_city_json_download(city: str):
    """Télécharge/affiche le JSON brut d'une ville."""
    city = city.lower().strip()
    if city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 404

    json_files = _find_json(city)
    if not json_files:
        return jsonify({"error": "Aucun fichier JSON disponible"}), 404

    return send_file(
        json_files[0],
        mimetype="application/json",
        as_attachment=False,
        download_name=json_files[0].name,
    )


@app.route("/api/city/<city>/urls")
def api_city_urls(city: str):
    """Retourne les URLs extraites pour une ville."""
    city = city.lower().strip()
    if city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 404

    json_files = _find_json(city)
    if not json_files:
        return jsonify({"urls": [], "total": 0})

    try:
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        urls = data.get("event_urls", [])
        return jsonify({"urls": urls, "total": len(urls), "file": json_files[0].name})
    except (json.JSONDecodeError, OSError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/city/<city>/metadata")
def api_city_metadata(city: str):
    """Retourne les métadonnées et le résumé d'extraction pour une ville."""
    city = city.lower().strip()
    if city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 404

    json_files = _find_json(city)
    if not json_files:
        return jsonify({"metadata": None, "extraction_summary": None})

    try:
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({
            "metadata": data.get("metadata"),
            "extraction_summary": data.get("extraction_summary"),
            "file": json_files[0].name,
        })
    except (json.JSONDecodeError, OSError) as e:
        return jsonify({"error": str(e)}), 500


# ── API : Cache ──────────────────────────────────────────────

@app.route("/api/cache/check", methods=["POST"])
def api_cache_check():
    """Vérifie le cache pour une action donnée (même contrat que quefaire.be)."""
    body = request.get_json(silent=True) or {}
    city = body.get("city", "").lower().strip()
    action = body.get("action", "urls")

    if not city:
        results = {}
        all_cached = True
        for c in CITIES:
            cache = check_cache(c, action)
            results[c] = cache
            if not cache.get("cached"):
                all_cached = False
        return jsonify({"all_cached": all_cached, "cities": results})

    if city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 400

    return jsonify(check_cache(city, action))


# ── API : Lancement scraping ─────────────────────────────────

@app.route("/api/run/extract-urls", methods=["POST"])
def api_run_extract_urls():
    """Lance l'extraction de l'agenda (URLs) pour une ou plusieurs villes."""
    body = request.get_json(silent=True) or {}
    city = body.get("city", "").lower().strip()
    cities_list = body.get("cities", [])

    # Plusieurs villes
    if cities_list:
        normalized = [c.lower().strip() for c in cities_list]
        invalid = [c for c in normalized if c not in CITIES]
        if invalid:
            return jsonify({"error": f"Villes inconnues: {', '.join(invalid)}"}), 400

        task_ids = []
        for c in normalized:
            task_id = str(uuid.uuid4())[:8]
            label = f"scraper_agenda - {CITIES_DISPLAY[c]}"

            with tasks_lock:
                tasks[task_id] = {
                    "id": task_id, "script": CITY_AGENDA_SCRIPT[c],
                    "label": label, "city": c, "status": "pending",
                    "output": [], "created_at": datetime.now().isoformat(),
                }

            thread = threading.Thread(
                target=run_script_task,
                args=(task_id, CITY_AGENDA_SCRIPT[c], []),
                daemon=True,
            )
            thread.start()
            task_ids.append(task_id)

        return jsonify({"task_ids": task_ids, "status": "started", "count": len(task_ids)})

    # Ville unique ou toutes
    if city and city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 400

    targets = [city] if city else CITIES
    task_ids = []
    for c in targets:
        task_id = str(uuid.uuid4())[:8]
        label = f"scraper_agenda - {CITIES_DISPLAY[c]}"

        with tasks_lock:
            tasks[task_id] = {
                "id": task_id, "script": CITY_AGENDA_SCRIPT[c],
                "label": label, "city": c, "status": "pending",
                "output": [], "created_at": datetime.now().isoformat(),
            }

        thread = threading.Thread(
            target=run_script_task,
            args=(task_id, CITY_AGENDA_SCRIPT[c], []),
            daemon=True,
        )
        thread.start()
        task_ids.append(task_id)

    if len(task_ids) == 1:
        return jsonify({"task_id": task_ids[0], "status": "started"})
    return jsonify({"task_ids": task_ids, "status": "started", "count": len(task_ids)})


@app.route("/api/run/extract-details", methods=["POST"])
def api_run_extract_details():
    """Lance l'extraction des détails pour une ou plusieurs villes."""
    body = request.get_json(silent=True) or {}
    city = body.get("city", "").lower().strip()
    cities_list = body.get("cities", [])

    # Plusieurs villes
    if cities_list:
        normalized = [c.lower().strip() for c in cities_list]
        invalid = [c for c in normalized if c not in CITIES]
        if invalid:
            return jsonify({"error": f"Villes inconnues: {', '.join(invalid)}"}), 400

        task_ids = []
        for c in normalized:
            task_id = str(uuid.uuid4())[:8]
            label = f"scraper_event_details - {CITIES_DISPLAY[c]}"

            with tasks_lock:
                tasks[task_id] = {
                    "id": task_id, "script": CITY_DETAILS_SCRIPT[c],
                    "label": label, "city": c, "status": "pending",
                    "output": [], "created_at": datetime.now().isoformat(),
                }

            thread = threading.Thread(
                target=run_script_task,
                args=(task_id, CITY_DETAILS_SCRIPT[c], []),
                daemon=True,
            )
            thread.start()
            task_ids.append(task_id)

        return jsonify({"task_ids": task_ids, "status": "started", "count": len(task_ids)})

    # Ville unique ou toutes
    if city and city not in CITIES:
        return jsonify({"error": "Ville inconnue"}), 400

    targets = [city] if city else CITIES
    task_ids = []
    for c in targets:
        task_id = str(uuid.uuid4())[:8]
        label = f"scraper_event_details - {CITIES_DISPLAY[c]}"

        with tasks_lock:
            tasks[task_id] = {
                "id": task_id, "script": CITY_DETAILS_SCRIPT[c],
                "label": label, "city": c, "status": "pending",
                "output": [], "created_at": datetime.now().isoformat(),
            }

        thread = threading.Thread(
            target=run_script_task,
            args=(task_id, CITY_DETAILS_SCRIPT[c], []),
            daemon=True,
        )
        thread.start()
        task_ids.append(task_id)

    if len(task_ids) == 1:
        return jsonify({"task_id": task_ids[0], "status": "started"})
    return jsonify({"task_ids": task_ids, "status": "started", "count": len(task_ids)})


# ── API : Tâches ─────────────────────────────────────────────

@app.route("/api/tasks")
def api_tasks():
    """Liste toutes les tâches (même format que quefaire.be)."""
    with tasks_lock:
        return jsonify(list(tasks.values()))


@app.route("/api/tasks/<task_id>")
def api_task_status(task_id: str):
    """Statut d'une tâche spécifique."""
    with tasks_lock:
        task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Tâche introuvable"}), 404
    return jsonify(task)


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    print("=" * 50)
    print("  Centre de contrôle - site de la ville scraper")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    app.run(debug=debug, host="0.0.0.0", port=port)
