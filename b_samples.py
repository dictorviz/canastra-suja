"""
B_SAMPLES - CANASTRA SUJA (o baralho do mundo)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: este arquivo e o "baralho de paisagens sonoras". Na pasta
samples/ existem varios audios longos (chamados HABITATS -- uma praia, uma
mata, um motor...). Este arquivo embaralha esses audios como se fossem cartas
e, cada vez que uma carta do Buraco e jogada, ele "vira a proxima paisagem":
o som vai derretendo (crossfade) do habitat atual pro proximo. Um lugar de
cada vez.

Importante: assim como o b_glitch, este arquivo NAO faz barulho sozinho. Ele
manda recadinhos (OSC) pro SuperCollider (b_synth.scd), que e quem toca o WAV
de verdade. Aqui a gente so decide QUAL paisagem vem agora e como ela soa
(volume, de que lado do estereo etc.).

FLUXO:
    1. a_synth.scd E b_synth.scd rodando no SC.
    2. MundoPlayer().preload()  -> /mundo/load de cada WAV + monta o baralho.
    3. play_card('Q','C')       -> sorteia o proximo habitat e crossfade.

USO RAPIDO (com SC + os dois .scd rodando):
    python b_samples.py          # atravessa alguns habitats em sequencia
"""

# -- IMPORTS: caixas de ferramentas que vamos usar. (ver secao 5 do guia)
import contextlib  # ajuda a "fechar com seguranca" um arquivo depois de abrir
import glob        # acha arquivos por padrao (ex: todos os "*.wav" da pasta)
import os          # mexer com pastas e caminhos de arquivo
import random      # sorteios (embaralhar, escolher ao acaso)
import time        # medir/esperar tempo
import wave        # ler arquivos .wav (aqui so pra medir quanto tempo cada um dura)
from typing import Dict, List, Optional  # "rotulos" que dizem o tipo das coisas:
# Dict = dicionario, List = lista, Optional = "pode ser aquilo OU nada (None)".
# Eles nao mudam o que o programa faz; so ajudam quem le (e o editor) a entender.

from pythonosc import udp_client  # a ferramenta que manda as mensagens OSC
import b_config  # o painel de ajustes unico (DEBUG, rede OSC)

# =============================================================================
# CONFIG = numeros de ajuste (ver os comentarios; mude aqui se quiser calibrar)
# =============================================================================

DEFAULT_HOST = b_config.HOST  # "este mesmo computador" (vem do painel unico)
DEFAULT_PORT = b_config.PORT  # mesma porta do SC; namespace /mundo/* separado

HERE = os.path.dirname(os.path.abspath(__file__))  # a pasta deste arquivo
SAMPLES_DIR = os.path.join(HERE, "samples")        # a subpasta "samples"

# Habitats com duracao >= LOOP_THRESHOLD loopam (permanece-se neles ate a
# proxima carta). Mais curtos tocam uma vez e somem no crossfade.
LOOP_THRESHOLD = 12.0   # segundos: o "ponto de corte" entre habitat longo e curto
DEFAULT_FADE    = 5.0   # segundos de crossfade entre habitats
DEFAULT_AMP     = 0.22  # volume baixo (fantasmagorico): fica BEM abaixo do synth
DEFAULT_LPF     = 2600  # Hz -- veu de distancia (corta os agudos do habitat)
DEFAULT_REVWASH = 0.45  # quanto de "cauda de reverb" embutir no habitat

# A lista dos valores de carta, EM ORDEM (a posicao importa: A e a 0, K e a ultima).
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
# Tabela de-para: sigla do naipe -> nome por extenso.
SUIT_NAMES = {"C": "Copas", "O": "Ouros", "E": "Espadas", "P": "Paus"}

# Espacializacao placeholder por naipe (estereo). Fase 5 vira octofonia:
# Copas=horario, Ouros=anti, Espadas=salto, Paus=centro.
# Cada naipe ganha um "pan": -1 = tudo na caixa esquerda, +1 = tudo na direita,
# 0 = no meio. (Mais pra frente isso vira som em 8 caixas em volta do publico.)
SUIT_PAN = {"C": -0.25, "O": 0.6, "E": -0.6, "P": 0.25}


