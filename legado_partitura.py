"""
TRADUTOR BARALHO -> MUSIC21

Converte objetos Note do sistema (nucleo_compositor.py) em objetos music21.
Permite exportar a composicao gerada como MIDI, MusicXML, PDF (via LilyPond), etc.

USO BASICO:
    from nucleo_compositor import Compositor
    from legado_partitura import composition_to_stream, export_midi, export_musicxml

    compositor = Compositor(num_notes=16)
    compositor.compose(seed=42, verbose=False)

    stream = composition_to_stream(compositor.notes)
    export_midi(stream, "saida.mid")
    export_musicxml(stream, "saida.musicxml")

MAPEAMENTO DE FLAGS:
    is_rest       -> music21.note.Rest
    has_fermata   -> music21.expressions.Fermata (anexada a nota/pausa)
    tie_backward  -> fecha um Slur que comecou na nota anterior
    tie_forward   -> abre um Slur que sera fechado na proxima nota com tie_backward
"""

import sys
from typing import List, Tuple, Dict, Any, Optional

import music21 as m21

from nucleo_compositor import Note, Compositor, RITMO_TO_QUARTERLENGTH


# =============================================================================
# TABELAS DE CONVERSAO
# =============================================================================
# RITMO_TO_QUARTERLENGTH agora vive em nucleo_compositor.py (canonico).
# Re-exportado acima para nao quebrar imports antigos.

# Articulacao -> lista de classes music21 (algumas combinam duas)
ARTICULATION_MAP = {
    'NORMAL': [],
    'STACATTO': [m21.articulations.Staccato],
    'TENUTO': [m21.articulations.Tenuto],
    'ACENTO': [m21.articulations.Accent],
    'ACENTO C/ STACATTO': [m21.articulations.Accent, m21.articulations.Staccato],
    'TENUTO C/ STACATTO': [m21.articulations.Tenuto, m21.articulations.Staccato],
    'ACENTO C/ TENUTO': [m21.articulations.Accent, m21.articulations.Tenuto],
}


# =============================================================================
# CONVERSAO Note -> music21
# =============================================================================

def _build_pitch(note_name: str, oitava: str, alt_cents: int) -> m21.pitch.Pitch:
    """
    Constroi um Pitch com possivel microtone (alteracao em cents).
    - cents multiplo de 100 -> usa accidental padrao (sustenido/bemol)
    - cents nao-multiplo de 100 -> usa microtone (afinacao expressiva)
    """
    p = m21.pitch.Pitch(f"{note_name}{oitava}")
    if alt_cents == 0:
        return p

    semitones = alt_cents / 100.0
    # Se cair em um semitom inteiro, usa accidental padrao
    if alt_cents % 100 == 0:
        # Define alter (em semitons) - music21 ajusta o accidental
        p.accidental = m21.pitch.Accidental(int(semitones))
    else:
        # Microtone para valores expressivos (33, 50, 83, 133, 150, 183...)
        p.microtone = m21.pitch.Microtone(alt_cents)
    return p


def note_to_m21(note: Note) -> Tuple[m21.note.GeneralNote, Dict[str, Any]]:
    """
    Converte um Note do baralho em (m21_obj, metadata):
    - m21_obj: Rest ou Note pronto pra inserir num Stream
    - metadata: dict com {bpm, dynamic, slur_in, slur_out}
      (slurs e dynamics sao spanners/objetos separados, vao no Stream)
    """
    if note.is_rest:
        if note.parameters:
            ritmo = note.parameters[0].mapped_value
            ql = RITMO_TO_QUARTERLENGTH.get(ritmo, 1.0)
        else:
            ql = 1.0
        m21_obj = m21.note.Rest(quarterLength=ql)
        if note.has_fermata:
            m21_obj.expressions.append(m21.expressions.Fermata())
        return m21_obj, {
            'bpm': None,
            'dynamic': None,
            'slur_in': note.tie_backward,
            'slur_out': note.tie_forward,
        }

    # Nota normal: 7 parametros na ordem
    p = note.parameters
    pitch_name   = p[0].mapped_value   # NOTA: 'G'..'F'
    alt_cents    = p[1].mapped_value   # ALTERACOES: int em cents
    ritmo        = p[2].mapped_value   # FIGURA: string
    bpm          = p[3].mapped_value   # ANDAMENTO: int
    dinamica     = p[4].mapped_value   # DINAMICA: 'ppp'..'fff'
    articulacao  = p[5].mapped_value   # ARTICULACAO: string
    oitava       = p[6].mapped_value   # OITAVA: '1'..'7'

    pitch = _build_pitch(pitch_name, oitava, alt_cents if isinstance(alt_cents, int) else 0)
    m21_obj = m21.note.Note(pitch=pitch)

    ql = RITMO_TO_QUARTERLENGTH.get(ritmo, 1.0)
    m21_obj.duration = m21.duration.Duration(quarterLength=ql)

    # Articulacoes
    for art_cls in ARTICULATION_MAP.get(articulacao, []):
        m21_obj.articulations.append(art_cls())

    # Fermata
    if note.has_fermata:
        m21_obj.expressions.append(m21.expressions.Fermata())

    return m21_obj, {
        'bpm': bpm,
        'dynamic': dinamica,
        'slur_in': note.tie_backward,
        'slur_out': note.tie_forward,
    }


