"""
BARALHO TTS - pre-renderiza palavras via SAPI em arquivos WAV cacheados.
Substitui a sintese formantica do \baralhoVox por samples reais de voz.

USO:
    import a_voz
    paths = a_voz.precompute_all_chapters()  # {chave: path_abs}
    # depois, o player OSC envia (chave, path) pra SC, que carrega em Buffer.

CHAVE vs PALAVRA:
    chave (cache key):  ASCII lower stripped, sem acentos      -> "pagina"
    palavra (raw TTS):  texto original com acentos             -> "Página"
                        (acentos importam pra prosodia do SAPI)
    O TTS recebe RAW pra pronunciar bem; o cache eh indexado por CHAVE
    pra casar com o texto normalizado que o Python ja manda pro SC.

VOZES POR IDIOMA:
    pt -> Microsoft Maria Desktop (pt-BR)
    en -> Microsoft Zira Desktop  (en-US)
    fr -> sem voz local; nucleo_perec.WORD_TTS_OVERRIDE redireciona
          a entrada do SAPI pra grafia foneticamente aproximada em pt-br
          (renderiza com Maria).

MANIFEST:
    tts_cache/_manifest.json mantem {chave: {raw, lang, voice}}. Se algum
    desses campos mudar entre runs (ex: usuario corrigiu acento, mudou
    idioma da palavra, ou instalou nova voz), a chave eh re-renderizada
    automaticamente. Sem manifest, todas as WAVs sao tratadas como stale.

DEPENDENCIA: Windows + SAPI. Maria + Zira ja vem em qualquer Windows
moderno; outras vozes precisam ser instaladas via Settings > Time & Lang.
"""

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import nucleo_perec


# Pasta de cache (mesmo dir do projeto)
CACHE_DIR = Path(__file__).parent / "tts_cache"
MANIFEST_PATH = CACHE_DIR / "_manifest.json"

# Mapeamento idioma -> substring (case-insensitive) procurada em SAPI voices.
# A primeira voz cujo Name contem o hint eh usada.
LANG_VOICE_HINT: Dict[str, str] = {
    "pt": "maria",      # Microsoft Maria Desktop (pt-BR)
    "en": "zira",       # Microsoft Zira Desktop (en-US)
    "fr": "hortense",   # Microsoft Hortense Desktop (fr-FR) - PRECISA SER
                        # INSTALADA (Settings > Hora e Idioma > Fala > add
                        # frances). Enquanto nao estiver, _resolve_voice_name
                        # devolve "" e o frances cai na voz default do SAPI
                        # com a grafia transliterada (WORD_TTS_OVERRIDE).
                        # Assim que a Hortense aparecer, o manifest detecta a
                        # troca de voz E de grafia e re-renderiza sozinho.
}

# Rate do SAPI: -10..+10 (default 0 ~200wpm). Negativo = mais lento.
# Recitativo / fantasma legivel quer LENTO -> ~ -2 (≈140wpm).
TTS_RATE = -2

# Volume 0..1 (controle fino fica no SC; aqui mantemos cheio)
TTS_VOLUME = 1.0


# =============================================================================
# NORMALIZACAO
# =============================================================================

def normalize_key(text: str) -> str:
    """ASCII lower, sem acentos, sem pontuacao - chave canonica de uma palavra."""
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if not unicodedata.combining(c))
    out = []
    for c in stripped.lower():
        if c.isalpha() and ord(c) < 128:
            out.append(c)
    return "".join(out)


def _strip_punct(word: str) -> str:
    """Tira pontuacao de borda pra preservar 'habito' de 'habito.'"""
    return word.strip(".,;:!?\"'()[]{}—-–…")


# =============================================================================
# EXTRACAO DE PALAVRAS DOS CAPITULOS
# =============================================================================

class WordSpec:
    """Tudo que o renderer precisa pra uma palavra: chave, raw, lang, voz.

    O texto efetivo passado pro SAPI (tts_input) NAO eh fixado aqui: depende
    de qual voz estiver de fato instalada (ver precompute_all_chapters). Se a
    voz dedicada do idioma existir, fala a grafia original (raw_display); se
    nao, usa a transliteracao foneticamente aproximada (tts_override).
    """
    __slots__ = ("key", "raw_display", "tts_override", "lang", "voice_hint")

    def __init__(self, key: str, raw_display: str, tts_override: Optional[str],
                 lang: str, voice_hint: str):
        self.key = key
        self.raw_display = raw_display    # palavra original (com acentos)
        self.tts_override = tts_override  # transliteracao fallback (ou None)
        self.lang = lang
        self.voice_hint = voice_hint


