# =============================================================================
# REGENERA_WAVS.PS1 - reconstroi samples/*.wav a partir de biblioteca/*.mp3
# =============================================================================
# O SuperCollider so toca os WAV de samples/ (o b_samples.py le essa pasta).
# A biblioteca/*.mp3 e so o master de origem. Sempre que voce mexer nos mp3,
# rode este script pra deixar os wav em dia.
#
# O que ele faz:
#   1) confere se o ffmpeg esta instalado
#   2) apaga os WAV antigos de samples/ (evita orfaos que nao tem mais mp3)
#   3) pra cada biblioteca/NNN.mp3 gera samples/NNN.wav (mono, 44.1 kHz)
#
# Uso:   .\regenera_wavs.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# pasta onde este script esta (assim funciona de qualquer lugar)
$raiz       = $PSScriptRoot
$biblioteca = Join-Path $raiz "biblioteca"
$samples    = Join-Path $raiz "samples"

# --- 1) ffmpeg instalado? ---------------------------------------------------
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ff) {
    Write-Host "[ERRO] ffmpeg nao encontrado no PATH." -ForegroundColor Red
    Write-Host "       Instale com:  winget install Gyan.FFmpeg" -ForegroundColor Yellow
    Write-Host "       e reabra o terminal antes de rodar de novo." -ForegroundColor Yellow
    exit 1
}

# --- pasta biblioteca existe e tem mp3? -------------------------------------
if (-not (Test-Path $biblioteca)) {
    Write-Host "[ERRO] pasta nao encontrada: $biblioteca" -ForegroundColor Red
    exit 1
}
$mp3s = Get-ChildItem (Join-Path $biblioteca "*.mp3") | Sort-Object Name
if ($mp3s.Count -eq 0) {
    Write-Host "[ERRO] nenhum .mp3 em $biblioteca" -ForegroundColor Red
    exit 1
}

# --- 2) limpa os WAV antigos ------------------------------------------------
if (-not (Test-Path $samples)) {
    New-Item -ItemType Directory -Path $samples | Out-Null
}
$velhos = Get-ChildItem (Join-Path $samples "*.wav") -ErrorAction SilentlyContinue
if ($velhos) {
    Write-Host "[LIMPA] removendo $($velhos.Count) WAV antigo(s) de samples/..." -ForegroundColor DarkGray
    Remove-Item (Join-Path $samples "*.wav") -Force
}

# --- 3) converte cada mp3 -> wav (mono, 44.1 kHz) ---------------------------
Write-Host "[CONVERTE] $($mp3s.Count) arquivo(s) -> mono 44.1k ..." -ForegroundColor Cyan
$ok = 0
foreach ($mp3 in $mp3s) {
    $nome   = [System.IO.Path]::GetFileNameWithoutExtension($mp3.Name)  # "001"
    $saida  = Join-Path $samples "$nome.wav"
    # -ac 1   = mono | -ar 44100 = 44.1 kHz | -y = sobrescreve sem perguntar
    # -loglevel error so mostra erro de verdade (sem o despejo todo do ffmpeg)
    & ffmpeg -hide_banner -loglevel error -y -i $mp3.FullName -ac 1 -ar 44100 $saida
    if ($LASTEXITCODE -eq 0) {
        $ok++
        Write-Host ("  [OK] {0}.mp3 -> {0}.wav" -f $nome) -ForegroundColor Green
    } else {
        Write-Host ("  [FALHOU] {0}.mp3 (ffmpeg exit {1})" -f $nome, $LASTEXITCODE) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[PRONTO] $ok/$($mp3s.Count) habitats regenerados em samples/." -ForegroundColor Cyan
Write-Host "         Teste com:  python b_samples.py" -ForegroundColor Yellow
