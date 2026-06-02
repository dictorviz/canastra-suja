"""
LIVE MIDI PLAYBACK - SISTEMA BARALHO MUSICAL

Toca a composicao em tempo real via MIDI, MONOFONICO.
Saida MIDI pode ser roteada para DAW, SuperCollider, sintetizadores virtuais
(via loopMIDI/IAC), VST hosts, etc. Maximo controle pra usuario.

MAPEAMENTO:
    - dinamica (ppp..fff)  -> velocity (16..127)
    - articulacao          -> sustain ratio (staccato=40%, tenuto=100%, etc.)
    - acento               -> +20 de velocity
    - alteracao (cents)    -> pitch bend (assume +/-200c range no synth)
    - fermata              -> duracao x 2
    - ligadura (slur)      -> sustain 100% (legato, sem gap)

USO PASSIVO (cap 5 min):
    python legado_midi.py

USO INTERATIVO (step-by-step, sem limite):
    python legado_midi.py interactive

USO COMO BIBLIOTECA:
    from nucleo_compositor import Compositor
    from legado_midi import play_composition, play_composition_interactive

    comp = Compositor(num_notes=32)
    comp.compose(seed=42, verbose=False)
    play_composition(comp.notes, max_seconds=300)
"""

import sys
import time
from typing import Callable, List, Optional, Tuple

import pygame.midi

from nucleo_compositor import (
    Compositor,
    Note,
    note_duration_seconds,
)


# =============================================================================
# CONFIGURACAO
# =============================================================================

MAX_DURATION_SECONDS = 300  # 5 minutos (limite do modo passivo)

# Semitons a partir do C dentro da oitava
NOTE_TO_SEMITONE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

# Velocity MIDI por dinamica
DYNAMIC_VELOCITY = {
    'ppp': 16, 'pp': 32, 'p': 48, 'mp': 64,
    'mf': 80, 'f': 96, 'ff': 112, 'fff': 127,
}

# Sustain ratio: porcao da duracao tocada antes do NoteOff
# (resto vira silencio antes da proxima nota)
ARTICULATION_SUSTAIN = {
    'NORMAL': 0.9,
    'STACATTO': 0.4,
    'TENUTO': 1.0,
    'ACENTO': 0.9,
    'ACENTO C/ STACATTO': 0.4,
    'TENUTO C/ STACATTO': 0.5,
    'ACENTO C/ TENUTO': 1.0,
}

# Articulacoes com acento ganham velocity extra
ARTICULATION_VELOCITY_BOOST = {
    'ACENTO': 20,
    'ACENTO C/ STACATTO': 20,
    'ACENTO C/ TENUTO': 20,
}

BEND_RANGE_CENTS = 200     # range padrao do pitch bend MIDI (assumindo synth default)


# =============================================================================
# CONVERSAO Note -> MIDI primitivas
# =============================================================================

def note_pitch_to_midi(note_name: str, oitava_str: str) -> int:
    """G/'4' -> 67, C/'4' -> 60. (oitava+1)*12 + semitom."""
    base = NOTE_TO_SEMITONE[note_name]
    oitava = int(oitava_str)
    return (oitava + 1) * 12 + base


def cents_to_bend(alt_cents: int, bend_range_cents: int = BEND_RANGE_CENTS) -> int:
    """
    Cents (+/-200) -> valor 14-bit de pitch bend (0..16383, 8192=centro).
    Clampa se passar do range.
    """
    if bend_range_cents == 0:
        return 8192
    ratio = max(-1.0, min(1.0, alt_cents / bend_range_cents))
    return int(8192 + ratio * 8191)


# compute_note_duration_seconds esta em nucleo_compositor.note_duration_seconds
# (a constante FERMATA_MULTIPLIER tambem migrou pra la).


# =============================================================================
# PLAYER MIDI MONOFONICO
# =============================================================================

