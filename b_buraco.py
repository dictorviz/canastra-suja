"""
B_BURACO - CANASTRA SUJA: as regras do Buraco (a estrutura do jogo)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md -- ele ensina do zero
*** o que e variavel, lista, dicionario, funcao e classe. Aqui a gente usa
*** tudo isso de um jeito bem mansinho, e este e o arquivo MAIS SIMPLES do
*** projeto, otimo pra comecar.

O que este arquivo faz, em uma frase: ele guarda "as regrinhas do Buraco que
a peca precisa saber" -- tipo quantos jogadores tem, de quem e a vez agora,
quanto vale cada carta em pontos. Só isso. Ele NAO faz som, NAO mexe na
camera, NAO joga Buraco de verdade. Pense nele como o "caderninho de regras"
em cima da mesa.

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

# -- Estas primeiras linhas criam "caixas com nome" (variaveis) que valem pro
#    arquivo inteiro. Ficam em MAIUSCULA por convencao: e o jeito de avisar
#    "isto e um numero fixo, de ajuste, nao muda enquanto o programa roda".

# Baralho do Buraco: 2 baralhos de 52 + 2 coringas cada = 108 cartas.
N_BARALHOS = 2              # quantos baralhos o Buraco usa (sao dois)
CORINGAS_POR_BARALHO = 2    # cada baralho tem 2 coringas (o JOKER e o curinguinha)
# A linha abaixo e uma CONTA: 2 baralhos x 52 cartas + 2 baralhos x 2 coringas.
# O computador resolve a conta e guarda o resultado (108) na caixa TOTAL_CARTAS.
TOTAL_CARTAS = N_BARALHOS * 52 + N_BARALHOS * CORINGAS_POR_BARALHO  # 108

MIN_JOGADORES = 2   # menos que isso nao da pra jogar
MAX_JOGADORES = 4   # mais que isso a gente nao trata aqui

# Valor em pontos de cada carta (tabela do Buraco Aberto / Canastra):
#   Curinga (Joker) = 50 ; 2 usado como curinga = 10 ; As = 15 ;
#   do 8 ao K = 10 ; do 3 ao 7 = 5.
# (Ha tabelas alternativas por ai com Joker=20; adotamos a detalhada.)
#
# Isto e um DICIONARIO (tabela de-para). A chave (esquerda do ":") e o nome da
# carta como TEXTO; o valor (direita) e quantos pontos ela vale. Pra consultar:
# PONTOS["A"] devolve 15.
PONTOS = {
    "A": 15,
    "K": 10, "Q": 10, "J": 10, "10": 10, "9": 10, "8": 10,
    "7": 5, "6": 5, "5": 5, "4": 5, "3": 5,
    "2": 10,          # o "2" e curinga (curinguinha)
    "JOKER": 50,      # o curingao
}

# Cartas especiais (curingas). Guardamos o nome delas em caixas com nome bonito
# pra o resto do codigo poder dizer "CURINGA_MAIOR" em vez de decorar o texto.
CURINGA_MAIOR = "JOKER"   # curingao
CURINGA_MENOR = "2"       # curinguinha (qualquer naipe)

# Os 4 tipos de canastra -- so referencia/poetica (o nome da peca mora aqui:
# CANASTRA SUJA = canastra com curinga).
# Repare que aqui o VALOR de cada chave e um PAR entre parenteses (descricao,
# pontos): "(texto, numero)". Esse par junto chama-se "tupla" -- e como uma
# lista, mas fixa. Ex: CANASTRAS["real"] devolve o par ("As a As...", 1000).
CANASTRAS = {
    "limpa":      ("sem curinga, 7+ cartas em sequencia do mesmo naipe", 200),
    "suja":       ("com curinga ou curinguinha",                         100),
    "quinhentos": ("As a 2, sem curinga",                                500),
    "real":       ("As a As, sem curinga",                              1000),
}


# -- Agora duas FUNCOES (truques com nome). A palavra "def" cria a funcao; o que
#    vem entre parenteses sao os ingredientes; "return" e o que ela devolve.

def pontos_da_carta(rank: str) -> int:
    """Valor em pontos de uma carta (rank 'A'..'K', '2'..'10' ou 'JOKER')."""
    # str(rank) garante que o ingrediente vire texto; .upper() poe em MAIUSCULA
    # ("joker" -> "JOKER"). Depois PONTOS.get(chave, 0) procura essa carta no
    # dicionario: se achar, devolve os pontos; se NAO achar, devolve 0 (o "0"
    # depois da virgula e o "valor padrao pra quando nao existe"). Usar .get
    # evita o programa quebrar com uma carta desconhecida.
    return PONTOS.get(str(rank).upper(), 0)


def eh_curinga(rank: str) -> bool:
    """True se a carta e curingao (Joker) ou curinguinha (2)."""
    # guarda a carta ja em maiuscula numa caixa curtinha 'r' pra reusar embaixo.
    r = str(rank).upper()
    # "==" pergunta "sao iguais?" e devolve True/False. "or" significa "ou":
    # a resposta e True se for o curingao OU o curinguinha. Devolve esse True/False.
    return r == CURINGA_MAIOR or r == CURINGA_MENOR


# -- E agora uma CLASSE: a "planta" de uma Mesa de Buraco. Dela a gente fabrica
#    objetos-mesa (um por partida). Veja a secao 4 do PYTHON_DO_ZERO.md.

class Mesa:
    """A mesa de Buraco: jogadores, duplas e de quem e a vez.

    Nao guarda maos nem pontos -- so a ESTRUTURA de turnos da performance.
    A vez gira em sentido horario (J1 -> J2 -> ... -> J1).
    """

    # __init__ = a "montagem" da mesa: roda automatico quando a mesa e criada.
    # Recebe quantos jogadores e, se quiser, uma lista de nomes ("nomes=None"
    # quer dizer "se ninguem passar nomes, deixa vazio que eu invento").
    def __init__(self, num_jogadores: int, nomes=None):
        n = int(num_jogadores)   # garante que o numero de jogadores seja inteiro
        # Verificacao de seguranca: SE n NAO estiver entre 2 e 4, o programa
        # "levanta um erro" (raise) com uma mensagem clara e para. E melhor
        # avisar na hora do que jogar errado silenciosamente.
        if not (MIN_JOGADORES <= n <= MAX_JOGADORES):
            raise ValueError(
                f"Buraco aqui e de {MIN_JOGADORES} a {MAX_JOGADORES} jogadores "
                f"(pedido: {n}).")
        self.n = n   # guarda o numero de jogadores DENTRO da mesa (self = "eu, a mesa")
        # A linha abaixo decide os nomes dos jogadores. Leia o "se/senao" assim:
        #   - SE 'nomes' foi passado, usa ele (vira uma lista);
        #   - SENAO, monta nomes automaticos com uma "list comprehension":
        #     [f"Jogador {i+1}" for i in range(n)] le-se "pra cada i de 0 ate n-1,
        #     crie o texto 'Jogador i+1'". Com n=3 isso vira
        #     ["Jogador 1", "Jogador 2", "Jogador 3"].
        self.jogadores = list(nomes) if nomes else [f"Jogador {i+1}" for i in range(n)]
        self.vez = 0  # indice do jogador da vez (0 = o primeiro da lista)
        # Duplas so no jogo de 4 (parceiro de frente: J1+J3 x J2+J4).
        # Com 2 ou 3 jogadores: contagem individual (sem duplas).
        # Cada dupla e um par (tupla) de POSICOES: (0,2) = 1o e 3o jogador.
        # Se nao for jogo de 4, a lista de duplas fica vazia [].
        self.duplas = [(0, 2), (1, 3)] if n == 4 else []

    def atual_idx(self) -> int:
        # devolve a POSICAO (numero) do jogador da vez. So entrega o self.vez.
        return self.vez

    def atual_nome(self) -> str:
        # devolve o NOME do jogador da vez: vai na lista de jogadores e pega o
        # que esta na posicao self.vez.
        return self.jogadores[self.vez]

    def dupla_de(self, idx: int):
        """Letra da dupla ('A'/'B') de um jogador, ou None se individual."""
        # enumerate(self.duplas) percorre a lista de duplas dando, pra cada uma,
        # um numerinho 'd' (0, 1) MAIS o conteudo. E "(a, b)" desmonta o par da
        # dupla em duas caixas: a = primeira posicao, b = segunda.
        for d, (a, b) in enumerate(self.duplas):
            if idx in (a, b):   # se o jogador procurado esta nesta dupla...
                return "AB"[d]  # ..."AB"[0] da "A", "AB"[1] da "B" (pega a letra)
        return None  # nao achou em dupla nenhuma -> e contagem individual

    def parceiro_de(self, idx: int):
        """Indice do parceiro (jogo de 4), ou None."""
        # procura, entre as duplas, aquela onde o jogador esta, e devolve o OUTRO.
        for a, b in self.duplas:
            if idx == a:   # se ele e o primeiro do par...
                return b   # ...o parceiro e o segundo
            if idx == b:   # e vice-versa
                return a
        return None  # sem parceiro (jogo de 2 ou 3)

    def label(self) -> str:
        """Rotulo da vez, ex: 'Jogador 1' ou 'Jogador 1 (Dupla A)'."""
        dup = self.dupla_de(self.vez)  # descobre a letra da dupla do jogador da vez
        # SE tem dupla, escreve "Nome (Dupla X)"; SENAO so o nome. Esse "A if C
        # else B" e um if/else em uma linha so: "use A caso C seja verdade, senao B".
        return f"{self.atual_nome()} (Dupla {dup})" if dup else self.atual_nome()

    def proximo(self) -> int:
        """Passa a vez pro proximo (horario). Retorna o novo indice."""
        # (self.vez + 1) % self.n: soma 1 e usa o "%" (resto da divisao) pra dar
        # a volta. Ex com 4 jogadores: 0,1,2,3 e depois 4 % 4 = 0 -> volta pro
        # primeiro. E o truque classico pra "girar em circulo" sem estourar a lista.
        self.vez = (self.vez + 1) % self.n
        return self.vez

    def resumo(self) -> str:
        # devolve um texto-resumo da mesa, pronto pra mostrar na tela.
        if self.duplas:  # se tem duplas (jogo de 4)...
            # " + ".join(lista) cola os itens de uma lista num texto so, com
            # " + " no meio. Aqui monta "Jogador 1 + Jogador 3", por exemplo.
            a = " + ".join(self.jogadores[i] for i in self.duplas[0])
            b = " + ".join(self.jogadores[i] for i in self.duplas[1])
            return f"{self.n} jogadores, 2 duplas:  [A] {a}   x   [B] {b}"
        # senao (2 ou 3 jogadores): lista os nomes separados por virgula.
        return (f"{self.n} jogadores (contagem individual): "
                + ", ".join(self.jogadores))


# -- DEMO: so roda se voce executar este arquivo direto (python b_buraco.py).
#    Serve pra ver as regras funcionando no terminal, sem som nenhum.

def _demo():
    print("B_BURACO - demo das regras (estrutura de turnos)")
    print(f"Baralho: {TOTAL_CARTAS} cartas ({N_BARALHOS} baralhos + coringas).")
    print(f"Curingas: {CURINGA_MAIOR} (50pts) e o {CURINGA_MENOR} (curinguinha, 10pts).")
    for n in (2, 4):           # faz a demo pra uma mesa de 2 e outra de 4 jogadores
        print()
        mesa = Mesa(n)         # FABRICA uma mesa com n jogadores (roda o __init__)
        print(mesa.resumo())   # mostra o resumo dela
        print("  giro das vezes: ", end="")  # 'end=""' = nao pula linha no fim do print
        for _ in range(n + 1):              # gira a vez algumas vezes pra demonstrar
            print(mesa.label(), end="  ->  ")  # mostra quem e a vez, sem pular linha
            mesa.proximo()                   # passa pro proximo jogador
        print("...")           # fecha a linha


# "Se rodaram este arquivo direto, mostre a demo." (Se foi so importado, nao.)
if __name__ == "__main__":
    _demo()
