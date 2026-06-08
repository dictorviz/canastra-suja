"""
B_ARUCO - CANASTRA SUJA: captacao das cartas por WEBCAM + ArUco

Cada carta FISICA do Buraco ganha um marcador ArUco colado/impresso. Uma
webcam aponta pra mesa; quando um jogador VIRA uma carta, o marcador aparece
no quadro, o sistema reconhece QUAL carta e (valor + naipe) e dispara, via
b_partida, o mesmo efeito do teclado:

    partida.jogar(rank, suit)   # atravessa habitat (b_samples) + degradacao (b_glitch)

A PROJECAO e a propria imagem da WEBCAM (com os marcadores detectados
desenhados + um HUD opcional: de quem e a vez, ultima carta, degradacao).

MAPA carta <-> marcador (dicionario DICT_4X4_100, ids 0..53):
    id 0..51 -> carta normal: suit = id // 13 (0=C,1=O,2=E,3=P); rank = id % 13
    id 52,53 -> coringas (curingao / JOKER)

USO:
    python b_aruco.py            # roda a deteccao (pergunta jogadores/seed/camera)
    python b_aruco.py gerar      # gera os 54 PNGs dos marcadores pra imprimir
    python b_aruco.py gerar out  # idem, na pasta 'out/'

TECLAS na janela: q/ESC=sair  f=tela cheia  h=liga/desliga HUD  m=espelhar

Requer: pip install opencv-contrib-python  +  uma webcam.
"""

import os
import sys

try:
    import cv2
    import cv2.aruco as aruco
except ImportError:  # OpenCV ausente: o modulo ainda importa (mapa/fallback)
    cv2 = None
    aruco = None

from b_samples import RANKS, SUIT_NAMES

# Ordem dos naipes pra convencao de id (id // 13). Bate com SUIT_NAMES.
SUIT_ORDER = ["C", "O", "E", "P"]
N_NORMAL = 52  # ids 0..51; 52 e 53 sao coringas
ARUCO_DICT_ID = "DICT_4X4_100"  # >= 54 ids; 4x4 imprime pequeno


# =============================================================================
# MAPA carta <-> marcador (nao depende de OpenCV nem de camera)
# =============================================================================

def id_to_card(marker_id: int):
    """id 0..51 -> (rank, suit); id 52,53 -> ('JOKER', None); fora -> None."""
    if marker_id < 0:
        return None
    if marker_id < N_NORMAL:
        suit = SUIT_ORDER[marker_id // len(RANKS)]
        rank = RANKS[marker_id % len(RANKS)]
        return rank, suit
    if marker_id < N_NORMAL + 2:
        return "JOKER", None
    return None


def card_to_id(rank: str, suit: str):
    """Inverso de id_to_card -- util pra gerar os marcadores na ordem certa."""
    if suit not in SUIT_ORDER or rank not in RANKS:
        return None
    return SUIT_ORDER.index(suit) * len(RANKS) + RANKS.index(rank)


def _card_name(marker_id: int) -> str:
    card = id_to_card(marker_id)
    if card is None:
        return f"id{marker_id}"
    if card[1] is None:
        return "JOKER"
    return f"{card[0]}{card[1]}"


def _aruco_dict():
    return aruco.getPredefinedDictionary(getattr(aruco, ARUCO_DICT_ID))


# =============================================================================
# GERAR OS MARCADORES PRA IMPRIMIR
# =============================================================================

def gerar_marcadores(out_dir: str = "marcadores", size: int = 600):
    """Salva um PNG por carta (52 + 2 coringas) com rotulo, pra imprimir."""
    if cv2 is None:
        print("[!] OpenCV ausente. pip install opencv-contrib-python")
        return
    os.makedirs(out_dir, exist_ok=True)
    dic = _aruco_dict()
    for mid in range(N_NORMAL + 2):
        marker = aruco.generateImageMarker(dic, mid, size)
        # margem branca + rotulo legivel embaixo
        canvas = cv2.copyMakeBorder(marker, 50, 110, 50, 50,
                                    cv2.BORDER_CONSTANT, value=255)
        card = id_to_card(mid)
        if card and card[1] is None:
            label = f"JOKER  (id {mid})"
        elif card:
            label = f"{card[0]} {SUIT_NAMES[card[1]]}  (id {mid})"
        else:
            label = f"id {mid}"
        h = canvas.shape[0]
        cv2.putText(canvas, label, (50, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
        path = os.path.join(out_dir, f"marker_{mid:02d}_{_card_name(mid)}.png")
        cv2.imwrite(path, canvas)
    print(f"[OK] {N_NORMAL + 2} marcadores em '{out_dir}/' "
          f"(dicionario {ARUCO_DICT_ID}, {size}px). Imprima e cole nas cartas.")


# =============================================================================
# PROJECAO (HUD desenhado sobre a imagem da webcam)
# =============================================================================

def _put(img, text, org, scale=0.8, color=(255, 255, 255), thick=2):
    """Texto com contorno preto, pra ler por cima da imagem da camera."""
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale,
                (0, 0, 0), thick + 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale,
                color, thick, cv2.LINE_AA)


def _draw_hud(frame, partida):
    h, w = frame.shape[:2]
    _put(frame, "CANASTRA SUJA", (20, 40), 1.0, (255, 255, 255), 2)
    _put(frame, f"Vez: {partida.vez_label}", (20, 80), 0.9, (80, 220, 255), 2)
    _put(frame, f"Ultima: {partida.ultima_str()}", (20, 115), 0.7, (200, 200, 200), 2)
    # barra de degradacao
    pct = partida.corrupcao
    bx, by, bw, bh = 20, h - 50, min(360, w - 40), 22
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (60, 60, 60), -1)
    cv2.rectangle(frame, (bx, by), (bx + int(bw * pct), by + bh), (40, 40, 230), -1)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (255, 255, 255), 1)
    _put(frame, f"degradacao {int(pct * 100)}%", (bx, by - 8), 0.6, (255, 255, 255), 1)