class MidiPlayer:
    """
    Player MIDI monofonico: uma nota por vez.
    Slurs/ligaduras produzem legato (sustenta ate a proxima NoteOn).
    """

    def __init__(self, device_id: Optional[int] = None, channel: int = 0, verbose: bool = True):
        pygame.midi.init()
        self.channel = channel
        self.verbose = verbose
        self.active_pitch: Optional[int] = None
        self.out = self._open(device_id)
        self.current_bpm = 100  # default ate primeira nota com BPM definir

    def _open(self, device_id: Optional[int]) -> pygame.midi.Output:
        outputs: List[Tuple[int, str]] = []
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            _, name_bytes, _, is_output, _ = info
            if is_output:
                outputs.append((i, name_bytes.decode('utf-8', errors='replace')))

        if not outputs:
            raise RuntimeError(
                "Nenhuma porta MIDI de saida disponivel. "
                "Instale loopMIDI ou habilite uma porta MIDI no sistema."
            )

        if self.verbose:
            print("[MIDI] Portas de saida disponiveis:")
            for i, name in outputs:
                print(f"  [{i}] {name}")

        if device_id is None:
            # Preferencia: porta nao-Microsoft (provavel virtual cable do usuario)
            chosen = next((i for i, n in outputs if 'microsoft' not in n.lower()), outputs[0][0])
        else:
            chosen = device_id

        chosen_name = next((n for i, n in outputs if i == chosen), '?')
        if self.verbose:
            print(f"[MIDI] Usando porta [{chosen}] {chosen_name}")

        return pygame.midi.Output(chosen)

    def close(self):
        try:
            self._note_off_active()
            self._reset_bend()
        except Exception:
            pass
        if self.out:
            try:
                self.out.close()
            except Exception:
                pass
        pygame.midi.quit()

    @staticmethod
    def list_devices() -> List[Tuple[int, str, bool]]:
        """Lista (id, name, is_output) das portas MIDI."""
        pygame.midi.init()
        result = []
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            _, name_bytes, _, is_output, _ = info
            result.append((i, name_bytes.decode('utf-8', errors='replace'), bool(is_output)))
        return result

    def _note_off_active(self):
        if self.active_pitch is not None:
            self.out.note_off(self.active_pitch, 0, self.channel)
            self.active_pitch = None

    def _send_bend(self, alt_cents: int):
        bend = cents_to_bend(alt_cents)
        status = 0xE0 + self.channel
        lsb = bend & 0x7F
        msb = (bend >> 7) & 0x7F
        self.out.write_short(status, lsb, msb)

    def _reset_bend(self):
        self._send_bend(0)

    def play_note(self, note: Note, on_event: Optional[Callable] = None) -> float:
        """
        Toca uma nota (ou pausa). Atualiza self.current_bpm se a nota definir um.
        Retorna a duracao real ocupada em segundos.
        Em monofonia: para nota anterior antes do NoteOn (exceto se slur conecta).
        """
        # Atualiza BPM
        if not note.is_rest and len(note.parameters) > 3:
            bpm_val = note.parameters[3].mapped_value
            if isinstance(bpm_val, int):
                self.current_bpm = bpm_val

        total = note_duration_seconds(note, self.current_bpm)

        # =====================================================================
        # PAUSA
        # =====================================================================
        if note.is_rest:
            self._note_off_active()
            if on_event:
                on_event({
                    'type': 'rest',
                    'duration': total,
                    'fermata': note.has_fermata,
                    'tie_backward': note.tie_backward,
                    'tie_forward': note.tie_forward,
                })
            elif self.verbose:
                fer = " (^)" if note.has_fermata else ""
                slur_in = " <-" if note.tie_backward else ""
                slur_out = " ->" if note.tie_forward else ""
                print(f"  ... PAUSA {total:.2f}s{slur_in}{slur_out}{fer}")
            time.sleep(total)
            return total

        # =====================================================================
        # NOTA NORMAL: extrai parametros
        # =====================================================================
        nota_name   = note.parameters[0].mapped_value
        alt_param   = note.parameters[1].mapped_value
        alt_cents   = alt_param if isinstance(alt_param, int) else 0
        dinamica    = note.parameters[4].mapped_value
        articulacao = note.parameters[5].mapped_value
        oitava      = note.parameters[6].mapped_value

        midi_pitch = note_pitch_to_midi(nota_name, oitava)
        velocity = DYNAMIC_VELOCITY.get(dinamica, 80)
        velocity = min(127, velocity + ARTICULATION_VELOCITY_BOOST.get(articulacao, 0))

        # Slur = legato: sustenta ate o proximo NoteOn (sem gap)
        is_slurred = note.tie_forward or note.tie_backward
        sustain_ratio = 1.0 if is_slurred else ARTICULATION_SUSTAIN.get(articulacao, 0.9)
        sustain_seconds = total * sustain_ratio
        gap_seconds = max(0.0, total - sustain_seconds)

        # Para a nota anterior (monofonia estrita)
        self._note_off_active()

        # PitchBend + NoteOn
        self._send_bend(alt_cents)
        self.out.note_on(midi_pitch, velocity, self.channel)
        self.active_pitch = midi_pitch

        if on_event:
            on_event({
                'type': 'note',
                'pitch': midi_pitch,
                'velocity': velocity,
                'duration': total,
                'sustain': sustain_seconds,
                'gap': gap_seconds,
                'note_name': nota_name,
                'oitava': oitava,
                'alt_cents': alt_cents,
                'dinamica': dinamica,
                'articulacao': articulacao,
                'bpm': self.current_bpm,
                'fermata': note.has_fermata,
                'tie_backward': note.tie_backward,
                'tie_forward': note.tie_forward,
            })
        elif self.verbose:
            cents_str = f" {alt_cents:+d}c" if alt_cents else ""
            fer = " (^)" if note.has_fermata else ""
            sb = " <-" if note.tie_backward else ""
            sf = " ->" if note.tie_forward else ""
            print(
                f"  {nota_name}{oitava}{cents_str} [MIDI {midi_pitch:3d}] vel={velocity:3d} "
                f"{total:.2f}s @ {self.current_bpm}bpm {dinamica} {articulacao}{sb}{sf}{fer}"
            )

        time.sleep(sustain_seconds)
        self._note_off_active()
        if gap_seconds > 0:
            time.sleep(gap_seconds)

        return total


