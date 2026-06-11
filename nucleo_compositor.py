"""
SISTEMA BARALHO MUSICAL
Transforma cartas de baralho em parametros musicais.

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md. E este e o arquivo MAIS
*** AVANCADO e mais matematico do projeto -- de boa se ele parecer dificil.
*** Voce NAO precisa entender tudo aqui pra entender a peca: pense neste
*** arquivo como uma "maquina de traducao" que pega uma carta e cospe numeros
*** que viram musica. Os outros arquivos so usam o resultado.

A ideia central, em palavras simples:
  - Cada carta tem um VALOR (As=1, ..., 10=10) e um NAIPE (Copas/Ouros/Espadas/Paus).
  - O NAIPE diz qual CONTA fazer entre o valor da carta e o "resultado anterior":
        Copas  -> somar         Ouros   -> subtrair
        Paus   -> gcd (*)       Espadas -> lcm (*)
    (*) gcd = "maior divisor comum"; lcm = "menor multiplo comum". Sao duas
        contas classicas de matematica de escola. Nao precisa dominar: o codigo
        faz a conta; aqui elas servem so pra gerar numeros com "personalidade".
  - O numero que sai da conta vira um PARAMETRO musical (que nota tocar, quao
    forte, qual andamento, etc.), consultando umas TABELAS de-para mais abaixo.
  - Como as contas podem dar numeros enormes, existe um truque chamado "fold"
    (dobra) que traz o numero de volta pra uma faixinha musical [-10, +10],
    como uma corda batendo na parede e voltando (ver a funcao fold_range).
  - As figuras J, Q, K nao tem valor proprio: viram "tempo" (passado/presente/
    futuro). O codigo explica cada uma onde elas aparecem (process_card).

Resumo pro leigo: cartas entram, contas acontecem, numeros saem, numeros viram
musica. O detalhe tecnico abaixo e pra quem quiser MESMO mergulhar -- pode pular.

FLUXO:
1. Embaralha o baralho (52 cartas)
2. Evento inicial = 0
3. Cada nota usa 7 cartas consecutivas -> 7 parametros
4. Para cada carta: E_novo = current_value OPERACAO E_anterior
5. O resultado mapeia para um dos 7 parametros da nota

OPERACOES POR NAIPE:
  - PAUS (PRETO): gcd(current, E_anterior)      (identidade = 0; gcd(a,0)=a)
  - OUROS (VERMELHO): current - E_anterior      (identidade = 0)
  - COPAS (VERMELHO): current + E_anterior      (identidade = 0)
  - ESPADAS (PRETO): lcm(current, E_anterior)   (identidade = 1; lcm(a,1)=a)

GCD/LCM operam em magnitudes e aplicam o SINAL do current (preserva a
"direcao" da carta atual mesmo com e_anterior negativo).

CARTAS DE ACAO (J, Q, K) - nao tem valor proprio:
  - J (PASSADO / R): current = valor da carta IMEDIATAMENTE anterior.
                     Se a anterior tambem for J/Q/K -> identidade do naipe.
  - Q (PRESENTE / I): current = IDENTIDADE do naipe (sem valor mesmo).
                      Aplica ESPELHO no parametro depois.
  - K (FUTURO / RI): current = valor da PROXIMA carta do baralho.
                     Se a proxima for J/Q/K -> identidade do naipe.
                     Aplica ESPELHO no parametro depois.

ESPELHO PARAMETRICO (Q e K):
  Espelha a tabela do parametro em torno do centro musical (0):
  - key 0 (centro) fixo: -0 = 0
  - demais: -key (G<->F, ppp<->fff, 20bpm<->180bpm, etc.)

SINAL DOS NAIPES:
  - Vermelhos (Ouros, Copas): valor negativo
  - Pretos (Paus, Espadas): valor positivo
  - 10: sempre +10 (neutro, sem partido - unica carta que nao escolhe lado)

GRAMATICA DE ARTICULACAO:
  - A (Ace)  : PAUSA   - encerra a nota imediatamente (silencio)
  - 10       : FERMATA - flag has_fermata=True, nao encerra a nota
  - evento -1: LIGADURA com nota anterior (tie_backward)
  - evento +1: LIGADURA com nota seguinte  (tie_forward)
  Note flags (is_rest, has_fermata, tie_backward, tie_forward) acumulam
  conforme as cartas/eventos sao processados na nota.

PARAMETROS (por ordem das 7 cartas):
  1. NOTA: G(-4), A(-3), B(-2), C(0-centro), D(+2), E(+3), F(+4)
  2. ALTERACOES (cents): -200(-9) a +200(+9), 0 = centro
  3. FIGURA RITMICA: Fusa(-7) a Breve(+7), Seminima(0) = centro
  4. ANDAMENTO (BPM): 20(-9) a 180(+9), 100(0) = centro
  5. DINAMICA: ppp(-5) a fff(+5), SEM centro - pula +/-1 (ligadura)
  6. ARTICULACAO: Acento c/Stacatto(-4) a Acento c/Tenuto(+4), Normal(0) = centro
  7. OITAVA: 1(-4) a 7(+4), oitava 4(0) = centro
"""

import math    # contas (aqui: gcd = maior divisor comum)
import random  # embaralhar/sortear
import sys      # ajustes do sistema (encoding do terminal)
from typing import List, Tuple, Optional, Dict, Any  # rotulos de tipo (so documentam)
from dataclasses import dataclass  # um atalho pra criar "fichas" de dados (ver Card/Note)
from enum import Enum  # cria uma LISTA FIXA de opcoes com nome (ver Suit, os 4 naipes)

# Fix terminal encoding for Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')


# =============================================================================
# CONSTANTES E CONFIGURACOES
# =============================================================================

