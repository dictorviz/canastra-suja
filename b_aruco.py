"""
B_ARUCO - CANASTRA SUJA: captacao das cartas por WEBCAM + ArUco

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: este arquivo usa a WEBCAM pra "ler" as cartas. Cada carta de
verdade ganha colado um quadradinho preto-e-branco (um marcador "ArUco" -- e
tipo um QR code bem simples). A camera ve esse quadradinho, descobre QUAL carta
e, e dispara o mesmo efeito do teclado: toca a cama, atravessa um habitat e
suja o som. De brinde, a propria imagem da camera VIRA a projecao pro publico,
e ela vai apodrecendo conforme o jogo suja.

Duas ferramentas de fora fazem o trabalho pesado da imagem:
  - OpenCV ("cv2"): abre a camera, acha os marcadores, desenha na tela.
  - NumPy ("np"): mexe rapido nos PIXELS da imagem (a imagem, pro computador, e
    so uma GRADE gigante de numeros: altura x largura x 3 cores R, G, B).

Se o OpenCV nao estiver instalado, o arquivo ainda CARREGA (o mapa carta<->id
nao precisa de camera), e o programa cai no modo teclado. Por isso o "try" la
embaixo no import: "tente importar; se nao der, siga sem".

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
import sys  # acessa argumentos da linha de comando e o nome do sistema (Windows/Linux)

# Tenta importar as ferramentas de imagem. Se nao estiverem instaladas, em vez
# de quebrar, a gente "captura" o erro (except ImportError) e segue com elas
# valendo None (nada). Assim o mapa carta<->id ainda funciona sem camera.
try:
    import cv2                 # OpenCV: a "visao computacional"
    import cv2.aruco as aruco  # a parte do OpenCV que lida com os marcadores ArUco
    import numpy as np         # NumPy: contas rapidas em grades de numeros (pixels)
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
    if marker_id < 0 or marker_id >= N_MARKERS:  # id fora da faixa valida -> nada
        return None
    # "% DECK_SIZE" (resto da divisao por 54) faz o baralho B cair sobre o A:
    # id 5 e id 59 dao o mesmo local 5 -> a mesma carta. So o id muda.
    local = marker_id % DECK_SIZE  # deck B (54..107) cai sobre o deck A
    if local < N_NORMAL:  # se for uma carta normal (nao coringa)...
        # "//" (divisao inteira) agrupa de 13 em 13 -> qual naipe.
        # "%" (resto) diz a posicao dentro do naipe -> qual valor.
        suit = SUIT_ORDER[local // len(RANKS)]
        rank = RANKS[local % len(RANKS)]
        return rank, suit
    return "JOKER", None  # locais 52 e 53 -> coringa (sem naipe)


def card_to_id(rank: str, suit: str, deck: int = 0):
    """Inverso de id_to_card. Com 2 baralhos o inverso nao e unico: 'deck'
    (0=A, 1=B) escolhe qual das duas vias retornar."""
    if suit not in SUIT_ORDER or rank not in RANKS:  # carta invalida -> nada
        return None
    # faz a conta ao contrario: baralho escolhido + posicao do naipe + posicao do valor.
    return deck * DECK_SIZE + SUIT_ORDER.index(suit) * len(RANKS) + RANKS.index(rank)


def _card_name(marker_id: int) -> str:
    # devolve um nome curtinho da carta pra usar no nome do arquivo PNG.
    card = id_to_card(marker_id)
    if card is None:
        return f"id{marker_id}"
    if card[1] is None:        # naipe None -> coringa
        return "JOKER"
    return f"{card[0]}{card[1]}"  # ex: "QC"


def _aruco_dict():
    # pega o "dicionario" de marcadores que o OpenCV ja conhece (o DICT_4X4_250).
    # getattr(aruco, "DICT_4X4_250") busca esse nome dentro da ferramenta aruco.
    return aruco.getPredefinedDictionary(getattr(aruco, ARUCO_DICT_ID))


# =============================================================================
# GERAR OS MARCADORES PRA IMPRIMIR
# =============================================================================

def gerar_marcadores(out_dir: str = "marcadores", size: int = 600):
    """Salva um PNG por marcador (2 baralhos x 54 = 108) com rotulo, pra imprimir.

    O rotulo traz a carta, o id e o baralho (A/B). As duas vias da mesma carta
    tem ids diferentes (a deteccao precisa de id unico) mas o MESMO nome de carta.
    """
    if cv2 is None:  # sem OpenCV nao da pra desenhar imagem
        print("[!] OpenCV ausente. pip install opencv-contrib-python")
        return
    os.makedirs(out_dir, exist_ok=True)  # cria a pasta de saida (sem erro se ja existe)
    dic = _aruco_dict()
    for mid in range(N_MARKERS):  # pra cada id de 0 a 107...
        # desenha o quadradinho do marcador (uma imagem de 'size' x 'size' pixels).
        marker = aruco.generateImageMarker(dic, mid, size)
        # poe uma moldura branca em volta (espaco em cima/baixo/lados) pra caber o rotulo.
        canvas = cv2.copyMakeBorder(marker, 50, 110, 50, 50,
                                    cv2.BORDER_CONSTANT, value=255)
        deck = "AB"[mid // DECK_SIZE]  # ids 0..53 -> "A"; 54..107 -> "B"
        card = id_to_card(mid)
        # monta o texto do rotulo conforme seja coringa, carta normal, ou desconhecido.
        if card and card[1] is None:
            label = f"JOKER  (id {mid} - baralho {deck})"
        elif card:
            label = f"{card[0]} {SUIT_NAMES[card[1]]}  (id {mid} - baralho {deck})"
        else:
            label = f"id {mid}"
        h = canvas.shape[0]  # altura da imagem (pra posicionar o texto la embaixo)
        # escreve o rotulo na imagem (cv2.putText desenha letras sobre os pixels).
        cv2.putText(canvas, label, (50, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
        # monta o caminho do arquivo, ex: "marcadores/marker_011_A_QC.png".
        # "{mid:03d}" escreve o numero com 3 digitos (11 -> "011"), pra ordenar bonito.
        path = os.path.join(out_dir,
                            f"marker_{mid:03d}_{deck}_{_card_name(mid)}.png")
        cv2.imwrite(path, canvas)  # salva a imagem em disco
    print(f"[OK] {N_MARKERS} marcadores em '{out_dir}/' "
          f"({N_DECKS} baralhos x {DECK_SIZE}, dicionario {ARUCO_DICT_ID}, "
          f"{size}px). Imprima e cole nas cartas.")


# =============================================================================
# PROJECAO (HUD desenhado sobre a imagem da webcam)
# =============================================================================

def _put(img, text, org, scale=0.8, color=(255, 255, 255), thick=2):
    """Texto com contorno preto, pra ler por cima da imagem da camera."""
    # desenha o texto DUAS vezes: primeiro grosso e preto (contorno), depois fino
    # e colorido por cima. Assim da pra ler mesmo sobre uma imagem clara.
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale,
                (0, 0, 0), thick + 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale,
                color, thick, cv2.LINE_AA)


def _draw_hud(frame, partida):
    # desenha o "painel do operador" sobre a imagem: titulo, vez, ultima carta e
    # a barrinha de degradacao. So aparece se o HUD estiver ligado (tecla 'h').
    h, w = frame.shape[:2]  # altura e largura da imagem (em pixels)
    _put(frame, "CANASTRA SUJA", (20, 40), 1.0, (255, 255, 255), 2)
    _put(frame, f"Vez: {partida.vez_label}", (20, 80), 0.9, (80, 220, 255), 2)
    _put(frame, f"Ultima: {partida.ultima_str()}", (20, 115), 0.7, (200, 200, 200), 2)
    # barra de degradacao
    pct = partida.corrupcao  # o quanto ja sujou (0..1)
    bx, by, bw, bh = 20, h - 50, min(360, w - 40), 22  # posicao/tamanho da barra
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (60, 60, 60), -1)            # fundo
    cv2.rectangle(frame, (bx, by), (bx + int(bw * pct), by + bh), (40, 40, 230), -1)  # preenchido
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (255, 255, 255), 1)          # contorno
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
    barato (numpy/OpenCV), sem camada visual extra.

    (Nivel tecnico avancado: este metodo mexe direto nos numeros dos pixels com
    NumPy. Voce nao precisa entender cada conta -- a ideia geral e "estraga a
    imagem de varios jeitos, cada vez mais forte conforme a sujeira sobe".)"""
    kicks = kicks or {}  # se ninguem passou socos, usa um dicionario vazio
    if np is None or (level <= 0.01 and not kicks):  # sem NumPy ou nada a sujar -> sai
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
        b, g, r = cv2.split(out)  # separa a imagem nas 3 cores
        # np.roll desliza uma cor pro lado; faz a azul ir pra um lado e a vermelha
        # pro outro -> aquele efeito de "imagem 3D desalinhada".
        out = cv2.merge([np.roll(b, shift, axis=1), g, np.roll(r, -shift, axis=1)])

    # 2. bitcrush de cor (Paus/saturate): esmaga a profundidade de bits (menos tons
    #    de cor -> a imagem fica "chapada", tipo videogame antigo)
    bits = int(round(crush * 5))                  # ate 5 bits fora -> 3-bit color
    if bits > 0:
        mask = (0xFF << bits) & 0xFF
        out = (out & np.uint8(mask))

    # 3. scanlines: estrias que escurecem linhas alternadas (puro acumulo)
    if level > 0.2:
        dark = 1.0 - ((level - 0.2) * 0.7)
        out = out.copy()
        out[::2, :] = (out[::2, :] * dark).astype(np.uint8)  # "::2" = de 2 em 2 linhas

    # 4. blocos arrancados (Espadas/shards): datamosh tosco -- copia pedacos da
    #    imagem pra lugares ligeiramente errados, varias vezes.
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

    # 5. ruido granulado que cresce com o acumulo (chuvisco, tipo TV sem sinal)
    if level > 0.3:
        sigma = (level - 0.3) * 60
        noise = np.random.normal(0, sigma, (h, w, 1)).astype(np.int16)
        out = np.clip(out.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return out


def _try_open(index: int, backend):
    # tenta abrir UM indice com UM backend e CONFIRMA com uma leitura real.
    # No Windows o DSHOW as vezes diz isOpened()=True mas nao entrega quadro;
    # so confiamos se um cap.read() de fato vier com imagem.
    cap = cv2.VideoCapture(index, backend) if backend is not None \
        else cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release()
        return None
    # PEDE 720p (1280x720). Quanto mais pixels, mais LONGE o marcador ainda e
    # "lido": a 480p as distancias de deteccao caem pela METADE. So um PEDIDO --
    # se a webcam nao tiver 720p ela entrega a resolucao dela mesmo, sem quebrar.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    ok, frame = False, None
    for _ in range(8):  # da uns quadros de "esquenta" pra camera acordar
        ok, frame = cap.read()
        if ok and frame is not None:
            return cap
    cap.release()  # abriu mas nao entregou imagem -> trata como falha
    return None


def _open_camera(index: int):
    """Abre a camera de forma resiliente: tenta o indice pedido em varios
    backends e, se falhar, varre os outros indices (0..3). Devolve (cap, idx_real)
    ou (None, -1) se nada funcionou.

    Por que: no Windows o indice 0 nem sempre e a webcam (pode ser camera virtual
    ou sensor), e um backend so as vezes nao abre o dispositivo certo. Tentar
    DSHOW -> MSMF -> ANY e varrer indices acha a HP sozinho."""
    # ordem de backends: no Windows DSHOW costuma abrir mais rapido; MSMF e o
    # nativo moderno; ANY deixa o OpenCV escolher. Fora do Windows, so o padrao.
    if sys.platform.startswith("win"):
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    else:
        backends = [None]

    # primeiro tudo no indice pedido; depois os indices 0..3 (sem repetir o pedido)
    indices = [index] + [i for i in range(4) if i != index]
    for idx in indices:
        for backend in backends:
            cap = _try_open(idx, backend)
            if cap is not None:
                if idx != index:
                    print(f"[i] camera {index} nao respondeu; usando a camera {idx}.")
                return cap, idx
    return None, -1


def _set_fullscreen(win, on):
    # liga ou desliga a tela cheia da janela 'win'.
    cv2.setWindowProperty(
        win, cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN if on else cv2.WINDOW_NORMAL)


# =============================================================================
# O LOOP: webcam -> deteccao -> carta -> som/degradacao + projecao
# =============================================================================

# Debounce: um marcador precisa aparecer ESTAVEL por STABLE_FRAMES quadros pra
# disparar uma vez; so dispara de novo se sumir por GONE_FRAMES (carta tirada
# e mostrada outra vez). Evita re-disparo da carta parada na mesa.
# (Sem isso, uma carta parada na frente da camera dispararia 30x por segundo!)
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

    # cria o maestro da partida e carrega os habitats (igual ao teclado).
    from b_partida import Partida
    partida = Partida(num_jogadores, seed, verbose=True)
    print("  " + partida.mesa.resumo())
    partida.preload()

    # prepara o "detetor" de marcadores do OpenCV.
    dic = _aruco_dict()
    params = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(dic, params)

    cap, camera_index = _open_camera(camera_index)  # abre a webcam (com fallback)
    if cap is None:
        print(f"[!] nao consegui abrir nenhuma camera (tentei indices 0..3 em "
              f"DSHOW/MSMF/ANY).")
        print("    Causas comuns:")
        print("      - outro app esta usando a webcam (Teams, Zoom, navegador,")
        print("        app Camera do Windows, OBS, utilitario HP) -> feche-os;")
        print("      - permissao da camera desligada (Config. > Privacidade >")
        print("        Camera > 'Permitir que aplicativos da area de trabalho...');")
        print("      - a webcam HP esta desconectada ou com driver com problema.")
        return

    win = "CANASTRA SUJA"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)  # cria a janela da projecao
    if fullscreen:
        _set_fullscreen(win, True)

    # dois "cadernos" pro debounce (ver explicacao em STABLE_FRAMES/GONE_FRAMES):
    seen = {}    # id -> quadros consecutivos visto (estabilidade)
    active = {}  # id -> quadros consecutivos sumido (presente=ja disparou)
    prev_disp = None  # ultimo quadro projetado (pro stutter da degradacao)

    # mostra a resolucao que a webcam REALMENTE entregou (pode nao ser 720p).
    cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"\n[OK] webcam no ar a {cam_w}x{cam_h}. Vire as cartas na frente da camera.")
    if cam_w < 1280:
        print("     (abaixo de 720p -> marcadores precisam estar MAIS PERTO; "
              "use marcadores maiores se possivel.)")
    print("     teclas na janela: q/ESC=sair  f=tela cheia  h=HUD  m=espelhar  g=degradar  r=nova mao\n")

    # "try/finally": faca o laco; aconteca o que acontecer (saida normal ou erro),
    # no FIM solte a camera e feche as janelas direitinho (o bloco 'finally').
    try:
        while True:  # o laco roda uma vez por QUADRO da camera (varias vezes por segundo)
            ok, frame = cap.read()  # le um quadro (a foto atual). 'ok' diz se deu certo.
            if not ok:
                print("[!] falha lendo a camera. Encerrando.")
                break

            # procura marcadores no quadro. Devolve os cantos, os ids achados, etc.
            corners, ids, _ = detector.detectMarkers(frame)
            present = set()  # um "conjunto" (lista sem repetidos) dos ids vistos AGORA
            if ids is not None and len(ids) > 0:
                present = {int(x) for x in ids.flatten()}  # junta todos os ids num conjunto
                aruco.drawDetectedMarkers(frame, corners, ids)  # desenha as bordas na imagem

            # marcadores NOVOS e estaveis deste quadro (varios juntos = rajada)
            fired = []  # cartas que vao "disparar" neste quadro
            for mid in present:
                seen[mid] = seen.get(mid, 0) + 1  # conta +1 quadro que esse id apareceu
                if mid in active:
                    active[mid] = 0  # ja disparou e continua na mesa -> zera ausencia
                elif seen[mid] >= STABLE_FRAMES:  # apareceu estavel o bastante -> dispara!
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
                    if active[mid] >= GONE_FRAMES:  # sumiu tempo suficiente...
                        del active[mid]             # ...esquece (pode disparar de novo)
                        seen.pop(mid, None)
            for mid in list(seen.keys()):
                if mid not in present and mid not in active:
                    seen.pop(mid, None)

            # 'disp' e a imagem que vai pra tela. Se 'mirror', espelha (tipo selfie).
            disp = cv2.flip(frame, 1) if mirror else frame.copy()
            # a projecao apodrece com a degradacao E glitcha PELO NAIPE de cada
            # carta (video_kicks: detune->cor, saturate->bitcrush, shards->blocos,
            # freeze->trava de quadro aqui embaixo). O tracking nao se importa:
            # a deteccao roda no 'frame' cru, nao nesta imagem.
            if degradar:
                lvl = partida.corrupcao
                kicks = partida.glitch.video_kicks()  # os "socos" visuais por naipe
                # Ouros (freeze) -> trava de quadro: o soco do naipe + o acumulo
                # perto do teto decidem a chance de repetir o quadro anterior.
                stutter = max(0.0, (lvl - 0.5) * 0.6) + kicks.get("freeze", 0.0) * 0.8
                # random.random() sorteia um numero entre 0 e 1; se cair abaixo da
                # "chance de travar", mostra o quadro velho de novo (efeito de engasgo).
                if prev_disp is not None and random.random() < stutter:
                    disp = prev_disp
                else:
                    disp = _degradar(disp, lvl, kicks)  # senao, apodrece a imagem atual
                    prev_disp = disp
            if hud:  # operador: ligar so pra conferir (aparece pro publico tb)
                _draw_hud(disp, partida)
            cv2.imshow(win, disp)  # finalmente, mostra a imagem na janela

            # le se alguma tecla foi apertada (espera 1 milissegundo). O "& 0xFF"
            # e so um ajuste tecnico pra pegar a tecla certa em qualquer sistema.
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):     # 27 = tecla ESC; ord('q') = o codigo do 'q'
                break
            elif key == ord('f'):
                fullscreen = not fullscreen        # inverte (liga<->desliga) tela cheia
                _set_fullscreen(win, fullscreen)
            elif key == ord('h'):
                hud = not hud                       # liga/desliga o HUD
            elif key == ord('m'):
                mirror = not mirror                 # liga/desliga o espelho
            elif key == ord('g'):
                degradar = not degradar             # liga/desliga o apodrecer da imagem
            elif key == ord('r'):
                partida.reset()                     # nova mao (zera a sujeira)
    finally:
        # sempre executado no fim: devolve a camera ao sistema e fecha tudo limpo.
        cap.release()
        cv2.destroyAllWindows()
        partida.encerrar()
        print("Fim da mao. O baralho se recolhe, sujo.")


