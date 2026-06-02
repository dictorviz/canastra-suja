"""
MAIN - SISTEMA BARALHO MUSICAL

Ponto de entrada unico do projeto. Roda com:

    python main.py

Apresenta um menu interativo no terminal pra escolher:

    [1] Tocar via OSC (SuperCollider) - som de qualidade, requer setup do SC
    [2] Tocar via MIDI               - manda pro Windows ou pra uma DAW
    [3] Exportar arquivos             - .mid e .musicxml (pro MuseScore)
    [4] Abrir visualizador (pygame)
    [0] Sair

Em todos os modos pergunta duracao (h/m/s) e seed antes de gerar a
composicao. A composicao gerada e reusada se vc voltar pra escolher
outra saida no mesmo seed (ex: tocou via OSC, agora exporta MIDI).

OUTRAS PORTAS DE ENTRADA (continuam funcionando):
    python legado_midi.py        # MIDI direto, 5min, seed 42
    python a_osc.py 60      # OSC direto, 60s, seed 42
    python a_visual_pygame.py        # visualizador pygame
"""

import os
import random
import re
import sys
from typing import List, Optional, Tuple

import nucleo_perec
from nucleo_compositor import Compositor, Note, total_duration_seconds


# =============================================================================
# UTILITARIOS DE INPUT
# =============================================================================

def _print_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def parse_duration(text: str) -> Optional[float]:
    """
    Le uma duracao em formato livre e retorna segundos (float).

    Aceita:
        '300'        -> 300s
        '300s'       -> 300s
        '5m'         -> 300s
        '5.5m'       -> 330s
        '1h'         -> 3600s
        '1h30m'      -> 5400s
        '1h30m20s'   -> 5420s
        '1:30:00'    -> 5400s   (h:m:s)
        '5:00'       -> 300s    (m:s)

    Retorna None se nao conseguiu parsear.
    """
    text = text.strip().lower()
    if not text:
        return None

    # Formato HH:MM:SS ou MM:SS
    if ':' in text:
        try:
            parts = [float(p) for p in text.split(':')]
        except ValueError:
            return None
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return None

    # Formato '1h30m20s' / '5m' / '300s' / '300'
    if re.fullmatch(r'[\d.]+', text):
        try:
            return float(text)
        except ValueError:
            return None

    total = 0.0
    matched = False
    for value, unit in re.findall(r'([\d.]+)\s*([hms])', text):
        try:
            v = float(value)
        except ValueError:
            return None
        if unit == 'h':
            total += v * 3600
        elif unit == 'm':
            total += v * 60
        elif unit == 's':
            total += v
        matched = True
    return total if matched else None


def format_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s:.1f}s" if (s or not parts) else "")
    return "".join(p for p in parts if p)


def prompt(text: str, default: str = "") -> str:
    """input() com default visivel."""
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)
    return ans if ans else default


def prompt_duration(default_seconds: float = 300.0) -> float:
    """Pergunta duracao da peca. Loop ate parsear OK."""
    print()
    print("Quanto tempo a peca deve durar?")
    print("  Exemplos: 300 (=300s), 5m, 1h30m, 1:30:00, 5:00")
    while True:
        text = prompt("Duracao", f"{format_duration(default_seconds)}")
        secs = parse_duration(text)
        if secs is not None and secs > 0:
            print(f"  -> alvo: {format_duration(secs)} ({secs:.1f}s)")
            return secs
        print("  [!] formato invalido, tenta de novo.")


def prompt_seed() -> Optional[int]:
    print()
    print("Seed (numero) ou ENTER pra aleatoria:")
    text = prompt("Seed", "aleatoria")
    if text.lower().startswith('aleat') or text == '':
        s = random.randint(0, 999999)
        print(f"  -> seed sorteada: {s}")
        return s
    try:
        return int(text)
    except ValueError:
        print(f"  [!] '{text}' nao e numero, usando seed aleatoria.")
        return random.randint(0, 999999)


