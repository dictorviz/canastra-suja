"""
B_BURACO - CANASTRA SUJA: as regras do Buraco (a estrutura do jogo)

Este modulo guarda o que a PERFORMANCE precisa do Buraco -- e NAO e um motor
completo de Buraco. Ele NAO simula maos, jogos baixados, morto, batida nem
pontuacao real (isso acontece na mesa fisica, entre as pessoas). Ele modela:

  - quantos jogadores (2 a 4) e as DUPLAS (no jogo de 4, o parceiro senta
    de frente: J1+J3 contra J2+J4; com 2 ou 3 a contagem e individual);
  - a VEZ -- de quem e a jogada agora e como ela gira (sentido horario);
  - a SEMANTICA das cartas (valor em pontos, curingas) -- dados prontos pra,
    mais pra frente, reger a degradacao por carta.

A carta virada (teclado hoje, webcam/ArUco amanha) so dispara som + glitch;
aqui a gente apenas acompanha de quem e a vez.
"""

# Baralho do Buraco: 2 baralhos de 52 + 2 coringas cada = 108 cartas.
N_BARALHOS = 2
CORINGAS_POR_BARALHO = 2
TOTAL_CARTAS = N_BARALHOS * 52 + N_BARALHOS * CORINGAS_POR_BARALHO  # 108

MIN_JOGADORES = 2
MAX_JOGADORES = 4

# Valor em pontos de cada carta (tabela do Buraco Aberto / Canastra):
#   Curinga (Joker) = 50 ; 2 usado como curinga = 10 ; As = 15 ;
#   do 8 ao K = 10 ; do 3 ao 7 = 5.
# (Ha tabelas alternativas por ai com Joker=20; adotamos a detalhada.)
PONTOS = {
    "A": 15,
    "K": 10, "Q": 10, "J": 10, "10": 10, "9": 10, "8": 10,
    "7": 5, "6": 5, "5": 5, "4": 5, "3": 5,
    "2": 10,          # o "2" e curinga (curinguinha)
    "JOKER": 50,      # o curingao
}

# Cartas especiais (curingas).
CURINGA_MAIOR = "JOKER"   # curingao
CURINGA_MENOR = "2"       # curinguinha (qualquer naipe)

# Os 4 tipos de canastra -- so referencia/poetica (o nome da peca mora aqui:
# CANASTRA SUJA = canastra com curinga). (descricao, pontos)
CANASTRAS = {
    "limpa":      ("sem curinga, 7+ cartas em sequencia do mesmo naipe", 200),
    "suja":       ("com curinga ou curinguinha",                         100),
    "quinhentos": ("As a 2, sem curinga",                                500),
    "real":       ("As a As, sem curinga",                              1000),
}


def pontos_da_carta(rank: str) -> int:
    """Valor em pontos de uma carta (rank 'A'..'K', '2'..'10' ou 'JOKER')."""
    return PONTOS.get(str(rank).upper(), 0)


def eh_curinga(rank: str) -> bool:
    """True se a carta e curingao (Joker) ou curinguinha (2)."""
    r = str(rank).upper()
    return r == CURINGA_MAIOR or r == CURINGA_MENOR


class Mesa:
    """A mesa de Buraco: jogadores, duplas e de quem e a vez.

    Nao guarda maos nem pontos -- so a ESTRUTURA de turnos da performance.
    A vez gira em sentido horario (J1 -> J2 -> ... -> J1).
    """

    def __init__(self, num_jogadores: int, nomes=None):
        n = int(num_jogadores)
        if not (MIN_JOGADORES <= n <= MAX_JOGADORES):
            raise ValueError(
                f"Buraco aqui e de {MIN_JOGADORES} a {MAX_JOGADORES} jogadores "
                f"(pedido: {n}).")
        self.n = n
        self.jogadores = list(nomes) if nomes else [f"Jogador {i+1}" for i in range(n)]
        self.vez = 0  # indice do jogador da vez
        # Duplas so no jogo de 4 (parceiro de frente: J1+J3 x J2+J4).
        # Com 2 ou 3 jogadores: contagem individual (sem duplas).
        self.duplas = [(0, 2), (1, 3)] if n == 4 else []

    def atual_idx(self) -> int:
        return self.vez

    def atual_nome(self) -> str:
        return self.jogadores[self.vez]

    def dupla_de(self, idx: int):
        """Letra da dupla ('A'/'B') de um jogador, ou None se individual."""
        for d, (a, b) in enumerate(self.duplas):
            if idx in (a, b):
                return "AB"[d]
        return None

    def parceiro_de(self, idx: int):
        """Indice do parceiro (jogo de 4), ou None."""
        for a, b in self.duplas:
            if idx == a:
                return b
            if idx == b:
                return a
        return None

    def label(self) -> str:
        """Rotulo da vez, ex: 'Jogador 1' ou 'Jogador 1 (Dupla A)'."""
        dup = self.dupla_de(self.vez)
        return f"{self.atual_nome()} (Dupla {dup})" if dup else self.atual_nome()

    def proximo(self) -> int:
        """Passa a vez pro proximo (horario). Retorna o novo indice."""
        self.vez = (self.vez + 1) % self.n
        return self.vez

    def resumo(self) -> str:
        if self.duplas:
            a = " + ".join(self.jogadores[i] for i in self.duplas[0])
            b = " + ".join(self.jogadores[i] for i in self.duplas[1])
            return f"{self.n} jogadores, 2 duplas:  [A] {a}   x   [B] {b}"
        return (f"{self.n} jogadores (contagem individual): "
                + ", ".join(self.jogadores))


def _demo():
    print("B_BURACO - demo das regras (estrutura de turnos)")
    print(f"Baralho: {TOTAL_CARTAS} cartas ({N_BARALHOS} baralhos + coringas).")
    print(f"Curingas: {CURINGA_MAIOR} (50pts) e o {CURINGA_MENOR} (curinguinha, 10pts).")
    for n in (2, 4):
        print()
        mesa = Mesa(n)
        print(mesa.resumo())
        print("  giro das vezes: ", end="")
        for _ in range(n + 1):
            print(mesa.label(), end="  ->  ")
            mesa.proximo()
        print("...")


if __name__ == "__main__":
    _demo()
