"""
BARALHO PEREC - integracao do livro "Especes d'espaces" (Georges Perec)
com o sistema musical do baralho.

ESTRUTURA:
  Cada capitulo do livro vira um "movimento" da peca. O usuario escolhe o
  capitulo ao vivo (via UI do visualizer); o texto-fonte desse capitulo eh
  picotado deterministicamente pelo estado do baralho e enviado:
    - como FRAGMENTOS CURTOS sussurrados nos ecos harmonicos (delays)
    - como FRASE LONGA declamada no recitativo durante FERMATA
  Tudo isso eh CAMADA EXTRA - nao substitui o synth (vibrafone) base.

PICOTAMENTO:
  Reusa a mesma gramatica do sistema musical:
    - NAIPE  -> operacao no ponteiro do texto:
        COPAS  (+):   avanca (soma magnitude da carta)
        OUROS  (-):   recua  (subtrai)
        ESPADAS (lcm): salta esparso (lcm com ponteiro atual)
        PAUS   (gcd): contrai/condensa (gcd com ponteiro atual)
    - NUMERO -> tamanho do pedaco
    - J/Q/K  -> direcao/janela:
        J (passado) -> retrogrado (le pra tras)
        Q (presente)-> ordem natural
        K (futuro)  -> projeta (pula adiante)
  Aplica FOLD no ponteiro [0, len-1] - igual fold do sistema musical.

INVENTARIO (id "INF", display "∞"):
  Sempre acessivel como CAMADA DE FUNDO. Vaza palavras-semente pro grid
  64x64 do visualizer mesmo quando outro capitulo eh o ativo.

BUGS PROGRESSIVOS:
  A cada volta completa do texto (cycle_count++), pequenas mutacoes
  deterministicas de letra sao introduzidas. Simula degradacao analogica
  textual - igual a degradacao dos ecos no SC.

OBS: Os textos comecam vazios (placeholder ""). Quando o usuario fornecer
o conteudo do livro, basta chamar set_texto(id, texto) ou registrar via
load_textos(dict).
"""

import math
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# Fix terminal encoding for Windows (igual nucleo_compositor.py)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")


# Id especial do Inventario (display: "∞")
INFINITY_ID = "INF"


# =============================================================================
# ESTRUTURA DOS CAPITULOS
# =============================================================================

@dataclass
class Capitulo:
    """Um capitulo (ou subcapitulo) do livro."""
    id: str                  # "0", "1", "4.1", "12.6", "INF"
    nome: str
    parent: Optional[str] = None     # id do capitulo pai (subcapitulo)
    attractor: str = "neutro"        # nome do atrator visual (vai pro grid)
    texto: str = ""                  # placeholder ate o usuario fornecer

    @property
    def display_id(self) -> str:
        return "∞" if self.id == INFINITY_ID else self.id


# Ordem oficial do livro - mantida pra exibicao e navegacao
CHAPTER_ORDER: List[str] = [
    "0",
    "1", "2", "3",
    "4", "4.1", "4.2", "4.3",
    "5", "6", "7", "8",
    "9", "9.1",
    "10", "11",
    "12", "12.1", "12.2", "12.3", "12.4", "12.5", "12.6",
    INFINITY_ID,
]

CAPITULOS: Dict[str, Capitulo] = {}


def _add(cid: str, nome: str, parent: Optional[str] = None, attractor: str = "neutro"):
    CAPITULOS[cid] = Capitulo(id=cid, nome=nome, parent=parent, attractor=attractor)


# Constroi o livro inteiro
_add("0",       "Prólogo",                                attractor="prologo")
_add("1",       "A página",                               attractor="pagina")
_add("2",       "A cama",                                 attractor="cama")
_add("3",       "O quarto",                               attractor="quarto")
_add("4",       "O apartamento",                          attractor="apartamento")
_add("4.1",     "Portas",                  parent="4",    attractor="porta")
_add("4.2",     "Escadas",                 parent="4",    attractor="escada")
_add("4.3",     "Paredes",                 parent="4",    attractor="parede")
_add("5",       "O prédio",                               attractor="predio")
_add("6",       "A rua",                                  attractor="rua")
_add("7",       "O bairro",                               attractor="bairro")
_add("8",       "A cidade",                               attractor="cidade")
_add("9",       "O campo",                                attractor="campo")
_add("9.1",     "Sobre o movimento",       parent="9",    attractor="movimento")
_add("10",      "O país",                                 attractor="pais")
_add("11",      "O mundo",                                attractor="mundo")
_add("12",      "O espaço",                               attractor="espaco")
_add("12.1",    "Sobre as linhas retas",   parent="12",   attractor="linhas_retas")
_add("12.2",    "Medidas",                 parent="12",   attractor="medidas")
_add("12.3",    "Brincar com o espaço",    parent="12",   attractor="brincar")
_add("12.4",    "A conquista do espaço",   parent="12",   attractor="conquista")
_add("12.5",    "O inabitável",            parent="12",   attractor="inabitavel")
_add("12.6",    "O espaço (cont. e fim)",  parent="12",   attractor="fim")
_add(INFINITY_ID, "Inventário",                           attractor="inventario")


