# PYTHON DO ZERO — o alicerce pra ler o código da *Canastra Suja*

> Pra quem **nunca** programou. Sério: nem o "hello world". Leia isto **uma vez**,
> com calma, e depois cada arquivo `.py` do projeto vai fazer sentido — porque
> todos eles são comentados linha a linha apoiados nas ideias daqui.

Não precisa decorar nada. É só pra você reconhecer as peças quando elas
aparecerem. Pode voltar aqui sempre que travar numa palavra.

---

## 1. O que é "programar", afinal?

Um **programa** é uma **receita**: uma lista de passos que o computador segue,
de cima pra baixo, na ordem, sem pular e sem adivinhar nada. O computador é
rápido e obediente, mas **burro**: ele faz *exatamente* o que está escrito.
Se você esquecer um passo, ele não "entende o que você quis dizer" — ele para
e reclama.

**Python** é só um **idioma** pra escrever essas receitas. Foi escolhido aqui
porque é dos mais parecidos com o inglês comum e dos mais fáceis de ler.

Um arquivo que termina em **`.py`** é um arquivo escrito nesse idioma. Os
arquivos que terminam em **`.scd`** são de **outro** idioma (o do SuperCollider,
o programa que faz o som de verdade) — esses a gente comenta separado.

---

## 2. Como eu "rodo" um programa?

Você abre o **terminal** (uma janelinha preta onde se digitam comandos, em vez
de clicar com o mouse) e digita:

```
python b_glitch.py
```

Isso quer dizer: *"ó Python, leia o arquivo `b_glitch.py` e execute a receita
que está nele"*. O computador faz, mostra o resultado, e volta.

Pronto — isso é "rodar um programa". O famoso **"hello world"** (alô, mundo) é
o primeiro programa que todo mundo faz: uma receita de **um passo só**, que
manda escrever a frase "alô, mundo" na tela. Em Python é literalmente:

```python
print("alo, mundo")
```

A palavra `print` (do inglês "imprimir/escrever") **mostra algo na tela**.
É o jeito do programa "falar" com você. Você vai ver MUITO `print` no projeto —
é assim que a peça avisa "carta tal caiu", "corrupção em 30%", etc.

---

## 3. As peças do idioma (o vocabulário todo que você precisa)

### 3.1. Variável = uma **caixa com nome**

Imagine uma caixa onde você guarda uma coisa e cola uma etiqueta com um nome.
Depois, sempre que você falar o nome, é como mostrar o que está dentro.

```python
idade = 30
```

Lê-se: *"crie uma caixa chamada `idade` e guarde o número 30 dentro"*. O sinal
de **`=`** aqui **não** é "igual" da matemática — é **"guarde isto nesta caixa"**
(a gente chama de "atribuir"). Depois, `idade` vale 30 onde quer que apareça.

Você pode trocar o conteúdo a qualquer momento:

```python
idade = idade + 1   # pega o que tinha na caixa (30), soma 1, e guarda de volta (31)
```

> No código você verá muito `+=`, que é só um atalho pra isso:
> `idade += 1` é a mesma coisa que `idade = idade + 1`.

### 3.2. Os **tipos** de coisa que cabem numa caixa

- **Texto** (chamado *string*): qualquer palavra/frase, **sempre entre aspas**.
  `"Copas"`, `"alo, mundo"`, `"7E"`. As aspas são o jeito de dizer "isto é texto
  literal, não é um nome de caixa".
- **Número inteiro** (*int*): `0`, `7`, `108`, `-3`. Sem casa decimal.
- **Número com vírgula** (*float*): escrito com **ponto**, não vírgula:
  `0.5`, `1.0`, `0.015`. (Computador usa ponto pra decimais.) No projeto, a
  "sujeira do som" é um float que vai de `0.0` (limpo) a quase `1.0` (destruído).
- **Verdadeiro/Falso** (*boolean*): só dois valores possíveis, `True` (verdadeiro)
  e `False` (falso). Servem pra perguntas de sim/não: "o HUD está ligado?".
- **Nada** (`None`): a palavra especial pra "vazio / não tem / ainda não sei".