# Um "Enum" e uma lista fixa de opcoes nomeadas. Aqui, os 4 naipes. Em vez de
# espalhar o texto "PAUS" pelo codigo (e arriscar erro de digitacao), usa-se
# Suit.PAUS -- mais seguro e mais legivel.
class Suit(Enum):
    PAUS = 'PAUS'
    OUROS = 'OUROS'
    COPAS = 'COPAS'
    ESPADAS = 'ESPADAS'

SUIT_INFO = {
    Suit.PAUS:     {'symbol': 'Paus', 'color': 'PRETO', 'op_name': 'gcd'},
    Suit.OUROS:    {'symbol': 'Ouros', 'color': 'VERMELHO', 'op_name': 'subtract'},
    Suit.COPAS:    {'symbol': 'Copas', 'color': 'VERMELHO', 'op_name': 'add'},
    Suit.ESPADAS:  {'symbol': 'Espadas', 'color': 'PRETO', 'op_name': 'lcm'},
}

# Elemento neutro da operacao de cada naipe.
# E o que J/Q/K assumem quando nao ha valor disponivel para herdar.
#   Copas (+):     a + 0 = a       ->  identidade = 0
#   Ouros (-):     a - 0 = a       ->  identidade = 0
#   Espadas (lcm): lcm(a, 1) = a   ->  identidade = 1
#   Paus (gcd):    gcd(a, 0) = a   ->  identidade = 0
SUIT_IDENTITY = {
    Suit.COPAS:   0,
    Suit.OUROS:   0,
    Suit.ESPADAS: 1,
    Suit.PAUS:    0,
}

CARD_TYPES = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
NUMERIC_VALUES = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10}


# =============================================================================
# MAPEAMENTO DOS PARAMETROS
# =============================================================================

PARAM_NOTA = {
    'name': 'NOTA',
    'mapping': {-4: 'G', -3: 'A', -2: 'B', 0: 'C', 2: 'D', 3: 'E', 4: 'F'}
}

PARAM_ALTERACAO = {
    'name': 'ALTERACOES (cents)',
    'mapping': {
        -9: -200, -8: -183, -7: -150, -6: -133, -5: -100, -4: -83,
        -3: -50, -2: -33, 0: 0, 2: 33, 3: 50, 4: 83, 5: 100,
        6: 133, 7: 150, 8: 183, 9: 200
    }
}

PARAM_RITMO = {
    'name': 'FIGURA RITMICA',
    'mapping': {
        -7: 'FUSA', -6: 'FUSA PONTUADA', -5: 'SEMICOLCHEIA',
        -4: 'SEMICOLCHEIA PONTUADA', -3: 'COLCHEIA', -2: 'COLCHEIA PONTUADA',
        0: 'SEMINIMA',
        2: 'SEMINIMA PONTUADA', 3: 'MINIMA', 4: 'MINIMA PONTUADA',
        5: 'SEMIBREVE', 6: 'SEMIBREVE PONTUADA', 7: 'BREVE'
    }
}

PARAM_ANDAMENTO = {
    'name': 'ANDAMENTO (BPM)',
    'mapping': {
        -9: 20, -8: 30, -7: 40, -6: 50, -5: 60, -4: 70, -3: 80, -2: 90,
        0: 100,
        2: 110, 3: 120, 4: 130, 5: 140, 6: 150, 7: 160, 8: 170, 9: 180
    }
}

# DINAMICA nao tem centro (nao existe "dinamica neutra"). 8 niveis espalhados
# em +/-2 a +/-5, pulando +/-1 (reservado para LIGADURA).
PARAM_DINAMICA = {
    'name': 'DINAMICA',
    'mapping': {-5: 'ppp', -4: 'pp', -3: 'p', -2: 'mp', 2: 'mf', 3: 'f', 4: 'ff', 5: 'fff'}
}

PARAM_ARTICULACAO = {
    'name': 'ARTICULACAO',
    'mapping': {
        -4: 'ACENTO C/ STACATTO', -3: 'TENUTO C/ STACATTO', -2: 'STACATTO',
        0: 'NORMAL',
        2: 'TENUTO', 3: 'ACENTO', 4: 'ACENTO C/ TENUTO'
    }
}

PARAM_OITAVA = {
    'name': 'OITAVA',
    'mapping': {-4: '1', -3: '2', -2: '3', 0: '4', 2: '5', 3: '6', 4: '7'}
}

# Lista de parametros na ordem de processamento (7 cartas por nota)
PARAMETERS = [
    PARAM_NOTA, PARAM_ALTERACAO, PARAM_RITMO, PARAM_ANDAMENTO,
    PARAM_DINAMICA, PARAM_ARTICULACAO, PARAM_OITAVA
]

# Figura ritmica -> duracao em "quarterLength" (1.0 = seminima/quarter note).
# Usado para calcular duracao real em segundos (junto com BPM) e por
# legado_partitura.py para exportar partitura.
RITMO_TO_QUARTERLENGTH = {
    'FUSA': 0.125,
    'FUSA PONTUADA': 0.1875,
    'SEMICOLCHEIA': 0.25,
    'SEMICOLCHEIA PONTUADA': 0.375,
    'COLCHEIA': 0.5,
    'COLCHEIA PONTUADA': 0.75,
    'SEMINIMA': 1.0,
    'SEMINIMA PONTUADA': 1.5,
    'MINIMA': 2.0,
    'MINIMA PONTUADA': 3.0,
    'SEMIBREVE': 4.0,
    'SEMIBREVE PONTUADA': 6.0,
    'BREVE': 8.0,
}

DEFAULT_BPM = 100         # Usado antes da primeira nota com BPM explicito
FERMATA_MULTIPLIER = 2.0  # Fermata dobra a duracao tocada


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

