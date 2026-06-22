# =============================================================================
# AUDIO_SYNC.PS1 - backup/sync do audio pesado no Google Drive (via rclone)
# =============================================================================
# O audio (biblioteca/ = mp3 MASTER irreproduzivel ; samples/ = wav derivados)
# NAO vai pro git (pesado demais, ~384MB). Este script guarda esse audio no seu
# Google Drive e traz de volta em outra maquina -- e o "backup que falta".
#
# Usa o rclone (uma ferramenta que conversa com o Google Drive). So precisa
# configurar UMA vez (ver abaixo); depois e so push (manda) e pull (traz).
#
# -------- SETUP (uma vez so) --------
#   1) Instale o rclone:   winget install Rclone.Rclone
#      (reabra o terminal depois de instalar)
#   2) Configure o Google Drive UMA vez:   rclone config
#      - n (new remote)
#      - name> gdrive            <-- use ESTE nome (o script procura por ele)
#      - storage> drive          (Google Drive)
#      - deixe client_id/secret em branco (Enter), scope> 1 (full)
#      - "Use auto config?" > y  -> abre o navegador pra voce logar no Google
#      - "team drive" > n , depois y pra confirmar, q pra sair
#      (Dica no Claude Code: rode o passo 2 digitando  ! rclone config  no prompt.)
#
# -------- USO (sempre) --------
#   .\audio_sync.ps1 push      # manda biblioteca/ e samples/ PRO Google Drive
#   .\audio_sync.ps1 pull      # TRAZ biblioteca/ e samples/ do Google Drive
#   .\audio_sync.ps1 status    # mostra o tamanho do que esta la no Drive
#
# ATENCAO: 'sync' espelha (apaga no destino o que nao existe na origem).
#   push -> a origem e a SUA pasta local (o local manda no Drive).
#   pull -> a origem e o DRIVE (o Drive sobrescreve o seu local).
# Por isso o script PERGUNTA antes de um pull (pra nao apagar local sem querer).
# =============================================================================

param(
    [string]$Action = ""   # push | pull | status
)

$ErrorActionPreference = "Stop"

# --- ajustes (mude aqui se quiser outro nome de remote ou pasta no Drive) ---
$Remote     = "gdrive"             # o nome que voce deu no 'rclone config'
$RemoteBase = "CanastraSuja/audio" # a pasta dentro do Google Drive
$raiz       = $PSScriptRoot
$pastas     = @("biblioteca", "samples")   # o que sincronizar

# --- rclone instalado? ------------------------------------------------------
$rc = Get-Command rclone -ErrorAction SilentlyContinue
if (-not $rc) {
    Write-Host "[ERRO] rclone nao encontrado no PATH." -ForegroundColor Red
    Write-Host "       Instale com:  winget install Rclone.Rclone" -ForegroundColor Yellow
    Write-Host "       e reabra o terminal. Depois rode:  rclone config" -ForegroundColor Yellow
    Write-Host "       (veja o passo a passo no topo deste arquivo.)" -ForegroundColor Yellow
    exit 1
}

# --- o remote 'gdrive' ja foi configurado? ----------------------------------
$remotes = & rclone listremotes
if ($remotes -notcontains "${Remote}:") {
    Write-Host "[ERRO] o remote '${Remote}:' nao existe no rclone." -ForegroundColor Red
    Write-Host "       Configure uma vez com:  rclone config" -ForegroundColor Yellow
    Write-Host "       (use o nome '$Remote' -- veja o setup no topo do arquivo.)" -ForegroundColor Yellow
    exit 1
}

# --- a acao foi informada? --------------------------------------------------
if ($Action -notin @("push", "pull", "status")) {
    Write-Host "Uso:  .\audio_sync.ps1 [push|pull|status]" -ForegroundColor Cyan
    Write-Host "  push   -> manda biblioteca/ e samples/ PRO Google Drive" -ForegroundColor Yellow
    Write-Host "  pull   -> TRAZ biblioteca/ e samples/ do Google Drive" -ForegroundColor Yellow
    Write-Host "  status -> mostra o tamanho do que esta no Drive" -ForegroundColor Yellow
    exit 1
}

# --- STATUS: so mede o que ja esta no Drive ---------------------------------
if ($Action -eq "status") {
    foreach ($p in $pastas) {
        $dest = "${Remote}:$RemoteBase/$p"
        Write-Host "[STATUS] $dest" -ForegroundColor Cyan
        & rclone size $dest
        Write-Host ""
    }
    exit 0
}

# --- PULL: confirma antes (vai sobrescrever o local) ------------------------
if ($Action -eq "pull") {
    Write-Host "[ATENCAO] 'pull' vai SOBRESCREVER as pastas locais com o que esta no Drive:" -ForegroundColor Yellow
    foreach ($p in $pastas) { Write-Host "    $p\  <-  ${Remote}:$RemoteBase/$p" -ForegroundColor DarkGray }
    $ok = Read-Host "Confirma? (s/N)"
    if ($ok -notmatch '^[sS]') { Write-Host "Cancelado."; exit 0 }
}

# --- PUSH/PULL: sincroniza cada pasta ---------------------------------------
$ok = 0
foreach ($p in $pastas) {
    $local = Join-Path $raiz $p
    $dest  = "${Remote}:$RemoteBase/$p"

    if ($Action -eq "push") {
        if (-not (Test-Path $local)) {
            Write-Host "[PULA] pasta local nao existe: $local" -ForegroundColor DarkYellow
            continue
        }
        Write-Host "[PUSH] $p\  ->  $dest" -ForegroundColor Cyan
        & rclone sync $local $dest --progress
    } else {
        # pull: garante a pasta local e traz do Drive
        if (-not (Test-Path $local)) { New-Item -ItemType Directory -Path $local | Out-Null }
        Write-Host "[PULL] $dest  ->  $p\" -ForegroundColor Cyan
        & rclone sync $dest $local --progress
    }

    if ($LASTEXITCODE -eq 0) {
        $ok++
        Write-Host "  [OK] $p sincronizado." -ForegroundColor Green
    } else {
        Write-Host "  [FALHOU] $p (rclone exit $LASTEXITCODE)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[PRONTO] $Action concluido em $ok/$($pastas.Count) pasta(s)." -ForegroundColor Cyan
if ($Action -eq "pull") {
    Write-Host "         Se os mp3 mudaram, rode:  .\regenera_wavs.ps1" -ForegroundColor Yellow
}
