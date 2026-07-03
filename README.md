# CANASTRA SUJA

> *Um baralho de Buraco que, carta a carta, vai sujando o som do mundo.*

Performance eletroacústica ao vivo construída sobre o jogo de **Buraco**
(2–4 jogadores — regras em [`REGRAS_BURACO.md`](REGRAS_BURACO.md)). Não há
palavras nem voz, e **nada toca sozinho: os jogadores tocam a peça.** Cada carta
da vida real, captada por **webcam + ArUco**, faz o **MUNDO** (`b_*`) reagir de
**três jeitos ao mesmo tempo**:

- **atravessa um habitat** — uma biblioteca de paisagens sonoras gravadas
  (mp3/wav) faz crossfade pro próximo habitat sorteado;
- **suja o som** — soma ao **nível de degradação** (o glitch do naipe da carta),
  que cresce carta a carta, do quase-limpo à beira do desmoronamento;
- **vira instrumento (o theremin)** — enquanto o marcador está visível, a
  **pose** da carta (a câmera vira um *theremin*) modula uma voz ao vivo que
  **pica o habitat** e **buga/desbuga** o som em tempo real.

A captação é por **webcam + ArUco**: o jogador vira uma carta, a câmera
reconhece qual é (valor + naipe) e dispara o habitat + o glitch + o theremin.
Tem também um modo **teclado** que simula a virada (pra ensaiar sem câmera, sem
o theremin — que precisa da pose da câmera).

> **Camada A (a cama/vibrafone) está DORMENTE.** A peça nasceu com uma **CAMA** —
> o vibrafone tocado pelas cartas (`a_*`, o "estado rolante"). Esse vibrafone foi
> **tirado da peça ao vivo** (não casava com o resto): os arquivos `a_*` seguem
> na raiz, **intactos**, e o `a_synth.scd` ainda é necessário (boota o servidor de
> áudio e o master limiter), mas a badalada **não soa** durante o jogo — como a
> voz do Perec, ficou arquivada *no lugar*. Ver *Camada A — dormente* abaixo.

