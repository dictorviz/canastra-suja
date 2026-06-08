"""
VISUALIZER OSC + WEB - SISTEMA BARALHO MUSICAL

Sobe um servidor HTTP local que serve o visualizador web (visualizer/) e
publica os eventos musicais via Server-Sent Events (SSE). Em paralelo,
toca a composicao via OSC (mesmo player do a_osc.py), entao o som
sai pelo SuperCollider e o visual aparece no browser.

USO:
    python a_visual_web.py [target_seconds] [seed]

    Por padrao abre http://localhost:8000 no navegador automaticamente.

ARQUITETURA:
    [Compositor] -> [OscPlayer] --OSC--> [SuperCollider] (audio)
                         |
                         +-- on_event() --> [SSE queue] --> [Browser] (visual)
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Optional

import nucleo_perec
from nucleo_compositor import Compositor
from a_osc import (
    DEFAULT_HOST as OSC_HOST,
    DEFAULT_PORT as OSC_PORT,
    play_composition_osc,
)

# OSC listener (SC -> Python) pra eventos de sincronia (ex: word_now)
from pythonosc import dispatcher as _osc_dispatcher
from pythonosc import osc_server as _osc_server

# Porta onde o Python escuta SC. Tem que bater com NetAddr no a_synth.scd.
WORD_SYNC_PORT = 57121


# =============================================================================
# CONFIGURACAO
# =============================================================================

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(HERE, "visualizer")

DEFAULT_HTTP_PORT = 8000


def _open_browser_kiosk(url: str) -> bool:
    """Tenta abrir Chrome/Edge em modo --app (janela limpa, sem barra de URL).
    Retorna True se conseguiu lancar um navegador customizado."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome"),
        shutil.which("msedge"),
    ]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            subprocess.Popen([
                path,
                f"--app={url}",
                "--start-fullscreen",
                "--new-window",
            ])
            return True
        except OSError:
            continue
    return False


# =============================================================================
# BROADCASTER: registra clientes SSE e empurra eventos pra cada um
# =============================================================================

class EventBroadcaster:
    """Mantem uma lista de Queues, uma por cliente SSE conectado."""

    def __init__(self):
        self._clients: "list[queue.Queue]" = []
        self._lock = threading.Lock()

    def register(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=256)
        with self._lock:
            self._clients.append(q)
        return q

    def unregister(self, q: queue.Queue):
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def publish(self, event: dict):
        payload = json.dumps(event, ensure_ascii=False)
        with self._lock:
            dead = []
            for q in self._clients:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                if q in self._clients:
                    self._clients.remove(q)

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)


BROADCASTER = EventBroadcaster()


# =============================================================================
# HTTP HANDLER (estaticos + SSE)
# =============================================================================

