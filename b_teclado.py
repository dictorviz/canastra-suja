"""
B_TECLADO - CANASTRA SUJA por teclado (simula a webcam/ArUco)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: este arquivo deixa voce JOGAR a peca DIGITANDO as cartas no
teclado, em vez de mostrar cartas pra uma camera. Voce digita "QC" (Dama de
Copas), aperta ENTER, e a carta "acontece": toca a cama (vibrafone), atravessa
um habitat e suja um pouco o som. E o jeito de ensaiar a peca SEM precisar de
camera nem de marcadores impressos.

Quando a webcam (b_aruco.py) entra em cena, ela faz o MESMO papel deste arquivo
-- so muda DE ONDE vem a carta (camera no lugar do teclado). O resto da peca
nao muda nada. Os dois "falam a mesma lingua": uma carta = (valor, naipe).

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

import random  # pra sortear cartas aleatorias

# pega coisas prontas de outros arquivos nossos:
from b_samples import RANKS, SUIT_NAMES                 # lista de valores e nomes de naipe
from b_buraco import MIN_JOGADORES, MAX_JOGADORES       # limites de jogadores (2 e 4)

# Tokens que lancam o curingao (Joker, sem naipe). E uma tupla (lista fixa) com
# varios jeitos de escrever "joker" -- assim a peca aceita qualquer um deles.
JOKER_TOKENS = ("joker", "coringa", "curingao", "curingão", "z", "j0")


def _prompt(text: str, default: str = "") -> str:
    # mostra uma pergunta e LE o que a pessoa digita. input() e a funcao que
    # pausa o programa e espera voce escrever algo e apertar ENTER.
    suffix = f" [{default}]" if default else ""  # mostra o valor padrao entre []
    try:
        # input(...) mostra o texto e devolve o que foi digitado; .strip() tira
        # espacos sobrando das pontas ("  oi  " -> "oi").
        ans = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        # se a pessoa apertar Ctrl+C / Ctrl+D, sai do programa de forma limpa.
        raise SystemExit(0)
    # se digitou algo, devolve o que digitou; se deixou vazio, devolve o padrao.
    return ans if ans else default


def ask_num_jogadores() -> int:
    """Pergunta quantos jogadores (2-4). Loop ate um numero valido."""
    # "while True" = repita PRA SEMPRE (ate alguem mandar parar com return/break).
    # Aqui serve pra insistir na pergunta enquanto a resposta nao for valida.
    while True:
        t = _prompt(f"Numero de jogadores ({MIN_JOGADORES}-{MAX_JOGADORES})", "2")
        try:
            n = int(t)             # tenta transformar o texto digitado em numero
        except ValueError:         # se nao for um numero ("abc")...
            print("  [!] digite um numero.")
            continue               # "continue" = volta pro comeco do while e pergunta de novo
        if MIN_JOGADORES <= n <= MAX_JOGADORES:  # se o numero esta entre 2 e 4...
            return n                              # ...aceita e devolve (sai do while)
        print(f"  [!] entre {MIN_JOGADORES} e {MAX_JOGADORES} jogadores.")


def ask_seed():
    """Pergunta a seed (embaralha o baralho do mundo). ENTER = aleatoria."""
    t = _prompt("Seed (numero) ou ENTER pra aleatoria", "aleatoria")
    # se a resposta comeca com "aleat" (de "aleatoria") ou esta vazia...
    if t.lower().startswith("aleat") or t == "":
        return None   # ...devolve None, que mais pra frente vira "sorteie a semente"
    try:
        return int(t)  # senao tenta usar o numero digitado como semente
    except ValueError:
        print(f"  [!] '{t}' nao e numero, usando aleatoria.")
        return None


def parse_card(text: str):
    """'10o' -> ('10','O'). Retorna (rank, suit) ou None."""
    # arruma o texto: tira espacos, poe em MAIUSCULA, remove espacos do meio.
    t = text.strip().upper().replace(" ", "")
    if len(t) < 2:   # uma carta valida tem pelo menos 2 caracteres (valor+naipe)
        return None
    # AQUI esta o truque de "fatiar texto":
    #   t[-1]  = o ULTIMO caractere (o naipe). Ex: em "10O", e "O".
    #   t[:-1] = TUDO menos o ultimo (o valor). Ex: em "10O", e "10".
    suit, rank = t[-1], t[:-1]
    # so vale se o naipe existe na tabela E o valor existe na lista de cartas.
    if suit not in SUIT_NAMES or rank not in RANKS:
        return None
    return rank, suit  # devolve o par (valor, naipe)


def random_card():
    # sorteia um valor e um naipe ao acaso e devolve o par.
    # list(SUIT_NAMES.keys()) = a lista das siglas de naipe: ["C","O","E","P"].
    return random.choice(RANKS), random.choice(list(SUIT_NAMES.keys()))


def print_help():
    # so imprime o "manual" rapido na tela. Varias linhas de print, nada demais.
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
    # importa AQUI dentro (e nao la em cima) so quando a funcao roda. Cria o
    # objeto Partida, que junta tudo (mesa + cama + mundo + glitch) num lugar so.
    from b_partida import Partida
    partida = Partida(num_jogadores, seed, verbose=True)
    print()
    print("  " + partida.mesa.resumo())  # mostra quem joga
    print_help()                          # mostra o manual
    # Canastra Suja NAO usa voz/palavras. Cada carta TOCA a cama (vibrafone ao
    # vivo, a_synth) + atravessa um habitat + suja (b_synth). Sem carta, sem som.
    partida.preload()  # carrega os habitats no SuperCollider
    print("\n[OK] mesa pronta. Cada jogador, na sua vez, lanca uma carta.\n")

    # O LACO PRINCIPAL do jogo: fica pra sempre lendo o que a pessoa digita e
    # reagindo, ate alguem mandar sair (break).
    while True:
        try:
            # mostra de quem e a vez e espera a carta. ".strip()" limpa as pontas.
            raw = input(f"{partida.vez_label} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break  # "break" = pula pra FORA do while (encerra o laco)

        low = raw.lower()  # versao em minuscula, pra comparar comandos sem ligar pra caixa
        # --- primeiro, os COMANDOS (que NAO sao cartas) ---
        if low in ("q", "sair", "exit", "quit"):  # "in (...)" = "e um destes?"
            break
        if low in ("?", "h", "help", "ajuda"):
            print_help()
            continue   # volta pro comeco do while (nao consome a vez)
        if raw == ".":
            partida.silencio()
            print("  ... silencio (habitat encerrado)")
            continue
        if low in ("r", "reset", "nova"):
            partida.reset()
            print("  ... degradacao zerada (nova mao). A vez continua.")
            continue

        # --- a partir daqui, e uma carta LANCADA (consome a vez) ---
        if low in JOKER_TOKENS:        # se digitou "joker"/"z"/etc -> curingao
            partida.jogar_joker()
        elif raw == "":                # se so apertou ENTER (vazio) -> carta aleatoria
            partida.jogar_aleatoria()
        else:                          # senao, tenta entender como carta normal
            parsed = parse_card(raw)
            if parsed is None:         # nao deu pra entender a carta digitada
                print("  [!] carta invalida. '?' pra ajuda. (a vez continua)")
                continue
            # parsed e o par (rank, suit). O "*" ESPALHA o par nos dois argumentos
            # da funcao: jogar(*('Q','C')) vira jogar('Q','C').
            partida.jogar(*parsed)

    partida.encerrar()  # saiu do laco: encerra tudo com calma (fade final)
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
    num_jogadores = ask_num_jogadores()  # pergunta quantos jogam
    seed = ask_seed()                    # pergunta a semente
    run_partida(num_jogadores, seed)     # toca a partida


if __name__ == "__main__":
    main()
