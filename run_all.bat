@echo off
REM Script de lancement rapide pour les deux dashboards intégrés (Windows)
REM Lance:
REM   - Quefaire.be sur le port 5000
REM   - Site de la Ville sur le port 5001

title Scraper Urban - Dashboards Intégrés
cls

echo.
echo ======================================================
echo   ^> LANCEUR INTEGRE - Quefaire.be et Site de la Ville
echo ======================================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou pas dans le PATH
    pause
    exit /b 1
)

echo [INFO] Python détecté: 
python --version
echo.

REM Vérifier les dossiers
if not exist "quefaire.be" (
    echo [ERREUR] Dossier 'quefaire.be' non trouvé
    pause
    exit /b 1
)

if not exist "site de la ville" (
    echo [ERREUR] Dossier 'site de la ville' non trouvé
    pause
    exit /b 1
)

echo [OK] Dossiers trouvés
echo.

REM Établir les ports
set QUEFAIRE_PORT=5000
set SITE_VILLE_PORT=5001

echo [INFO] Vérification des dépendances...
python -m pip show flask >nul 2>&1
if errorlevel 1 (
    echo [ATTENTION] Flask n'est pas installé. Installation...
    python -m pip install flask
)

echo.
echo ======================================================
echo   ^> DEMARRAGE DES SERVEURS
echo ======================================================
echo.
echo [INFO] Démarrage de Quefaire.be sur le port %QUEFAIRE_PORT%...
start "Quefaire.be Server" cmd /k cd /d "%CD%\quefaire.be" && python server.py

timeout /t 2 /nobreak

echo [INFO] Démarrage de Site de la Ville sur le port %SITE_VILLE_PORT%...
start "Site de la Ville Server" cmd /k cd /d "%CD%\site de la ville" && set PORT=%SITE_VILLE_PORT% && python server.py

echo.
echo ======================================================
echo   ^> SERVEURS ACTIFS
echo ======================================================
echo.
echo   ^[ URLs d'Acces ^]
echo   * Quefaire.be      : http://localhost:%QUEFAIRE_PORT%
echo   * Site de la Ville : http://localhost:%SITE_VILLE_PORT%
echo.
echo   ^[ Conseil ^]
echo   Deux nouvelles fenêtres de terminal se sont ouvertes.
echo   Closez-les pour arrêter les serveurs.
echo.
echo ======================================================
echo.

REM Garder cette fenêtre ouverte
pause
