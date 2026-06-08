"""
B_SAMPLES - CANASTRA SUJA (o baralho do mundo)

O "baralho do mundo": a pasta samples/ tem uma biblioteca de HABITATS
sonoros longos (paisagens convertidas de biblioteca/*.mp3). Eles formam o
BARALHO, embaralhado. Cada carta do Buraco puxada (teclado hoje, webcam/ArUco
amanha) faz o mundo ATRAVESSAR -- crossfade do habitat atual pro proximo
habitat sorteado. Um lugar de cada vez.

A carta nao carrega o som diretamente: ela sorteia o proximo habitat, define
a ESPACIALIZACAO pelo naipe e rege a DEGRADACAO (ver b_glitch). O som vem do
baralho do mundo.

FLUXO:
    1. a_synth.scd E b_synth.scd rodando no SC.
    2. MundoPlayer().preload()  -> /mundo/load de cada WAV + monta o baralho.
    3. play_card('Q','C')       -> sorteia o proximo habitat e crossfade.

USO RAPIDO (com SC + os dois .scd rodando):
    python b_samples.py          # atravessa alguns habitats em sequencia
"""

import contextlib
import glob
import os
import random
import time
import wave
from typing import Dict, List, Optional

from pythonosc import udp_client

# =============================================================================
# CONFIG
# =============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 57120  # mesma porta do SC; namespace /mundo/* separado

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(HERE, "samples")

# Habitats com duracao >= LOOP_THRESHOLD loopam (permanece-se neles ate a
# proxima carta). Mais curtos tocam uma vez e somem no crossfade.
LOOP_THRESHOLD = 12.0
DEFAULT_FADE    = 5.0   # segundos de crossfade entre habitats
DEFAULT_AMP     = 0.22  # fantasmagorico: bem abaixo do synth protagonista
DEFAULT_LPF     = 2600  # Hz -- veu de distancia (corta agudos do habitat)
DEFAULT_REVWASH = 0.45  # cauda de reverb embutida no habitat

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUIT_NAMES = {"C": "Copas", "O": "Ouros", "E": "Espadas", "P": "Paus"}

# Espacializacao placeholder por naipe (estereo). Fase 5 vira octofonia:
# Copas=horario, Ouros=anti, Espadas=salto, Paus=centro.
SUIT_PAN = {"C": -0.25, "O": 0.6, "E": -0.6, "P": 0.25}


# =============================================================================
# O BARALHO DO MUNDO (sorteio sem reposicao, reembaralha ao esgotar)
# =============================================================================

class WorldDeck:
    """Embaralha as chaves dos habitats; draw() devolve o proximo sem repetir
    ate esgotar, ai reembaralha (evitando emendar a mesma carta na virada)."""

    def __init__(self, keys: List[str], rng: Optional[random.Random] = None):
        self.keys = list(keys)
        self.rng = rng or random.Random()
        self._pile: List[str] = []
        self._last: Optional[str] = None
        self._reshuffle()

    def _reshuffle(self):
        self._pile = list(self.keys)
        self.rng.shuffle(self._pile)
        # evita repetir a ultima carta logo na virada do baralho
        if self._last is not None and len(self._pile) > 1 and self._pile[-1] == self._last:
            self._pile[0], self._pile[-1] = self._pile[-1], self._pile[0]

    def draw(self) -> Optional[str]:
        if not self.keys:
            return None
        if not self._pile:
            self._reshuffle()
        key = self._pile.pop()
        self._last = key
        return key


# =============================================================================
# PLAYER (manda OSC pro b_synth.scd)
# =============================================================================