> A peça nasceu como *A Cartomante* (tarô/Perec, com voz). **Canastra Suja** é o
> pivô: trocou a poética (do tarô pro Buraco), a fonte da carta (do teclado pra
> webcam) e **tirou a voz**. A camada de voz/texto do Perec foi **arquivada, não
> apagada** (ver [`arquivo/`](#o-que-ficou-em-arquivo)).

---

## Como funciona (a cadeia)

```
                                          ┌─► b_samples ──► b_synth.scd (/mundo/*) [habitat]
  carta virada ─► webcam/ArUco (b_aruco) ─┤
  (mesa real)    ou teclado   (b_teclado) ├─► b_glitch  ──► b_synth.scd (/mundo/*) [degradação]
                       │                  │
                       │ (pose, só webcam)└─► b_glitch.TereminBridge ─► b_synth.scd (/mundo/control) [theremin]
                       └─► b_partida (junta tudo) ────────► SuperCollider ─► alto-falantes

  [dormente] a_cama ─► a_synth.scd (/baralho/*)  — o vibrafone, fora da peça ao vivo
```

1. **A carta** da vida real entra pelo teclado (`b_teclado.py`) ou pela webcam
   (`b_aruco.py`). As duas falam a mesma língua — `(valor, naipe)` — então uma
   substitui a outra sem mexer no resto. Tudo passa pelo `b_partida.py`.
2. **O mundo** (`b_samples.py`): 43 habitats longos embaralhados. A carta sorteia
   o próximo e o mundo atravessa pra ele (crossfade, em `b_synth.scd`).
3. **A degradação** (`b_glitch.py`) sobe a cada carta. O **naipe** escolhe a
   operação sonora do glitch, o **valor** a força do golpe ("kick"), e o
   **acúmulo** a profundidade — começa quase limpo e termina à beira do
   desmoronamento.
4. **O theremin** (só na webcam): a cada quadro, a **pose** de cada marcador
   visível (`b_aruco._pose_features`) é mandada ao `b_synth.scd`, que modula uma
   voz ao vivo — a carta vira instrumento (ver *A câmera como instrumento*).
5. *(Dormente)* a **cama** (`a_cama.py` → `a_synth.scd`) seria o vibrafone tocado
   pelas cartas — **fora da peça ao vivo** (ver *Camada A — dormente*).

As duas camadas usam a **mesma porta OSC (57120)**, mas **namespaces separados**
(`/baralho/*` para a cama, `/mundo/*` para o mundo), então convivem sem colisão.

### Camada A — dormente (o "estado rolante" do vibrafone)

> O que segue descreve a **cama** — o vibrafone tocado pelas cartas. Ele foi
> **tirado da peça ao vivo** (`b_partida.jogar()` não chama mais a cama). O
> código continua intacto em `a_cama.py`/`a_synth.scd` e roda no **demo**
> (`python a_cama.py`), mas **não soa durante o jogo**. Fica aqui como registro
> da poética original e por se valer da mesma matemática da camada A.

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
| ♠ **Espadas** | **fragmenta** (`shards`) | o habitat atual vira cacos (granular `TGrains` que estilhaça mais com o nível) |
| ♣ **Paus** | **satura** (`saturate`) | o habitat queima (drive + fold), distorce |

> **♠ Espadas — resolvido.** No projeto antigo Espadas cortava a voz do Perec em
> cacos. Como a voz saiu, a espada agora **estilhaça o próprio habitat que está
> tocando** (`TGrains` sobre `~mundoCurrentBuf`, em `b_synth.scd`): escolhe uma
> região do habitat e os grãos vagam numa janela que se abre com o nível — começa
> coeso, vira poeira conforme corrompe. Não depende mais do `tts_cache`
> (`load_voice` virou opcional/legado).

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

- **`b_config.py`** — o **painel de ajustes único** (fonte de verdade): o flag
  `DEBUG` (laboratório/estéreo × apresentação/octofonia), a rede OSC (`HOST`/
  `PORT`), os parâmetros do fluxo contínuo (`CONTROL_RATE_HZ`, `CONTROL_SMOOTH`,
  `MAX_VOICES`, `TAIL_SECONDS`) e o **cooldown da carta** (`CARD_COOLDOWN_S`): cada
  marcador só re-dispara a jogada discreta uma vez a cada N segundos (a carta
  parada na mesa não re-glitcha; o theremin segue alterando ao vivo). Todos os
  módulos `b_*` importam daqui.
- **`b_imprimir.py`** — gera **folhas A4 em PDF** com os marcadores ArUco em
  tamanho real, prontas pra gráfica (`python b_imprimir.py`).
- **`audio_sync.ps1`** — backup/sync do áudio pesado (`biblioteca/` + `samples/`)
  no **Google Drive** via rclone (`push`/`pull`/`status`). Ver *Áudio e backup*.
- **`regenera_wavs.ps1`** — regenera `samples/*.wav` a partir de `biblioteca/*.mp3`
  (a conversão mono 44.1k). Rode depois de um `audio_sync.ps1 pull` se os mp3
  mudaram. Ver *Áudio e backup*.

### CAMADA A — a cama (o vibrafone) — **DORMENTE na peça ao vivo**

> Estes arquivos seguem na raiz e funcionam (rode `python a_cama.py`), mas a
> `b_partida` **não os chama** durante o jogo — o vibrafone foi tirado da peça
> ao vivo. O `a_synth.scd` continua **obrigatório** porque é ele que **boota o
> servidor de áudio e o master limiter** (o `b_synth.scd` herda os canais dele).

- **`a_cama.py`** — a **cama** (o **estado rolante**). *No demo* recebe cada carta
  e toca o vibrafone na hora; **na peça ao vivo não é chamado**. A classe
  `CamaViva`:
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
  `/baralho/*`). **Ainda é necessário rodar:** boota o **servidor de áudio**
  (define estéreo/octofonia) e instancia o **master limiter** por onde todo o som
  passa. Os SynthDefs da badalada e o handler `/baralho/note` continuam aqui, mas
  **ninguém manda `/baralho/note` na peça ao vivo** (a cama está dormente — só o
  demo `python a_cama.py`/`a_osc.py` dispara). Quando recebe, toca a badalada:
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
  > As **regras completas** (a versão canônica da peça, o que o código usa × o que
  > é só contexto, e como naipe/valor viram som) estão em
  > [`REGRAS_BURACO.md`](REGRAS_BURACO.md).

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
  - `video_kicks()` espelha o golpe do naipe na **imagem** (o `b_aruco` lê e
    glitcha a projeção pelo mesmo naipe — detune→cor, saturate→bitcrush etc.).
  - `TereminBridge` — a **ponte do fluxo contínuo** (o theremin): manda a pose de
    cada marcador (`/mundo/control`, com rate-limit por id e até `MAX_VOICES`
    vozes) e pede a **cauda** quando o marcador some (`/mundo/control_off`).
  - `load_voice()` é **legado/opcional** (carregava palavras do Perec pro
    `tts_cache/`); Espadas não depende mais disso — fragmenta o habitat atual.

- **`b_synth.scd`** — o som do mundo no SuperCollider (namespace `/mundo/*`).
  **Aditivo**: não toca no `a_synth.scd` nem lê o sinal da camada A — são vozes
  paralelas que *soam como* a máquina se desfazendo. Sem este arquivo carregado,
  o mundo toca limpo. Define:
  - `\mundoBed` — o habitat: `PlayBuf` longo com LPF (véu de distância) + reverb
    embutido, com crossfade por `gate`/envelope. `\mundoSample` — one-shot
    pontual.
  - Os **4 glitches** discretos, um por naipe: `\glitchDetune` (cluster que
    afunda), `\glitchFreeze` (janelinha do habitat travada via `Phasor`+`BufRd`),
    `\glitchShards` (**granula o habitat atual** com `TGrains` — não mais a voz) e
    `\glitchSaturate` (o habitat com `tanh`+`fold2`). Todos escalam com `level`/`kick`.
  - **`\teremin`** — a voz **contínua** do theremin (a pose do marcador a controla
    ao vivo). Dentro dela convivem **a colagem** (grãos que picam o habitat — "os
    áudios") e **o synth digital bugado** (modem/dial-up: tons que gaguejam,
    chiado, bleep, ghost). Um macro **`clareza`** faz o som **bugar/desbugar**
    sozinho (~2–5 s por fase): quando sobe, abaixa o synth e deixa o áudio
    reconhecível; quando cai, buga tudo. Mapeamento da pose: ver *A câmera como
    instrumento*.
  - Receptores OSC: `/mundo/load`, `/mundo/bed`, `/mundo/trigger`, `/mundo/stop`,
    `/mundo/clear`, `/mundo/voz_load`, `/mundo/glitch`, `/mundo/glitch_reset`,
    **`/mundo/control`** e **`/mundo/control_off`** (o theremin).

- **`b_partida.py`** — o **motor da partida**: junta tudo num objeto só.
  `Partida` tem a `Mesa` (b_buraco) + o `MundoPlayer` (b_samples) + o
  `GlitchEngine` (b_glitch) + a `TereminBridge` (b_glitch). Cada `jogar(rank,
  suit)` atravessa um habitat + soma degradação + **passa a vez**. *(A `CamaViva`
  ainda é instanciada, mas `jogar()` **não a toca** — vibrafone dormente, pedido
  4; ela serve só ao `reset()`.)* `jogar_joker()` (curingão = força máxima no
  mundo), `reset()` (zera a degradação — nova mão), `silencio()`, `encerrar()`
  (solta as vozes do theremin + para os habitats). Expõe `vez_label`, `corrupcao`
  e `ultima_str()` pra UI. É **reutilizável**: teclado e webcam chamam os mesmos
  métodos.

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
    redispara se sumir e voltar) + **cooldown** (`CARD_COOLDOWN_S`) joga a carta
    na `Partida`. **A janela da webcam é a projeção** (marcadores desenhados +
    HUD opcional). Teclas: `q`/ESC=sair, `f`=tela cheia, `h`=HUD, `m`=espelhar,
    `g`=liga/desliga o apodrecer da imagem, `r`=nova mão.
  - **Gesto de finalizar (tapar a lente):** se a peça já começou e a lente fica
    **coberta** — quadro **genuinamente escuro** (`_brilho_medio < END_DARK_LEVEL`)
    **E** sem carta — por `END_COVER_S` (~6 s) seguidos, a obra **encerra** — solta
    as vozes do theremin, para os habitats (fade) e a projeção escurece em
    `END_FADE_S`. Mesa vazia com luz acesa ou um quadro preto solto **não** encerram
    (era o bug antigo: bastava ficar sem carta). `r` cancela/recomeça. Ver *Como
    acabar a peça*.
  - **Fluxo contínuo (theremin):** além do disparo discreto, a cada quadro calcula
    a **pose** de cada marcador visível (`_pose_features`: **x/y/size/spin/tilt/luma**
    a partir dos 4 cantos, sem calibrar a câmera) e a manda ao SC pela
    `TereminBridge` (`b_glitch.py`). Em `DEBUG`, sobrepõe um HUD com os números da
    pose. Ver a seção *A câmera como instrumento* abaixo.