# =============================================================================
# TEXTOS DOS CAPITULOS (vazios por padrao - usuario fornece via set_texto /
# load_textos quando tiver o Perec real). O INVENTARIO eh o unico que ja
# carrega palavras-semente — eh o capitulo sempre-acessivel.
# Sem texto: fragmento_para_eco/frase_para_recitativo retornam "" e nenhuma
# voz sai do SC pra aquele capitulo (so o vibrafone toca).
# =============================================================================

_TEXTOS_DEFAULT = {
    INFINITY_ID: (
        "Adler Larry. Agenda. Alfafa. Alma. Almofada. Alpinista. "
        "Amarelo. Amiens. Angostura. Área de serviço. Areias de "
        "Beauchamp. Avery Tex. Avião. Página. Cama. Quarto. "
        "Apartamento. Porta. Escada. Parede. Prédio. Rua. Bairro. "
        "Cidade. Campo. Movimento. País. Mundo. Espaço. Linha. "
        "Medida. Brincar. Conquista. Inabitável. Fim."
    ),
}

for _cid, _txt in _TEXTOS_DEFAULT.items():
    if _cid in CAPITULOS:
        CAPITULOS[_cid].texto = _txt


# =============================================================================
# IDIOMA POR PALAVRA (chave normalizada -> 'pt' | 'en' | 'fr' | ...)
# Default eh 'pt'. Lista so o que NAO eh portugues. TTS le isso pra
# escolher voz SAPI (Maria=pt, Zira=en).
# =============================================================================

WORD_LANG: Dict[str, str] = {
    # Ingles
    "adler": "en",
    "larry": "en",
    "avery": "en",
    "tex":   "en",
    # Frances - nao temos voz SAPI fr instalada; o TTS aplica fallback
    # via WORD_TTS_OVERRIDE abaixo (Maria com grafia foneticamente
    # aproximada). Mantemos o lang='fr' pra metadados futuros (ex:
    # instalar Hortense e re-renderizar).
    "amiens":    "fr",
    "beauchamp": "fr",
}


# Substituicao de TEXTO PASSADO PRO TTS (chave normalizada -> grafia
# alternativa). A CHAVE/lookup continua sendo a normalizada do original
# ('amiens', 'beauchamp'), mas o que vai pro SAPI eh a transliteracao
# foneticamente aproximada. Visualizer continua mostrando o original.
WORD_TTS_OVERRIDE: Dict[str, str] = {
    "amiens":    "amiã",      # /a.mjɛ̃/ aprox em pt-br
    "beauchamp": "bochã",     # /bo.ʃɑ̃/ aprox em pt-br
}


def word_lang(key: str) -> str:
    """Idioma de uma palavra (chave normalizada). Default 'pt'."""
    return WORD_LANG.get(key, "pt")


def word_tts_input(key: str, raw: str) -> str:
    """
    Texto a passar pro TTS pra essa palavra. Usa WORD_TTS_OVERRIDE
    quando definido (ex: francês transliterado), senão o raw original.
    """
    return WORD_TTS_OVERRIDE.get(key, raw)


# =============================================================================
# ESTADO GLOBAL (capitulo atual + ponteiro no texto + ciclos)
# =============================================================================

# Comeca no Prologo (id "0")
_state = {
    "current_id": "0",
    "pointer": 0,          # posicao corrente no texto do capitulo atual
    "cycle_count": 0,      # quantas voltas no texto (controla mutacao)
}

# Listeners pra notificar mudanca de capitulo (ex: visualizer SSE)
_listeners: List[Callable[[Capitulo], None]] = []


def on_change(cb: Callable[[Capitulo], None]) -> None:
    """Registra callback que recebe o Capitulo novo a cada mudanca."""
    _listeners.append(cb)


def _notify():
    cap = get_capitulo()
    for cb in list(_listeners):
        try:
            cb(cap)
        except Exception:
            pass


