# A CARTOMANTE

> *"Olhe, leitor, que bonito par de cartas..."* — uma profecia que a vida desmente.

Performance eletroacústica ao vivo construída sobre um sistema generativo:
um **baralho de 52 cartas** vira **música** (cada carta → 7 parâmetros por
nota), atravessado pelo texto de Georges Perec (*Espèces d'espaces*) e pela
sombra do conto *A Cartomante*, de Machado de Assis.

A peça põe **dois cartomantes** na mesma sala:

- **A máquina** lê o destino que *já está escrito* (sistema determinístico).
- **Uma cartomante de carne** puxa cartas FÍSICAS ao vivo — e o acaso do
  corpo vai, carta a carta, **desmentindo a profecia**.

---

## Os dois cartomantes (arquitetura)

O código é dividido em duas camadas que coexistem sem se misturar no fonte:

### Camada A — a profecia / a máquina
O sistema generativo, determinístico (com *seed*). Roda sozinho. É a voz do
destino "já escrito". **É intocável** — não se edita nenhum arquivo `a_*` nem
`nucleo_*`. Tudo que é novo entra *por cima*, de forma aditiva.

- `nucleo_compositor.py` — o motor: 52 cartas → 7 parâmetros → notas.
- `nucleo_perec.py` — o texto de Perec, fatiado em capítulos/fragmentos.
- `a_synth.scd` — síntese no SuperCollider (namespace OSC `/baralho/*`).
- `a_osc.py` — manda a composição pro SuperCollider via OSC.
- `a_voz.py` — voz-fantasma do Perec (TTS via SAPI do Windows, cacheado).
- `a_visual_web.py` + `visualizer/` — visualizador no browser (p5js/hydra).
- `a_visual_pygame.py` — visualizador alternativo (janela pygame).

### Camada B — o mundo / o acaso real
A cartomante de carne. Uma biblioteca de **43 habitats sonoros longos**
(paisagens de 10s a vários minutos) forma um **segundo baralho** — o *baralho
do mundo*, embaralhado. Cada carta física faz o mundo **ATRAVESSAR** pro
próximo habitat (crossfade). Um lugar de cada vez. Toda a camada B vive em
arquivos `b_*` e no namespace OSC `/mundo/*`, separado da camada A.

- `b_synth.scd` — habitats no SuperCollider (`\mundoBed` com crossfade) +
  os 4 glitches da colisão (`\glitchDetune/Freeze/Shards/Saturate`).
- `b_samples.py` — o baralho do mundo (`WorldDeck`) + o player (`MundoPlayer`).
- `b_glitch.py` — a colisão: acúmulo de corrupção + naipe→glitch (`GlitchEngine`).
- `b_teclado.py` — a cartomante por teclado (substituível por leitor NFC).

> **Por que dois baralhos independentes?** A carta não *carrega* o som — ela
> apenas revela qual habitat vem a seguir. Dois baralhos = dois destinos que
> não se devem um ao outro. O naipe define a espacialização (e, na colisão
> abaixo, o tipo de corrupção); o som vem do baralho do mundo.

### Esquema de nomes
| prefixo | papel |
|---|---|
| `nucleo_*` | motor compartilhado pelas duas camadas |
| `a_*` | camada A (a máquina / a profecia) — **intocável** |
| `b_*` | camada B (o mundo / o acaso ao vivo) — aditivo |
| `legado_*` | exportação MIDI / MusicXML (escondida, mas intacta) |

---

## A colisão — cada naipe corrompe de um jeito

O coração dramático da peça: a carta física (B) **corrompe a profecia (A)**.
A corrupção é **graduada e acumulativa** — cada carta soma ao *nível global
de corrupção*, e a máquina vai gaguejando até quase desmoronar no fim
(mais Machado: a profecia desmentida devagar, não num estalo).

Os quatro naipes são os quatro elementos da cartomância — cada um, um glitch:

| Naipe | Elemento | Glitch | O som da máquina... |
|---|---|---|---|
| ♥ **Copas** | água | **desafina** | escorrega de altura, afunda — perde o tom |
| ♦ **Ouros** | terra | **congela** | um grão trava e repete — o tempo petrifica |
| ♠ **Espadas** | lâmina/ar | **fragmenta a voz** | corta as palavras do Perec em cacos |
| ♣ **Paus** | fogo | **satura** | queima, distorce, suja |

O **naipe** escolhe o *sabor* da corrupção; o **valor** da carta (A…K) escolhe
a *força do golpe* daquela carta (um Rei abala mais que um 2); e o **acúmulo**
(quantas cartas já caíram) escolhe a *profundidade*. No começo, abalos quase
imperceptíveis; perto do fim, a máquina mal segura a própria voz.

> Estado: **construído** (Fase 2). A camada A continua intocada: o glitch é
> uma sombra *paralela* — vozes aditivas em `b_synth.scd` que **soam como** A
> se desfazendo, sem ler o sinal real dela (bus 0 intocado, nenhum arquivo
> `a_*` editado). Sem `b_synth.scd` carregado, A soa pristina. Controle em
> `b_glitch.py`; OSC `/mundo/glitch [tipo, nível, kick]`.
> A espada (Espadas) corta as **palavras reais do Perec**, lendo o
> `tts_cache/` que a camada A já gera.

---

## Como rodar

### Pré-requisitos
- **SuperCollider** (o som sai por ele).
- **Python 3** com `python-osc`:
  ```
  pip install python-osc
  ```
  Opcionais, só pro legado/visual pygame: `pip install pygame music21`.
- **Windows** — a voz do Perec usa o SAPI nativo (vozes Maria/Zira já vêm
  instaladas). O resto roda multiplataforma.

### Passo a passo
1. Abra o **SuperCollider** e rode, na ordem:
   - `a_synth.scd` (camada A) — selecione tudo, `Ctrl+Enter`.
   - `b_synth.scd` (camada B) — **depois**, com o servidor já booted.
2. No terminal:
   ```
   python main.py
   ```
3. Escolha uma opção do menu:

| Opção | O que faz |
|---|---|
| **1** | Tocar via OSC (só a camada A — som de qualidade) |
| **4** | Abrir o visualizador (janela pygame) |
| **5** | OSC + visualizador web (som + visual ao vivo no browser) |
| **6** | Cartomante dupla (visual no browser + cartas no teclado) |
| **7** | **A Cartomante — peça completa** (synth + voz + visual no browser + cartas, tudo num terminal só) |
| **0** | Sair |

> A opção **7** é a peça inteira: abre o visualizador no browser
> automaticamente, toca a camada A em segundo plano e te deixa puxar cartas
> (`QC`, `10O`, `AP`, `7E`… ou ENTER pra uma carta aleatória, `.` pra
> silêncio, `?` pra ajuda).

### Portas de entrada diretas (sem o menu)
```
python a_osc.py 60        # camada A via OSC, 60s
python a_visual_pygame.py # visualizador pygame
python b_teclado.py       # só a camada B (cartas) — precisa dos 2 .scd
python b_samples.py       # demo: atravessa alguns habitats sozinho
```

---

## Áudio e backup ⚠️

O áudio **não** está versionado no git (são ~384 MB):

- `biblioteca/` — os **43 MP3 fonte** (≈60 min). É o **master irreproduzível**.
- `samples/` — os 43 WAV (mono 44.1k) derivados de `biblioteca/`.

`samples/` dá pra regenerar a partir de `biblioteca/`. Mas `biblioteca/` é o
único original — **faça backup separado dele** (HD externo / nuvem). O git
protege o código; não protege o áudio.

---

## Roteiro de fases

- **Fase 0 — Subtração** ✅ — esconder MIDI/MusicXML do menu (intactos no legado).
- **Fase 1 — Som do mundo (habitats), sem hardware** ✅ — `b_synth.scd` +
  `b_samples.py` + `b_teclado.py`. Roda hoje só com teclado.
- **Fase 2 — A colisão (o glitch por naipe)** ✅ — corrupção paralela:
  `b_synth.scd` (4 glitches) + `b_glitch.py`. O acaso corrompendo a profecia,
  acumulando carta a carta (ver tabela acima). Testável já, pelo teclado.
- **Fase 3 — Leitor NFC** — `b_nfc.py` substitui o teclado (ACR122U +
  tags NTAG215). Entra no *lugar* do teclado; o resto da cadeia não muda.
- **Fase 4 — Motor da performance** — `b_performance.py`: A autônoma + B ao
  vivo + as fases/fermatas do roteiro, com um botão "começar a peça".
- **Fase 5 — Espaço físico** — octofonia (8 canais), projeção em cacos de
  espelho, a escada-cenografia (o *escalier* de Perec), ensaio na sala.

---

## Cenografia (em aberto)

Sala escura, mesa-altar central iluminada (a cartomante), possivelmente um
instrumentista = "o consultado" que reage às cartas. Cacos de espelho
pendurados nos 4 ganchos do teto fragmentam o visual p5js pela sala (o
público dentro do grid). Uma escada como cenografia: o capítulo *l'escalier*
de Perec encarnado. Octofonia planejada. Estreia provável no conservatório.

---

## Nota técnica

Projeto versionado com git desde 2026-06-02. A regra de ouro: **a camada A é
intocável** — tudo novo é aditivo (`b_*`, namespace `/mundo/*`). Sem git no
passado, então toda mudança ainda é verificada (compile + import) antes de
seguir.