# =============================================================================
# MAIN
# =============================================================================

def _ask_camera() -> int:
    # pergunta qual camera usar (0 e a primeira; se tiver mais de uma, 1, 2...).
    try:
        t = input("Indice da camera (0,1,2...) [0]: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)
    try:
        return int(t)
    except ValueError:
        return 0  # se digitou algo que nao e numero, usa 0


def main():
    # sys.argv sao as "palavras" digitadas depois de 'python b_aruco.py'.
    # [1:] pega da segunda em diante (a primeira e o nome do arquivo).
    args = sys.argv[1:]

    # se a primeira palavra for "gerar" (ou similar), so gera os PNGs e sai.
    if args and args[0] in ("gerar", "markers", "marcadores"):
        out = args[1] if len(args) > 1 else "marcadores"  # pasta opcional
        gerar_marcadores(out)
        return

    print("=" * 64)
    print("CANASTRA SUJA - ArUco (webcam) - a projecao e a imagem da camera")
    print("=" * 64)

    if cv2 is None:  # sem OpenCV: avisa e cai no modo teclado (a peca nao para)
        print("\n[!] OpenCV nao instalado -> deteccao por webcam indisponivel.")
        print("    pip install opencv-contrib-python")
        print("    (e uma webcam). Por ora, caindo no simulador por teclado.\n")
        import b_teclado
        b_teclado.main()
        return

    print("Mostre os marcadores das cartas pra webcam. Pra gerar os marcadores")
    print("pra imprimir:  python b_aruco.py gerar\n")

    # reaproveita as perguntas do teclado (jogadores + seed) pra nao repetir codigo.
    import b_teclado
    num = b_teclado.ask_num_jogadores()
    seed = b_teclado.ask_seed()
    cam = _ask_camera()
    run(num, seed, camera_index=cam)  # parte pra deteccao por webcam


if __name__ == "__main__":
    main()
