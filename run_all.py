"""
Lanceur rapide pour les deux dashboards intégrés.
Lance quefaire.be sur le port 5000 et site de la ville sur le port 5001.
"""
import subprocess
import sys
import threading
import time
import os
from pathlib import Path


def run_server(name, port, cwd):
    """Lance un serveur dans un subprocess."""
    print(f"🚀 Démarrage de {name} sur le port {port}...")

    cmd = [sys.executable, "server.py"]
    env = os.environ.copy()
    env["PORT"] = str(port)

    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return process
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de {name}: {e}")
        return None


def stream_output(process, prefix):
    """Lit et affiche la sortie d'un subprocess dans un thread dédié."""
    try:
        for line in process.stdout:
            print(f"[{prefix}] {line.rstrip()}", flush=True)
    except (OSError, ValueError):
        pass


def kill_process_tree(pid):
    """Tue un processus et tous ses enfants (Windows)."""
    try:
        subprocess.call(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def main():
    print("=" * 60)
    print("  🔗 LANCEUR INTÉGRÉ - Quefaire.be & Site de la Ville")
    print("=" * 60)

    script_dir = Path(__file__).parent
    quefaire_dir = script_dir / "quefaire.be"
    site_ville_dir = script_dir / "site de la ville"

    if not quefaire_dir.exists():
        print(f"❌ Dossier quefaire.be introuvable: {quefaire_dir}")
        return

    if not site_ville_dir.exists():
        print(f"❌ Dossier 'site de la ville' introuvable: {site_ville_dir}")
        return

    # Lancer les serveurs
    p1 = run_server("Quefaire.be", 5000, str(quefaire_dir))
    time.sleep(2)

    p2 = run_server("Site de la Ville", 5001, str(site_ville_dir))

    if not p1 or not p2:
        print("\n❌ Erreur lors du démarrage des serveurs")
        return

    print("\n" + "=" * 60)
    print("✅ Serveurs actifs!")
    print("=" * 60)
    print("\n📍 URLs d'accès:")
    print("   • Quefaire.be      : http://localhost:5000")
    print("   • Site de la Ville : http://localhost:5001")
    print("\n💡 Appuyez sur CTRL+C pour arrêter les serveurs\n")

    # Lire la sortie de chaque serveur dans un thread séparé (non-bloquant)
    t1 = threading.Thread(target=stream_output, args=(p1, "Quefaire"), daemon=True)
    t2 = threading.Thread(target=stream_output, args=(p2, "Site"), daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            if p1.poll() is not None:
                print("\n⚠️ Quefaire.be s'est arrêté")
                break
            if p2.poll() is not None:
                print("\n⚠️ Site de la Ville s'est arrêté")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        pass

    print("\n🛑 Arrêt des serveurs...")
    if p1 and p1.poll() is None:
        kill_process_tree(p1.pid)
    if p2 and p2.poll() is None:
        kill_process_tree(p2.pid)

    # Attendre l'arrêt effectif
    for p in (p1, p2):
        if p:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    print("✅ Serveurs arrêtés. Au revoir!")


if __name__ == "__main__":
    main()
