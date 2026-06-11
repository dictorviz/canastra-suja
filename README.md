# CANASTRA SUJA

> *Um baralho de Buraco que, carta a carta, vai sujando o som do mundo.*

Performance eletroacústica ao vivo construída sobre o jogo de **Buraco**
(2–4 jogadores). Não há palavras nem voz, e **nada toca sozinho: os jogadores
tocam a peça.** Cada carta da vida real faz **duas coisas ao mesmo tempo**, em
duas camadas:

- **CAMA** (`a_*`) — cada carta **toca o vibrafone ao vivo**: gira um parâmetro
  de um "painel" de 7 botões e dispara uma badalada na hora (o **estado
  rolante**, ver `a_cama.py`). A matemática generativa que já existia (operação
  por naipe → 7 parâmetros) continua intacta — só que agora a **entrada são as
  cartas reais**, não um baralho sorteado. Sem carta, sem som.
- **MUNDO** (`b_*`) — a mesma carta faz uma biblioteca de **habitats sonoros
  gravados** (mp3/wav) atravessar pro próximo (crossfade) e soma ao **nível de
  degradação**. O jogo vai, carta a carta, **sujando o som**.

A captação das cartas reais é por **webcam + ArUco**: assim que um jogador vira
uma carta, a câmera reconhece qual é (valor + naipe) e o sistema toca a cama +
dispara o habitat e o glitch. Tem também um modo **teclado** que simula a
virada (pra ensaiar sem câmera).