def nearest_value(mapping: Dict[int, Any], event_value: int) -> Tuple[int, Any]:
    """
    Encontra o valor mais proximo no mapeamento para um dado event_value.
    Retorna (key, display_name).
    Em caso de empate, prefere a chave mais proxima do zero (centro musical).
    """
    keys = sorted(mapping.keys())  # as posicoes da tabela, em ordem

    if event_value in mapping:                 # se o valor existe exatinho na tabela...
        return event_value, mapping[event_value]  # ...devolve ele direto

    # senao, acha a posicao MAIS PERTO. O "key=lambda k: ..." e uma mini-funcao
    # anonima (sem nome) que diz ao min() COMO comparar: primeiro pela distancia
    # ate o valor procurado (abs = valor absoluto, "tira o sinal"), e em caso de
    # empate, pela proximidade do zero (o centro musical). abs(3 - 5) = 2.
    best_key = min(keys, key=lambda k: (abs(k - event_value), abs(k)))
    return best_key, mapping[best_key]


def map_event_to_param(param: Dict[str, Any], event_value: int) -> Tuple[int, Any]:
    """
    Mapeia um evento para o range do parametro, com semantica de fold:

      - Aplica fold no range das chaves do parametro (min/max).
      - nearest_value resolve buracos (ex: +/-1 que nao existem mais em quase
        nenhuma tabela porque sao reservados para LIGADURA).

    Isso impede que valores grandes (ex: +7 em DINAMICA que vai so ate +/-5)
    colapsem todos no extremo: eles "dobram" de volta (ping-pong).
    """
    mapping = param['mapping']

    keys = list(mapping.keys())
    lo = min(keys)
    hi = max(keys)
    folded = fold_range(event_value, lo, hi)
    return nearest_value(mapping, folded)


def get_card_numeric_value(card_type: str, suit: Suit) -> int:
    """
    Obtem o valor numerico de uma carta, considerando o sinal do naipe.
    - Naipes vermelhos (Ouros, Copas): valor negativo
    - Naipes pretos (Paus, Espadas): valor positivo
    - 10: sempre 10 (neutro/centro)
    """
    base = NUMERIC_VALUES[card_type]
    if card_type == '10':
        return 10  # Neutro
    
    if SUIT_INFO[suit]['color'] == 'VERMELHO':
        return -base
    else:
        return base


def signed_gcd(a: int, b: int) -> int:
    """
    GCD (maximo divisor comum) aplicando o SINAL de 'a' (current).
    Edge cases:
      gcd(0, 0) = 0
      gcd(a, 0) = a   (preserva sinal e magnitude de a -> identidade limpa)
      gcd(0, b) = 0   (current zero domina)
    """
    if a == 0:
        return 0
    g = math.gcd(abs(a), abs(b))  # gcd sempre da positivo; usamos os valores sem sinal
    return -g if a < 0 else g     # depois devolvemos o sinal do 'a' (a "direcao" da carta)


def signed_lcm(a: int, b: int) -> int:
    """
    LCM (minimo multiplo comum) aplicando o SINAL de 'a' (current).
    Edge cases:
      lcm(a, 0) = 0   (qualquer * 0 = 0)
      lcm(0, b) = 0
      lcm(a, 1) = a   (preserva sinal e magnitude de a -> identidade limpa)
    """
    if a == 0 or b == 0:
        return 0
    # formula classica: lcm(a,b) = |a|*|b| / gcd(a,b). "//" e divisao inteira.
    g = math.gcd(abs(a), abs(b))
    l = abs(a) * abs(b) // g
    return -l if a < 0 else l  # de novo, devolve o sinal do 'a'


def suit_operation(suit: Suit, current_value: int, modified_previous: int) -> int:
    """
    Aplica a operacao do naipe: E_atual OP (E_anterior_modificado)

    PAUS:     gcd(current, E_ant)  -> contrai para divisor comum (sempre inteiro)
    OUROS:    current - E_ant      -> subtracao
    COPAS:    current + E_ant      -> soma
    ESPADAS:  lcm(current, E_ant)  -> expande para multiplo comum

    GCD/LCM trabalham com magnitudes e aplicam o sinal do current. Resultado
    sempre inteiro. LCM pode estourar (lcm(7, 8) = 56), mas o fold no
    process_card devolve para [-10, +10].
    """
    if suit == Suit.PAUS:
        return signed_gcd(current_value, modified_previous)
    elif suit == Suit.OUROS:
        return current_value - modified_previous
    elif suit == Suit.COPAS:
        return current_value + modified_previous
    elif suit == Suit.ESPADAS:
        return signed_lcm(current_value, modified_previous)
    else:
        raise ValueError(f"Naipe desconhecido: {suit}")


def fold_range(x: int, lo: int = -10, hi: int = 10) -> int:
    """
    Espelha 'x' reflexivamente para dentro de [lo, hi] (fold/reflect).

    Funciona como uma corda dobrando de volta quando ultrapassa o limite.
    Ex em [-10, 10]:
      11 -> 9,  18 -> 2,  20 -> 0,  25 -> -5,  30 -> -10,  81 -> 1
      -11 -> -9,  -18 -> -2,  -20 -> 0,  -81 -> -1

    Diferente do modulo (que envelopa circular: 18 -> -3), o fold mantem
    a polaridade: valores positivos grandes viram positivos pequenos.
    """
    # imagine uma corda esticada entre 'lo' e 'hi'. Se o numero passa do limite,
    # ele "rebate" pra dentro, como uma bolinha quicando entre duas paredes.
    if lo <= x <= hi:        # ja esta dentro? entao nem mexe.
        return x
    span = hi - lo            # ex: 20
    period = 2 * span         # ex: 40 (ir ate a parede e voltar)
    shifted = (x - lo) % period  # "%" = resto da divisao; traz pra dentro de um ciclo
    if shifted > span:           # se passou da metade do ciclo, esta "voltando"...
        shifted = period - shifted  # ...entao reflete (rebate na parede)
    return lo + shifted