def get_capitulo() -> Capitulo:
    """Capitulo atualmente selecionado."""
    return CAPITULOS[_state["current_id"]]


def set_capitulo(cid: str) -> bool:
    """Troca o capitulo atual. Reseta ponteiro/ciclo. Retorna True se ok."""
    if cid not in CAPITULOS:
        return False
    if cid == _state["current_id"]:
        return True
    _state["current_id"] = cid
    _state["pointer"] = 0
    _state["cycle_count"] = 0
    _notify()
    return True


def list_capitulos() -> List[Capitulo]:
    """Lista os capitulos na ordem oficial do livro."""
    return [CAPITULOS[cid] for cid in CHAPTER_ORDER if cid in CAPITULOS]


def set_texto(cid: str, texto: str) -> bool:
    """Define o texto-fonte de um capitulo."""
    if cid not in CAPITULOS:
        return False
    CAPITULOS[cid].texto = texto or ""
    return True


def load_textos(textos: Dict[str, str]) -> int:
    """
    Carrega textos em batch. Aceita dict {id: texto}.
    Retorna numero de capitulos atualizados.
    """
    n = 0
    for cid, txt in (textos or {}).items():
        if set_texto(cid, txt):
            n += 1
    return n


def estado_resumo() -> Dict:
    """Estado atual em formato serializavel (debug + SSE)."""
    cap = get_capitulo()
    return {
        "capitulo_id": cap.id,
        "capitulo_display": cap.display_id,
        "capitulo_nome": cap.nome,
        "attractor": cap.attractor,
        "pointer": _state["pointer"],
        "cycle": _state["cycle_count"],
        "texto_len": len(cap.texto),
    }


# =============================================================================
# OPERACOES DETERMINISTICAS (espelham as do sistema musical)
# =============================================================================

def fold_pointer(p: int, hi: int) -> int:
    """Fold de ponteiro em [0, hi] (igual nucleo_compositor.fold_range, range [0,hi])."""
    if hi <= 0:
        return 0
    span = hi
    period = 2 * span
    shifted = p % period
    if shifted < 0:
        shifted += period
    if shifted > span:
        shifted = period - shifted
    return shifted


def _gcd(a: int, b: int) -> int:
    if a == 0 and b == 0:
        return 0
    return math.gcd(abs(a), abs(b))


