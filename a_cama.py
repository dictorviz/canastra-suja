"""
A_CAMA - CANASTRA SUJA: a cama AO VIVO (estado rolante)

A cama (camada A) deixou de tocar sozinha. Agora QUEM toca sao os jogadores:
cada carta da vida real (teclado/webcam, via b_partida) gira UM parametro do
vibrafone e dispara uma badalada na hora. A peca nao anda sem a mesa.

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

import time
from typing import Optional

from pythonosc import udp_client

from nucleo_compositor import (
    Suit, Card, InterpretadorEventos, PARAMETERS,
    map_event_to_param, apply_param_mirror, map_event_to_integer,
    nearest_value, RITMO_TO_QUARTERLENGTH, NUMERIC_VALUES,
)
from a_osc import (
    DEFAULT_HOST, DEFAULT_PORT, note_pitch_to_midi,
    DYNAMIC_VELOCITY, ARTICULATION_SUSTAIN, ARTICULATION_VELOCITY_BOOST,
)

# Naipe do mundo (C/O/E/P) -> naipe do nucleo_compositor (enum Suit).
SUIT_LETTER_TO_ENUM = {
    "C": Suit.COPAS, "O": Suit.OUROS, "E": Suit.ESPADAS, "P": Suit.PAUS,
}
SUIT_GLYPH = {"C": "C", "O": "O", "E": "E", "P": "P"}

# Painel inicial: tudo no centro (key 0). DINAMICA nao tem centro (0 nao existe
# na tabela), entao comeca em 'mf' (key 2).
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
        self.client = udp_client.SimpleUDPClient(host, port)
        self.verbose = verbose
        self.interp = InterpretadorEventos()       # a corrente matematica
        self.painel = list(PAINEL_INICIAL)          # key de cada um dos 7 botoes
        self.idx = 0                                # qual botao a proxima carta gira
        if verbose:
            print(f"[CAMA] vibrafone ao vivo (estado rolante) -> "
                  f"{host}:{port} (/baralho/note)")

    def reset(self):
        """Nova mao: zera a corrente e volta o painel ao centro."""
        self.interp.reset()
        self.painel = list(PAINEL_INICIAL)
        self.idx = 0
        if self.verbose:
            print("[CAMA] painel de volta ao centro (nova mao).")

    # --- valor de display de um botao (a partir da sua key) ------------------

    def _valor(self, param_idx: int):
        param = PARAMETERS[param_idx]
        key = self.painel[param_idx]
        mapping = param['mapping']
        if key in mapping:
            return mapping[key]
        _, v = nearest_value(mapping, key)
        return v

    # --- a carta toca a cama -------------------------------------------------

    def tocar_carta(self, rank: str, suit: str):
        """Uma carta real gira um botao e dispara a badalada (ou respira, no As)."""
        suit = suit.upper()
        s = SUIT_LETTER_TO_ENUM.get(suit)
        # Cartas que o nucleo entende: A,2..10,J,Q,K. JOKER vai por tocar_joker().
        conhecida = (rank in NUMERIC_VALUES) or (rank in ("J", "Q", "K"))
        if s is None or not conhecida:
            return
        card = Card(type=rank, suit=s)

        # 1. roda a operacao do naipe (futuro nao existe ao vivo -> next_card=None)
        slot = self.idx
        param = PARAMETERS[slot]
        result = self.interp.process_card(card, None)
        key, _ = map_event_to_param(param, map_event_to_integer(result.event_value))
        if result.mirror_applied:                   # Q e K espelham o parametro
            key, _ = apply_param_mirror(param, key)
        self.painel[slot] = key

        # 2. gira o ponteiro pro proximo botao
        self.idx = (self.idx + 1) % 7

        # 3. gramatica
        if card.is_ace():
            # A = respira: a cama silencia nesta carta (a corrente continua).
            if self.verbose:
                print(f"[CAMA] {rank}{suit} -> respira (As: sem badalada)")
            return
        fermata = (rank == "10")

        # 4. dispara a badalada com o painel atual
        self._badalar(fermata=fermata, slot_changed=slot)

    def tocar_joker(self):
        """Curingao: re-badala o painel atual no forte (acento), sem mexer na conta."""
        self._badalar(fermata=True, accent=True, slot_changed=None)

    # --- envia a nota pro a_synth.scd (nao bloqueia; o SC cuida do envelope) --

    def _badalar(self, fermata: bool = False, accent: bool = False,
                 slot_changed: Optional[int] = None):
        nota = self._valor(0)
        cents = self._valor(1)
        ritmo = self._valor(2)
        bpm = self._valor(3)
        din = self._valor(4)
        art = self._valor(5)
        oit = self._valor(6)

        midi = note_pitch_to_midi(nota, str(oit))
        vel = DYNAMIC_VELOCITY.get(din, 80) + ARTICULATION_VELOCITY_BOOST.get(art, 0)
        if accent:
            vel = 127
        vel = max(1, min(127, vel))

        cents_int = cents if isinstance(cents, int) else 0
        bpm_int = bpm if isinstance(bpm, int) else 100

        # figura ritmica -> tempo de ressonancia (s). 10/joker dobram (fermata).
        ql = RITMO_TO_QUARTERLENGTH.get(ritmo, 1.0)
        ring = min(RING_MAX, max(RING_MIN, ql))
        if fermata:
            ring = min(RING_FERMATA_MAX, ring * 2.0)
        sustain_ratio = ARTICULATION_SUSTAIN.get(art, 0.9)
        ring_sustain = ring * sustain_ratio

        self.client.send_message("/baralho/note", [
            int(midi), int(vel), int(cents_int),
            float(ring), float(ring_sustain),
            str(art), int(bpm_int),
            int(1 if fermata else 0), 0, 0,
        ])

        if self.verbose:
            knob = PARAMETERS[slot_changed]['name'] if slot_changed is not None else "(acento)"
            cents_s = f" {cents_int:+d}c" if cents_int else ""
            print(f"[CAMA] badala {nota}{oit}{cents_s} {din} {art} "
                  f"ring={ring:.1f}s | girou {knob}")


# =============================================================================
# DEMO
# =============================================================================

def main():
    import random

    print("=" * 60)
    print("A_CAMA - o vibrafone ao vivo (estado rolante) - DEMO")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd rodando.")
    print()
    cama = CamaViva(verbose=True)
    print()
    print("[DEMO] 14 cartas -- repara o painel rolando botao a botao...")
    ranks = list(NUMERIC_VALUES.keys()) + ["J", "Q", "K"]
    suits = list(SUIT_LETTER_TO_ENUM.keys())
    for _ in range(14):
        cama.tocar_carta(random.choice(ranks), random.choice(suits))
        time.sleep(1.2)
    print()
    print("[DEMO] fim. (a cama so anda com carta; reinicie pra zerar o painel)")


if __name__ == "__main__":
    main()