def map_event_to_integer(event_value: float) -> int:
    """Converte o valor do evento para inteiro (arredondamento correto)."""
    return round(event_value)


def note_duration_seconds(note: "Note", current_bpm: int) -> float:
    """
    Calcula a duracao real (em segundos) de uma Note dada o BPM atual.
    Considera fermata (dobra a duracao). Se a nota nao tem ritmo definido,
    assume 1 seminima.
    """
    ritmo_value = None
    if note.parameters:
        if note.is_rest:
            ritmo_value = note.parameters[0].mapped_value
        elif len(note.parameters) > 2:
            ritmo_value = note.parameters[2].mapped_value
    ql = RITMO_TO_QUARTERLENGTH.get(ritmo_value, 1.0) if ritmo_value else 1.0
    seconds_per_beat = 60.0 / max(int(current_bpm), 1)
    total = float(ql) * seconds_per_beat
    if note.has_fermata:
        total *= FERMATA_MULTIPLIER
    return total


def total_duration_seconds(notes: List["Note"], initial_bpm: int = DEFAULT_BPM) -> float:
    """
    Duracao total (segundos) de uma lista de Notes, propagando o BPM:
    cada nota normal define o BPM atual via parameters[3]; pausas mantem o BPM
    anterior. Util pra saber quanto tempo a composicao toca.
    """
    current_bpm = initial_bpm
    total = 0.0
    for note in notes:
        if not note.is_rest and len(note.parameters) > 3:
            bpm_val = note.parameters[3].mapped_value
            if isinstance(bpm_val, int):
                current_bpm = bpm_val
        total += note_duration_seconds(note, current_bpm)
    return total


def note_to_dict(note: "Note", current_bpm: int, start_seconds: float) -> Dict[str, Any]:
    """
    Extrai um dicionario estruturado com TUDO que esta acontecendo na nota:
    altura, microtonalidade (cents), figura, duracao real em segundos, BPM,
    dinamica, articulacao, fermata e ligaduras. Usado pela exportacao escrita.

    current_bpm: BPM vigente (propagado de fora, pausas herdam o anterior).
    start_seconds: instante (em s) em que a nota comeca na linha do tempo.
    """
    dur = note_duration_seconds(note, current_bpm)
    base = {
        'is_rest': note.is_rest,
        'start': start_seconds,
        'dur': dur,
        'end': start_seconds + dur,
        'fermata': note.has_fermata,
        'tie_in': note.tie_backward,
        'tie_out': note.tie_forward,
        'bpm': current_bpm,
    }

    if note.is_rest:
        ritmo = note.parameters[0].mapped_value if note.parameters else 'SEMINIMA'
        base.update({'ritmo': ritmo})
        return base

    p = note.parameters
    cents = p[1].mapped_value if len(p) > 1 else 0
    base.update({
        'nota': p[0].mapped_value if len(p) > 0 else '?',
        'oitava': p[6].mapped_value if len(p) > 6 else '4',
        'cents': cents if isinstance(cents, int) else 0,
        'ritmo': p[2].mapped_value if len(p) > 2 else 'SEMINIMA',
        'dinamica': p[4].mapped_value if len(p) > 4 else 'mf',
        'articulacao': p[5].mapped_value if len(p) > 5 else 'NORMAL',
    })
    return base


def describe_note_text(d: Dict[str, Any]) -> str:
    """
    Formata UMA nota (ja extraida por note_to_dict) em uma frase legivel.
    """
    flags = []
    if d['fermata']:
        flags.append("FERMATA(segura)")
    if d['tie_in']:
        flags.append("ligada<-anterior")
    if d['tie_out']:
        flags.append("ligada->proxima")
    flag_str = ("  [" + ", ".join(flags) + "]") if flags else ""

    tempo = f"t={d['start']:6.2f}s  dur={d['dur']:5.2f}s"

    if d['is_rest']:
        return f"{tempo}  PAUSA ({d['ritmo']}){flag_str}"

    cents = d['cents']
    if cents == 0:
        micro = "afinacao justa (0 cents)"
    elif cents % 100 == 0:
        micro = f"{cents:+d} cents (semitom temperado)"
    else:
        micro = f"{cents:+d} cents (MICROTOM)"

    return (
        f"{tempo}  {d['nota']}{d['oitava']}  {micro}  |  "
        f"{d['ritmo']} @ {d['bpm']}bpm  |  "
        f"din={d['dinamica']}  art={d['articulacao']}{flag_str}"
    )


