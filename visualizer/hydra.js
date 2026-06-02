// Hydra patch — fundo bem discreto, soh um leve grain reativo no naipe atual.
// Sem brilho saturado: a esfera p5 eh a estrela visual; aqui eh ambient noise.

function startHydra() {
  const canvas = document.getElementById('hydra-canvas');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  new Hydra({
    canvas,
    detectAudio: false,
    makeGlobal: true,
    autoLoop: true,
  });

  const rCh = () => window.suitNorm(window.viz.currentSuit, 0);
  const gCh = () => window.suitNorm(window.viz.currentSuit, 1);
  const bCh = () => window.suitNorm(window.viz.currentSuit, 2);
  const pulse = () => window.viz.beatPulse;

  // Grain ambient: noise lento + um leve mult de cor do naipe.
  // Sem colorama, sem pixelate dramatico — fica como "static" de monitor.
  noise(
    () => 6 + pulse() * 4,
    () => 0.04 + pulse() * 0.08,
  )
    .thresh(() => 0.62 - pulse() * 0.10, 0.04)
    .mult(
      solid(
        () => 0.20 + rCh() * 0.35 + pulse() * 0.10,
        () => 0.20 + gCh() * 0.35 + pulse() * 0.10,
        () => 0.20 + bCh() * 0.35 + pulse() * 0.10,
      )
    )
    .modulate(
      noise(1.2, 0.03),
      () => 0.02 + pulse() * 0.05,
    )
    .out();
}

window.addEventListener('load', () => {
  setTimeout(startHydra, 100);
});

window.addEventListener('resize', () => {
  const c = document.getElementById('hydra-canvas');
  c.width = window.innerWidth;
  c.height = window.innerHeight;
});
