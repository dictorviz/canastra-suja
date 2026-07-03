"""
MAIN - CANASTRA SUJA

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Este e o arquivo que voce RODA PRIMEIRO. Ele e so a "porta de entrada": mostra
um menuzinho e, conforme voce escolhe, chama o teclado ou a webcam. Sozinho ele
nao faz som -- ele apenas abre a peca. Pra rodar, no terminal:

    python main.py

A poetica e o BURACO (2-4 jogadores). NAO ha baralho que toca sozinho: os
JOGADORES tocam a peca. Cada carta da vida real faz o MUNDO (b_synth) reagir:

  - atravessa um habitat gravado (samples mp3/wav) -- crossfade pro proximo;
  - soma ao nivel de degradacao/glitch -- o som vai se sujando carta a carta;
  - (so na webcam) vira THEREMIN: a pose da carta modula uma voz ao vivo que
    pica o habitat e buga/desbuga o som.

A CAMA (a_synth, o vibrafone) ficou DORMENTE: foi tirada da peca ao vivo (a
b_partida nao toca mais a cama). O a_synth.scd ainda precisa rodar -- ele boota
o servidor de audio e o master limiter -- mas a badalada so soa no demo
(python a_cama.py). Ver o README (secao "Camada A -- dormente").

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
    # so imprime um titulo emoldurado por linhas de "=", pra ficar bonito na tela.
    print()
    print("=" * 70)   # "=" * 70 = a letra "=" repetida 70 vezes
    print(title)
    print("=" * 70)


def prompt(text: str, default: str = "") -> str:
    """input() com default visivel."""
    suffix = f" [{default}]" if default else ""  # mostra o valor padrao entre [ ]
    try:
        ans = input(f"{text}{suffix}: ").strip()  # pergunta e le a resposta
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)  # Ctrl+C / Ctrl+D -> sai limpo
    return ans if ans else default  # vazio -> usa o padrao


# =============================================================================
# OPCOES DO MENU (CANASTRA SUJA)
# =============================================================================

def _ask_num_seed():
    """Pergunta jogadores (2-4) + seed (resolve aleatoria pra um int).
    A seed embaralha o baralho do mundo (habitats); a cama responde as cartas."""
    import random
    import b_teclado  # reaproveita as perguntas que ja existem no teclado
    num = b_teclado.ask_num_jogadores()
    seed = b_teclado.ask_seed()
    if seed is None:  # se a pessoa pediu "aleatoria", sorteia um numero de verdade
        seed = random.randint(0, 999999)
        print(f"  -> seed sorteada: {seed}")
    return num, seed


def opt_jogar():
    """A peca por TECLADO: cada carta digitada (b_teclado) atravessa um habitat +
    suja o som (glitch). A vez gira. (Sem theremin -- ele precisa da webcam.)"""
    import b_teclado
    _print_header("CANASTRA SUJA - JOGAR (cartas no teclado)")
    print()
    # daqui pra baixo e so um monte de print() explicando pro operador o que fazer.
    print("Pre-requisito no SuperCollider, NESTA ORDEM:")
    print("  1. a_synth.scd  (boota o servidor de audio + o master limiter)")
    print("  2. b_synth.scd  (MUNDO - habitats + degradacao)")
    print()
    print("  MUNDO (b_synth) - cada carta atravessa um habitat e soma degradacao")
    print("  (a CAMA/vibrafone esta dormente -- nao soa na peca ao vivo)")
    print()
    print("Vai perguntar JOGADORES (2-4) e a seed; durante a peca, mostra de quem")
    print("e a vez (Jogador 1, Jogador 2...) e cada um lanca uma carta:")
    print("  <valor><naipe>: QC 10O AP 7E | JOKER | ENTER=aleatoria | .=silencio | q=sair")
    print("  r=nova mao (zera degradacao e o painel da cama).")
    print()
    print("(Pra captar as cartas pela WEBCAM em vez do teclado, use a opcao [2].)")
    print()
    ans = prompt("Comecar? (s/n)", "s").lower()
    if not ans.startswith('s'):  # se nao comecou com 's' (de "sim"), volta ao menu
        return

    num, seed = _ask_num_seed()
    print()
    b_teclado.run_partida(num, seed)  # entrega o jogo pro laco do teclado


def opt_aruco():
    """A peca por WEBCAM: cada carta captada por ArUco (b_aruco) atravessa um
    habitat + suja + vira theremin (a pose). A janela da webcam e a PROJECAO."""
    import b_aruco
    import b_teclado  # noqa: F401  (usado por _ask_num_seed)
    _print_header("CANASTRA SUJA - ARUCO (webcam) - a projecao e a imagem da camera")
    print()
    if b_aruco.cv2 is None:  # se o OpenCV nao esta instalado, a webcam nao roda
        print("OpenCV nao instalado -> deteccao por webcam indisponivel.")
        print("  pip install opencv-contrib-python   (e uma webcam)")
        print()
        print("Pra gerar os marcadores pra imprimir (depois de instalar):")
        print("  python b_aruco.py gerar")
        return

    print("Pre-requisito no SuperCollider, NESTA ORDEM:")
    print("  1. a_synth.scd  (boota o servidor de audio + o master limiter)")
    print("  2. b_synth.scd  (MUNDO - habitats + degradacao + theremin)")
    print()
    print("  A janela da webcam E A PROJECAO (marcadores detectados + HUD).")
    print("  Vire as cartas com marcador ArUco na frente da camera; cada carta")
    print("  nova atravessa o habitat + degradacao + vira theremin e passa a vez.")
    print("  TAPAR a lente (escuro, sem carta) por ~6s ENCERRA a peca (fade-out de tudo).")
    print("  Marcadores pra imprimir:  python b_aruco.py gerar")
    print("  Teclas na janela: q=sair  f=tela cheia  h=HUD  m=espelhar  g=degradar  r=nova mao")
    print()
    ans = prompt("Comecar? (s/n)", "s").lower()
    if not ans.startswith('s'):
        return

    num, seed = _ask_num_seed()
    cam = b_aruco._ask_camera()  # pergunta qual webcam usar
    print()
    b_aruco.run(num, seed, camera_index=cam)  # entrega o jogo pro laco da webcam


# =============================================================================
# MENU PRINCIPAL
# =============================================================================

# texto fixo do menu (uma string de varias linhas, entre tres aspas).
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

    # laco do menu: mostra as opcoes, le a escolha e age. Repete ate escolher sair.
    while True:
        print()
        print("-" * 70)
        print(MENU)
        choice = prompt("Escolha", "1")
        if choice in ('0', 'q', 'sair', 'exit'):
            print("Tchau!")
            return  # sai da funcao main -> encerra o programa
        elif choice == '1':
            # try/except: tenta rodar a opcao; se der ALGUM erro, mostra a mensagem
            # e volta pro menu, em vez de o programa inteiro quebrar.
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
