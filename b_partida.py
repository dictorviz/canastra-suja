"""
B_PARTIDA - CANASTRA SUJA: o motor da partida (mesa + mundo + degradacao)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: este arquivo e o MAESTRO. Sozinho ele nao faz quase nada -- ele
junta as quatro pecas da peca num objeto so e, quando uma carta cai, manda
todas tocarem juntas, na ordem certa. As quatro pecas sao:

  - Mesa        (b_buraco) - de quem e a vez, duplas, giro dos turnos;
  - CamaViva    (a_cama)   - o vibrafone ao vivo (a badalada da carta);
  - MundoPlayer (b_samples)- atravessa habitats a cada carta;
  - GlitchEngine(b_glitch) - soma a degradacao (a sujeira) a cada carta.

Cada carta jogada: toca a cama + atravessa um habitat + soma degradacao +
PASSA A VEZ. Como tudo esta reunido aqui, tanto o teclado (b_teclado) quanto a
webcam (b_aruco) so precisam chamar os metodos deste maestro -- nenhum dos dois
precisa saber dos detalhes de cama/mundo/glitch.
"""

import random
from typing import Optional, Tuple  # Tuple = "uma tupla", o par fixo (rank, suit)

# importa as pecas, cada uma do seu arquivo:
from b_samples import MundoPlayer, RANKS, SUIT_NAMES
from b_glitch import GlitchEngine, TereminBridge, SUIT_GLITCH, GLITCH_LABEL
from b_buraco import Mesa
from a_cama import CamaViva
import b_config  # o painel de ajustes unico (DEBUG)