---

## A câmera como instrumento (o theremin) + debug + octofonia

A captação do ArUco faz **duas coisas ao mesmo tempo**:

1. **Gatilho discreto:** quando uma carta nova aparece estável (e passou o
   `CARD_COOLDOWN_S`), ela *uma vez* atravessa um habitat e soma um passo de
   degradação. (A cama/vibrafone **não** dispara mais — está dormente.)
2. **Controle contínuo (o "theremin"):** enquanto o marcador está visível, a
   câmera manda a **pose** dele ~30×/s pro SuperCollider, que **modula uma voz ao
   vivo** (`\teremin`) — a carta vira instrumento. Quando o marcador **some**, a
   voz não corta: solta o envelope e **ecoa em delay + reverb** (a cauda).

   Dentro dessa voz convivem **duas camadas**: **(a) a colagem** — grãos
   (`TGrains`) que picam o **habitat de verdade** ("os áudios") — e **(b) o synth
   digital bugado** — um modem/dial-up dos anos 2000 (tons que gaguejam, chiado de
   dados, bleep tipo morse e um modo *ghost* quase mudo, com bitcrush). Mapeamento
   da pose (todos 0..1, menos `spin` que é −1..1):

   | feature | gesto na carta | controla no som |
   |---|---|---|
   | `x` | mover na **horizontal** | **scrub** (qual trecho do habitat os grãos picam) + azimute/pan |
   | `y` | mover na **vertical** | **altura/pitch** dos grãos e dos tons do modem + tempo do delay |
   | `size` | **aproximar/afastar** | densidade dos grãos + **velocidade** do modem + intensidade |
   | `spin` | **girar** no plano | detune dos grãos + **esmaga bits** (bitcrush) |
   | `tilt` | **tombar** a carta | **freeze/stutter** (trava a posição, fica mais lo-fi) |
   | `luma` | **iluminação** do marcador | **cor do filtro** + taxa do bitcrush |

   O **naipe** tempera o sabor da voz. Um macro **`clareza`** (lento, aleatório)
   faz o som **bugar/desbugar** sozinho a cada ~2–5 s: quando sobe, abaixa o synth
   digital e levanta o áudio (dá pra entender o que é); quando cai, o synth volta e
   buga tudo. Até `MAX_VOICES` marcadores (os mais perto) viram voz ao mesmo tempo
   — ver `b_config.py`.

