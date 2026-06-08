// Painel de capitulos do livro "Especes d'espaces" (Perec).
// Lista clicavel com botoes pra trocar o capitulo/movimento ao vivo.
//
// Comportamento:
//   - Ao carregar a pagina, busca GET /capitulos pra montar a lista
//   - Click num botao manda POST /capitulo {"id": "..."}
//   - SSE 'capitulo_change' (chamado por window.onCapituloChange) atualiza
//     o botao ativo + window.viz.attractor (consumido pelo grid 64x64)
//
// Carrega DEPOIS de state.js (precisa de window.viz).

(function() {
  let chapters = [];
  let currentId = '0';
  let panelEl = null;

  // Painel visual desativado - capitulo e escolhido pelo terminal.
  // Mantemos o fetch da lista e o SSE pra atualizar window.viz.attractor.
  function buildPanel() {
    // no-op: nada renderizado no browser
  }

  function updateActive(id) {
    currentId = id;
  }

  function applyChapter(meta) {
    if (!meta) return;
    updateActive(meta.id);
    window.viz.capituloId = meta.id;
    window.viz.capituloNome = meta.nome || '';
    window.viz.attractor = meta.attractor || 'neutro';
  }

  // Handler global usado pelo sketch.js ao receber SSE
  window.onCapituloChange = applyChapter;

  // Carrega a lista do servidor
  function loadList() {
    fetch('/capitulos').then(r => r.json()).then(data => {
      chapters = data.capitulos || [];
      currentId = data.atual || '0';
      buildPanel();
      // Aplica estado inicial em window.viz
      const meta = chapters.find(c => c.id === currentId);
      if (meta) applyChapter(meta);
    }).catch(err => console.warn('GET /capitulos falhou', err));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadList);
  } else {
    loadList();
  }
})();