def export_partitura_texto(
    notes: List["Note"],
    filename: str = "composicao.txt",
    title: str = "Composicao Baralho Musical",
    seed: Optional[int] = None,
    initial_bpm: int = DEFAULT_BPM,
) -> str:
    """
    Exporta a composicao como uma PARTITURA ESCRITA (texto legivel), nota por
    nota: altura, microtonalidade em cents, duracao real em segundos, instante
    de inicio na linha do tempo, BPM, dinamica, articulacao, fermata, ligaduras
    e pausas.

    E uma alternativa ao MusicXML: em vez de uma partitura grafica, descreve
    tudo que esta acontecendo de forma narrada. Retorna o caminho do arquivo.
    """
    current_bpm = initial_bpm
    elapsed = 0.0
    lines: List[str] = []

    lines.append("=" * 78)
    lines.append(title)
    lines.append("=" * 78)
    if seed is not None:
        lines.append(f"Seed: {seed}")
    total = total_duration_seconds(notes, initial_bpm)
    n_rests = sum(1 for n in notes if n.is_rest)
    lines.append(f"Total: {len(notes)} eventos ({len(notes) - n_rests} notas, "
                 f"{n_rests} pausas)  |  duracao ~{total:.2f}s "
                 f"(~{total / 60:.2f} min)")
    lines.append("")
    lines.append("Legenda: t=instante de inicio | dur=duracao tocada | "
                 "cents=desvio microtonal | bpm=andamento vigente")
    lines.append("-" * 78)
    lines.append("")

    for i, note in enumerate(notes):
        # BPM vigente: nota normal define; pausa herda o anterior.
        if not note.is_rest and len(note.parameters) > 3:
            bpm_val = note.parameters[3].mapped_value
            if isinstance(bpm_val, int):
                current_bpm = bpm_val

        d = note_to_dict(note, current_bpm, elapsed)
        lines.append(f"#{i + 1:>4}  {describe_note_text(d)}")
        elapsed = d['end']

    lines.append("")
    lines.append("-" * 78)
    lines.append(f"FIM  |  duracao total: {elapsed:.2f}s (~{elapsed / 60:.2f} min)")

    text = "\n".join(lines) + "\n"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"[OK] Partitura escrita exportada: {filename}")
    return filename


def apply_param_mirror(param: Dict[str, Any], mapped_key: int) -> Tuple[int, Any]:
    """
    Espelha o resultado de um parametro em torno do centro musical (0).
    Regra:
      - key 0 (centro) fixo: -0 = 0
      - demais keys: -key
    Se a key espelhada nao existir no mapping, faz nearest_value como fallback.
    """
    mirrored = -mapped_key
    if mirrored in param['mapping']:
        return mirrored, param['mapping'][mirrored]
    return nearest_value(param['mapping'], mirrored)


# =============================================================================
# CLASSES PRINCIPAIS
# =============================================================================

# "@dataclass" e um atalho: ele transforma a classe numa "ficha" de dados. A
# gente so lista quais campos a ficha tem (type e suit) e o Python ja cria a
# montagem automatica. Card(type='Q', suit=Suit.COPAS) = a ficha da Dama de Copas.
@dataclass
class Card:
    """Representa uma carta de baralho."""
    type: str       # 'A', '2'-'10', 'J', 'Q', 'K'
    suit: Suit
    
    def __str__(self):
        symbol = SUIT_INFO[self.suit]['symbol']
        return f"{self.type}/{symbol}"
    
    def is_action(self) -> bool:
        """Verifica se e uma carta de acao (J, Q, K)."""
        return self.type in ('J', 'Q', 'K')
    
    def is_ace(self) -> bool:
        """Verifica se e um As (pausa)."""
        return self.type == 'A'


@dataclass
class NoteParameter:
    """Um parametro processado para uma nota."""
    param_name: str
    event_value: int
    mapped_key: int
    mapped_value: Any
    
    def __str__(self):
        return f"{self.param_name}: {self.mapped_value} (event={self.event_value})"


@dataclass
class Note:
    """Uma nota musical gerada pelo sistema."""
    parameters: List[NoteParameter]
    is_rest: bool = False        # Disparado pela carta A (encerra a nota)
    has_fermata: bool = False    # Disparado pela carta 10 (segura a nota)
    tie_backward: bool = False   # Disparado por evento -1 (liga com nota anterior)
    tie_forward: bool = False    # Disparado por evento +1 (liga com nota seguinte)
    cards_used: List['Card'] = None  # Cartas que geraram esta nota (na ordem de saida)

    def __post_init__(self):
        if self.cards_used is None:
            self.cards_used = []

    def _articulation_marks(self) -> str:
        marks = []
        if self.tie_backward:
            marks.append("<-")
        if self.tie_forward:
            marks.append("->")
        if self.has_fermata:
            marks.append("(^)")
        return " " + " ".join(marks) if marks else ""

    def __str__(self):
        if self.is_rest:
            return f"PAUSA (REST){self._articulation_marks()}"
        parts = [str(p) for p in self.parameters]
        return f"Nota: {' | '.join(parts)}{self._articulation_marks()}"

    def get_summary(self) -> str:
        """Resumo compacto da nota."""
        marks = self._articulation_marks()
        if self.is_rest:
            if self.parameters:
                key = self.parameters[0].mapped_key
                ritmo = self.parameters[0].mapped_value
                return f"PAUSA ({key}: {ritmo}){marks}"
            return f"PAUSA{marks}"
        nota = self.parameters[0].mapped_value
        alteracao = self.parameters[1].mapped_value
        if isinstance(alteracao, int) and alteracao != 0:
            alteracao_str = f"{alteracao:+d}cents"
        else:
            alteracao_str = ""
        ritmo = self.parameters[2].mapped_value
        andamento = self.parameters[3].mapped_value
        din = self.parameters[4].mapped_value
        art = self.parameters[5].mapped_value
        oit = self.parameters[6].mapped_value

        return f"{nota}{alteracao_str} {ritmo} {andamento}bpm {din} {art} Oit.{oit}{marks}"


