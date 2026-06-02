// =====================================================================
// B_SYNTH.scd  -  CAMADA B (o mundo / a cartomante ao vivo)
//
// ADITIVO. NAO TOCA em a_synth.scd. Rode ESTE arquivo DEPOIS de
// a_synth.scd (Ctrl+A, Ctrl+Enter), com o servidor ja booted.
// Usa o namespace OSC /mundo/* (separado de /baralho/*), entao convive
// com a camada A sem colisao.
//
// O "baralho do mundo": uma biblioteca de HABITATS sonoros longos
// (paisagens de 10s a varios minutos). Cada carta fisica puxada pela
// cartomante faz o mundo ATRAVESSAR -- crossfade do habitat atual pro
// proximo (sorteado). Um lugar de cada vez. E o "habitar o espaco"
// concreto, contra a voz sintetica do Perec (camada A).
//
// Mensagens OSC:
//   /mundo/load    [chave, path_abs]               - carrega um WAV em buffer
//   /mundo/bed     [chave, fade, amp, pan, loop]   - crossfade pro novo habitat
//   /mundo/trigger [chave, amp, pan, rate]         - one-shot curto (pontual)
//   /mundo/stop    [fade]                          - encerra o habitat atual
//   /mundo/clear   []                              - libera todos os buffers
//
// TODO Fase 2: SynthDef \mundoGlitch + /mundo/glitch -- a corrupcao que
//   a carta fisica (B) causa na maquina (A): desafina, satura, congela.
// TODO Fase 5: octofonia. Hoje Pan2 (estereo). Pra 8 canais, trocar por
//   saida multicanal e rotear o pan pelo naipe.
// =====================================================================
(
Server.default.waitForBoot({

    ~mundoBuffers = Dictionary.new;
    ~mundoBed = nil;   // synth do habitat atual (pra crossfade)

    // HABITAT: textura longa. Fantasmagorica -- fundo atras do synth principal.
    // lpf: corte de agudos (distancia/veu). revWash: quantidade de cauda reverb.
    // Amplitude baixa por padrao: o protagonista e o synth da camada A.
    SynthDef(\mundoBed, { |bufnum=0, amp=0.22, pan=0, rate=1.0, fade=5.0,
                           loop=1, gate=1, lpf=2600, revWash=0.45, out=0|
        var sig, env, wet;
        env = EnvGen.kr(Env.asr(fade, 1, fade, \sin), gate, doneAction: 2);
        sig = PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum) * rate,
                         loop: loop, doneAction: 2);
        // Veu de distancia: tira agudos, faz soar longe/atras
        sig = LPF.ar(sig, lpf);
        // Lavagem de reverb embutida -- espaca o sample sem precisar dos buses da camada A
        wet = FreeVerb.ar(sig, mix: 1.0, room: 0.75, damp: 0.55);
        sig = (sig * (1.0 - revWash)) + (wet * revWash);
        Out.ar(out, Pan2.ar(sig * env * amp, pan.clip(-1, 1)));
    }).add;

    // ONE-SHOT: hit curto, toca uma vez e some. Uso pontual / Fase 2.
    SynthDef(\mundoSample, { |bufnum=0, amp=0.8, pan=0, rate=1.0, out=0|
        var sig, env, dur;
        dur = BufDur.kr(bufnum) / rate;
        env = EnvGen.kr(
            Env([0, 1, 1, 0], [0.01, (dur - 0.21).max(0.01), 0.2], curve: \sin),
            doneAction: 2);
        sig = PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum) * rate, doneAction: 0);
        Out.ar(out, Pan2.ar(sig * env * amp, pan.clip(-1, 1)));
    }).add;

    // /mundo/load [chave, path_abs] - Python manda no startup, um por WAV.
    OSCdef(\mundoLoad, { |msg|
        var key = (msg[1] ? "").asString.asSymbol;
        var path = (msg[2] ? "").asString;
        if((key != '') && (path.size > 0)) {
            Buffer.read(s, path, action: { |b| ~mundoBuffers[key] = b; });
        };
    }, "/mundo/load");

    // /mundo/bed [chave, fade, amp, pan, loop, lpf, revWash] - atravessa pro novo habitat.
    // amp/lpf/revWash controlam o quao fantasmagorico o habitat soa.
    OSCdef(\mundoBed, { |msg|
        var key     = (msg[1] ? "").asString.asSymbol;
        var fade    = (msg[2] ? 5.0).asFloat;
        var amp     = (msg[3] ? 0.22).asFloat;
        var pan     = (msg[4] ? 0.0).asFloat;
        var loop    = (msg[5] ? 1).asInteger;
        var lpf     = (msg[6] ? 2600).asFloat;
        var revWash = (msg[7] ? 0.45).asFloat;
        var buf     = ~mundoBuffers[key];
        if(buf.notNil) {
            // libera o habitat anterior: gate=0 dispara o fade-out (rel=fade)
            if(~mundoBed.notNil) { ~mundoBed.set(\gate, 0); };
            ~mundoBed = Synth(\mundoBed, [
                \bufnum, buf, \amp, amp, \pan, pan, \fade, fade, \loop, loop,
                \lpf, lpf, \revWash, revWash,
            ]);
        } {
            ("[MUNDO] habitat nao carregado: " ++ key).postln;
        };
    }, "/mundo/bed");

    // /mundo/trigger [chave, amp, pan, rate] - one-shot pontual.
    OSCdef(\mundoTrigger, { |msg|
        var key  = (msg[1] ? "").asString.asSymbol;
        var amp  = (msg[2] ? 0.8).asFloat;
        var pan  = (msg[3] ? 0.0).asFloat;
        var rate = (msg[4] ? 1.0).asFloat;
        var buf  = ~mundoBuffers[key];
        if(buf.notNil) {
            Synth(\mundoSample, [\bufnum, buf, \amp, amp, \pan, pan, \rate, rate]);
        } {
            ("[MUNDO] sample nao carregado: " ++ key).postln;
        };
    }, "/mundo/trigger");

    // /mundo/stop [fade] - encerra o habitat atual (fim da peca / silencio).
    OSCdef(\mundoStop, { |msg|
        if(~mundoBed.notNil) { ~mundoBed.set(\gate, 0); ~mundoBed = nil; };
    }, "/mundo/stop");

    // /mundo/clear - libera buffers (troca de projeto / fim).
    OSCdef(\mundoClear, { |msg|
        if(~mundoBed.notNil) { ~mundoBed.set(\gate, 0); ~mundoBed = nil; };
        ~mundoBuffers.do { |b| if(b.notNil) { b.free } };
        ~mundoBuffers = Dictionary.new;
        "[MUNDO] buffers limpos.".postln;
    }, "/mundo/clear");

    "[MUNDO] Pronto. Camada B (habitats) escutando /mundo/* na porta 57120.".postln;
});
)