### 3.3. Lista `[ ]` = uma **fila de coisas em ordem**

Colchetes `[ ]` guardam **várias** coisas numa caixa só, em ordem, tipo uma
fila ou uma lista de compras:

```python
naipes = ["C", "O", "E", "P"]   # uma lista com 4 textos
```

Cada item tem uma **posição**, e — detalhe importante — a contagem **começa do
zero**: a 1ª coisa está na posição `0`, a 2ª na `1`, e assim por diante.

```python
naipes[0]   # vale "C" (a primeira)
naipes[2]   # vale "E" (a terceira)
```

### 3.4. Dicionário `{ }` = uma **tabela de-para**

Chaves `{ }` guardam pares **"de → para"**. Você dá uma **chave** e recebe um
**valor**. É igualzinho a um dicionário de verdade: você procura a palavra
(chave) e acha o significado (valor).

```python
pontos = {"A": 15, "K": 10, "JOKER": 50}
pontos["JOKER"]   # vale 50  (procurei "JOKER", recebi 50)
```

No projeto isso aparece o tempo todo: *naipe → tipo de defeito*, *carta →
quantos pontos*, *sigla → nome bonito*.

### 3.5. Comentário `#` = **bilhete pra humano, o computador ignora**

Tudo que vem **depois de uma `#`** numa linha é um recado pra quem está lendo.
O computador pula. É exatamente isso que enche os arquivos do projeto: explicação.

```python
nivel = 0.0   # a sujeira começa zerada (som limpo)
```

### 3.6. Função `def` = **ensinar um truque novo e dar um nome a ele**

Uma **função** é um pedacinho de receita que você guarda com um nome pra poder
mandar fazer depois, quantas vezes quiser, sem reescrever. A palavra `def`
(de "define", definir) cria a função:

```python
def saudar(nome):          # "ensine um truque chamado 'saudar', que recebe um 'nome'"
    print("ola, " + nome)  # o que o truque faz (repare no recuo, ver 3.9)

saudar("Maria")   # MANDA fazer o truque com nome="Maria"  ->  escreve "ola, Maria"
saudar("Victor")  # de novo, com outro nome                ->  escreve "ola, Victor"
```

- O que vai dentro dos parênteses (`nome`) são os **ingredientes** que a função
  recebe pra trabalhar (o nome chique é "parâmetros" ou "argumentos").
- Às vezes a função **devolve** um resultado com a palavra `return`. Pense em
  `return` como "a função te entrega isto de volta na mão e termina":

```python
def dobro(x):
    return x * 2    # devolve o dobro do que entrou

y = dobro(5)        # y vira 10
```

### 3.7. `if` / `else` = **decisão** ("se isso, faça aquilo")

```python
if nivel > 0.5:                  # SE a sujeira passou da metade...
    print("a maquina ta pifando")  # ...faça isto
else:                            # SENAO (caso contrário)...
    print("ainda ta limpa")        # ...faça aquilo
```

### 3.8. `for` = **repetição** ("faça pra cada um da fila")

```python
for naipe in naipes:    # "pra CADA item da lista 'naipes', chame ele de 'naipe' e..."
    print(naipe)        # ...escreva ele. (vai escrever C, depois O, depois E, depois P)
```

E `range(12)` é um jeito de dizer "os números de 0 a 11" — útil pra "repita 12
vezes": `for _ in range(12):`. O `_` (underline sozinho) é um nome de caixa que
significa "tô repetindo, mas não ligo pro número em si".

### 3.9. O **recuo** (os espaços no começo da linha) **importa de verdade**

Esta é a regra que mais pega iniciante. Em Python, os **espaços no início da
linha** dizem **o que está "dentro" do quê**. As linhas mais "pra dentro"
pertencem ao `def`/`if`/`for` de cima. É como tópicos e subtópicos de uma lista:

```python
def saudar(nome):
    print("ola, " + nome)   # ESTA linha está dentro do 'saudar' (recuada)
print("fim")                # ESTA não está (voltou pra margem) — roda sempre
```

Se o recuo estiver errado, o programa nem roda. Então, quando você vir linhas
"empurradas pra direita", leia como "isto faz parte do bloco de cima".

