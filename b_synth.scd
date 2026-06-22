// =====================================================================
// B_SYNTH.scd  -  CAMADA B (o mundo / a cartomante ao vivo)
//
// ---------------------------------------------------------------------
// LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
// ---------------------------------------------------------------------
// ATENCAO: este arquivo NAO e Python! E "SuperCollider", uma linguagem
// feita pra FAZER SOM. Enquanto os arquivos .py sao o "cerebro" (decidem
// o que tocar), os .scd sao os "alto-falantes" (produzem o barulho de
// verdade). Voce roda este arquivo DENTRO do programa SuperCollider
// (selecionar tudo e apertar Ctrl+Enter), nao no terminal.
//
// Tres palavrinhas que se repetem aqui e voce so precisa reconhecer:
//   * SynthDef(\nome, { ... })  = a RECEITA de um som (ex: como soa o
//       habitat, como soa a distorcao). E so a planta; nao toca sozinha.
//   * OSCdef(\nome, { ... }, "/mundo/x") = um "ouvido": fica esperando a
//       mensagem OSC "/mundo/x" que o Python manda, e quando ela chega,
//       executa a receita. E a ponte Python -> som.
//   * Os simbolos: ~algumaCoisa = uma "caixa com nome" global (variavel);
//       \algumaCoisa (com barra) = so um nome/etiqueta (um rotulo de texto).
//   * // assim e um comentario (o computador ignora), igual ao # do Python.
//
// Resumo: o Python grita "/mundo/glitch" pela rede; o "ouvido" OSCdef aqui
// embaixo escuta e dispara a receita SynthDef que faz a sujeira soar. Os
// comentarios de cada bloco abaixo dizem, em portugues, o que cada som faz.
// (Os detalhes de SINTESE -- envelope, buffer, filtro -- nao sao explicados
//  linha a linha de proposito: e um mundo a parte; aqui fica a ideia geral.)
// ---------------------------------------------------------------------
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
//   /mundo/control [id, naipe, x,y,size,spin,tilt,luma] - CHOPPER: pose ao vivo (continuo)
//   /mundo/control_off [id]                        - marcador sumiu -> cauda (solta a voz)
//
// FASE 2 (FEITO): corrupcao PARALELA por naipe -- detune/freeze/shards/saturate
//   (ver bloco no fim). Sombra ADITIVA que soa como A se desfazendo; nao le o
//   sinal de A (bus 0 intocado). Sem este arquivo carregado, A soa pristina.
// FASE 3 (FEITO): o THEREMIN -- voz CONTINUA (\teremin) controlada pela pose do
//   marcador. DUAS camadas: a COLAGEM (graos que picam o habitat -- "os audios")
//   + o SYNTH DIGITAL bugado (modem/dial-up: tons que gaguejam, chiado, bleep,
//   ghost, bitcrush). Um macro 'clareza' faz o som BUGAR/DESBUGAR sozinho (~2-5s
//   por fase): sobe -> abaixa o synth e o audio aparece; cai -> buga tudo. Cauda
//   longa na release (delay+reverb). Mapa da pose: x/y/size/spin/tilt/luma.
// OCTOFONIA (FEITO): ~debug/~nChans no topo + ~spat/~spread. debug=true -> estereo
//   (Pan2, identico ao de antes); debug=false -> 8 canais (PanAz num anel). O
//   numero de canais e bootado pelo a_synth.scd; rode-o ANTES deste.
// =====================================================================
(
// DEBUG / OCTOFONIA (pedidos 7 e 2): mantenha IGUAL ao a_synth.scd e ao DEBUG
// do b_config.py. Aqui o ~debug so controla o quanto se fala na tela; o numero
// de canais (~nChans) e HERDADO do servidor que o a_synth.scd bootou -- assim
// nunca desencontra do hardware. (Rode a_synth.scd ANTES deste.)
~debug = true;
Server.default.waitForBoot({

    // herda 2 (estereo/laptop) ou 8 (octofonia/conservatorio) do servidor ja
    // bootado pelo a_synth.scd. Se rodar este sozinho, cai no default do server.
    ~nChans = s.options.numOutputBusChannels;

    // POSICIONAR uma fonte mono num azimute (azim 0..1 = volta no anel). Em
    // estereo vira um Pan2 normal (identico ao de antes); em octofonia vira
    // PanAz pelas 8 caixas -- e o que faz o theremin ANDAR entre os Genelecs
    // conforme a carta se move na imagem (x -> azimute).
    ~spat = { |sig, azim=0.5|
        if(~nChans == 2,
            { Pan2.ar(sig, (azim * 2 - 1).clip(-1, 1)) },
            { PanAz.ar(~nChans, sig, (azim * 2).wrap(0, 2)) });
    };
    // ESPALHAR um sinal estereo/multi pelas caixas (difuso, sem posicao fixa).
    ~spread = { |sig|
        if(~nChans == 2, { sig }, { SplayAz.ar(~nChans, sig.asArray) });
    };

    ~mundoBuffers = Dictionary.new;
    ~mundoBed = nil;   // synth do habitat atual (pra crossfade)

    // HABITAT: textura longa. Fantasmagorica -- fundo atras do synth principal.
    // lpf: corte de agudos (distancia/veu). revWash: quantidade de cauda reverb.
    // Amplitude baixa por padrao: o protagonista e o synth da camada A.
    // PICOTADA (pedido): em vez de tocar o WAV liso (PlayBuf), a cama agora e uma
    // NUVEM DE GRAOS (TGrains) que VARRE o habitat devagar e, de vez em quando,
    // PULA pra outro trecho sorteado -- recola o lugar. Continua sendo cama
    // (overlap alto = textura continua), mas estilhacada. chop = o quanto pica.
    SynthDef(\mundoBed, { |bufnum=0, amp=0.22, pan=0, rate=1.0, fade=5.0,
                           loop=1, gate=1, lpf=2600, revWash=0.45, chop=0.7, out=0|
        var sig, env, wet, bdur, scan, center, jumpGate, pos;
        var dens, gtrig, gpos, grate, gdur, spread;
        env = EnvGen.kr(Env.asr(fade, 1, fade, \sin), gate, doneAction: 2);
        bdur = BufDur.kr(bufnum);
        // A CABECA varre o habitat devagar, em loop (a "cama" anda pelo lugar).
        scan = LFSaw.kr((1 / bdur) * rate, 1).range(0, bdur);
        // COLAGEM: de vez em quando a cabeca PULA pra um trecho sorteado (recola),
        // em vez de so varrer em ordem. chop decide o quao often e o quanto.
        center   = TRand.ar(0.02, (bdur - 0.02).max(0.05), Dust.ar(0.25 + chop));
        jumpGate = Lag.kr((LFDNoise0.kr(0.2 + chop).range(0, 1) > (1 - (chop * 0.45))), 0.12);
        pos      = (scan * (1 - jumpGate)) + (center * jumpGate);
        // NUVEM DE GRAOS picando essa posicao. gdur > intervalo => graos sobrepostos
        // => textura continua mesmo picotada (cama estilhacada, nao staccato).
        dens   = 12 + (chop * 30);
        gtrig  = Impulse.ar(dens);
        spread = 0.02 + (chop * 0.22);
        gpos   = (pos + TRand.ar(spread.neg, spread, gtrig)).clip(0.02, (bdur - 0.02).max(0.05));
        grate  = 1.0 + (TRand.ar(-0.04, 0.04, gtrig) * chop);   // leve desafinacao por grao
        gdur   = (1 / dens) * (2.0 + chop);
        sig = TGrains.ar(2, gtrig, bufnum, grate, gpos, gdur, TRand.ar(-0.5, 0.5, gtrig), 1, 2);
        sig = sig.sum * 0.5;
        // Veu de distancia: tira agudos, faz soar longe/atras
        sig = LPF.ar(sig, lpf);
        // Lavagem de reverb embutida -- espaca o sample sem precisar dos buses da camada A
        wet = FreeVerb.ar(sig, mix: 1.0, room: 0.75, damp: 0.55);
        sig = (sig * (1.0 - revWash)) + (wet * revWash);
        Out.ar(out, ~spat.(sig * env * amp, (pan.clip(-1, 1) + 1) * 0.5));
    }).add;

    // ONE-SHOT: hit curto, toca uma vez e some. Uso pontual / Fase 2.
    SynthDef(\mundoSample, { |bufnum=0, amp=0.8, pan=0, rate=1.0, out=0|
        var sig, env, dur;
        dur = BufDur.kr(bufnum) / rate;
        env = EnvGen.kr(
            Env([0, 1, 1, 0], [0.01, (dur - 0.21).max(0.01), 0.2], curve: \sin),
            doneAction: 2);
        sig = PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum) * rate, doneAction: 0);
        Out.ar(out, ~spat.(sig * env * amp, (pan.clip(-1, 1) + 1) * 0.5));
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
            // CHOPS/COLAGEM (pedido 2): re-aponta as vozes vivas do teremim pro NOVO
            // habitat. Sem isto, uma voz que abriu antes da 1a carta ficava presa no
            // buffer de silencio (~teremSilent) e a colagem picava o NADA -- por isso
            // "os chops nao rolavam nos audios". Agora todo crossfade arrasta as vozes
            // pro buffer que esta tocando, e os graos picam o som de verdade.
            if(~teremVoices.notNil) {
                ~teremVoices.do { |v| if(v.notNil) { v.set(\bufnum, buf) } };
            };
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
        // solta tambem qualquer voz de theremin ainda aberta.
        if(~teremVoices.notNil) {
            ~teremVoices.do { |v| if(v.notNil) { v.set(\gate, 0) } };
            ~teremVoices = Dictionary.new;
        };
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
    //   Espadas=shards(habitat atual)   Paus=saturate
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
        Out.ar(out, ~spat.(sig, (pan.clip(-1, 1) + 1) * 0.5));
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
        Out.ar(out, ~spat.(sig, (pan.clip(-1, 1) + 1) * 0.5));
    }).add;

    // ESPADAS -> FRAGMENTA O HABITAT: granula o habitat ATUAL em cacos. A voz do
    // Perec saiu (arquivada); a espada agora estilhaca o proprio mundo que toca.
    // Escolhe uma REGIAO do habitat longo e os graos vagam numa janela que se
    // abre com o nivel -- comeca coeso, vira poeira conforme corrompe.
    SynthDef(\glitchShards, { |bufnum=0, level=0.3, kick=0.5, amp=0.35, out=0|
        var sig, env, dur, dens, trig, cpos, grainDur, rate, center, win, bdur;
        dur = 1.0 + (level * 3.0);
        bdur = BufDur.kr(bufnum);
        dens = 8 + (level * 34);                          // cacos por segundo
        trig = Impulse.ar(dens);
        center = Rand(0.05, 0.95) * bdur;                 // a regiao estilhacada
        win = 0.05 + (level * 0.5);                       // janela (s) abre com o nivel
        cpos = (center + TRand.ar(win.neg, win, trig)).clip(0.02, (bdur - 0.02).max(0.03));
        grainDur = (1 / dens) * (1.0 + level);
        rate = TRand.ar(0.6, 1.5, trig);                  // cacos desafinados
        sig = TGrains.ar(2, trig, bufnum, rate, cpos, grainDur,
                         TRand.ar(-0.7, 0.7, trig), 1, 2);  // pan espalhado
        env = EnvGen.kr(Env.linen(0.02, dur, 0.25, 1, \sin), doneAction: 2);
        sig = sig * env * amp * (level + kick).clip(0, 1.3);
        Out.ar(out, ~spread.(sig));                       // TGrains sai em 2 -> espalha no anel
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
        Out.ar(out, ~spat.(sig, (pan.clip(-1, 1) + 1) * 0.5));
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
            // Espadas estilhaca o HABITAT ATUAL (a voz do Perec foi arquivada).
            if(~mundoCurrentBuf.notNil) {
                Synth(\glitchShards, [\bufnum, ~mundoCurrentBuf, \level, level,
                      \kick, kick], addAction: \addToTail);
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

    // =================================================================
    // FASE 3 - O THEREMIN: voz CONTINUA controlada pela POSE do marcador.
    //
    // Diferenca pro glitch acima: aquele e DISCRETO (um soco por carta, some
    // sozinho). Este e CONTINUO -- enquanto o ArUco enxerga o marcador, o
    // b_aruco manda /mundo/control [id, naipe, x,y,size,spin,tilt] varias vezes
    // por segundo, e esta voz SEGUE a pose ao vivo (a camera vira instrumento,
    // tipo theremin). Quando o marcador SOME, /mundo/control_off solta o gate e
    // a voz cai numa cauda longa de delay+reverb -- nao corta de vez.
    //
    // O MOTOR tem DUAS camadas que andam juntas:
    //   (a) A COLAGEM (pedido 2): um CHOPPER granular ao vivo (TGrains) do habitat
    //       atual -- a pose pica e recola o mundo em tempo real. Os graos picam o
    //       SOM DE VERDADE (o bug do buffer preso no silencio foi consertado no
    //       /mundo/bed, que agora arrasta a voz pro habitat que esta tocando).
    //   (b) O DIGITAL BUGADO (pedido 1): no lugar do antigo "radio" de ruido branco
    //       (aquele som de VASSOURA), agora corre uma camada de DADOS dos anos 2000
    //       -- modem/fax/internet discada: um par de tons tipo DTMF que GAGUEJA num
    //       clock (FSK, o "warble" do handshake), um chiado de dados PULSADO (pacote
    //       a pacote, nao continuo) e BITCRUSH (reducao de taxa de amostra + de bits)
    //       que da a cor de "coisa digital pifando". Nada de vassoura.
    //
    // Mapeamento da pose (a carta TOCA o sample E disca os dados):
    //   x    -> SCRUB (qual fragmento do mundo) + azimute   size -> VELOCIDADE dos dados + densidade
    //   y    -> ALTURA (pitch dos graos E dos tons de modem) spin -> detune + ESMAGA bits
    //   tilt -> FREEZE/stutter (trava o caco e o lo-fi)      luma -> COR do filtro + taxa do crush
    //   naipe (flavor) -> tempera o caracter dos graos
    // =================================================================

    ~teremVoices = Dictionary.new;                 // id do marcador -> Synth vivo
    ~teremSilent = Buffer.alloc(s, s.sampleRate, 1);  // 1s de silencio (fallback
    // pra quando ainda nao ha habitat: a colagem fica muda e soa so o modem/digital).
    ~teremFlavorMap = Dictionary["C" -> 0, "O" -> 1, "E" -> 2, "P" -> 3];
    ~teremFlavor = { |suit| ~teremFlavorMap[suit.asString.toUpper] ? 4 };

    SynthDef(\teremin, { |bufnum=0, gate=1, amp=0.32,
                         x=0.5, y=0.5, size=0.3, spin=0.0, tilt=0.0, luma=0.5,
                         flavor=0, out=0|
        var env, lx, ly, lsize, lspin, ltilt, lluma;
        var bdur, scrub, win, cpos, dens, trig, grainDur, rate, chop, frozen;
        var base, clk, tick, hop, warp, toneA, toneB, dial, hiss, gliss, screech, modeSel, modem;
        var bleep, ghost, clareza, clarTrig;
        var crushRate, crushBits, levels, cf, sig, wet, fb;

        // suaviza os controles (o .set chega em saltos do Python; .lag derrete o gesto).
        lx    = Lag.kr(x, 0.12);    ly    = Lag.kr(y, 0.14);    lsize = Lag.kr(size, 0.20);
        lspin = Lag.kr(spin, 0.15); ltilt = Lag.kr(tilt, 0.18); lluma = Lag.kr(luma, 0.20);

        // envelope GATED: abre suave, sustenta enquanto gate=1; ao soltar (gate=0)
        // cai numa cauda longa (~4.5s) que o delay/reverb embaixo preenche.
        env = EnvGen.kr(Env.asr(0.4, 1.0, 4.5, \sin), gate, doneAction: 2);

        bdur = BufDur.kr(bufnum);

        // ---- FREEZE/STUTTER (tilt) ----
        // de frente (tilt~0) os graos VAGAM (recolagem viva) e o digital corre liso;
        // tombando a carta a janela FECHA, a posicao TRAVA e o crush fica mais lo-fi.
        frozen = ltilt.lincurve(0, 1, 0, 1, 4);   // tomba pouco ainda solta; no fim trava

        // ---- CLAREZA (pedidos 2 e 3): a respiracao "buga / desbuga" ----
        // Um macro LENTO e ALEATORIO entre 1 (audio limpo: da pra entender o que e)
        // e 0 (tudo bugado). Cada fase dura ~2..5s (NADA dura muito): Dust sorteia
        // QUANDO vira, Dwhite sorteia o ALVO, Lag derrete a transicao (1.4s). Tombar
        // a carta (frozen) puxa pro lado bugado. So este sinal ja faz a peca ir e
        // voltar entre "reconhecivel" e "corrompido" SOZINHA, sem depender do gesto.
        // (Pra desbugar mais vezes, suba o 0.22; pra fases mais longas, desca.)
        clarTrig = Dust.kr(0.22 + (lsize * 0.25));
        clareza  = Lag.kr(Demand.kr(clarTrig, 0, Dwhite(0.0, 1.0, inf)), 1.4);
        clareza  = (clareza * (1 - (frozen * 0.6))).clip(0, 1);

        // =============================================================
        // (a) A COLAGEM: chop granular ao vivo do HABITAT (pedido 2)
        // =============================================================
        dens = 8 + (lsize * 55) + (flavor * 4);
        trig = Impulse.ar(dens);
        grainDur = (1 / dens) * (1.0 + (frozen * 3) + (lsize * 0.5));  // tilt borra o grao
        // x escolhe ONDE no habitat a cabeca pousa: andar a carta varre o sample.
        scrub = lx * (bdur - 0.05);
        win   = (0.015 + (lsize * 0.35)) * (1 - frozen);   // janela de recolagem; fecha ao congelar
        cpos  = (scrub + TRand.ar(win.neg, win, trig)).clip(0.02, (bdur - 0.05).max(0.05));
        // y -> pitch dos graos ; spin -> detune por grao
        rate = ly.linexp(0, 1, 0.5, 2.0) * (1.0 + (lspin * 0.3));
        rate = rate * (1.0 + TRand.ar(lspin.abs.neg * 0.06, lspin.abs * 0.06, trig));
        chop = TGrains.ar(2, trig, bufnum, rate, cpos, grainDur,
                          TRand.ar(-0.6, 0.6, trig), 1, 2);
        chop = chop.sum * 0.5;

        // =============================================================
        // (b) O DIGITAL BUGADO: dados dos anos 2000 -- agora VIVO SOZINHO.
        //   Antes: clock FIXO + intervalo FIXO (base, base*1.5) => um arpejo que
        //   ia pra sempre, e so a mao trazia variacao. Agora a variedade mora
        //   DENTRO do som: mesmo com a carta PARADA, o modem gagueja em tempo
        //   irregular, PULA de altura, PERDE pacote e TROCA de modo sozinho. A
        //   pose ainda rege (size=velocidade, y=altura, spin=leque dos saltos),
        //   mas nao e mais a unica fonte de vida.
        // =============================================================
        base = ly.linexp(0, 1, 240, 2200);                 // y -> altura dos tons de dados
        // CLOCK IRREGULAR: a velocidade dos dados (size) ainda manda, mas vagueia
        // sozinha -- LFDNoise0 tem passo de tempo ALEATORIO, entao nunca metronomico.
        clk  = (6 + (lsize * 40)) * LFDNoise0.kr(0.4).exprange(0.6, 1.8);
        tick = Impulse.ar(clk);
        // PITCH QUE PULA: a cada tick sorteia uma transposicao nova (Dxrand = nao
        // repete a ultima). No lugar do intervalo fixo, uma sequencia imprevisivel
        // tipo discagem. spin estica o leque dos saltos (de discreto a esganicado).
        hop  = Demand.ar(tick, 0, Dxrand([1, 1.5, 2, 0.5, 0.75, 1.25, 1.333, 3, 4], inf));
        hop  = hop * (1.0 + (lspin.abs * TRand.ar(0.0, 1.5, tick)));
        warp = SinOsc.kr(clk * 0.5).range(0.99, 1.01);     // micro-wobble do carrier
        toneA = SinOsc.ar(base * hop * warp);
        toneB = SinOsc.ar(base * hop * Demand.ar(tick, 0, Dxrand([1.5, 2, 0.667, 1.333, 1], inf)));
        dial  = (toneA + toneB) * 0.5;
        // chiado de DADOS em rajada desigual (pacotes), nao pulso continuo:
        hiss  = BPF.ar(WhiteNoise.ar(1.0), (base * hop).clip(220, 6000) * 2, 0.1) * 5;
        hiss  = hiss * Decay2.ar(tick, 0.003, 0.04 + (lsize * 0.05));
        // GLISSANDO de discagem: varredura de portamento (aquele "subir" do dial-up).
        gliss = SinOsc.ar(base * LFDNoise1.kr(0.3 + (lsize * 3)).exprange(0.5, 4.0)) * 0.6;
        // SCREECH de handshake: o grito do modem conectando (par batendo rapido).
        screech = (SinOsc.ar(base * 2 * LFPulse.kr(clk * 2).range(1, 1.5))
                   + SinOsc.ar(base * 3 * hop)) * 0.4;
        // BLEEP: bipes esparsos (tipo morse) -- deixa BURACOS de silencio entre os
        // tons. E o "espacado" do pedido 1: da tempo de ouvir o audio por baixo.
        bleep = SinOsc.ar(base * 2 * hop) * LFPulse.ar((clk * 0.4).clip(1, 12), 0, 0.18) * 0.5;
        // GHOST: quase silencio, so estalos esparsos (Dust2) -- o modo que RESPIRA,
        // pra peca nao ser um muro de dados o tempo todo (pedido 1: mais espacado).
        ghost = Dust2.ar(2 + (lsize * 7)) * 0.7;
        // TROCA DE REGIME mais LENTA (pedido 1: TEMPO pra ouvir cada sonoridade).
        // Antes virava a cada ~0.6..3s; agora a cada ~2..6s -- cada bug "mora" mais.
        // E agora sao 6 regimes (mais VARIADO), incluindo o bleep e o ghost.
        // (Mais variedade ainda? acrescente texturas na lista do Select abaixo.)
        modeSel = Demand.kr(Dust.kr(0.15 + (lsize * 0.5)), 0, Diwhite(0, 5, inf));
        modem = Select.ar(modeSel, [dial * 0.7, hiss * 0.5, gliss, screech, bleep, ghost]);
        // DROPOUT de "conexao caindo": muta tudo em lacunas curtas e desiguais.
        modem = modem * Lag.kr(LFDNoise0.kr((clk * 0.3).clip(0.5, 25)) > -0.45, 0.003);

        // ---- mistura colagem (o AUDIO) + digital (o SYNTH bugado) ----
        // pedido 2: o synth digital entra MAIS BAIXO que antes (era 0.35+.., agora
        // 0.18+..) pra nao cobrir os audios. pedido 3: a 'clareza' ainda ABAIXA o
        // synth e LEVANTA o audio quando sobe -> da pra entender o som; quando ela
        // cai, o synth volta e buga tudo de novo. (Pra ouvir AINDA mais os audios,
        // desca o 0.18; pra synth mais presente, suba.)
        sig = (chop  * (0.7  + (lsize * 0.3))  * (0.55 + (clareza * 0.45)))
            + (modem * (0.18 + (lsize * 0.22)) * (1.0  - (clareza * 0.85)));
        sig = sig.tanh;   // mantem em [-1,1] pro bitcrush abaixo fazer sentido

        // ---- BITCRUSH (o "bugado": reduz taxa de amostra E profundidade de bits) ----
        // luma abre o brilho/taxa ; tilt (frozen) puxa pra mais lo-fi/stutter.
        crushRate = lluma.linexp(0, 1, 1800, 16000) * (1 - (frozen * 0.7));
        crushRate = crushRate * (0.25 + (clareza * 0.75));  // clareza -> taxa cheia (limpa o crush)
        sig = Latch.ar(sig, Impulse.ar(crushRate));         // sample & hold = reduz taxa
        crushBits = lspin.abs.linlin(0, 1, 12, 4);          // spin -> esmaga bits (12 -> 4)
        crushBits = (crushBits + (clareza * 4)).clip(3, 16);  // clareza -> mais bits (mais limpo)
        levels = 2 ** crushBits;
        sig = (sig * levels).round / levels;                // reduz profundidade de bits

        // ---- COR (luma -> brilho do filtro) ----
        cf = lluma.linexp(0, 1, 500, 8000) * (0.6 + (clareza * 0.7));  // clareza abre o veu
        sig = (BPF.ar(sig, cf.clip(200, 9000), 0.6) * 1.5) + (sig * 0.5);
        sig = sig.tanh;

        // intensidade global pelo size (dinamica) + seguranca.
        sig = (sig * amp * (0.3 + (lsize * 0.9)) * env).tanh;

        // ---- CAUDA: delay com feedback + reverb (ecoam na release; pedidos 3/5) ----
        fb  = LocalIn.ar(1) * (0.4 + (frozen * 0.2));
        wet = DelayC.ar(sig + fb, 0.8, ly.linlin(0, 1, 0.12, 0.6));
        LocalOut.ar(wet);
        wet = FreeVerb.ar(sig + (wet * 0.5), mix: 0.55, room: 0.9, damp: 0.4);
        sig = ((sig + wet) * 0.5).tanh;             // segura o nivel (master pega o resto)

        // posiciona pela horizontal: a carta "anda" entre as caixas (x -> azimute).
        Out.ar(out, ~spat.(sig, lx));
    }).add;

    // /mundo/control [id, naipe, x, y, size, spin, tilt] - a pose ao vivo.
    OSCdef(\mundoControl, { |msg|
        var id    = (msg[1] ? 0).asInteger;
        var suit  = (msg[2] ? "?").asString;
        var x     = (msg[3] ? 0.5).asFloat;
        var y     = (msg[4] ? 0.5).asFloat;
        var size  = (msg[5] ? 0.3).asFloat;
        var spin  = (msg[6] ? 0.0).asFloat;
        var tilt  = (msg[7] ? 0.0).asFloat;
        var luma  = (msg[8] ? 0.5).asFloat;
        var voice = ~teremVoices[id];
        if(voice.notNil) {
            // ja tem voz aberta pra este marcador -> so atualiza a pose.
            voice.set(\x, x, \y, y, \size, size, \spin, spin, \tilt, tilt, \luma, luma);
        } {
            // marcador novo -> abre a voz (gate=1), sabor pelo naipe, no habitat
            // atual (ou no silencio se ainda nao caiu carta nenhuma).
            voice = Synth(\teremin, [
                \bufnum, (~mundoCurrentBuf ? ~teremSilent), \gate, 1,
                \flavor, ~teremFlavor.(suit),
                \x, x, \y, y, \size, size, \spin, spin, \tilt, tilt, \luma, luma,
            ]);
            ~teremVoices[id] = voice;
        };
    }, "/mundo/control");

    // /mundo/control_off [id] - o marcador sumiu: solta o gate -> cauda (nao corta).
    OSCdef(\mundoControlOff, { |msg|
        var id = (msg[1] ? 0).asInteger;
        var voice = ~teremVoices[id];
        if(voice.notNil) {
            voice.set(\gate, 0);          // release longa; doneAction libera sozinho
            ~teremVoices.removeAt(id);
        };
    }, "/mundo/control_off");

    "[MUNDO] Pronto. Camada B (habitats + glitch + theremin) escutando /mundo/* na porta 57120.".postln;
});
)
