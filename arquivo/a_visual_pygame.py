"""
Visualizador Pygame do Sistema Baralho Musical.

Acompanha passo-a-passo a transformacao de cartas em parametros musicais.
- Tela cheia (Esc encerra).
- Composicao infinita: cresce ate o usuario parar.
- 2 coringas no baralho: resetam o interpretador (E=0) e reembaralham.
- Cartas incompativeis (Paus com E_anterior = 0 -> div por zero)
  sao descartadas e a proxima carta entra no lugar.
- J/Q/K nunca sao incompativeis: caem na identidade do naipe quando
  nao ha valor a herdar.
- Setas <-/-> ou botoes para navegar. Avancar alem do ultimo gera proximo passo.
- Botao Salvar grava a sessao em JSON na pasta sessoes/.
- Botao Historico abre lista de sessoes salvas para reabrir.
"""

import json
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

import pygame

from nucleo_compositor import (
    CARD_TYPES,
    PARAM_RITMO,
    PARAMETERS,
    SUIT_IDENTITY,
    SUIT_INFO,
    Card,
    InterpretadorEventos,
    Note,
    NoteParameter,
    ProcessResult,
    Suit,
    apply_param_mirror,
    fold_range,
    get_card_numeric_value,
    map_event_to_integer,
    map_event_to_param,
    nearest_value,
)

SESSION_FORMAT_VERSION = 3

# ---------------------------------------------------------------------------
# Config (WIDTH/HEIGHT sao redefinidos em main() conforme display real)
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 800
FPS = 60
HERE = os.path.dirname(os.path.abspath(__file__))
SESSOES_DIR = os.path.join(HERE, "sessoes")

# ---------------------------------------------------------------------------
# Paleta Claude Code (light theme)
# ---------------------------------------------------------------------------
BG          = (250, 249, 245)   # creme / off-white
PANEL       = (244, 241, 233)   # creme um pouco mais escuro
PANEL_HI    = (234, 229, 218)
BORDER      = (210, 203, 188)
TEXT        = (45, 42, 38)      # warm near-black
TEXT_DIM    = (130, 124, 112)
ACCENT      = (217, 119, 87)    # terracotta (Anthropic)
ACCENT_DIM  = (180, 95, 70)
ACCENT_SOFT = (240, 215, 200)
RED         = (192, 50, 60)
BLACK_INK   = (40, 38, 35)
CARD_BG     = (253, 251, 246)
CARD_BACK_A = (217, 119, 87)
CARD_BACK_B = (180, 95, 70)
BTN         = (236, 231, 220)
BTN_HOV     = (245, 240, 228)
BTN_DIS     = (222, 217, 206)
OK_GREEN    = (90, 140, 95)
OK_GREEN_BG = (220, 232, 218)
WARN        = (200, 140, 50)
WARN_BG     = (245, 232, 205)
JOKER_GOLD  = (192, 152, 60)
SHADOW      = (210, 200, 185)
# Articulacao (gramatica fermata + ligaduras)
FERMATA_FG  = (160, 105, 60)    # bronze
FERMATA_BG  = (245, 228, 200)
TIE_FG      = (110, 90, 160)    # roxo
TIE_BG      = (228, 220, 240)

SUIT_GLYPH = {
    Suit.PAUS:    "♣",  # paus
    Suit.OUROS:   "♦",  # ouros
    Suit.COPAS:   "♥",  # copas
    Suit.ESPADAS: "♠",  # espadas
}

OP_SYMBOL = {
    Suit.PAUS: "gcd",
    Suit.OUROS: "-",
    Suit.COPAS: "+",
    Suit.ESPADAS: "lcm",
}


# ---------------------------------------------------------------------------
# Modelo do baralho com coringas
# ---------------------------------------------------------------------------

@dataclass
class CardX:
    """Carta estendida que tambem suporta coringa."""
    type: str             # 'A','2'..'10','J','Q','K' ou 'JOKER'
    suit: Optional[Suit]  # None para coringa
    is_joker: bool = False

    def is_action(self) -> bool:
        return self.type in ("J", "Q", "K")

    def is_ace(self) -> bool:
        return self.type == "A"


def build_deck_with_jokers() -> List[CardX]:
    deck: List[CardX] = []
    for suit in Suit:
        for t in CARD_TYPES:
            deck.append(CardX(type=t, suit=suit))
    deck.append(CardX(type="JOKER", suit=None, is_joker=True))
    deck.append(CardX(type="JOKER", suit=None, is_joker=True))
    return deck


def card_to_core(c: CardX) -> Card:
    """Converte CardX (nao-coringa) para Card original usado pelo interpretador."""
    assert not c.is_joker
    return Card(type=c.type, suit=c.suit)


# ---------------------------------------------------------------------------
# Compatibilidade da carta com o estado atual
# ---------------------------------------------------------------------------

def motivo_incompatibilidade(card: CardX, interp: InterpretadorEventos) -> Optional[str]:
    """
    Retorna o motivo se a carta nao pode ser processada agora, ou None.

    Na nova semantica J/Q/K nunca sao incompativeis (caem em identidade do naipe).
    A unica incompatibilidade restante e divisao por zero: Paus com E_anterior = 0.
    """
    if card.is_joker:
        return None
    e_anterior = interp.event_history[-1] if interp.event_history else 0.0
    if card.suit == Suit.PAUS and abs(e_anterior) < 1e-9:
        return "Paus = divisao e E_anterior = 0 -> divisao por zero"
    return None


# ---------------------------------------------------------------------------
# Snapshot de cada passo (estado completo apos o passo)
# ---------------------------------------------------------------------------

@dataclass
class Detalhe:
    """Detalhes do calculo de um passo 'normal', so para exibicao."""
    valor_carta: float
    valor_carta_origem: str
    e_anterior: float
    action_label: str           # 'passado' | 'presente' | 'futuro' | 'numero'
    op_symbol: str
    op_name: str
    event_value: float
    int_event: int
    mapped_param_name: str
    mapped_key: int             # KEY final (depois do espelho se aplicavel)
    mapped_value: Any           # valor final
    nota_finalizada: bool
    mirror_applied: bool = False
    pre_mirror_key: Optional[int] = None
    pre_mirror_value: Any = None
    next_card_preview: Optional[dict] = None   # so para K, registro do peek
    # Triggers de articulacao disparados NESTE passo
    fired_fermata: bool = False         # carta == '10'
    fired_tie_backward: bool = False    # int_event == -1
    fired_tie_forward: bool = False     # int_event == +1


@dataclass
class Snapshot:
    idx: int
    tipo: str  # 'inicio' | 'normal' | 'descarte' | 'coringa'
    card: Optional[CardX]
    motivo_descarte: Optional[str]
    detalhe: Optional[Detalhe]
    # Estado APOS este passo:
    event_history: List[float]
    previous_card_value: Optional[int]
    previous_card: Optional[CardX]
    deck_remaining: List[CardX]
    current_note_params: List[NoteParameter]
    current_note_has_ace: bool
    notas_completas: List[Note]
    # Flags acumuladas para a nota em construcao (resetam quando a nota fecha)
    current_note_fermata: bool = False
    current_note_tie_backward: bool = False
    current_note_tie_forward: bool = False


