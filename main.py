"""
MAIN - CANASTRA SUJA

Ponto de entrada unico da peca. Roda com:

    python main.py

A poetica e o BURACO (2-4 jogadores). NAO ha baralho que toca sozinho: os
JOGADORES tocam a peca. Cada carta da vida real faz DUAS coisas ao mesmo tempo:

  - CAMA (a_synth) - TOCA o vibrafone ao vivo: cada carta gira um parametro do
    painel e dispara uma badalada na hora (estado rolante; ver a_cama.py). Sem
    carta, sem som -- a cama nao anda sozinha.
  - MUNDO (b_synth) - atravessa um habitat gravado (samples mp3/wav) e soma ao
    nivel de degradacao/glitch. O som vai se sujando carta a carta.

Menu:

    [1] Jogar no teclado (cartas simuladas)  - sem webcam
    [2] Jogar na webcam (cartas reais/ArUco) - a PROJECAO e a camera
    [0] Sair

A captacao das cartas e por WEBCAM + ArUco (b_aruco.py) -- e a imagem da webcam
vira a PROJECAO. O teclado (b_teclado.py) simula a virada quando nao ha camera.
Marcadores pra imprimir: python b_aruco.py gerar.

--- O QUE FICOU EM arquivo/ ---
A VOZ/TEXTO do Perec saiu (sem voz, sem palavras). Ficaram arquivados em
arquivo/: a_voz.py, a_visual_*, nucleo_perec.py, legado_*, visualizer/,
tts_cache/, sessoes/. O \\baralhoVox do a_synth.scd fica dormente.

OUTRAS PORTAS DE ENTRADA:
    python b_teclado.py       # so as cartas (cama + mundo, sem menu)
    python a_cama.py          # demo: simula cartas tocando o vibrafone ao vivo
    python a_osc.py 60        # a cama AUTONOMA (generativa), 60s -- so pra testar o synth
    python b_samples.py       # demo: atravessa alguns habitats sozinho
    python b_buraco.py        # demo das regras (turnos/duplas)
"""


def _print_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def prompt(text: str, default: str = "") -> str:
    """input() com default visivel."""
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)
    return ans if ans else default


# =============================================================================
# OPCOES DO MENU (CANASTRA SUJA)
# =============================================================================

def _ask_num_seed():
    """Pergunta jogadores (2-4) + seed (resolve aleatoria pra um int).
    A seed embaralha o baralho do mundo (habitats); a cama responde as cartas."""
    import random
    import b_teclado
    num = b_teclado.ask_num_jogadores()
    seed = b_teclado.ask_seed()
    if seed is None:
        seed = random.randint(0, 999999)
        print(f"  -> seed sorteada: {seed}")
    return num, seed


def opt_jogar():
    """A peca por TECLADO: cada carta digitada (b_teclado) toca a cama (vibrafone
    ao vivo) + atravessa um habitat + suja. A vez gira. A cama nao toca sozinha."""
    import b_teclado
    _print_header("CANASTRA SUJA - JOGAR (cartas no teclado)")
    print()
    print("Pre-requisito no SuperCollider, NESTA ORDEM:")
    print("  1. a_synth.scd  (CAMA - o vibrafone, agora TOCADO pelas cartas)")
    print("  2. b_synth.scd  (MUNDO - habitats + degradacao)")
    print()
    print("  CAMA  (a_synth) - cada carta gira um parametro e dispara uma badalada")
    print("  MUNDO (b_synth) - cada carta atravessa um habitat e soma degradacao")
    print()
    print("Vai perguntar JOGADORES (2-4) e a seed; durante a peca, mostra de quem")
    print("e a vez (Jogador 1, Jogador 2...) e cada um lanca uma carta:")
    print("  <valor><naipe>: QC 10O AP 7E | JOKER | ENTER=aleatoria | .=silencio | q=sair")
    print("  r=nova mao (zera degradacao e o painel da cama).")
    print()
    print("(Pra captar as cartas pela WEBCAM em vez do teclado, use a opcao [2].)")
    print()
    ans = prompt("Comecar? (s/n)", "s").lower()
    if not ans.startswith('s'):
        return

    num, seed = _ask_num_seed()
    print()
    b_teclado.run_partida(num, seed)


def opt_aruco():
    """A peca por WEBCAM: cada carta captada por ArUco (b_aruco) toca a cama +
    atravessa um habitat + suja. A janela da webcam e a PROJECAO."""
    import b_aruco
    import b_teclado  # noqa: F401  (usado por _ask_num_seed)
    _print_header("CANASTRA SUJA - ARUCO (webcam) - a projecao e a imagem da camera")
    print()
    if b_aruco.cv2 is None:
        print("OpenCV nao instalado -> deteccao por webcam indisponivel.")
        print("  pip install opencv-contrib-python   (e uma webcam)")
        print()
        print("Pra gerar os marcadores pra imprimir (depois de instalar):")
        print("  python b_aruco.py gerar")
        return

    print("Pre-requisito no SuperCollider, NESTA ORDEM:")
    print("  1. a_synth.scd  (CAMA - o vibrafone, agora TOCADO pelas cartas)")
    print("  2. b_synth.scd  (MUNDO - habitats + degradacao)")
    print()
    print("  A janela da webcam E A PROJECAO (marcadores detectados + HUD).")
    print("  Vire as cartas com marcador ArUco na frente da camera; cada carta")
    print("  nova toca a cama + dispara o habitat + degradacao e passa a vez.")
    print("  Marcadores pra imprimir:  python b_aruco.py gerar")
    print("  Teclas na janela: q=sair  f=tela cheia  h=HUD  m=espelhar  r=nova mao")
    print()
    ans = prompt("Comecar? (s/n)", "s").lower()
    if not ans.startswith('s'):
        return

    num, seed = _ask_num_seed()
    cam = b_aruco._ask_camera()
    print()
    b_aruco.run(num, seed, camera_index=cam)


# =============================================================================
# MENU PRINCIPAL
# =============================================================================

MENU = """
[1] Jogar no teclado   - baralho virtual + cartas simuladas (sem webcam)
[2] Jogar na webcam    - baralho virtual + cartas reais (ArUco); projecao = camera
[0] Sair
"""


def main():
    print()
    print("=" * 70)
    print("CANASTRA SUJA")
    print("=" * 70)
    print("BURACO (2-4 jogadores) -> cada carta suja o som do mundo.")
    print("Cartas viram samples + degradacao. Sem voz, sem palavras.")

    while True:
        print()
        print("-" * 70)
        print(MENU)
        choice = prompt("Escolha", "1")
        if choice in ('0', 'q', 'sair', 'exit'):
            print("Tchau!")
            return
        elif choice == '1':
            try:
                opt_jogar()
            except Exception as e:
                print(f"[!] Erro: {e}")
        elif choice == '2':
            try:
                opt_aruco()
            except Exception as e:
                print(f"[!] Erro: {e}")
        else:
            print(f"  [!] opcao '{choice}' nao reconhecida.")


if __name__ == "__main__":
    main()