def _open_camera(index: int):
    # No Windows, CAP_DSHOW abre mais rapido e evita o backend MSMF travar.
    if sys.platform.startswith("win"):
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)


def _set_fullscreen(win, on):
    cv2.setWindowProperty(
        win, cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN if on else cv2.WINDOW_NORMAL)


# =============================================================================
# O LOOP: webcam -> deteccao -> carta -> som/degradacao + projecao
# =============================================================================

# Debounce: um marcador precisa aparecer ESTAVEL por STABLE_FRAMES quadros pra
# disparar uma vez; so dispara de novo se sumir por GONE_FRAMES (carta tirada
# e mostrada outra vez). Evita re-disparo da carta parada na mesa.
STABLE_FRAMES = 3
GONE_FRAMES = 8


def run(num_jogadores: int, seed=None, camera_index: int = 0,
        fullscreen: bool = False, mirror: bool = False, hud: bool = True):
    """Roda a partida com captacao por webcam. A janela e a projecao."""
    if cv2 is None:
        print("[!] OpenCV ausente. pip install opencv-contrib-python")
        return

    from b_partida import Partida
    partida = Partida(num_jogadores, seed, verbose=True)
    print("  " + partida.mesa.resumo())
    partida.preload()

    dic = _aruco_dict()
    params = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(dic, params)

    cap = _open_camera(camera_index)
    if cap is None or not cap.isOpened():
        print(f"[!] nao consegui abrir a camera {camera_index}. "
              f"Tente outro indice (0,1,2...) ou cheque a webcam.")
        return

    win = "CANASTRA SUJA"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    if fullscreen:
        _set_fullscreen(win, True)

    seen = {}    # id -> quadros consecutivos visto (estabilidade)
    active = {}  # id -> quadros consecutivos sumido (presente=ja disparou)

    print("\n[OK] webcam no ar. Vire as cartas na frente da camera.")
    print("     teclas na janela: q/ESC=sair  f=tela cheia  h=HUD  m=espelhar  r=nova mao\n")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[!] falha lendo a camera. Encerrando.")
                break

            corners, ids, _ = detector.detectMarkers(frame)
            present = set()
            if ids is not None and len(ids) > 0:
                present = {int(x) for x in ids.flatten()}
                aruco.drawDetectedMarkers(frame, corners, ids)

            # dispara cada marcador NOVO e estavel
            for mid in present:
                seen[mid] = seen.get(mid, 0) + 1
                if mid in active:
                    active[mid] = 0  # continua na mesa
                elif seen[mid] >= STABLE_FRAMES:
                    _disparar(partida, mid)
                    active[mid] = 0
            # quem saiu de cena: conta ausencia ate liberar pra disparar de novo
            for mid in list(active.keys()):
                if mid not in present:
                    active[mid] += 1
                    if active[mid] >= GONE_FRAMES:
                        del active[mid]
                        seen.pop(mid, None)
            for mid in list(seen.keys()):
                if mid not in present and mid not in active:
                    seen.pop(mid, None)

            disp = cv2.flip(frame, 1) if mirror else frame
            if hud:
                _draw_hud(disp, partida)
            cv2.imshow(win, disp)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):
                break
            elif key == ord('f'):
                fullscreen = not fullscreen
                _set_fullscreen(win, fullscreen)
            elif key == ord('h'):
                hud = not hud
            elif key == ord('m'):
                mirror = not mirror
            elif key == ord('r'):
                partida.reset()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        partida.encerrar()
        print("Fim da mao. O baralho se recolhe, sujo.")


def _disparar(partida, marker_id: int):
    """Marcador detectado -> joga a carta correspondente."""
    card = id_to_card(marker_id)
    if card is None:
        return
    rank, suit = card
    if suit is None:  # coringa
        partida.jogar_joker()
    else:
        partida.jogar(rank, suit)


# =============================================================================
# MAIN
# =============================================================================

def _ask_camera() -> int:
    try:
        t = input("Indice da camera (0,1,2...) [0]: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)
    try:
        return int(t)
    except ValueError:
        return 0


def main():
    args = sys.argv[1:]

    if args and args[0] in ("gerar", "markers", "marcadores"):
        out = args[1] if len(args) > 1 else "marcadores"
        gerar_marcadores(out)
        return

    print("=" * 64)
    print("CANASTRA SUJA - ArUco (webcam) - a projecao e a imagem da camera")
    print("=" * 64)

    if cv2 is None:
        print("\n[!] OpenCV nao instalado -> deteccao por webcam indisponivel.")
        print("    pip install opencv-contrib-python")
        print("    (e uma webcam). Por ora, caindo no simulador por teclado.\n")
        import b_teclado
        b_teclado.main()
        return

    print("Mostre os marcadores das cartas pra webcam. Pra gerar os marcadores")
    print("pra imprimir:  python b_aruco.py gerar\n")

    import b_teclado
    num = b_teclado.ask_num_jogadores()
    seed = b_teclado.ask_seed()
    cam = _ask_camera()
    run(num, seed, camera_index=cam)


if __name__ == "__main__":
    main()