class Baralho:
    """Baralho de 52 cartas."""
    
    def __init__(self):
        self.cards: List[Card] = []
        self._build()
    
    def _build(self):
        """Constroi o baralho com 52 cartas."""
        # dois "for" um dentro do outro: pra cada naipe, pra cada valor, cria a
        # carta e .append() a poe no fim da lista. 4 naipes x 13 valores = 52.
        for suit in Suit:
            for card_type in CARD_TYPES:
                self.cards.append(Card(type=card_type, suit=suit))
    
    def shuffle(self, seed: Optional[int] = None):
        """Embaralha o baralho."""
        if seed is not None:
            random.seed(seed)
        random.shuffle(self.cards)
    
    def draw(self) -> Optional[Card]:
        """Compra a carta do topo."""
        if not self.cards:
            return None
        return self.cards.pop(0)
    
    def reset(self):
        """Reconstroi o baralho."""
        self.cards.clear()
        self._build()
    
    def remaining(self) -> int:
        return len(self.cards)


@dataclass
class ProcessResult:
    """Resultado do processamento de uma carta pelo InterpretadorEventos."""
    event_value: float
    action_label: str          # 'passado' | 'presente' | 'futuro' | 'numero'
    current_value: float       # valor efetivo usado na operacao
    valor_origem: str          # explicacao de onde veio o current_value (display)
    mirror_applied: bool       # se aplica espelho parametrico (Q e K)


class InterpretadorEventos:
    """
    Interpreta as cartas e gera eventos musicais.

    SEMANTICA J/Q/K (passado/presente/futuro):
      - J (passado): current = valor da carta imediatamente anterior;
                     se a anterior tambem for J/Q/K -> identidade do naipe.
      - Q (presente): current = identidade do naipe (sem valor). Aplica espelho.
      - K (futuro): current = valor da proxima carta;
                    se a proxima for J/Q/K -> identidade do naipe. Aplica espelho.

    O E_anterior nao e mais modificado por J/Q/K. A "transformacao temporal"
    vive na fonte do current_value, e a "inversao" vive no espelho parametrico
    aplicado depois do mapeamento (so para Q e K).
    """

    def __init__(self):
        self.event_history: List[int] = [0]  # Comeca com 0
        self.parameter_index: int = 0
        self.previous_card_value: Optional[int] = None  # ultima carta NUMERICA
        self.previous_card: Optional[Card] = None       # ultima carta processada (qualquer tipo)

    def reset(self):
        """Reinicia o interpretador."""
        self.event_history = [0]
        self.parameter_index = 0
        self.previous_card_value = None
        self.previous_card = None

    def process_card(self, card: Card, next_card: Optional[Card] = None) -> ProcessResult:
        """
        Processa uma carta retornando o resultado completo (ProcessResult).
        next_card so e usado por K (peek do futuro).
        """
        suit = card.suit

        # Esta funcao e o CORACAO da matematica. Em 4 passos: (1) decide qual numero
        # a carta "vale" agora -- so que J/Q/K nao tem valor proprio, eles viram
        # passado/presente/futuro; (2) anota a carta na memoria; (3) faz a conta do
        # naipe com o resultado anterior e dobra de volta pra faixa musical; (4)
        # guarda no historico e devolve o resultado. Leia bloco a bloco abaixo.

        # 1. Determinar current_value conforme tempo (J/Q/K) ou valor proprio
        if card.type == 'J':  # VALETE = passado: herda o valor da carta anterior
            action_label = 'passado'
            prev = self.previous_card
            if prev is None or prev.is_action():
                current_value = SUIT_IDENTITY[suit]
                valor_origem = f"identidade de {SUIT_INFO[suit]['symbol']} (passado sem valor)"
            else:
                current_value = get_card_numeric_value(prev.type, prev.suit)
                valor_origem = f"valor da carta anterior ({prev.type}/{SUIT_INFO[prev.suit]['symbol']})"
        elif card.type == 'Q':  # DAMA = presente: nao tem valor (usa a "identidade")
            action_label = 'presente'
            current_value = SUIT_IDENTITY[suit]
            valor_origem = f"identidade de {SUIT_INFO[suit]['symbol']} (presente, sem valor)"
        elif card.type == 'K':  # REI = futuro: espia a PROXIMA carta (next_card)
            action_label = 'futuro'
            if next_card is None or next_card.is_action():
                current_value = SUIT_IDENTITY[suit]
                qual = "futuro inexistente" if next_card is None else "futuro sem valor"
                valor_origem = f"identidade de {SUIT_INFO[suit]['symbol']} ({qual})"
            else:
                current_value = get_card_numeric_value(next_card.type, next_card.suit)
                valor_origem = f"valor da proxima carta ({next_card.type}/{SUIT_INFO[next_card.suit]['symbol']})"
        else:
            action_label = 'numero'
            current_value = get_card_numeric_value(card.type, suit)
            valor_origem = "valor proprio"

        # 2. Atualizar trackers ANTES da operacao (proximo passo precisa)
        self.previous_card = card
        if not card.is_action():
            self.previous_card_value = current_value

        # 3. Aplicar a operacao do naipe entre current_value e E_anterior (intacto)
        # "event_history[-1]" = o ultimo resultado guardado (o [-1] pega o ultimo
        # item de uma lista). e_anterior e o "resultado anterior" com que a conta
        # do naipe vai operar.
        e_anterior = self.event_history[-1] if self.event_history else 0
        # suit_operation ja retorna inteiro (divisao e truncada).
        # Aplicar fold em [-10, +10] para manter o evento dentro do range musical:
        # multiplicacao/soma podem explodir, mas a corda "dobra" de volta.
        raw = suit_operation(suit, current_value, e_anterior)  # a conta do naipe
        event_value = fold_range(raw, -10, 10)                 # traz pra faixa musical

        # 4. Guardar no historico (pra proxima carta usar como "anterior")
        self.event_history.append(event_value)

        return ProcessResult(
            event_value=event_value,
            action_label=action_label,
            current_value=current_value,
            valor_origem=valor_origem,
            mirror_applied=card.type in ('Q', 'K'),
        )


