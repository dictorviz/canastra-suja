"""
B_IMPRIMIR - CANASTRA SUJA: folhas A4 prontas pra grafica (marcadores ArUco)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: o b_aruco.py sabe gerar os 108 quadradinhos (um por carta), mas
cada um sai num PNG solto, em pixels, sem tamanho fisico. Este arquivo pega
esses mesmos quadradinhos e MONTA folhas A4 com o tamanho em CENTIMETROS DE
VERDADE -- 3cm e 3cm na regua -- e salva tudo num PDF. Voce leva o PDF na
grafica, manda imprimir em "tamanho real / 100% / sem ajustar a pagina", recorta
e cola nas cartas.

POR QUE PDF (e nao PNG): PNG so guarda pixels; a grafica pode esticar/encolher
sem querer. O PDF aqui carrega a medida fisica (mm) embutida, entao 3cm sai 3cm.

A "zona muda" (margem branca em volta do marcador): o ArUco PRECISA de um
respiro branco ao redor do quadrado preto pra camera achar a borda. A gente
deixa ~1 modulo (1/6 do lado) de folga branca de cada lado, sempre.

USO:
    python b_imprimir.py              # PDF com os 108 marcadores a 3.0 cm (padrao)
    python b_imprimir.py 2.5          # idem, mas a 2.5 cm de lado
    python b_imprimir.py teste        # 1 pagina de TESTE: 1, 1.5, 2, 2.5 e 3 cm
                                      # (cole numa carta e meca a distancia na SUA
                                      #  webcam antes de imprimir as 108)
    python b_imprimir.py 3.0 saida.pdf  # escolhe o nome do arquivo

Requer: pip install opencv-contrib-python pillow
"""

import sys

try:
    import cv2
    import cv2.aruco as aruco
    import numpy as np
    from PIL import Image
except ImportError:
    cv2 = None
    aruco = None
    np = None
    Image = None

# reaproveita TODO o mapa carta<->id e o dicionario do b_aruco (uma fonte so).
from b_aruco import (
    ARUCO_DICT_ID, N_MARKERS, DECK_SIZE,
    id_to_card, _aruco_dict,
)
from b_samples import SUIT_NAMES

# -- Constantes de papel e impressao -----------------------------------------
DPI = 300                 # densidade de impressao (300 = padrao de grafica)
A4_MM = (210.0, 297.0)    # A4 em milimetros (largura x altura)
MARGIN_MM = 10.0          # margem branca de seguranca na borda da folha
GAP_MM = 4.0              # respiro EXTRA entre um marcador e o vizinho (corte)
LABEL_MM = 5.0            # altura reservada pro rotulo (carta + id) embaixo


def _mm2px(mm: float) -> int:
    """Converte milimetros em pixels nesta densidade (DPI). 25.4 mm = 1 polegada."""
    return int(round(mm * DPI / 25.4))


def _marcador_px(mid: int, lado_px: int) -> "np.ndarray":
    """Desenha UM marcador (so o quadrado preto-e-branco) com 'lado_px' pixels."""
    dic = _aruco_dict()
    return aruco.generateImageMarker(dic, mid, lado_px)


