# ============================================================
# MONEYMAKER V1 - Windows Virtual Environment Setup
# ============================================================
# Questo script crea un venv Python, installa tutte le
# dipendenze e configura i pacchetti locali (editable mode).
#
# PREREQUISITI:
#   - Python 3.11+ installato e nel PATH
#   - MetaTrader 5 Terminal installato (per il pacchetto MT5)
#
# UTILIZZO:
#   PowerShell:  .\setup-venv.ps1
#   (Se execution policy blocca: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
# ============================================================

$ErrorActionPreference = "Stop"

# Colori output
function Write-Step { param($msg) Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    [!] $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "    [X] $msg" -ForegroundColor Red }

# --- 0. Verifica Python ---
Write-Step "Verifica Python..."
try {
    $pyVersion = python --version 2>&1
    Write-Ok "Trovato: $pyVersion"
    $versionMatch = [regex]::Match($pyVersion, '(\d+)\.(\d+)')
    $major = [int]$versionMatch.Groups[1].Value
    $minor = [int]$versionMatch.Groups[2].Value
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Warn "Python 3.11+ raccomandato. Trovato $major.$minor - potrebbe funzionare ma non garantito."
    }
} catch {
    Write-Fail "Python non trovato nel PATH. Installalo da https://www.python.org/downloads/"
    exit 1
}

# --- 1. Crea Virtual Environment ---
$venvPath = Join-Path $PSScriptRoot ".venv"
Write-Step "Creazione virtual environment in $venvPath..."

if (Test-Path $venvPath) {
    Write-Warn "Il venv esiste gia'. Vuoi ricrearlo? (S/n)"
    $response = Read-Host
    if ($response -eq "" -or $response -match "^[Ss]") {
        Write-Host "    Rimozione venv esistente..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $venvPath
    } else {
        Write-Ok "Riutilizzo venv esistente."
    }
}

if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Ok "Virtual environment creato."
}

# --- 2. Attiva venv ---
Write-Step "Attivazione virtual environment..."
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Fail "Script di attivazione non trovato: $activateScript"
    exit 1
}
& $activateScript
Write-Ok "Venv attivato."

# --- 3. Aggiorna pip e setuptools ---
Write-Step "Aggiornamento pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel --quiet
Write-Ok "Pip aggiornato."

# --- 4. Installa requirements.txt ---
Write-Step "Installazione dipendenze da requirements.txt..."
$reqFile = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqFile) {
    python -m pip install -r $reqFile
    Write-Ok "Dipendenze installate."
} else {
    Write-Fail "requirements.txt non trovato in $PSScriptRoot"
    exit 1
}

# --- 5. Installa pacchetti locali in editable mode ---
Write-Step "Installazione pacchetti locali (editable mode)..."

$localPackages = @(
    "program\shared\python-common",
    "program\shared\proto",
    "program\services\algo-engine",
    "program\services\mt5-bridge",
    "program\services\console",
    "program\services\dashboard"
)

foreach ($pkg in $localPackages) {
    $pkgPath = Join-Path $PSScriptRoot $pkg
    if (Test-Path (Join-Path $pkgPath "pyproject.toml")) {
        Write-Host "    Installazione: $pkg ..." -ForegroundColor Gray
        python -m pip install -e $pkgPath --quiet 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "$pkg"
        } else {
            Write-Warn "$pkg - installazione con warning (potrebbe essere ok)"
        }
    } else {
        Write-Warn "Saltato $pkg (pyproject.toml non trovato)"
    }
}

# --- 6. Configurazione .env ---
Write-Step "Verifica file .env..."
$envFile = Join-Path $PSScriptRoot "program\.env"
$envExample = Join-Path $PSScriptRoot "program\.env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Warn "File .env creato da .env.example. DEVI configurarlo prima di avviare!"
        Write-Host ""
        Write-Host "    Variabili OBBLIGATORIE da impostare in program\.env:" -ForegroundColor Yellow
        Write-Host "      MONEYMAKER_DB_PASSWORD=<genera con openssl rand -base64 24>" -ForegroundColor White
        Write-Host "      MONEYMAKER_REDIS_PASSWORD=<genera con openssl rand -base64 24>" -ForegroundColor White
        Write-Host "      MT5_ACCOUNT=<numero conto broker>" -ForegroundColor White
        Write-Host "      MT5_PASSWORD=<password conto>" -ForegroundColor White
        Write-Host "      MT5_SERVER=<server broker, es: ICMarkets-Demo>" -ForegroundColor White
        Write-Host "      POLYGON_API_KEY=<chiave API polygon.io>" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Warn ".env.example non trovato. Dovrai creare manualmente program\.env"
    }
} else {
    Write-Ok "File .env gia' presente."
}

# --- 7. Verifica MetaTrader 5 ---
Write-Step "Verifica MetaTrader 5..."
try {
    python -c "import MetaTrader5; print(f'MetaTrader5 v{MetaTrader5.__version__}')" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Pacchetto MetaTrader5 importabile."
    } else {
        Write-Warn "MetaTrader5 installato ma non importabile. Assicurati che il terminale MT5 sia installato."
    }
} catch {
    Write-Warn "Impossibile verificare MetaTrader5. Assicurati che il terminale MT5 sia installato."
}

# --- 8. Riepilogo ---
Write-Step "Setup completato!"
Write-Host ""
Write-Host "  Per attivare il venv in futuro:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  Per avviare i servizi (dopo aver configurato .env e Docker):" -ForegroundColor Cyan
Write-Host "    python -m algo_engine.main        # Algo Engine" -ForegroundColor White
Write-Host "    python -m mt5_bridge.main          # MT5 Bridge" -ForegroundColor White
Write-Host "    python program\services\console\moneymaker_console.py  # Console" -ForegroundColor White
Write-Host ""
Write-Host "  IMPORTANTE: Prima di avviare i servizi Python, assicurati che" -ForegroundColor Yellow
Write-Host "  PostgreSQL e Redis siano in esecuzione (via Docker Compose)." -ForegroundColor Yellow
Write-Host ""
