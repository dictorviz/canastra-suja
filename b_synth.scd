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
//   /mundo/voz_load[palavra, path]                 - palavra do Perec (shards)
//   /mundo/glitch  [tipo, level, kick]             - a colisao (corrupcao paralela)
//   /mundo/glitch_reset []                         - nova consulta
//
// FASE 2 (FEITO): corrupcao PARALELA por naipe -- detune/freeze/shards/saturate
//   (ver bloco no fim). Sombra ADITIVA que soa como A se desfazendo; nao le o
//   sinal de A (bus 0 intocado). Sem este arquivo carregado, A soa pristina.
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
            ~mundoCurrentBuf = buf;  // Fase 2: freeze/saturate mordem o habitat atual
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

    // =================================================================
    // FASE 2 - A COLISAO: corrupcao PARALELA (a sombra de A se desfazendo).
    //
    // NAO le o sinal da camada A (bus 0 intocado, a_synth.scd intacto). Sao
    // vozes ADITIVAS que SOAM como a maquina corrompendo. Cada NAIPE e um
    // glitch; a intensidade vem do nivel global de corrupcao (0..1, acumulado
    // no Python, sobe a cada carta) e do "kick" (forca do valor da carta).
    //   Copas=detune   Ouros=freeze
    //   Espadas=shards(voz do Perec)   Paus=saturate
    // =================================================================

    ~mundoCurrentBuf = nil;            // habitat atual (freeze/saturate mordem nele)
    ~vozBuffers = Dictionary.new;      // palavras do Perec (a espada corta estas)

    // /mundo/voz_load [palavra, path] - Python manda no preload (do tts_cache).
    OSCdef(\mundoVozLoad, { |msg|
        var key = (msg[1] ? "").asString.asSymbol;
        var path = (msg[2] ? "").asString;
        if((key != '') && (path.size > 0)) {
            Buffer.read(s, path, action: { |b| ~vozBuffers[key] = b; });
        };
    }, "/mundo/voz_load");

    // COPAS -> DESAFINA: cluster de parciais que escorrega pra baixo.
    SynthDef(\glitchDetune, { |level=0.3, kick=0.5, amp=0.3, pan=0, out=0|
        var freq, n=5, sig, env, dur, spread, sink;
        dur = 2.0 + (level * 4.0);                       // mais corrompido, arrasta mais
        spread = 0.5 + (level * 6.0);                    // detune (Hz) cresce com o nivel
        sink = Line.kr(1.0, 1.0 - (0.04 + (level * 0.12)), dur);  // a altura afunda
        freq = Rand(48.0, 72.0).midicps;                 // uma "nota" da profecia
        sig = Mix.fill(n, { |i|
            SinOsc.ar((freq * sink) + ((i - 2) * spread), 0, 1/n)
        });
        env = EnvGen.kr(Env.perc(0.4, dur, 1, \sin), doneAction: 2);
        sig = sig * env * amp * (level + kick).clip(0, 1.2);
        Out.ar(out, Pan2.ar(sig, pan.clip(-1, 1)));
    }).add;

    // OUROS -> CONGELA: uma janelinha do habitat trava e se repete.
    SynthDef(\glitchFreeze, { |bufnum=0, level=0.3, kick=0.5, amp=0.35, pan=0, out=0|
        var sig, env, dur, winFrames, startFr, phasor;
        dur = 1.5 + (level * 3.5);
        winFrames = BufFrames.kr(bufnum) * (0.02 + (0.06 * (1 - level)));  // encolhe = petrifica
        startFr = Rand(0.0, 1.0) * (BufFrames.kr(bufnum) - winFrames);
        phasor = Phasor.ar(0, BufRateScale.kr(bufnum), startFr, startFr + winFrames);
        sig = BufRd.ar(1, bufnum, phasor, loop: 1);
        sig = sig * LFPulse.ar(6 + (level * 30), 0, 0.6);  // estria mecanica
        env = EnvGen.kr(Env.linen(0.05, dur, 0.3, 1, \sin), doneAction: 2);
        sig = sig * env * amp * (level + kick).clip(0, 1.2);
        Out.ar(out, Pan2.ar(sig, pan.clip(-1, 1)));
    }).add;

    // ESPADAS -> FRAGMENTA A VOZ: granula uma palavra do Perec em cacos.
    SynthDef(\glitchShards, { |bufnum=0, level=0.3, kick=0.5, amp=0.6, out=0|
        var sig, env, dur, dens, trig, cpos, grainDur, rate;
        dur = 1.0 + (level * 3.0);
        dens = 8 + (level * 30);                          // cacos por segundo
        trig = Impulse.ar(dens);
        cpos = TRand.ar(0.02, (BufDur.kr(bufnum) - 0.02).max(0.03), trig);  // ponto da palavra
        grainDur = (1 / dens) * (1.0 + level);
        rate = TRand.ar(0.6, 1.5, trig);                  // cacos desafinados
        sig = TGrains.ar(2, trig, bufnum, rate, cpos, grainDur,
                         TRand.ar(-0.6, 0.6, trig), 1, 2);  // pan espalhado
        env = EnvGen.kr(Env.linen(0.02, dur, 0.25, 1, \sin), doneAction: 2);
        sig = sig * env * amp * (level + kick).clip(0, 1.3);
        Out.ar(out, sig);                                 // TGrains ja sai em 2 canais
    }).add;

    // PAUS -> SATURA: o habitat atual queima (drive + fold).
    SynthDef(\glitchSaturate, { |bufnum=0, level=0.3, kick=0.5, amp=0.3, pan=0, out=0|
        var sig, env, dur, drive, startFr;
        dur = 1.5 + (level * 3.0);
        drive = 1.0 + (level * 18.0) + (kick * 6.0);      // queima mais com o nivel
        startFr = Rand(0.0, 1.0) * BufFrames.kr(bufnum);
        sig = PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum), startPos: startFr, loop: 1);
        sig = (sig * drive).tanh.fold2(0.9);              // satura e dobra
        sig = HPF.ar(sig, 200 + (level * 600));           // brilho que cresce
        env = EnvGen.kr(Env.perc(0.05, dur, 1, \sin), doneAction: 2);
        sig = sig * env * amp * (0.5 + level);
        Out.ar(out, Pan2.ar(sig, pan.clip(-1, 1)));
    }).add;

    // /mundo/glitch [tipo, level, kick] - a corrupcao da carta (naipe = tipo).
    OSCdef(\mundoGlitch, { |msg|
        var tipo  = (msg[1] ? "").asString;
        var level = (msg[2] ? 0.3).asFloat.clip(0, 1);
        var kick  = (msg[3] ? 0.5).asFloat.clip(0, 1);
        var pan   = 1.0.rand2 * 0.5;
        case
        { tipo == "detune" } {
            Synth(\glitchDetune, [\level, level, \kick, kick, \pan, pan],
                  addAction: \addToTail);
        }
        { tipo == "freeze" } {
            if(~mundoCurrentBuf.notNil) {
                Synth(\glitchFreeze, [\bufnum, ~mundoCurrentBuf, \level, level,
                      \kick, kick, \pan, pan], addAction: \addToTail);
            };
        }
        { tipo == "shards" } {
            var keys = ~vozBuffers.keys.asArray;
            if(keys.size > 0) {
                Synth(\glitchShards, [\bufnum, ~vozBuffers[keys.choose],
                      \level, level, \kick, kick], addAction: \addToTail);
            };
        }
        { tipo == "saturate" } {
            if(~mundoCurrentBuf.notNil) {
                Synth(\glitchSaturate, [\bufnum, ~mundoCurrentBuf, \level, level,
                      \kick, kick, \pan, pan], addAction: \addToTail);
            };
        };
    }, "/mundo/glitch");

    // /mundo/glitch_reset - nova consulta (a corrupcao mora no Python; aqui so loga).
    OSCdef(\mundoGlitchReset, { |msg|
        "[MUNDO] corrupcao zerada (nova consulta).".postln;
    }, "/mundo/glitch_reset");

    "[MUNDO] Pronto. Camada B (habitats + glitch) escutando /mundo/* na porta 57120.".postln;
});
)
