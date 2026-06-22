"""
B_GLITCH - CANASTRA SUJA: a DEGRADACAO (a carta suja o som)

====================================================================
LEIA ISTO PRIMEIRO (explicacao pra quem NUNCA viu codigo)
====================================================================
*** Se voce nunca programou: abra antes o arquivo PYTHON_DO_ZERO.md. Ele
*** explica do zero o que e variavel, lista, dicionario, funcao, classe etc.
*** Aqui embaixo a gente repete o essencial, mas o guia ensina com calma.

Pensa neste arquivo como o "controlador de sujeira" da peca. Conforme as
cartas vao caindo na mesa, o som do mundo vai ficando cada vez mais sujo,
distorcido, quebrado -- como uma maquina velha que vai pifando aos poucos.
Este arquivo NAO produz som nenhum sozinho. Ele so faz UMA coisa: a cada
carta, ele calcula "o quanto sujar" e manda um recadinho pelo correio pro
programa que de fato faz barulho (o SuperCollider, no arquivo b_synth.scd).

Esse "correio" se chama OSC: e so um jeito de um programa mandar mensagens
curtas pra outro programa pela rede (mesmo que os dois estejam no mesmo PC).
Cada mensagem tem um "endereco" (tipo /mundo/glitch) e uns numeros junto.

Tres ideias guiam tudo aqui:
  - o NAIPE da carta escolhe o SABOR da sujeira (que tipo de defeito):
        Copas    -> DESAFINA     a altura escorrega/afunda
        Ouros    -> CONGELA      um pedacinho trava e fica repetindo
        Espadas  -> FRAGMENTA    o som vira cacos/estilhacos
        Paus     -> SATURA       o som queima/distorce
  - o VALOR da carta (A=As, 2, 3 ... ate K=Rei) escolhe a FORCA do golpe
    daquela carta (As bate leve, Rei bate pesado);
  - o ACUMULO (quantas cartas ja cairam no total) escolhe a PROFUNDIDADE:
    no comeco a maquina so gagueja de leve; perto do fim ela quase desmorona.

>>> Espadas (resolvido): no projeto antigo (A Cartomante) a espada cortava a
>>> VOZ do Perec (arquivada). Sem voz, ela agora estilhaca o PROPRIO habitat
>>> que esta tocando -- TGrains sobre ~mundoCurrentBuf no b_synth.scd. Nao
>>> depende mais do tts_cache (load_voice virou opcional/legado).

A degradacao age em PARALELO: sao vozes aditivas em b_synth.scd (SynthDefs
glitch*) que SOAM como a maquina se desfazendo. Sem b_synth.scd carregado,
o som do mundo (camada B) toca limpo.

USO RAPIDO (com SC + a_synth.scd E b_synth.scd rodando):
    python b_glitch.py        # simula cartas e ouve a corrupcao crescer
"""

# ---------------------------------------------------------------------------
# IMPORTS = "pegar ferramentas prontas que ja existem e usar aqui".
# Em vez de reinventar a roda, a gente importa caixas de ferramentas (chamadas
# "modulos") que vem com o Python ou que instalamos. Cada linha abaixo traz uma.
# ---------------------------------------------------------------------------
import glob   # acha arquivos por um padrao (ex: "todos os .wav desta pasta")
import math   # contas de matematica (aqui a gente usa a funcao exponencial)
import os     # mexer com pastas/caminhos de arquivo do computador
import random # sortear coisas ao acaso (embaralhar, escolher uma carta)
import time   # ver as horas e medir o tempo (pra fazer o "soco" sumir devagar)
from typing import Optional  # so um "rotulo" que ajuda a documentar o codigo
                             # (Optional[float] = "pode ser um numero OU nada")

# Aqui pegamos uma ferramenta de FORA do Python (instalada com pip): a "udp_client"
# do pacote pythonosc. E ela que sabe mandar as mensagens OSC pela rede.
from pythonosc import udp_client

# E aqui pegamos coisas de OUTRO arquivo NOSSO, o b_samples.py:
#   RANKS      = a lista dos valores das cartas, em ordem (A, 2, 3, ... K)
#   SUIT_NAMES = uma tabela que traduz a sigla do naipe ("C") pro nome ("Copas")
from b_samples import RANKS, SUIT_NAMES
# o painel de ajustes unico (DEBUG, rede OSC, taxa do fluxo continuo).
import b_config