# ---------------------------------------------------------------------------
# Engine: gera/navega snapshots
# ---------------------------------------------------------------------------

class Engine:
    def __init__(self):
        self.session_started_at = datetime.now().isoformat(timespec="seconds")
        self.snapshots: List[Snapshot] = []
        self.cursor: int = 0
        self._init_snapshot()

    def _init_snapshot(self):
        deck = build_deck_with_jokers()
        random.shuffle(deck)
        snap = Snapshot(
            idx=0,
            tipo="inicio",
            card=None,
            motivo_descarte=None,
            detalhe=None,
            event_history=[0.0],
            previous_card_value=None,
            previous_card=None,
            deck_remaining=deck,
            current_note_params=[],
            current_note_has_ace=False,
            notas_completas=[],
        )
        self.snapshots = [snap]
        self.cursor = 0

    @property
    def atual(self) -> Snapshot:
        return self.snapshots[self.cursor]

    def can_back(self) -> bool:
        return self.cursor > 0

    def back(self):
        if self.can_back():
            self.cursor -= 1

    def forward(self):
        if self.cursor < len(self.snapshots) - 1:
            self.cursor += 1
        else:
            self._gerar_proximo()
            self.cursor = len(self.snapshots) - 1

    def _restore_interp(self, snap: Snapshot) -> InterpretadorEventos:
        interp = InterpretadorEventos()
        interp.event_history = list(snap.event_history)
        interp.previous_card_value = snap.previous_card_value
        if snap.previous_card is not None and not snap.previous_card.is_joker:
            interp.previous_card = card_to_core(snap.previous_card)
        else:
            interp.previous_card = None
        return interp

    def _gerar_proximo(self):
        atual = self.atual
        # Copia estado mutavel
        deck = list(atual.deck_remaining)
        interp = self._restore_interp(atual)
        cur_params = list(atual.current_note_params)
        cur_ace = atual.current_note_has_ace
        cur_fermata = atual.current_note_fermata
        cur_tie_b = atual.current_note_tie_backward
        cur_tie_f = atual.current_note_tie_forward
        notas = list(atual.notas_completas)
        prev_card_x = atual.previous_card

        # Garante baralho nao vazio (baralho vazio reembaralha automaticamente)
        if not deck:
            deck = build_deck_with_jokers()
            random.shuffle(deck)

        card = deck.pop(0)
        novo_idx = len(self.snapshots)

        if card.is_joker:
            # CORINGA: reset interpretador, reembaralha. Notas geradas permanecem.
            interp.reset()
            cur_params = []
            cur_ace = False
            cur_fermata = False
            cur_tie_b = False
            cur_tie_f = False
            deck = build_deck_with_jokers()
            random.shuffle(deck)
            snap = Snapshot(
                idx=novo_idx,
                tipo="coringa",
                card=card,
                motivo_descarte=None,
                detalhe=None,
                event_history=list(interp.event_history),
                previous_card_value=interp.previous_card_value,
                previous_card=None,
                deck_remaining=deck,
                current_note_params=cur_params,
                current_note_has_ace=cur_ace,
                notas_completas=notas,
                current_note_fermata=cur_fermata,
                current_note_tie_backward=cur_tie_b,
                current_note_tie_forward=cur_tie_f,
            )
            self.snapshots.append(snap)
            return

        motivo = motivo_incompatibilidade(card, interp)
        if motivo is not None:
            # Descarta: estado interpretador/nota nao mudam; baralho diminui.
            snap = Snapshot(
                idx=novo_idx,
                tipo="descarte",
                card=card,
                motivo_descarte=motivo,
                detalhe=None,
                event_history=list(interp.event_history),
                previous_card_value=interp.previous_card_value,
                previous_card=prev_card_x,
                deck_remaining=deck,
                current_note_params=cur_params,
                current_note_has_ace=cur_ace,
                notas_completas=notas,
                current_note_fermata=cur_fermata,
                current_note_tie_backward=cur_tie_b,
                current_note_tie_forward=cur_tie_f,
            )
            self.snapshots.append(snap)
            return

        # Carta normal: processa via interpretador
        param_idx = len(cur_params)
        e_anterior_antes = interp.event_history[-1]

        # Peek do futuro (so importa pra K, mas pega sempre pro display)
        next_card_x = deck[0] if deck else None
        next_card_core: Optional[Card] = None
        if next_card_x is not None and not next_card_x.is_joker:
            next_card_core = card_to_core(next_card_x)

        result: ProcessResult = interp.process_card(card_to_core(card), next_card_core)
        int_event = map_event_to_integer(result.event_value)

        # Gramatica de articulacao - triggers DESTE passo (acumulam na nota)
        fired_fermata = (card.type == "10")
        fired_tie_b = (int_event == -1)
        fired_tie_f = (int_event == 1)
        if fired_fermata:
            cur_fermata = True
        if fired_tie_b:
            cur_tie_b = True
        if fired_tie_f:
            cur_tie_f = True

        # Registro de preview do futuro para K (se aplicavel)
        next_preview = None
        if card.type == "K" and next_card_x is not None:
            next_preview = {
                "type": next_card_x.type,
                "suit": next_card_x.suit.value if next_card_x.suit else None,
                "is_joker": next_card_x.is_joker,
            }

        if card.is_ace():
            # AS = PAUSA: define o tamanho da pausa via PARAM_RITMO e encerra a nota.
            # Demais parametros nao se aplicam (pausa nao tem nota/dinamica/etc.).
            # Flags ja disparadas antes (fermata por carta 10, ligaduras por ev=±1)
            # persistem nesta pausa - "hold the silence" e musicalmente valido.
            mapped_key, mapped_value = map_event_to_param(PARAM_RITMO, int_event)
            rest_param = NoteParameter(
                param_name=PARAM_RITMO["name"],
                event_value=int_event,
                mapped_key=mapped_key,
                mapped_value=mapped_value,
            )
            notas.append(Note(
                parameters=[rest_param],
                is_rest=True,
                has_fermata=cur_fermata,
                tie_backward=cur_tie_b,
                tie_forward=cur_tie_f,
            ))
            cur_params = []
            cur_ace = False
            cur_fermata = False
            cur_tie_b = False
            cur_tie_f = False
            nota_finalizada = True

            detalhe = Detalhe(
                valor_carta=result.current_value,
                valor_carta_origem=result.valor_origem,
                e_anterior=e_anterior_antes,
                action_label=result.action_label,
                op_symbol=OP_SYMBOL[card.suit],
                op_name=SUIT_INFO[card.suit]["op_name"],
                event_value=result.event_value,
                int_event=int_event,
                mapped_param_name=PARAM_RITMO["name"],
                mapped_key=mapped_key,
                mapped_value=mapped_value,
                nota_finalizada=True,
                mirror_applied=False,
                pre_mirror_key=None,
                pre_mirror_value=None,
                next_card_preview=next_preview,
                fired_fermata=fired_fermata,
                fired_tie_backward=fired_tie_b,
                fired_tie_forward=fired_tie_f,
            )
        else:
            param = PARAMETERS[param_idx]
            mapped_key, mapped_value = map_event_to_param(param, int_event)
            pre_mirror_key = mapped_key
            pre_mirror_value = mapped_value
            if result.mirror_applied:
                mapped_key, mapped_value = apply_param_mirror(param, mapped_key)

            note_param = NoteParameter(
                param_name=param["name"],
                event_value=int_event,
                mapped_key=mapped_key,
                mapped_value=mapped_value,
            )
            cur_params.append(note_param)

            nota_finalizada = False
            if len(cur_params) == 7:
                notas.append(Note(
                    parameters=cur_params,
                    is_rest=False,
                    has_fermata=cur_fermata,
                    tie_backward=cur_tie_b,
                    tie_forward=cur_tie_f,
                ))
                cur_params = []
                cur_ace = False
                cur_fermata = False
                cur_tie_b = False
                cur_tie_f = False
                nota_finalizada = True

            detalhe = Detalhe(
                valor_carta=result.current_value,
                valor_carta_origem=result.valor_origem,
                e_anterior=e_anterior_antes,
                action_label=result.action_label,
                op_symbol=OP_SYMBOL[card.suit],
                op_name=SUIT_INFO[card.suit]["op_name"],
                event_value=result.event_value,
                int_event=int_event,
                mapped_param_name=param["name"],
                mapped_key=mapped_key,
                mapped_value=mapped_value,
                nota_finalizada=nota_finalizada,
                mirror_applied=result.mirror_applied,
                pre_mirror_key=pre_mirror_key,
                pre_mirror_value=pre_mirror_value,
                next_card_preview=next_preview,
                fired_fermata=fired_fermata,
                fired_tie_backward=fired_tie_b,
                fired_tie_forward=fired_tie_f,
            )
        snap = Snapshot(
            idx=novo_idx,
            tipo="normal",
            card=card,
            motivo_descarte=None,
            detalhe=detalhe,
            event_history=list(interp.event_history),
            previous_card_value=interp.previous_card_value,
            previous_card=card,  # ultima carta processada (incluindo J/Q/K)
            deck_remaining=deck,
            current_note_params=cur_params,
            current_note_has_ace=cur_ace,
            notas_completas=notas,
            current_note_fermata=cur_fermata,
            current_note_tie_backward=cur_tie_b,
            current_note_tie_forward=cur_tie_f,
        )
        self.snapshots.append(snap)

    # ----- persistencia em JSON ---------------------------------------------

    def to_serializable(self) -> dict:
        def card_d(c: Optional[CardX]):
            if c is None:
                return None
            return {
                "type": c.type,
                "suit": c.suit.value if c.suit else None,
                "is_joker": c.is_joker,
            }

        def np_d(p: NoteParameter):
            return {
                "param_name": p.param_name,
                "event_value": p.event_value,
                "mapped_key": p.mapped_key,
                "mapped_value": p.mapped_value,
            }

        def nota_d(n: Note):
            return {
                "is_rest": n.is_rest,
                "has_fermata": n.has_fermata,
                "tie_backward": n.tie_backward,
                "tie_forward": n.tie_forward,
                "summary": n.get_summary(),
                "parameters": [np_d(p) for p in n.parameters],
            }

        def det_d(d: Optional[Detalhe]):
            if d is None:
                return None
            return {
                "valor_carta": d.valor_carta,
                "valor_carta_origem": d.valor_carta_origem,
                "e_anterior": d.e_anterior,
                "action_label": d.action_label,
                "op_symbol": d.op_symbol,
                "op_name": d.op_name,
                "event_value": d.event_value,
                "int_event": d.int_event,
                "mapped_param_name": d.mapped_param_name,
                "mapped_key": d.mapped_key,
                "mapped_value": d.mapped_value,
                "nota_finalizada": d.nota_finalizada,
                "mirror_applied": d.mirror_applied,
                "pre_mirror_key": d.pre_mirror_key,
                "pre_mirror_value": d.pre_mirror_value,
                "next_card_preview": d.next_card_preview,
                "fired_fermata": d.fired_fermata,
                "fired_tie_backward": d.fired_tie_backward,
                "fired_tie_forward": d.fired_tie_forward,
            }

        snaps = []
        for s in self.snapshots:
            snaps.append({
                "idx": s.idx,
                "tipo": s.tipo,
                "card": card_d(s.card),
                "motivo_descarte": s.motivo_descarte,
                "detalhe": det_d(s.detalhe),
                "current_note_params": [np_d(p) for p in s.current_note_params],
                "current_note_has_ace": s.current_note_has_ace,
                "current_note_fermata": s.current_note_fermata,
                "current_note_tie_backward": s.current_note_tie_backward,
                "current_note_tie_forward": s.current_note_tie_forward,
                "notas_completas": [nota_d(n) for n in s.notas_completas],
                "deck_remaining_count": len(s.deck_remaining),
            })
        return {
            "format_version": SESSION_FORMAT_VERSION,
            "session_started_at": self.session_started_at,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "cursor": self.cursor,
            "total_steps": len(self.snapshots),
            "snapshots": snaps,
        }

    def salvar_json(self) -> str:
        os.makedirs(SESSOES_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SESSOES_DIR, f"sessao_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_serializable(), f, ensure_ascii=False, indent=2)
        return path


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

class Fonts:
    def __init__(self, scale: float = 1.0):
        # Texto principal: monospace (Cascadia/JetBrains/Consolas) — estetica Claude Code
        mono = pygame.font.match_font(
            "cascadiamono,cascadiacode,jetbrainsmono,firacode,consolas,couriernew"
        )
        # Naipes precisam de fonte com glifos Unicode
        sym = pygame.font.match_font("segoeuisymbol,segoeui,arialunicodems,arial")

        def s(n: int) -> int:
            return max(10, int(round(n * scale)))

        self.tiny  = pygame.font.Font(mono, s(13))
        self.small = pygame.font.Font(mono, s(16))
        self.med   = pygame.font.Font(mono, s(20))
        self.big   = pygame.font.Font(mono, s(28))
        self.huge  = pygame.font.Font(mono, s(48))
        self.card_small = pygame.font.Font(sym, s(14))
        self.card_med   = pygame.font.Font(sym, s(22))
        self.card_big   = pygame.font.Font(sym, s(38))
        self.card_huge  = pygame.font.Font(sym, s(70))


def draw_text(surf, text, font, color, x, y, center=False, right=False):
    img = font.render(text, True, color)
    r = img.get_rect()
    if center:
        r.center = (x, y)
    elif right:
        r.topright = (x, y)
    else:
        r.topleft = (x, y)
    surf.blit(img, r)
    return r


def draw_panel(surf, rect, title=None, fonts: Optional[Fonts] = None):
    # sombra suave
    shadow = pygame.Rect(rect.x + 2, rect.y + 3, rect.w, rect.h)
    pygame.draw.rect(surf, SHADOW, shadow, border_radius=12)
    pygame.draw.rect(surf, PANEL, rect, border_radius=12)
    pygame.draw.rect(surf, BORDER, rect, width=1, border_radius=12)
    if title and fonts:
        header = pygame.Rect(rect.x, rect.y, rect.w, 30)
        pygame.draw.rect(surf, PANEL_HI, header,
                         border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(surf, BORDER,
                         (rect.x, rect.y + 30), (rect.right - 1, rect.y + 30))
        draw_text(surf, title, fonts.small, ACCENT, rect.x + 12, rect.y + 7)


def card_color_for(suit: Optional[Suit]) -> tuple:
    if suit is None:
        return JOKER_GOLD
    if SUIT_INFO[suit]["color"] == "VERMELHO":
        return RED
    return BLACK_INK


def draw_card(surf, card: Optional[CardX], rect, fonts: Fonts, face_up=True, highlight=False):
    # sombra
    sh = pygame.Rect(rect.x + 2, rect.y + 3, rect.w, rect.h)
    pygame.draw.rect(surf, SHADOW, sh, border_radius=10)

    if not face_up:
        pygame.draw.rect(surf, CARD_BACK_A, rect, border_radius=10)
        pygame.draw.rect(surf, CARD_BACK_B, rect.inflate(-10, -10), border_radius=8)
        pygame.draw.rect(surf, ACCENT_DIM, rect, width=2, border_radius=10)
        return

    pygame.draw.rect(surf, CARD_BG, rect, border_radius=10)
    pygame.draw.rect(surf, ACCENT if highlight else BORDER, rect,
                     width=3 if highlight else 1, border_radius=10)

    if card is None:
        return
    if card.is_joker:
        col = JOKER_GOLD
        img = fonts.card_big.render("JOKER", True, col)
        ir = img.get_rect(center=rect.center)
        surf.blit(img, ir)
        draw_text(surf, "*", fonts.card_med, col, rect.x + 8, rect.y + 6)
        draw_text(surf, "*", fonts.card_med, col,
                  rect.right - 20, rect.bottom - 28)
        return

    col = card_color_for(card.suit)
    glyph = SUIT_GLYPH[card.suit]
    small_w = rect.w < 80
    # Canto superior esquerdo
    draw_text(surf, card.type, fonts.card_small if small_w else fonts.card_med,
              col, rect.x + 8, rect.y + 6)
    draw_text(surf, glyph, fonts.card_small if small_w else fonts.card_med,
              col, rect.x + 8, rect.y + (24 if not small_w else 20))
    # Centro grande naipe
    big_font = fonts.card_huge if rect.w >= 100 else (fonts.card_big if rect.w >= 70 else fonts.card_med)
    img = big_font.render(glyph, True, col)
    ir = img.get_rect(center=rect.center)
    surf.blit(img, ir)
    # Canto inferior direito
    draw_text(surf, card.type, fonts.card_small if small_w else fonts.card_med,
              col, rect.right - 8, rect.bottom - 6 - (40 if not small_w else 32), right=True)
    draw_text(surf, glyph, fonts.card_small if small_w else fonts.card_med,
              col, rect.right - 8, rect.bottom - (26 if not small_w else 22), right=True)


# ---------------------------------------------------------------------------
# Botoes simples
# ---------------------------------------------------------------------------

@dataclass
class Button:
    rect: pygame.Rect
    label: str
    enabled: bool = True
    hovered: bool = False
    primary: bool = False  # destaque com cor de accent

    def draw(self, surf, fonts: Fonts):
        if not self.enabled:
            color = BTN_DIS
            txt_color = TEXT_DIM
            border = BORDER
        elif self.primary:
            color = ACCENT if not self.hovered else (230, 138, 105)
            txt_color = (255, 255, 250)
            border = ACCENT_DIM
        elif self.hovered:
            color = BTN_HOV
            txt_color = TEXT
            border = ACCENT
        else:
            color = BTN
            txt_color = TEXT
            border = BORDER
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, border, self.rect, width=1, border_radius=8)
        draw_text(surf, self.label, fonts.small, txt_color,
                  self.rect.centerx, self.rect.centery, center=True)

    def click_if_hit(self, pos) -> bool:
        return self.enabled and self.rect.collidepoint(pos)


# ---------------------------------------------------------------------------
# Painel Historico (overlay)
# ---------------------------------------------------------------------------

class HistoricoOverlay:
    def __init__(self):
        self.aberto = False
        self.arquivos: List[str] = []
        self.scroll = 0

    def abrir(self):
        self.aberto = True
        self.scroll = 0
        if os.path.isdir(SESSOES_DIR):
            self.arquivos = sorted(
                [f for f in os.listdir(SESSOES_DIR) if f.endswith(".json")],
                reverse=True,
            )
        else:
            self.arquivos = []

    def fechar(self):
        self.aberto = False

    def _panel_rect(self) -> pygame.Rect:
        w = min(900, int(WIDTH * 0.6))
        h = int(HEIGHT * 0.75)
        return pygame.Rect((WIDTH - w) // 2, (HEIGHT - h) // 2, w, h)

    def draw(self, surf, fonts: Fonts):
        if not self.aberto:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((40, 38, 35, 140))
        surf.blit(overlay, (0, 0))
        panel = self._panel_rect()
        draw_panel(surf, panel, "HISTORICO DE SESSOES (clique para abrir, ESC fecha)", fonts)
        y = panel.y + 44
        if not self.arquivos:
            draw_text(surf, "Nenhuma sessao salva ainda.", fonts.med, TEXT_DIM,
                      panel.centerx, panel.centery, center=True)
            return
        visiveis = max(4, (panel.h - 60) // 40)
        for fname in self.arquivos[self.scroll:self.scroll + visiveis]:
            row = pygame.Rect(panel.x + 16, y, panel.w - 32, 32)
            mouse = pygame.mouse.get_pos()
            hov = row.collidepoint(mouse)
            pygame.draw.rect(surf, PANEL_HI if hov else BG, row, border_radius=6)
            pygame.draw.rect(surf, ACCENT if hov else BORDER, row, width=1, border_radius=6)
            draw_text(surf, fname, fonts.small, TEXT, row.x + 12, row.y + 8)
            y += 40

    def file_at(self, pos) -> Optional[str]:
        if not self.aberto:
            return None
        panel = self._panel_rect()
        y = panel.y + 44
        visiveis = max(4, (panel.h - 60) // 40)
        for fname in self.arquivos[self.scroll:self.scroll + visiveis]:
            row = pygame.Rect(panel.x + 16, y, panel.w - 32, 32)
            if row.collidepoint(pos):
                return fname
            y += 40
        return None


# ---------------------------------------------------------------------------
# Carrega sessao salva (modo leitura)
# ---------------------------------------------------------------------------

class SessaoCarregada:
    """Snapshot visualizador read-only de uma sessao JSON salva."""
    def __init__(self, data: dict):
        self.data = data
        self.cursor = 0
        self.snaps = data["snapshots"]

    def can_back(self): return self.cursor > 0
    def can_forward(self): return self.cursor < len(self.snaps) - 1
    def back(self):
        if self.can_back(): self.cursor -= 1
    def forward(self):
        if self.can_forward(): self.cursor += 1
    @property
    def atual(self): return self.snaps[self.cursor]
    @property
    def total(self): return len(self.snaps)


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

class App:
    def __init__(self, fullscreen: bool = True):
        global WIDTH, HEIGHT
        pygame.init()
        pygame.display.set_caption("Baralho Musical - Visualizador")
        if fullscreen:
            info = pygame.display.Info()
            WIDTH, HEIGHT = info.current_w, info.current_h
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else:
            WIDTH, HEIGHT = 1400, 880
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.fullscreen = fullscreen
        self.clock = pygame.time.Clock()
        # Escala de fonte proporcional a altura (1.0 a 1.35 entre 800 e 1440px)
        scale = max(1.0, min(1.4, HEIGHT / 800.0))
        self.fonts = Fonts(scale=scale)
        self.engine = Engine()
        self.historico = HistoricoOverlay()
        self.sessao_carregada: Optional[SessaoCarregada] = None
        self.mensagem = ""
        self.mensagem_until = 0
        self.auto_play = False
        self.auto_play_last = 0

        self._build_buttons()

    def _build_buttons(self):
        bh = 40
        bw = 130
        margin = 24
        # Header (canto direito): Nova | Salvar | Historico | Sair
        right = WIDTH - margin
        self.btn_sair    = Button(pygame.Rect(right - bw, margin, bw, bh), "Sair")
        right -= bw + 10
        self.btn_hist    = Button(pygame.Rect(right - bw, margin, bw, bh), "Historico")
        right -= bw + 10
        self.btn_salvar  = Button(pygame.Rect(right - bw, margin, bw, bh), "Salvar")
        right -= bw + 10
        self.btn_nova    = Button(pygame.Rect(right - bw, margin, bw, bh), "Nova")

        # Footer: < Voltar | Auto-play | Avancar >
        fy = HEIGHT - bh - margin
        self.btn_back   = Button(pygame.Rect(margin, fy, bw + 20, bh), "< Voltar")
        self.btn_auto   = Button(pygame.Rect(WIDTH // 2 - (bw + 20) // 2, fy, bw + 20, bh), "Auto-play")
        self.btn_fwd    = Button(pygame.Rect(WIDTH - margin - bw - 20, fy, bw + 20, bh),
                                 "Avancar >", primary=True)

    def flash(self, msg: str, dur_ms=2500):
        self.mensagem = msg
        self.mensagem_until = pygame.time.get_ticks() + dur_ms

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def handle_events(self):
        mouse = pygame.mouse.get_pos()
        for b in (self.btn_back, self.btn_fwd, self.btn_auto,
                  self.btn_salvar, self.btn_hist, self.btn_nova, self.btn_sair):
            b.hovered = b.rect.collidepoint(mouse)

        if self.sessao_carregada is not None:
            self.btn_back.enabled = self.sessao_carregada.can_back()
            self.btn_fwd.enabled = self.sessao_carregada.can_forward()
            self.btn_salvar.enabled = False
            self.btn_auto.enabled = False
        else:
            self.btn_back.enabled = self.engine.can_back()
            self.btn_fwd.enabled = True
            self.btn_salvar.enabled = True
            self.btn_auto.enabled = True

        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if evt.type == pygame.KEYDOWN:
                if self.historico.aberto:
                    if evt.key == pygame.K_ESCAPE:
                        self.historico.fechar()
                    continue
                if evt.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_SPACE):
                    self._forward()
                elif evt.key in (pygame.K_LEFT, pygame.K_a):
                    self._back()
                elif evt.key == pygame.K_s:
                    self._salvar()
                elif evt.key == pygame.K_h:
                    self.historico.abrir()
                elif evt.key == pygame.K_n:
                    self._nova()
                elif evt.key == pygame.K_p:
                    self.auto_play = not self.auto_play
                elif evt.key == pygame.K_ESCAPE:
                    if self.sessao_carregada is not None:
                        self.sessao_carregada = None
                        self.flash("Voltou para a sessao ativa")
                    else:
                        pygame.quit()
                        sys.exit(0)
            if evt.type == pygame.MOUSEBUTTONDOWN and evt.button == 1:
                if self.historico.aberto:
                    fname = self.historico.file_at(evt.pos)
                    if fname is not None:
                        self._carregar(fname)
                        self.historico.fechar()
                    else:
                        panel = self.historico._panel_rect()
                        if not panel.collidepoint(evt.pos):
                            self.historico.fechar()
                    continue
                if self.btn_back.click_if_hit(evt.pos):
                    self._back()
                elif self.btn_fwd.click_if_hit(evt.pos):
                    self._forward()
                elif self.btn_auto.click_if_hit(evt.pos):
                    self.auto_play = not self.auto_play
                elif self.btn_salvar.click_if_hit(evt.pos):
                    self._salvar()
                elif self.btn_hist.click_if_hit(evt.pos):
                    self.historico.abrir()
                elif self.btn_nova.click_if_hit(evt.pos):
                    self._nova()
                elif self.btn_sair.click_if_hit(evt.pos):
                    pygame.quit()
                    sys.exit(0)
            if evt.type == pygame.MOUSEWHEEL and self.historico.aberto:
                self.historico.scroll = max(0, self.historico.scroll - evt.y)

    def update(self):
        if self.auto_play and self.sessao_carregada is None:
            now = pygame.time.get_ticks()
            if now - self.auto_play_last > 700:
                self.auto_play_last = now
                self.engine.forward()

    def _forward(self):
        if self.sessao_carregada is not None:
            self.sessao_carregada.forward()
        else:
            self.engine.forward()

    def _back(self):
        if self.sessao_carregada is not None:
            self.sessao_carregada.back()
        else:
            self.engine.back()

    def _salvar(self):
        if self.sessao_carregada is not None:
            return
        path = self.engine.salvar_json()
        self.flash(f"Salvo: {os.path.basename(path)}")

    def _nova(self):
        if self.sessao_carregada is not None:
            self.sessao_carregada = None
        self.engine = Engine()
        self.auto_play = False
        self.flash("Nova sessao iniciada")

    def _carregar(self, fname: str):
        path = os.path.join(SESSOES_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.sessao_carregada = SessaoCarregada(data)
            ver = data.get("format_version", 1)
            extra = "" if ver == SESSION_FORMAT_VERSION else f" [formato v{ver} legado]"
            self.flash(f"Sessao: {fname}{extra} (ESC volta a ativa)")
        except Exception as e:
            self.flash(f"Erro ao carregar: {e}")

    # ----- render ----------------------------------------------------------
    def draw(self):
        self.screen.fill(BG)
        self._draw_header()
        if self.sessao_carregada is not None:
            self._draw_main_from_saved(self.sessao_carregada)
        else:
            self._draw_main_from_engine(self.engine)
        self._draw_footer()
        self.historico.draw(self.screen, self.fonts)
        self._draw_message()
        pygame.display.flip()

    def _draw_header(self):
        # Banner de titulo
        if self.sessao_carregada is not None:
            titulo = f"BARALHO MUSICAL  ·  [LEITURA]  {self.sessao_carregada.data.get('session_started_at','')}"
        else:
            titulo = f"BARALHO MUSICAL  ·  Sessao  {self.engine.session_started_at}"
        draw_text(self.screen, titulo, self.fonts.med, ACCENT, 30, 30)
        # Linha separadora
        pygame.draw.line(self.screen, BORDER, (30, 78), (WIDTH - 30, 78), 1)
        # Botoes
        self.btn_nova.draw(self.screen, self.fonts)
        self.btn_salvar.draw(self.screen, self.fonts)
        self.btn_hist.draw(self.screen, self.fonts)
        self.btn_sair.draw(self.screen, self.fonts)

    def _draw_footer(self):
        if self.sessao_carregada is not None:
            total = self.sessao_carregada.total
            cur = self.sessao_carregada.cursor + 1
        else:
            total = len(self.engine.snapshots)
            cur = self.engine.cursor + 1
        # Linha separadora superior do footer
        pygame.draw.line(self.screen, BORDER,
                         (30, HEIGHT - 90), (WIDTH - 30, HEIGHT - 90), 1)
        self.btn_back.draw(self.screen, self.fonts)
        self.btn_fwd.draw(self.screen, self.fonts)
        self.btn_auto.label = "Auto: ON" if self.auto_play else "Auto-play"
        self.btn_auto.draw(self.screen, self.fonts)
        info = f"Passo {cur} / {total}"
        draw_text(self.screen, info, self.fonts.small, TEXT_DIM,
                  WIDTH // 2, HEIGHT - 76, center=True)
        atalhos = "Setas: navegar  ·  Espaco/P: auto  ·  S: salvar  ·  H: historico  ·  N: nova  ·  Esc: sair"
        draw_text(self.screen, atalhos, self.fonts.tiny, TEXT_DIM,
                  WIDTH // 2, HEIGHT - 6, center=True)

    def _draw_message(self):
        if not self.mensagem:
            return
        if pygame.time.get_ticks() > self.mensagem_until:
            self.mensagem = ""
            return
        w = self.fonts.small.size(self.mensagem)[0] + 36
        rect = pygame.Rect(WIDTH // 2 - w // 2, HEIGHT - 124, w, 30)
        pygame.draw.rect(self.screen, OK_GREEN_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, OK_GREEN, rect, width=1, border_radius=8)
        draw_text(self.screen, self.mensagem, self.fonts.small, TEXT,
                  rect.centerx, rect.centery, center=True)

    # ----- corpo principal -------------------------------------------------
    def _draw_main_from_engine(self, eng: Engine):
        snap = eng.atual
        self._draw_main_from_snap(snap, deck_count=len(snap.deck_remaining))

    def _draw_main_from_saved(self, sess: SessaoCarregada):
        s = sess.atual
        deck_count = s.get("deck_remaining_count", 0)
        tipo = s["tipo"]
        card = None
        if s["card"]:
            cd = s["card"]
            suit = Suit(cd["suit"]) if cd["suit"] else None
            card = CardX(type=cd["type"], suit=suit, is_joker=cd["is_joker"])
        det = None
        if s["detalhe"]:
            d = dict(s["detalhe"])
            # compatibilidade com sessoes antigas (formato v1)
            if "action_label" not in d:
                old = d.pop("action_type", None)
                d["action_label"] = {
                    "retrograde": "passado",
                    "invert": "presente",
                    "retrograde_invert": "futuro",
                }.get(old, "numero")
            d.pop("e_anterior_mod", None)
            d.pop("action_type", None)
            d.setdefault("mirror_applied", False)
            d.setdefault("pre_mirror_key", None)
            d.setdefault("pre_mirror_value", None)
            d.setdefault("next_card_preview", None)
            d.setdefault("fired_fermata", False)
            d.setdefault("fired_tie_backward", False)
            d.setdefault("fired_tie_forward", False)
            det = Detalhe(**d)
        cur_params = []
        for p in s["current_note_params"]:
            cur_params.append(NoteParameter(
                param_name=p["param_name"], event_value=p["event_value"],
                mapped_key=p["mapped_key"], mapped_value=p["mapped_value"]))
        notas = []
        for n in s["notas_completas"]:
            params = []
            for p in n["parameters"]:
                params.append(NoteParameter(
                    param_name=p["param_name"], event_value=p["event_value"],
                    mapped_key=p["mapped_key"], mapped_value=p["mapped_value"]))
            notas.append(Note(
                parameters=params,
                is_rest=n["is_rest"],
                has_fermata=n.get("has_fermata", False),
                tie_backward=n.get("tie_backward", False),
                tie_forward=n.get("tie_forward", False),
            ))
        fake = Snapshot(
            idx=s["idx"], tipo=tipo, card=card,
            motivo_descarte=s.get("motivo_descarte"),
            detalhe=det,
            event_history=[], previous_card_value=None, previous_card=None,
            deck_remaining=[],
            current_note_params=cur_params,
            current_note_has_ace=s["current_note_has_ace"],
            notas_completas=notas,
            current_note_fermata=s.get("current_note_fermata", False),
            current_note_tie_backward=s.get("current_note_tie_backward", False),
            current_note_tie_forward=s.get("current_note_tie_forward", False),
        )
        self._draw_main_from_snap(fake, deck_count=deck_count)

    def _draw_main_from_snap(self, snap: Snapshot, deck_count: int):
        top = 100
        bottom = HEIGHT - 110
        h = bottom - top

        # Larguras adaptativas
        left_w  = min(360, int(WIDTH * 0.22))
        right_w = max(420, int(WIDTH * 0.32))
        mid_w   = WIDTH - left_w - right_w - 90  # gaps de 30 entre paineis

        x_left = 30
        x_mid  = x_left + left_w + 30
        x_right = x_mid + mid_w + 30

        left  = pygame.Rect(x_left,  top, left_w,  h)
        mid   = pygame.Rect(x_mid,   top, mid_w,   h)
        right = pygame.Rect(x_right, top, right_w, h)

        draw_panel(self.screen, left,  "BARALHO",      self.fonts)
        draw_panel(self.screen, mid,   "PASSO ATUAL",  self.fonts)
        draw_panel(self.screen, right, "COMPOSICAO",   self.fonts)

        self._draw_deck_panel(left, snap, deck_count)
        self._draw_passo_panel(mid, snap)
        self._draw_composicao_panel(right, snap)

    def _draw_deck_panel(self, rect: pygame.Rect, snap: Snapshot, deck_count: int):
        cx = rect.centerx
        cy = rect.y + 130
        # pilha empilhada
        for off in (10, 5, 0):
            r = pygame.Rect(cx - 56, cy - 84 + off, 112, 156)
            draw_card(self.screen, None, r, self.fonts, face_up=False)
        draw_text(self.screen, f"{deck_count} cartas", self.fonts.med, TEXT,
                  cx, cy + 92, center=True)
        draw_text(self.screen, "(reembaralha sozinho)",
                  self.fonts.tiny, TEXT_DIM, cx, cy + 118, center=True)

        # estado do interpretador
        sx = rect.x + 16
        sy = cy + 165
        draw_text(self.screen, "ESTADO  E:", self.fonts.small, ACCENT, sx, sy)
        hist = snap.event_history[-6:] if snap.event_history else [0.0]
        for i, e in enumerate(hist):
            label = (f"E[-{len(hist)-i-1}] = {int(e)}"
                     if i < len(hist) - 1 else f"E_atual = {int(e)}")
            draw_text(self.screen, label, self.fonts.tiny, TEXT_DIM,
                      sx + 4, sy + 22 + i * 16)
        pv = snap.previous_card_value
        draw_text(self.screen, f"ult_numerica = {pv if pv is not None else '-'}",
                  self.fonts.tiny, TEXT_DIM, sx + 4,
                  sy + 22 + len(hist) * 16 + 6)
        pc = snap.previous_card
        pc_str = "-"
        if pc is not None:
            if pc.is_joker:
                pc_str = "JOKER"
            else:
                pc_str = f"{pc.type}/{SUIT_GLYPH[pc.suit]}"
        draw_text(self.screen, f"ult_carta = {pc_str}",
                  self.fonts.tiny, TEXT_DIM, sx + 4,
                  sy + 22 + len(hist) * 16 + 22)

    def _draw_passo_panel(self, rect: pygame.Rect, snap: Snapshot):
        cx = rect.centerx
        if snap.tipo == "inicio":
            draw_text(self.screen,
                      "Inicio - aperte AVANCAR ou seta direita",
                      self.fonts.med, TEXT, cx, rect.y + 80, center=True)
            draw_text(self.screen,
                      "Cada passo processa UMA carta.",
                      self.fonts.small, TEXT_DIM, cx, rect.y + 120, center=True)
            # legenda da semantica
            ly = rect.y + 180
            legenda = [
                ("J  = PASSADO  (R)",   "valor da carta anterior; senao identidade do naipe"),
                ("Q  = PRESENTE (I)",   "identidade do naipe; espelha o parametro"),
                ("K  = FUTURO   (RI)",  "valor da proxima carta; espelha o parametro"),
            ]
            for titulo, sub in legenda:
                draw_text(self.screen, titulo, self.fonts.small, ACCENT,
                          rect.x + 30, ly)
                draw_text(self.screen, sub, self.fonts.tiny, TEXT_DIM,
                          rect.x + 30, ly + 20)
                ly += 50
            # tabela de identidades
            ly += 10
            draw_text(self.screen, "IDENTIDADES DOS NAIPES:", self.fonts.small,
                      ACCENT, rect.x + 30, ly)
            ly += 22
            ids = [
                (Suit.COPAS, "+", 0),
                (Suit.OUROS, "-", 0),
                (Suit.ESPADAS, "*", 1),
                (Suit.PAUS,    "/", 1),
            ]
            for suit, op, ident in ids:
                txt = f"{SUIT_GLYPH[suit]}  ({op})  -> {ident}"
                col = RED if SUIT_INFO[suit]["color"] == "VERMELHO" else BLACK_INK
                draw_text(self.screen, txt, self.fonts.small, col,
                          rect.x + 50, ly)
                ly += 22
            return

        # Carta grande
        card_w, card_h = 170, 240
        card_rect = pygame.Rect(rect.x + 28, rect.y + 56, card_w, card_h)
        draw_card(self.screen, snap.card, card_rect, self.fonts, face_up=True,
                  highlight=(snap.tipo == "normal"))

        tx = card_rect.right + 24
        ty = rect.y + 56

        if snap.tipo == "coringa":
            draw_text(self.screen, "CORINGA", self.fonts.big, JOKER_GOLD, tx, ty)
            draw_text(self.screen, "Reset: E volta a 0, baralho reembaralha.",
                      self.fonts.small, TEXT, tx, ty + 42)
            draw_text(self.screen, "Notas geradas permanecem.",
                      self.fonts.small, TEXT, tx, ty + 64)
            draw_text(self.screen, "Nota em construcao reinicia.",
                      self.fonts.small, TEXT_DIM, tx, ty + 88)
            return

        if snap.tipo == "descarte":
            # banner de descarte
            badge = pygame.Rect(tx, ty, 160, 28)
            pygame.draw.rect(self.screen, WARN_BG, badge, border_radius=6)
            pygame.draw.rect(self.screen, WARN, badge, width=1, border_radius=6)
            draw_text(self.screen, "DESCARTADA", self.fonts.small, WARN,
                      badge.centerx, badge.centery, center=True)
            draw_text(self.screen, "Motivo:", self.fonts.small, TEXT_DIM,
                      tx, ty + 44)
            self._draw_wrapped(snap.motivo_descarte or "", self.fonts.small, TEXT,
                               tx, ty + 66, rect.right - tx - 20)
            draw_text(self.screen, "A proxima carta entra no lugar.",
                      self.fonts.small, TEXT_DIM, tx, ty + 140)
            return

        # passo NORMAL
        det = snap.detalhe
        if det is None:
            return

        # Tag temporal grande
        label_map = {
            "passado":  ("PASSADO  (J)",   ACCENT_DIM),
            "presente": ("PRESENTE (Q)",   ACCENT),
            "futuro":   ("FUTURO   (K)",   (140, 90, 160)),
            "numero":   ("NUMERICA",       TEXT_DIM),
        }
        tag, tag_color = label_map.get(det.action_label, ("?", TEXT_DIM))
        draw_text(self.screen, tag, self.fonts.med, tag_color, tx, ty)

        # cabecalho parametro / naipe
        draw_text(self.screen, f"Parametro: {det.mapped_param_name}",
                  self.fonts.small, ACCENT, tx, ty + 32)
        if snap.card.suit is not None:
            naipe_txt = f"Naipe: {SUIT_GLYPH[snap.card.suit]} {SUIT_INFO[snap.card.suit]['symbol']}  ({det.op_name})"
            naipe_col = card_color_for(snap.card.suit)
            draw_text(self.screen, naipe_txt, self.fonts.small, naipe_col,
                      tx, ty + 54)

        # equacao
        eq_y = ty + 92
        draw_text(self.screen,
                  f"current = {self._fmt_num(det.valor_carta)}    [{det.valor_carta_origem}]",
                  self.fonts.small, TEXT, tx, eq_y)
        draw_text(self.screen, f"E_anterior = {int(det.e_anterior)}",
                  self.fonts.small, TEXT, tx, eq_y + 22)

        # preview do futuro (K)
        if det.next_card_preview is not None:
            nc = det.next_card_preview
            if nc["is_joker"]:
                next_str = "JOKER (sem valor)"
            else:
                suit_enum = Suit(nc["suit"]) if nc["suit"] else None
                glyph = SUIT_GLYPH[suit_enum] if suit_enum else "?"
                next_str = f"{nc['type']}/{glyph}"
            draw_text(self.screen, f"PEEK (futuro) = {next_str}",
                      self.fonts.small, (140, 90, 160), tx, eq_y + 44)

        # gcd/lcm usam notacao funcional; +,-,*,/ usam infixa
        a_str = self._fmt_num(det.valor_carta)
        b_str = f"{int(det.e_anterior)}"
        e_str = f"{int(det.event_value)}"
        if det.op_symbol in ("gcd", "lcm"):
            eq_main = f"{det.op_symbol}({a_str}, {b_str}) = {e_str}"
        else:
            eq_main = f"{a_str} {det.op_symbol} ({b_str}) = {e_str}"
        draw_text(self.screen, eq_main, self.fonts.big, ACCENT, tx, eq_y + 74)

        draw_text(self.screen, f"int(E) = {det.int_event}",
                  self.fonts.small, TEXT_DIM, tx, eq_y + 120)

        # mapeamento -> parametro
        if det.mirror_applied:
            # mostra antes e depois do espelho
            draw_text(self.screen,
                      f"-> {det.mapped_param_name} = {det.pre_mirror_value}  "
                      f"(key={det.pre_mirror_key})",
                      self.fonts.small, TEXT_DIM, tx, eq_y + 144)
            arrow = f"ESPELHO -> {det.mapped_value}  (key={det.mapped_key})"
            draw_text(self.screen, arrow, self.fonts.med, OK_GREEN,
                      tx, eq_y + 168)
        else:
            draw_text(self.screen,
                      f"-> {det.mapped_param_name} = {det.mapped_value}  "
                      f"(key={det.mapped_key})",
                      self.fonts.med, OK_GREEN, tx, eq_y + 144)

        if snap.card.is_ace():
            # Ás = pausa imediata. Encerra a nota com o ritmo definido pela carta.
            badge = pygame.Rect(tx, eq_y + 200, 320, 26)
            pygame.draw.rect(self.screen, WARN_BG, badge, border_radius=6)
            pygame.draw.rect(self.screen, WARN, badge, width=1, border_radius=6)
            draw_text(self.screen,
                      f"AS = PAUSA  ({det.mapped_value})",
                      self.fonts.small, WARN, badge.centerx, badge.centery,
                      center=True)
        elif det.nota_finalizada:
            badge = pygame.Rect(tx, eq_y + 200, 180, 26)
            pygame.draw.rect(self.screen, OK_GREEN_BG, badge, border_radius=6)
            pygame.draw.rect(self.screen, OK_GREEN, badge, width=1, border_radius=6)
            draw_text(self.screen, "Nota finalizada!", self.fonts.small,
                      OK_GREEN, badge.centerx, badge.centery, center=True)

        # Gramatica de articulacao disparada neste passo: FERMATA (10), TIE+-(ev=+-1)
        art_triggers = []
        if det.fired_fermata:
            art_triggers.append(("FERMATA (10)", FERMATA_FG, FERMATA_BG))
        if det.fired_tie_backward:
            art_triggers.append(("LIGADURA <- (E=-1)", TIE_FG, TIE_BG))
        if det.fired_tie_forward:
            art_triggers.append(("LIGADURA -> (E=+1)", TIE_FG, TIE_BG))
        if art_triggers:
            bx = tx
            by = eq_y + 238
            for txt, fg, bg in art_triggers:
                w = self.fonts.small.size(txt)[0] + 18
                badge = pygame.Rect(bx, by, w, 26)
                pygame.draw.rect(self.screen, bg, badge, border_radius=6)
                pygame.draw.rect(self.screen, fg, badge, width=1, border_radius=6)
                draw_text(self.screen, txt, self.fonts.small, fg,
                          badge.centerx, badge.centery, center=True)
                bx += w + 8

    @staticmethod
    def _fmt_num(x: float) -> str:
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x))}"
        return f"{x:.3f}"

    def _draw_wrapped(self, text, font, color, x, y, max_w):
        words = text.split()
        line = ""
        ly = y
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] > max_w and line:
                draw_text(self.screen, line, font, color, x, ly)
                ly += font.get_linesize()
                line = w
            else:
                line = test
        if line:
            draw_text(self.screen, line, font, color, x, ly)

    def _draw_composicao_panel(self, rect: pygame.Rect, snap: Snapshot):
        x = rect.x + 16
        y = rect.y + 44
        draw_text(self.screen, "Nota em construcao:", self.fonts.small, ACCENT, x, y)
        params = snap.current_note_params
        labels = ["1 Nota", "2 Alt.", "3 Ritmo", "4 BPM", "5 Din.", "6 Art.", "7 Oit."]
        slot_y = y + 24
        slot_h = 28
        for i in range(7):
            slot = pygame.Rect(x, slot_y + i * (slot_h + 2), rect.w - 32, slot_h)
            if i < len(params):
                pygame.draw.rect(self.screen, OK_GREEN_BG, slot, border_radius=6)
                pygame.draw.rect(self.screen, OK_GREEN, slot, width=1, border_radius=6)
                p = params[i]
                draw_text(self.screen, f"{labels[i]}: {p.mapped_value}",
                          self.fonts.small, TEXT, slot.x + 8, slot.y + 6)
                draw_text(self.screen, f"E={p.event_value}", self.fonts.tiny,
                          TEXT_DIM, slot.right - 8, slot.y + 9, right=True)
            elif i == len(params):
                pygame.draw.rect(self.screen, ACCENT_SOFT, slot, border_radius=6)
                pygame.draw.rect(self.screen, ACCENT, slot, width=1, border_radius=6)
                draw_text(self.screen, f"{labels[i]}: ...", self.fonts.small,
                          ACCENT_DIM, slot.x + 8, slot.y + 6)
            else:
                pygame.draw.rect(self.screen, BG, slot, border_radius=6)
                pygame.draw.rect(self.screen, BORDER, slot, width=1, border_radius=6)
                draw_text(self.screen, labels[i], self.fonts.tiny, TEXT_DIM,
                          slot.x + 8, slot.y + 9)
        ny = slot_y + 7 * (slot_h + 2) + 12
        # Flags de articulacao acumuladas para a nota em construcao
        acc = []
        if snap.current_note_fermata:
            acc.append(("FERMATA", FERMATA_FG, FERMATA_BG))
        if snap.current_note_tie_backward:
            acc.append(("LIG <-", TIE_FG, TIE_BG))
        if snap.current_note_tie_forward:
            acc.append(("LIG ->", TIE_FG, TIE_BG))
        draw_text(self.screen, "Articulacao acumulada:", self.fonts.tiny,
                  TEXT_DIM, x, ny)
        fy = ny + 16
        fx = x
        if acc:
            for label, fg, bg in acc:
                w = self.fonts.tiny.size(label)[0] + 14
                badge = pygame.Rect(fx, fy, w, 20)
                pygame.draw.rect(self.screen, bg, badge, border_radius=4)
                pygame.draw.rect(self.screen, fg, badge, width=1, border_radius=4)
                draw_text(self.screen, label, self.fonts.tiny, fg,
                          badge.centerx, badge.centery, center=True)
                fx += w + 6
        else:
            draw_text(self.screen, "(nenhuma)", self.fonts.tiny, TEXT_DIM, fx, fy + 2)
        ny = fy + 32
        draw_text(self.screen, f"Notas geradas: {len(snap.notas_completas)}",
                  self.fonts.small, ACCENT, x, ny)
        ny += 22
        # mostra as ultimas N notas (calculado pelo espaco disponivel)
        max_lines = max(4, (rect.bottom - ny - 16) // 18)
        ultimas = list(enumerate(snap.notas_completas))[-max_lines:]
        for idx, nota in ultimas:
            line = f"{idx+1:3d}. {nota.get_summary()}"
            color = WARN if nota.is_rest else TEXT
            draw_text(self.screen, line, self.fonts.tiny, color, x, ny)
            ny += 18


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    # --windowed para forcar modo janela durante debug
    fullscreen = "--windowed" not in sys.argv
    app = App(fullscreen=fullscreen)
    app.run()


if __name__ == "__main__":
    main()
