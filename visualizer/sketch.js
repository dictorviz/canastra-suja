// Baralho Musical - SSE bridge.
// Recebe eventos do servidor e atualiza window.viz, que o grid.js consome.
// Nao desenha nada — o visualizer agora eh puramente o grid de palavras cruzadas.

(function() {
  let connectionStatus = 'conectando...';

  function updateStatus() {
    const s = document.getElementById('status');
    if (s) s.textContent = connectionStatus;
  }

  function connectSSE() {
    const ev = new EventSource('/events');
    ev.onopen = () => {
      connectionStatus = 'conectado';
      updateStatus();
    };
    ev.onerror = () => {
      connectionStatus = 'desconectado (retry...)';
      updateStatus();
    };
    ev.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        handleEvent(data);
      } catch (e) {
        console.warn('parse fail', e);
      }
    };
  }

  function handleEvent(e) {
    if (e.type === 'hello') return;
    if (e.type === 'compose_ready') {
      connectionStatus = `pronto — ${e.n_notes} notas`;
      updateStatus();
      if (e.capitulo) applyCapitulo(e.capitulo);
      return;
    }
    if (e.type === 'capitulo_change') {
      applyCapitulo({
        id: e.id, nome: e.nome, attractor: e.attractor,
      });
      return;
    }
    if (e.type === 'end') {
      connectionStatus = 'fim';
      updateStatus();
      return;
    }
    if (e.type === 'word_now') {
      onWordNow(e);
      return;
    }
    if (e.type === 'note' || e.type === 'rest') {
      onMusicalEvent(e);
    }
  }

  // Sync palavra-a-palavra: o SC dispara word_now no momento em que a
  // Routine de ~falaWords vai tocar cada palavra. Atualizamos lastSpoken
  // pra essa UNICA palavra e zeramos a idade — grid.js destaca por ate
  // 4s, mas a proxima palavra (e/ou silencio) chega bem antes disso.
  function onWordNow(e) {
    const w = (e.word || '').trim();
    if (!w) return;
    window.viz.lastSpoken = w;
    window.viz.spokenAge = 0;
    window.viz.spokenSource = e.source || 'echo';
  }

  function applyCapitulo(meta) {
    if (!meta) return;
    window.viz.capituloId = meta.id;
    window.viz.capituloNome = meta.nome || '';
    window.viz.attractor = meta.attractor || 'neutro';
    // Sincroniza com o painel (destaca botao ativo)
    if (typeof window.onCapituloChange === 'function') {
      window.onCapituloChange(meta);
    }
  }

  function onMusicalEvent(e) {
    if (e.cards && e.cards.length > 0) {
      window.viz.currentSuit = e.cards[0].suit;
    }

    const art = (e.articulacao || 'NORMAL');
    window.viz.articulation = art;
    window.viz.fermata = !!e.fermata;
    window.viz.accento = art.indexOf('ACENTO') >= 0;
    window.viz.staccato = art.indexOf('STACATTO') >= 0;
    window.viz.tenuto = art.indexOf('TENUTO') >= 0;

    const dyn = e.dinamica || 'mp';
    const intensity = window.DYN_INTENSITY[dyn] || 0.5;
    window.viz.intensity = intensity;
    window.viz.beatPulse = Math.min(1.2, intensity * (window.viz.accento ? 1.6 : 1.0));

    // NOTA: lastSpoken NAO eh mais setado aqui. Quem dirige eh o evento
    // 'word_now' (vindo via SC OSC -> a_visual_web.start_osc_listener
    // -> SSE), que chega no instante real em que cada palavra eh disparada
    // pela Routine de ~falaWords no SuperCollider.

    window.viz.noteCount++;
  }

  // Decai beatPulse e spokenAge em loop proprio (sem p5).
  let lastT = performance.now();
  function tick(now) {
    const dt = Math.min(0.05, (now - lastT) / 1000);
    lastT = now;
    window.viz.beatPulse = Math.max(0, window.viz.beatPulse - dt * 1.6);
    window.viz.spokenAge += dt;
    requestAnimationFrame(tick);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      connectSSE();
      requestAnimationFrame((now) => { lastT = now; tick(now); });
    });
  } else {
    connectSSE();
    requestAnimationFrame((now) => { lastT = now; tick(now); });
  }
})();