def extract_unique_words() -> List[WordSpec]:
    """
    Varre todos CAPITULOS.texto. Retorna lista de WordSpec unica por key.
    'raw_display' eh a primeira ocorrencia com acentos (preservado pro display);
    'tts_input' aplica WORD_TTS_OVERRIDE se houver.
    """
    seen: Dict[str, WordSpec] = {}
    for cap in nucleo_perec.CAPITULOS.values():
        if not cap.texto:
            continue
        for tok in cap.texto.split():
            raw = _strip_punct(tok)
            if not raw:
                continue
            key = normalize_key(raw)
            if not key or key in seen:
                continue
            lang = nucleo_perec.word_lang(key)
            voice_hint = LANG_VOICE_HINT.get(lang, LANG_VOICE_HINT["pt"])
            # Transliteracao fallback (ex: frances -> grafia pt aproximada),
            # so usada quando NAO houver voz dedicada do idioma instalada.
            override = nucleo_perec.WORD_TTS_OVERRIDE.get(key)
            seen[key] = WordSpec(
                key=key,
                raw_display=raw,
                tts_override=override,
                lang=lang,
                voice_hint=voice_hint,
            )
    return list(seen.values())


# =============================================================================
# RESOLUCAO DE VOZ (qual voz SAPI realmente atende cada hint de idioma)
# =============================================================================

_INSTALLED_VOICES_CACHE: Optional[List[str]] = None


def installed_voice_names() -> List[str]:
    """Nomes completos das vozes SAPI instaladas (ex: 'Microsoft Maria
    Desktop'). Consulta o SAPI uma vez e cacheia pro resto do processo."""
    global _INSTALLED_VOICES_CACHE
    if _INSTALLED_VOICES_CACHE is not None:
        return _INSTALLED_VOICES_CACHE
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
    )
    names: List[str] = []
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=60,
        )
        names = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    except (OSError, subprocess.SubprocessError):
        names = []
    _INSTALLED_VOICES_CACHE = names
    return names


def resolve_voice_name(hint: str) -> str:
    """Nome SAPI completo da primeira voz instalada cujo Name contem o hint
    (case-insensitive), ou "" se nenhuma estiver instalada."""
    hint_l = (hint or "").lower()
    if not hint_l:
        return ""
    for name in installed_voice_names():
        if hint_l in name.lower():
            return name
    return ""


# =============================================================================
# MANIFEST (controle de invalidacao de cache)
# =============================================================================

def _load_manifest() -> Dict[str, Dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_manifest(manifest: Dict[str, Dict[str, str]]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)


def _entry_matches(entry: Optional[Dict[str, str]], spec: WordSpec,
                   tts_input: str, voice_resolved: str) -> bool:
    """Cache valido sse grafia falada, idioma E voz REAL usada nao mudaram.
    Comparar a voz resolvida (e nao so o hint) garante re-render automatico
    quando o usuario instala a voz que faltava (ex: Hortense fr-FR)."""
    if entry is None:
        return False
    return (
        entry.get("raw") == tts_input
        and entry.get("lang") == spec.lang
        and entry.get("voice") == voice_resolved
    )


# =============================================================================
# RENDER via PowerShell + System.Speech (batch num processo so)
# =============================================================================

def _path_for_key(key: str) -> Path:
    return CACHE_DIR / f"{key}.wav"


def _build_ps_batch_script(voice_name: str, jobs: List[Tuple[str, Path]]) -> str:
    """
    Monta um script PowerShell que renderiza um batch de palavras numa
    UNICA voz. `voice_name` eh o Name EXATO ja resolvido em Python (ex:
    'Microsoft Maria Desktop'); vazio = usa a voz default do SAPI.
    Pra renderizar em varias vozes, chame esta funcao uma vez por grupo.
    """
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "Add-Type -AssemblyName System.Speech",
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        f"$s.Rate = {TTS_RATE}",
        f"$s.Volume = {int(TTS_VOLUME * 100)}",
    ]
    if voice_name:
        name_esc = voice_name.replace("'", "''")
        lines.append(f"$s.SelectVoice('{name_esc}')")
    for raw, path in jobs:
        raw_esc = raw.replace("'", "''")
        path_esc = str(path).replace("'", "''")
        lines.append(f"$s.SetOutputToWaveFile('{path_esc}')")
        lines.append(f"$s.Speak('{raw_esc}')")
    lines.append("$s.SetOutputToNull()")
    lines.append("$s.Dispose()")
    return "\n".join(lines)


def _run_ps_batch(voice_name: str, jobs: List[Tuple[str, Path]]) -> Tuple[int, str]:
    """Roda um lote de renders num unico processo PowerShell, numa voz."""
    if not jobs:
        return (0, "")
    script = _build_ps_batch_script(voice_name, jobs)
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=600,
    )
    return (proc.returncode, (proc.stderr or "") + (proc.stdout or ""))


