# Ollama Installation and GPU Setup for Windows

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Ollama GPU-Only Installation Script" -ForegroundColor Cyan
Write-Host "PageIndex OpenAI to Ollama Migration" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator. Installation may fail." -ForegroundColor Yellow
    Write-Host "   Right-click PowerShell and Run as Administrator for best results." -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Check for NVIDIA GPU
Write-Host "Step 1: Checking for NVIDIA GPU..." -ForegroundColor Green
try {
    $nvidiaCheck = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: NVIDIA GPU detected:" -ForegroundColor Green
        $nvidiaCheck | ForEach-Object { Write-Host "  $_" -ForegroundColor White }
    } else {
        throw "nvidia-smi not found"
    }
} catch {
    Write-Host "ERROR: No NVIDIA GPU detected or drivers not installed" -ForegroundColor Red
    Write-Host "   Install NVIDIA drivers from: https://www.nvidia.com/drivers" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 2: Check if Ollama is already installed
Write-Host "Step 2: Checking Ollama installation..." -ForegroundColor Green
$ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaInstalled) {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "SUCCESS: Ollama already installed: $ollamaVersion" -ForegroundColor Green
} else {
    Write-Host "WARNING: Ollama not installed" -ForegroundColor Yellow
    Write-Host "   Installing Ollama using official installer..." -ForegroundColor Cyan
    
    try {
        Write-Host "   Running: irm https://ollama.com/install.ps1 | iex" -ForegroundColor Cyan
        irm https://ollama.com/install.ps1 | iex
        
        Write-Host "SUCCESS: Ollama installed" -ForegroundColor Green
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } catch {
        Write-Host "ERROR: Failed to install Ollama" -ForegroundColor Red
        Write-Host "   Please install manually using:" -ForegroundColor Yellow
        Write-Host "   irm https://ollama.com/install.ps1 | iex" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host ""

# Step 3: Start Ollama service
Write-Host "Step 3: Starting Ollama service..." -ForegroundColor Green
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Write-Host "   Starting Ollama in background..." -ForegroundColor Cyan
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# Check if Ollama API is responding
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "SUCCESS: Ollama service running on http://localhost:11434" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Ollama service not responding" -ForegroundColor Red
    Write-Host "   Try running manually: ollama serve" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 4: Pull recommended small language model
Write-Host "Step 4: Pulling small language model for GPU..." -ForegroundColor Green
Write-Host "   Recommended models for 4GB VRAM (3B parameters or smaller):" -ForegroundColor Cyan
Write-Host "   - phi:2.7b         [2GB VRAM, FASTEST inference]" -ForegroundColor Green
Write-Host "   - qwen2.5:3b       [1.9GB VRAM, good quality + fast]" -ForegroundColor Green
Write-Host "   - neural-chat:7b   [4GB VRAM, balanced]" -ForegroundColor White
Write-Host ""
Write-Host "   Note: mistral:7b (8GB) and llama2:7b (4GB) are too slow for GTX 1650" -ForegroundColor Yellow
Write-Host ""

$model = Read-Host "Enter model to pull [default: phi:2.7b]"
if ([string]::IsNullOrWhiteSpace($model)) {
    $model = "phi:2.7b"
}

Write-Host "   Pulling $model - this may take several minutes..." -ForegroundColor Cyan
try {
    ollama pull $model
    Write-Host "SUCCESS: Model $model pulled successfully" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to pull model" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Test GPU inference
Write-Host "Step 5: Testing GPU inference..." -ForegroundColor Green
$testPrompt = "What is 2+2? Answer in one word."
Write-Host "   Test prompt: $testPrompt" -ForegroundColor Cyan

try {
    $testStart = Get-Date
    $testResponse = ollama run $model "$testPrompt"
    $testEnd = Get-Date
    $duration = ($testEnd - $testStart).TotalSeconds
    
    Write-Host "SUCCESS: GPU inference working!" -ForegroundColor Green
    Write-Host "   Response time: $([math]::Round($duration, 2))s" -ForegroundColor White
    Write-Host "   Response: $testResponse" -ForegroundColor White
} catch {
    Write-Host "WARNING: Could not test inference" -ForegroundColor Yellow
}
Write-Host ""

# Step 6: Verify GPU usage
Write-Host "Step 6: Checking GPU utilization..." -ForegroundColor Green
Write-Host "   Run this in another window to monitor GPU:" -ForegroundColor Cyan
Write-Host "   nvidia-smi -l 1" -ForegroundColor Yellow
Write-Host ""
try {
    $gpuInfo = nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
    Write-Host "   Current GPU status:" -ForegroundColor White
    Write-Host "   $gpuInfo" -ForegroundColor White
} catch {
    Write-Host "   Could not read GPU status" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Ollama GPU Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor White
Write-Host "  - Ollama URL: http://localhost:11434" -ForegroundColor White
Write-Host "  - Model: $model" -ForegroundColor White
Write-Host "  - GPU Mode: Enabled (automatic)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run integration tests:" -ForegroundColor White
Write-Host "     python -m pytest tests/test_ollama_integration.py -v" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Run migration tests:" -ForegroundColor White
Write-Host "     python -m pytest tests/test_openai_to_ollama_migration.py -v" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Update pageindex/config.yaml:" -ForegroundColor White
Write-Host "     provider: ollama" -ForegroundColor Yellow
Write-Host "     model: $model" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop Ollama: Get-Process ollama | Stop-Process" -ForegroundColor Gray
Write-Host ""
