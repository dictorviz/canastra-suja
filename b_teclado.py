"""
B_TECLADO - teste da CAMADA B por teclado (Fase 1, sem hardware NFC)

Simula a cartomante puxando cartas: voce digita uma carta e o mundo
ATRAVESSA pro proximo habitat sonoro (crossfade), sorteado do baralho do
mundo (b_samples -> b_synth.scd). Quando o leitor NFC (b_nfc.py, Fase 3)
existir, ele entra no LUGAR deste teclado -- o resto da cadeia nao muda.

PRE-REQUISITOS:
    1. SuperCollider aberto com a_synth.scd E b_synth.scd rodando.
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

from b_samples import MundoPlayer, RANKS, SUIT_NAMES


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
    print("  Digite <valor><naipe>:  QC  10O  AP  7E")
    print("    valores: A 2 3 4 5 6 7 8 9 10 J Q K")
    print("    naipes:  C=Copas  O=Ouros  E=Espadas  P=Paus")
    print("  ENTER = carta aleatoria  |  . = silencio  |  q = sair  |  ? = ajuda")
    print("  (cada carta ATRAVESSA pro proximo habitat do baralho do mundo)")
    print()


def main():
    print("=" * 60)
    print("B_TECLADO - a cartomante (teste por teclado)")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd E b_synth.scd rodando.")
    print_help()

    player = MundoPlayer(verbose=True)
    player.preload()
    print("\n[OK] baralho do mundo montado. Puxe uma carta.\n")

    while True:
        try:
            raw = input("carta> ").strip()
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
            player.stop()
            print("  ... silencio (habitat encerrado)")
            continue

        if raw == "":
            rank, suit = random_card()
        else:
            parsed = parse_card(raw)
            if parsed is None:
                print("  [!] carta invalida. '?' pra ajuda.")
                continue
            rank, suit = parsed

        player.play_card(rank, suit)

    player.stop()
    print("A cartomante recolhe o baralho. Tchau.")


if __name__ == "__main__":
    main()