# =============================================================================
# CONFIG = os "numeros que dao pra ajustar". Ficam no topo, com nome em MAIUSCULA,
# pra ser facil achar e mudar sem ter que cacar no meio do codigo.
# =============================================================================

# vem do painel unico b_config (mesma rede pra peca inteira). "127.0.0.1" quer
# dizer "este mesmo computador"; a porta 57120 e onde o SuperCollider escuta (as
# camadas A e B usam a MESMA porta, mas enderecos diferentes -- /baralho/* e
# /mundo/* -- entao nao se atrapalham).
DEFAULT_HOST = b_config.HOST
DEFAULT_PORT = b_config.PORT

# os.path.abspath(__file__) = o caminho completo deste proprio arquivo.
# os.path.dirname(...)        = sobe um nivel e pega so a PASTA onde ele esta.
# Resultado: HERE = a pasta do projeto, sem a gente precisar digitar na mao.
HERE = os.path.dirname(os.path.abspath(__file__))
# "junta" a pasta do projeto com "tts_cache" pra formar o caminho dessa subpasta
# (do jeito certo pro sistema, com / ou \ conforme Windows/Linux).
TTS_CACHE_DIR = os.path.join(HERE, "tts_cache")

# Um DICIONARIO ({...}) e uma tabela de-para: voce da uma CHAVE (a esquerda do :)
# e recebe um VALOR (a direita). Aqui: dado o naipe, qual o sabor da sujeira.
SUIT_GLITCH = {
    "C": "detune",    # Copas   -> desafina
    "O": "freeze",    # Ouros   -> congela
    "E": "shards",    # Espadas -> fragmenta
    "P": "saturate",  # Paus    -> satura
}
# Outra tabela de-para, so pra MOSTRAR na tela em portugues bonito o nome do
# defeito (o codigo la em cima usa "detune"; aqui vira "desafina" pra leitura).
GLITCH_LABEL = {
    "detune": "desafina", "freeze": "congela",
    "shards": "fragmenta", "saturate": "satura",
}

# Fracao da DISTANCIA que falta pro teto que cada carta fecha (curva assintotica:
# ver corrupt()). A degradacao sobe rapido no comeco e desacelera perto do fim,
# mas NUNCA chega em 1.0 -- sempre sobra pra onde piorar, sem plato, qualquer que
# seja o tamanho da mao (uma mao de Buraco varia muito de carta a carta).
# Passo BAIXO de proposito: o arco e longo, documental por boa parte da mao
# (~50% so la pela 45a carta). Calibre no olho/ouvido tocando de verdade.
DEFAULT_STEP = 0.015
DEFAULT_WORDS = 16     # quantas palavras do Perec a espada tem pra cortar

# Decaimento do "soco" visual de cada carta (segundos): a operacao do naipe
# acende na projecao quando a carta cai e some em ~VID_KICK_TAU s. So o b_aruco
# le isso (video_kicks) -- e o elo que faz a imagem glitchar PELO NAIPE, igual
# ao audio, e nao so pelo nivel global.
VID_KICK_TAU = 0.45


# =============================================================================
# O MOTOR DA CORRUPCAO
#
# Uma CLASSE (class) e como a PLANTA de uma fabrica, ou um molde de biscoito:
# descreve o que um "objeto" sabe guardar e o que sabe fazer. Depois a gente
# "fabrica" um objeto a partir dela (glitch = GlitchEngine()) e usa esse objeto.
# Dentro da classe, "self" e o jeito do objeto falar de si mesmo ("eu, o motor").
# =============================================================================