# =============================================================================
# O BARALHO DO MUNDO (sorteio sem reposicao, reembaralha ao esgotar)
#
# A ideia: imagine um monte de cartas viradas pra baixo. Voce vai tirando uma
# de cada vez (sem repetir). Quando acaba o monte, embaralha tudo de novo. E
# isso que esta classe faz com os NOMES dos habitats.
# =============================================================================

class WorldDeck:
    """Embaralha as chaves dos habitats; draw() devolve o proximo sem repetir
    ate esgotar, ai reembaralha (evitando emendar a mesma carta na virada)."""

    def __init__(self, keys: List[str], rng: Optional[random.Random] = None):
        self.keys = list(keys)  # guarda a lista completa de nomes (a "fonte")
        # rng = o "sorteador". Se passaram um, usa ele; senao cria um novo. Ter um
        # sorteador proprio (com semente) deixa o embaralho REPETIVEL quando se
        # quer. O "or" aqui le-se: "use rng, mas se ele for None, use random.Random()".
        self.rng = rng or random.Random()
        self._pile: List[str] = []     # o "monte" atual de onde a gente tira; comeca vazio
        self._last: Optional[str] = None  # qual foi o ultimo tirado (pra nao repetir na virada)
        self._reshuffle()  # ja embaralha um monte cheio na montagem

    def _reshuffle(self):
        self._pile = list(self.keys)  # repoe o monte com TODOS os nomes de novo
        self.rng.shuffle(self._pile)  # embaralha o monte (ordem ao acaso)
        # evita repetir a ultima carta logo na virada do baralho:
        # se o proximo a sair (o do fim do monte, ver draw) for igual ao ultimo
        # que ja saiu, troca ele de lugar com o do comeco. A linha "a, b = b, a"
        # e o jeito Python de TROCAR dois valores de lugar de uma vez so.
        if self._last is not None and len(self._pile) > 1 and self._pile[-1] == self._last:
            self._pile[0], self._pile[-1] = self._pile[-1], self._pile[0]

    def draw(self) -> Optional[str]:
        if not self.keys:      # se nem ha nomes (lista vazia)...
            return None        # ...nao da pra tirar nada
        if not self._pile:     # se o monte acabou...
            self._reshuffle()  # ...embaralha um novo
        key = self._pile.pop()  # .pop() TIRA e devolve o ultimo item do monte
        self._last = key        # anota qual foi (pra nao repetir na proxima virada)
        return key              # entrega o nome sorteado


# =============================================================================
# PLAYER (manda OSC pro b_synth.scd)
# =============================================================================