class Compositor:
    """
    Gera a composicao musical a partir do baralho.

    Configuracao:
    - Cada nota: 7 cartas (7 parametros)
    - Tamanho: pode ser definido por num_notes OU por target_seconds em compose()

    Quando o baralho fica vazio durante a geracao (composicoes longas),
    ele e reembaralhado e adicionado novamente. Isso e proposital -
    composicoes de minutos/horas precisam de varios baralhos.
    """

    def __init__(self, num_notes: int = 32):
        self.num_notes = num_notes
        self.baralho = Baralho()
        self.interpretador = InterpretadorEventos()
        self.notes: List[Note] = []
        # Seed/contador para reembaralhamentos sob demanda
        self._reshuffle_seed: Optional[int] = None
        self._reshuffle_count: int = 0

    def _ensure_cards(self, n: int, verbose: bool = False) -> bool:
        """
        Garante que o baralho tem pelo menos n cartas. Reabastece com um novo
        baralho embaralhado se necessario. Retorna True se conseguiu.
        """
        while self.baralho.remaining() < n:
            new_deck = Baralho()
            # Reembaralha com seed derivada (deterministico se seed foi dado)
            self._reshuffle_count += 1
            if self._reshuffle_seed is not None:
                new_deck.shuffle(self._reshuffle_seed + self._reshuffle_count)
            else:
                new_deck.shuffle(None)
            self.baralho.cards.extend(new_deck.cards)
            if verbose:
                print(f"[INFO] Baralho reabastecido (#{self._reshuffle_count + 1}).")
        return True

    def _generate_one_note(self, note_idx: int, total_hint: Optional[int], verbose: bool) -> Note:
        """Gera UMA nota (consome ate 7 cartas, podendo parar antes em caso de Ás)."""
        if verbose:
            print("-" * 80)
            header = f"NOTA {note_idx + 1}"
            if total_hint is not None:
                header += f"/{total_hint}"
            print(header)
            print("-" * 80)

        note_params: List[NoteParameter] = []
        cards_consumed: List[Card] = []
        rest_param_only: Optional[NoteParameter] = None
        is_rest_flag = False
        has_fermata = False
        tie_backward = False
        tie_forward = False

        # cada NOTA usa ate 7 cartas, uma por botao/parametro (a menos que um As
        # apareca e encerre a nota antes). Este for vai do parametro 0 ao 6.
        for param_idx in range(7):
            param = PARAMETERS[param_idx]
            # Garante carta disponivel (reabastece se preciso)
            self._ensure_cards(1, verbose=verbose)
            card = self.baralho.draw()  # compra a proxima carta do topo
            if card is None:
                if verbose:
                    print(f"[ERRO] Acabaram as cartas!")
                break
            cards_consumed.append(card)

            next_card = self.baralho.cards[0] if self.baralho.cards else None
            e_anterior_atual = self.interpretador.event_history[-1]

            if card.type == '10':
                has_fermata = True

            if card.is_ace():
                result = self.interpretador.process_card(card, next_card)
                int_event = map_event_to_integer(result.event_value)
                mapped_key, mapped_value = map_event_to_param(PARAM_RITMO, int_event)
                if int_event == -1:
                    tie_backward = True
                elif int_event == 1:
                    tie_forward = True
                rest_param_only = NoteParameter(
                    param_name=PARAM_RITMO['name'],
                    event_value=int_event,
                    mapped_key=mapped_key,
                    mapped_value=mapped_value,
                )
                is_rest_flag = True
                if verbose:
                    color = SUIT_INFO[card.suit]['color']
                    op = SUIT_INFO[card.suit]['op_name']
                    print(f"  [{param_idx+1}/7] {card} ({color}, {op}) [AS=PAUSA] "
                          f"current={result.current_value} OP E_ant={e_anterior_atual} "
                          f"-> E={int_event} "
                          f"-> DURACAO DA PAUSA: {mapped_value} (key={mapped_key})")
                    print(f"  [AS encerra a nota - demais cartas nao sao compradas]")
                break

            result = self.interpretador.process_card(card, next_card)
            int_event = map_event_to_integer(result.event_value)
            if int_event == -1:
                tie_backward = True
            elif int_event == 1:
                tie_forward = True

            mapped_key, mapped_value = map_event_to_param(param, int_event)
            pre_mirror_key = mapped_key
            pre_mirror_value = mapped_value
            if result.mirror_applied:
                mapped_key, mapped_value = apply_param_mirror(param, mapped_key)

            note_params.append(NoteParameter(
                param_name=param['name'],
                event_value=int_event,
                mapped_key=mapped_key,
                mapped_value=mapped_value,
            ))

            if verbose:
                color = SUIT_INFO[card.suit]['color']
                op = SUIT_INFO[card.suit]['op_name']
                tempo = result.action_label.upper()
                mirror_str = ""
                if result.mirror_applied and pre_mirror_key != mapped_key:
                    mirror_str = f" [ESPELHO {pre_mirror_value} -> {mapped_value}]"
                elif result.mirror_applied:
                    mirror_str = " [ESPELHO (fixo)]"
                art_flags = []
                if card.type == '10':
                    art_flags.append("FERMATA")
                if int_event == -1:
                    art_flags.append("LIGADURA<-")
                elif int_event == 1:
                    art_flags.append("LIGADURA->")
                art_str = f" [{' + '.join(art_flags)}]" if art_flags else ""
                print(f"  [{param_idx+1}/7] {card} ({color}, {op}) [{tempo}] "
                      f"current={result.current_value} OP E_ant={e_anterior_atual} "
                      f"-> E={int_event}{mirror_str}{art_str} "
                      f"-> {param['name']}: {mapped_value}")

        params_for_note: List[NoteParameter]
        if is_rest_flag:
            params_for_note = [rest_param_only] if rest_param_only is not None else []
        else:
            params_for_note = note_params

        note = Note(
            parameters=params_for_note,
            is_rest=is_rest_flag,
            has_fermata=has_fermata,
            tie_backward=tie_backward,
            tie_forward=tie_forward,
            cards_used=cards_consumed,
        )

        if verbose:
            print(f"  >>> {note.get_summary()}")

        return note

    def compose(
        self,
        seed: Optional[int] = None,
        verbose: bool = True,
        target_seconds: Optional[float] = None,
        initial_bpm: int = DEFAULT_BPM,
    ) -> List[Note]:
        """
        Gera a composicao completa.

        Args:
            seed: Semente para reproducao (deterministico).
            verbose: Mostra o processamento detalhado.
            target_seconds: Se dado, gera notas ate a duracao total atingir/passar
                este valor (a ultima nota toca inteira mesmo que estoure um pouco).
                Quando ativo, num_notes e ignorado.
            initial_bpm: BPM padrao antes da primeira carta de BPM (default 100).

        Returns:
            Lista de notas geradas.
        """
        # Embaralha baralho inicial
        self.baralho.reset()
        self.baralho.shuffle(seed)
        self.interpretador.reset()
        self.notes.clear()
        # Guarda info pra reembaralhar sob demanda
        self._reshuffle_seed = seed
        self._reshuffle_count = 0

        if verbose:
            print("=" * 80)
            if target_seconds is not None:
                print(f"COMPOSICAO: ate {target_seconds:.1f}s (~{target_seconds/60:.1f} min)")
            else:
                print(f"COMPOSICAO: {self.num_notes} notas")
            print("=" * 80)
            print()

        current_bpm = initial_bpm
        accumulated_seconds = 0.0  # quanto tempo de musica ja foi gerado
        note_idx = 0               # quantas notas ja foram geradas

        # gera nota apos nota ate atingir o alvo: ou um tempo total (target_seconds)
        # ou um numero de notas (num_notes). O "break" sai do laco quando chega la.
        while True:
            if target_seconds is not None:
                if accumulated_seconds >= target_seconds:
                    break
            else:
                if note_idx >= self.num_notes:
                    break

            note = self._generate_one_note(
                note_idx=note_idx,
                total_hint=self.num_notes if target_seconds is None else None,
                verbose=verbose,
            )
            self.notes.append(note)

            # Atualiza BPM e duracao acumulada
            if not note.is_rest and len(note.parameters) > 3:
                bpm_val = note.parameters[3].mapped_value
                if isinstance(bpm_val, int):
                    current_bpm = bpm_val
            accumulated_seconds += note_duration_seconds(note, current_bpm)
            note_idx += 1

        if verbose:
            print()
            print("=" * 80)
            print(f"COMPOSICAO COMPLETA: {len(self.notes)} notas, "
                  f"{accumulated_seconds:.2f}s (~{accumulated_seconds/60:.2f} min)")
            print("=" * 80)

        return self.notes
    
    def print_composition(self):
        """Exibe a composicao completa de forma resumida."""
        print()
        print("=" * 60)
        print("COMPOSICAO GERADA")
        print("=" * 60)
        
        for i, note in enumerate(self.notes):
            compasso = i // 4 + 1
            beat = (i % 4) + 1
            print(f"  Compasso {compasso}/{beat}: {note.get_summary()}")
        
        print()
        print(f"Total: {len(self.notes)} notas")
    
    def export_text(self, filename: str = "composicao.txt"):
        """Exporta a composicao para um arquivo texto."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("COMPOSICAO GERADA PELO SISTEMA BARALHO MUSICAL\n")
            f.write(f"{'='*60}\n\n")
            
            for i, note in enumerate(self.notes):
                compasso = i // 4 + 1
                beat = (i % 4) + 1
                f.write(f"Compasso {compasso}.{beat}: {note.get_summary()}\n")
                
                if note.is_rest:
                    f.write("  -> PAUSA (As)\n")
                else:
                    for p in note.parameters:
                        f.write(f"  {p.param_name}: {p.mapped_value}\n")
                f.write("\n")
        
        print(f"Composicao exportada para '{filename}'")


# =============================================================================
# FUNCAO PRINCIPAL
# =============================================================================

def main():
    """Funcao principal de demonstracao."""
    
    print("=" * 80)
    print("SISTEMA BARALHO MUSICAL")
    print("Transforma cartas de baralho em composicoes musicais")
    print("=" * 80)
    print()
    print("PARAMETROS POR NOTA (7 cartas):")
    for i, param in enumerate(PARAMETERS):
        keys = list(param['mapping'].keys())[:5]
        vals = [param['mapping'][k] for k in keys]
        samples = list(zip(keys, vals))
        print(f"  {i+1}. {param['name']}: {samples}...")
    print()
    
    # Exemplo: 8 notas (para teste rapido com 1 baralho)
    print("[INFO] Gerando 8 notas de exemplo...")
    compositor = Compositor(num_notes=8)
    compositor.compose(seed=42)
    compositor.print_composition()
    
    print()
    print("[INFO] Composicao completa de 32 notas:")
    
    compositor32 = Compositor(num_notes=32)
    compositor32.compose(seed=123, verbose=False)
    compositor32.print_composition()
    compositor32.export_text("composicao_32_notas.txt")
    
    # Mostra as primeiras 4 notas em detalhe
    print()
    print("[DETALHE] Primeiras 4 notas:")
    print("-" * 60)
    compositor_det = Compositor(num_notes=4)
    compositor_det.compose(seed=123)
    compositor_det.print_composition()


if __name__ == "__main__":
    main()