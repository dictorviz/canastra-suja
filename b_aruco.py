"""
B_ARUCO - CANASTRA SUJA: captacao das cartas por WEBCAM + ArUco

Cada carta FISICA do Buraco ganha um marcador ArUco colado/impresso. Uma
webcam aponta pra mesa; quando um jogador VIRA uma carta, o marcador aparece
no quadro, o sistema reconhece QUAL carta e (valor + naipe) e dispara, via
b_partida, o mesmo efeito do teclado:

    partida.jogar(rank, suit)   # atravessa habitat (b_samples) + degradacao (b_glitch)

A PROJECAO e a propria imagem da WEBCAM com os contornos de tracking do ArUco
desenhados (distopico, fica pro publico) e ela APODRECE conforme a degradacao
sobe -- comeca documental (Ato I) e desmorona ate o fim (Ato IV). O HUD de
operador (vez/ultima/barra) e opcional e fica DESLIGADO por padrao (tecla 'h').

MAPA carta <-> marcador (dicionario DICT_4X4_250, ids 0..107):
    Buraco joga com 2 BARALHOS, entao sao 2 x 54 = 108 marcadores. Cada baralho
    tem 54 ids (52 cartas + 2 coringas); o deck B (ids 54..107) DOBRA sobre o
    deck A: a 2a via de cada carta cai na MESMA (rank, naipe) -- duas damas de
    copas sao a mesma carta pro jogo, so mudam de id (a deteccao exige id unico).
      local = id % 54
      local 0..51 -> carta normal: suit = local // 13 (0=C,1=O,2=E,3=P); rank = local % 13
      local 52,53 -> coringas (curingao / JOKER)

USO:
    python b_aruco.py            # roda a deteccao (pergunta jogadores/seed/camera)
    python b_aruco.py gerar      # gera os 108 PNGs dos marcadores pra imprimir
    python b_aruco.py gerar out  # idem, na pasta 'out/'

TECLAS na janela: q/ESC=sair  f=tela cheia  h=HUD operador  m=espelhar
                  g=liga/desliga o apodrecer da imagem  r=nova mao

Requer: pip install opencv-contrib-python  +  uma webcam.
"""

import os
import random
import sys

try:
    import cv2
    import cv2.aruco as aruco
    import numpy as np
except ImportError:  # OpenCV ausente: o modulo ainda importa (mapa/fallback)
    cv2 = None
    aruco = None
    np = None

from b_samples import RANKS, SUIT_NAMES

# Ordem dos naipes pra convencao de id (id // 13). Bate com SUIT_NAMES.
SUIT_ORDER = ["C", "O", "E", "P"]
N_NORMAL = 52              # por baralho: cartas nos locais 0..51
DECK_SIZE = N_NORMAL + 2   # 54 ids por baralho (52 cartas + 2 coringas)
N_DECKS = 2                # Buraco joga com 2 baralhos
N_MARKERS = DECK_SIZE * N_DECKS  # 108 marcadores ao todo (ids 0..107)
ARUCO_DICT_ID = "DICT_4X4_250"  # >= 108 ids; 4x4 ainda imprime pequeno


# =============================================================================
# MAPA carta <-> marcador (nao depende de OpenCV nem de camera)
# =============================================================================