### Como acabar a peça (cobrir a câmera)

A peça **termina por gesto**: se ela já começou (já caiu ao menos uma carta) e a
**lente fica coberta** — quadro **genuinamente escuro** (brilho médio abaixo de
`END_DARK_LEVEL`) **E** sem nenhuma carta — por `END_COVER_S` (~6 s) seguidos, a
obra **encerra** — as vozes do theremin soltam, os habitats param (fade) e a
**projeção escurece** em `END_FADE_S` (~4 s), até o laço sair. Tapar a lente =
**apagar a luz da peça**. Exigir escuro de verdade (não só "sem carta") evita que a
peça feche sozinha com a mesa vazia ou num piscar preto da câmera. A tecla `r`
cancela um encerramento em curso (recomeça a mão); `q`/ESC sai na hora. Os tempos e
o limiar de escuro moram no topo do `b_aruco.py` (suba `END_DARK_LEVEL` se a lente
coberta ainda vaza luz; suba `END_COVER_S` se a câmera chega a cegar no meio sem
querer).

### Modo debug (laboratório) × apresentação (octofonia)

Há **um flag de debug** (pedido de prova) em **três lugares** que devem ficar
**iguais**:

| onde | True (laptop) | False (conservatório) |
|---|---|---|
| `b_config.py` → `DEBUG` | fala na tela + HUD de pose na projeção | tela quieta, projeção limpa |
| `a_synth.scd` → `~debug` | som em **estéreo** (2 caixas) | **octofonia** (8 Genelecs, PanAz) |
| `b_synth.scd` → `~debug` | (idem; herda os canais do `a_synth`) | (idem) |

