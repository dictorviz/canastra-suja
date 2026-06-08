// Grid retangular dinamico (cobre 100vw x 100vh, cellSize ~28px).
// Cada capitulo eh um ATRATOR que define a configuracao alvo dos glyphs.
// Cada celula flutua (offset, alpha, escala) — estetica Severance.
//
// Palavras-inventario aparecem em VERMELHO sobre o ruido azul, fade out.
// Spawn espontaneo no capitulo "inventario"; recitativos SSE que casam
// uma palavra do INVENTORIO tambem disparam o efeito vermelho.
//
// Renderiza num canvas proprio (z-index 1).
// Carrega DEPOIS de state.js (precisa de window.viz, INVENTORIO, paletas).

(function() {
  // Dimensoes do grid sao dinamicas — calculadas em resize() a partir do
  // tamanho da tela. Alvo: cellSize ~24px, grid cobre 100vw x 100vh.
  // Celulas RETANGULARES (cellW != cellH possivel) pra preencher tela exata
  // sem sobra/letterbox.
  let GRID_W = 64;
  let GRID_H = 36;
  const TARGET_CELL_PX = 24;

  // Glyph sets
  const ALPHA = 'abcdefghijklmnopqrstuvwxyz';
  const ACENTOS = 'áàâãéêíóôõúç';
  const DIGIT = '0123456789';
  const SUITS = '♠♥♦♣';   // ♠♥♦♣

  // Pool de algarismos do "ruido" de fundo do inventario (azul).
  // a-z + acentos PT + 0-9 + 4 naipes.
  const NOISE_POOL = (ALPHA + ACENTOS + DIGIT + SUITS).split('');
  const BOX_H = '─';   // ─
  const BOX_V = '│';   // │
  const BOX_TL = '┌';  // ┌
  const BOX_TR = '┐';  // ┐
  const BOX_BL = '└';  // └
  const BOX_BR = '┘';  // ┘
  const BOX_T  = '┬';  // ┬
  const BOX_B  = '┴';  // ┴
  const BOX_L  = '├';  // ├
  const BOX_R  = '┤';  // ┤
  const BOX_X  = '┼';  // ┼
  const SLASH = '/';
  const BSLASH = '\\';
  const ARROW_L = '<';
  const ARROW_R = '>';
  const ARROW_U = '^';
  const ARROW_D = 'v';
  const STAR = '*';
  const DOT = '.';
  const MID = '·';     // ·
  const BLOCK = '▒';   // ▒

  // ---------------------------------------------------------------------------
  // Estado
  // ---------------------------------------------------------------------------
  let canvas, ctx;
  let cellW = 14, cellH = 18;
  let cssW = 0, cssH = 0;
  let t = 0;

  let prevAttractor = 'prologo';
  let currentAttractor = 'prologo';
  let transitionT = 1.0;       // 0=acabou de mudar, 1=transicao completa
  const TRANSITION_DUR = 2.2;  // segundos

  // Linha (y) e palavra que esta "tocando" agora
  let activeWord = '';
  let activeWordY = -1;

  // ---------------------------------------------------------------------------
  // Hash deterministico (x, y, seed) -> uint32
  // ---------------------------------------------------------------------------
  function hashUint(x, y, seed) {
    let h = (((x | 0) * 374761393) ^ ((y | 0) * 668265263) ^ ((seed | 0) * 1274126177)) >>> 0;
    h = ((h ^ (h >>> 13)) * 1274126177) >>> 0;
    return h;
  }
  function rnd(x, y, seed) {
    return hashUint(x, y, seed) / 0xFFFFFFFF;
  }

  // ---------------------------------------------------------------------------
  // Flutuacao "Severance": cada celula tem fase e frequencia proprias e
  // oscila lentamente em x, y e alpha. Resultado: o grid parece vivo.
  // ---------------------------------------------------------------------------
  function floatOffsetX(x, y) {
    const phase = rnd(x, y, 91) * Math.PI * 2;
    const speed = 0.45 + rnd(x, y, 92) * 0.75;    // ~0.45-1.2 Hz
    return Math.sin(t * speed + phase) * 0.50;    // ±0.5 celula
  }
  function floatOffsetY(x, y) {
    const phase = rnd(x, y, 93) * Math.PI * 2;
    const speed = 0.40 + rnd(x, y, 94) * 0.70;
    return Math.cos(t * speed + phase) * 0.50;
  }
  function floatAlpha(x, y) {
    // Respiracao mais marcada: alpha varia entre 0.45 e 1.05
    const phase = rnd(x, y, 95) * Math.PI * 2;
    const speed = 0.55 + rnd(x, y, 96) * 0.90;
    return 0.75 + 0.30 * Math.sin(t * speed + phase);
  }
  function floatScale(x, y) {
    // Respiracao de tamanho visivel
    const phase = rnd(x, y, 97) * Math.PI * 2;
    const speed = 0.60 + rnd(x, y, 98) * 0.80;
    return 1.0 + 0.18 * Math.sin(t * speed + phase);
  }

  // Indice de ciclo da celula — muda a cada ~1.2-3.2s, mais movimentado.
  function cellCycle(x, y) {
    const period = 1.2 + rnd(x, y, 81) * 2.0;
    return Math.floor(t / period + rnd(x, y, 82) * 100);
  }

  // ---------------------------------------------------------------------------
  // ATRATORES — cada funcao retorna { ch, a } pra celula (x, y) no tempo t.
  // a = alpha 0..1. ch = caractere. Espaco vazio -> a=0.
  // ---------------------------------------------------------------------------

  function aPrologo(x, y) {
    // chuva calma de letras, com vazios — entropia media
    const r = rnd(x, y, 1);
    if (r < 0.45) return { ch: ' ', a: 0 };
    return { ch: ALPHA[Math.floor(r * 26)], a: 0.18 + r * 0.22 };
  }

  function aPagina(x, y) {
    // linhas horizontais de texto - alternancia linha/entrelinha
    const lineH = 3;
    if ((y % lineH) === 0) return { ch: ' ', a: 0 };
    const seed = Math.floor(y / lineH) * 31;
    const r = rnd(x, seed, 7);
    if (r < 0.18) return { ch: ' ', a: 0 };
    if (r < 0.92) return { ch: ALPHA[Math.floor(r * 26)], a: 0.32 + r * 0.30 };
    return { ch: ',', a: 0.4 };
  }

  function aCama(x, y) {
    // retangulo horizontal achatado centrado, com travesseiro e cobertor
    const cx = GRID_W / 2, cy = GRID_H / 2 + 2;
    const dx = x - cx, dy = y - cy;
    const HW = 18, HH = 5;
    const onSideV = (Math.abs(dx) === HW) && (Math.abs(dy) <= HH);
    const onSideH = (Math.abs(dy) === HH) && (Math.abs(dx) <= HW);
    const isCorner = (Math.abs(dx) === HW) && (Math.abs(dy) === HH);
    if (isCorner) {
      const ch = dy < 0 ? (dx < 0 ? BOX_TL : BOX_TR) : (dx < 0 ? BOX_BL : BOX_BR);
      return { ch, a: 0.85 };
    }
    if (onSideV) return { ch: BOX_V, a: 0.7 };
    if (onSideH) return { ch: BOX_H, a: 0.7 };
    // travesseiro
    if (dy < -2 && dy >= -4 && Math.abs(dx + 10) <= 3) return { ch: BLOCK, a: 0.35 };
    // hachura do cobertor
    if (Math.abs(dy) < HH && Math.abs(dx) < HW) {
      if ((x + y) % 5 === 0) return { ch: MID, a: 0.18 };
    }
    return { ch: ' ', a: 0 };
  }

  function aQuarto(x, y) {
    // caixa quadrada grande
    const m = 8;
    const top = m, bot = GRID_H - m - 1;
    const left = m, right = GRID_W - m - 1;
    if (y === top || y === bot) {
      if (x === left) return { ch: y === top ? BOX_TL : BOX_BL, a: 0.9 };
      if (x === right) return { ch: y === top ? BOX_TR : BOX_BR, a: 0.9 };
      if (x > left && x < right) return { ch: BOX_H, a: 0.55 };
    }
    if ((x === left || x === right) && y > top && y < bot) return { ch: BOX_V, a: 0.55 };
    return { ch: ' ', a: 0 };
  }

  function aApartamento(x, y) {
    // 4 quartos conectados (planta-baixa). dividida em 2x2
    const halfX = GRID_W / 2;
    const halfY = GRID_H / 2;
    const m = 5;
    function inRoom(x, y, x0, y0, x1, y1) {
      if (y === y0 || y === y1) {
        if (x === x0) return { ch: y === y0 ? BOX_TL : BOX_BL, a: 0.85 };
        if (x === x1) return { ch: y === y0 ? BOX_TR : BOX_BR, a: 0.85 };
        if (x > x0 && x < x1) {
          // deixa um "vao" no meio (porta)
          if (Math.abs(x - (x0 + x1) / 2) < 1) return { ch: ' ', a: 0 };
          return { ch: BOX_H, a: 0.5 };
        }
      }
      if ((x === x0 || x === x1) && y > y0 && y < y1) {
        if (Math.abs(y - (y0 + y1) / 2) < 1) return { ch: ' ', a: 0 };
        return { ch: BOX_V, a: 0.5 };
      }
      return null;
    }
    let r;
    r = inRoom(x, y, m, m, halfX - 1, halfY - 1); if (r) return r;
    r = inRoom(x, y, halfX + 1, m, GRID_W - m - 1, halfY - 1); if (r) return r;
    r = inRoom(x, y, m, halfY + 1, halfX - 1, GRID_H - m - 1); if (r) return r;
    r = inRoom(x, y, halfX + 1, halfY + 1, GRID_W - m - 1, GRID_H - m - 1); if (r) return r;
    return { ch: ' ', a: 0 };
  }

  function aPorta(x, y) {
    // retangulo vertical no centro com gap (entrada)
    const cx = GRID_W / 2, cy = GRID_H / 2;
    const HW = 8, HH = 20;
    const dx = x - cx, dy = y - cy;
    const onLeft = (dx === -HW) && (Math.abs(dy) <= HH);
    const onRight = (dx === HW) && (Math.abs(dy) <= HH);
    const onTop = (dy === -HH) && (Math.abs(dx) <= HW);
    const onBot = (dy === HH) && (Math.abs(dx) <= HW);
    if (onTop && dx === -HW) return { ch: BOX_TL, a: 0.95 };
    if (onTop && dx === HW) return { ch: BOX_TR, a: 0.95 };
    if (onTop) return { ch: BOX_H, a: 0.7 };
    if (onLeft || onRight) return { ch: BOX_V, a: 0.7 };
    if (onBot && (dx === -HW || dx === HW)) return { ch: dx < 0 ? BOX_BL : BOX_BR, a: 0.95 };
    if (onBot && Math.abs(dx) > 1) return { ch: BOX_H, a: 0.7 };
    // macaneta
    if (dx === HW - 2 && dy === 2) return { ch: 'o', a: 0.8 };
    // hachura interna da porta
    if (Math.abs(dx) < HW && Math.abs(dy) < HH && ((x + y * 2) % 7 === 0))
      return { ch: '|', a: 0.15 };
    return { ch: ' ', a: 0 };
  }

  function aEscada(x, y) {
    // zig-zag descendente
    const step = 4;
    const targetY = Math.floor((x / GRID_W) * GRID_H);
    if (Math.abs(y - targetY) === 0) return { ch: BOX_H, a: 0.7 };
    if ((x % step === 0) && Math.abs(y - targetY) < step && y > targetY)
      return { ch: BOX_V, a: 0.7 };
    // sombras tracejadas
    if (y > targetY && y < targetY + step && (x + y) % 3 === 0)
      return { ch: MID, a: 0.15 };
    return { ch: ' ', a: 0 };
  }

  function aParede(x, y) {
    // tijolo: linhas horizontais alternando offset (igual parede real)
    if (y % 3 === 0) return { ch: BOX_H, a: 0.55 };
    if (y % 3 === 1) {
      const off = (Math.floor(y / 3) % 2) * 4;
      if ((x + off) % 8 === 0) return { ch: BOX_V, a: 0.55 };
    }
    return { ch: ' ', a: 0 };
  }

  function aPredio(x, y) {
    // empilhamento vertical de "andares"
    const floorH = 6;
    const W = 22;
    const cx = GRID_W / 2;
    const onSide = (x === cx - W / 2) || (x === cx + W / 2);
    const isFloor = (y % floorH === 0);
    if (onSide && y >= 6 && y < GRID_H - 4) return { ch: BOX_V, a: 0.7 };
    if (isFloor && y >= 6 && y < GRID_H - 4
        && x > cx - W / 2 && x < cx + W / 2) return { ch: BOX_H, a: 0.55 };
    // janelas
    if (y % floorH === 3 && Math.abs((x - cx) % 6) < 1
        && Math.abs(x - cx) <= W / 2 - 3) return { ch: BLOCK, a: 0.4 };
    return { ch: ' ', a: 0 };
  }

  function aRua(x, y) {
    // corredor horizontal central com marcacoes nas bordas
    const cy = GRID_H / 2;
    if (y === cy - 6 || y === cy + 6) return { ch: BOX_H, a: 0.65 };
    if (y === cy && (x % 4 < 2)) return { ch: BOX_H, a: 0.40 };  // faixa central
    // "predios" baixos nas margens
    if (y < cy - 6) {
      const cellSeed = Math.floor(x / 6) * 13;
      const h = Math.floor(rnd(cellSeed, 0, 5) * 5) + 2;
      if (y >= cy - 6 - h) return { ch: BLOCK, a: 0.35 };
    }
    if (y > cy + 6) {
      const cellSeed = Math.floor(x / 6) * 17;
      const h = Math.floor(rnd(cellSeed, 0, 9) * 5) + 2;
      if (y <= cy + 6 + h) return { ch: BLOCK, a: 0.35 };
    }
    return { ch: ' ', a: 0 };
  }

  function aBairro(x, y) {
    // varias caixas pequenas (predios) numa grid
    const block = 8;
    const inX = x % block, inY = y % block;
    if (inX === 0 || inX === 6) return { ch: BOX_V, a: 0.45 };
    if (inY === 0 || inY === 6) return { ch: BOX_H, a: 0.45 };
    // janelinhas
    if ((inX === 3 || inX === 5) && (inY === 3 || inY === 4))
      return { ch: MID, a: 0.25 };
    return { ch: ' ', a: 0 };
  }

  function aCidade(x, y) {
    // skyline - barras de altura variavel determinadas por hash
    const skyTop = 14;
    const groundY = GRID_H - 8;
    if (y === groundY) return { ch: BOX_H, a: 0.65 };
    if (y > groundY) {
      if ((x + y) % 3 === 0) return { ch: MID, a: 0.18 };
      return { ch: ' ', a: 0 };
    }
    // altura do predio na coluna x
    const colSeed = Math.floor(x / 3) * 7;
    const h = Math.floor(rnd(colSeed, 0, 11) * (groundY - skyTop)) + 4;
    if (y >= groundY - h) {
      if ((y === groundY - h)) return { ch: BOX_H, a: 0.7 };
      // janelas iluminadas
      if ((x + y * 2) % 5 === 0) return { ch: BLOCK, a: 0.45 };
      return { ch: BOX_V, a: 0.35 };
    }
    // estrelas raras
    if (y < skyTop / 2 && rnd(x, y, 99) > 0.97) return { ch: STAR, a: 0.5 };
    return { ch: ' ', a: 0 };
  }

  function aCampo(x, y) {
    // dispersao orgânica esparsa, muito espaco aberto
    const r = rnd(x, y, 21);
    if (r > 0.97) return { ch: '*', a: 0.4 };       // flor/estrela
    if (r > 0.92) return { ch: MID, a: 0.2 };       // grama
    if (r > 0.88) return { ch: '.', a: 0.15 };
    return { ch: ' ', a: 0 };
  }

  function aMovimento(x, y) {
    // setas direcionais em padrao de fluxo
    const phase = ((x + y * 0.7) * 0.15 + t * 0.5) % 4;
    if (Math.abs((x % 6) - 3) < 1 && Math.abs((y % 4) - 2) < 1) {
      const dir = Math.floor(phase) % 4;
      const ch = [ARROW_R, ARROW_D, ARROW_L, ARROW_U][dir];
      return { ch, a: 0.45 };
    }
    return { ch: ' ', a: 0 };
  }

  function aPais(x, y) {
    // contorno irregular - blob assimetrico
    const cx = GRID_W / 2, cy = GRID_H / 2;
    const dx = x - cx, dy = y - cy;
    const r = Math.sqrt(dx * dx + dy * dy);
    const angle = Math.atan2(dy, dx);
    // forma com perturbacao senoidal nos varios harmonics
    const noise = 0.5 + 0.18 * Math.sin(angle * 3) + 0.12 * Math.sin(angle * 5 + 1.3)
                  + 0.08 * Math.sin(angle * 7 - 0.4);
    const limit = 18 * noise + 6;
    if (Math.abs(r - limit) < 1) return { ch: rnd(x, y, 3) > 0.5 ? SLASH : BSLASH, a: 0.7 };
    if (r < limit && (x + y) % 4 === 0) return { ch: MID, a: 0.12 };
    return { ch: ' ', a: 0 };
  }

  function aMundo(x, y) {
    // grande circulo (esfera) com hachura de longitudes
    const cx = GRID_W / 2, cy = GRID_H / 2;
    const dx = x - cx, dy = y - cy;
    const r = Math.sqrt(dx * dx + dy * dy);
    const R = 22;
    if (Math.abs(r - R) < 0.7) return { ch: rnd(x, y, 1) > 0.5 ? '(' : ')', a: 0.6 };
    if (r < R) {
      // meridianos
      if ((x % 4 === 0) && (Math.abs(dx) < R * 0.95))
        return { ch: BOX_V, a: 0.13 };
      // paralelos (curvas)
      const ringRatio = r / R;
      if (Math.abs(ringRatio - 0.5) < 0.05 || Math.abs(ringRatio - 0.8) < 0.05)
        return { ch: BOX_H, a: 0.13 };
    }
    return { ch: ' ', a: 0 };
  }

  function aEspaco(x, y) {
    // espaco cosmico - pontos esparsos como estrelas
    const r = rnd(x, y, 88);
    if (r > 0.992) return { ch: STAR, a: 0.85 };
    if (r > 0.97) return { ch: '+', a: 0.45 };
    if (r > 0.93) return { ch: '.', a: 0.3 };
    return { ch: ' ', a: 0 };
  }

  function aLinhasRetas(x, y) {
    // grade perpendicular pura - linhas + cruzamentos
    if (x % 6 === 0 && y % 6 === 0) return { ch: BOX_X, a: 0.7 };
    if (x % 6 === 0) return { ch: BOX_V, a: 0.45 };
    if (y % 6 === 0) return { ch: BOX_H, a: 0.45 };
    return { ch: ' ', a: 0 };
  }

  function aMedidas(x, y) {
    // reguas nas bordas + numeracao
    if (y === 0 || y === GRID_H - 1) {
      if (x % 5 === 0) return { ch: String(((x / 5) | 0) % 10), a: 0.6 };
      if (x % 2 === 0) return { ch: '│', a: 0.4 };
      return { ch: '.', a: 0.25 };
    }
    if (x === 0 || x === GRID_W - 1) {
      if (y % 5 === 0) return { ch: String(((y / 5) | 0) % 10), a: 0.6 };
      if (y % 2 === 0) return { ch: '─', a: 0.4 };
      return { ch: '.', a: 0.25 };
    }
    // grid interno bem leve
    if (x % 10 === 0 && y % 10 === 0) return { ch: '+', a: 0.18 };
    return { ch: ' ', a: 0 };
  }

  function aBrincar(x, y) {
    // padrao ludico - X's, O's intercalados
    const r = rnd(x, y, 33);
    if (r > 0.85) {
      const pick = Math.floor(r * 13) % 4;
      return { ch: ['x', 'o', '+', '#'][pick], a: 0.55 };
    }
    return { ch: ' ', a: 0 };
  }

  function aConquista(x, y) {
    // setas projetando de centro pra fora
    const cx = GRID_W / 2, cy = GRID_H / 2;
    const dx = x - cx, dy = y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 1) return { ch: '+', a: 0.95 };
    const angle = Math.atan2(dy, dx);
    // 8 raios direcionais
    const sector = Math.round(angle / (Math.PI / 4));
    const expected = sector * Math.PI / 4;
    if (Math.abs(angle - expected) < 0.18 && dist < 26) {
      const ch = [ARROW_R, BSLASH, ARROW_D, SLASH, ARROW_L, BSLASH, ARROW_U, SLASH][((sector % 8) + 8) % 8];
      // pulsa com t — mais brilho perto da onda atual
      const wave = ((dist * 0.7) - (t * 8)) % 8;
      const a = 0.4 + Math.max(0, 0.5 - Math.abs(wave - 2) * 0.15);
      return { ch, a };
    }
    return { ch: ' ', a: 0 };
  }

  function aInabitavel(x, y) {
    // caos denso - tudo sobreposto, ilegivel
    const seed = (x * 7 + y * 13 + Math.floor(t * 2)) | 0;
    const r = rnd(x, y, seed);
    const pool = ALPHA + DIGIT + DIGIT + ALPHA + '/\\#@!?*';
    return { ch: pool[Math.floor(r * pool.length)], a: 0.5 + r * 0.35 };
  }

  function aFim(x, y) {
    // dissipacao - poucos chars, vazio crescente
    const r = rnd(x, y, 200);
    if (r > 0.96) return { ch: '.', a: 0.18 };
    return { ch: ' ', a: 0 };
  }

  function aInventario(x, y) {
    // Fundo: ruido denso do NOISE_POOL, cada celula ciclando devagar.
    // Sem palavras embutidas — as palavras-inventario sao sobrepostas via
    // sistema de activeWords (renderizadas em vermelho).
    const cyc = cellCycle(x, y);
    const r = rnd(x, y + cyc * 7, 71);
    // ~22% de celulas em branco — respiro visual
    if (r < 0.22) return { ch: ' ', a: 0 };
    const idx = Math.floor(rnd(x + cyc, y, 73) * NOISE_POOL.length);
    return { ch: NOISE_POOL[idx % NOISE_POOL.length], a: 0.42 + r * 0.38 };
  }

  function aNeutro(x, y) {
    return aPrologo(x, y);
  }

  // Fundo de "preenchimento" — usado quando o atrator deixaria a celula vazia.
  // Ruido leve do NOISE_POOL com alpha baixo, pra eliminar quadradinhos em
  // branco e manter a tela inteiramente viva.
  function aBackgroundFill(x, y) {
    const cyc = cellCycle(x, y);
    const r = rnd(x, y + cyc * 11, 161);
    // Pequena chance de respirar vazio (~12%) - evita uniformidade morta
    if (r < 0.12) return { ch: ' ', a: 0 };
    const idx = Math.floor(rnd(x + cyc, y, 163) * NOISE_POOL.length);
    return { ch: NOISE_POOL[idx % NOISE_POOL.length], a: 0.10 + r * 0.16 };
  }

  function sample(attractor, x, y) {
    switch (attractor) {
      case 'prologo':       return aPrologo(x, y);
      case 'pagina':        return aPagina(x, y);
      case 'cama':          return aCama(x, y);
      case 'quarto':        return aQuarto(x, y);
      case 'apartamento':   return aApartamento(x, y);
      case 'porta':         return aPorta(x, y);
      case 'escada':        return aEscada(x, y);
      case 'parede':        return aParede(x, y);
      case 'predio':        return aPredio(x, y);
      case 'rua':           return aRua(x, y);
      case 'bairro':        return aBairro(x, y);
      case 'cidade':        return aCidade(x, y);
      case 'campo':         return aCampo(x, y);
      case 'movimento':     return aMovimento(x, y);
      case 'pais':          return aPais(x, y);
      case 'mundo':         return aMundo(x, y);
      case 'espaco':        return aEspaco(x, y);
      case 'linhas_retas':  return aLinhasRetas(x, y);
      case 'medidas':       return aMedidas(x, y);
      case 'brincar':       return aBrincar(x, y);
      case 'conquista':     return aConquista(x, y);
      case 'inabitavel':    return aInabitavel(x, y);
      case 'fim':           return aFim(x, y);
      case 'inventario':    return aInventario(x, y);
      default:              return aNeutro(x, y);
    }
  }

  // ---------------------------------------------------------------------------
  // Palavra falada -> overlay legivel numa linha do grid
  // ---------------------------------------------------------------------------
  function pickActiveWord() {
    const txt = (window.viz.lastSpoken || '').trim();
    const age = window.viz.spokenAge;
    if (!txt || age > 4.0) {
      activeWord = '';
      activeWordY = -1;
      return;
    }
    // pega a primeira "frase" curta
    let snippet = txt.replace(/\s+/g, ' ');
    if (snippet.length > GRID_W - 4) snippet = snippet.slice(0, GRID_W - 4);
    activeWord = snippet;
    // linha estavel por nota (hash do texto)
    if (activeWordY < 0) {
      let h = 0;
      for (let i = 0; i < txt.length; i++) h = (h * 31 + txt.charCodeAt(i)) | 0;
      activeWordY = Math.abs(h) % (GRID_H - 4) + 2;
    }
  }

  function overlayWord(x, y) {
    if (!activeWord || y !== activeWordY) return null;
    const wx = Math.floor((GRID_W - activeWord.length) / 2);
    if (x >= wx && x < wx + activeWord.length) {
      const ch = activeWord[x - wx];
      if (ch === ' ') return null;
      const age = window.viz.spokenAge;
      const fade = Math.max(0, 1 - age / 4.0);
      return { ch, a: 0.55 + 0.40 * fade, highlight: true };
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Palavras-inventario: aparecem em VERMELHO, somem em fade out.
  // Cada palavra tem posicao, orientacao (h/v) e tempo de vida.
  // ---------------------------------------------------------------------------
  const activeInventoryWords = [];   // { texto, col, row, orient, born, life, primary }
  const INV_LIFETIME = 3.6;          // segundos de vida total (com fade)
  // Spawns ESPONTANEOS (fundo) ficam mais raros: a palavra FALADA eh quem
  // dirige a tela agora, os aleatorios so dao textura de "inventario vivo".
  const INV_SPAWN_MIN = 1.8;         // intervalo minimo entre spawns de fundo
  const INV_SPAWN_MAX = 4.0;         // intervalo maximo
  let nextInvSpawnAt = 1.5;

  // primary=true => palavra FALADA (destaque forte, no tempo do audio).
  // primary=false => spawn espontaneo de fundo (esmaecido).
  function spawnInventoryWord(forcedText, primary) {
    const inv = window.INVENTORIO || [];
    if (!inv.length && !forcedText) return;
    const texto = forcedText || inv[Math.floor(Math.random() * inv.length)].palavra;

    // Se a palavra tem um RABISCO 2D, desenha o sketch em vez do texto.
    const sketches = window.INV_SKETCHES || {};
    const sketch = sketches[normalizePT(texto)];
    if (sketch && sketch.length) {
      const sw = sketch.reduce((m, l) => Math.max(m, l.length), 0);
      const sh = sketch.length;
      const col = Math.floor(Math.random() * Math.max(1, GRID_W - sw - 1));
      const row = Math.floor(Math.random() * Math.max(1, GRID_H - sh - 1));
      activeInventoryWords.push({ sketch, col, row, born: t, life: INV_LIFETIME, primary: !!primary });
      return;
    }

    // Palavra falada prefere horizontal (mais legivel); fundo varia.
    const orient = primary ? 'h' : ((Math.random() < 0.82) ? 'h' : 'v');
    let col, row;
    if (orient === 'h') {
      const maxCol = Math.max(1, GRID_W - texto.length - 1);
      col = Math.floor(Math.random() * maxCol);
      row = Math.floor(Math.random() * (GRID_H - 2)) + 1;
    } else {
      const maxRow = Math.max(1, GRID_H - texto.length - 1);
      col = Math.floor(Math.random() * (GRID_W - 1)) + 1;
      row = Math.floor(Math.random() * maxRow);
    }
    activeInventoryWords.push({ texto, col, row, orient, born: t, life: INV_LIFETIME, primary: !!primary });
  }

  function updateInventoryWords() {
    // Remove expiradas
    for (let i = activeInventoryWords.length - 1; i >= 0; i--) {
      if (t - activeInventoryWords[i].born > activeInventoryWords[i].life) {
        activeInventoryWords.splice(i, 1);
      }
    }
    // Spawn espontaneo so durante capitulo inventario
    if (currentAttractor === 'inventario' && t >= nextInvSpawnAt) {
      spawnInventoryWord();
      nextInvSpawnAt = t + INV_SPAWN_MIN + Math.random() * (INV_SPAWN_MAX - INV_SPAWN_MIN);
    }
  }

  // Se SSE trouxe uma palavra do inventario via lastSpoken, dispara em vermelho
  let lastSpokenSeen = '';
  const DIACRITICS = /[̀-ͯ]/g;
  function normalizePT(s) {
    return s.normalize('NFD').replace(DIACRITICS, '').toLowerCase();
  }
  function consumeSpokenInventory() {
    const spoken = (window.viz.lastSpoken || '').trim();
    if (!spoken || spoken === lastSpokenSeen) return;
    if (window.viz.spokenAge > 0.5) return;   // muito antiga, ignora
    lastSpokenSeen = spoken;
    // TODA palavra falada vira destaque (primary), no instante em que o SC
    // a toca (word_now). Se ela existir no inventario, usa a grafia bonita
    // (com acentos/maiusculas); senao mostra a propria falada capitalizada.
    // Antes so aparecia se casasse com as 13 do INVENTORIO -> a maioria do
    // que se ouvia nunca aparecia, dando a sensacao de dessincronia.
    const inv = window.INVENTORIO || [];
    const spokenN = normalizePT(spoken);
    let display = null;
    for (const item of inv) {
      const n = normalizePT(item.palavra);
      if (spokenN.includes(n) || n.includes(spokenN)) { display = item.palavra; break; }
    }
    if (!display) display = spoken.charAt(0).toUpperCase() + spoken.slice(1);
    spawnInventoryWord(display, true);
  }

  // Procura char vermelho cobrindo (x, y) por alguma palavra ativa.
  // Retorna { ch, a, fade } ou null.
  function inventoryCharAt(x, y) {
    for (let i = activeInventoryWords.length - 1; i >= 0; i--) {
      const w = activeInventoryWords[i];
      const age = t - w.born;
      // Fade-in rapido nos primeiros 0.25s, fade-out a partir de ~60% da vida
      const fadeInDur = 0.25;
      const fadeOutStart = w.life * 0.55;
      let fade;
      if (age < fadeInDur) fade = age / fadeInDur;
      else if (age > fadeOutStart) {
        fade = Math.max(0, 1 - (age - fadeOutStart) / (w.life - fadeOutStart));
      } else fade = 1.0;
      // Fundo (nao-falada) entra esmaecido pra palavra falada se destacar.
      const dim = w.primary ? 1.0 : 0.42;
      // Rabisco 2D (sketch): bounding box de varias linhas.
      if (w.sketch) {
        const sy = y - w.row;
        if (sy < 0 || sy >= w.sketch.length) continue;
        const line = w.sketch[sy];
        const sx = x - w.col;
        if (sx < 0 || sx >= line.length) continue;
        const ch = line[sx];
        if (!ch || ch === ' ') continue;
        return { ch, a: fade * dim, fade, primary: w.primary };
      }
      if (w.orient === 'h') {
        if (y !== w.row) continue;
        if (x < w.col || x >= w.col + w.texto.length) continue;
        const ch = w.texto[x - w.col];
        if (!ch || ch === ' ') continue;
        return { ch, a: fade * dim, fade, primary: w.primary };
      } else {
        if (x !== w.col) continue;
        if (y < w.row || y >= w.row + w.texto.length) continue;
        const ch = w.texto[y - w.row];
        if (!ch || ch === ' ') continue;
        return { ch, a: fade * dim, fade, primary: w.primary };
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  // Offset pra centralizar a grade quadrada na tela
  let offX = 0, offY = 0;
  let cellSize = 16;
  // Tamanho do grid em pixels (visivel)
  let gridPxW = 0, gridPxH = 0;

  function ensureCanvas() {
    if (canvas) return;
    canvas = document.createElement('canvas');
    canvas.id = 'grid-canvas';
    Object.assign(canvas.style, {
      position: 'fixed',
      inset: '0',
      width: '100vw',
      height: '100vh',
      zIndex: '1',
      pointerEvents: 'none',
    });
    document.body.appendChild(canvas);
    ctx = canvas.getContext('2d');
    resize();
    window.addEventListener('resize', resize);
  }

  function resize() {
    cssW = window.innerWidth;
    cssH = window.innerHeight;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Grid retangular real: cellW e cellH independentes pra preencher 100%
    // exato sem sobra/letterbox em qualquer aspect ratio.
    GRID_W = Math.max(24, Math.floor(cssW / TARGET_CELL_PX));
    GRID_H = Math.max(14, Math.floor(cssH / TARGET_CELL_PX));
    cellW = cssW / GRID_W;
    cellH = cssH / GRID_H;
    cellSize = Math.min(cellW, cellH);   // base pra fontSize/lineWidth
    gridPxW = cssW;
    gridPxH = cssH;
    offX = 0;
    offY = 0;

    activeWordY = -1;
  }

  function setAttractor(attr) {
    if (attr === currentAttractor) return;
    prevAttractor = currentAttractor;
    currentAttractor = attr;
    transitionT = 0;
    activeWordY = -1;   // forca recalcular linha da palavra
  }

  // -------------------------------------------------------------------------
  // Glyph escolhido — interpola entre prev e current usando "tempo de
  // mudanca" deterministico por celula (entre 0 e 1).
  // -------------------------------------------------------------------------
  function glyphAt(x, y) {
    let s;
    if (transitionT >= 1) {
      s = sample(currentAttractor, x, y);
    } else {
      const cellTime = rnd(x, y, 42);
      s = transitionT >= cellTime
        ? sample(currentAttractor, x, y)
        : sample(prevAttractor, x, y);
    }
    // Inventario gera fundo proprio (denso), nao precisa fill.
    if (currentAttractor === 'inventario') return s;
    // Se o atrator deixou a celula vazia, preenche com ruido leve
    if (!s || !s.ch || s.ch === ' ' || s.a <= 0.02) {
      return aBackgroundFill(x, y);
    }
    return s;
  }

  // -------------------------------------------------------------------------
  // Cor azul do glyph - varia de claro a escuro por hash da celula.
  // Celulas com alpha mais alto ganham azul mais escuro (peso visual).
  // -------------------------------------------------------------------------
  function glyphColor(x, y, alpha, highlight) {
    const blues = window.CW_BLUES || [[28,64,124],[56,96,160],[88,128,188],[124,160,208],[168,192,220]];
    if (highlight) {
      // palavra falada — azul mais escuro/saturado
      return blues[0];
    }
    // indice por hash da celula deslocado pelo alpha (alpha alto -> azul mais escuro)
    const h = hashUint(x, y, 11) % 100;
    const tilt = Math.floor((1 - Math.min(1, alpha)) * 2);   // 0..2
    const idx = Math.max(0, Math.min(blues.length - 1,
                Math.floor(h / 25) + tilt - 1));
    return blues[idx];
  }

  function render(dt) {
    if (!canvas) return;
    t += dt;
    if (transitionT < 1) {
      transitionT = Math.min(1, transitionT + dt / TRANSITION_DUR);
    }

    // Mantem o atrator atualizado a partir de window.viz
    if (window.viz.attractor && window.viz.attractor !== currentAttractor) {
      setAttractor(window.viz.attractor);
    }
    pickActiveWord();
    updateInventoryWords();
    consumeSpokenInventory();

    // Pulsa global - sutilmente reage ao beatPulse
    const pulse = 1 + (window.viz.beatPulse || 0) * 0.10;

    // === Fundo branco ===
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, cssW, cssH);

    // === Letras (sem numeracao crossword, sem moldura) ===
    const baseFont = Math.floor(cellSize * 0.82);
    const reds = window.CW_REDS || [[196, 44, 60], [176, 56, 72], [200, 92, 104], [216, 144, 152]];

    for (let y = 0; y < GRID_H; y++) {
      for (let x = 0; x < GRID_W; x++) {
        // Prioridade: 1) palavra-inventario vermelha 2) overlay recitativo 3) glyph base
        const invHit = inventoryCharAt(x, y);
        const ovr = invHit ? null : overlayWord(x, y);
        const sel = invHit
          ? { ch: invHit.ch, a: invHit.a, highlight: true }
          : (ovr || glyphAt(x, y));
        if (!sel || !sel.ch || sel.a <= 0.02 || sel.ch === ' ') continue;

        const dxOff = floatOffsetX(x, y) * cellW;
        const dyOff = floatOffsetY(x, y) * cellH;
        const aMod  = floatAlpha(x, y);
        const scale = floatScale(x, y);

        const px = offX + (x + 0.5) * cellW + dxOff;
        const py = offY + (y + 0.5) * cellH + dyOff;
        const a = Math.min(1, sel.a * pulse * aMod);
        const fontSize = Math.max(8, Math.floor(baseFont * scale));

        let col;
        if (invHit) {
          const ri = invHit.fade > 0.75 ? 0
                   : invHit.fade > 0.45 ? 1
                   : invHit.fade > 0.20 ? 2 : 3;
          col = reds[ri];
        } else {
          col = glyphColor(x, y, sel.a, !!ovr);
        }

        ctx.font = `${fontSize}px VT323, monospace`;
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'center';
        ctx.fillStyle = `rgba(${col[0]}, ${col[1]}, ${col[2]}, ${a.toFixed(3)})`;
        ctx.fillText(sel.ch, px, py);
      }
    }
  }

  // -------------------------------------------------------------------------
  // Loop proprio (independente do p5)
  // -------------------------------------------------------------------------
  let lastT = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, (now - lastT) / 1000);
    lastT = now;
    render(dt);
    requestAnimationFrame(loop);
  }

  function init() {
    ensureCanvas();
    requestAnimationFrame((now) => { lastT = now; loop(now); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
