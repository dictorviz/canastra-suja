"""
A_OSC - CANASTRA SUJA: a CAMA generativa (baralho virtual -> SuperCollider)

====================================================================
LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
====================================================================
*** Nunca programou? Abra antes o PYTHON_DO_ZERO.md.

Em uma frase: este e o tocador "automatico" antigo da cama. Antes da peca virar
ao vivo, a musica era GERADA por um computador (no nucleo_compositor.py) como
uma lista de notas, e este arquivo tocava essa lista de cabo a rabo, dormindo o
tempo de cada nota. Hoje, na peca, quem manda as notas e o a_cama.py (carta a
carta). Este a_osc.py ficou util sobretudo pra TESTAR o synth sozinho:
    python a_osc.py 60      # toca 60 segundos de cama gerada, pra ouvir o som

A diferenca chave: o a_cama NAO dorme (a carta humana e o relogio); o a_osc
DORME a duracao de cada nota, porque ele toca uma composicao inteira sozinho.

>>> SEM VOZ. Em Canastra Suja a voz/palavras do Perec saiu: este driver NAO
>>> dispara nenhuma mensagem /baralho/fala_* -- so as notas instrumentais
>>> (/baralho/note, /rest, /start, /end). O synth de voz do a_synth.scd
>>> (\\baralhoVox) fica dormente (~voxFragments segue vazio, pre-inicializado).

CONFIG PADRAO:
    host: 127.0.0.1   port: 57120 (sclang)

MENSAGENS OSC ENVIADAS:
    /baralho/start  []
    /baralho/note   [pitch_midi, velocity, cents, dur_total, dur_sustain,
                     articulacao, bpm, fermata, tie_in, tie_out]
    /baralho/rest   [dur, fermata, tie_in, tie_out]
    /baralho/end    []

USO COMO BIBLIOTECA:
    from nucleo_compositor import Compositor
    from a_osc import play_composition_osc
    comp = Compositor(); comp.compose(seed=42, target_seconds=120)
    play_composition_osc(comp.notes)
"""

import time
from typing import Callable, List, Optional  # rotulos de tipo. Callable = "uma funcao".

from pythonosc import udp_client

# pega do nucleo da matematica: o andamento padrao, o tipo "Note" (uma nota) e
# uma funcao que calcula quantos segundos uma nota dura.
from nucleo_compositor import (
    DEFAULT_BPM,
    Note,
    note_duration_seconds,
)


# =============================================================================
# CONFIGURACAO (tabelas de-para que traduzem "musica" em numeros pro synth)
# =============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 57120  # sclang default

# nome da nota -> quantos semitons acima do "do" (C). Usado pra achar o MIDI.
NOTE_TO_SEMITONE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

# dinamica (forte/fraco em italiano) -> "velocidade" MIDI (1 a 127). ppp = bem
# fraco (16), fff = bem forte (127). E o volume/intensidade da batida.
DYNAMIC_VELOCITY = {
    'ppp': 16, 'pp': 32, 'p': 48, 'mp': 64,
    'mf': 80, 'f': 96, 'ff': 112, 'fff': 127,
}

# articulacao -> quanto da duracao a nota fica "presa" (soando). Staccato = curto
# (0.4 = 40%), tenuto = cheio (1.0 = 100%).
ARTICULATION_SUSTAIN = {
    'NORMAL': 0.9,
    'STACATTO': 0.4,
    'TENUTO': 1.0,
    'ACENTO': 0.9,
    'ACENTO C/ STACATTO': 0.4,
    'TENUTO C/ STACATTO': 0.5,
    'ACENTO C/ TENUTO': 1.0,
}

# acento -> um "empurrao" a mais na velocidade (a nota soa mais forte).
ARTICULATION_VELOCITY_BOOST = {
    'ACENTO': 20,
    'ACENTO C/ STACATTO': 20,
    'ACENTO C/ TENUTO': 20,
}


def note_pitch_to_midi(note_name: str, oitava_str: str) -> int:
    """G/'4' -> 67. (oitava+1)*12 + semitom."""
    # MIDI numera as notas: cada oitava sao 12 semitons. A formula junta a oitava
    # com o semitom da nota pra achar o numero exato (ex: G na oitava 4 = 67).
    return (int(oitava_str) + 1) * 12 + NOTE_TO_SEMITONE[note_name]