> A peça nasceu como *A Cartomante* (tarô/Perec, com voz). **Canastra Suja** é o
> pivô: trocou a poética (do tarô pro Buraco), a fonte da carta (do teclado pra
> webcam) e **tirou a voz**. A camada de voz/texto do Perec foi **arquivada, não
> apagada** (ver [`arquivo/`](#o-que-ficou-em-arquivo)).

---

## Como funciona (a cadeia)

```
                              ┌► a_cama  ──► a_synth.scd (/baralho/*)  [vibrafone ao vivo]
  carta virada ─► webcam/ArUco (b_aruco) │
  (mesa real)    ou teclado   (b_teclado)├─► b_partida ─► b_samples ──► b_synth.scd (/mundo/*) [habitat]
                                          │             └► b_glitch  ──► b_synth.scd (/mundo/*) [degradação]
                                          └────────────────────────────► SuperCollider ─► alto-falantes
```

1. **A carta** da vida real entra pelo teclado (`b_teclado.py`) ou pela webcam
   (`b_aruco.py`). As duas falam a mesma língua — `(valor, naipe)` — então uma
   substitui a outra sem mexer no resto. Tudo passa pelo `b_partida.py`.
2. **A cama** (`a_cama.py`) recebe a carta, roda a operação do naipe (a
   matemática do `nucleo_compositor`), gira **um** dos 7 parâmetros do vibrafone
   e **dispara a badalada na hora** (`a_synth.scd`). O painel persiste entre
   cartas — é o **estado rolante** (ver abaixo).
3. **O mundo** (`b_samples.py`): 43 habitats longos embaralhados. A carta sorteia
   o próximo e o mundo atravessa pra ele (crossfade, em `b_synth.scd`).
4. **A degradação** (`b_glitch.py`) sobe a cada carta. O **naipe** escolhe a
   operação sonora do glitch, o **valor** a força do golpe ("kick"), e o
   **acúmulo** a profundidade — começa quase limpo e termina à beira do
   desmoronamento.

As duas camadas usam a **mesma porta OSC (57120)**, mas **namespaces separados**
(`/baralho/*` para a cama, `/mundo/*` para o mundo), então convivem sem colisão.

### O estado rolante (como os jogadores "tocam" a cama)

A nota do vibrafone tem **7 botões** (os 7 parâmetros, nesta ordem): `NOTA`,
`ALTERAÇÃO (cents)`, `RITMO→RINGAR`, `BPM→ECOS`, `DINÂMICA`, `ARTICULAÇÃO`,
`OITAVA`. O painel **nasce todo no centro** (neutro) e **cada carta gira UM
botão** — o da vez — e dispara uma badalada com o painel atual. Depois do 7º
botão volta pro 1º, em círculo, pra sempre.

Assim **toda carta soa na hora** e a "nota" vira um som vivo que a mesa esculpe
junto. Como o relógio passa a ser a mão humana, os dois parâmetros temporais
deixam de fingir um compasso e viram **ressonância**: o ritmo controla **quanto
a barra ringa** e o BPM controla o **espaçamento dos ecos**. De brinde: a cama
começa neutra e vai ficando característica conforme o jogo anda — sujando junto
com os habitats.

**Gramática:** `A` (Ás) = a cama **respira** (silencia naquela carta); `10` =
**fermata** (ringa bem mais); `J/Q/K` já são passado/presente/futuro na própria
matemática (ao vivo, o futuro do Rei não existe → cai no neutro do naipe);
`JOKER` = **acento** (re-badala o painel no forte).

---

## Os 4 naipes — operações

A peça **não tem cosmologia** (nada de água/terra/ar/fogo). O naipe é uma
**operação**: matemática na camada A, sonora na camada B.

### Na camada A (o virtual) — cada naipe é uma operação matemática

A composição generativa interpreta cada carta como uma **operação** entre o
valor da carta e o evento anterior (ver `nucleo_compositor.py`):

| Naipe | Cor | Operação | Elemento neutro (identidade) |
|---|---|---|---|
| ♣ **Paus** | preto (+) | `gcd(atual, anterior)` | 0 |
| ♦ **Ouros** | vermelho (−) | `atual − anterior` | 0 |
| ♥ **Copas** | vermelho (−) | `atual + anterior` | 0 |
| ♠ **Espadas** | preto (+) | `lcm(atual, anterior)` | 1 |

Naipes vermelhos dão valor **negativo**, pretos **positivo** (o `10` é sempre
`+10`, neutro). O "elemento neutro" aí é o da **operação** (identidade do `gcd`,
do `lcm`, da soma) — não tem nada de místico. `J/Q/K` são cartas de **tempo**
(passado/presente/futuro), não têm valor próprio — ver detalhe no arquivo.

### Na camada B (o mundo) — cada naipe é uma operação sobre o som

A mesma lógica de "naipe = operação", agora aplicada ao habitat gravado:

| Naipe | Operação sonora | O som... |
|---|---|---|
| ♥ **Copas** | **desafina** (`detune`) | um cluster de parciais escorrega de altura, afunda |
| ♦ **Ouros** | **congela** (`freeze`) | uma janelinha do habitat trava e repete |
| ♠ **Espadas** | **fragmenta** (`shards`) | *(placeholder — ver abaixo)* |
| ♣ **Paus** | **satura** (`saturate`) | o habitat queima (drive + fold), distorce |

> **♠ Espadas — em aberto.** No projeto antigo Espadas cortava a voz do Perec em
> cacos (granular sobre as palavras). Como a voz saiu, o cache de voz fica
> vazio e os shards saem **mudos** — sem quebrar nada. A decidir: fragmentar os
> próprios samples? bitcrush? reverse? (TODO em `b_glitch.py` e `b_synth.scd`).

---

## Arquivos — coisa por coisa

> **Nunca programou?** Cada arquivo `.py` e `.scd` está comentado **linha a linha,
> pra leigo** (um "professor pra quem nunca viu código"), e há um guia-alicerce
> em [`PYTHON_DO_ZERO.md`](PYTHON_DO_ZERO.md) que ensina o básico do zero
> (variável, lista, dicionário, função, classe…). Ordem sugerida de leitura:
> `b_buraco → b_samples → b_teclado → b_aruco → a_cama → b_partida → a_osc →
> nucleo_compositor → main`. Os `.scd` (SuperCollider) trazem um "LEIA PRIMEIRO"
> explicando que são o lado do **som**.

### Ponto de entrada

- **`main.py`** — o menu da peça (`python main.py`). Duas opções, as duas
  perguntam jogadores (2–4) + seed e chamam a partida (a cama agora é tocada
  pelas cartas, dentro da `Partida` — **não há mais loop autônomo**):
  - `[1]` **Teclado** (`opt_jogar`) — cartas digitadas;
  - `[2]` **Webcam/ArUco** (`opt_aruco`) — cartas pela câmera (a janela é a
    projeção).
  - A **seed** só embaralha o baralho do mundo (habitats); a cama responde às
    cartas, não a um sorteio.

### CAMADA A — a cama (o vibrafone tocado pelas cartas)

- **`a_cama.py`** — a **cama ao vivo** (o **estado rolante**). Recebe cada carta
  da partida e toca o vibrafone na hora. A classe `CamaViva`:
  - guarda o **painel** (os 7 parâmetros, mapped_key de cada um, começando no
    centro) e um ponteiro `idx` que **gira** 0→6→0;
  - `tocar_carta(rank, suit)` — roda a operação do naipe no `InterpretadorEventos`
    (matemática do `nucleo_compositor`, com `next_card=None` → o futuro do Rei
    cai no neutro), mexe **um** botão (o da vez), e dispara `/baralho/note` pro
    `a_synth.scd` **sem bloquear** (o SC cuida do envelope). `A`=respira (não
    soa), `10`=fermata (ringa o dobro), `tocar_joker()`=acento;
  - traduz o painel pra nota: `RITMO→ringar` (segundos de ressonância, não
    duração métrica) e `BPM→ecos`. Os outros 5 botões viram pitch/cents/dinâmica/
    articulação/oitava como sempre.

- **`nucleo_compositor.py`** — o **motor da matemática** (reusado pela cama ao
  vivo, e ainda roda autônomo no demo do `a_osc.py`). As peças:
  - `Suit` / `Card` / `Baralho` — o baralho de 52 cartas (usado só no modo
    autônomo; ao vivo o "baralho" é a mesa real).
  - **Os 7 parâmetros** (tabelas `PARAM_*`), na ordem: `NOTA`, `ALTERAÇÃO
    (cents)`, `FIGURA RÍTMICA`, `ANDAMENTO (BPM)`, `DINÂMICA`, `ARTICULAÇÃO`,
    `OITAVA`.
  - **Operação por naipe** (`suit_operation`, `signed_gcd`, `signed_lcm`):
    cada carta faz `E_novo = valor_atual OP E_anterior`. `fold_range` dobra o
    resultado de volta pro intervalo musical `[-10, +10]` (como uma corda
    refletindo, preservando a polaridade — diferente do módulo).
  - **Cartas de ação** `J/Q/K` (`InterpretadorEventos.process_card`):
    `J`=passado (herda o valor da carta anterior), `Q`=presente (identidade do
    naipe + espelho paramétrico), `K`=futuro (espia a próxima carta + espelho —
    que ao vivo não existe, então cai no neutro).
  - `Compositor.compose(seed, target_seconds)` gera uma composição inteira de
    uma vez (modo **autônomo**, usado pelo demo do `a_osc.py`). Tem também export
    de "partitura escrita" em texto (`export_partitura_texto`).

- **`a_osc.py`** — o driver OSC **autônomo** (a cama generativa antiga, hoje só
  pra **testar o synth**: `python a_osc.py 60`). `OscPlayer.play_note` traduz uma
  `Note` em `/baralho/note` e **dorme** a duração (toca uma composição inteira em
  sequência). Na peça ao vivo quem manda `/baralho/note` é o `a_cama.py` (sem
  dormir). **Sem voz** em nenhum dos dois: ninguém dispara `/baralho/fala_*`.

- **`a_synth.scd`** — o **synth da cama** no SuperCollider (namespace
  `/baralho/*`). Boota o servidor, define os SynthDefs e os receptores OSC.
  Recebe `/baralho/note` (do `a_cama.py`, ao vivo) e toca a badalada:
  - `~mainSynth` é o timbre da nota. **Padrão = `\baralhoVibeKlank`** (o
    **vibrafone**, banco de ressonadores `DynKlank` com parciais inarmônicas de
    barra de metal). Alternativas pra A/B: `\baralho` (o original serra+tri+sin
    com vibrato) e `\baralhoVibeAdd` (vibrafone aditivo). Trocar é só rodar a
    linha `~mainSynth = ...`.
  - **Enriquecimentos** disparados pelo handler `/baralho/note`:
    `\baralhoEcho` (ecos harmônicos ping-pong com degradação analógica
    progressiva — wow/flutter, LPF, saturação por eco) e `\baralhoSparkle`
    (parciais extras com onset atrasado, só pra notas > 2 s).
  - **3 reverbs em buses paralelos**: `\baralhoRevSpring` (mola), `…Hall`
    (sala) e `…Plate` (placa). A articulação da nota escolhe pra qual reverb
    mandar, e a mistura depende da frequência (agudos recebem mais).
  - **Voz (dormente)**: `\baralhoVox` (síntese formântica fonema a fonema, com
    tabela `~voxFormants` pt-br) e `\baralhoWord` (sussurro via vocoder sobre
    WAVs de TTS). Eram a voz do Perec; **ninguém dispara mais** `/baralho/fala_*`.
    Ficaram aqui intactos, mudos.

### CAMADA B — o mundo (as cartas da vida real)

- **`b_buraco.py`** — as **regras do Buraco como dados** (não é um motor de
  Buraco). Tem a `PONTOS` (valor das cartas), os curingas (`JOKER`=curingão,
  `2`=curinguinha), os tipos de `CANASTRAS` (de onde vem o nome *suja*) e a
  classe **`Mesa`**: jogadores, duplas (no jogo de 4: J1+J3 × J2+J4) e **de
  quem é a vez** (`proximo()` gira em sentido horário). Só a estrutura de turnos
  da performance — pontuação real acontece na mesa física.

- **`b_samples.py`** — o **baralho do mundo** (os habitats):
  - `WorldDeck` — embaralha as chaves dos 43 habitats; `draw()` devolve o
    próximo sem repetir até esgotar, aí reembaralha (sem emendar a mesma carta
    na virada).
  - `MundoPlayer` — manda OSC pro `b_synth.scd`. `preload()` lê `samples/*.wav`,
    manda `/mundo/load` de cada um e mede a duração. `play_card(rank, suit)`
    sorteia o próximo habitat e manda `/mundo/bed` (crossfade); o **naipe**
    define a espacialização (pan). Habitats longos (≥ 12 s) loopam; curtos tocam
    uma vez. Volume baixo por padrão (fantasmagórico, fundo).

- **`b_glitch.py`** — a **degradação** (a carta suja o som):
  - `GlitchEngine` acumula o nível global de corrupção (`level`, 0→1, sobe
    `step` por carta) e a cada carta manda `/mundo/glitch [tipo, level, kick]`
    pro `b_synth.scd`.
  - `SUIT_GLITCH` mapeia o **naipe → sabor** (detune/freeze/shards/saturate);
    `_kick_for_rank` mapeia o **valor → força** do golpe (A=leve … K=pesado).
  - `load_voice()` carrega palavras do `tts_cache/` pro SC (são as que Espadas
    fragmentaria) — hoje o cache está vazio, então shards ficam mudos
    (placeholder).

- **`b_synth.scd`** — o som do mundo no SuperCollider (namespace `/mundo/*`).
  **Aditivo**: não toca no `a_synth.scd` nem lê o sinal da camada A — são vozes
  paralelas que *soam como* a máquina se desfazendo. Sem este arquivo carregado,
  o mundo toca limpo. Define:
  - `\mundoBed` — o habitat: `PlayBuf` longo com LPF (véu de distância) + reverb
    embutido, com crossfade por `gate`/envelope. `\mundoSample` — one-shot
    pontual.
  - Os **4 glitches**, um por naipe: `\glitchDetune` (cluster que afunda),
    `\glitchFreeze` (janelinha do habitat travada via `Phasor`+`BufRd`),
    `\glitchShards` (granula uma palavra do Perec com `TGrains`) e
    `\glitchSaturate` (o habitat atual com `tanh`+`fold2`). Todos escalam com
    `level` e `kick`.
  - Receptores OSC: `/mundo/load`, `/mundo/bed`, `/mundo/trigger`, `/mundo/stop`,
    `/mundo/clear`, `/mundo/voz_load`, `/mundo/glitch`, `/mundo/glitch_reset`.

- **`b_partida.py`** — o **motor da partida**: junta tudo num objeto só.
  `Partida` tem a `Mesa` (b_buraco) + a `CamaViva` (a_cama) + o `MundoPlayer`
  (b_samples) + o `GlitchEngine` (b_glitch). Cada `jogar(rank, suit)` **toca a
  cama** (vibrafone ao vivo) + atravessa um habitat + soma degradação + **passa
  a vez**. `jogar_joker()` (curingão = acento na cama + força máxima no mundo),
  `reset()` (zera a degradação **e** o painel da cama — nova mão), `silencio()`,
  `encerrar()`. Expõe `vez_label`, `corrupcao` e `ultima_str()` pra UI. É
  **reutilizável**: teclado e webcam chamam os mesmos métodos.

- **`b_teclado.py`** — fonte de carta por **teclado** (simula a webcam). Lê a
  carta digitada (`QC`, `10O`, `AP`, `7E`, `JOKER`, ENTER=aleatória,
  `.`=silêncio, `r`=nova mão, `q`=sair), faz o parse e chama os métodos da
  `Partida`. `run_partida(num, seed)` é o laço, reaproveitado pelo `main.py`.

- **`b_aruco.py`** — fonte de carta por **webcam + ArUco** (OpenCV). Como o
  Buraco joga com **2 baralhos**, são `2 × 54 = 108` marcadores (`DICT_4X4_250`,
  ids 0–107). A função:
  - `id_to_card` / `card_to_id` — o mapa carta ↔ marcador. Cada baralho tem 54
    ids; o **deck B (54–107) dobra sobre o deck A** (`local = id % 54`;
    `suit = local // 13`, `rank = local % 13`; locais 52/53 = coringas), então as
    duas vias da mesma carta caem na mesma `(rank, naipe)`. **Não depende de
    OpenCV** (o mapa importa mesmo sem câmera).
  - `gerar_marcadores()` — `python b_aruco.py gerar` salva os 108 PNGs (com
    rótulo: carta + id + baralho A/B) em `marcadores/` pra imprimir e colar.
  - `run(...)` — o laço: abre a webcam, detecta marcadores, e com **debounce**
    (um marcador precisa ficar estável alguns quadros pra disparar uma vez, e só
    redispara se sumir e voltar) joga a carta na `Partida`. **A janela da webcam
    é a projeção** (marcadores desenhados + HUD: vez, última carta, barra de
    degradação). Teclas: `q`=sair, `f`=tela cheia, `h`=HUD, `m`=espelhar,
    `r`=nova mão.

---

## Referência OSC (porta 57120)

**`/baralho/*`** — a cama (enviado por `a_cama.py` ao vivo, ou `a_osc.py` no
demo autônomo → recebido por `a_synth.scd`):

| Mensagem | Args | Faz |
|---|---|---|
| `/baralho/note` | pitch, vel, cents, ring, ring_sustain, articulação, bpm, fermata, tie_in, tie_out | toca uma badalada (+ ecos/sparkle/reverb) |
| `/baralho/start` `/end` | — | marca início/fim (só no demo autônomo) |
| `/baralho/rest` | dur, fermata, tie_in, tie_out | pausa (só no demo autônomo) |
| `/baralho/fala_*` | (vários) | **voz — dormente**, ninguém dispara |

**`/mundo/*`** — o mundo (enviado por `b_samples`/`b_glitch` → recebido por
`b_synth.scd`):

| Mensagem | Args | Faz |
|---|---|---|
| `/mundo/load` | chave, path | carrega um WAV em buffer |
| `/mundo/bed` | chave, fade, amp, pan, loop, lpf, revWash | atravessa pro habitat (crossfade) |
| `/mundo/trigger` | chave, amp, pan, rate | one-shot pontual |
| `/mundo/stop` | fade | encerra o habitat atual |
| `/mundo/clear` | — | libera todos os buffers |
| `/mundo/voz_load` | palavra, path | carrega palavra do Perec (Espadas corta) |
| `/mundo/glitch` | tipo, level, kick | a corrupção da carta (naipe = tipo) |
| `/mundo/glitch_reset` | — | nova mão (a corrupção mora no Python) |

---

## O que ficou em `arquivo/`

A **voz/texto** do Perec saiu da peça (sem voz, sem palavras). Esses arquivos
foram **arquivados, não apagados** — movidos pra **`arquivo/`**, intactos e
resgatáveis. A **cama** (`a_synth.scd`, `a_cama.py`, `a_osc.py`,
`nucleo_compositor.py`) ficou na raiz, sem a voz.

```
arquivo/
  a_voz.py            (TTS / síntese da voz do Perec)
  a_visual_pygame.py  a_visual_web.py   (visualizers antigos)
  nucleo_perec.py     (seleção/gestão do texto do Perec)
  legado_midi.py  legado_partitura.py   (exportes MIDI/MusicXML antigos)
  visualizer/   (p5js + hydra — NÃO volta: a projeção agora é a webcam)
  tts_cache/    (WAVs de voz pré-renderizados)
  sessoes/      (gravações/estados de sessões antigas)
```

| onde | papel |
|---|---|
| raiz (`a_*` + `b_*`) | **Canastra Suja** — a cama tocada pelas cartas + o mundo |
| `arquivo/` | voz/texto/visual do Perec — arquivado, intacto, fora do caminho |

---

## Como rodar

### Pré-requisitos
- **SuperCollider** (o som sai por ele).
- **Python 3** com `python-osc`:
  ```
  pip install python-osc
  ```
- Pro modo **webcam (ArUco)**: `pip install opencv-contrib-python` + uma webcam.

### Passo a passo
1. Abra o **SuperCollider** e rode, **nesta ordem** (selecione tudo, `Ctrl+Enter`,
   com o servidor já booted):
   - `a_synth.scd` — a **cama** (o vibrafone). Aguarde `[BARALHO] Pronto.`.
   - `b_synth.scd` — o **mundo** (habitats + degradação). Aguarde
     `[MUNDO] Pronto.`.
   - *(opcional)* `a_banco.scd` — a **vitrine de timbres** pra audicionar e
     comparar sonoridades do vibrafone (`~bancoLista.()`, `~tocar.(\arco)`,
     `~bancoTodos.()`). Não entra na peça; é só laboratório. Rode **depois** do
     `a_synth.scd`.
2. No terminal: `python main.py`
3. Escolha o modo e responda **jogadores (2–4)** + **seed**. Nada toca até a
   primeira carta — **os jogadores tocam a peça**:
   - **[1] Teclado** — você digita as cartas (simula a virada). Cada jogador,
     na sua vez, lança: `QC`, `10O`, `AP`, `7E`, `JOKER`… ou ENTER pra uma
     carta aleatória, `.` pra silêncio, `r` pra nova mão, `q` pra sair.
   - **[2] Webcam (ArUco)** — vire as cartas com marcador na frente da câmera;
     **a janela da webcam é a projeção**. Cada carta nova toca a cama + dispara
     o habitat + degradação e passa a vez. Teclas na janela: `q`=sair, `f`=tela
     cheia, `h`=HUD, `m`=espelhar, `r`=nova mão.

**Marcadores ArUco** (pra colar nas cartas): `python b_aruco.py gerar` salva
108 PNGs em `marcadores/` — **2 baralhos** de 54 (52 cartas + 2 coringas cada).
Imprima e cole.

### Portas de entrada diretas (sem o menu)
```
python b_teclado.py     # cartas no teclado (cama + mundo) — precisa de a_synth.scd + b_synth.scd
python b_aruco.py       # cartas pela webcam — precisa de a_synth.scd + b_synth.scd + OpenCV
python b_aruco.py gerar # gera os 108 marcadores ArUco (2 baralhos) em marcadores/
python a_cama.py        # demo: simula cartas tocando o vibrafone ao vivo — precisa de a_synth.scd
python a_osc.py 60      # a cama AUTÔNOMA (generativa), 60s — só pra testar o synth
python b_samples.py     # demo: atravessa alguns habitats sozinho
python b_glitch.py      # demo: simula cartas e ouve a corrupção crescer
python b_buraco.py      # demo das regras (turnos/duplas)
python nucleo_compositor.py  # demo da matemática (sem som, só texto)
```

---

## Áudio e backup ⚠️

O áudio **não** está versionado no git (são ~384 MB):

- `biblioteca/` — os **43 MP3 fonte** (≈60 min). É o **master irreproduzível**.
- `samples/` — os 43 WAV (mono 44.1k) derivados de `biblioteca/`.

`samples/` dá pra regenerar a partir de `biblioteca/`. Mas `biblioteca/` é o
único original — **faça backup separado dele** (HD externo / nuvem).

---

## Próximos passos

- **Afinar o estado rolante (no ouvido)** — o esqueleto está em `a_cama.py`:
  calibrar o `RITMO→ringar` (quanto cada figura faz a barra soar), os gestos de
  gramática (`A`=respira, `10`=fermata, `JOKER`=acento) e ver se 1 botão por
  carta é a granularidade certa. Tudo a ajustar tocando de verdade.
- **ArUco na prática** — imprimir os marcadores, colar nas cartas e calibrar a
  detecção na luz/altura reais da mesa (a webcam ainda precisa ser testada no
  hardware; o pipeline já foi validado em PNG).
- **Espadas (em aberto)** — definir o sabor novo do glitch de Espadas agora que
  a voz saiu (fragmentar os próprios samples? bitcrush? reverse?). TODO em
  `b_glitch.py` + `b_synth.scd`.
- **Timbres** — afinar o vibrafone (`\baralhoVibeKlank`) e, se valer, detalhar
  técnicas estendidas (sul pont/tasto, pizz, jeté, flautando…) como variações de
  parâmetro — tudo dentro do `a_synth.scd`, com o ouvido do Victor. Há um
  **banco de sonoridades pra audicionar** em [`a_banco.scd`](a_banco.scd): rode-o
  **depois** do `a_synth.scd` e use `~bancoLista.()`, `~tocar.(\arco)`,
  `~bancoTodos.()` pra ouvir e comparar 11 cores (as 3 bases + arco, sul
  tasto/ponticello, pizz, sino, motor lento/rápido, gongo) e decidir o que adotar.
- **Multijogador** — contabilizar de quem é a carta (2–4 jogadores) e, talvez,
  espacializar por jogador.
- **Espaço físico** — octofonia (hoje é estéreo; o `b_synth.scd` já marca o TODO
  pra 8 canais), projeção (a imagem da webcam), cenografia da mesa de jogo.

> Renomear a pasta do projeto (`SOPA DE LETRINHAS V2` → `Canastra Suja`) é um
> passo manual opcional — o código não depende do nome da pasta.
