// Estado global compartilhado entre componentes do visualizer.

window.viz = {
  currentSuit: 'COPAS',
  intensity: 0.4,
  beatPulse: 0.0,     // 0..1, decai apos cada ataque
  articulation: 'NORMAL',
  fermata: false,
  staccato: false,
  tenuto: false,
  accento: false,
  noteCount: 0,
  // --- Perec / capitulos ---
  capituloId: '0',
  capituloNome: 'Prologo',
  attractor: 'prologo',   // alvo morfologico atual do grid 64x64
  // Ultima fala/recitativo recebido (pro grid destacar).
  // Dirigido por evento 'word_now' do SC: uma palavra por vez, sincronizada
  // com a Routine de fala. spokenSource = 'echo' | 'recitativo'.
  lastSpoken: '',
  spokenAge: 999,         // segundos desde a fala
  spokenSource: 'echo',
};

// Paleta por naipe — tons de azul (claro a escuro) sobre fundo branco.
// main = cor principal do naipe, soft = mais clara, accent = destaque.
window.SUIT_PALETTE = {
  COPAS:   { main: [120, 156, 200], soft: [180, 200, 224], accent: [ 60,  96, 156] },  // azul medio
  OUROS:   { main: [ 92, 140, 196], soft: [160, 190, 222], accent: [ 40,  84, 152] },  // azul navy claro
  PAUS:    { main: [156, 184, 220], soft: [200, 218, 236], accent: [ 80, 120, 176] },  // azul pastel
  ESPADAS: { main: [ 36,  72, 132], soft: [108, 144, 192], accent: [ 20,  44,  96] },  // azul escuro
};

// Tons base do tema palavras cruzadas (azul claro -> escuro).
window.CW_BLUES = [
  [ 28,  64, 124],   // 0: muito escuro
  [ 56,  96, 160],   // 1: escuro
  [ 88, 128, 188],   // 2: medio
  [124, 160, 208],   // 3: claro
  [168, 192, 220],   // 4: muito claro
];
window.CW_GRID_LINE = [180, 196, 218];   // linhas finas da grade
window.CW_NUMBER    = [ 60,  96, 156];   // numeros tipo crossword (top-left)

// Vermelhos do destaque das palavras-inventario.
// Tons quentes do claro (recente) ao escuro (auge da aparicao).
window.CW_REDS = [
  [196,  44,  60],   // 0: vermelho cheio (auge)
  [176,  56,  72],   // 1
  [200,  92, 104],   // 2: clareando no fade
  [216, 144, 152],   // 3: pastel rosado
];