# =============================================================================
# MODOS DE REPRODUCAO
# =============================================================================

def play_composition(
    notes: List[Note],
    device_id: Optional[int] = None,
    max_seconds: float = MAX_DURATION_SECONDS,
    on_event: Optional[Callable] = None,
    verbose: bool = True,
) -> float:
    """
    Modo PASSIVO: toca a composicao do inicio ao fim, com cap de max_seconds.
    Default 300s (5 minutos). Retorna o tempo total decorrido.
    """
    player = MidiPlayer(device_id=device_id, verbose=verbose)
    elapsed = 0.0
    notes_played = 0

    try:
        if verbose:
            print()
            print(f"[INFO] Tocando ate {len(notes)} notas, limite {max_seconds:.0f}s")
            print("-" * 60)
        for note in notes:
            if elapsed >= max_seconds:
                if verbose:
                    print(
                        f"[INFO] Limite {max_seconds:.0f}s atingido. "
                        f"{notes_played}/{len(notes)} notas tocadas."
                    )
                break
            elapsed += player.play_note(note, on_event=on_event)
            notes_played += 1
        else:
            if verbose:
                print(
                    f"[INFO] Fim. {notes_played} notas tocadas, "
                    f"{elapsed:.2f}s totais."
                )
    finally:
        player.close()

    return elapsed


def play_composition_interactive(
    notes: List[Note],
    device_id: Optional[int] = None,
    on_event: Optional[Callable] = None,
) -> int:
    """
    Modo INTERATIVO: aperta ENTER pra avancar uma nota. 'q' para sair.
    Sem limite de tempo (o usuario controla o ritmo).
    """
    player = MidiPlayer(device_id=device_id, verbose=True)
    notes_played = 0
    try:
        print()
        print(f"[INTERATIVO] {len(notes)} notas. ENTER pra proxima, 'q' pra sair.")
        print("-" * 60)
        for i, note in enumerate(notes):
            try:
                user_in = input(f"[{i+1:3d}/{len(notes)}] > ")
            except (EOFError, KeyboardInterrupt):
                break
            if user_in.lower().strip() == 'q':
                break
            player.play_note(note, on_event=on_event)
            notes_played += 1
        print(f"\n[INFO] {notes_played} notas tocadas.")
    finally:
        player.close()
    return notes_played


# =============================================================================
# MAIN (DEMO)
# =============================================================================

def main():
    print("=" * 80)
    print("LIVE MIDI - SISTEMA BARALHO MUSICAL")
    print("=" * 80)
    print()

    # Lista dispositivos
    print("[INFO] Dispositivos MIDI:")
    for d_id, name, is_out in MidiPlayer.list_devices():
        kind = "OUT" if is_out else "IN "
        print(f"  [{d_id:2d}] {kind} {name}")
    pygame.midi.quit()  # libera, MidiPlayer reabrira

    # Decide modo
    mode = 'passive'
    if len(sys.argv) > 1 and sys.argv[1].startswith('interact'):
        mode = 'interactive'

    print()
    print(f"[INFO] Compondo (alvo {MAX_DURATION_SECONDS:.0f}s, seed=42)...")
    comp = Compositor()
    comp.compose(seed=42, verbose=False, target_seconds=MAX_DURATION_SECONDS)
    print(f"[OK] {len(comp.notes)} notas geradas.")

    if mode == 'passive':
        print()
        print(f"[INFO] Modo PASSIVO (limite {MAX_DURATION_SECONDS:.0f}s)")
        print("       Adicione 'interactive' como arg pra modo step-by-step.")
        play_composition(comp.notes, max_seconds=MAX_DURATION_SECONDS)
    else:
        play_composition_interactive(comp.notes)


if __name__ == "__main__":
    main()