def prompt_capitulo() -> str:
    """
    Pergunta qual capitulo do Perec usar. Retorna o id do capitulo.
    Aplica via nucleo_perec.set_capitulo() e retorna o id.
    """
    print()
    print("Capitulo do livro (Especes d'espaces - Perec):")
    print("  O capitulo determina o TEXTO-FONTE picotado nos ecos (fonemas")
    print("  sussurrados) e o RECITATIVO declamado durante fermatas.")
    print()
    caps = nucleo_perec.list_capitulos()
    # mostra numerado pra navegacao por indice
    for i, c in enumerate(caps, start=1):
        ind = "    " if c.parent else "  "
        print(f"  [{i:>2}] {ind}{c.display_id:>4}  {c.nome}")
    print()
    print("Digite o numero da lista (1-{0}), o id do capitulo ('0', '4.2',".format(len(caps)))
    print("'INF', '∞'), o nome ('cama', 'mundo'), ou ENTER pra Prologo.")
    text = prompt("Capitulo", "Prologo")
    cid = _resolve_capitulo_choice(text, caps)
    if cid is None:
        print(f"  [!] '{text}' nao reconhecido, usando Prologo.")
        cid = "0"
    nucleo_perec.set_capitulo(cid)
    cap = nucleo_perec.get_capitulo()
    txt_len = len(cap.texto or "")
    print(f"  -> capitulo: {cap.display_id}  {cap.nome}  (texto: {txt_len} chars)")
    if txt_len == 0:
        print(f"  [AVISO] esse capitulo nao tem texto - fonemas/recitativos sairao vazios.")
    return cid


def _resolve_capitulo_choice(text: str, caps) -> Optional[str]:
    """Aceita: indice na lista, id exato, simbolo '∞', prefixo de nome/attractor."""
    t = (text or "").strip()
    if not t:
        return "0"
    # indice 1..N
    try:
        i = int(t)
        if 1 <= i <= len(caps):
            return caps[i - 1].id
    except ValueError:
        pass
    if t in ("∞", "inf", "INF", "infinity"):
        return nucleo_perec.INFINITY_ID
    for c in caps:
        if c.id.lower() == t.lower():
            return c.id
    for c in caps:
        if c.attractor.lower() == t.lower():
            return c.id
    low = t.lower()
    for c in caps:
        if c.nome.lower().startswith(low):
            return c.id
    return None


# =============================================================================
# COMPOSITION CACHE
# =============================================================================

class CompositionState:
    """Guarda a composicao gerada pra ser reutilizada entre opcoes do menu."""

    def __init__(self):
        self.notes: Optional[List[Note]] = None
        self.seed: Optional[int] = None
        self.target_seconds: Optional[float] = None
        self.capitulo_id: Optional[str] = None

    def has(self) -> bool:
        return self.notes is not None and len(self.notes) > 0

    def info(self) -> str:
        if not self.has():
            return "(nenhuma composicao gerada ainda)"
        dur = total_duration_seconds(self.notes)
        cap = nucleo_perec.get_capitulo()
        return (f"seed={self.seed}, alvo={format_duration(self.target_seconds or 0)}, "
                f"{len(self.notes)} notas, dur real={format_duration(dur)}, "
                f"cap={cap.display_id} ({cap.nome})")

    def generate(self, seed: int, target_seconds: float):
        print()
        print(f"[GERANDO] seed={seed}, alvo={format_duration(target_seconds)}...")
        comp = Compositor()
        comp.compose(seed=seed, verbose=False, target_seconds=target_seconds)
        self.notes = comp.notes
        self.seed = seed
        self.target_seconds = target_seconds
        dur = total_duration_seconds(self.notes)
        print(f"[OK] {len(self.notes)} notas geradas. Duracao real: "
              f"{format_duration(dur)}")

    def ensure(self) -> bool:
        """Se nao tem composicao, pergunta dados e gera. Retorna True se ok."""
        if self.has():
            print()
            print(f"Ja existe composicao: {self.info()}")
            ans = prompt("Usar essa mesma? (s/n)", "s").lower()
            if ans.startswith('s'):
                return True
        secs = prompt_duration()
        seed = prompt_seed()
        if seed is None:
            return False
        self.capitulo_id = prompt_capitulo()
        self.generate(seed, secs)
        return True


# =============================================================================
# OPCOES DO MENU
# =============================================================================

def opt_play_osc(state: CompositionState):
    _print_header("TOCAR VIA OSC (SuperCollider)")
    print()
    print("Pre-requisitos:")
    print("  1. SuperCollider aberto")
    print("  2. Arquivo 'a_synth.scd' executado (Ctrl+A, Ctrl+Enter)")
    print("  3. Mensagem '[BARALHO] Pronto.' visivel no SC")
    print()

    if not state.ensure():
        return

    from a_osc import play_composition_osc, DEFAULT_HOST, DEFAULT_PORT
    host = prompt("Host", DEFAULT_HOST)
    port_str = prompt("Porta", str(DEFAULT_PORT))
    try:
        port = int(port_str)
    except ValueError:
        print(f"  [!] porta invalida, usando {DEFAULT_PORT}")
        port = DEFAULT_PORT

    print()
    play_composition_osc(state.notes, host=host, port=port, verbose=True)


