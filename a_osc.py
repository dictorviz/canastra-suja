"""
PLAYER OSC - SISTEMA BARALHO MUSICAL

Envia a composicao em tempo real via OSC para o SuperCollider (ou qualquer
receptor OSC). Diferente de MIDI, o OSC manda dados ricos: cents como float
exato (sem pitch bend), articulacao como string, dinamica como string, etc.

CONFIGURACAO PADRAO:
    host: 127.0.0.1  (localhost)
    port: 57120      (porta padrao do SuperCollider language - sclang)

MENSAGENS OSC ENVIADAS:
    /baralho/start  []
        - inicio da composicao (limpa estado no lado SC)

    /baralho/note   [pitch_midi:int, velocity:int, cents:int, dur_total:float,
                     dur_sustain:float, articulacao:str, bpm:int,
                     fermata:int, tie_in:int, tie_out:int]
        - pitch_midi: 0..127 (numero MIDI)
        - velocity:   0..127 (intensidade)
        - cents:      desvio em cents (-200..+200)
        - dur_total:  duracao total da nota em segundos
        - dur_sustain: porcao em que a nota fica ativa (resto e silencio)
        - articulacao: string ('NORMAL', 'STACATTO', 'ACENTO', ...)
        - bpm:        bpm atual
        - fermata, tie_in, tie_out: 0 ou 1

    /baralho/rest   [dur:float, fermata:int, tie_in:int, tie_out:int]

    /baralho/end    []
        - fim da composicao

USO COMO BIBLIOTECA:
    from nucleo_compositor import Compositor
    from a_osc import play_composition_osc

    comp = Compositor()
    comp.compose(seed=42, verbose=False, target_seconds=120)
    play_composition_osc(comp.notes, host="127.0.0.1", port=57120)
"""

import time
import unicodedata
from typing import Callable, List, Optional

from pythonosc import udp_client

import nucleo_perec
import a_voz
from nucleo_compositor import (
    DEFAULT_BPM,
    Note,
    note_duration_seconds,
)


# =============================================================================
# NORMALIZACAO DE TEXTO PRA VOZ (SuperCollider so come ASCII)
# =============================================================================

def normalize_for_vox(text: str) -> str:
    """
    Tira acentos (NFD + drop combining marks), reduz a ASCII lowercase.
    SC trata strings como bytes ASCII; mandar UTF-8 multi-byte estoura a
    tabela de fonemas. Tudo que nao for letra/espaco vira espaco (= pausa).
    """
    if not text:
        return ""
    # NFD decompoe "á" em "a" + "U+0301", depois removemos os combining marks
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if not unicodedata.combining(c))
    out = []
    for c in stripped.lower():
        if c.isalpha() and ord(c) < 128:
            out.append(c)
        elif c.isspace() or c in ".,;:!?-—":
            out.append(" ")
        # outros caracteres sao dropados
    return "".join(out)


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
# PLAYER OSC
# =============================================================================

class OscPlayer:
    """Envia notas via OSC pra um receptor (SuperCollider, Pd, Max, etc.)."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        verbose: bool = True,
        preload_tts: bool = True,
    ):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.client = udp_client.SimpleUDPClient(host, port)
        self.current_bpm = DEFAULT_BPM
        if verbose:
            print(f"[OSC] Enviando para {host}:{port}")
        if preload_tts:
            self.preload_tts_buffers()

    def preload_tts_buffers(self):
        """
        Renderiza todas palavras unicas via SAPI (cache em tts_cache/*.wav)
        e envia (chave, path_abs) pra SC carregar em Buffers.
        Idempotente: WAVs ja em cache nao sao re-renderizadas.
        """
        if self.verbose:
            print("[TTS] pre-render + envio de paths pra SC...")
        idx = a_voz.precompute_all_chapters(verbose=self.verbose)
        for key, path in idx.items():
            self.client.send_message("/baralho/fala_load", [str(key), str(path)])
        if self.verbose:
            print(f"[TTS] {len(idx)} buffers enviados pra SC carregar.")
        # SC carrega async; da uma pausa pequena pra Buffer.read completar
        # antes da primeira nota tocar.
        time.sleep(0.5)

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

        # ---------------------------------------------------------------
        # VOZ (Perec) - 6 fragmentos sussurrados sincronizados com os ecos
        # do SC. STACATTO nao recebe fala (seco/sem ecos longos), mas
        # SEMPRE enviamos /baralho/fala_setup pra "limpar" os fragments
        # da nota anterior no SC.
        # ---------------------------------------------------------------
        fragments_raw: List[str] = ["", "", "", "", "", ""]
        spoken_fragments: List[str] = []
        main_card_dict = None
        if note.cards_used:
            main_card_dict = {
                "type": note.cards_used[0].type,
                "suit": note.cards_used[0].suit.value,
            }
        if main_card_dict is not None and "STACATTO" not in articulacao:
            for i in range(6):
                frag = nucleo_perec.fragmento_para_eco(main_card_dict, eco_idx=i)
                norm = normalize_for_vox(frag)
                fragments_raw[i] = norm
                if norm.strip():
                    spoken_fragments.append(norm)
        # Sempre envia (mesmo todos vazios) - serve de reset no SC
        self.client.send_message("/baralho/fala_setup", fragments_raw)

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

        # ---------------------------------------------------------------
        # RECITATIVO durante FERMATA - frase longa declamada
        # Vai pelo hall (cauda longa). Disparado em paralelo com o tom.
        # ---------------------------------------------------------------
        recitativo_text = ""
        if note.has_fermata and main_card_dict is not None:
            raw = nucleo_perec.frase_para_recitativo(main_card_dict)
            recitativo_text = normalize_for_vox(raw)
            if recitativo_text.strip():
                # Pequena pan aleatorio sutil pra o recitativo respirar
                rec_pan = ((hash(recitativo_text) % 21) - 10) * 0.02
                self.client.send_message(
                    "/baralho/fala_recitativo",
                    [str(recitativo_text), float(total), float(rec_pan)],
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
                'spoken_fragments': spoken_fragments,
                'recitativo': recitativo_text,
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
    preload_tts: bool = True,
) -> float:
    """
    Toca a composicao via OSC. Se max_seconds for dado, faz cap; senao toca tudo.
    """
    player = OscPlayer(host=host, port=port, verbose=verbose, preload_tts=preload_tts)
    elapsed = 0.0
    notes_played = 0

    try:
        if verbose:
            print()
            print(f"[INFO] Tocando {len(notes)} notas via OSC -> {host}:{port}")
            print("-" * 60)
        player.send_start()
        for note in notes:
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

    print("=" * 80)
    print("OSC PLAYER - SISTEMA BARALHO MUSICAL")
    print("=" * 80)
    print()
    print(f"[INFO] Enviando para {DEFAULT_HOST}:{DEFAULT_PORT}")
    print("       (porta padrao do SuperCollider/sclang)")
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