class VisualizerHandler(SimpleHTTPRequestHandler):
    """Serve arquivos de visualizer/ + endpoint /events (SSE)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_ROOT, **kwargs)

    def log_message(self, format, *args):
        # Silencia o spam do http.server (so mostra erros 5xx)
        if args and isinstance(args[1], str) and args[1].startswith('5'):
            super().log_message(format, *args)

    def do_GET(self):
        if self.path == "/events":
            self._handle_sse()
            return
        if self.path == "/capitulos":
            self._handle_capitulos_list()
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/capitulo":
            self._handle_set_capitulo()
            return
        self.send_error(404)

    def _handle_capitulos_list(self):
        """Retorna a lista de capitulos + o ativo atual."""
        caps = []
        for c in nucleo_perec.list_capitulos():
            caps.append({
                "id": c.id,
                "display_id": c.display_id,
                "nome": c.nome,
                "parent": c.parent,
                "attractor": c.attractor,
            })
        body = json.dumps({
            "capitulos": caps,
            "atual": nucleo_perec.get_capitulo().id,
        }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_set_capitulo(self):
        """POST /capitulo body={"id":"4.2"} - troca o capitulo ativo."""
        try:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            cid = str(data.get("id", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return
        ok = nucleo_perec.set_capitulo(cid)
        if not ok:
            self.send_error(404, f"Capitulo '{cid}' nao encontrado")
            return
        # on_change registrado no run() vai propagar via SSE pros browsers
        cap = nucleo_perec.get_capitulo()
        body = json.dumps({
            "ok": True, "id": cap.id, "display_id": cap.display_id,
            "nome": cap.nome, "attractor": cap.attractor,
        }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        q = BROADCASTER.register()
        try:
            # ping inicial pra abrir o canal
            self._write_event({"type": "hello"})
            while True:
                try:
                    payload = q.get(timeout=15.0)
                except queue.Empty:
                    # comment-keepalive
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    continue
                try:
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
        finally:
            BROADCASTER.unregister(q)

    def _write_event(self, event: dict):
        try:
            self.wfile.write(
                f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
            )
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


# =============================================================================
# MAIN
# =============================================================================

def start_http_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), VisualizerHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[HTTP] visualizer em http://localhost:{port}")
    return server


# =============================================================================
# OSC LISTENER (SC -> Python) - sincronia palavra-a-palavra
# =============================================================================
# SC envia /baralho/word_now [word, idx, total] no instante em que cada
# Synth(\baralhoWord) eh disparado pela Routine. Aqui propagamos via SSE
# pro visualizer destacar UMA palavra de cada vez, no tempo certo.

def _on_word_now(_address, *args):
    if not args:
        return
    word = str(args[0])
    idx = int(args[1]) if len(args) > 1 else 0
    total = int(args[2]) if len(args) > 2 else 1
    source = str(args[3]) if len(args) > 3 else "echo"   # 'echo' | 'recitativo'
    BROADCASTER.publish({
        "type": "word_now",
        "word": word,
        "idx": idx,
        "total": total,
        "source": source,
    })


def start_osc_listener(port: int = WORD_SYNC_PORT):
    """Sobe o servidor OSC que escuta /baralho/word_now do SC. Retorna o
    objeto server (chamar .shutdown() pra encerrar)."""
    disp = _osc_dispatcher.Dispatcher()
    disp.map("/baralho/word_now", _on_word_now)
    try:
        server = _osc_server.ThreadingOSCUDPServer(("127.0.0.1", port), disp)
    except OSError as e:
        print(f"[OSC<-] AVISO: nao consegui abrir porta {port}: {e}")
        print(f"[OSC<-] sync palavra-a-palavra ficara desligado.")
        return None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[OSC<-] escutando SC em 127.0.0.1:{port} (/baralho/word_now)")
    return server


def _resolve_capitulo_id(arg: str) -> Optional[str]:
    """Resolve um arg do usuario pra um id de capitulo valido.
    Aceita id exato ('0', '4.2', 'INF'), '∞', ou prefixo de nome/attractor
    (ex: 'cama', 'porta', 'mundo')."""
    if not arg:
        return None
    arg = arg.strip()
    if not arg:
        return None
    if arg in ("∞", "inf", "infinity"):
        return nucleo_perec.INFINITY_ID
    # match exato pelo id
    for c in nucleo_perec.list_capitulos():
        if c.id.lower() == arg.lower():
            return c.id
    # match pelo attractor
    for c in nucleo_perec.list_capitulos():
        if c.attractor.lower() == arg.lower():
            return c.id
    # match prefixo do nome
    low = arg.lower()
    for c in nucleo_perec.list_capitulos():
        if c.nome.lower().startswith(low):
            return c.id
    return None


def run(
    target_seconds: float = 60.0,
    seed: Optional[int] = 42,
    capitulo: Optional[str] = None,
    http_port: int = DEFAULT_HTTP_PORT,
    osc_host: str = OSC_HOST,
    osc_port: int = OSC_PORT,
    open_browser: bool = True,
    verbose: bool = True,
):
    # Aplica o capitulo escolhido ANTES de comecar a compor / abrir o browser
    if capitulo:
        cid = _resolve_capitulo_id(capitulo)
        if cid is None:
            print(f"[ERRO] Capitulo '{capitulo}' nao encontrado.")
            print("Capitulos disponiveis:")
            for c in nucleo_perec.list_capitulos():
                print(f"  {c.display_id:>4}  {c.nome}  (attractor={c.attractor})")
            sys.exit(1)
        nucleo_perec.set_capitulo(cid)

    cap_inicial = nucleo_perec.get_capitulo()

    print("=" * 70)
    print("BARALHO MUSICAL - VISUALIZER WEB + OSC")
    print("=" * 70)
    print()
    print(f"[INFO] OSC -> {osc_host}:{osc_port}  (SuperCollider)")
    print(f"[INFO] HTTP -> http://localhost:{http_port}")
    print(f"[INFO] Capitulo: {cap_inicial.display_id} - {cap_inicial.nome}  "
          f"(attractor={cap_inicial.attractor})")
    print()
    print("Pre-requisitos:")
    print("  1. SuperCollider aberto com a_synth.scd rodando")
    print("  2. Browser moderno (Chrome/Firefox/Edge)")
    print()

    server = start_http_server(http_port)
    osc_listener = start_osc_listener(WORD_SYNC_PORT)
    url = f"http://localhost:{http_port}"

    if open_browser:
        if not _open_browser_kiosk(url):
            try:
                webbrowser.open(url)
            except Exception:
                pass

    print(f"[INFO] Aguardando o browser conectar...")
    # Espera ate 6s pra um cliente conectar antes de comecar
    for _ in range(60):
        if BROADCASTER.client_count() > 0:
            break
        time.sleep(0.1)

    if BROADCASTER.client_count() == 0:
        print(f"[AVISO] Nenhum browser conectou em {url} - tocando mesmo assim.")
    else:
        print(f"[OK] Browser conectado.")

    print()
    print(f"[INFO] Compondo (alvo {target_seconds:.0f}s, seed={seed})...")
    comp = Compositor()
    comp.compose(seed=seed, verbose=False, target_seconds=target_seconds)
    print(f"[OK] {len(comp.notes)} notas geradas.")
    print()

    # Propaga mudanca de capitulo (do POST /capitulo) pra todos os browsers via SSE
    def _on_capitulo_change(cap):
        BROADCASTER.publish({
            "type": "capitulo_change",
            "id": cap.id,
            "display_id": cap.display_id,
            "nome": cap.nome,
            "attractor": cap.attractor,
        })

    nucleo_perec.on_change(_on_capitulo_change)

    # Aviso inicial ao browser: vai comecar
    cap_atual = nucleo_perec.get_capitulo()
    BROADCASTER.publish({
        "type": "compose_ready",
        "n_notes": len(comp.notes),
        "capitulo": {
            "id": cap_atual.id, "display_id": cap_atual.display_id,
            "nome": cap_atual.nome, "attractor": cap_atual.attractor,
        },
    })

    def emit(event: dict):
        BROADCASTER.publish(event)

    try:
        play_composition_osc(
            comp.notes,
            host=osc_host,
            port=osc_port,
            on_event=emit,
            verbose=verbose,
        )
    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuario.")
    finally:
        BROADCASTER.publish({"type": "end"})

    print()
    print("[INFO] Fim. Ctrl+C pra fechar o servidor.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    server.shutdown()
    if osc_listener is not None:
        osc_listener.shutdown()


def main():
    """Uso: python a_visual_web.py [target_seconds] [seed] [capitulo]

    capitulo pode ser:
      - id exato: '0', '4.2', '12.6', 'INF'
      - simbolo: '∞'
      - attractor: 'cama', 'porta', 'mundo', 'inabitavel'
      - prefixo do nome: 'A cama', 'O quarto'
    """
    target_seconds = 60.0
    seed: Optional[int] = 42
    capitulo: Optional[str] = None

    if len(sys.argv) > 1:
        try:
            target_seconds = float(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        try:
            seed = int(sys.argv[2])
        except ValueError:
            pass
    if len(sys.argv) > 3:
        capitulo = sys.argv[3]

    run(target_seconds=target_seconds, seed=seed, capitulo=capitulo)


if __name__ == "__main__":
    main()