class Partida:
    """O estado vivo de uma partida: mesa + cama (vibrafone ao vivo) + mundo +
    degradacao. Cada carta TOCA a cama, atravessa um habitat e suja o som."""

    def __init__(self, num_jogadores: int, seed: Optional[int] = None,
                 verbose: bool = b_config.DEBUG):
        # na montagem, FABRICA as pecas e guarda cada uma dentro de si.
        self.mesa = Mesa(num_jogadores)           # quem joga e de quem e a vez
        self.cama = CamaViva(verbose=verbose)     # camada A: vibrafone tocado pelas cartas
        self.player = MundoPlayer(verbose=verbose, seed=seed)  # os habitats
        self.glitch = GlitchEngine(verbose=verbose)            # a sujeira (discreta, por carta)
        # a ponte do fluxo CONTINUO (theremin): a pose dos marcadores ao vivo. So
        # o b_aruco a alimenta (partida.teremin.update/release); sem webcam fica
        # parada, sem custo. Mora aqui pra reset()/encerrar() soltarem as vozes.
        self.teremin = TereminBridge(verbose=verbose)
        self.suits = list(SUIT_NAMES.keys())      # ["C","O","E","P"], usado em sorteios
        self._rng = random.Random(seed)           # sorteador proprio (semente = repetivel)
        self.ultima: Optional[Tuple[str, str]] = None  # (rank, suit) ultima carta jogada

    def preload(self):
        """Carrega os habitats no SC (chame uma vez antes de jogar)."""
        self.player.preload()

    # --- jogadas (todas passam a vez) -----------------------------------

    def jogar(self, rank: str, suit: str, kick: Optional[float] = None):
        """Joga uma carta: toca a cama + atravessa um habitat + degradacao + passa a vez."""
        suit = suit.upper()
        # AQUI esta o coracao da peca: as camadas reagem a MESMA carta, em ordem.
        # (Vibrafone REMOVIDO -- pedido 4: nao casava com o resto. A cama segue
        #  instanciada so pra reset()/painel, mas nao badala mais a cada carta.)
        self.player.play_card(rank, suit)        # 1) o mundo atravessa de habitat
        self.glitch.corrupt(rank, suit, kick=kick)  # 2) a sujeira sobe
        self.ultima = (rank, suit)               # lembra qual foi a ultima carta
        self.mesa.proximo()                      # 4) passa a vez pro proximo jogador

    def jogar_carta(self, card: Tuple[str, Optional[str]]):
        """Despacha uma carta (rank, suit) ou ('JOKER', None). Conveniencia pro
        ArUco, que ja trabalha com tuplas vindas de id_to_card."""
        rank, suit = card        # desmonta o par em duas caixas
        if suit is None:         # se nao tem naipe, e o curingao
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
        # filtra: fica so com as cartas que existem (joga fora os None).
        # "[c for c in cartas if c is not None]" le-se "pegue cada c da lista,
        # mas so se c nao for None".
        cartas = [c for c in cartas if c is not None]
        if not cartas:           # lista vazia -> nada a fazer
            return
        if len(cartas) == 1:     # se sobrou so uma, trata como jogada normal
            self.jogar_carta(cartas[0])
            return

        # 1. (vibrafone REMOVIDO -- pedido 4: a rajada nao badala mais a cama.)

        # 2. camada B consolidada: a carta de golpe mais forte rege a travessia.
        # Aqui criamos uma mini-funcao DENTRO do metodo (so usada aqui embaixo):
        # ela diz a "forca" de uma carta -- coringa vale 1.0, senao usa a forca
        # pela altura (As leve ... Rei pesado).
        def _kick(c):
            return 1.0 if c[1] is None else self.glitch._kick_for_rank(c[0])
        # max(cartas, key=_kick): de toda a rajada, pega a carta de MAIOR forca.
        # "key=_kick" diz ao max() como medir cada carta (usando a funcao acima).
        rank, suit = max(cartas, key=_kick)
        if suit is None:                       # rajada liderada por um coringa
            suit = self._rng.choice(self.suits)  # sorteia um naipe so pra espacializar
            kick = 1.0
        else:
            kick = self.glitch._kick_for_rank(rank)
        self.player.play_card(rank, suit)      # UM habitat atravessa
        self.glitch.corrupt(rank, suit, kick=kick)  # UM passo de degradacao
        self.ultima = (rank, suit)

        # 3. a vez passa uma unica vez
        self.mesa.proximo()

    def jogar_joker(self):
        """Curingao: naipe sorteado (espacializacao) + forca maxima de sujeira."""
        suit = self._rng.choice(self.suits)    # o coringa nao tem naipe -> sorteia um
        # (vibrafone REMOVIDO -- pedido 4: nem o coringa badala mais a cama.)
        self.player.play_card("JOKER", suit)   # atravessa habitat
        self.glitch.corrupt("JOKER", suit, kick=1.0)  # sujeira no maximo
        self.ultima = ("JOKER", suit)
        self.mesa.proximo()

    def jogar_aleatoria(self):
        """Uma carta qualquer (simula a virada sem digitar)."""
        # sorteia um valor e um naipe e joga normalmente.
        self.jogar(self._rng.choice(RANKS), self._rng.choice(self.suits))

    # --- controles que NAO passam a vez ---------------------------------

    def silencio(self):
        """Encerra o habitat atual (silencio), sem consumir a vez."""
        self.player.stop()

    def reset(self):
        """Nova mao: zera a degradacao acumulada e volta o painel da cama ao centro."""
        self.glitch.reset()        # sujeira de volta a zero
        self.cama.reset()          # painel do vibrafone de volta ao centro
        self.teremin.release_all() # solta as vozes continuas abertas (cauda)

    def encerrar(self):
        """Fim da partida: encerra o habitat e solta as vozes do theremin."""
        self.teremin.release_all()  # nenhuma voz continua presa tocando
        self.player.stop()

    # --- estado pra UI (terminal ou projecao) ---------------------------
    #
    # "@property" e um truquezinho: deixa a gente ESCREVER um metodo (uma funcao)
    # mas USAR ele como se fosse so um valor guardado -- sem os parenteses.
    # Ex: a gente escreve "partida.vez_label" (e nao "partida.vez_label()").
    # Serve pra perguntas simples de estado, que a tela (HUD) consulta o tempo todo.

    @property
    def vez_label(self) -> str:
        return self.mesa.label()  # de quem e a vez agora (texto pronto)

    @property
    def corrupcao(self) -> float:
        """Nivel global de degradacao 0..1."""
        return self.glitch.level  # o quanto ja sujou (0 = limpo, perto de 1 = destruido)

    def ultima_str(self) -> str:
        # monta um textinho da ultima carta + o tipo de sujeira que ela causou,
        # pra mostrar na tela. Ex: "QC (desafina)".
        if not self.ultima:      # se ainda nao jogaram nenhuma carta...
            return "-"
        rank, suit = self.ultima
        # descobre o "sabor" do glitch desse naipe e traduz pro nome bonito.
        glitch = GLITCH_LABEL.get(SUIT_GLITCH.get(suit, ""), "?")
        return f"{rank}{suit} ({glitch})"