class GlitchEngine:
    """Acumula a corrupcao e manda /mundo/glitch pro b_synth.scd a cada carta."""

    # __init__ e a "montagem" do objeto: roda automaticamente uma vez, no momento
    # em que a gente cria o motor. E onde ele guarda suas coisas iniciais.
    # Os valores depois do "=" sao PADROES: se ninguem disser, usa esses.
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 verbose: bool = b_config.DEBUG, step: float = DEFAULT_STEP,
                 max_words: int = DEFAULT_WORDS):
        # cria o "carteiro" que vai mandar as mensagens OSC pro endereco e porta.
        self.client = udp_client.SimpleUDPClient(host, port)
        # guarda dentro do objeto (no "self") cada coisa que ele vai precisar lembrar:
        self.verbose = verbose      # se True, escreve na tela o que esta fazendo
        self.step = step            # o tamanho do passo da sujeira por carta
        self.max_words = max_words  # quantas palavras do Perec carregar (legado)
        self.level = 0.0  # nivel global de corrupcao, comeca em 0.0 (limpo) e vai
                          # subindo ate perto de 1.0 (quase totalmente sujo).
                          # O ".0" deixa claro que e um numero com casa decimal.
        self._vid_kick = {}  # comeca como dicionario VAZIO. Vai guardar, por naipe,
                             # o ultimo "soco" visual: op -> (pico, instante).
                             # O "_" no comeco do nome e so um aviso de "uso interno".
        if verbose:
            # f"...{host}..." e uma "string formatada": o que estiver dentro de
            # {chaves} e trocado pelo valor da variavel. Imprime de onde pra onde
            # a corrupcao vai ser mandada.
            print(f"[GLITCH] corrupcao paralela -> {host}:{port} (/mundo/glitch)")

    def load_voice(self) -> int:
        """Manda algumas palavras do Perec (tts_cache) pro SC -- a espada
        (Espadas) corta ESTAS palavras em cacos. Reusa o cache da camada A
        sem editar nada dela. Se o cache estiver vazio, os shards ficam mudos
        ate a voz ser renderizada (qualquer run da opcao 1/5/7 enche o cache)."""
        # glob.glob acha TODOS os arquivos que batem com o padrao "*.wav" (qualquer
        # nome, terminando em .wav) dentro da pasta tts_cache. sorted() poe em ordem.
        wavs = sorted(glob.glob(os.path.join(TTS_CACHE_DIR, "*.wav")))
        if not wavs:  # "se a lista estiver vazia" (nenhum arquivo de voz achado)
            if self.verbose:
                print("[GLITCH] tts_cache vazio -> shards (Espadas) mudos "
                      "ate a voz do Perec ser renderizada uma vez.")
            return 0  # devolve 0 (zero palavras) e para por aqui
        random.shuffle(wavs)        # embaralha a lista (ordem ao acaso)
        chosen = wavs[:self.max_words]  # pega so as primeiras max_words da lista
        for path in chosen:         # "pra cada caminho de arquivo na lista escolhida"
            # tira a pasta e a extensao, sobrando so o nome (a "palavra"):
            #   ".../tts_cache/casa.wav" -> "casa"
            key = os.path.splitext(os.path.basename(path))[0]
            # manda pro SuperCollider: "carregue este arquivo com este apelido".
            self.client.send_message("/mundo/voz_load", [str(key), str(path)])
        if self.verbose:
            print(f"[GLITCH] {len(chosen)} palavras do Perec carregadas "
                  f"(a espada corta estas).")
        time.sleep(0.4)  # espera 0.4 segundo: o SC carrega o arquivo "em segundo
                         # plano" (async) e precisa de um tempinho pra terminar.
        return len(chosen)  # devolve QUANTAS palavras foram carregadas

    def _kick_for_rank(self, rank: str) -> float:
        """Valor da carta -> forca do golpe. A=leve (0.3) ... K=pesado (1.0)."""
        # "tentar" achar a posicao da carta na lista RANKS. Ex: A esta na posicao 0,
        # 2 na posicao 1, ... K na ultima. try/except = "tente; se der erro, faca
        # o plano B" em vez de o programa quebrar.
        try:
            idx = RANKS.index(rank)        # idx = posicao da carta (0, 1, 2, ...)
        except ValueError:                 # se a carta nao estiver na lista...
            idx = len(RANKS) // 2          # ...usa o meio (forca media). "//" e
                                           # divisao inteira (joga fora o resto).
        # transforma a posicao (0 ate o ultimo) num numero entre 0.3 e 1.0:
        #   posicao 0      -> 0.3 (golpe leve, o As)
        #   ultima posicao -> 1.0 (golpe pesado, o Rei)
        return 0.3 + (idx / (len(RANKS) - 1)) * 0.7

    def corrupt(self, rank: str, suit: str, kick: Optional[float] = None):
        """A carta corrompe: sobe o nivel global e dispara o glitch do naipe."""
        suit = suit.upper()             # garante o naipe em MAIUSCULA ("c" -> "C")
        tipo = SUIT_GLITCH.get(suit)    # consulta a tabela: naipe -> sabor da sujeira
        if tipo is None:                # se o naipe nao existe na tabela (ex: coringa
            return                      # sem naipe), nao faz nada e sai da funcao.
        if kick is None:                # se ninguem passou a forca do golpe...
            kick = self._kick_for_rank(rank)  # ...calcula pela carta (As leve..Rei forte)
        # curva assintotica: fecha uma fracao do que falta pro teto. Sobe forte
        # cedo, desacelera perto do fim, mas nunca satura em 1.0 (sem plato).
        # Em portugues: "o quanto falta pra 1.0" e (1.0 - self.level); a gente
        # anda um pedacinho (step) DESSA distancia. Por isso desacelera sozinho.
        self.level += self.step * (1.0 - self.level)
        # manda o recado pro SuperCollider: o sabor, o quanto ja sujou (level) e
        # a forca do golpe desta carta (kick). E a lista [..] sao os tres dados.
        self.client.send_message(
            "/mundo/glitch", [tipo, float(self.level), float(kick)])
        # acende o soco visual do naipe (o b_aruco le e glitcha a projecao
        # PELO NAIPE -- mesma operacao do audio, so que na imagem). Guarda o pico
        # (forca) e o instante AGORA (time.time() = relogio em segundos).
        self._vid_kick[tipo] = (float(kick), time.time())
        if self.verbose:
            pct = int(round(self.level * 100))  # vira porcentagem inteira pra mostrar
            print(f"[GLITCH] {rank}{suit} "
                  f"-> {GLITCH_LABEL.get(tipo, tipo)}  |  corrupcao {pct}%")

    def video_kicks(self) -> dict:
        """O 'soco' visual de cada naipe AGORA, decaindo no tempo. So o b_aruco
        le isso (a cada quadro): cada carta acende a operacao do seu naipe na
        projecao -- detune/freeze/shards/saturate, as mesmas chaves do audio --
        e ela some em ~VID_KICK_TAU s. E o que faz a IMAGEM glitchar pelo naipe,
        nao so pelo acumulo. Sem video (teclado), ninguem chama -- custo zero."""
        now = time.time()  # que horas sao AGORA (em segundos)
        out = {}           # vai montando aqui a resposta (dicionario vazio)
        # passa por cada soco guardado: "op" e o sabor, "peak" a forca, "t" o
        # instante em que aconteceu.
        for op, (peak, t) in self._vid_kick.items():
            # (now - t) = ha quantos segundos a carta caiu. A funcao exponencial
            # math.exp(-tempo/TAU) faz o valor DESCER suave: vale ~forca logo apos
            # a carta e vai virando quase zero conforme o tempo passa.
            v = peak * math.exp(-(now - t) / VID_KICK_TAU)
            if v > 0.01:   # se ainda sobrou um tiquinho de soco (> 1%)...
                out[op] = v  # ...inclui na resposta; senao ignora (ja sumiu).
        return out         # devolve "quais naipes estao 'acesos' agora, e quanto"

    def reset(self):
        """Zera a corrupcao -- nova consulta / nova performance."""
        self.level = 0.0          # volta a sujeira pra zero (limpo de novo)
        self._vid_kick.clear()    # apaga todos os socos visuais guardados
        # avisa o SuperCollider pra tambem zerar do lado dele
        self.client.send_message("/mundo/glitch_reset", [])
        if self.verbose:
            print("[GLITCH] corrupcao zerada (nova consulta).")


