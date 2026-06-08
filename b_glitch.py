"""
B_GLITCH - CANASTRA SUJA: a DEGRADACAO (a carta suja o som)

Cada carta puxada soma ao NIVEL GLOBAL de degradacao e dispara um glitch
cujo SABOR vem do NAIPE -- cada naipe e uma OPERACAO sobre o som:

    Copas    -> DESAFINA     a altura escorrega/afunda
    Ouros    -> CONGELA      um grao trava/repete
    Espadas  -> FRAGMENTA    granula o HABITAT ATUAL em cacos (ver nota abaixo)
    Paus     -> SATURA       queima/distorce

>>> Espadas (resolvido): no projeto antigo (A Cartomante) a espada cortava a
>>> VOZ do Perec (arquivada). Sem voz, ela agora estilhaca o PROPRIO habitat
>>> que esta tocando -- TGrains sobre ~mundoCurrentBuf no b_synth.scd. Nao
>>> depende mais do tts_cache (load_voice virou opcional/legado).

A degradacao age em PARALELO: sao vozes aditivas em b_synth.scd (SynthDefs
glitch*) que SOAM como a maquina se desfazendo. Sem b_synth.scd carregado,
o som do mundo (camada B) toca limpo.

  - o NAIPE escolhe o SABOR da corrupcao;
  - o VALOR da carta (A..K) escolhe a FORCA do golpe daquela carta (o "kick");
  - o ACUMULO (quantas cartas ja cairam) escolhe a PROFUNDIDADE -- a maquina
    gagueja de leve no comeco e quase desmorona no fim (a profecia desmentida
    devagar).

USO RAPIDO (com SC + a_synth.scd E b_synth.scd rodando):
    python b_glitch.py        # simula cartas e ouve a corrupcao crescer
"""

import glob
import os
import random
import time
from typing import Optional

from pythonosc import udp_client

from b_samples import RANKS, SUIT_NAMES

# =============================================================================
# CONFIG
# =============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 57120  # mesma porta do SC; namespace /mundo/* separado

HERE = os.path.dirname(os.path.abspath(__file__))
TTS_CACHE_DIR = os.path.join(HERE, "tts_cache")

# Naipe -> glitch (a operacao sonora). Cada naipe e UMA operacao sobre o som.
SUIT_GLITCH = {
    "C": "detune",    # Copas   -> desafina
    "O": "freeze",    # Ouros   -> congela
    "E": "shards",    # Espadas -> fragmenta [PLACEHOLDER: voz vazia=mudo]
    "P": "saturate",  # Paus    -> satura
}
GLITCH_LABEL = {
    "detune": "desafina", "freeze": "congela",
    "shards": "fragmenta", "saturate": "satura",
}

# Fracao da DISTANCIA que falta pro teto que cada carta fecha (curva assintotica:
# ver corrupt()). A degradacao sobe rapido no comeco e desacelera perto do fim,
# mas NUNCA chega em 1.0 -- sempre sobra pra onde piorar, sem plato, qualquer que
# seja o tamanho da mao (uma mao de Buraco varia muito de carta a carta).
DEFAULT_STEP = 0.04
DEFAULT_WORDS = 16     # quantas palavras do Perec a espada tem pra cortar


# =============================================================================
# O MOTOR DA CORRUPCAO
# =============================================================================

class GlitchEngine:
    """Acumula a corrupcao e manda /mundo/glitch pro b_synth.scd a cada carta."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 verbose: bool = True, step: float = DEFAULT_STEP,
                 max_words: int = DEFAULT_WORDS):
        self.client = udp_client.SimpleUDPClient(host, port)
        self.verbose = verbose
        self.step = step
        self.max_words = max_words
        self.level = 0.0  # nivel global de corrupcao, 0.0 -> 1.0
        if verbose:
            print(f"[GLITCH] corrupcao paralela -> {host}:{port} (/mundo/glitch)")

    def load_voice(self) -> int:
        """Manda algumas palavras do Perec (tts_cache) pro SC -- a espada
        (Espadas) corta ESTAS palavras em cacos. Reusa o cache da camada A
        sem editar nada dela. Se o cache estiver vazio, os shards ficam mudos
        ate a voz ser renderizada (qualquer run da opcao 1/5/7 enche o cache)."""
        wavs = sorted(glob.glob(os.path.join(TTS_CACHE_DIR, "*.wav")))
        if not wavs:
            if self.verbose:
                print("[GLITCH] tts_cache vazio -> shards (Espadas) mudos "
                      "ate a voz do Perec ser renderizada uma vez.")
            return 0
        random.shuffle(wavs)
        chosen = wavs[:self.max_words]
        for path in chosen:
            key = os.path.splitext(os.path.basename(path))[0]
            self.client.send_message("/mundo/voz_load", [str(key), str(path)])
        if self.verbose:
            print(f"[GLITCH] {len(chosen)} palavras do Perec carregadas "
                  f"(a espada corta estas).")
        time.sleep(0.4)  # Buffer.read async no SC
        return len(chosen)

    def _kick_for_rank(self, rank: str) -> float:
        """Valor da carta -> forca do golpe. A=leve (0.3) ... K=pesado (1.0)."""
        try:
            idx = RANKS.index(rank)
        except ValueError:
            idx = len(RANKS) // 2
        return 0.3 + (idx / (len(RANKS) - 1)) * 0.7

    def corrupt(self, rank: str, suit: str, kick: Optional[float] = None):
        """A carta corrompe: sobe o nivel global e dispara o glitch do naipe."""
        suit = suit.upper()
        tipo = SUIT_GLITCH.get(suit)
        if tipo is None:
            return
        if kick is None:
            kick = self._kick_for_rank(rank)
        # curva assintotica: fecha uma fracao do que falta pro teto. Sobe forte
        # cedo, desacelera perto do fim, mas nunca satura em 1.0 (sem plato).
        self.level += self.step * (1.0 - self.level)
        self.client.send_message(
            "/mundo/glitch", [tipo, float(self.level), float(kick)])
        if self.verbose:
            pct = int(round(self.level * 100))
            print(f"[GLITCH] {rank}{suit} "
                  f"-> {GLITCH_LABEL.get(tipo, tipo)}  |  corrupcao {pct}%")

    def reset(self):
        """Zera a corrupcao -- nova consulta / nova performance."""
        self.level = 0.0
        self.client.send_message("/mundo/glitch_reset", [])
        if self.verbose:
            print("[GLITCH] corrupcao zerada (nova consulta).")


# =============================================================================
# DEMO
# =============================================================================

def main():
    print("=" * 60)
    print("B_GLITCH - a colisao (corrupcao paralela) - DEMO")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd E b_synth.scd rodando.")
    print()
    glitch = GlitchEngine(verbose=True)
    glitch.load_voice()
    print()
    print("[DEMO] 12 cartas -- a corrupcao sobe e a maquina vai gaguejando...")
    suits = list(SUIT_NAMES.keys())
    for _ in range(12):
        rank = random.choice(RANKS)
        suit = random.choice(suits)
        glitch.corrupt(rank, suit)
        time.sleep(2.5)
    print()
    print("[DEMO] fim. (a corrupcao mora no Python; reinicie pra zerar)")


if __name__ == "__main__":
    main()
