"""
A_CAMA - CANASTRA SUJA: a cama (estado rolante) -- DORMENTE na peca ao vivo

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

*** ATENCAO (dormente): este vibrafone foi TIRADO da peca ao vivo. A b_partida
*** NAO chama mais CamaViva.tocar_carta() -- veja o comentario "Vibrafone
*** REMOVIDO" la no b_partida.jogar(). O codigo aqui continua intacto e FUNCIONA
*** no demo (python a_cama.py), mas NAO soa durante o jogo. Fica como registro da
*** poetica original e por usar a mesma matematica da camada A (nucleo_compositor).
*** Este arquivo e mais avancado: ele usa a "matematica das cartas" que mora
*** no nucleo_compositor.py. Voce NAO precisa entender a matematica pra ler
*** aqui -- pensa nela como uma caixa-preta que, dada uma carta, devolve um
*** numero. Aqui a gente so usa esse numero pra mexer no som.

Em uma frase: este arquivo e o VIBRAFONE que os jogadores tocam. Imagine um
painel com 7 botoes (altura da nota, microafinacao, ressonancia, ecos, volume,
articulacao, oitava). Toda carta jogada GIRA UM desses botoes (sempre o
proximo da fila) e faz o vibrafone soar JA com o painel do jeito que ficou.
O painel nunca e zerado no meio -- ele vai sendo esculpido carta a carta. E o
que a gente chama de "estado rolante".

O PAINEL DE 7 BOTOES
--------------------
Uma nota do vibrafone tem 7 parametros (os mesmos do nucleo_compositor, na
mesma ordem). Pensa neles como 7 botoes de um painel:

    0. NOTA          (do, re, mi...)
    1. ALTERACAO     (cents / microtom)
    2. RITMO->RINGAR (quanto a barra soa; NAO e mais duracao metrica)
    3. BPM->ECOS     (espacamento do ping-pong dos harmonicos)
    4. DINAMICA      (forte/fraco)
    5. ARTICULACAO   (seco, acentuado...)
    6. OITAVA        (grave/agudo)

ESTADO ROLANTE
--------------
O painel NUNCA e jogado fora. Ele nasce todo no centro (neutro) e cada carta:
  1. roda a operacao do naipe (gcd/-/+/lcm) sobre o historico -- a MESMA
     matematica do nucleo_compositor, intacta;
  2. usa o resultado pra mexer UM botao (o da vez);
  3. dispara o vibrafone JA com o painel atual;
  4. gira o ponteiro pro proximo botao (0->1->...->6->0...).

Assim toda carta soa na hora, e a "nota" e um som vivo que a mesa vai
esculpindo junto. Como o relogio passa a ser a mao humana, os dois parametros
temporais (ritmo, BPM) deixam de fingir um compasso e viram RESSONANCIA:
ritmo = quanto ringa, BPM = espacamento dos ecos.

FUTURO NAO EXISTE AO VIVO
-------------------------
O K (Rei) no nucleo_compositor e o "futuro" -- ele espia a proxima carta. Ao
vivo a proxima carta ainda nao foi jogada, entao passamos next_card=None e o
proprio process_card cai na identidade do naipe. O Rei vira o neutro: ao vivo,
ninguem ve o futuro.

GRAMATICA (gestos por cima da matematica)
-----------------------------------------
  A  (As)  -> respira: a cama silencia nessa carta (sem badalada).
  10       -> fermata: deixa ringar bem mais (dobra o tempo de ressonancia).
  J/Q/K    -> ja resolvidos na matematica (passado/presente/futuro).
  JOKER    -> acento: re-badala o painel atual no forte, sem mexer na conta.

Manda OSC pro a_synth.scd (namespace /baralho/note, porta 57120) -- o mesmo
handler de sempre. NAO precisa tocar no .scd.

USO RAPIDO (com SC + a_synth.scd rodando):
    python a_cama.py        # simula algumas cartas e ouve o painel rolar
"""

import time                       # pra esperar entre as cartas na demo
from typing import Optional       # "Optional[int]" = "um numero OU nada (None)"

from pythonosc import udp_client  # o carteiro que manda OSC

# Pega varias coisas prontas do arquivo da matematica (nucleo_compositor.py).
# Quando os nomes nao cabem numa linha, o Python deixa listar entre parenteses.
# Voce nao precisa decorar cada um -- sao as pecas da "caixa-preta matematica".
from nucleo_compositor import (
    Suit, Card, InterpretadorEventos, PARAMETERS,
    map_event_to_param, apply_param_mirror, map_event_to_integer,
    nearest_value, RITMO_TO_QUARTERLENGTH, NUMERIC_VALUES,
)
# E pega do a_osc.py (o tocador antigo) algumas tabelas/funcoes de traducao
# pra som (qual MIDI, qual velocidade por dinamica etc.).
from a_osc import (
    DEFAULT_HOST, DEFAULT_PORT, note_pitch_to_midi,
    DYNAMIC_VELOCITY, ARTICULATION_SUSTAIN, ARTICULATION_VELOCITY_BOOST,
)