# =============================================================================
# PLAYER OSC (instrumental, sem voz)
# =============================================================================

class OscPlayer:
    """Envia notas via OSC pra um receptor (SuperCollider, Pd, Max, etc.)."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        verbose: bool = True,
    ):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.client = udp_client.SimpleUDPClient(host, port)  # carteiro OSC
        self.current_bpm = DEFAULT_BPM  # guarda o andamento atual (pode mudar por nota)
        if verbose:
            print(f"[OSC] Enviando para {host}:{port}")

    def send_start(self):
        # avisa o synth que a composicao vai comecar.
        self.client.send_message("/baralho/start", [])

    def send_end(self):
        # avisa o synth que a composicao acabou.
        self.client.send_message("/baralho/end", [])

    def play_note(self, note: Note, on_event: Optional[Callable] = None) -> float:
        # toca UMA nota: manda o recado pro synth e DORME a duracao dela. Devolve
        # quantos segundos durou (pra quem chamou ir somando o tempo total).

        # Atualiza BPM se a nota tem (o parametro 3 e o andamento).
        if not note.is_rest and len(note.parameters) > 3:
            bpm_val = note.parameters[3].mapped_value
            if isinstance(bpm_val, int):
                self.current_bpm = bpm_val

        total = note_duration_seconds(note, self.current_bpm)  # duracao em segundos

        # -- CASO 1: a "nota" e uma PAUSA (silencio) --
        if note.is_rest:
            self.client.send_message(
                "/baralho/rest",
                [
                    float(total),
                    int(note.has_fermata),    # int(True)=1, int(False)=0
                    int(note.tie_backward),
                    int(note.tie_forward),
                ],
            )
            if on_event:  # se passaram um "avisador", chama ele com os dados (pra UI)
                on_event({
                    'type': 'rest', 'duration': total,
                    'fermata': note.has_fermata,
                    'tie_backward': note.tie_backward,
                    'tie_forward': note.tie_forward,
                    'cards': [
                        {'type': c.type, 'suit': c.suit.value}
                        for c in (note.cards_used or [])
                    ],
                })
            elif self.verbose:
                fer = " (^)" if note.has_fermata else ""
                print(f"  ... PAUSA {total:.2f}s{fer}")
            time.sleep(total)  # DORME o tempo da pausa
            return total

        # -- CASO 2: e uma nota de verdade. Le cada parametro pra traduzir em som. --
        nota_name   = note.parameters[0].mapped_value  # nome da nota (do, re...)
        alt_param   = note.parameters[1].mapped_value  # microafinacao (cents)
        alt_cents   = alt_param if isinstance(alt_param, int) else 0
        dinamica    = note.parameters[4].mapped_value  # forte/fraco
        articulacao = note.parameters[5].mapped_value  # seco/acentuado...
        oitava      = note.parameters[6].mapped_value  # grave/agudo

        midi_pitch = note_pitch_to_midi(nota_name, oitava)  # vira numero MIDI
        velocity = DYNAMIC_VELOCITY.get(dinamica, 80)       # vira forca base
        # soma o empurrao do acento (se houver) e nunca passa de 127.
        velocity = min(127, velocity + ARTICULATION_VELOCITY_BOOST.get(articulacao, 0))

        # "ligadura" (tie/slur): se a nota se liga a vizinha, ela soa o tempo todo.
        is_slurred = note.tie_forward or note.tie_backward
        sustain_ratio = 1.0 if is_slurred else ARTICULATION_SUSTAIN.get(articulacao, 0.9)
        sustain_seconds = total * sustain_ratio  # quanto tempo a nota fica "presa"

        self.client.send_message(
            "/baralho/note",
            [
                int(midi_pitch),
                int(velocity),
                int(alt_cents),
                float(total),
                float(sustain_seconds),
                str(articulacao),
                int(self.current_bpm),
                int(note.has_fermata),
                int(note.tie_backward),
                int(note.tie_forward),
            ],
        )

        if on_event:  # de novo: avisa a UI, se houver
            on_event({
                'type': 'note', 'pitch': midi_pitch, 'velocity': velocity,
                'duration': total, 'sustain': sustain_seconds,
                'note_name': nota_name, 'oitava': oitava,
                'alt_cents': alt_cents, 'dinamica': dinamica,
                'articulacao': articulacao, 'bpm': self.current_bpm,
                'fermata': note.has_fermata,
                'tie_backward': note.tie_backward,
                'tie_forward': note.tie_forward,
                'cards': [
                    {'type': c.type, 'suit': c.suit.value}
                    for c in (note.cards_used or [])
                ],
            })
        elif self.verbose:
            cents_str = f" {alt_cents:+d}c" if alt_cents else ""
            fer = " (^)" if note.has_fermata else ""
            print(
                f"  {nota_name}{oitava}{cents_str} [MIDI {midi_pitch:3d}] vel={velocity:3d} "
                f"{total:.2f}s @ {self.current_bpm}bpm {dinamica} {articulacao}{fer}"
            )

        # SC controla o envelope/release: aqui so esperamos a duracao total
        time.sleep(total)  # DORME o tempo da nota antes de seguir pra proxima
        return total


def play_composition_osc(
    notes: List[Note],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    max_seconds: Optional[float] = None,
    on_event: Optional[Callable] = None,
    verbose: bool = True,
    stop_event=None,
) -> float:
    """
    Toca a composicao via OSC. Para antes do fim se max_seconds for atingido
    ou se stop_event (threading.Event) for setado -- usado pela cama em loop.
    """
    player = OscPlayer(host=host, port=port, verbose=verbose)  # cria o tocador
    elapsed = 0.0       # tempo ja tocado (vai somando)
    notes_played = 0    # quantas notas ja tocaram

    try:
        if verbose:
            print()
            print(f"[INFO] Tocando {len(notes)} notas via OSC -> {host}:{port}")
            print("-" * 60)
        player.send_start()
        for note in notes:  # toca nota por nota, em ordem
            # para na hora se mandaram parar (stop_event) -- usado quando a cama
            # roda em "thread" (em paralelo) e precisa ser interrompida.
            if stop_event is not None and stop_event.is_set():
                break
            # para se ja passou do tempo-alvo (ex: pediram so 60 segundos).
            if max_seconds is not None and elapsed >= max_seconds:
                if verbose:
                    print(f"[INFO] Limite {max_seconds:.0f}s atingido. "
                          f"{notes_played}/{len(notes)} notas tocadas.")
                break
            elapsed += player.play_note(note, on_event=on_event)  # toca e soma o tempo
            notes_played += 1
        else:
            # DETALHE Python: este "else" e do FOR (nao de um if!). Ele so roda se o
            # for terminou NATURALMENTE (sem cair num "break"). Ou seja: tocou tudo
            # ate o fim. Se houve break (limite/parada), este bloco e pulado.
            if verbose:
                print(f"[INFO] Fim. {notes_played} notas tocadas, {elapsed:.2f}s totais.")
    finally:
        player.send_end()  # aconteca o que acontecer, avisa o synth que acabou

    return elapsed


# =============================================================================
# MAIN (DEMO) -- 'python a_osc.py 60' toca 60s de cama gerada, so pra testar o som
# =============================================================================

def main():
    import sys
    from nucleo_compositor import Compositor

    print("=" * 70)
    print("A_OSC - o BARALHO VIRTUAL generativo (sem voz) - DEMO")
    print("=" * 70)
    print(f"[INFO] Enviando para {DEFAULT_HOST}:{DEFAULT_PORT} (sclang)")
    print()

    target_seconds = 60.0  # padrao: 60 segundos
    if len(sys.argv) > 1:  # se a pessoa digitou um numero depois do nome do arquivo...
        try:
            target_seconds = float(sys.argv[1])  # ...usa ele como duracao-alvo
        except ValueError:
            pass  # se nao for numero, ignora e fica com o padrao

    print(f"[INFO] Compondo (alvo {target_seconds:.0f}s)...")
    comp = Compositor()  # cria o compositor (o gerador da musica)
    comp.compose(seed=42, verbose=False, target_seconds=target_seconds)  # gera as notas
    print(f"[OK] {len(comp.notes)} notas geradas.")
    print()

    play_composition_osc(comp.notes)  # toca a composicao gerada


if __name__ == "__main__":
    main()
