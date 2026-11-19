$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Find-Python {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @($launcher.Source, '-3') }
    }
    $candidates = @()
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { $candidates += $python.Source }
    $candidates += "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @($candidate) }
    }
    return @()
}

function Install-Package($id) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "No se encuentra winget. Instala $id manualmente y vuelve a iniciar."
    }
    Write-Host "Instalando $id con winget. Es posible que Windows solicite confirmacion..."
    & winget.exe install --id $id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar $id con winget (codigo $LASTEXITCODE)." }
}

function Find-Ollama {
    $command = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $path = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path -LiteralPath $path) { return $path }
    return $null
}

function Test-Ollama {
    try {
        $result = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2
        return $null -ne $result.models
    } catch { return $false }
}

function Run-Checked([string]$program, [string[]]$arguments) {
    & $program @arguments
    if ($LASTEXITCODE -ne 0) { throw "Fallo al ejecutar $program (codigo $LASTEXITCODE)." }
}

function Test-Model($models, $name) {
    $fullName = if ($name.Contains(':')) { $name } else { "${name}:latest" }
    return @($models | Where-Object { $_.name -eq $fullName }).Count -gt 0
}

$server = $null
try {
    Write-Host 'Preparando Virtual EmpreCoach. La primera ejecucion descarga varios GB.'
    $python = @(Find-Python)
    if ($python.Count -eq 0) {
        Install-Package 'Python.Python.3.12'
        $python = @(Find-Python)
        if ($python.Count -eq 0) { throw 'Python no se encontro tras instalarlo. Reinicia Windows o instalalo manualmente.' }
    }

    $ollama = Find-Ollama
    if (-not $ollama) {
        Install-Package 'Ollama.Ollama'
        $ollama = Find-Ollama
        if (-not $ollama) { throw 'Ollama no se encontro tras instalarlo. Abre Ollama y vuelve a intentarlo.' }
    }

    # This launcher deliberately uses only the local Ollama instance and its own models.
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    $env:OLLAMA_URL = 'http://127.0.0.1:11434'
    $env:CHAT_MODEL = 'salamandra-emprecoach'
    $env:EMBED_MODEL = 'qwen3-embedding:0.6b'
    if (-not (Test-Ollama)) {
        Write-Host 'Iniciando Ollama...'
        Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden | Out-Null
        $deadline = (Get-Date).AddSeconds(60)
        while (-not (Test-Ollama)) {
            if ((Get-Date) -ge $deadline) { throw 'Ollama no responde en 127.0.0.1:11434. Abre Ollama y vuelve a intentarlo.' }
            Start-Sleep -Seconds 1
        }
    }

    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host 'Creando entorno Python...'
        $pythonArgs = @($python | Select-Object -Skip 1) + @('-m', 'venv', '.venv')
        Run-Checked $python[0] $pythonArgs
    }
    Write-Host 'Comprobando dependencias Python...'
    Run-Checked $venvPython @('-m', 'pip', 'install', '-r', 'requirements.txt')

    $models = (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 10).models
    if (-not (Test-Model $models $env:EMBED_MODEL)) {
        Write-Host 'Descargando el modelo de embeddings...'
        Run-Checked $ollama @('pull', $env:EMBED_MODEL)
    }
    if (-not (Test-Model $models $env:CHAT_MODEL)) {
        $gguf = Join-Path $PSScriptRoot 'salamandra-7b-instruct-Q4_K_M.gguf'
        $expectedHash = 'da90a4badcb493ddf7a213b6775732c775f75347a0560f8e1c586ba6ed07596c'
        if (-not (Test-Path -LiteralPath $gguf)) {
            Write-Host 'Descargando Salamandra desde Hugging Face (aproximadamente 4,85 GB)...'
            $partial = Join-Path $PSScriptRoot ("salamandra-" + [guid]::NewGuid().ToString() + '.partial')
            try {
                $url = 'https://huggingface.co/hdnh2006/BSC-LT-salamandra-7b-instruct-gguf/resolve/main/salamandra-7b-instruct-Q4_K_M.gguf'
                Invoke-WebRequest -Uri $url -OutFile $partial -UseBasicParsing
                if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ne $expectedHash) {
                    throw 'La descarga de Salamandra no supera la comprobacion SHA-256.'
                }
                Move-Item -LiteralPath $partial -Destination $gguf
            } finally {
                if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial }
            }
        } elseif ((Get-FileHash -LiteralPath $gguf -Algorithm SHA256).Hash -ne $expectedHash) {
            throw 'El archivo GGUF existente no coincide con la version esperada; revisalo o retiralo manualmente.'
        }
        Write-Host 'Creando el modelo Salamandra en Ollama...'
        Run-Checked $ollama @('create', $env:CHAT_MODEL, '-f', 'Modelfile')
    }

    $indexPath = Join-Path $PSScriptRoot 'data\index.json'
    if (Test-Path -LiteralPath $indexPath) {
        Write-Host 'Reutilizando el índice existente. Si modificaste el corpus, ejecuta python ingest.py.'
    } else {
        Write-Host 'Indexando los documentos del corpus...'
        Run-Checked $venvPython @('ingest.py')
    }

    $listener = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback), 5000
    try { $listener.Start() } catch { throw 'El puerto 5000 esta ocupado. Cierra la aplicacion que lo usa y vuelve a intentarlo.' } finally { $listener.Stop() }
    Write-Host 'Iniciando la web...'
    $server = Start-Process -FilePath $venvPython -ArgumentList 'app.py' -WorkingDirectory $PSScriptRoot -PassThru -NoNewWindow
    $deadline = (Get-Date).AddSeconds(30)
    do {
        if ($server.HasExited) { throw "La aplicacion termino inesperadamente (codigo $($server.ExitCode))." }
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/' -UseBasicParsing -TimeoutSec 2
            $ready = $response.StatusCode -eq 200
        } catch { $ready = $false }
        if (-not $ready) { Start-Sleep -Milliseconds 500 }
    } while (-not $ready -and (Get-Date) -lt $deadline)
    if (-not $ready) { throw 'La web no responde en el puerto 5000.' }
    Start-Process 'http://127.0.0.1:5000/'
    Write-Host 'Web iniciada. Manten esta ventana abierta; cierrala para terminar.'
    $server.WaitForExit()
    if ($server.ExitCode -ne 0) { throw "La aplicacion termino inesperadamente (codigo $($server.ExitCode))." }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id }
}
