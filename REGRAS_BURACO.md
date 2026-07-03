# Regras do Buraco (Canastra) — a versão canônica da peça

> **Por que este documento existe.** *Canastra Suja* nasce do **Buraco**: o jogo é
> a **moldura poética e o gesto** da obra, não um placar que o computador calcula.
> Este arquivo fixa **a versão das regras que a peça adota** (há dezenas de
> variações regionais) e — mais importante — separa **o que o código usa** do que
> é **só contexto**. Se um dia alguém for mapear uma regra nova no som, decide
> aqui primeiro.
>
> **Fonte da verdade no código:** `b_buraco.py` (`PONTOS`, `CURINGA_*`,
> `CANASTRAS`, `Mesa`). Se este doc e o código divergirem, o código manda —
> abra um PR alinhando os dois.

---

## O que é o Buraco (em uma frase)

Jogo de cartas para **2 a 4 jogadores** (em 4, duplas de frente), com **2 baralhos
de 52 + coringas** (108 cartas no total aqui). Joga-se por **rodadas**, somando
pontos até uma meta (3.000 ou 5.000). Formam-se **sequências do mesmo naipe**; uma
sequência de **7+ cartas** é uma **canastra**. Criado em Montevidéu (1939), espalhou-
se pela América do Sul nos anos 40 virando incontáveis variações.

O nome da obra vem daqui: **canastra "suja"** = canastra formada **com curinga**.
Sujeira na canastra ⇄ sujeira no som.

---

## O que a PEÇA usa (modelado em código)

Esta é a fatia que o `b_buraco.py` realmente implementa — o resto (abaixo) é
contexto que acontece na **mesa física**, entre as pessoas.

### Baralho
- **2 baralhos** de 52 + **2 coringas** cada = **108 cartas** (`TOTAL_CARTAS`).
- Isso casa com os **108 marcadores ArUco** (`b_aruco.py`): 2 decks de 54.

### Valor das cartas — tabela canônica
| Carta | Pontos |
|---|---|
| Ás (A) | **15** |
| 8, 9, 10, J, Q, K | **10** |
| 3, 4, 5, 6, 7 | **5** |
| 2 (curinguinha) | **10** |
| Joker / Coringão | **20** |

> **Decisão (Joker = 20).** Existem tabelas com Joker=50 por aí; **a nossa canônica
> usa 20** (alinhada ao texto de referência). No código: `PONTOS["JOKER"] = 20`.

### Curingas
- **Coringão** (`JOKER`) e **curinguinha** (o **2**, qualquer naipe) — `eh_curinga()`.
- O 2 trava o lixo e, colado no lugar natural (entre Ás e 3), pode até "limpar" uma
  sequência antes de fechar. *(No som, curinga = a marca do "sujo".)*

### Os 4 tipos de canastra
| Tipo | O que é | Pontos |
|---|---|---|
| **Suja** | 7+ em sequência **com** curinga/curinguinha | **100** |
| **Limpa** | 7+ em sequência **sem** curinga | **200** |
| **Quinhentos** | Ás a Rei (13 cartas), sem curinga | **500** |
| **Real** | Ás a Ás (começa e termina com Ás), sem curinga | **1000** |

> **Nota de nomenclatura.** As fontes brigam entre si: a de 500 aparece como
> "quinhentos" **e** como "real"; a de 1000 como "real" **e** como "canastra de ás".
> **Nós fixamos:** `quinhentos` = 500, `real` = 1000 (as chaves em `CANASTRAS`).
> No código elas são **só referência/poética** — a peça não verifica canastras.

### Estrutura de turnos
- **2 ou 3 jogadores:** contagem individual. **4 jogadores:** duplas de frente
  (J1+J3 × J2+J4) — `Mesa.duplas`.
- A **vez gira em sentido horário** (`Mesa.proximo()`). *(No Buraco tradicional a
  distribuição é anti-horária; aqui só importa o giro da vez da performance.)*

---

## O que a peça NÃO modela (contexto — fica na mesa física)

Tudo abaixo é regra de verdade do Buraco, mas **não** vive no código — a peça não
é um motor de Buraco, e o placar real é das pessoas na mesa. Fica aqui como
referência (e como possível inspiração pra mapeamentos sonoros futuros).

- **O morto:** dois montes de 11 cartas separados no início. Cada dupla pega **um**.
  Perder o morto = **−100**.
- **Bater:** ficar sem cartas na mão. 1ª batida pega o morto (sem exigir canastra);
  2ª batida (encerra a rodada) exige **canastra limpa**. Quem fica "na fina" (1 carta)
  só bate com carta do monte.
- **Lixo (descarte) preso × solto:** no **preso** (padrão), pra pegar o lixo é
  preciso ter **2 cartas** que sequenciem com a última do lixo e baixar o jogo. No
  **solto**, pega quando convém (menos usado).
- **Pontuação da rodada:** soma das canastras + batida (+50) − morto não pego (−100)
  − "mão a pagar"; arredonda pra múltiplo de 10 (pra cima). Pode dar **negativo**.
- **Vulnerabilidade:** ao passar da metade da meta, a dupla só baixa jogos que somem
  **≥ 75 pontos**.
- **Estratégia de descarte:** não largar 7 e 8 (essenciais pra canastra limpa),
  descartar 3/4 no início, vigiar as compras do adversário.

---

## Como as regras viram SOM (a ponte poética)

O ponto de contato entre regra e obra — o que **de fato** a peça faz com a carta:

| Regra do Buraco | Na peça (código) |
|---|---|
| **Naipe** da carta | escolhe a **operação sonora** do glitch (`b_glitch.SUIT_GLITCH`): ♥ desafina, ♦ congela, ♠ fragmenta, ♣ satura |
| **Valor** da carta | força do "kick" do glitch (`_kick_for_rank`: A leve … K pesado) |
| **Canastra suja** (com curinga) | a metáfora-mãe: **curinga = sujeira** → o som suja carta a carta |
| **A vez / o turno** | `Mesa` gira a vez; cada carta atravessa um habitat + soma degradação + passa a vez |
| **Pontuação, morto, batida** | **não** sonorizados hoje — candidatos a exploração futura (ver *Próximos passos* do README) |

> **Onde não estamos usando o jogo (ainda):** pontuação, morto, batida e
> vulnerabilidade não têm tradução sonora. Não é lacuna a "consertar" — é escolha:
> a obra sonoriza o **gesto** (virar a carta, sujar o som, passar a vez), não o
> **placar**. Se um dia quiser sonorizar (ex.: a vulnerabilidade dobrar a
> degradação), decide-se aqui e implementa-se em `b_partida.py`.

---

## Divergências resolvidas (registro)

| Item | Antes | Agora (canônico) |
|---|---|---|
| Pontos do Joker | código dizia 50 | **20** (`PONTOS["JOKER"]`) |
| Canastra de 500 | descrita como "Ás a 2" | **Ás a Rei (13 cartas)** |
| Nomes das canastras 500/1000 | fontes se contradizem | `quinhentos`=500, `real`=1000 |