def opt_play_midi(state: CompositionState):
    _print_header("TOCAR VIA MIDI")
    print()
    print("Sai como mensagens MIDI pra uma porta de saida do Windows.")
    print("Por padrao, vai tentar usar o sintetizador embutido do Windows")
    print("(Microsoft GS Wavetable Synth) - som basico mas faz barulho.")
    print()
    print("Pra DAW: abra a DAW antes e configure ela pra escutar a porta")
    print("MIDI virtual (loopMIDI etc) que aparece na lista.")
    print()

    # Lista portas pra usuario escolher
    from legado_midi import MidiPlayer, play_composition

    devices = MidiPlayer.list_devices()
    outputs = [(i, n) for i, n, is_out in devices if is_out]
    if not outputs:
        print("[!] Nenhuma porta MIDI de saida disponivel no sistema.")
        return

    print("Portas MIDI disponiveis:")
    for i, name in outputs:
        print(f"  [{i}] {name}")
    print()
    # Default: a primeira "Microsoft GS Wavetable Synth" se existir,
    # senao a primeira da lista
    default_idx = next(
        (i for i, n in outputs if 'wavetable' in n.lower() or 'gs' in n.lower()),
        outputs[0][0],
    )
    text = prompt("Escolha o ID da porta", str(default_idx))
    try:
        device_id = int(text)
    except ValueError:
        device_id = default_idx

    if not state.ensure():
        return

    print()
    # max_seconds = None nao existe nessa funcao - usa um cap absurdo
    cap = (state.target_seconds or 300) + 60
    play_composition(state.notes, device_id=device_id, max_seconds=cap, verbose=True)


def opt_export_files(state: CompositionState):
    _print_header("EXPORTAR ARQUIVOS (MIDI + MusicXML + TXT)")
    print()
    if not state.ensure():
        return

    from legado_partitura import composition_to_stream, export_midi, export_musicxml
    from nucleo_compositor import export_partitura_texto

    base = prompt("Nome base dos arquivos", "composicao_baralho")
    print()
    print("[INFO] Convertendo pra Stream music21...")
    score = composition_to_stream(
        state.notes,
        title=f"Baralho Musical (seed {state.seed})",
    )
    export_midi(score, f"{base}.mid")
    export_musicxml(score, f"{base}.musicxml")
    export_partitura_texto(
        state.notes,
        f"{base}.txt",
        title=f"Baralho Musical (seed {state.seed})",
        seed=state.seed,
    )
    print()
    print("Pra ver a partitura: abre o .musicxml no MuseScore (gratis).")
    print("Pra tocar o MIDI: abre o .mid em qualquer player ou DAW.")
    print(f"Pra ler nota por nota (cents, duracao em s, etc): abre o {base}.txt.")


def opt_osc_visualizer_web(state: CompositionState):
    _print_header("OSC + VISUALIZER WEB (browser)")
    print()
    print("Pre-requisitos:")
    print("  1. SuperCollider aberto com a_synth.scd rodando")
    print("  2. Vai abrir o browser automaticamente em http://localhost:8000")
    print()

    if not state.ensure():
        return

    from a_osc import DEFAULT_HOST, DEFAULT_PORT

    host = prompt("Host OSC", DEFAULT_HOST)
    port_str = prompt("Porta OSC", str(DEFAULT_PORT))
    try:
        osc_port = int(port_str)
    except ValueError:
        osc_port = DEFAULT_PORT

    http_str = prompt("Porta HTTP", "8000")
    try:
        http_port = int(http_str)
    except ValueError:
        http_port = 8000

    # Reusa a composicao ja gerada — chamamos run() mas pulando a geracao.
    # Em vez disso, fazemos os passos diretamente.
    import time as _time
    import webbrowser as _wb
    from a_visual_web import (
        start_http_server, start_osc_listener, BROADCASTER, WORD_SYNC_PORT,
    )
    from a_osc import play_composition_osc

    server = start_http_server(http_port)
    osc_listener = start_osc_listener(WORD_SYNC_PORT)
    url = f"http://localhost:{http_port}"
    try:
        _wb.open(url)
    except Exception:
        pass

    print(f"[INFO] Aguardando o browser conectar...")
    for _ in range(60):
        if BROADCASTER.client_count() > 0:
            break
        _time.sleep(0.1)
    if BROADCASTER.client_count() == 0:
        print(f"[AVISO] Nenhum browser conectou em {url} - tocando mesmo assim.")
    else:
        print(f"[OK] Browser conectado.")

    BROADCASTER.publish({"type": "compose_ready", "n_notes": len(state.notes)})

    def emit(event):
        BROADCASTER.publish(event)

    try:
        play_composition_osc(
            state.notes, host=host, port=osc_port,
            on_event=emit, verbose=True,
        )
    except KeyboardInterrupt:
        print("\n[INFO] Interrompido.")
    finally:
        BROADCASTER.publish({"type": "end"})
        print()
        print("[INFO] Fim. Server segue ate voce voltar pro menu.")
        ans = prompt("Fechar servidor agora? (s/n)", "s").lower()
        if ans.startswith('s'):
            server.shutdown()
            if osc_listener is not None:
                osc_listener.shutdown()


