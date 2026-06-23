# Debug: Falha na abertura da webcam (Errno 35)

## Sintoma

Na **primeira** tentativa de rodar `python main.py` -> opção 2 (webcam), o programa
imprime:

```
[!] Erro: [Errno 35] Resource temporarily unavailable
```

e volta pro menu. Na **segunda** tentativa (sem reiniciar nada), a câmera abre
normalmente.

## Condição de reprodução conhecida

- O erro ocorre quando o **SuperCollider NÃO está aberto** (ou acabou de ser
  fechado).
- Com o SuperCollider **aberto e rodando** (`a_synth.scd` + `b_synth.scd`), a
  câmera abre já na primeira tentativa.

## Hipótese principal

`[Errno 35]` é `EAGAIN` no macOS — a câmera ainda não está pronta para entregar
quadros. Possíveis causas:

1. **Contention de permissão TCC**: o macOS serializa pedidos de câmera entre
   processos. Quando o SuperCollider está ativo (e já obteve a permissão de câmera
   ou de microfone), o sistema libera o dispositivo mais rápido para o próximo
   processo.
2. **Tempo de aquecimento do dispositivo**: a câmera demora ~200–500 ms para
   entregar o primeiro quadro válido depois de aberta via `cv2.VideoCapture`. Sem
   outro processo "mantendo" o daemon `AVCaptureSession` ativo, esse tempo é maior.
3. **`VDCAssistant` / `CMIODPSimpleCapture`**: processo de câmera do macOS que pode
   estar em estado de sleep quando nenhum app usa câmera; o primeiro cliente o
   acorda, o segundo já pega ele no ar.

## Diagnóstico (2026-06-23)

**Iteração 1** — hipótese: backend de câmera errado.
- `pgrep VDCAssistant` retornou PID ativo → daemon NÃO dorme sem SC.
- `CAP_AVFOUNDATION` isolado abriu em 0.83 s sem `OSError`.
- Fix aplicado: macOS usa `CAP_AVFOUNDATION` primeiro em `_open_camera`.
- Resultado: **ainda falhou** na primeira tentativa via `main.py`.

**Iteração 2** — causa raiz real encontrada.
- O erro ocorre ANTES de `[MUNDO] 30 habitats carregados`, dentro de `preload()`.
- `MundoPlayer.client` é um `pythonosc.SimpleUDPClient` com socket em **modo
  não-bloqueante** (`blocking=False`, `timeout=0.0`).
- `preload()` envia 30 mensagens `/mundo/load` em rajada rápida. Sem SC ouvindo,
  o kernel não drena o buffer UDP; numa das entregas o buffer satura e lança
  `OSError errno 35 (EAGAIN)`.
- Com SC aberto, os pacotes são consumidos rápido o suficiente — nunca satura.
- **Fix definitivo**: `self.client._sock.setblocking(True)` em `b_samples.py`
  logo após criar o cliente. Em modo bloqueante, o kernel espera o buffer vazar
  em vez de lançar EAGAIN. Verificado: `preload()` completa sem erro sem SC.

## O que foi corrigido

1. `_try_open` (`b_aruco.py`): captura `OSError` no loop de leitura, retry com
   `sleep(0.05)`, até 20 tentativas. Mitigação de segurança para casos futuros.
2. `_open_camera` (`b_aruco.py`): no macOS usa `CAP_AVFOUNDATION` antes do
   backend padrão — inicialização mais estável.
3. `MundoPlayer.__init__` (`b_samples.py`): força `_sock.setblocking(True)` no
   cliente OSC — elimina EAGAIN em rajadas de envio sem SC ouvindo.

## Status

**Resolvido.** `preload()` e câmera abrem na primeira tentativa sem SuperCollider.
