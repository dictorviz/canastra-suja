// =====================================================================
// A_BANCO.scd  -  BANCO DE SONORIDADES da cama (vibrafone)
// =====================================================================
//
// ---------------------------------------------------------------------
// LEIA ISTO PRIMEIRO (pra quem nunca viu codigo)
// ---------------------------------------------------------------------
// ATENCAO: isto e SuperCollider (linguagem de SOM), nao Python. Este
// arquivo e uma "vitrine de timbres" pra voce OUVIR e COMPARAR varias
// cores do vibrafone -- as que a peca ja usa e algumas TECNICAS
// ESTENDIDAS novas (arco, sul tasto, ponticello, pizz, sino, motor,
// gongo). Nada aqui entra na peca automaticamente: e um laboratorio pra
// voce decidir o que vale a pena adotar depois no a_synth.scd.
//
// COMO USAR (passo a passo):
//   1. Rode o a_synth.scd PRIMEIRO (Ctrl+A, Ctrl+Enter) -- este banco usa
//      os reverbs (spring/hall/plate) que ele cria.
//   2. Rode ESTE arquivo (Ctrl+A, Ctrl+Enter). Aguarde "[BANCO] pronto".
//   3. Ouca uma sonoridade (cursor na linha + Ctrl+Enter):
//        ~tocar.(\arco);            // toca a tecnica "arco" numa nota
//        ~tocar.(\sul_tasto, 330);  // mesma coisa, mas na frequencia 330 Hz
//      Ouca TODAS em fila, com o nome aparecendo no post:
//        ~bancoTodos.();
//      Ver a lista de nomes + descricao:
//        ~bancoLista.();
//   4. Pra parar tudo: Ctrl+. (Ctrl + ponto).
//
// Tres palavrinhas (igual aos outros .scd):
//   * SynthDef(\nome, {...}) = a RECEITA de um som (a planta).
//   * ~algumaCoisa = uma "caixa com nome" global (variavel/funcao).
//   * \algumaCoisa (com barra) = so um nome/etiqueta. // = comentario.
//
// Pra mexer e dar MAIS variedade: cada SynthDef abaixo tem parametros
// (parciais, ring times, filtros, motor...). Mude os numeros, rode a
// SynthDef de novo (Ctrl+Enter no bloco dela) e ~tocar de novo pra ouvir.
// Os comentarios dizem o que cada bloco controla.
// ---------------------------------------------------------------------