class MundoPlayer:
    """Carrega os habitats no SC e atravessa entre eles a cada carta."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 verbose: bool = True, seed: Optional[int] = None):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.client = udp_client.SimpleUDPClient(host, port)
        self.paths: Dict[str, str] = {}
        self.durations: Dict[str, float] = {}
        self.deck: Optional[WorldDeck] = None
        self._rng = random.Random(seed)
        if verbose:
            print(f"[MUNDO] OSC -> {host}:{port} (namespace /mundo/*)")

    def preload(self) -> Dict[str, str]:
        """Le os WAVs de samples/, manda /mundo/load de cada um e monta o baralho."""
        wavs = sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.wav")))
        if not wavs:
            raise RuntimeError(
                f"nenhum WAV em {SAMPLES_DIR}. Converta biblioteca/*.mp3 primeiro.")
        for path in wavs:
            key = os.path.splitext(os.path.basename(path))[0]  # '001'
            self.paths[key] = path
            try:
                with contextlib.closing(wave.open(path, "rb")) as w:
                    self.durations[key] = w.getnframes() / w.getframerate()
            except Exception:
                self.durations[key] = 0.0
            self.client.send_message("/mundo/load", [str(key), str(path)])
        self.deck = WorldDeck(list(self.paths.keys()), self._rng)
        if self.verbose:
            total = sum(self.durations.values())
            print(f"[MUNDO] {len(self.paths)} habitats carregados "
                  f"({total/60:.0f} min de mundo).")
        time.sleep(0.6)  # Buffer.read e async no SC
        return self.paths

    def bed(self, key: str, fade: float = DEFAULT_FADE, amp: float = DEFAULT_AMP,
            pan: float = 0.0, lpf: float = DEFAULT_LPF,
            rev_wash: float = DEFAULT_REVWASH):
        """Atravessa pro habitat 'key' (crossfade)."""
        loop = 1 if self.durations.get(key, 0.0) >= LOOP_THRESHOLD else 0
        self.client.send_message(
            "/mundo/bed", [str(key), float(fade), float(amp), float(pan),
                           int(loop), float(lpf), float(rev_wash)])

    def play_card(self, rank: str, suit: str, fade: float = DEFAULT_FADE,
                  amp: float = DEFAULT_AMP) -> Optional[str]:
        """
        A carta fisica: sorteia o proximo habitat do baralho do mundo e
        atravessa pra ele. O naipe define a espacializacao. Retorna a chave
        do habitat revelado (ou None se o baralho esta vazio).
        """
        if self.deck is None:
            raise RuntimeError("chame preload() antes de play_card().")
        suit = suit.upper()
        key = self.deck.draw()
        if key is None:
            return None
        pan = SUIT_PAN.get(suit, 0.0) + self._rng.uniform(-0.15, 0.15)
        self.bed(key, fade=fade, amp=amp, pan=max(-1.0, min(1.0, pan)))
        if self.verbose:
            dur = self.durations.get(key, 0.0)
            loop = "loop" if dur >= LOOP_THRESHOLD else "1x"
            print(f"[MUNDO] {rank}{suit} ({SUIT_NAMES.get(suit, '?')}) "
                  f"-> habitat {key}  ({dur:.0f}s, {loop})")
        return key

    def stop(self, fade: float = DEFAULT_FADE):
        """Encerra o habitat atual (fim da peca)."""
        self.client.send_message("/mundo/stop", [float(fade)])


# =============================================================================
# DEMO
# =============================================================================

def main():
    print("=" * 60)
    print("B_SAMPLES - o baralho do mundo (habitats) - DEMO")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd E b_synth.scd rodando.")
    print()
    player = MundoPlayer()
    player.preload()
    print()
    print("[DEMO] atravessando 5 habitats (8s em cada)...")
    suits = list(SUIT_NAMES.keys())
    for _ in range(5):
        rank = random.choice(RANKS)
        suit = random.choice(suits)
        player.play_card(rank, suit)
        time.sleep(8.0)
    print()
    print("[DEMO] encerrando o ultimo habitat...")
    player.stop()
    print("Pra puxar cartas voce mesmo:  python b_teclado.py")


if __name__ == "__main__":
    main()