# Tabela de-para: a sigla do naipe do "mundo" (C/O/E/P) vira o naipe que a
# matematica entende. "Suit.COPAS" e um valor de uma LISTA FIXA de opcoes
# (chamada "enum") -- e so um jeito organizado de dizer "o naipe Copas".
SUIT_LETTER_TO_ENUM = {
    "C": Suit.COPAS, "O": Suit.OUROS, "E": Suit.ESPADAS, "P": Suit.PAUS,
}
SUIT_GLYPH = {"C": "C", "O": "O", "E": "E", "P": "P"}

# Painel inicial: tudo no centro (key 0). DINAMICA nao tem centro (0 nao existe
# na tabela), entao comeca em 'mf' (key 2).
# Isto e uma LISTA com 7 numeros -- a posicao de cada um dos 7 botoes no comeco.
PAINEL_INICIAL = [0, 0, 0, 0, 2, 0, 0]

# A figura ritmica vira tempo de RESSONANCIA (s), nao duracao metrica.
RING_MIN = 0.4   # figura curtissima (fusa) -> badalada quase seca
RING_MAX = 6.0   # figura longuissima (breve) -> ringa longo
RING_FERMATA_MAX = 8.0  # teto quando o 10/joker dobram o ringar


class CamaViva:
    """O vibrafone ao vivo: um painel de 7 botoes que as cartas vao girando.

    Cada carta gira UM botao (na ordem) e dispara uma badalada com o painel
    atual. O painel persiste entre cartas (estado rolante).
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 verbose: bool = True):
        self.client = udp_client.SimpleUDPClient(host, port)  # carteiro OSC
        self.verbose = verbose
        self.interp = InterpretadorEventos()       # a corrente matematica (a caixa-preta)
        self.painel = list(PAINEL_INICIAL)          # COPIA da lista inicial dos 7 botoes
        # (usamos list(...) pra COPIAR; se fizessemos self.painel = PAINEL_INICIAL
        #  mexer no painel mexeria no original. Copiar evita essa armadilha.)
        self.idx = 0                                # qual botao a proxima carta gira (0..6)
        if verbose:
            print(f"[CAMA] vibrafone ao vivo (estado rolante) -> "
                  f"{host}:{port} (/baralho/note)")

    def reset(self):
        """Nova mao: zera a corrente e volta o painel ao centro."""
        self.interp.reset()                 # zera a memoria da matematica
        self.painel = list(PAINEL_INICIAL)  # volta os 7 botoes ao inicio
        self.idx = 0                        # volta o ponteiro pro primeiro botao
        if self.verbose:
            print("[CAMA] painel de volta ao centro (nova mao).")

    # --- valor de display de um botao (a partir da sua key) ------------------

    def _valor(self, param_idx: int):
        # dado o numero de um botao (0..6), descobre o VALOR atual dele
        # (ex: o botao 0 esta em "do"? o botao 4 esta em "mf"?).
        param = PARAMETERS[param_idx]   # a definicao desse botao (nome + tabela)
        key = self.painel[param_idx]    # em que posicao o botao esta agora
        mapping = param['mapping']      # a tabela posicao -> valor desse botao
        if key in mapping:              # se a posicao existe na tabela...
            return mapping[key]         # ...devolve o valor direto
        _, v = nearest_value(mapping, key)  # senao, pega o valor mais PROXIMO
        return v

    # --- a carta toca a cama -------------------------------------------------

    def tocar_carta(self, rank: str, suit: str):
        """Uma carta real gira um botao e dispara a badalada (ou respira, no As)."""
        suit = suit.upper()
        s = SUIT_LETTER_TO_ENUM.get(suit)  # traduz a sigla pro naipe da matematica
        # Cartas que o nucleo entende: A,2..10,J,Q,K. JOKER vai por tocar_joker().
        # "conhecida" vira True/False: a carta e um numero conhecido OU uma das letras.
        conhecida = (rank in NUMERIC_VALUES) or (rank in ("J", "Q", "K"))
        if s is None or not conhecida:  # naipe invalido ou carta estranha -> ignora
            return
        card = Card(type=rank, suit=s)  # monta o objeto "carta" pra matematica

        # 1. roda a operacao do naipe (futuro nao existe ao vivo -> next_card=None)
        slot = self.idx                 # qual botao vamos mexer nesta carta
        param = PARAMETERS[slot]        # a definicao desse botao
        result = self.interp.process_card(card, None)  # <- a caixa-preta calcula
        # converte o numero que saiu da matematica na nova POSICAO do botao:
        key, _ = map_event_to_param(param, map_event_to_integer(result.event_value))
        if result.mirror_applied:                   # Q e K espelham o parametro
            key, _ = apply_param_mirror(param, key)
        self.painel[slot] = key         # grava a nova posicao nesse botao

        # 2. gira o ponteiro pro proximo botao
        # (idx + 1), e o "% 7" faz dar a volta: depois do botao 6 volta pro 0.
        self.idx = (self.idx + 1) % 7

        # 3. gramatica (os gestos especiais por cima da conta)
        if card.is_ace():
            # A = respira: a cama silencia nesta carta (a corrente continua).
            if self.verbose:
                print(f"[CAMA] {rank}{suit} -> respira (As: sem badalada)")
            return
        fermata = (rank == "10")  # o 10 faz ringar o dobro (fermata = True/False)

        # 4. dispara a badalada com o painel atual
        self._badalar(fermata=fermata, slot_changed=slot)

    def tocar_joker(self):
        """Curingao: re-badala o painel atual no forte (acento), sem mexer na conta."""
        self._badalar(fermata=True, accent=True, slot_changed=None)

    # --- envia a nota pro a_synth.scd (nao bloqueia; o SC cuida do envelope) --

    def _badalar(self, fermata: bool = False, accent: bool = False,
                 slot_changed: Optional[int] = None):
        # le o valor ATUAL de cada um dos 7 botoes (o estado do painel agora).
        nota = self._valor(0)
        cents = self._valor(1)
        ritmo = self._valor(2)
        bpm = self._valor(3)
        din = self._valor(4)
        art = self._valor(5)
        oit = self._valor(6)

        # traduz "nota + oitava" pro numero MIDI que o synth entende (ex: 60 = do central).
        midi = note_pitch_to_midi(nota, str(oit))
        # calcula a "velocidade" (forca) da nota a partir da dinamica + articulacao.
        vel = DYNAMIC_VELOCITY.get(din, 80) + ARTICULATION_VELOCITY_BOOST.get(art, 0)
        if accent:          # se for acento (curingao), manda no maximo
            vel = 127
        vel = max(1, min(127, vel))  # prende a forca entre 1 e 127 (limites do MIDI)

        # isinstance(x, int) pergunta "x e um numero inteiro?". Se nao for, usa um
        # padrao seguro (0 cents, 100 bpm) pra nunca mandar lixo pro synth.
        cents_int = cents if isinstance(cents, int) else 0
        bpm_int = bpm if isinstance(bpm, int) else 100

        # figura ritmica -> tempo de ressonancia (s). 10/joker dobram (fermata).
        ql = RITMO_TO_QUARTERLENGTH.get(ritmo, 1.0)   # traduz a figura num numero
        ring = min(RING_MAX, max(RING_MIN, ql))       # prende entre o min e o max
        if fermata:
            ring = min(RING_FERMATA_MAX, ring * 2.0)  # dobra (sem passar do teto)
        sustain_ratio = ARTICULATION_SUSTAIN.get(art, 0.9)  # quanto do ring fica "preso"
        ring_sustain = ring * sustain_ratio

        # manda a badalada pro SuperCollider. A lista [..] sao os dados da nota,
        # na ordem que o a_synth.scd espera (altura, forca, cents, ressonancia...).
        self.client.send_message("/baralho/note", [
            int(midi), int(vel), int(cents_int),
            float(ring), float(ring_sustain),
            str(art), int(bpm_int),
            int(1 if fermata else 0), 0, 0,
        ])

        if self.verbose:
            # so monta um texto bonito pra mostrar o que acabou de tocar. O nome do
            # botao girado, ou "(acento)" quando foi o curingao (slot_changed=None).
            knob = PARAMETERS[slot_changed]['name'] if slot_changed is not None else "(acento)"
            cents_s = f" {cents_int:+d}c" if cents_int else ""  # "+d" mostra sinal (+/-)
            print(f"[CAMA] badala {nota}{oit}{cents_s} {din} {art} "
                  f"ring={ring:.1f}s | girou {knob}")


# =============================================================================
# DEMO (so roda com 'python a_cama.py' -- simula cartas tocando o vibrafone)
# =============================================================================

def main():
    import random

    print("=" * 60)
    print("A_CAMA - o vibrafone ao vivo (estado rolante) - DEMO")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd rodando.")
    print()
    cama = CamaViva(verbose=True)  # FABRICA o vibrafone ao vivo
    print()
    print("[DEMO] 14 cartas -- repara o painel rolando botao a botao...")
    # monta a lista de cartas possiveis: os numeros + as letras J,Q,K.
    ranks = list(NUMERIC_VALUES.keys()) + ["J", "Q", "K"]
    suits = list(SUIT_LETTER_TO_ENUM.keys())  # ["C","O","E","P"]
    for _ in range(14):  # joga 14 cartas ao acaso
        cama.tocar_carta(random.choice(ranks), random.choice(suits))
        time.sleep(1.2)  # espera 1,2s entre as cartas pra dar pra ouvir o painel rolar
    print()
    print("[DEMO] fim. (a cama so anda com carta; reinicie pra zerar o painel)")


if __name__ == "__main__":
    main()
