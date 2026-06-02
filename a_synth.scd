// =====================================================================
// BARALHO MUSICAL - RECEPTOR OSC + SYNTH (SuperCollider)
// =====================================================================
//
// Como usar:
//   1. Abra este arquivo no SuperCollider (sclang/IDE).
//   2. Selecione TUDO (Ctrl+A) e aperte Ctrl+Enter pra rodar de uma vez.
//      OU: posicione o cursor em cada bloco entre parenteses e Ctrl+Enter
//      bloco por bloco.
//   3. Aguarde "[BARALHO] Pronto." aparecer no post window.
//   4. No terminal Python, rode:  python a_osc.py
//      (ou main.py e escolha tocar via OSC)
//
// Pra trocar o som: edita o SynthDef \baralho abaixo (oscilador, envelope,
// filtros, efeitos...). Toda mudanca exige reexecutar o bloco do SynthDef.
//
// Pra parar tudo:  Ctrl+. (Ctrl + ponto)
// =====================================================================


// ---------------------------------------------------------------------
// 1. Inicia o servidor de audio
// ---------------------------------------------------------------------
(
s.waitForBoot({
    "[BARALHO] Servidor de audio iniciado.".postln;

    // -----------------------------------------------------------------
    // 2. SynthDef principal - som suave de "cordas+sopro" microtonal
    //
    // Parametros:
    //   freq:    frequencia em Hz (calculada do MIDI + cents no lado SC)
    //   amp:     amplitude 0..1 (vem da velocity MIDI/127)
    //   sustain: tempo em que o envelope fica em "hold" (segundos)
    //   atk:     ataque (fade-in)
    //   rel:     release (fade-out)
    //   pan:     -1 (esquerda) .. +1 (direita)
    // -----------------------------------------------------------------
    SynthDef(\baralho, { |freq=440, amp=0.3, sustain=0.5, atk=0.02, rel=0.4, pan=0,
                         revBusSpring=0, revBusHall=0, revBusPlate=0,
                         sendSpring=0, sendHall=0, sendPlate=0|
        var env, sig, vibrato;

        // Envelope ADSR-ish: ataque -> sustain hold -> release
        env = EnvGen.kr(
            Env([0, 1, 1, 0], [atk, sustain, rel], curve: \sin),
            doneAction: 2
        );

        // Vibrato sutil (LFO em torno da fundamental)
        vibrato = SinOsc.kr(5.5, mul: freq * 0.004);

        // Mistura: serra (corpo) + triangular (suavidade) + harmonico
        sig = Mix([
            Saw.ar(freq + vibrato, mul: 0.35),
            LFTri.ar((freq + vibrato) * 1.005, mul: 0.25),
            SinOsc.ar((freq + vibrato) * 2.0, mul: 0.15),
        ]);

        // Filtro passa-baixas que abre com o ataque (~"corpo" do som)
        sig = RLPF.ar(sig, freq * 6, 0.5);

        // Aplica envelope, panoramico e amplitude
        sig = Pan2.ar(sig * env * amp, pan);

        // Dry direto pro master + sends pros 3 buses de reverb
        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // -----------------------------------------------------------------
    // VIBRAFONE - VERSAO A: DynKlank (banco de ressonadores)
    //
    // Excita um banco de filtros ressonantes nas parciais INARMONICAS
    // tipicas de uma barra de metal. O vibrafone moderno tem barras
    // afinadas por "undercut" (rebaixo na barriga) pra concentrar as
    // parciais em razoes proximas a 1, 4, 10 da fundamental.
    //
    // Razoes usadas aqui: 1.0, 4.01, 9.97, 16.05 (com leves desafinos
    // pra dar "alma" - barra fisica nunca afina perfeito).
    //
    // O exciter e um burst MUITO curto de ruido (1-2ms) - simula o
    // impacto do mallet de feltro/borracha na barra. O ringtime de
    // cada parcial controla quanto ela "soa" depois do impacto.
    //
    // Mais "fisico" que aditiva - reage organicamente ao excitador.
    // -----------------------------------------------------------------
    SynthDef(\baralhoVibeKlank, { |freq=440, amp=0.3, sustain=0.5, atk=0.005, rel=2.0, pan=0,
                                   revBusSpring=0, revBusHall=0, revBusPlate=0,
                                   sendSpring=0, sendHall=0, sendPlate=0|
        var env, sig, exciter, excEnv, tremolo, masterRel;

        // Excitador: noise burst muito curto (mallet hit ~1-2ms)
        excEnv = EnvGen.kr(Env.perc(0.0005, 0.012), doneAction: 0);
        exciter = PinkNoise.ar(0.8) * excEnv;
        exciter = HPF.ar(exciter, freq * 1.5);  // "tinkle" do impacto

        // Banco de ressonadores - parciais inarmonicas de barra de metal
        sig = DynKlank.ar(
            `[
                [freq * 1.0, freq * 4.01, freq * 9.97, freq * 16.05],
                [1.0, 0.5, 0.2, 0.06],
                [2.5, 1.4, 0.7, 0.35]   // ring times: parciais altas decaem mais rapido
            ],
            exciter
        );

        // Tremolo das "ventoinhas" do vibrafone real (~6Hz, amp 18%)
        tremolo = SinOsc.kr(6, mul: 0.18, add: 0.82);
        sig = sig * tremolo;

        // Envelope mestre - garante cauda metalica de pelo menos 1.5s
        // (vibrafone real ringa 3-6s; STACATTO seria "damp com a palma"
        // que aqui aproximamos cortando mais cedo)
        masterRel = rel.max(1.5);
        env = EnvGen.kr(
            Env([0, 1, 1, 0], [0.001, sustain.max(0.01), masterRel], curve: \exp),
            doneAction: 2
        );

        sig = Pan2.ar(sig * env * amp * 0.35, pan);

        // Dry direto pro master + sends pros 3 buses de reverb
        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // -----------------------------------------------------------------
    // VIBRAFONE - VERSAO B: aditiva (SinOscs com envelopes proprios)
    //
    // Mesmas razoes inarmonicas (1, 4.01, 9.97, 16.05) mas cada parcial
    // e um SinOsc puro com seu PROPRIO envelope. Parciais altas decaem
    // mais rapido (decay multiplier menor) - imita o comportamento
    // fisico da barra sem usar DynKlank.
    //
    // Mais controlavel e previsivel; menos "vivo" que DynKlank porque
    // nao tem a ressonancia natural reagindo ao excitador.
    // Mallet click via HPF noise burst pra dar o "ataque seco".
    // -----------------------------------------------------------------
    SynthDef(\baralhoVibeAdd, { |freq=440, amp=0.3, sustain=0.5, atk=0.005, rel=2.0, pan=0,
                                 revBusSpring=0, revBusHall=0, revBusPlate=0,
                                 sendSpring=0, sendHall=0, sendPlate=0|
        var env, sig, partials, mallet, tremolo, totalDur;
        var ratios, pAmps, pDecays;

        ratios   = [1.0, 4.01, 9.97, 16.05];
        pAmps    = [1.0, 0.45, 0.2, 0.06];
        pDecays  = [1.0, 0.55, 0.30, 0.18];   // multiplica (sustain+rel)

        // Click do mallet - noise burst muito curto, HPF alto
        mallet = EnvGen.kr(Env.perc(0.0005, 0.015), doneAction: 0);
        mallet = HPF.ar(WhiteNoise.ar(0.4) * mallet, freq * 3);

        // Cauda minima de 1.5s pra dar "metal ringando"
        totalDur = (sustain + rel).max(1.5);

        // Soma de parciais com envelopes proprios decaindo
        partials = Mix.fill(4, { |i|
            var pEnv = EnvGen.kr(
                Env([0, 1, 0], [0.0008, totalDur * pDecays[i]], curve: \exp),
                doneAction: 0
            );
            SinOsc.ar(freq * ratios[i]) * pAmps[i] * pEnv
        });

        // Tremolo das ventoinhas
        tremolo = SinOsc.kr(6, mul: 0.16, add: 0.84);

        sig = (partials + mallet) * tremolo;

        // Envelope mestre - garante release limpo (doneAction libera o synth)
        env = EnvGen.kr(
            Env([0, 1, 1, 0], [0.001, sustain.max(0.01), totalDur - sustain.max(0.01)], curve: \exp),
            doneAction: 2
        );

        sig = Pan2.ar(sig * env * amp * 0.4, pan);

        // Dry direto pro master + sends pros 3 buses de reverb
        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // -----------------------------------------------------------------
    // SynthDef do ECO HARMONICO
    // Cada eco e uma senoide num harmonico da fundamental (2f, 3f, 4f...)
    // com um leve detune pra ganhar corpo. Envelope percussivo curto.
    // Sao disparados em sequencia pela Routine no OSCdef \baralhoNote,
    // formando o ping-pong stereo + serie harmonica decrescente.
    // -----------------------------------------------------------------
    SynthDef(\baralhoEcho, { |freq=440, amp=0.1, atk=0.005, rel=0.4, pan=0,
                              revBusSpring=0, revBusHall=0, revBusPlate=0,
                              sendSpring=0, sendHall=0, sendPlate=0,
                              echoIdx=0|
        var env, sig, wowMod, lpfMult, satDrive;

        // -------------------------------------------------------------
        // DEGRADACAO ANALOGICA progressiva por indice do eco:
        //   - wow & flutter: pitch oscila lentamente, mais intenso a cada eco
        //   - LPF aperta: cada eco perde mais agudo (mult cai 0.5 por eco)
        //   - saturacao acumula: tanh com drive crescente
        // -------------------------------------------------------------

        // Wow: SinOsc lento (0.5..1.2Hz) modulando freq. Amp 0.2%..0.7%.
        wowMod = SinOsc.kr(0.5 + (echoIdx * 0.15),
                           mul: freq * (0.002 + (echoIdx * 0.001)));

        env = EnvGen.kr(Env.perc(atk, rel, 1, -4), doneAction: 2);
        sig = SinOsc.ar(freq + wowMod) * 0.7
            + (SinOsc.ar((freq + wowMod) * 1.005) * 0.3);

        // LPF: i=0 -> cutoff em 4*freq (brilhante);  i=5 -> 1.5*freq (abafado)
        lpfMult = (4.0 - (echoIdx * 0.5)).max(1.3);
        sig = LPF.ar(sig, freq * lpfMult);

        // Saturacao: drive sobe a cada eco, compensa o ganho com sqrt
        satDrive = 1.0 + (echoIdx * 0.25);
        sig = (sig * satDrive).tanh / satDrive.sqrt;

        sig = Pan2.ar(sig * env * amp, pan);

        // Dry direto + sends pros reverbs (ecos seguem a nota original)
        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // -----------------------------------------------------------------
    // SPARKLE - enriquecimento progressivo pra notas LONGAS
    //
    // So e disparado pelo OSCdef quando durTotal > 2.0. Adiciona 3
    // parciais inarmonicas (1.498f, 6.21f, 13.05f) com onsets atrasados
    // (0.4s, 1.0s, 2.0s) - aditiva temporal, o timbre vai crescendo.
    // LPF abre ao longo da nota (2f -> 8f) - som "respirando".
    //
    // Razao das frequencias escolhidas:
    //   1.498f - quinta justa "quase" pitagorica (3:2 desafinada)
    //   6.21f  - parcial alta inarmonica, brilho
    //   13.05f - super-aguda, "shimmer"
    //
    // Granular ficou pra proxima iteracao (precisa de buffer setup).
    // -----------------------------------------------------------------
    SynthDef(\baralhoSparkle, { |freq=440, amp=0.1, durTotal=3.0, pan=0,
                                  revBusSpring=0, revBusHall=0, revBusPlate=0,
                                  sendSpring=0, sendHall=0, sendPlate=0|
        var sig, p1, p2, p3, lpfCut, masterEnv, safeDur;

        // Clamper duracao pra evitar tempos negativos no envelope
        safeDur = durTotal.max(2.0);

        // Parciais com onsets atrasados (atk = silencio inicial)
        // Env: [0, 0, peak, 0] em tempos [silencio, fadein, decay]
        p1 = SinOsc.ar(freq * 1.498) * EnvGen.kr(
            Env([0, 0, 0.5, 0], [0.4, 0.3, safeDur - 0.7])
        );
        p2 = SinOsc.ar(freq * 6.21) * EnvGen.kr(
            Env([0, 0, 0.3, 0], [1.0, 0.5, (safeDur - 1.5).max(0.5)])
        );
        p3 = SinOsc.ar(freq * 13.05) * EnvGen.kr(
            Env([0, 0, 0.15, 0], [2.0, 0.5, (safeDur - 2.5).max(0.3)])
        );

        sig = (p1 + p2 + p3) * amp;

        // LPF "respirando": cutoff abre de 2f pra 8f ao longo da nota
        lpfCut = EnvGen.kr(
            Env([freq * 2, freq * 8], [safeDur], curve: \exp)
        );
        sig = LPF.ar(sig, lpfCut);

        // Envelope mestre libera o synth ao final
        masterEnv = EnvGen.kr(
            Env([0, 1, 0], [0.05, safeDur], curve: \sin),
            doneAction: 2
        );
        sig = sig * masterEnv;

        sig = Pan2.ar(sig, pan);
        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // -----------------------------------------------------------------
    // REVERB SPRING - mola metalica (amp de guitarra, dub)
    //
    // Cadeia de AllpassN curtos com modulacao + LPF/HPF -> "boing" de
    // mola. Tempos pequenos (15-45ms) e moduladores LFNoise2 dao a
    // instabilidade caracteristica do spring fisico.
    // -----------------------------------------------------------------
    SynthDef(\baralhoRevSpring, { |inBus=0, mix=1.0|
        var in, sig;
        in = In.ar(inBus, 2);
        sig = in;
        4.do { |i|
            sig = AllpassN.ar(sig, 0.05,
                LFNoise2.kr(0.5 + (i * 0.3)).range(0.015, 0.045), 1.8);
        };
        // "Chirp" sutil do spring (delay modulado)
        sig = DelayC.ar(sig, 0.06, SinOsc.kr(0.4).range(0.005, 0.055));
        sig = HPF.ar(sig, 300);    // spring nao tem grave
        sig = LPF.ar(sig, 3500);   // metalico mas nao agressivo
        Out.ar(0, sig * mix * 0.55);
    }).add;

    // -----------------------------------------------------------------
    // REVERB HALL - espaco grande, decay longo
    //
    // GVerb com revtime alto (~5s) pra simular sala de concerto.
    // Damping medio pra atenuar agudos no decay (igual sala real).
    // -----------------------------------------------------------------
    SynthDef(\baralhoRevHall, { |inBus=0, mix=1.0|
        var in, mono, sig;
        in = In.ar(inBus, 2);
        mono = in.sum * 0.5;
        sig = GVerb.ar(mono,
            roomsize: 80, revtime: 5.0, damping: 0.4,
            inputbw: 0.5, spread: 25,
            drylevel: 0, earlyreflevel: 0.4, taillevel: 0.6,
            maxroomsize: 100);
        Out.ar(0, sig * mix * 0.35);
    }).add;

    // -----------------------------------------------------------------
    // REVERB PLATE - placa metalica, denso e brilhante
    //
    // FreeVerb2 com room alta e damp baixo simula a placa Lexicon-style.
    // HPF tira grave (placa real tinge agudos).
    // -----------------------------------------------------------------
    SynthDef(\baralhoRevPlate, { |inBus=0, mix=1.0|
        var in, sig;
        in = In.ar(inBus, 2);
        sig = FreeVerb2.ar(in[0], in[1], mix: 1.0, room: 0.85, damp: 0.2);
        sig = HPF.ar(sig, 180);
        Out.ar(0, sig * mix * 0.5);
    }).add;

    s.sync;
    "[BARALHO] SynthDefs carregados: \\baralho, \\baralhoVibeKlank, \\baralhoVibeAdd, \\baralhoEcho, \\baralhoSparkle, \\baralhoRev{Spring,Hall,Plate}.".postln;

    // -----------------------------------------------------------------
    // BUSES DE REVERB + INSTANCIA OS 3 PROCESSADORES NA CAUDA
    //
    // Cada nota escreve em ate 3 buses (spring/hall/plate) com ganho
    // independente. Os Synths abaixo leem cada bus, processam e somam
    // ao Out 0. `addToTail` garante que rodam DEPOIS das notas (que
    // entram no Group default em `addToHead`).
    //
    // Pra mudar parametros do reverb em runtime:
    //   ~revHall.set(\mix, 0.5);
    // Pra resetar tudo:  s.freeAll  e reexecutar o bloco.
    // -----------------------------------------------------------------
    if(~revBusSpring.notNil) { ~revBusSpring.free };
    if(~revBusHall.notNil)   { ~revBusHall.free };
    if(~revBusPlate.notNil)  { ~revBusPlate.free };
    ~revBusSpring = Bus.audio(s, 2);
    ~revBusHall   = Bus.audio(s, 2);
    ~revBusPlate  = Bus.audio(s, 2);

    if(~revSpring.notNil) { ~revSpring.free };
    if(~revHall.notNil)   { ~revHall.free };
    if(~revPlate.notNil)  { ~revPlate.free };
    ~revSpring = Synth.tail(nil, \baralhoRevSpring, [\inBus, ~revBusSpring.index]);
    ~revHall   = Synth.tail(nil, \baralhoRevHall,   [\inBus, ~revBusHall.index]);
    ~revPlate  = Synth.tail(nil, \baralhoRevPlate,  [\inBus, ~revBusPlate.index]);
    "[BARALHO] Reverbs ativos (spring, hall, plate) lendo dos buses.".postln;

    // -----------------------------------------------------------------
    // >>> SWITCH DE SOM BASE - troque pra comparar A/B/Original <<<
    //
    // Opcoes:
    //   \baralho           - original (serra+tri+sin com vibrato)
    //   \baralhoVibeKlank  - vibrafone via DynKlank (mais "fisico")
    //   \baralhoVibeAdd    - vibrafone aditivo (mais controlavel)
    //
    // Pra trocar: edite a linha abaixo e rode SO ELA (cursor + Ctrl+Enter).
    // Nao precisa reexecutar o bloco inteiro.
    // -----------------------------------------------------------------
    ~mainSynth = \baralhoVibeKlank;

    // -----------------------------------------------------------------
    // 3. Conversao MIDI + cents -> frequencia em Hz
    //    Python manda pitch_midi (int) e cents (-200..+200).
    //    A formula: hz = 440 * 2^((midi + cents/100 - 69)/12)
    // -----------------------------------------------------------------
    ~midiCentsToHz = { |midi, cents|
        var noteAdjusted = midi + (cents / 100.0);
        440 * (2 ** ((noteAdjusted - 69) / 12));
    };

    // -----------------------------------------------------------------
    // VOZ POR FORMANTES (camada de texto - Perec)
    //
    // \baralhoVox sintetiza UM fonema (vogal ou consoante) por ~80-150ms.
    // Tres BPFs em paralelo formam o "tubo vocal" (F1, F2, F3 do fonema).
    // Fonte voiced = pulso glotal (Saw + harmonico); unvoiced = ruido HPF.
    //
    // Usado em 2 contextos:
    //   1) Fragmentos curtos sincronizados com cada eco harmonico (whisper)
    //   2) Recitativo longo durante FERMATA (frase declamada)
    //
    // Roteado pros mesmos buses de reverb do synth principal - degrada
    // junto com o resto (wow & flutter, LPF, saturacao acontecem no proprio
    // \baralhoEcho; a voz adiciona um plano semantico em cima).
    // -----------------------------------------------------------------
    SynthDef(\baralhoVox, { |freq=180, formant1=730, formant2=1090, formant3=2440,
                             voiced=1, noiseHpf=0, gain=1.0, dur=0.12, pan=0,
                             revBusSpring=0, revBusHall=0, revBusPlate=0,
                             sendSpring=0, sendHall=0, sendPlate=0|
        var glott, noise, source, sig, env, hasF1, hasF2, hasF3, anyF;

        // Envelope: ataque rapido, hold curto, release suave (consoante seca,
        // vogal mais "redonda"). Linen(atk, sus, rel).
        env = EnvGen.kr(
            Env.linen(0.015, dur * 0.55, dur * 0.45, 1, \sin),
            doneAction: 2,
        );

        // Fonte voiced: pulso glotal aproximado (Saw + 2a harmonica
        // levemente desafinada + LPF pra suavizar). Boost de fundamental
        // pra dar mais "peito" pra voz nao soar tao filtrada.
        glott = Saw.ar(freq) * 1.2 + (Saw.ar(freq * 2.001) * 0.35);
        glott = LPF.ar(glott, 4800);

        // Fonte unvoiced: ruido HPF (consoantes fricativas e burst de
        // oclusivas tem energia concentrada em alta freq)
        noise = WhiteNoise.ar(0.5);
        noise = Select.ar(noiseHpf > 0,
            [noise, HPF.ar(noise, noiseHpf.max(100))]);

        // Voiced = pulso; unvoiced = ruido; consoante voiced = mistura
        source = (glott * voiced) + (noise * ((1 - voiced) + (voiced * 0.25)));

        // Tres BPFs em paralelo - o trato vocal.
        // RQ alargado (0.12->0.30, 0.10->0.25, 0.08->0.20) pra deixar o
        // source passar com "corpo" e a vogal ser identificavel em vez
        // de soar como sopro filtrado.
        hasF1 = formant1 > 1;
        hasF2 = formant2 > 1;
        hasF3 = formant3 > 1;
        anyF = hasF1 + hasF2 + hasF3;
        sig =
            (Select.ar(hasF1, [Silent.ar(1), BPF.ar(source, formant1.max(80), 0.30, 1.4)])
           + Select.ar(hasF2, [Silent.ar(1), BPF.ar(source, formant2.max(80), 0.25, 0.95)])
           + Select.ar(hasF3, [Silent.ar(1), BPF.ar(source, formant3.max(80), 0.20, 0.55)]));
        // Se nao tem formante nenhum (puro burst de ruido), usar source direto
        sig = Select.ar(anyF > 0, [source, sig]);

        sig = sig * env * gain * 0.55;   // gain global da voz (fantasma legivel)
        sig = Pan2.ar(sig, pan);

        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // -----------------------------------------------------------------
    // Tabela de formantes pt-br (aprox.) - Dictionary de fonemas
    //
    // Cada entrada tem: formants=[F1,F2,F3], voiced, dur (mult), gain,
    //                   noiseHpf (pra fricativas/oclusivas).
    // Quem disparou a sintese e responsavel por mapear o caractere pra
    // essa tabela via ~voxLookup (que normaliza acentos).
    // -----------------------------------------------------------------
    ~voxFormants = Dictionary[
        // vogais
        $a -> ( formants: [730, 1090, 2440], voiced: 1, dur: 1.0, gain: 1.0,  noiseHpf: 0 ),
        $e -> ( formants: [530, 1840, 2480], voiced: 1, dur: 1.0, gain: 1.0,  noiseHpf: 0 ),
        $i -> ( formants: [270, 2290, 3010], voiced: 1, dur: 0.9, gain: 0.85, noiseHpf: 0 ),
        $o -> ( formants: [570,  840, 2410], voiced: 1, dur: 1.0, gain: 1.0,  noiseHpf: 0 ),
        $u -> ( formants: [300,  870, 2240], voiced: 1, dur: 1.0, gain: 0.9,  noiseHpf: 0 ),
        $y -> ( formants: [270, 2290, 3010], voiced: 1, dur: 0.9, gain: 0.85, noiseHpf: 0 ),
        // aproximantes / liquidas
        $l -> ( formants: [380, 1200, 2700], voiced: 1, dur: 0.7, gain: 0.8,  noiseHpf: 0 ),
        $r -> ( formants: [380, 1300, 2600], voiced: 1, dur: 0.5, gain: 0.7,  noiseHpf: 0 ),
        // nasais
        $m -> ( formants: [250, 1100, 2700], voiced: 1, dur: 0.7, gain: 0.7,  noiseHpf: 0 ),
        $n -> ( formants: [280, 1700, 2700], voiced: 1, dur: 0.7, gain: 0.7,  noiseHpf: 0 ),
        // fricativas unvoiced (so noise filtrado)
        $s -> ( formants: [4500, 6500, 0], voiced: 0, dur: 0.9, gain: 0.55, noiseHpf: 4000 ),
        $f -> ( formants: [1500, 3500, 0], voiced: 0, dur: 0.8, gain: 0.45, noiseHpf: 1800 ),
        $x -> ( formants: [3000, 5000, 0], voiced: 0, dur: 0.8, gain: 0.50, noiseHpf: 2500 ),
        $h -> ( formants: [   0,    0, 0], voiced: 0, dur: 0.6, gain: 0.30, noiseHpf:  800 ),
        // fricativas voiced (pulso + ruido)
        $v -> ( formants: [ 400, 1500, 0], voiced: 1, dur: 0.6, gain: 0.55, noiseHpf: 1500 ),
        $z -> ( formants: [ 250, 1700, 0], voiced: 1, dur: 0.7, gain: 0.55, noiseHpf: 3500 ),
        $j -> ( formants: [ 350, 2200, 0], voiced: 1, dur: 0.6, gain: 0.50, noiseHpf: 2200 ),
        // oclusivas unvoiced - burst curtissimo
        $p -> ( formants: [   0,    0, 0], voiced: 0, dur: 0.3, gain: 0.6, noiseHpf: 1200 ),
        $t -> ( formants: [   0,    0, 0], voiced: 0, dur: 0.3, gain: 0.6, noiseHpf: 3500 ),
        $k -> ( formants: [   0,    0, 0], voiced: 0, dur: 0.3, gain: 0.6, noiseHpf: 2000 ),
        // oclusivas voiced - burst + tonal
        $b -> ( formants: [ 200,  800, 2200], voiced: 1, dur: 0.4, gain: 0.6, noiseHpf:  600 ),
        $d -> ( formants: [ 300, 1700, 2500], voiced: 1, dur: 0.4, gain: 0.6, noiseHpf: 1500 ),
        $g -> ( formants: [ 250, 1500, 2200], voiced: 1, dur: 0.4, gain: 0.6, noiseHpf: 1000 ),
        // outros (catch-all)
        $w -> ( formants: [ 300,  600, 2200], voiced: 1, dur: 0.8, gain: 0.7, noiseHpf: 0 ),
        $q -> ( formants: [   0,    0,    0], voiced: 0, dur: 0.3, gain: 0.6, noiseHpf: 2000 ),
        $c -> ( formants: [   0,    0,    0], voiced: 0, dur: 0.3, gain: 0.6, noiseHpf: 2000 ),
        // espaco = pausa silenciosa
        $\  -> ( formants: [   0,    0, 0], voiced: 0, dur: 0.6, gain: 0.0, noiseHpf: 0 ),
    ];

    // Retorna entry da tabela pro caractere (ascii lower), nil se nao tem.
    // O Python normaliza acentos ANTES de enviar (NFD + strip), entao aqui
    // assumimos so ASCII a-z + espaco.
    ~voxLookup = { |chr|
        ~voxFormants[chr.asString.toLower[0]]
    };

    // Dispara uma string como sequencia de fonemas. Cada caractere vira um
    // Synth(\baralhoVox) com timing baseado em sua duracao tabelada.
    //
    // Args:
    //   str:      a string a ser falada
    //   basefreq: freq fundamental da voz (Hz) - 120-200 da voz "media"
    //   charDur:  duracao base por caractere (modulada pela tabela)
    //   pan, gain: pan estereo e ganho global
    //   sends:    roteamento pros buses de reverb (pra integrar com efeitos)
    ~falaString = { |str, basefreq=160, charDur=0.10, pan=0, gain=0.6,
                     revBusSpring=0, revBusHall=0, revBusPlate=0,
                     sendSpring=0, sendHall=0, sendPlate=0|
        if(str.notNil && (str.size > 0)) {
            Routine({
                str.do { |chr|
                    var entry = ~voxLookup.(chr);
                    var d = charDur;
                    if(entry.notNil) {
                        d = charDur * (entry[\dur] ? 1.0);
                        if((entry[\gain] ? 0) > 0.001) {
                            Synth(\baralhoVox, [
                                // Pitch jitter sutil (±1%) pra nao soar
                                // robotico mas sem pular entre fonemas
                                // como se fossem vozes diferentes.
                                \freq, basefreq * (1 + 1.0.rand2 * 0.01),
                                \formant1, (entry[\formants])[0],
                                \formant2, (entry[\formants])[1],
                                \formant3, (entry[\formants])[2],
                                \voiced, (entry[\voiced] ? 1).asInteger,
                                \noiseHpf, (entry[\noiseHpf] ? 0),
                                \gain, gain * (entry[\gain] ? 1.0),
                                \dur, d,
                                // Pan FIXO - sem jitter por fonema. Voz
                                // tem que ficar parada no espaco pro
                                // cerebro rastrear como "uma voz".
                                \pan, pan.clip(-1, 1),
                                \revBusSpring, revBusSpring,
                                \revBusHall,   revBusHall,
                                \revBusPlate,  revBusPlate,
                                \sendSpring, sendSpring,
                                \sendHall,   sendHall,
                                \sendPlate,  sendPlate,
                            ]);
                        };
                    };
                    d.wait;
                };
            }).play;
        };
    };

    // -----------------------------------------------------------------
    // TTS PRE-RENDERIZADO (caminho 3) - samples WAV de SAPI Maria pt-br
    //
    // Python renderiza cada palavra unica via a_voz.py e manda
    // /baralho/fala_load [chave, path_abs] no startup. Aqui carregamos
    // em ~ttsBuffers[chave] = Buffer. Na hora de "falar", ~falaWords
    // separa a string em palavras e toca o buffer de cada uma em
    // sequencia. Mais legivel que sintese formantica (\baralhoVox).
    // -----------------------------------------------------------------
    ~ttsBuffers = Dictionary.new;

    // Toca um buffer de palavra como SUSSURRO via channel vocoder simples:
    // voz original eh dividida em bandas BPF; pra cada banda extraimos a
    // amplitude (envelope follower) e modulamos noise filtrado na mesma
    // banda. Resultado: a articulacao da Maria, com timbre de ar/sopro
    // em vez de tonal. Mistura controlada por \whisper (0=tonal, 1=puro
    // sussurro). Pra fantasma legivel: whisper~0.85, com um pingo de
    // tonal pra manter inflexao prosodica.
    //
    // breath: ruido HPF de fundo modulado pelo envelope global. Da o
    // "sopro" entre fonemas (e nao soa tao seco quanto so vocoder).
    SynthDef(\baralhoWord, { |bufnum=0, rate=1.0, amp=0.6, pan=0,
                              lpf=2800, atk=0.01, rel=0.15,
                              whisper=0.55, tonal=0.50, breath=0.08,
                              revBusSpring=0, revBusHall=0, revBusPlate=0,
                              sendSpring=0, sendHall=0, sendPlate=0|
        var src, env, dur, sig, voiceLPF, whisperSig, breathSig, ampGlobal;
        var bands = [380, 620, 950, 1400, 2000, 2800, 4000];

        dur = BufDur.kr(bufnum) / rate;
        env = EnvGen.kr(
            Env([0, 1, 1, 0], [atk, (dur - atk - rel).max(0.01), rel], curve: \sin),
            doneAction: 2
        );

        src = PlayBuf.ar(1, bufnum, BufRateScale.kr(bufnum) * rate, doneAction: 0);
        voiceLPF = LPF.ar(src, lpf);

        // Channel vocoder: pra cada banda formantica, ruido modulado pela
        // amplitude da voz naquela mesma banda. rq=0.4 = banda larga
        // (mantem inteligibilidade); rq menor = mais formantico/cantado.
        whisperSig = Mix.ar(bands.collect { |fc|
            var voiceBand = BPF.ar(voiceLPF, fc, 0.4);
            var bandAmp = Amplitude.kr(voiceBand,
                attackTime: 0.005, releaseTime: 0.025);
            var noiseBand = BPF.ar(WhiteNoise.ar(1.0), fc, 0.4);
            noiseBand * bandAmp * 5.5;
        }) * 0.55;

        // Breath: ar HPF de fundo, modulado pelo envelope geral da voz
        // (pra respirar com a articulacao, nao constante).
        ampGlobal = Amplitude.kr(voiceLPF,
            attackTime: 0.020, releaseTime: 0.080);
        breathSig = HPF.ar(PinkNoise.ar(0.7), 1800) * ampGlobal * 3.5 * breath;

        // Blend whisper vs tonal. whisper=1 -> so vocoder; whisper=0 -> so voz.
        // tonal eh um ganho EXTRA da voz original (sempre presente em pouca
        // dose, mesmo com whisper=1, pra manter prosodia).
        sig = (whisperSig * whisper) + (voiceLPF * tonal) + breathSig;
        sig = sig * env * amp;
        sig = Pan2.ar(sig, pan);

        Out.ar(0, sig);
        Out.ar(revBusSpring, sig * sendSpring);
        Out.ar(revBusHall,   sig * sendHall);
        Out.ar(revBusPlate,  sig * sendPlate);
    }).add;

    // Toca uma string como sequencia de PALAVRAS (buffers TTS), com gap
    // entre palavras pra prosodia parar/respirar. Args espelham ~falaString
    // pra ser drop-in (basefreq/charDur agora viram rate/wordGap).
    //
    // rate:    pitch shift global (0.85 = um pouco grave/fantasma)
    // wordGap: pausa entre palavras (s). 0.08-0.18 funciona bem.
    // NetAddr pra mandar sync palavra-a-palavra de volta pro Python.
    // Tem que bater com WORD_SYNC_PORT em a_visual_web.py.
    ~wordSyncTarget = NetAddr.new("127.0.0.1", 57121);

    ~falaWords = { |str, rate=0.92, wordGap=0.10, pan=0, gain=0.6, lpf=4500,
                    revBusSpring=0, revBusHall=0, revBusPlate=0,
                    sendSpring=0, sendHall=0, sendPlate=0,
                    source=\echo|
        if(str.notNil && (str.size > 0)) {
            Routine({
                var words = str.asString.toLower.split($ );
                var total = words.size;
                words.do { |w, idx|
                    var key = w.select({ |c| c.isAlpha });
                    var buf = ~ttsBuffers[key.asSymbol];
                    // Avisa o visualizer ANTES de soar (ou nao soar): so
                    // a Routine sabe o tempo real de cada palavra. Manda
                    // a forma displayed (lowercase ascii) - JS faz match
                    // por normalizePT no cliente.
                    if(key.size > 0) {
                        ~wordSyncTarget.sendMsg("/baralho/word_now",
                            key.asString, idx, total, source.asString);
                    };
                    if(buf.notNil && buf.numFrames.notNil && (buf.numFrames > 0)) {
                        Synth(\baralhoWord, [
                            \bufnum, buf.bufnum,
                            \rate, rate,
                            \amp, gain,
                            \pan, pan.clip(-1, 1),
                            \lpf, lpf,
                            \revBusSpring, revBusSpring,
                            \revBusHall,   revBusHall,
                            \revBusPlate,  revBusPlate,
                            \sendSpring, sendSpring,
                            \sendHall,   sendHall,
                            \sendPlate,  sendPlate,
                        ]);
                        (buf.duration / rate + wordGap).wait;
                    } {
                        // palavra sem buffer (vazia, ou nao foi pre-renderizada)
                        if(w.size > 0) { wordGap.wait };
                    };
                };
            }).play;
        };
    };

    // Buffer dos 6 fragmentos da nota atual. Setado pelo OSC
    // /baralho/fala_setup ANTES de /baralho/note chegar; a Routine
    // de ecos do baralhoNote le esse array.
    ~voxFragments = Array.fill(6, "");

    // -----------------------------------------------------------------
    // 4. Receptor OSC /baralho/note
    //    args: pitch, vel, cents, dur_total, dur_sustain, articulacao,
    //          bpm, fermata, tie_in, tie_out
    // -----------------------------------------------------------------
    OSCdef(\baralhoNote, { |msg|
        var pitch, vel, cents, durTotal, durSustain, art, bpm,
            fermata, tieIn, tieOut,
            freq, amp, atk, rel, pan,
            revMix, revType, sendSpring, sendHall, sendPlate;

        pitch      = msg[1];
        vel        = msg[2];
        cents      = msg[3];
        durTotal   = msg[4];
        durSustain = msg[5];
        art        = msg[6].asString;   // SC recebe symbols/strings
        bpm        = msg[7];
        fermata    = msg[8];
        tieIn      = msg[9];
        tieOut     = msg[10];

        freq = ~midiCentsToHz.(pitch, cents);
        amp = (vel / 127) * 0.5;        // teto em 0.5 pra nao saturar

        // Ataque e release variam com a articulacao
        atk = (art == "STACATTO").if(0.005, 0.02);
        atk = ((art == "ACENTO") || (art == "ACENTO C/ STACATTO") || (art == "ACENTO C/ TENUTO")).if(0.003, atk);
        rel = durTotal - durSustain;
        rel = rel.max(0.05);            // release minimo de 50ms

        // Pan suave aleatorio pra dar "campo estereo" entre notas
        pan = 1.0.rand2 * 0.3;

        // -------------------------------------------------------------
        // MAPEAMENTO DE REVERB POR ARTICULACAO + MIX POR FREQUENCIA
        //
        // Tabela:
        //   NORMAL              -> plate (default brilhante)
        //   ACENTO              -> spring (mola, impacto)
        //   TENUTO              -> hall (decay longo, sustenta)
        //   STACATTO            -> seco (damp, sem reverb)
        //   ACENTO C/ STACATTO  -> spring (acento ganha, spring ja curto)
        //   TENUTO C/ STACATTO  -> plate (meio termo)
        //   ACENTO C/ TENUTO    -> hall (sustento + acento -> hall amplo)
        //
        // Mix base depende da freq: notas agudas decaem rapido fisicamente
        // entao recebem mais reverb pra compensar (0.15 a 0.7).
        // -------------------------------------------------------------
        revMix = freq.linlin(200, 4000, 0.15, 0.7);

        revType = case
            { art == "STACATTO" }              { \dry }
            { art == "ACENTO C/ STACATTO" }    { \spring }
            { art == "TENUTO C/ STACATTO" }    { \plate }
            { art == "ACENTO C/ TENUTO" }      { \hall }
            { art == "ACENTO" }                { \spring }
            { art == "TENUTO" }                { \hall }
            { true }                            { \plate };   // NORMAL e fallback

        sendSpring = 0; sendHall = 0; sendPlate = 0;
        case
            { revType == \spring } { sendSpring = revMix }
            { revType == \hall }   { sendHall   = revMix }
            { revType == \plate }  { sendPlate  = revMix };

        Synth(~mainSynth ? \baralho, [
            \freq, freq,
            \amp, amp,
            \atk, atk,
            \sustain, durSustain.max(0.01),
            \rel, rel,
            \pan, pan,
            \revBusSpring, ~revBusSpring.index,
            \revBusHall,   ~revBusHall.index,
            \revBusPlate,  ~revBusPlate.index,
            \sendSpring, sendSpring,
            \sendHall,   sendHall,
            \sendPlate,  sendPlate,
        ]);

        // -------------------------------------------------------------
        // SPARKLE pra notas longas - parciais inarmonicas extras com
        // onsets atrasados (aditiva temporal). So dispara se durTotal>2s
        // pra nao poluir o ataque de notas curtas.
        // -------------------------------------------------------------
        if(durTotal > 2.0) {
            Synth(\baralhoSparkle, [
                \freq, freq,
                \amp, amp * 0.3,             // 30% do volume da nota
                \durTotal, durTotal,
                \pan, pan,
                \revBusSpring, ~revBusSpring.index,
                \revBusHall,   ~revBusHall.index,
                \revBusPlate,  ~revBusPlate.index,
                \sendSpring, sendSpring,
                \sendHall,   sendHall,
                \sendPlate,  sendPlate,
            ]);
        };

        // -------------------------------------------------------------
        // ECOS HARMONICOS PING-PONG (serie harmonica decrescente)
        //
        // Para cada nota com duracao suficiente, dispara N ecos:
        //   - eco i toca o (i+2)-esimo harmonico da fundamental
        //     (ou seja: 2f, 3f, 4f, 5f, 6f, 7f - oitava, oit+5a, 2 oit,
        //      2 oit+3a, 2 oit+5a, 7a harmonica microtonal)
        //   - pan alterna esquerda/direita (ping-pong stereo) comecando
        //     no lado OPOSTO ao da nota original
        //   - amplitude decai exponencialmente (decay^i)
        //   - intervalo entre ecos = metade do beat (deriva do BPM)
        //
        // Notas curtas (< 0.15s) nao disparam pra evitar papa sonora.
        // -------------------------------------------------------------
        if(durTotal > 0.15) {
            var freqLocal = freq;
            var ampLocal = amp;
            var bpmLocal = bpm.max(20);
            var panSign = if(pan >= 0, { -1.0 }, { 1.0 });

            Routine({
                var nHarms = 6;
                var delayTime = (60 / bpmLocal) * 0.5;
                var decay = 0.55;
                nHarms.do { |i|
                    var harmFreq, harmAmp, harmPan;
                    delayTime.wait;
                    harmFreq = freqLocal * (i + 2);
                    harmAmp  = ampLocal * (decay ** (i + 1));
                    harmPan  = panSign * if(i.even, { 0.85 }, { -0.85 });
                    // Nao toca harmonicos que ja sairam da faixa audivel
                    if((harmFreq < 16000) && (harmAmp > 0.001)) {
                        // Mix de reverb proprio do eco - reduz pra ele nao
                        // dominar o reverb global (ja que ecos sao agudos)
                        var echoRevMix = harmFreq.linlin(200, 4000, 0.10, 0.5);
                        var eSpring = 0, eHall = 0, ePlate = 0;
                        var fragStr;
                        case
                            { revType == \spring } { eSpring = echoRevMix }
                            { revType == \hall }   { eHall   = echoRevMix }
                            { revType == \plate }  { ePlate  = echoRevMix };
                        Synth(\baralhoEcho, [
                            \freq, harmFreq,
                            \amp, harmAmp,
                            \pan, harmPan,
                            \atk, 0.005,
                            \rel, 0.35 + (i * 0.08),   // ecos posteriores tem cauda maior
                            \revBusSpring, ~revBusSpring.index,
                            \revBusHall,   ~revBusHall.index,
                            \revBusPlate,  ~revBusPlate.index,
                            \sendSpring, eSpring,
                            \sendHall,   eHall,
                            \sendPlate,  ePlate,
                            \echoIdx, i,
                        ]);
                        // -----------------------------------------------------
                        // VOZ sincronizada com o eco: pega o fragmento i do
                        // buffer ~voxFragments. Apenas eco 0 fala (uma voz
                        // so) - mais de uma sobreposta vira confusao
                        // semantica. Fonemas mais longos (charDur=0.18) pra
                        // ficar no limiar de identificacao da vogal.
                        // -----------------------------------------------------
                        fragStr = (~voxFragments[i] ? "").asString;
                        if((i < 1) && (fragStr.size > 0)) {
                            // TTS pre-renderizado: dispara cada palavra como
                            // buffer (~falaWords). Rate < 1 desce o pitch um
                            // pouco - voz fantasma sem comprometer fonemas.
                            ~falaWords.(
                                fragStr,
                                0.92 - (i * 0.02),                    // rate (pitch shift sutil)
                                0.10,                                  // wordGap entre palavras
                                harmPan * 0.6,                        // pan menos extremo
                                (ampLocal * 0.45) * (0.78 ** i),      // fantasma: sub-mix do vibrafone
                                2800,                                  // lpf bem abafado (fantasma distante)
                                ~revBusSpring.index, ~revBusHall.index, ~revBusPlate.index,
                                eSpring, eHall, ePlate,
                            );
                        };
                    };
                };
            }).play;
        };

        // Log no post window
        ("  [NOTE] MIDI " ++ pitch ++ " cents " ++ cents
            ++ "  hz=" ++ freq.round(0.1)
            ++ "  vel=" ++ vel ++ "  " ++ art
            ++ "  dur=" ++ durTotal.round(0.01) ++ "s"
            ++ (fermata > 0).if(" ^", "")).postln;
    }, "/baralho/note");

    // -----------------------------------------------------------------
    // 5. Receptor /baralho/rest  (pausa)
    //    Nao toca nada - so loga.
    // -----------------------------------------------------------------
    OSCdef(\baralhoRest, { |msg|
        var dur = msg[1];
        ("  ... PAUSA " ++ dur.round(0.01) ++ "s").postln;
    }, "/baralho/rest");

    // -----------------------------------------------------------------
    // 6. Inicio / fim
    // -----------------------------------------------------------------
    OSCdef(\baralhoStart, { |msg|
        "[BARALHO] ===== INICIO DA COMPOSICAO =====".postln;
    }, "/baralho/start");

    OSCdef(\baralhoEnd, { |msg|
        "[BARALHO] ===== FIM DA COMPOSICAO =====".postln;
    }, "/baralho/end");

    // -----------------------------------------------------------------
    // /baralho/fala_setup [s0, s1, s2, s3, s4, s5]
    //
    // Python envia ANTES do /baralho/note com os 6 fragmentos de texto
    // que cada eco harmonico vai sussurrar. Cada eco i le ~voxFragments[i].
    // String vazia = eco sem fala (so o tom do eco). Strings podem vir
    // em qualquer das 6 slots; ordem segue a sequencia dos ecos.
    // -----------------------------------------------------------------
    OSCdef(\baralhoFalaSetup, { |msg|
        ~voxFragments = Array.fill(6, { |i| (msg[i+1] ? "").asString });
    }, "/baralho/fala_setup");

    // -----------------------------------------------------------------
    // /baralho/fala_recitativo [texto, dur_segundos, pan]
    //
    // Disparado pelo Python quando a nota tem FERMATA. Sintetiza voz
    // declamada distribuida ao longo de dur_segundos (charDur ajustada
    // proporcionalmente ao tamanho do texto e duracao).
    // Vai roteada pro hall (decay longo, "presenca" de recitativo).
    // -----------------------------------------------------------------
    OSCdef(\baralhoFalaRecitativo, { |msg|
        var texto = (msg[1] ? "").asString;
        var dur = (msg[2] ? 2.0).asFloat;
        var pan = (msg[3] ? 0.0).asFloat;
        var sendHall, wordGap;
        if(texto.size > 0) {
            sendHall = 0.55;  // recitativo bem na cauda do hall
            // Recitativo eh "narrado lento" - gap maior entre palavras
            // pra dar peso/presenca. Rate 0.88 = um pouco mais grave que
            // os ecos sussurrados.
            wordGap = (dur / texto.split($ ).size.max(1) * 0.20).clip(0.12, 0.45);
            ~falaWords.(
                texto,
                0.88,           // rate (voz narradora um pouco grave)
                wordGap,
                pan,
                0.42,           // gain fantasma - recitativo legivel mas sussurrado
                3400,           // lpf um pouco mais aberto que ecos, mas ainda velado
                ~revBusSpring.index, ~revBusHall.index, ~revBusPlate.index,
                0, sendHall, 0.15,
                \recitativo,    // source -> visualizer pinta diferente
            );
            ("[FALA REC] '" ++ texto.copyRange(0, 40.min(texto.size-1)) ++
                "...' (" ++ dur.round(0.1) ++ "s)").postln;
        };
    }, "/baralho/fala_recitativo");

    // -----------------------------------------------------------------
    // /baralho/fala_load [chave, path_abs]
    //
    // Python envia uma mensagem por palavra unica no startup, carregando
    // os WAVs do tts_cache/ em ~ttsBuffers. ~falaWords le esse dict.
    // -----------------------------------------------------------------
    OSCdef(\baralhoFalaLoad, { |msg|
        var key = (msg[1] ? "").asString.asSymbol;
        var path = (msg[2] ? "").asString;
        if((key != '') && (path.size > 0)) {
            Buffer.read(s, path, action: { |b|
                ~ttsBuffers[key] = b;
            });
        };
    }, "/baralho/fala_load");

    // /baralho/fala_clear  - libera todos buffers TTS (uso: troca de proj)
    OSCdef(\baralhoFalaClear, { |msg|
        ~ttsBuffers.do { |b| if(b.notNil) { b.free } };
        ~ttsBuffers = Dictionary.new;
        "[BARALHO] buffers TTS limpos.".postln;
    }, "/baralho/fala_clear");

    "[BARALHO] Pronto. Aguardando OSC em porta 57120.".postln;
    "[BARALHO] Pra parar tudo: Ctrl+. (Ctrl+ponto)".postln;
});
)


// =====================================================================
// COMANDOS UTEIS (executar com cursor na linha + Ctrl+Enter)
// =====================================================================

// Parar todos os sons agora:
// s.freeAll;

// Desligar os receptores OSC (se quiser silencio total):
// OSCdef(\baralhoNote).free;
// OSCdef(\baralhoRest).free;
// OSCdef(\baralhoStart).free;
// OSCdef(\baralhoEnd).free;

// =====================================================================
// TROCA RAPIDA DE SOM BASE (A/B test)
// Posicione o cursor numa linha e aperte Ctrl+Enter:
// =====================================================================
// ~mainSynth = \baralho;            // original (synth)
// ~mainSynth = \baralhoVibeKlank;   // vibrafone via DynKlank
// ~mainSynth = \baralhoVibeAdd;     // vibrafone aditivo

// Tocar uma nota de teste pra ouvir o synth atual sem mandar OSC
// (incluindo sends pros reverbs - troque \sendHall por \sendSpring/\sendPlate
// pra testar cada tipo, ou zere todos pra ouvir seco):
//
// Synth(~mainSynth, [
//     \freq, 440, \amp, 0.3, \sustain, 0.5, \rel, 1.5,
//     \revBusSpring, ~revBusSpring.index,
//     \revBusHall,   ~revBusHall.index,
//     \revBusPlate,  ~revBusPlate.index,
//     \sendHall, 0.5,
// ]);

// =====================================================================
// AJUSTAR REVERBS EM RUNTIME (sem reexecutar nada)
// =====================================================================
// ~revSpring.set(\mix, 0.0);   // mutar spring global
// ~revHall.set(\mix, 1.5);     // hall mais alto
// ~revPlate.set(\mix, 0.8);

// Reiniciar so os reverbs (mantem SynthDefs):
// ~revSpring.free; ~revHall.free; ~revPlate.free;
// ~revSpring = Synth.tail(nil, \baralhoRevSpring, [\inBus, ~revBusSpring.index]);
// ~revHall   = Synth.tail(nil, \baralhoRevHall,   [\inBus, ~revBusHall.index]);
// ~revPlate  = Synth.tail(nil, \baralhoRevPlate,  [\inBus, ~revBusPlate.index]);