(
// Guarda: o banco precisa do a_synth.scd ja rodando (pelos buses de reverb).
if(~revBusPlate.isNil) {
    "[BANCO] >>> Rode o a_synth.scd PRIMEIRO! Faltam os buses de reverb. <<<".postln;
};

// =====================================================================
// TECNICAS ESTENDIDAS NOVAS (SynthDefs)
// Todas roteiam pros mesmos 3 buses de reverb do a_synth.scd, entao
// convivem com a cama sem mexer nela.
// =====================================================================

// --- ARCO (bowed): a barra TOCADA COM ARCO. Sem ataque de mallet: uma
//     excitacao CONTINUA (ruido filtrado na fundamental) faz o metal
//     "cantar", etereo e sustentado. Ataque lento, cauda longa.
SynthDef(\bancoArco, { |freq=440, amp=0.3, atk=0.6, sustain=1.6, rel=1.6, pan=0,
                        revBusSpring=0, revBusHall=0, revBusPlate=0,
                        sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig, bow;
    env = EnvGen.kr(Env([0, 1, 1, 0], [atk, sustain, rel], \sin), doneAction: 2);
    // "arco" = friccao continua: ruido + um pouco de seno grave (a crina)
    bow = PinkNoise.ar(0.18) + (SinOsc.ar(freq * 0.5, 0, 0.03));
    bow = BPF.ar(bow, freq, 0.7) * 0.7;
    // mesmo banco de parciais do vibrafone, mas excitado SEM PARAR -> canta
    sig = DynKlank.ar(`[
        [freq * 1.0, freq * 4.01, freq * 9.97, freq * 16.05],
        [1.0, 0.6, 0.25, 0.08],
        [3.5, 2.0, 1.0, 0.5]
    ], bow);
    sig = LPF.ar(sig, freq * 8);
    sig = Pan2.ar(sig * env * amp * 0.5, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

// --- SUL TASTO / FLAUTANDO: doce e oco. So a fundamental + um fio de
//     parcial, filtro fechado, ataque macio, SEM o "click" do mallet.
//     O oposto do brilho metalico -- quase uma flauta de metal.
SynthDef(\bancoFlautando, { |freq=440, amp=0.3, atk=0.06, sustain=0.8, rel=2.5, pan=0,
                             revBusSpring=0, revBusHall=0, revBusPlate=0,
                             sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig;
    env = EnvGen.kr(Env([0, 1, 1, 0], [atk, sustain.max(0.01), rel.max(0.5)], \sin),
                    doneAction: 2);
    sig = SinOsc.ar(freq)
        + (SinOsc.ar(freq * 2.0) * 0.06)
        + (SinOsc.ar(freq * 4.01) * 0.10);     // um fio de parcial inarmonica
    sig = LPF.ar(sig, freq * 3);                // tira o brilho -> "tasto"
    sig = Pan2.ar(sig * env * amp * 0.45, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

// --- SUL PONTICELLO / VIDRO: aspero e agudo. Enfatiza as parciais ALTAS
//     (4x, 10x, 16x, 22x) e quase nada de fundamental. Mallet duro (HPF).
//     Som de vidro/metal raspado, brilhante e cortante.
SynthDef(\bancoPont, { |freq=440, amp=0.3, sustain=0.4, rel=2.0, pan=0,
                        revBusSpring=0, revBusHall=0, revBusPlate=0,
                        sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig, exc, excEnv;
    excEnv = EnvGen.kr(Env.perc(0.0003, 0.008), doneAction: 0);
    exc = WhiteNoise.ar(0.9) * excEnv;
    exc = HPF.ar(exc, freq * 3);                // mallet "vidro"
    sig = DynKlank.ar(`[
        [freq * 4.01, freq * 9.97, freq * 16.05, freq * 22.1],
        [0.5, 0.7, 0.5, 0.25],
        [1.5, 1.2, 0.8, 0.4]
    ], exc);
    sig = HPF.ar(sig, freq * 2);                // sem grave, so o vidro
    env = EnvGen.kr(Env([0, 1, 1, 0], [0.001, sustain.max(0.01), rel.max(1.0)], \exp),
                    doneAction: 2);
    sig = Pan2.ar(sig * env * amp * 0.32, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

// --- PIZZ / ABAFADO: a barra tocada e ABAFADA com a mao na hora. Ring
//     times curtissimos -> um "plink" seco e morto, sem cauda metalica.
SynthDef(\bancoPizz, { |freq=440, amp=0.35, rel=0.18, pan=0,
                        revBusSpring=0, revBusHall=0, revBusPlate=0,
                        sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig, exc, excEnv;
    excEnv = EnvGen.kr(Env.perc(0.0004, 0.01), doneAction: 0);
    exc = PinkNoise.ar(0.9) * excEnv;
    exc = HPF.ar(exc, freq * 1.5);
    sig = DynKlank.ar(`[
        [freq * 1.0, freq * 4.01, freq * 9.97],
        [1.0, 0.4, 0.15],
        [0.35, 0.2, 0.1]                        // ring CURTO = abafado/morto
    ], exc);
    env = EnvGen.kr(Env.perc(0.001, rel.max(0.05), 1, -4), doneAction: 2);
    sig = Pan2.ar(sig * env * amp * 0.5, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

// --- SINO (harmonicos): so parciais altas ressoando longo, como sino/taca.
//     Razoes de sino (2, 3, 4, 5.4, 10) com ring times longos -> badalada.
SynthDef(\bancoSino, { |freq=440, amp=0.3, rel=3.0, pan=0,
                        revBusSpring=0, revBusHall=0, revBusPlate=0,
                        sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig, exc, excEnv;
    excEnv = EnvGen.kr(Env.perc(0.0005, 0.01), doneAction: 0);
    exc = PinkNoise.ar(0.7) * excEnv;
    exc = HPF.ar(exc, freq * 1.5);
    sig = DynKlank.ar(`[
        [freq * 2.0, freq * 3.0, freq * 4.01, freq * 5.4, freq * 9.97],
        [0.5, 0.4, 0.5, 0.25, 0.15],
        [2.5, 2.0, 1.5, 1.0, 0.6]
    ], exc);
    env = EnvGen.kr(Env([0, 1, 1, 0], [0.001, 0.3, rel.max(1.0)], \exp), doneAction: 2);
    sig = Pan2.ar(sig * env * amp * 0.4, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

// --- MOTOR: o vibrafone tem um MOTOR que gira disquinhos na boca dos
//     tubos, criando o tremolo (a "ventoinha"). Aqui o motorRate (Hz) e o
//     motorDepth (profundidade) sao controlaveis -> mesma SynthDef serve
//     pro motor LENTO e pro RAPIDO (ver os presets motor_lento/rapido).
SynthDef(\bancoMotor, { |freq=440, amp=0.3, sustain=0.5, rel=2.5, pan=0,
                         motorRate=6, motorDepth=0.25,
                         revBusSpring=0, revBusHall=0, revBusPlate=0,
                         sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig, exc, excEnv, tremolo, masterRel;
    excEnv = EnvGen.kr(Env.perc(0.0005, 0.012), doneAction: 0);
    exc = PinkNoise.ar(0.8) * excEnv;
    exc = HPF.ar(exc, freq * 1.5);
    sig = DynKlank.ar(`[
        [freq * 1.0, freq * 4.01, freq * 9.97, freq * 16.05],
        [1.0, 0.5, 0.2, 0.06],
        [2.5, 1.4, 0.7, 0.35]
    ], exc);
    // a "ventoinha": LFO multiplicando a amplitude. rate = velocidade do motor.
    tremolo = SinOsc.kr(motorRate, mul: motorDepth, add: 1.0 - motorDepth);
    sig = sig * tremolo;
    masterRel = rel.max(1.5);
    env = EnvGen.kr(Env([0, 1, 1, 0], [0.001, sustain.max(0.01), masterRel], \exp),
                    doneAction: 2);
    sig = Pan2.ar(sig * env * amp * 0.35, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

// --- GONGO (ring mod): o vibrafone passado por uma RING MODULATION fixa,
//     que injeta parciais inarmonicas nao relacionadas a nota -> clangor
//     metalico de gongo/sino rachado. ringFreq nao segue a nota (de
//     proposito: e o que cria o "estranhamento" metalico).
SynthDef(\bancoGongo, { |freq=440, amp=0.3, sustain=0.5, rel=3.0, pan=0,
                         ringFreq=137,
                         revBusSpring=0, revBusHall=0, revBusPlate=0,
                         sendSpring=0, sendHall=0, sendPlate=0|
    var env, sig, exc, excEnv, masterRel, ringed;
    excEnv = EnvGen.kr(Env.perc(0.0005, 0.012), doneAction: 0);
    exc = PinkNoise.ar(0.8) * excEnv;
    exc = HPF.ar(exc, freq * 1.5);
    sig = DynKlank.ar(`[
        [freq * 1.0, freq * 4.01, freq * 9.97, freq * 16.05],
        [1.0, 0.5, 0.2, 0.06],
        [3.0, 1.8, 0.9, 0.45]
    ], exc);
    // mistura: 40% do som limpo + 60% modulado em anel -> gongo
    ringed = sig * SinOsc.ar(ringFreq);
    sig = (sig * 0.4) + (ringed * 0.6);
    masterRel = rel.max(1.5);
    env = EnvGen.kr(Env([0, 1, 1, 0], [0.001, sustain.max(0.01), masterRel], \exp),
                    doneAction: 2);
    sig = Pan2.ar(sig * env * amp * 0.33, pan.clip(-1, 1));
    Out.ar(0, sig);
    Out.ar(revBusSpring, sig * sendSpring);
    Out.ar(revBusHall,   sig * sendHall);
    Out.ar(revBusPlate,  sig * sendPlate);
}).add;

"[BANCO] SynthDefs de tecnica estendida carregados.".postln;

// =====================================================================
// O BANCO: nome -> (descricao, reverb sugerido, como tocar)
//
// Cada entrada tem:
//   desc   = o que e (texto pro post)
//   reverb = reverb sugerido (\spring \hall \plate \dry)
//   play   = a funcao que toca a nota. Recebe (freq, sS, sH, sP):
//            freq = a frequencia; sS/sH/sP = quanto mandar pra cada reverb.
// =====================================================================

~banco = Dictionary[

    // --- REFERENCIAS: o que a peca JA tem (pra comparar) ---
    \classico -> (
        desc: "ORIGINAL: serra+triangulo+seno com vibrato (o 1o synth)",
        reverb: \plate,
        play: { |freq, sS, sH, sP|
            Synth(\baralho, [\freq, freq, \amp, 0.3, \sustain, 0.5, \rel, 1.5, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \vibe_normal -> (
        desc: "VIBRAFONE padrao (DynKlank) -- o som ATUAL da cama",
        reverb: \plate,
        play: { |freq, sS, sH, sP|
            Synth(\baralhoVibeKlank, [\freq, freq, \amp, 0.32, \sustain, 0.4, \rel, 2.5, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \vibe_aditivo -> (
        desc: "VIBRAFONE aditivo (SinOscs) -- mais controlavel, menos vivo",
        reverb: \plate,
        play: { |freq, sS, sH, sP|
            Synth(\baralhoVibeAdd, [\freq, freq, \amp, 0.32, \sustain, 0.4, \rel, 2.5, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),

    // --- TECNICAS ESTENDIDAS NOVAS ---
    \arco -> (
        desc: "ARCO (bowed): a barra CANTA, sem ataque, etereo e sustentado",
        reverb: \hall,
        play: { |freq, sS, sH, sP|
            Synth(\bancoArco, [\freq, freq, \amp, 0.3, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \sul_tasto -> (
        desc: "SUL TASTO / flautando: doce e oco, so fundamental, sem brilho",
        reverb: \hall,
        play: { |freq, sS, sH, sP|
            Synth(\bancoFlautando, [\freq, freq, \amp, 0.32, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \sul_ponticello -> (
        desc: "SUL PONTICELLO / vidro: parciais altas, agudo e cortante",
        reverb: \spring,
        play: { |freq, sS, sH, sP|
            Synth(\bancoPont, [\freq, freq, \amp, 0.3, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \pizz_abafado -> (
        desc: "PIZZ / abafado: barra abafada com a mao, plink curto e morto",
        reverb: \dry,
        play: { |freq, sS, sH, sP|
            Synth(\bancoPizz, [\freq, freq, \amp, 0.35, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \sino -> (
        desc: "SINO (harmonicos): parciais altas ressoando longo, badalada",
        reverb: \plate,
        play: { |freq, sS, sH, sP|
            Synth(\bancoSino, [\freq, freq, \amp, 0.3, \pan, 0,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \motor_lento -> (
        desc: "MOTOR LENTO (~2Hz): ventoinha preguicosa, o som ondula devagar",
        reverb: \hall,
        play: { |freq, sS, sH, sP|
            Synth(\bancoMotor, [\freq, freq, \amp, 0.3, \sustain, 0.5, \rel, 2.5, \pan, 0,
                \motorRate, 2, \motorDepth, 0.35,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \motor_rapido -> (
        desc: "MOTOR RAPIDO (~11Hz): tremulo nervoso, vibrato de ventoinha",
        reverb: \plate,
        play: { |freq, sS, sH, sP|
            Synth(\bancoMotor, [\freq, freq, \amp, 0.3, \sustain, 0.5, \rel, 2.5, \pan, 0,
                \motorRate, 11, \motorDepth, 0.4,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
    \gongo -> (
        desc: "GONGO (ring mod): clangor inarmonico, metal rachado",
        reverb: \hall,
        play: { |freq, sS, sH, sP|
            Synth(\bancoGongo, [\freq, freq, \amp, 0.3, \sustain, 0.5, \rel, 3.0, \pan, 0,
                \ringFreq, 137,
                \revBusSpring, ~revBusSpring.index, \revBusHall, ~revBusHall.index,
                \revBusPlate, ~revBusPlate.index,
                \sendSpring, sS, \sendHall, sH, \sendPlate, sP]);
        }
    ),
];

// Ordem fixa do banco (Dictionary nao tem ordem; esta lista define a fila).
~bancoOrdem = [
    \classico, \vibe_normal, \vibe_aditivo,
    \arco, \sul_tasto, \sul_ponticello, \pizz_abafado, \sino,
    \motor_lento, \motor_rapido, \gongo
];

// Ajustes globais do banco:
~bancoFreq = 440;        // frequencia de teste padrao (440 Hz = La). Mude se quiser.
~bancoReverbMix = 0.5;   // quanto reverb (0 = seco, 1 = encharcado)

// Traduz o reverb sugerido (\spring/\hall/\plate/\dry) nos 3 "sends".
~bancoSends = { |rev|
    var sS = 0, sH = 0, sP = 0, m = ~bancoReverbMix;
    rev = rev ? \plate;
    case
        { rev == \spring } { sS = m }
        { rev == \hall }   { sH = m }
        { rev == \plate }  { sP = m }
        { rev == \dry }    { /* tudo zero */ };
    [sS, sH, sP];
};

// =====================================================================
// FUNCOES PRA OUVIR
// =====================================================================

// ~tocar.(\nome [, freq] [, reverb]) -> toca UMA sonoridade.
//   nome   = simbolo do banco (ex: \arco). Veja ~bancoLista.()
//   freq   = frequencia em Hz (opcional; padrao ~bancoFreq)
//   reverb = forca um reverb (\spring/\hall/\plate/\dry); opcional
//            (se omitir, usa o reverb sugerido daquela sonoridade)
~tocar = { |nome, freq, reverb|
    var entry, sends;
    if(~revBusPlate.isNil) {
        "[BANCO] rode o a_synth.scd primeiro (faltam os buses de reverb).".postln;
    } {
        entry = ~banco[nome];
        if(entry.isNil) {
            ("[BANCO] '" ++ nome ++ "' nao existe. Use ~bancoLista.() pra ver os nomes.").postln;
        } {
            freq = freq ? ~bancoFreq;
            sends = ~bancoSends.(reverb ? entry[\reverb]);
            ("[BANCO] " ++ nome ++ "  --  " ++ entry[\desc]).postln;
            entry[\play].(freq, sends[0], sends[1], sends[2]);
        };
    };
};

// ~bancoLista.() -> imprime todos os nomes + descricao, na ordem.
~bancoLista = {
    "".postln;
    "===== BANCO DE SONORIDADES =====".postln;
    ~bancoOrdem.do { |nome|
        var entry = ~banco[nome];
        if(entry.notNil) {
            ("  ~tocar.(\\" ++ nome ++ ")  --  " ++ entry[\desc]).postln;
        };
    };
    ("  (" ++ ~bancoOrdem.size ++ " sonoridades. ~bancoTodos.() toca todas em fila.)").postln;
    "".postln;
};

// ~bancoTodos.([freq] [, gap]) -> toca TODAS em fila, com rotulo no post.
//   gap = segundos entre uma e outra (padrao 3.5s).
~bancoTodos = { |freq, gap|
    freq = freq ? ~bancoFreq;
    gap = gap ? 3.5;
    Routine({
        "[BANCO] tocando todas em fila (Ctrl+. pra parar)...".postln;
        ~bancoOrdem.do { |nome|
            ~tocar.(nome, freq);
            gap.wait;
        };
        "[BANCO] fim da fila.".postln;
    }).play;
};

"[BANCO] pronto. Use ~bancoLista.() pra ver os nomes, ~tocar.(\\arco) pra ouvir.".postln;
)


// =====================================================================
// ATALHOS (cursor na linha + Ctrl+Enter)
// =====================================================================
// ~bancoLista.();                 // lista os nomes + descricao
// ~bancoTodos.();                 // toca todas em fila
// ~bancoTodos.(330, 2.5);         // todas, em 330 Hz, 2.5s entre cada
//
// ~tocar.(\vibe_normal);          // o som atual da peca (referencia)
// ~tocar.(\arco);                 // bowed
// ~tocar.(\sul_tasto);            // doce/flautando
// ~tocar.(\sul_ponticello);       // vidro/agudo
// ~tocar.(\pizz_abafado);         // seco
// ~tocar.(\sino);                 // badalada
// ~tocar.(\motor_lento);          // ventoinha lenta
// ~tocar.(\motor_rapido);         // ventoinha rapida
// ~tocar.(\gongo);                // clangor
//
// ~tocar.(\arco, 220);            // arco numa nota mais grave (220 Hz)
// ~tocar.(\sino, 660, \hall);     // sino agudo, forcando o reverb hall
// ~bancoFreq = 330;               // muda a nota de teste padrao
// ~bancoReverbMix = 0.8;          // mais reverb em tudo