def opt_visualizador(state: CompositionState):
    _print_header("VISUALIZADOR (pygame)")
    print()
    print("Abre janela em tela cheia. Esc pra sair.")
    print("OBS: o visualizador tem seu proprio motor passo-a-passo")
    print("     (cresce sob demanda). Nao usa a composicao do menu.")
    print()
    ans = prompt("Abrir agora? (s/n)", "s").lower()
    if not ans.startswith('s'):
        return

    # Executa como script - tem main() proprio com loop pygame
    here = os.path.dirname(os.path.abspath(__file__))
    visualizador_path = os.path.join(here, "a_visual_pygame.py")
    if not os.path.exists(visualizador_path):
        print(f"[!] a_visual_pygame.py nao encontrado em {visualizador_path}")
        return

    import subprocess
    subprocess.call([sys.executable, visualizador_path])


def opt_cartomante_completa(state: CompositionState):
    _print_header("A CARTOMANTE - PECA COMPLETA (um terminal so)")
    print()
    print("Roda tudo junto:")
    print("  SYNTH (camada A)    - composicao toca em segundo plano")
    print("  HABITATS (camada B) - voce puxa cartas aqui no terminal")
    print("  VISUALIZADOR        - abre no browser automaticamente")
    print()
    print("Pre-requisitos:")
    print("  1. SuperCollider com a_synth.scd E b_synth.scd rodando")
    print()

    if not state.ensure():
        return

    import threading
    import webbrowser as _wb
    from a_osc import play_composition_osc, DEFAULT_HOST, DEFAULT_PORT
    from a_visual_web import start_http_server, start_osc_listener, WORD_SYNC_PORT
    from b_samples import MundoPlayer
    from b_teclado import print_help, parse_card, random_card

    host = DEFAULT_HOST
    port = DEFAULT_PORT

    http_str = prompt("Porta HTTP do visualizador", "8000")
    try:
        http_port = int(http_str)
    except ValueError:
        http_port = 8000

    server = start_http_server(http_port)
    osc_listener = start_osc_listener(WORD_SYNC_PORT)

    url = f"http://localhost:{http_port}"
    try:
        _wb.open(url)
    except Exception:
        pass
    print(f"[INFO] Visualizador aberto em {url}")

    # Evento pra saber quando a composicao encerrou
    synth_done = threading.Event()

    def _play_synth():
        try:
            play_composition_osc(state.notes, host=host, port=port, verbose=True)
        except Exception as e:
            print(f"\n[SYNTH] erro: {e}")
        finally:
            print("\n[SYNTH] composicao encerrada. Digite 'q' pra sair.")
            synth_done.set()

    # Prepara o baralho do mundo
    player = MundoPlayer(verbose=True)
    try:
        player.preload()
    except RuntimeError as e:
        print(f"[!] {e}")
        server.shutdown()
        if osc_listener:
            osc_listener.shutdown()
        return

    print("\n[OK] Tudo pronto. Iniciando synth...\n")
    print_help()

    synth_thread = threading.Thread(target=_play_synth, daemon=True)
    synth_thread.start()

    while not synth_done.is_set():
        try:
            raw = input("carta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        low = raw.lower()
        if low in ("q", "sair", "exit", "quit"):
            break
        if low in ("?", "h", "help", "ajuda"):
            print_help()
            continue
        if raw == ".":
            player.stop()
            print("  ... silencio (habitat encerrado)")
            continue
        if raw == "":
            rank, suit = random_card()
        else:
            parsed = parse_card(raw)
            if parsed is None:
                print("  [!] carta invalida. '?' pra ajuda.")
                continue
            rank, suit = parsed

        player.play_card(rank, suit)

    player.stop()
    print("A cartomante recolhe o baralho.")
    print()
    ans = prompt("Fechar servidor HTTP? (s/n)", "s").lower()
    if ans.startswith('s'):
        server.shutdown()
        if osc_listener:
            osc_listener.shutdown()


def opt_cartomante_dupla(_state: CompositionState):
    _print_header("CARTOMANTE DUPLA (browser + teclado)")
    print()
    print("Abre o visualizador no browser (cartomante virtual) E roda o")
    print("teclado de cartas aqui no terminal (cartomante real), em paralelo.")
    print()
    print("Pre-requisitos:")
    print("  1. SuperCollider com a_synth.scd E b_synth.scd rodando")
    print()

    http_str = prompt("Porta HTTP", "8000")
    try:
        http_port = int(http_str)
    except ValueError:
        http_port = 8000

    import webbrowser as _wb
    from a_visual_web import start_http_server, start_osc_listener, WORD_SYNC_PORT
    from b_samples import MundoPlayer
    from b_teclado import print_help, parse_card, random_card

    server = start_http_server(http_port)
    osc_listener = start_osc_listener(WORD_SYNC_PORT)

    url = f"http://localhost:{http_port}"
    try:
        _wb.open(url)
    except Exception:
        pass
    print(f"[INFO] Browser aberto em {url}")
    print()

    player = MundoPlayer(verbose=True)
    try:
        player.preload()
    except RuntimeError as e:
        print(f"[!] {e}")
        server.shutdown()
        if osc_listener:
            osc_listener.shutdown()
        return

    print("\n[OK] tudo pronto. Puxe uma carta.\n")
    print_help()

    while True:
        try:
            raw = input("carta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        low = raw.lower()
        if low in ("q", "sair", "exit", "quit"):
            break
        if low in ("?", "h", "help", "ajuda"):
            print_help()
            continue
        if raw == ".":
            player.stop()
            print("  ... silencio (habitat encerrado)")
            continue
        if raw == "":
            rank, suit = random_card()
        else:
            parsed = parse_card(raw)
            if parsed is None:
                print("  [!] carta invalida. '?' pra ajuda.")
                continue
            rank, suit = parsed

        player.play_card(rank, suit)

    player.stop()
    print("A cartomante recolhe o baralho.")
    print()
    ans = prompt("Fechar servidor HTTP? (s/n)", "s").lower()
    if ans.startswith('s'):
        server.shutdown()
        if osc_listener:
            osc_listener.shutdown()


# =============================================================================
# MENU PRINCIPAL
# =============================================================================

MENU = """
[1] Tocar via OSC (SuperCollider)         - som de qualidade
[4] Abrir visualizador (pygame)
[5] OSC + Visualizer web (browser, 16bit) - som + visual ao vivo
[6] Cartomante dupla (browser + teclado)  - visual no browser, cartas no terminal
[7] A Cartomante - peca completa          - synth + cartas num terminal so
[0] Sair
"""
# [2] MIDI e [3] Exportar MusicXML escondidos do menu (peca ao vivo nao usa).
#     opt_play_midi() e opt_export_files() continuam definidos abaixo, intactos,
#     caso precise reativar — basta re-adicionar as linhas no MENU e no dispatch.


def main():
    state = CompositionState()

    print()
    print("=" * 70)
    print("SISTEMA BARALHO MUSICAL")
    print("=" * 70)
    print("52 cartas -> 7 parametros por nota -> composicao musical")

    while True:
        print()
        print("-" * 70)
        print(f"Composicao atual: {state.info()}")
        print(MENU)
        choice = prompt("Escolha", "1")
        if choice in ('0', 'q', 'sair', 'exit'):
            print("Tchau!")
            return
        elif choice == '1':
            try:
                opt_play_osc(state)
            except Exception as e:
                print(f"[!] Erro: {e}")
        elif choice == '4':
            try:
                opt_visualizador(state)
            except Exception as e:
                print(f"[!] Erro: {e}")
        elif choice == '5':
            try:
                opt_osc_visualizer_web(state)
            except Exception as e:
                print(f"[!] Erro: {e}")
        elif choice == '6':
            try:
                opt_cartomante_dupla(state)
            except Exception as e:
                print(f"[!] Erro: {e}")
        elif choice == '7':
            try:
                opt_cartomante_completa(state)
            except Exception as e:
                print(f"[!] Erro: {e}")
        else:
            print(f"  [!] opcao '{choice}' nao reconhecida.")


if __name__ == "__main__":
    main()
