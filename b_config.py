"""
B_CONFIG - CANASTRA SUJA: o painel de ajustes (uma fonte unica de verdade)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: este arquivo NAO faz nada sozinho -- ele so guarda, num lugar
so, os "numeros e chaves" que o resto da peca consulta. Em vez de cada arquivo
ter o seu proprio ajuste espalhado, todos importam DAQUI. Mudou aqui, mudou
pra peca inteira.

O ajuste mais importante e o DEBUG (o "modo de teste" que o professor pediu):

    DEBUG = True   -> modo LABORATORIO (no seu laptop):
                      * os arquivos falam bastante na tela (verbose);
                      * o som sai em ESTEREO (2 caixas);
                      * o HUD de pose aparece na projecao (numeros do ArUco).
    DEBUG = False  -> modo APRESENTACAO (no conservatorio):
                      * a tela fica quieta (so o essencial);
                      * o som sai em OCTOFONIA (8 Genelecs) -- ver os .scd;
                      * a projecao fica limpa, sem numeros.

ATENCAO: o lado do SOM (SuperCollider) tem o SEU proprio ~debug, no topo de
a_synth.scd e b_synth.scd. Mantenha os DOIS iguais a este: aqui DEBUG controla
o Python; la ~debug controla o estereo-vs-octofonia. (Sao programas separados,
nao da pra um setar o outro pela rede sem complicar -- entao e na mao, nos dois
lugares. So duas linhas.)
"""

# =============================================================================
# O FLAG MESTRE (pedido do professor): True = laptop/teste ; False = conservatorio
# =============================================================================
DEBUG = True

# =============================================================================
# REDE OSC -- pra onde o Python grita os recados que viram som no SuperCollider.
# "127.0.0.1" = este mesmo computador. A porta 57120 e onde o SC escuta (as
# camadas A e B usam a MESMA porta, mas enderecos diferentes: /baralho/* e
# /mundo/*, entao nao se atrapalham).
# =============================================================================
HOST = "127.0.0.1"
PORT = 57120

# =============================================================================
# O FLUXO CONTINUO (o "theremin"): com que frequencia e com quanta suavidade o
# ArUco alimenta a pose (posicao/inclinacao do marcador) no SuperCollider.
# =============================================================================

# Quantas mensagens /mundo/control por segundo, POR marcador. A webcam roda a
# ~30 quadros/s; mandar mais que isso so congestiona a rede sem ganho. 30 da um
# controle fluido sem inundar o SC.
CONTROL_RATE_HZ = 30

# Suavizacao (media movel exponencial, "EMA"). E o quanto a pose nova "puxa" a
# anterior, de 0 a 1: perto de 1 = segue na hora (mais nervoso, pega tremor da
# mao); perto de 0 = bem suave (mais preguicoso, derrete). 0.35 = meio-termo
# (segue o gesto mas tira o tremido). Calibre no olho/ouvido tocando de verdade.
CONTROL_SMOOTH = 0.35

# Quantos marcadores podem CONTROLAR som ao mesmo tempo (cada um abre uma voz no
# SC). Mais que isso vira sopa: a mesa pode ter dezenas de cartas paradas, mas
# so as N maiores/mais perto viram instrumento. Segura o custo no SC tambem.
MAX_VOICES = 4

# Release (cauda) padrao em segundos quando um marcador SOME: a voz nao corta
# seco, solta nesse tempo e ecoa no delay/reverb. (O valor real do envelope mora
# no SC; este aqui e so referencia/documentacao do tempo combinado.)
TAIL_SECONDS = 4.0

# =============================================================================
# COOLDOWN DA CARTA (pedido 3): cada marcador so DISPARA a jogada discreta
# (atravessar habitat + somar sujeira/glitch) UMA vez a cada CARD_COOLDOWN_S
# segundos. Se a mesma carta reaparecer antes disso, ela NAO re-dispara -- mas
# segue alterando o som ao vivo pelo teremim (o fluxo continuo nao respeita este
# cooldown, so a jogada discreta). 150 s = 2 min e meio.
# =============================================================================
CARD_COOLDOWN_S = 150.0