# =============================================================================
# A PONTE DO FLUXO CONTINUO (o "theremin")
#
# Enquanto o GlitchEngine acima e DISCRETO (um soco por carta), esta ponte e
# CONTINUA: o b_aruco, a cada quadro, manda a POSE de cada marcador visivel
# (onde esta, quao perto, quanto inclinado) e o SuperCollider modula uma voz ao
# vivo com isso -- a camera vira um instrumento, tipo theremin. Quando o
# marcador SOME, a ponte pede a cauda (a voz nao corta seco; ecoa em delay/
# reverb). So o b_aruco usa isto; sem webcam (teclado), ninguem chama.
#
#   /mundo/control     [id, naipe, x, y, size, spin, tilt, luma] - enquanto presente
#   /mundo/control_off [id]                                      - quando some (cauda)
#
# Os numeros da pose (todos 0..1, menos 'spin' que e -1..1) sao calculados no
# b_aruco a partir dos 4 cantos do marcador (sem precisar calibrar a camera):
#   x,y  = onde o marcador esta na imagem (x = scrub do sample ; y = altura/pitch)
#   size = tamanho aparente -> perto/longe (perto = mais intenso/denso)
#   spin = rotacao no proprio plano (girar a carta na mesa) -> detune/timbre
#   tilt = inclinacao (0 = de frente ; 1 = tombado) -> FREEZE (congela)
#   luma = brilho do marcador (iluminacao) -> cor do filtro/timbre
# =============================================================================