class MundoPlayer:
    """Carrega os habitats no SC e atravessa entre eles a cada carta."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 verbose: bool = b_config.DEBUG, seed: Optional[int] = None):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.client = udp_client.SimpleUDPClient(host, port)  # o "carteiro" OSC
        # Os dois dicionarios abaixo comecam VAZIOS e vao sendo preenchidos no
        # preload(): um guarda "nome do habitat -> caminho do arquivo", o outro
        # "nome do habitat -> quantos segundos ele dura".
        self.paths: Dict[str, str] = {}
        self.durations: Dict[str, float] = {}
        self.deck: Optional[WorldDeck] = None  # o baralho do mundo (criado no preload)
        self._rng = random.Random(seed)  # sorteador proprio. 'seed' (semente) fixa
        # deixa o sorteio REPETIVEL: mesma semente -> mesma sequencia de habitats.
        if verbose:
            print(f"[MUNDO] OSC -> {host}:{port} (namespace /mundo/*)")

    def preload(self) -> Dict[str, str]:
        """Le os WAVs de samples/, manda /mundo/load de cada um e monta o baralho."""
        # acha todos os .wav da pasta samples e poe em ordem alfabetica.
        wavs = sorted(glob.glob(os.path.join(SAMPLES_DIR, "*.wav")))
        if not wavs:  # se nao achou nenhum, avisa e para (sem WAV nao ha mundo).
            raise RuntimeError(
                f"nenhum WAV em {SAMPLES_DIR}. Converta biblioteca/*.mp3 primeiro.")
        for path in wavs:  # pra cada arquivo encontrado...
            # tira pasta e extensao, sobrando so o nome curtinho (a "chave"): '001'
            key = os.path.splitext(os.path.basename(path))[0]  # '001'
            self.paths[key] = path  # guarda no dicionario: nome -> caminho
            # tenta medir a duracao do WAV. "with ... as w" abre o arquivo e
            # garante que ele seja fechado certinho depois. A duracao em segundos
            # e (numero de quadros) dividido por (quadros por segundo).
            try:
                with contextlib.closing(wave.open(path, "rb")) as w:
                    self.durations[key] = w.getnframes() / w.getframerate()
            except Exception:  # se der qualquer erro lendo o arquivo...
                self.durations[key] = 0.0  # ...assume duracao 0 e segue sem quebrar
            # manda o SuperCollider carregar esse WAV na memoria (com o apelido 'key')
            self.client.send_message("/mundo/load", [str(key), str(path)])
        # agora que sabemos todos os nomes, monta o baralho embaralhado com eles.
        self.deck = WorldDeck(list(self.paths.keys()), self._rng)
        if self.verbose:
            total = sum(self.durations.values())  # soma a duracao de todos os habitats
            # ":.0f" formata o numero sem casas decimais. total/60 = em minutos.
            print(f"[MUNDO] {len(self.paths)} habitats carregados "
                  f"({total/60:.0f} min de mundo).")
        time.sleep(0.6)  # Buffer.read e async no SC (da um tempinho pra carregar)
        return self.paths

    def bed(self, key: str, fade: float = DEFAULT_FADE, amp: float = DEFAULT_AMP,
            pan: float = 0.0, lpf: float = DEFAULT_LPF,
            rev_wash: float = DEFAULT_REVWASH):
        """Atravessa pro habitat 'key' (crossfade)."""
        # decide se este habitat deve ficar em loop: 1 (sim) se for longo o
        # bastante, 0 (nao) se for curto. (1/0 funcionam como sim/nao no recado.)
        loop = 1 if self.durations.get(key, 0.0) >= LOOP_THRESHOLD else 0
        # manda o recado /mundo/bed com todos os parametros do crossfade. Os
        # float(...)/int(...) so garantem que cada numero vai no formato certo.
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
        if self.deck is None:  # seguranca: o baralho so existe depois do preload()
            raise RuntimeError("chame preload() antes de play_card().")
        suit = suit.upper()       # naipe em maiuscula
        key = self.deck.draw()    # sorteia o proximo habitat
        if key is None:           # baralho vazio -> nao ha o que tocar
            return None
        # calcula de que lado toca: pega o pan base do naipe e soma uma
        # variacaozinha ao acaso (uniform(-0.15, 0.15)) pra nao ficar mecanico.
        pan = SUIT_PAN.get(suit, 0.0) + self._rng.uniform(-0.15, 0.15)
        # max(-1.0, min(1.0, pan)) "prende" o pan entre -1 e 1 (nunca passa disso).
        self.bed(key, fade=fade, amp=amp, pan=max(-1.0, min(1.0, pan)))
        if self.verbose:
            dur = self.durations.get(key, 0.0)
            loop = "loop" if dur >= LOOP_THRESHOLD else "1x"
            print(f"[MUNDO] {rank}{suit} ({SUIT_NAMES.get(suit, '?')}) "
                  f"-> habitat {key}  ({dur:.0f}s, {loop})")
        return key  # devolve qual habitat foi revelado

    def stop(self, fade: float = DEFAULT_FADE):
        """Encerra o habitat atual (fim da peca)."""
        self.client.send_message("/mundo/stop", [float(fade)])


# =============================================================================
# DEMO (so roda com 'python b_samples.py' -- pra ouvir alguns habitats sozinho)
# =============================================================================

def main():
    print("=" * 60)
    print("B_SAMPLES - o baralho do mundo (habitats) - DEMO")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd E b_synth.scd rodando.")
    print()
    player = MundoPlayer()   # FABRICA o tocador do mundo
    player.preload()         # carrega os WAVs e monta o baralho
    print()
    print("[DEMO] atravessando 5 habitats (8s em cada)...")
    suits = list(SUIT_NAMES.keys())  # ["C","O","E","P"]
    for _ in range(5):               # repete 5 vezes
        rank = random.choice(RANKS)  # sorteia um valor de carta
        suit = random.choice(suits)  # sorteia um naipe
        player.play_card(rank, suit) # atravessa pro proximo habitat
        time.sleep(8.0)              # fica 8s nele pra dar pra ouvir
    print()
    print("[DEMO] encerrando o ultimo habitat...")
    player.stop()
    print("Pra puxar cartas voce mesmo:  python b_teclado.py")


if __name__ == "__main__":
    main()