def precompute_all_chapters(verbose: bool = True, batch_size: int = 80) -> Dict[str, Path]:
    """
    Renderiza todas palavras unicas de todos capitulos. Retorna {key: path_abs}.
    Re-renderiza apenas as que mudaram (raw/lang/voice diferente do manifest)
    ou nao existem ainda. Agrupa por voz pra abrir UM processo PowerShell
    por (voz x batch).
    """
    specs = extract_unique_words()
    total = len(specs)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Quais hints de idioma nao tem voz instalada? (avisa o usuario)
    if verbose:
        for lang, hint in LANG_VOICE_HINT.items():
            if not resolve_voice_name(hint):
                print(f"[TTS] AVISO: voz '{hint}' ({lang}) nao instalada - "
                      f"essas palavras usam a voz default + grafia aproximada.")

    manifest = _load_manifest()
    # group key = NOME REAL da voz resolvida ("" = default do SAPI).
    pending_by_voice: Dict[str, List[Tuple[str, Path, WordSpec]]] = {}
    resolved_for: Dict[str, str] = {}        # key -> voice_resolved
    tts_input_for: Dict[str, str] = {}       # key -> grafia falada
    out: Dict[str, Path] = {}
    skipped = 0

    for spec in specs:
        voice_resolved = resolve_voice_name(spec.voice_hint)
        # Com voz dedicada do idioma -> grafia original. Sem ela -> fallback
        # transliterado (se houver), pra default do SAPI chegar mais perto.
        if voice_resolved:
            tts_input = spec.raw_display
        else:
            tts_input = spec.tts_override or spec.raw_display
        resolved_for[spec.key] = voice_resolved
        tts_input_for[spec.key] = tts_input

        p = _path_for_key(spec.key)
        entry = manifest.get(spec.key)
        wav_ok = p.exists() and p.stat().st_size > 0
        if wav_ok and _entry_matches(entry, spec, tts_input, voice_resolved):
            out[spec.key] = p.resolve()
            skipped += 1
        else:
            pending_by_voice.setdefault(voice_resolved, []).append((tts_input, p, spec))

    pending_total = sum(len(v) for v in pending_by_voice.values())
    if verbose:
        print(f"[TTS] total={total} cache_hit={skipped} pendentes={pending_total} (dir={CACHE_DIR})")

    if pending_total == 0:
        return out

    rendered = 0
    failed: List[str] = []

    for voice_resolved, items in pending_by_voice.items():
        if verbose:
            label = voice_resolved or "(default do SAPI)"
            print(f"[TTS] voz='{label}': {len(items)} palavras")
        for batch_start in range(0, len(items), batch_size):
            batch = items[batch_start: batch_start + batch_size]
            jobs = [(raw, p) for raw, p, _spec in batch]
            if verbose:
                first = batch[0][0]
                last = batch[-1][0]
                print(f"[TTS]   batch {batch_start // batch_size + 1}: "
                      f"renderizando {len(batch)} ({first!r}..{last!r})")
            rc, log = _run_ps_batch(voice_resolved, jobs)
            for raw, p, spec in batch:
                if p.exists() and p.stat().st_size > 0:
                    out[spec.key] = p.resolve()
                    manifest[spec.key] = {
                        "raw": tts_input_for[spec.key],
                        "lang": spec.lang,
                        "voice": resolved_for[spec.key],
                        "voice_hint": spec.voice_hint,
                    }
                    rendered += 1
                else:
                    failed.append(raw)
            if rc != 0 and verbose:
                print(f"[TTS]   (batch retornou rc={rc}, log: {log[:200]})")

    _save_manifest(manifest)

    if verbose:
        print(f"[TTS] pronto. renderizadas={rendered} cacheadas={skipped} falhas={len(failed)}")
        if failed:
            print(f"[TTS] falhas: {failed[:10]}{'...' if len(failed) > 10 else ''}")
    return out


def cache_index() -> Dict[str, Path]:
    """Retorna {key: path_abs} apenas pras WAVs ja presentes em cache."""
    out: Dict[str, Path] = {}
    if not CACHE_DIR.exists():
        return out
    for f in CACHE_DIR.glob("*.wav"):
        if f.stat().st_size > 0:
            out[f.stem] = f.resolve()
    return out


def purge_cache() -> int:
    """Apaga todos os WAVs e o manifest. Retorna numero de arquivos removidos."""
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for f in CACHE_DIR.glob("*.wav"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    if MANIFEST_PATH.exists():
        try:
            MANIFEST_PATH.unlink()
        except OSError:
            pass
    return n


# =============================================================================
# DEMO STANDALONE
# =============================================================================

def _demo():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    specs = extract_unique_words()
    print(f"Palavras unicas: {len(specs)}")
    by_lang: Dict[str, int] = {}
    for s in specs:
        by_lang[s.lang] = by_lang.get(s.lang, 0) + 1
    print(f"Por idioma: {by_lang}")
    print(f"Vozes instaladas: {installed_voice_names()}")
    for lang, hint in LANG_VOICE_HINT.items():
        print(f"  {lang} -> hint '{hint}' -> resolvida '{resolve_voice_name(hint) or '(default)'}'")
    print(f"Amostra: {[(s.raw_display, s.lang, s.tts_override) for s in specs[:10]]}")
    print()
    idx = precompute_all_chapters(verbose=True)
    print()
    print(f"Index final: {len(idx)} entradas")
    sample_keys = list(idx.keys())[:5]
    for k in sample_keys:
        print(f"  {k!r} -> {idx[k]}")


if __name__ == "__main__":
    _demo()