# =============================================================================
# COMPOSICAO -> STREAM
# =============================================================================

def composition_to_stream(
    notes: List[Note],
    title: str = "Composicao Baralho",
    composer: str = "Sistema Baralho Musical",
) -> m21.stream.Score:
    """
    Converte uma lista de Note em um Score (Part dentro) music21.
    Adiciona MetronomeMark (so quando muda), Dynamics (so quando muda) e Slurs.
    """
    score = m21.stream.Score()
    score.insert(0, m21.metadata.Metadata())
    score.metadata.title = title
    score.metadata.composer = composer

    part = m21.stream.Part()

    last_bpm: Optional[int] = None
    last_dynamic: Optional[str] = None
    prev_m21: Optional[m21.note.GeneralNote] = None
    prev_note: Optional[Note] = None

    for note in notes:
        m21_obj, meta = note_to_m21(note)

        # MetronomeMark so quando BPM muda
        if meta.get('bpm') is not None and meta['bpm'] != last_bpm:
            part.append(m21.tempo.MetronomeMark(number=meta['bpm']))
            last_bpm = meta['bpm']

        # Dynamic so quando muda (e nao em pausas)
        if meta.get('dynamic') and meta['dynamic'] != last_dynamic:
            part.append(m21.dynamics.Dynamic(meta['dynamic']))
            last_dynamic = meta['dynamic']

        part.append(m21_obj)

        # Slur entre nota anterior e atual:
        # - Se a anterior tem tie_forward (queria ligar com proxima) OU
        # - Se a atual tem tie_backward (quer ligar com anterior),
        # entao desenha um slur entre as duas.
        if prev_m21 is not None and prev_note is not None:
            if prev_note.tie_forward or note.tie_backward:
                part.insert(0, m21.spanner.Slur([prev_m21, m21_obj]))

        prev_m21 = m21_obj
        prev_note = note

    score.insert(0, part)
    return score


# =============================================================================
# EXPORT
# =============================================================================

def export_midi(stream: m21.stream.Stream, filename: str = "composicao.mid") -> str:
    out = stream.write('midi', fp=filename)
    print(f"[OK] MIDI exportado: {out}")
    return str(out)


def export_musicxml(stream: m21.stream.Stream, filename: str = "composicao.musicxml") -> str:
    out = stream.write('musicxml', fp=filename)
    print(f"[OK] MusicXML exportado: {out}")
    return str(out)


# =============================================================================
# UTILIDADES DE INSPECAO
# =============================================================================

def describe_stream(stream: m21.stream.Stream) -> None:
    """Imprime um resumo do que tem no stream."""
    notes = list(stream.recurse().notes)
    rests = list(stream.recurse().notesAndRests.getElementsByClass(m21.note.Rest))
    fermatas = sum(
        1 for n in stream.recurse().notesAndRests
        if any(isinstance(e, m21.expressions.Fermata) for e in n.expressions)
    )
    slurs = list(stream.recurse().getElementsByClass(m21.spanner.Slur))
    tempos = list(stream.recurse().getElementsByClass(m21.tempo.MetronomeMark))
    dynamics = list(stream.recurse().getElementsByClass(m21.dynamics.Dynamic))

    print("=" * 60)
    print(f"RESUMO DO STREAM")
    print("=" * 60)
    print(f"  Notas:           {len(notes)}")
    print(f"  Pausas:          {len(rests)}")
    print(f"  Fermatas:        {fermatas}")
    print(f"  Slurs:           {len(slurs)}")
    print(f"  Mudancas tempo:  {len(tempos)}")
    print(f"  Dinamicas:       {len(dynamics)}")


# =============================================================================
# MAIN (DEMO)
# =============================================================================

def main():
    print("=" * 80)
    print("TRADUTOR BARALHO -> MUSIC21")
    print("=" * 80)
    print()

    print("[INFO] Compondo 16 notas (seed=42)...")
    compositor = Compositor(num_notes=16)
    compositor.compose(seed=42, verbose=False)
    print(f"[OK] {len(compositor.notes)} notas geradas.")
    print()

    print("[INFO] Convertendo para music21 Stream...")
    score = composition_to_stream(
        compositor.notes,
        title="Baralho Musical (seed 42)",
    )
    print("[OK] Score criado.")
    print()

    describe_stream(score)
    print()

    print("[INFO] Exportando...")
    export_midi(score, "composicao_baralho.mid")
    export_musicxml(score, "composicao_baralho.musicxml")
    print()
    print("Abra o MusicXML no MuseScore (ou similar) para visualizar a partitura.")
    print("Abra o MIDI em qualquer player ou DAW.")


if __name__ == "__main__":
    main()