def _lcm(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    if a == 0 or b == 0:
        return 0
    g = math.gcd(a, b)
    return a * b // g


def aplicar_operacao_naipe(pointer: int, carta_mag: int, suit: str, texto_len: int) -> int:
    """
    Aplica a operacao do naipe no ponteiro do texto.

    Naipes seguem as MESMAS operacoes do sistema musical:
        COPAS  (+):    avanca (pointer + carta_mag)
        OUROS  (-):    recua  (pointer - carta_mag)
        ESPADAS (lcm): salta esparso (pointer + lcm)
        PAUS   (gcd):  contrai (vai ate gcd)
    Resultado eh "folded" em [0, texto_len-1] pra simular ping-pong textual.

    carta_mag eh magnitude (>=1) - sinal do naipe ja determina a direcao.
    """
    if texto_len <= 1:
        return 0
    v = max(1, abs(carta_mag))
    suit_up = (suit or "").upper()
    if suit_up == "COPAS":
        novo = pointer + v
    elif suit_up == "OUROS":
        novo = pointer - v
    elif suit_up == "ESPADAS":
        salto = _lcm(max(1, pointer), v) or v
        # garantir progressao (lcm pode ser igual a pointer se v divide)
        novo = pointer + max(salto, v)
    elif suit_up == "PAUS":
        # contracao: gcd(pointer, v) puxa pra perto da origem
        novo = _gcd(pointer, v)
    else:
        novo = pointer + v
    return fold_pointer(novo, texto_len - 1)


def janela_por_figura(carta_type: str, tamanho: int) -> Tuple[int, str]:
    """
    J/Q/K controlam direcao/janela de leitura:
        J (passado)  -> modo "retrogrado": le de tras pra frente
        Q (presente) -> modo "presente"  : ordem normal
        K (futuro)   -> modo "futuro"    : projeta um pedaco a frente
    Cartas numericas -> "normal".
    Retorna (offset_adicional, modo).
    """
    t = (carta_type or "").upper()
    if t == "J":
        return (0, "retrogrado")
    if t == "Q":
        return (0, "presente")
    if t == "K":
        return (tamanho, "futuro")
    return (0, "normal")


def mutar(texto: str, cycle: int) -> str:
    """
    "Buga" o texto a cada volta do ciclo - deterministico mas crescente.
    cycle=0 -> sem mutacao. cycle alto -> ate ~10% das letras viram vizinhas.
    """
    if cycle <= 0 or not texto:
        return texto
    rate = min(0.10, cycle * 0.012)
    out = []
    for i, ch in enumerate(texto):
        h = hash((i, cycle)) & 0xFFFF
        if (h / 0xFFFF) < rate and ch.isalpha():
            offset = (h % 3) - 1
            if offset == 0:
                offset = 1
            new_code = ord(ch) + offset
            if ch.isupper():
                base = ord("A")
                new_code = base + (new_code - base) % 26
            else:
                base = ord("a")
                new_code = base + (new_code - base) % 26
            out.append(chr(new_code))
        else:
            out.append(ch)
    return "".join(out)


# =============================================================================
# EXTRACAO DE FRAGMENTOS (delays) E FRASES (recitativo)
# =============================================================================

def _resolve_carta(card) -> Tuple[str, str, int]:
    """
    Normaliza um card em (type, suit, magnitude).
    Aceita Card (nucleo_compositor), dict {'type', 'suit'}, ou tupla (type, suit).
    """
    if card is None:
        return ("?", "COPAS", 1)
    if isinstance(card, dict):
        ctype = str(card.get("type", "?"))
        suit = str(card.get("suit", "COPAS"))
    elif isinstance(card, tuple):
        ctype = str(card[0])
        suit = str(card[1])
    else:
        # Card do nucleo_compositor: .type (str), .suit (Enum com .value)
        ctype = getattr(card, "type", "?")
        s = getattr(card, "suit", None)
        suit = getattr(s, "value", str(s)) if s is not None else "COPAS"

    if ctype == "A":
        mag = 1
    elif ctype == "10":
        mag = 10
    elif ctype in ("J", "Q", "K"):
        mag = 11 if ctype == "J" else (12 if ctype == "Q" else 13)
    else:
        try:
            mag = int(ctype)
        except (TypeError, ValueError):
            mag = 1
    return (str(ctype).upper(), str(suit).upper(), mag)


def _tamanho_fragmento(carta_type: str) -> int:
    """Tamanho base do FRAGMENTO (curto, pra eco). Cartas mais altas = pedaco maior."""
    t = carta_type.upper()
    if t == "A":
        return 0
    if t == "10":
        return 7
    if t in ("J", "Q", "K"):
        return {"J": 4, "Q": 6, "K": 8}[t]
    try:
        n = int(t)
        return max(1, min(n, 10))
    except ValueError:
        return 3


def _tamanho_frase(carta_type: str) -> int:
    """Tamanho base da FRASE (longa, pra recitativo de fermata)."""
    t = carta_type.upper()
    if t == "10":
        return 90
    if t in ("J", "Q", "K"):
        return {"J": 60, "Q": 75, "K": 110}[t]
    try:
        n = int(t)
        return 30 + n * 8
    except ValueError:
        return 60


def fragmento_para_eco(card, eco_idx: int = 0) -> str:
    """
    Fragmento CURTO (poucas letras/silabas) pra um eco.

    Para uma mesma nota, eco_idx 0..5 entrega fatias DIFERENTES (cada
    eco fala uma coisa diferente). Avanca o ponteiro global so uma vez
    por nota (no eco_idx=0) pra nao "comer" texto rapido demais.
    """
    cap = get_capitulo()
    texto = cap.texto or ""
    if not texto:
        return ""
    texto = mutar(texto, _state["cycle_count"])
    n = len(texto)
    if n <= 1:
        return texto

    ctype, suit, mag = _resolve_carta(card)
    if ctype == "A":
        return ""  # As = silencio textual

    tamanho_base = _tamanho_fragmento(ctype)
    tamanho = max(1, min(tamanho_base + eco_idx, 14))

    # Aplica operacao do naipe + offset por eco_idx (cada eco le um deslocamento)
    p = aplicar_operacao_naipe(_state["pointer"], mag, suit, n)
    p = (p + eco_idx * max(1, tamanho_base // 2)) % n

    extra_offset, modo = janela_por_figura(ctype, tamanho)
    p = (p + extra_offset) % n

    if modo == "retrogrado":
        ini = max(0, p - tamanho)
        fim = p
    else:
        ini = p
        fim = min(n, p + tamanho)

    # Snap pra palavras inteiras: ini volta ate inicio-de-palavra, fim avanca
    # ate o proximo espaco. Sem isso a voz fala fatias mid-palavra ("screv",
    # "agin") que soam como gibberish, mesmo com fonemas corretos.
    while ini > 0 and not texto[ini - 1].isspace():
        ini -= 1
    while fim < n and not texto[fim - 1].isspace():
        fim += 1

    slc = texto[ini:fim].strip()
    if modo == "retrogrado":
        # Retrograde agora opera na ORDEM das palavras (cada palavra legivel,
        # sequencia invertida). Letras invertidas viravam ruido sem semantica.
        slc = " ".join(slc.split()[::-1])

    # Avanca ponteiro global so no primeiro eco (evita corrida)
    if eco_idx == 0:
        novo = p + max(1, tamanho_base // 2)
        if novo >= n:
            _state["cycle_count"] += 1
            novo = novo % n
        _state["pointer"] = novo

    return slc


def frase_para_recitativo(card) -> str:
    """
    Frase LONGA pra recitativo de fermata. Tenta estender ate uma pontuacao
    proxima (vira frase "completa" em vez de cortar no meio).
    """
    cap = get_capitulo()
    texto = cap.texto or ""
    if not texto:
        return ""
    texto = mutar(texto, _state["cycle_count"])
    n = len(texto)
    if n <= 1:
        return texto

    ctype, suit, mag = _resolve_carta(card)
    tamanho = min(_tamanho_frase(ctype), n)

    p = aplicar_operacao_naipe(_state["pointer"], mag, suit, n)
    ini = p
    fim = min(n, p + tamanho)

    # Estende ate pontuacao proxima (.!? ou \n), pra fechar frase
    extended = fim
    for j in range(fim, min(n, fim + 60)):
        if texto[j] in ".!?\n":
            extended = j + 1
            break

    slc = texto[ini:extended].strip()
    novo = extended
    if novo >= n:
        _state["cycle_count"] += 1
        novo = novo % n
    _state["pointer"] = novo
    return slc


def palavra_inventario(idx_shift: int = 0) -> str:
    """
    Sempre-acessivel. Retorna uma palavra do Inventario (∞), independente
    do capitulo ativo. Usado pra "vazar" palavras-semente no grid.
    idx_shift permite escolher palavras diferentes na mesma chamada.
    """
    inv = CAPITULOS[INFINITY_ID]
    if not inv.texto:
        return ""
    palavras = [w.strip(".,;:!?\"'()[]") for w in inv.texto.split()]
    palavras = [w for w in palavras if len(w) >= 3]
    if not palavras:
        return ""
    idx = (_state["pointer"] + _state["cycle_count"] * 7 + idx_shift) % len(palavras)
    return palavras[idx]


# =============================================================================
# DEMO STANDALONE
# =============================================================================

def _demo():
    """Demo rapido: carrega texto fake no Prologo e mostra fatiamento."""
    set_texto("0",
        "Eu escrevo: habito esta pagina, este folha, esta linha. "
        "Habito o quarto onde estou. Habito a cama, habito o sono. "
        "Habito os livros que leio, as palavras que escolho.")
    set_texto(INFINITY_ID,
        "cama quarto porta escada parede predio rua bairro cidade campo pais "
        "mundo espaco linha medida brincar conquistar inabitavel pagina")

    print("CAPITULOS:")
    for cap in list_capitulos():
        ind = "  " if cap.parent else ""
        print(f"  {ind}{cap.display_id:>6}  {cap.nome:<32}  [{cap.attractor}]")
    print()

    print("DEMO PICOTAMENTO (capitulo 0 = Prologo):")
    print(f"  texto: {CAPITULOS['0'].texto!r}")
    print()
    cards = [
        {"type": "5", "suit": "COPAS"},
        {"type": "K", "suit": "ESPADAS"},
        {"type": "J", "suit": "OUROS"},
        {"type": "10", "suit": "PAUS"},
        {"type": "Q", "suit": "COPAS"},
        {"type": "3", "suit": "PAUS"},
    ]
    for c in cards:
        for eco in range(3):
            frag = fragmento_para_eco(c, eco_idx=eco)
            print(f"  [{c['type']:>2}/{c['suit'][:3]:>3} eco={eco}] '{frag}'")
        print()

    print(f"  Estado: {estado_resumo()}")
    print()
    print("DEMO RECITATIVO:")
    rec = frase_para_recitativo({"type": "10", "suit": "OUROS"})
    print(f"  '{rec}'")
    print()
    print(f"DEMO INVENTARIO: '{palavra_inventario()}', '{palavra_inventario(1)}', '{palavra_inventario(3)}'")


if __name__ == "__main__":
    _demo()