A octofonia roteia cada fonte por **azimute** (o theremin **anda** entre os 8
Genelecs) e espalha a cama/reverbs pelo anel. Trocar estéreo↔octo exige
**rebootar** o servidor de áudio (Ctrl+. e rodar `a_synth.scd` de novo), pois o
número de canais de saída só é lido no boot. O **mapeamento canal→Genelec** (a
ordem física no anel) é calibração no local, no hardware.

### Não estourar o som (limiter)

Tudo passa por um **master limiter** (teto rígido) no `a_synth.scd`, então os
glitches não clipam mais. Em **debug**, o post window mostra o **pico em dBFS**
quando chega perto do teto (o "controle de dB e RMS"). Calibragem fina de ganho
é no ouvido, tocando.

## Referência OSC (porta 57120)

**`/baralho/*`** — a cama (**dormente na peça ao vivo**; só os demos `a_cama.py` /
`a_osc.py` enviam → recebido por `a_synth.scd`, que mesmo sem isto boota o
servidor + o master limiter):

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
| `/mundo/control` | id, naipe, x, y, size, spin, tilt, luma | **theremin**: a pose do marcador ao vivo (contínuo, todo quadro) |
| `/mundo/control_off` | id | marcador sumiu → solta a voz (cauda em delay/reverb, não corta seco) |

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
- **Python 3** com as dependências do núcleo. **Instale tudo de uma vez** com o
  `requirements.txt` (versões travadas — as mesmas em Windows e Mac, pra não dar
  a "loteria" de versão que quebrava o Mac):
  ```
  python -m pip install -r requirements.txt
  ```
  Isso instala `opencv-contrib-python`, `numpy` e `python-osc`. Pro modo **webcam
  (ArUco)** você ainda precisa de **uma webcam**.
  > ⚠️ É `opencv-CONTRIB` (traz o módulo `aruco`). **Não** instale `opencv-python`
  > junto — as duas brigam. Se já tiver a outra:
  > `python -m pip uninstall -y opencv-python opencv-python-headless`
  > **macOS:** na 1ª vez, libere a câmera em *Ajustes → Privacidade e Segurança →
  > Câmera* pro app que roda o Python (Terminal/iTerm/IDE), senão a câmera não abre.

### Passo a passo
1. Abra o **SuperCollider** e rode, **nesta ordem** (selecione tudo, `Ctrl+Enter`,
   com o servidor já booted):
   - `a_synth.scd` — **boota o servidor de áudio + o master limiter** (a cama/
     vibrafone vive aqui, mas fica dormente na peça). Aguarde `[BARALHO] Pronto.`.
   - `b_synth.scd` — o **mundo** (habitats + degradação + theremin). Aguarde
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
     **a janela da webcam é a projeção**. Cada carta nova atravessa o habitat +
     soma degradação + (na webcam) vira theremin, e passa a vez. **Tapar a lente
     (escuro, sem carta) por ~6 s encerra a peça** (fade). Teclas: `q`/ESC=sair,
     `f`=tela cheia, `h`=HUD, `m`=espelhar, `g`=degradar, `r`=nova mão.

