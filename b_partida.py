"""
B_PARTIDA - CANASTRA SUJA: o motor da partida (mesa + mundo + degradacao)

Junta os tres pedacos da camada B num so objeto:
  - Mesa        (b_buraco) - de quem e a vez, duplas, giro dos turnos;
  - MundoPlayer (b_samples) - atravessa habitats a cada carta;
  - GlitchEngine(b_glitch)  - soma a degradacao a cada carta.

Cada carta jogada atravessa um habitat, soma degradacao e PASSA A VEZ. E
reutilizavel pelas duas fontes de carta: o teclado (b_teclado) e a webcam +
ArUco (b_aruco) -- as duas chamam os mesmos metodos, so muda quem dispara.
"""

import random
from typing import Optional, Tuple

from b_samples import MundoPlayer, RANKS, SUIT_NAMES
from b_glitch import GlitchEngine, SUIT_GLITCH, GLITCH_LABEL
from b_buraco import Mesa
from a_cama import CamaViva


class Partida:
    """O estado vivo de uma partida: mesa + cama (vibrafone ao vivo) + mundo +
    degradacao. Cada carta TOCA a cama, atravessa um habitat e suja o som."""

    def __init__(self, num_jogadores: int, seed: Optional[int] = None,
                 verbose: bool = True):
        self.mesa = Mesa(num_jogadores)
        self.cama = CamaViva(verbose=verbose)     # camada A: vibrafone tocado pelas cartas
        self.player = MundoPlayer(verbose=verbose, seed=seed)
        self.glitch = GlitchEngine(verbose=verbose)
        self.suits = list(SUIT_NAMES.keys())
        self._rng = random.Random(seed)
        self.ultima: Optional[Tuple[str, str]] = None  # (rank, suit) ultima carta

    def preload(self):
        """Carrega os habitats no SC (chame uma vez antes de jogar)."""
        self.player.preload()

    # --- jogadas (todas passam a vez) -----------------------------------

    def jogar(self, rank: str, suit: str, kick: Optional[float] = None):
        """Joga uma carta: toca a cama + atravessa um habitat + degradacao + passa a vez."""
        suit = suit.upper()
        self.cama.tocar_carta(rank, suit)
        self.player.play_card(rank, suit)
        self.glitch.corrupt(rank, suit, kick=kick)
        self.ultima = (rank, suit)
        self.mesa.proximo()

    def jogar_carta(self, card: Tuple[str, Optional[str]]):
        """Despacha uma carta (rank, suit) ou ('JOKER', None). Conveniencia pro
        ArUco, que ja trabalha com tuplas vindas de id_to_card."""
        rank, suit = card
        if suit is None:
            self.jogar_joker()
        else:
            self.jogar(rank, suit)

    def jogar_rajada(self, cartas):
        """Varias cartas baixadas JUNTAS (ex: uma canastra inteira de uma vez).

        A cama BADALA cada carta (cascata ressonante -- e desejavel, o vibrafone
        empilha bonito). Mas a camada B CONSOLIDA: um unico crossfade de habitat
        e um unico passo de degradacao (o golpe da carta mais forte da rajada),
        senao 6 cartas atropelariam o mundo com 6 travessias simultaneas. A vez
        passa UMA vez -- baixar uma canastra e uma jogada so."""
        cartas = [c for c in cartas if c is not None]
        if not cartas:
            return
        if len(cartas) == 1:
            self.jogar_carta(cartas[0])
            return

        # 1. cama: cascata -- toda carta soa na hora
        for rank, suit in cartas:
            if suit is None:
                self.cama.tocar_joker()
            else:
                self.cama.tocar_carta(rank, suit)

        # 2. camada B consolidada: a carta de golpe mais forte rege a travessia
        def _kick(c):
            return 1.0 if c[1] is None else self.glitch._kick_for_rank(c[0])
        rank, suit = max(cartas, key=_kick)
        if suit is None:                       # rajada liderada por um coringa
            suit = self._rng.choice(self.suits)
            kick = 1.0
        else:
            kick = self.glitch._kick_for_rank(rank)
        self.player.play_card(rank, suit)      # UM habitat atravessa
        self.glitch.corrupt(rank, suit, kick=kick)  # UM passo de degradacao
        self.ultima = (rank, suit)

        # 3. a vez passa uma unica vez
        self.mesa.proximo()

    def jogar_joker(self):
        """Curingao: acento na cama + naipe sorteado (espacializacao) + forca maxima."""
        suit = self._rng.choice(self.suits)
        self.cama.tocar_joker()
        self.player.play_card("JOKER", suit)
        self.glitch.corrupt("JOKER", suit, kick=1.0)
        self.ultima = ("JOKER", suit)
        self.mesa.proximo()

    def jogar_aleatoria(self):
        """Uma carta qualquer (simula a virada sem digitar)."""
        self.jogar(self._rng.choice(RANKS), self._rng.choice(self.suits))

    # --- controles que NAO passam a vez ---------------------------------

    def silencio(self):
        """Encerra o habitat atual (silencio), sem consumir a vez."""
        self.player.stop()

    def reset(self):
        """Nova mao: zera a degradacao acumulada e volta o painel da cama ao centro."""
        self.glitch.reset()
        self.cama.reset()

    def encerrar(self):
        """Fim da partida: encerra o habitat."""
        self.player.stop()

    # --- estado pra UI (terminal ou projecao) ---------------------------

    @property
    def vez_label(self) -> str:
        return self.mesa.label()

    @property
    def corrupcao(self) -> float:
        """Nivel global de degradacao 0..1."""
        return self.glitch.level

    def ultima_str(self) -> str:
        if not self.ultima:
            return "-"
        rank, suit = self.ultima
        glitch = GLITCH_LABEL.get(SUIT_GLITCH.get(suit, ""), "?")
        return f"{rank}{suit} ({glitch})"
