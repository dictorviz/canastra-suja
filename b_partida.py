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