**Marcadores ArUco** (pra colar nas cartas): `python b_aruco.py gerar` salva
108 PNGs em `marcadores/` — **2 baralhos** de 54 (52 cartas + 2 coringas cada).
Imprima e cole.

### Portas de entrada diretas (sem o menu)
```
python b_teclado.py     # cartas no teclado (mundo + glitch) — precisa de a_synth.scd (servidor+limiter) + b_synth.scd
python b_aruco.py       # cartas pela webcam (mundo + glitch + theremin) — precisa de a_synth.scd + b_synth.scd + OpenCV
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

### Backup/sync no Google Drive — `audio_sync.ps1`

Pra guardar e trazer o áudio entre máquinas há um script (rclone → Google Drive):

```
.\audio_sync.ps1 push      # manda biblioteca/ e samples/ PRO Google Drive
.\audio_sync.ps1 pull      # TRAZ biblioteca/ e samples/ do Google Drive
.\audio_sync.ps1 status    # mostra o tamanho do que está lá
```

Setup (uma vez): `winget install Rclone.Rclone`, depois `rclone config` criando
um remote chamado **`gdrive`** (Google Drive) — o passo a passo está comentado no
topo do `audio_sync.ps1`. O `push` usa o seu local como fonte; o `pull`
sobrescreve o local (o script pergunta antes). Não gasta cota do GitHub e mantém
o master `biblioteca/` salvo na nuvem.

---

## Próximos passos

- **Afinar o theremin (no ouvido)** — calibrar o equilíbrio áudio × synth digital,
  o ritmo do `clareza` (buga/desbuga) e a variedade dos regimes do modem, tudo no
  `\teremin` do `b_synth.scd` (os números tunáveis estão comentados na própria
  SynthDef). Decidir se algum gesto (ex.: `luma`) deve reger a clareza, hoje
  automática.
- **Camada A (dormente) — decidir** se o vibrafone volta de alguma forma à peça
  (hoje `b_partida.jogar()` não chama a cama). O esqueleto segue pronto em
  `a_cama.py`/`a_synth.scd` (o "estado rolante": `A`=respira, `10`=fermata,
  `JOKER`=acento).
- **ArUco na prática** — imprimir os marcadores, colar nas cartas e calibrar a
  detecção na luz/altura reais da mesa (a webcam ainda precisa ser testada no
  hardware; o pipeline já foi validado em PNG).
- **Espadas (resolvido)** — o glitch de Espadas agora **fragmenta o próprio
  habitat** que está tocando (`TGrains` sobre `~mundoCurrentBuf`); não depende mais
  da voz/`tts_cache`. Resta calibrar densidade/janela no ouvido.
- **Timbres** — afinar o vibrafone (`\baralhoVibeKlank`) e, se valer, detalhar
  técnicas estendidas (sul pont/tasto, pizz, jeté, flautando…) como variações de
  parâmetro — tudo dentro do `a_synth.scd`, com o ouvido do Victor. Há um
  **banco de sonoridades pra audicionar** em [`a_banco.scd`](a_banco.scd): rode-o
  **depois** do `a_synth.scd` e use `~bancoLista.()`, `~tocar.(\arco)`,
  `~bancoTodos.()` pra ouvir e comparar 11 cores (as 3 bases + arco, sul
  tasto/ponticello, pizz, sino, motor lento/rápido, gongo) e decidir o que adotar.
- **Multijogador** — contabilizar de quem é a carta (2–4 jogadores) e, talvez,
  espacializar por jogador.
- **Espaço físico** — octofonia **implementada** (`~debug=false` → 8 canais via
  PanAz, ver seção acima); falta **calibrar no hardware** o mapeamento
  canal→Genelec e o nível por caixa no conservatório. Projeção (a imagem da
  webcam) e cenografia da mesa de jogo seguem em aberto.

> Renomear a pasta do projeto (`SOPA DE LETRINHAS V2` → `Canastra Suja`) é um
> passo manual opcional — o código não depende do nome da pasta.