// ---------------------------------------------------------------------------
// INVENTARIO — palavras com IPA, alimentadas pelo usuario.
// O visualizer usa `palavra` pra render; `ipa` fica pronto pra recitativo/synth.
// ---------------------------------------------------------------------------
window.INVENTORIO = [
  { palavra: 'Adler, Larry',          ipa: 'ˈæd.lɚ, ˈlɛɹ' },
  { palavra: 'Agenda',                ipa: 'aˈʒẽ.dɐ' },
  { palavra: 'Alfafa',                ipa: 'awˈfa.fɐ' },
  { palavra: 'Alma',                  ipa: 'ˈaw.mɐ' },
  { palavra: 'Almofada',              ipa: 'aw.muˈfa.dɐ' },
  { palavra: 'Alpinista',             ipa: 'aw.piˈnis.tɐ' },
  { palavra: 'Amarelo',               ipa: 'a.maˈɾɛ.lu' },
  { palavra: 'Amiens',                ipa: 'aˈmjɛ̃' },
  { palavra: 'Angostura',             ipa: 'ɐ̃.ɡosˈtu.ɾɐ' },
  { palavra: 'Área de serviço',       ipa: 'ˈa.ɾjɐ d͡ʒi seʁˈvi.su' },
  { palavra: 'Areias de Beauchamp',   ipa: 'aˈɾej.ɐs d͡ʒi boˈʃã' },
  { palavra: 'Avery, Tex',            ipa: 'ˈeɪ.və.ɹi, tɛks' },
  { palavra: 'Avião',                 ipa: 'a.viˈɐ̃w' },
  { palavra: 'Babás',                 ipa: 'baˈbas' },
  { palavra: 'Bach, Johann Sebastian',ipa: 'ˈbax, ˈjoːhan zeˈbas.ti̯an' },
  { palavra: 'Balança de banheiro',   ipa: 'baˈlɐ̃.sɐ d͡ʒi bɐˈɲej.ɾu' },
  { palavra: 'Bandeira francesa',     ipa: 'bɐ̃ˈdej.ɾɐ fɾɐ̃ˈse.zɐ' },
  { palavra: 'Banhos públicos',       ipa: 'ˈbɐ.ɲus ˈpu.bli.kus' },
  { palavra: 'Baobá',                 ipa: 'ba.oˈba' },
  { palavra: 'Barômetro',             ipa: 'baˈɾõ.mi.tɾu' },
  { palavra: 'Basalto',               ipa: 'baˈzaw.tu' },
  { palavra: 'Bayreuth',              ipa: 'baɪˈʁɔʏt' },
  { palavra: 'Berço',                 ipa: 'ˈbeʁ.su' },
  { palavra: 'Bilhar',                ipa: 'biˈʎaʁ' },
  { palavra: 'Bloom, Leopold',        ipa: 'blum, ˈliː.ə.poʊld' },
  { palavra: 'Bobes',                 ipa: 'ˈbɔ.bis' },
  { palavra: 'Bombons de sorvete',    ipa: 'bõˈbõs d͡ʒi soʁˈve.t͡ʃi' },
  { palavra: 'Bosques',               ipa: 'ˈbɔs.kis' },
  { palavra: 'Botas',                 ipa: 'ˈbɔ.tɐs' },
  { palavra: 'Brumas',                ipa: 'ˈbɾu.mɐs' },
];

// ---------------------------------------------------------------------------
// SKETCHES — algumas palavras do inventario, em vez de aparecerem como texto
// vermelho, aparecem como um RABISCO 2D (line-art monospace) tambem vermelho.
// So as mais simples/desenhaveis. Chave = palavra normalizada (sem acento,
// minuscula). Cada item e um array de linhas; espaco = celula vazia.
// O grid.js procura por aqui antes de desenhar a palavra como texto.
// ---------------------------------------------------------------------------
window.INV_SKETCHES = {
  'aviao': [
    '   /\\   ',
    '__/  \\__',
    '\\______/',
    '   ||   ',
  ],
  'almofada': [
    ' ______ ',
    '/      \\',
    '\\______/',
  ],
  'botas': [
    ' __   __ ',
    '|  | |  |',
    '|  | |  |',
    '|  |_|  |__',
    '|       |  |',
    '|_______|__|',
  ],
  'baoba': [
    ' (((()))) ',
    '((((()))))',
    '   |||    ',
    '   |||    ',
    '  _|||_   ',
  ],
  'bosques': [
    ' (())  (()) ',
    '((())  (()))',
    '  ||    ||  ',
    ' _||_  _||_ ',
  ],
  'bandeira francesa': [
    ' ______ ',
    '|: :  :|',
    '|: :  :|',
    '|______|',
    '|       ',
    '|       ',
  ],
  'bilhar': [
    ' ________ ',
    '|o o  o o|',
    '|   o    |',
    '|o______o|',
  ],
  'balanca de banheiro': [
    ' ______ ',
    '|      |',
    '| (oo) |',
    '|______|',
  ],
  'berco': [
    '\\        /',
    ' \\______/ ',
    '  \\____/  ',
    '   ----   ',
  ],
  'bombons de sorvete': [
    ' __ ',
    '/oo\\',
    '\\  /',
    ' \\/ ',
  ],
  'barometro': [
    '  ____  ',
    ' / 9  \\ ',
    '| 6 () |',
    ' \\_3__/ ',
  ],
};

window.suitColor = function(suit, key) {
  const p = window.SUIT_PALETTE[suit] || window.SUIT_PALETTE.COPAS;
  return p[key || 'main'];
};

window.suitNorm = function(suit, idx) {
  return window.suitColor(suit, 'main')[idx] / 255;
};

window.DYN_INTENSITY = {
  ppp: 0.10, pp: 0.20, p: 0.32, mp: 0.48,
  mf: 0.62, f: 0.78, ff: 0.92, fff: 1.0,
};
