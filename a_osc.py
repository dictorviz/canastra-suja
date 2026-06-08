"""
A_OSC - CANASTRA SUJA: a CAMA generativa (baralho virtual -> SuperCollider)

Toca a composicao gerada (nucleo_compositor: 52 cartas -> 7 parametros ->
notas) via OSC pro a_synth.scd. E a CAMA que fica rodando ao fundo da peca,
enquanto as cartas da vida real (camada B / b_synth) sujam por cima.

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
from typing import Callable, List, Optional

from pythonosc import udp_client

from nucleo_compositor import (
    DEFAULT_BPM,
    Note,
    note_duration_seconds,
)


# =============================================================================
# CONFIGURACAO
# =============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 57120  # sclang default

NOTE_TO_SEMITONE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

DYNAMIC_VELOCITY = {
    'ppp': 16, 'pp': 32, 'p': 48, 'mp': 64,
    'mf': 80, 'f': 96, 'ff': 112, 'fff': 127,
}

ARTICULATION_SUSTAIN = {
    'NORMAL': 0.9,
    'STACATTO': 0.4,
    'TENUTO': 1.0,
    'ACENTO': 0.9,
    'ACENTO C/ STACATTO': 0.4,
    'TENUTO C/ STACATTO': 0.5,
    'ACENTO C/ TENUTO': 1.0,
}

ARTICULATION_VELOCITY_BOOST = {
    'ACENTO': 20,
    'ACENTO C/ STACATTO': 20,
    'ACENTO C/ TENUTO': 20,
}


def note_pitch_to_midi(note_name: str, oitava_str: str) -> int:
    """G/'4' -> 67. (oitava+1)*12 + semitom."""
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
        self.client = udp_client.SimpleUDPClient(host, port)
        self.current_bpm = DEFAULT_BPM
        if verbose:
            print(f"[OSC] Enviando para {host}:{port}")

    def send_start(self):
        self.client.send_message("/baralho/start", [])

    def send_end(self):
        self.client.send_message("/baralho/end", [])

    def play_note(self, note: Note, on_event: Optional[Callable] = None) -> float:
        # Atualiza BPM se a nota tem
        if not note.is_rest and len(note.parameters) > 3:
            bpm_val = note.parameters[3].mapped_value
            if isinstance(bpm_val, int):
                self.current_bpm = bpm_val

        total = note_duration_seconds(note, self.current_bpm)

        if note.is_rest:
            self.client.send_message(
                "/baralho/rest",
                [
                    float(total),
                    int(note.has_fermata),
                    int(note.tie_backward),
                    int(note.tie_forward),
                ],
            )
            if on_event:
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
            time.sleep(total)
            return total

        nota_name   = note.parameters[0].mapped_value
        alt_param   = note.parameters[1].mapped_value
        alt_cents   = alt_param if isinstance(alt_param, int) else 0
        dinamica    = note.parameters[4].mapped_value
        articulacao = note.parameters[5].mapped_value
        oitava      = note.parameters[6].mapped_value

        midi_pitch = note_pitch_to_midi(nota_name, oitava)
        velocity = DYNAMIC_VELOCITY.get(dinamica, 80)
        velocity = min(127, velocity + ARTICULATION_VELOCITY_BOOST.get(articulacao, 0))

        is_slurred = note.tie_forward or note.tie_backward
        sustain_ratio = 1.0 if is_slurred else ARTICULATION_SUSTAIN.get(articulacao, 0.9)
        sustain_seconds = total * sustain_ratio

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

        if on_event:
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
        time.sleep(total)
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
    player = OscPlayer(host=host, port=port, verbose=verbose)
    elapsed = 0.0
    notes_played = 0

    try:
        if verbose:
            print()
            print(f"[INFO] Tocando {len(notes)} notas via OSC -> {host}:{port}")
            print("-" * 60)
        player.send_start()
        for note in notes:
            if stop_event is not None and stop_event.is_set():
                break
            if max_seconds is not None and elapsed >= max_seconds:
                if verbose:
                    print(f"[INFO] Limite {max_seconds:.0f}s atingido. "
                          f"{notes_played}/{len(notes)} notas tocadas.")
                break
            elapsed += player.play_note(note, on_event=on_event)
            notes_played += 1
        else:
            if verbose:
                print(f"[INFO] Fim. {notes_played} notas tocadas, {elapsed:.2f}s totais.")
    finally:
        player.send_end()

    return elapsed


# =============================================================================
# MAIN (DEMO)
# =============================================================================

def main():
    import sys
    from nucleo_compositor import Compositor

    print("=" * 70)
    print("A_OSC - o BARALHO VIRTUAL generativo (sem voz) - DEMO")
    print("=" * 70)
    print(f"[INFO] Enviando para {DEFAULT_HOST}:{DEFAULT_PORT} (sclang)")
    print()

    target_seconds = 60.0
    if len(sys.argv) > 1:
        try:
            target_seconds = float(sys.argv[1])
        except ValueError:
            pass

    print(f"[INFO] Compondo (alvo {target_seconds:.0f}s)...")
    comp = Compositor()
    comp.compose(seed=42, verbose=False, target_seconds=target_seconds)
    print(f"[OK] {len(comp.notes)} notas geradas.")
    print()

    play_composition_osc(comp.notes)


if __name__ == "__main__":
    main()