---

## 4. Objetos e classes (a parte mais "abstrata" — devagar aqui)

Às vezes a gente quer um troço que **guarda coisas E sabe fazer coisas** ao
mesmo tempo. Exemplo: um "motor de sujeira" que **lembra** o quanto já sujou e
**sabe** sujar mais um pouco quando cai uma carta.

- Uma **classe** (`class`) é a **planta/molde**: descreve *como* esse troço é.
  Pense na planta de uma casa, ou no molde de biscoito.
- Um **objeto** é um troço **de verdade**, feito a partir da planta. Com um
  molde você faz vários biscoitos; com uma classe você cria vários objetos.

```python
motor = GlitchEngine()   # FABRICA um objeto 'motor' a partir da planta 'GlitchEngine'
motor.corrupt("K", "C")  # MANDA o objeto fazer um dos truques dele
```

O **ponto** (`.`) em `motor.corrupt(...)` quer dizer "deste objeto, use o truque
`corrupt`". E `motor.level` seria "deste objeto, me dê o valor guardado `level`".

Dentro da planta, aparece a palavra **`self`** o tempo todo. `self` é o jeito do
objeto **falar de si mesmo** — "eu". `self.level` é "o meu nível", `self.client`
é "o meu carteiro". É o que faz cada objeto ter as **suas próprias** coisas.

E tem o **`__init__`** (com esses dois underlines de cada lado): é a **"montagem"**
do objeto. Roda **uma vez**, automaticamente, no instante em que o objeto é
criado — é onde ele arruma as coisas iniciais (tipo "comece com a sujeira zerada").

---

## 5. Pegar ferramentas dos outros: `import`

Ninguém escreve tudo do zero. A palavra **`import`** (importar) puxa uma "caixa
de ferramentas" pronta pra você usar:

```python
import random              # puxa a caixa "random" (sorteios)
carta = random.choice(lista)   # usa a ferramenta "choice" (escolher um ao acaso) dela
```

Algumas caixas já vêm com o Python (`os`, `time`, `random`, `math`...). Outras a
gente **instalou** (`pythonosc`, `cv2`/OpenCV). E a gente também importa de
**arquivos nossos**: `from b_samples import RANKS` quer dizer "do nosso arquivo
`b_samples.py`, me empreste a `RANKS`".

> Pra instalar uma caixa de fora, usa-se o `pip` no terminal, ex:
> `pip install python-osc`. Isso é como baixar um app: faz uma vez, fica instalado.

---

## 6. Um detalhe que aparece no fim de quase todo arquivo

```python
if __name__ == "__main__":
    main()
```

Tradução pro português: **"SE este arquivo foi rodado *direto* (você digitou
`python b_glitch.py`), então execute a `main()`. Mas se ele foi só *importado*
por outro arquivo, NÃO execute nada disso."**

É o que permite cada arquivo ter um **modo demonstração** (pra testar sozinho)
que **não atrapalha** quando ele é usado como peça da máquina maior.

---

## 7. Como esse projeto está organizado (mapa rápido)

- Arquivos que começam com **`a_`** = a **CAMA** (o vibrafone, a camada A).
- Arquivos que começam com **`b_`** = o **MUNDO** (os habitats e a sujeira, camada B).
- **`.py`** = receitas em Python (o "cérebro" — decide o que tocar).
- **`.scd`** = receitas em SuperCollider (os "alto-falantes" — fazem o som de verdade).
- **`main.py`** = a porta de entrada: o menu que você roda primeiro.

E o coração da poética: **cada carta de verdade, virada na mesa, vira som**.
Os arquivos `.py` ouvem a carta e mandam recadinhos (por "OSC", um correio entre
programas) pros `.scd`, que fazem o barulho.

> Sugestão de leitura, do mais fácil pro mais difícil:
> **b_buraco → b_samples → b_teclado → b_aruco → a_cama → b_partida →
> a_osc → nucleo_compositor → main**. Cada um tem, no topo, um bloco
> "LEIA ISTO PRIMEIRO" explicando pra que ele serve.

Boa leitura. Vai com calma — ninguém aprendeu a ler tudo de uma vez. 🌱
