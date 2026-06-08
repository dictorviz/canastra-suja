"""
B_TECLADO - CANASTRA SUJA por teclado (simula a webcam/ArUco)

Simula a virada das cartas do BURACO: voce digita uma carta e o mundo
ATRAVESSA pro proximo habitat sonoro (crossfade), sorteado do baralho do
mundo (b_samples -> b_synth.scd), enquanto a carta soma a degradacao
(b_glitch). Quando a webcam + ArUco (b_aruco.py, planejado) existir, ela
entra no LUGAR deste teclado -- o resto da cadeia nao muda.

PRE-REQUISITOS:
    1. SuperCollider com a_synth.scd (cama) + b_synth.scd (mundo) rodando.
    2. python b_teclado.py

COMO DIGITAR UMA CARTA:
    <valor><naipe>, ex:  QC  10O  AP  7E
    valores: A 2 3 4 5 6 7 8 9 10 J Q K
    naipes:  C=Copas  O=Ouros  E=Espadas  P=Paus
    ENTER (vazio) = compra uma carta ALEATORIA (sente o acaso)
    .  = encerra o habitat atual (silencio)
    ?  = ajuda      |   q = sair
"""

import random

from b_samples import RANKS, SUIT_NAMES
from b_buraco import MIN_JOGADORES, MAX_JOGADORES

# Tokens que lancam o curingao (Joker, sem naipe).
JOKER_TOKENS = ("joker", "coringa", "curingao", "curingão", "z", "j0")


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)
    return ans if ans else default


def ask_num_jogadores() -> int:
    """Pergunta quantos jogadores (2-4). Loop ate um numero valido."""
    while True:
        t = _prompt(f"Numero de jogadores ({MIN_JOGADORES}-{MAX_JOGADORES})", "2")
        try:
            n = int(t)
        except ValueError:
            print("  [!] digite um numero.")
            continue
        if MIN_JOGADORES <= n <= MAX_JOGADORES:
            return n
        print(f"  [!] entre {MIN_JOGADORES} e {MAX_JOGADORES} jogadores.")


def ask_seed():
    """Pergunta a seed (embaralha o baralho do mundo). ENTER = aleatoria."""
    t = _prompt("Seed (numero) ou ENTER pra aleatoria", "aleatoria")
    if t.lower().startswith("aleat") or t == "":
        return None
    try:
        return int(t)
    except ValueError:
        print(f"  [!] '{t}' nao e numero, usando aleatoria.")
        return None


def parse_card(text: str):
    """'10o' -> ('10','O'). Retorna (rank, suit) ou None."""
    t = text.strip().upper().replace(" ", "")
    if len(t) < 2:
        return None
    suit, rank = t[-1], t[:-1]
    if suit not in SUIT_NAMES or rank not in RANKS:
        return None
    return rank, suit


def random_card():
    return random.choice(RANKS), random.choice(list(SUIT_NAMES.keys()))


def print_help():
    print()
    print("  Na vez de cada jogador, lance UMA carta:")
    print("    <valor><naipe>:  QC  10O  AP  7E")
    print("    valores: A 2 3 4 5 6 7 8 9 10 J Q K   (o 2 e curinguinha)")
    print("    naipes:  C=Copas  O=Ouros  E=Espadas  P=Paus")
    print("    JOKER (ou Z) = curingao  |  ENTER = carta aleatoria (simula a virada)")
    print("  Apos lancar, a vez passa pro proximo jogador (sentido horario).")
    print("  .  = silencio  |  r = nova mao (zera a degradacao)  |  q = sair  |  ? = ajuda")
    print()


def run_partida(num_jogadores, seed):
    """Roda a partida (camada B): a vez gira entre os jogadores e cada carta
    lancada atravessa um habitat (b_samples) + soma degradacao (b_glitch).

    Separado do main() pra ser reutilizavel -- a cama generativa (main.py
    opt_jogar) e, no futuro, o ArUco chamam esta funcao direto, sem reprompt.
    """
    from b_partida import Partida
    partida = Partida(num_jogadores, seed, verbose=True)
    print()
    print("  " + partida.mesa.resumo())
    print_help()
    # Canastra Suja NAO usa voz/palavras. Cada carta TOCA a cama (vibrafone ao
    # vivo, a_synth) + atravessa um habitat + suja (b_synth). Sem carta, sem som.
    partida.preload()
    print("\n[OK] mesa pronta. Cada jogador, na sua vez, lanca uma carta.\n")

    while True:
        try:
            raw = input(f"{partida.vez_label} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        low = raw.lower()
        if low in ("q", "sair", "exit", "quit"):
            break
        if low in ("?", "h", "help", "ajuda"):
            print_help()
            continue
        if raw == ".":
            partida.silencio()
            print("  ... silencio (habitat encerrado)")
            continue
        if low in ("r", "reset", "nova"):
            partida.reset()
            print("  ... degradacao zerada (nova mao). A vez continua.")
            continue

        # --- a partir daqui, e uma carta LANCADA (consome a vez) ---
        if low in JOKER_TOKENS:
            partida.jogar_joker()
        elif raw == "":
            partida.jogar_aleatoria()
        else:
            parsed = parse_card(raw)
            if parsed is None:
                print("  [!] carta invalida. '?' pra ajuda. (a vez continua)")
                continue
            partida.jogar(*parsed)

    partida.encerrar()
    print("Fim da mao. O baralho se recolhe, sujo. Tchau.")


def main():
    """Modo standalone (python b_teclado.py): so as cartas, SEM a cama
    generativa. Pergunta jogadores + seed e roda a partida. Pra peca completa
    (cama + cartas), use main.py opcao [1]."""
    print("=" * 60)
    print("CANASTRA SUJA - jogar por teclado (simula a webcam/ArUco)")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd (cama) + b_synth.scd (mundo) rodando.")
    print("Cada carta toca o vibrafone ao vivo + atravessa um habitat + suja.")
    print()
    num_jogadores = ask_num_jogadores()
    seed = ask_seed()
    run_partida(num_jogadores, seed)


if __name__ == "__main__":
    main()