class TereminBridge:
    """Manda a pose de cada marcador (continuo) e pede a cauda quando some.

    Faz rate-limit por id (CONTROL_RATE_HZ) pra nao inundar o SC: a webcam
    cospe ~30 quadros/s, mas mandar isso vezes N marcadores entope a rede sem
    ganho audivel. O primeiro recado de um id sai NA HORA (abre a voz); os
    seguintes respeitam o intervalo minimo."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 verbose: bool = b_config.DEBUG,
                 rate_hz: float = b_config.CONTROL_RATE_HZ):
        self.client = udp_client.SimpleUDPClient(host, port)
        self.verbose = verbose
        # intervalo minimo (segundos) entre dois /mundo/control do MESMO id.
        self.min_dt = 1.0 / max(1.0, float(rate_hz))
        self._last_send = {}   # id -> instante (s) do ultimo envio
        self._active = set()   # ids com voz ABERTA agora no SC
        if verbose:
            print(f"[THEREMIN] fluxo continuo -> {host}:{port} "
                  f"(/mundo/control, ate {b_config.MAX_VOICES} vozes)")

    def update(self, mid: int, suit, x: float, y: float,
               size: float, spin: float, tilt: float, luma: float = 0.5):
        """Manda a pose deste marcador (abre a voz na primeira vez)."""
        now = time.time()
        last = self._last_send.get(mid, 0.0)
        # ja tem voz aberta E ainda nao deu o intervalo minimo -> segura o envio.
        if (mid in self._active) and ((now - last) < self.min_dt):
            return
        self._last_send[mid] = now
        self._active.add(mid)
        # 'suit' pode ser None (curingao) -> manda "?" e o SC escolhe um sabor neutro.
        # 'luma' (iluminacao do marcador) entra como ultimo dado -> cor do timbre.
        self.client.send_message(
            "/mundo/control",
            [int(mid), str(suit or "?"), float(x), float(y),
             float(size), float(spin), float(tilt), float(luma)])

    def release(self, mid: int):
        """Marcador sumiu: solta a voz (gate=0) -> cauda em delay/reverb."""
        if mid in self._active:
            self._active.discard(mid)
            self._last_send.pop(mid, None)
            self.client.send_message("/mundo/control_off", [int(mid)])

    def release_all(self):
        """Solta TODAS as vozes (fim da partida / saida)."""
        for mid in list(self._active):
            self.release(mid)

    def active_ids(self) -> set:
        """Quais ids estao controlando som agora (o b_aruco usa pra saber quem soltar)."""
        return set(self._active)


# =============================================================================
# DEMO
#
# Tudo aqui embaixo so roda quando voce executa ESTE arquivo direto
# (python b_glitch.py), pra testar/ouvir sozinho. Quando o b_glitch e usado
# pela peca inteira, esta parte NAO roda (ver o "if __name__" la no fim).
# =============================================================================

def main():
    print("=" * 60)  # imprime 60 sinais de "=" enfileirados (uma linha decorativa)
    print("B_GLITCH - a colisao (corrupcao paralela) - DEMO")
    print("=" * 60)
    print("Pre-requisito: SC com a_synth.scd E b_synth.scd rodando.")
    print()
    glitch = GlitchEngine(verbose=True)  # FABRICA o motor (roda o __init__ la em cima)
    glitch.load_voice()                  # tenta carregar as palavras do Perec
    print()
    print("[DEMO] 12 cartas -- a corrupcao sobe e a maquina vai gaguejando...")
    suits = list(SUIT_NAMES.keys())  # lista das siglas de naipe: ["C","O","E","P"]
    for _ in range(12):              # repete 12 vezes (o "_" = "nao me importa o numero")
        rank = random.choice(RANKS)  # sorteia um valor de carta
        suit = random.choice(suits)  # sorteia um naipe
        glitch.corrupt(rank, suit)   # joga essa carta no motor (sobe a sujeira)
        time.sleep(2.5)              # espera 2,5 segundos pra dar pra ouvir a mudanca
    print()
    print("[DEMO] fim. (a corrupcao mora no Python; reinicie pra zerar)")


# Esta linha e um classico do Python. Em portugues claro:
# "SE este arquivo foi executado DIRETO (e nao apenas importado por outro),
#  ENTAO rode a funcao main()". E por isso que 'import b_glitch' nao dispara o demo.
if __name__ == "__main__":
    main()