def _rotulo(mid: int) -> str:
    """Texto curto pra escrever embaixo do marcador: carta + id + baralho."""
    deck = "AB"[mid // DECK_SIZE]
    card = id_to_card(mid)
    if card and card[1] is None:
        return f"JOKER  id{mid} {deck}"
    if card:
        return f"{card[0]} {SUIT_NAMES[card[1]]}  id{mid} {deck}"
    return f"id{mid}"


def _celula(mid: int, lado_mm: float, com_rotulo: bool = True) -> "np.ndarray":
    """Monta a 'celula' de um marcador: o quadrado + zona muda branca + linha de
    corte cinza-clara + rotulo. Devolve uma imagem (grade de cinzas, 255=branco)."""
    lado_px = _mm2px(lado_mm)
    quiet_px = max(_mm2px(lado_mm / 6.0), _mm2px(3.0))  # >=1 modulo e >=3mm
    label_px = _mm2px(LABEL_MM) if com_rotulo else 0

    bloco = lado_px + 2 * quiet_px          # marcador + zona muda dos dois lados
    cel_w = bloco
    cel_h = bloco + label_px
    cel = np.full((cel_h, cel_w), 255, dtype=np.uint8)  # tudo branco

    # cola o marcador no centro da zona muda
    marker = _marcador_px(mid, lado_px)
    cel[quiet_px:quiet_px + lado_px, quiet_px:quiet_px + lado_px] = marker

    # linha de corte: retangulo cinza-claro na borda do bloco (so guia de tesoura)
    cv2.rectangle(cel, (0, 0), (bloco - 1, bloco - 1), 200, 1)

    if com_rotulo:
        escala = lado_mm / 30.0 * 0.5  # rotulo proporcional ao tamanho do marcador
        cv2.putText(cel, _rotulo(mid), (quiet_px // 2, bloco + label_px - quiet_px // 3),
                    cv2.FONT_HERSHEY_SIMPLEX, max(escala, 0.35), 0, 1, cv2.LINE_AA)
    return cel


def _nova_pagina() -> "np.ndarray":
    """Uma folha A4 em branco, em pixels, na densidade DPI."""
    return np.full((_mm2px(A4_MM[1]), _mm2px(A4_MM[0])), 255, dtype=np.uint8)


def _colar(pagina: "np.ndarray", cel: "np.ndarray", x: int, y: int) -> None:
    """Cola uma celula na pagina, na posicao (x, y) em pixels (canto superior esq.)."""
    h, w = cel.shape
    pagina[y:y + h, x:x + w] = cel


def _salvar_pdf(paginas, out_path: str) -> None:
    """Salva a lista de paginas (grades numpy) num PDF com a medida FISICA correta.
    O 'resolution=DPI' faz o PDF saber que cada pagina e A4 de verdade (210x297mm)."""
    imgs = [Image.fromarray(p) for p in paginas]
    imgs[0].save(out_path, "PDF", resolution=DPI, save_all=True,
                 append_images=imgs[1:])


# =============================================================================
# 1) O JOGO COMPLETO: 108 marcadores num tamanho so
# =============================================================================

def gerar_pdf(lado_cm: float = 3.0, out_path: str = None) -> None:
    """Gera o PDF com os 108 marcadores, todos com 'lado_cm' cm de lado."""
    if cv2 is None or Image is None:
        print("[!] Faltam libs. pip install opencv-contrib-python pillow")
        return
    if out_path is None:
        out_path = f"marcadores_a4_{lado_cm:.1f}cm.pdf".replace(".", "_", 1)
    lado_mm = lado_cm * 10.0  # o usuario pensa em cm; o resto do codigo trabalha em mm

    # mede uma celula pra saber quantas cabem por linha/coluna
    amostra = _celula(0, lado_mm)
    cel_h, cel_w = amostra.shape
    passo_x = cel_w + _mm2px(GAP_MM)
    passo_y = cel_h + _mm2px(GAP_MM)

    margem = _mm2px(MARGIN_MM)
    util_w = _mm2px(A4_MM[0]) - 2 * margem
    util_h = _mm2px(A4_MM[1]) - 2 * margem
    cols = max(1, util_w // passo_x)
    rows = max(1, util_h // passo_y)
    por_pagina = cols * rows

    paginas = []
    pagina = _nova_pagina()
    pos = 0
    for mid in range(N_MARKERS):
        if pos == por_pagina:           # encheu a folha -> comeca outra
            paginas.append(pagina)
            pagina = _nova_pagina()
            pos = 0
        col = pos % cols
        row = pos // cols
        x = margem + col * passo_x
        y = margem + row * passo_y
        _colar(pagina, _celula(mid, lado_mm), x, y)
        pos += 1
    paginas.append(pagina)

    _salvar_pdf(paginas, out_path)
    print(f"[OK] '{out_path}': {N_MARKERS} marcadores a {lado_cm:.1f}cm, "
          f"{cols}x{rows}/folha, {len(paginas)} folhas A4 ({DPI} DPI).")
    print("     Na grafica: imprimir em TAMANHO REAL / 100% (NAO 'ajustar a pagina').")


# =============================================================================
# 2) A PAGINA DE TESTE: varios tamanhos pra medir a distancia na SUA webcam
# =============================================================================

def gerar_teste(out_path: str = "marcadores_a4_teste.pdf") -> None:
    """Uma folha so com marcadores em 1.0, 1.5, 2.0, 2.5 e 3.0 cm. Imprima,
    cole numa carta e veja, na SUA webcam, a partir de que distancia cada
    tamanho some. Ai voce escolhe o tamanho final com seguranca."""
    if cv2 is None or Image is None:
        print("[!] Faltam libs. pip install opencv-contrib-python pillow")
        return

    tamanhos_cm = [1.0, 1.5, 2.0, 2.5, 3.0]
    pagina = _nova_pagina()
    margem = _mm2px(MARGIN_MM)

    # titulo
    cv2.putText(pagina, "TESTE DE TAMANHO - cole numa carta e meca a distancia",
                (margem, margem), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2, cv2.LINE_AA)

    y = margem + _mm2px(8.0)
    for i, cm in enumerate(tamanhos_cm):
        cel = _celula(i, cm * 10.0, com_rotulo=False)
        _colar(pagina, cel, margem, y)
        # rotulo grande do tamanho, ao lado do marcador
        cv2.putText(pagina, f"{cm:.1f} cm",
                    (margem + cel.shape[1] + _mm2px(6.0), y + cel.shape[0] // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2, cv2.LINE_AA)
        y += cel.shape[0] + _mm2px(GAP_MM)

    _salvar_pdf([pagina], out_path)
    print(f"[OK] '{out_path}': folha de teste (1.0 a 3.0 cm).")
    print("     Imprima em TAMANHO REAL, confira com a regua, e teste na webcam.")


# =============================================================================
# MAIN
# =============================================================================

def main():
    args = sys.argv[1:]
    if args and args[0] in ("teste", "test"):
        gerar_teste(args[1] if len(args) > 1 else "marcadores_a4_teste.pdf")
        return
    lado = 3.0
    out = None
    if args:
        try:
            lado = float(args[0].replace(",", "."))  # aceita "2,5" ou "2.5"
        except ValueError:
            print(f"[!] tamanho invalido: {args[0]} (use ex.: 3.0)")
            return
        if len(args) > 1:
            out = args[1]
    gerar_pdf(lado, out)


if __name__ == "__main__":
    main()