def id_to_card(marker_id: int):
    """Mapa id -> carta, com os 2 baralhos DOBRADOS na mesma carta.

    id 0..107 (2 baralhos de 54). local = id % 54 ignora QUAL baralho:
    local 0..51 -> (rank, suit); local 52,53 -> ('JOKER', None). Fora -> None.
    """
    if marker_id < 0 or marker_id >= N_MARKERS:
        return None
    local = marker_id % DECK_SIZE  # deck B (54..107) cai sobre o deck A
    if local < N_NORMAL:
        suit = SUIT_ORDER[local // len(RANKS)]
        rank = RANKS[local % len(RANKS)]
        return rank, suit
    return "JOKER", None


def card_to_id(rank: str, suit: str, deck: int = 0):
    """Inverso de id_to_card. Com 2 baralhos o inverso nao e unico: 'deck'
    (0=A, 1=B) escolhe qual das duas vias retornar."""
    if suit not in SUIT_ORDER or rank not in RANKS:
        return None
    return deck * DECK_SIZE + SUIT_ORDER.index(suit) * len(RANKS) + RANKS.index(rank)


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
    """Salva um PNG por marcador (2 baralhos x 54 = 108) com rotulo, pra imprimir.

    O rotulo traz a carta, o id e o baralho (A/B). As duas vias da mesma carta
    tem ids diferentes (a deteccao precisa de id unico) mas o MESMO nome de carta.
    """
    if cv2 is None:
        print("[!] OpenCV ausente. pip install opencv-contrib-python")
        return
    os.makedirs(out_dir, exist_ok=True)
    dic = _aruco_dict()
    for mid in range(N_MARKERS):
        marker = aruco.generateImageMarker(dic, mid, size)
        # margem branca + rotulo legivel embaixo
        canvas = cv2.copyMakeBorder(marker, 50, 110, 50, 50,
                                    cv2.BORDER_CONSTANT, value=255)
        deck = "AB"[mid // DECK_SIZE]
        card = id_to_card(mid)
        if card and card[1] is None:
            label = f"JOKER  (id {mid} - baralho {deck})"
        elif card:
            label = f"{card[0]} {SUIT_NAMES[card[1]]}  (id {mid} - baralho {deck})"
        else:
            label = f"id {mid}"
        h = canvas.shape[0]
        cv2.putText(canvas, label, (50, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
        path = os.path.join(out_dir,
                            f"marker_{mid:03d}_{deck}_{_card_name(mid)}.png")
        cv2.imwrite(path, canvas)
    print(f"[OK] {N_MARKERS} marcadores em '{out_dir}/' "
          f"({N_DECKS} baralhos x {DECK_SIZE}, dicionario {ARUCO_DICT_ID}, "
          f"{size}px). Imprima e cole nas cartas.")


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


def _degradar(frame, level: float, kicks=None):
    """Apodrece a imagem: um PISO global (level 0..1) que sobe DEVAGAR com o
    acumulo + um SOCO por carta na operacao do NAIPE que caiu (kicks), espelhando
    o glitch de audio. As mesmas chaves do b_glitch (detune/freeze/shards/saturate):

        Copas   detune   -> sangria de cor (canais B/R escorregam)
        Paus    saturate -> bitcrush de cor (esmaga bits, queima)
        Espadas shards   -> blocos arrancados (datamosh tosco)
        Ouros   freeze   -> trava de quadro (stutter) -- tratado no LOOP, nao aqui

    level ~0 = limpo/documental (Ato I: o tarot); level alto = a imagem quase
    desmoronando (Ato IV: o buteco em colapso). Cada carta pokeia a imagem do
    JEITO do seu naipe ja cedo; o piso so engrossa o caldo com o tempo. Tudo
    barato (numpy/OpenCV), sem camada visual extra."""
    kicks = kicks or {}
    if np is None or (level <= 0.01 and not kicks):
        return frame
    h, w = frame.shape[:2]
    out = frame

    # forca de cada efeito = piso (level, lento) + soco do naipe (kick), ate 1.0
    chroma = min(1.0, level * 0.5 + kicks.get("detune", 0.0))    # Copas
    crush = min(1.0, level * 0.6 + kicks.get("saturate", 0.0))   # Paus
    shred = min(1.0, level * 0.5 + kicks.get("shards", 0.0))     # Espadas

    # 1. sangria de cor (Copas/detune): canais B e R escorregam em sentidos opostos
    shift = int(chroma * 16)
    if shift > 0:
        b, g, r = cv2.split(out)
        out = cv2.merge([np.roll(b, shift, axis=1), g, np.roll(r, -shift, axis=1)])

    # 2. bitcrush de cor (Paus/saturate): esmaga a profundidade de bits
    bits = int(round(crush * 5))                  # ate 5 bits fora -> 3-bit color
    if bits > 0:
        mask = (0xFF << bits) & 0xFF
        out = (out & np.uint8(mask))

    # 3. scanlines: estrias que escurecem linhas alternadas (puro acumulo)
    if level > 0.2:
        dark = 1.0 - ((level - 0.2) * 0.7)
        out = out.copy()
        out[::2, :] = (out[::2, :] * dark).astype(np.uint8)

    # 4. blocos arrancados (Espadas/shards): datamosh tosco
    nblocks = int(shred * 12)
    if nblocks > 0:
        out = out.copy() if out is frame else out
        amp = int(shred * 44)
        for _ in range(nblocks):
            bw = random.randint(20, max(21, w // 6))
            bh = random.randint(8, max(9, h // 12))
            x = random.randint(0, w - bw); y = random.randint(0, h - bh)
            x2 = min(max(x + random.randint(-amp, amp), 0), w - bw)
            out[y:y + bh, x2:x2 + bw] = out[y:y + bh, x:x + bw]

    # 5. ruido granulado que cresce com o acumulo (um so canal, nos tres)
    if level > 0.3:
        sigma = (level - 0.3) * 60
        noise = np.random.normal(0, sigma, (h, w, 1)).astype(np.int16)
        out = np.clip(out.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return out


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
        fullscreen: bool = False, mirror: bool = False, hud: bool = False,
        degradar: bool = True):
    """Roda a partida com captacao por webcam. A janela e a projecao.

    A projecao mostra o feed cru + os contornos de tracking do ArUco (distopico,
    pro publico) e APODRECE conforme a degradacao sobe (_degradar). O HUD de
    operador (vez, %, barra) fica DESLIGADO por padrao -- e chrome de engenheiro,
    nao cena; ligue com 'h' so pra conferir o estado. 'g' liga/desliga o apodrecer."""
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
    prev_disp = None  # ultimo quadro projetado (pro stutter da degradacao)

    print("\n[OK] webcam no ar. Vire as cartas na frente da camera.")
    print("     teclas na janela: q/ESC=sair  f=tela cheia  h=HUD  m=espelhar  g=degradar  r=nova mao\n")

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

            # marcadores NOVOS e estaveis deste quadro (varios juntos = rajada)
            fired = []
            for mid in present:
                seen[mid] = seen.get(mid, 0) + 1
                if mid in active:
                    active[mid] = 0  # continua na mesa
                elif seen[mid] >= STABLE_FRAMES:
                    card = id_to_card(mid)
                    if card is not None:
                        fired.append(card)
                    active[mid] = 0
            # 1 carta = jogada normal; varias no mesmo quadro = canastra baixada
            # de uma vez -> rajada (cama em cascata, camada B consolidada)
            if len(fired) == 1:
                partida.jogar_carta(fired[0])
            elif len(fired) > 1:
                partida.jogar_rajada(fired)
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

            disp = cv2.flip(frame, 1) if mirror else frame.copy()
            # a projecao apodrece com a degradacao E glitcha PELO NAIPE de cada
            # carta (video_kicks: detune->cor, saturate->bitcrush, shards->blocos,
            # freeze->trava de quadro aqui embaixo). O tracking nao se importa:
            # a deteccao roda no 'frame' cru, nao nesta imagem.
            if degradar:
                lvl = partida.corrupcao
                kicks = partida.glitch.video_kicks()
                # Ouros (freeze) -> trava de quadro: o soco do naipe + o acumulo
                # perto do teto decidem a chance de repetir o quadro anterior.
                stutter = max(0.0, (lvl - 0.5) * 0.6) + kicks.get("freeze", 0.0) * 0.8
                if prev_disp is not None and random.random() < stutter:
                    disp = prev_disp
                else:
                    disp = _degradar(disp, lvl, kicks)
                    prev_disp = disp
            if hud:  # operador: ligar so pra conferir (aparece pro publico tb)
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
            elif key == ord('g'):
                degradar = not degradar
            elif key == ord('r'):
                partida.reset()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        partida.encerrar()
        print("Fim da mao. O baralho se recolhe, sujo.")


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
