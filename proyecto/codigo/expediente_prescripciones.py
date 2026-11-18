"""Expediente por participante-sesión para redactar prescripciones: niveles cualitativos (percentil interno) + fragmentos."""
import csv, json, sys, collections, bisect, yaml
from pathlib import Path
N = Path(__file__).resolve().parents[3] / 'NAIRA'   # codigo -> proyecto -> Tablero_NAIRA - publico -> carpeta que contiene NAIRA
O = N / 'outputs'
PREF = ["zoom01", "jabra01"]
rows = [r for r in csv.DictReader(open(O / 'metrics_all.csv', encoding='utf-8')) if r['role'] == 'participante' and r['session_id'].startswith('sesion')]
src = collections.defaultdict(set)
for r in rows: src[r['session_id']].add(r['source_id'])
eleg = {s: min(v, key=lambda x: PREF.index(x) if x in PREF else 9) for s, v in src.items()}
# (pregunta, clave, etiqueta); acústica/prosodia: referencia dentro del mismo micrófono; F0 media: dentro del mismo sexo
Q = [
 ("CS Q1 producción verbal", [("LEX_WORD_COUNT.n", "cantidad de palabras"), ("LEX_TYPES.n", "vocabulario distinto"), ("LEX_TTR.mattr_50", "riqueza léxica"), ("LEX_MLU.palabras_enunciado", "longitud de enunciados")]),
 ("CS Q2 organización semántica", [("SEM_SIMILARITY.media", "conexión temática con el turno anterior"), ("SEM_MAIN_CONCEPTS.pct", "conceptos centrales de la actividad mencionados")]),
 ("CS Q3 participación temporal", [("TMP_SPEECH_DUR.pct_sesion", "proporción del habla del grupo"), ("TMP_SPEECH_RATE.palabras_min", "tasa de habla")]),
 ("CS Q4 coordinación conversacional", [("CNV_TURNS.por_10min", "frecuencia de turnos"), ("CNV_UTTERANCES.n", "número de enunciados"), ("CNV_BACKCHANNEL.por_10min", "señales de escucha (asentimientos breves)"),
   ("CNV_OVERLAP.pct_habla", "habla superpuesta"), ("CNV_INTERRUPT.como_interruptor_por_10min", "interrumpe a otros"), ("CNV_INTERRUPT.como_interrumpido_por_10min", "es interrumpida"), ("CNV_REPAIR_INIT.por_10min", "pide aclaraciones/reparaciones")]),
 ("ToM Q1 elaboración", [("LEX_MTLD.mtld", "diversidad léxica sostenida")]),
 ("ToM Q2 referencia y perspectiva", [("LEX_PRON_1SG.pct", "referencias a sí misma (yo)"), ("LEX_PRON_1PL.pct", "referencias al grupo (nosotros)"), ("LEX_PRON_2.pct", "referencias al interlocutor (tú/usted)"),
   ("LEX_PRON_3SG.pct", "referencias a terceros (él/ella)"), ("LEX_PRON_PERS.pct", "pronombres personales"), ("LEX_PRON_TOTAL.pct", "pronombres en total")]),
 ("ToM Q3 estados mentales", [("SEM_MENTAL_TERMS.por_100", "términos de estados mentales"), ("SEM_MENTAL_TERMS.cognicion", "verbos de pensar/saber"), ("SEM_MENTAL_TERMS.emocion", "verbos de sentir"), ("SEM_MENTAL_TERMS.volicion", "verbos de querer")]),
 ("EMP Q1 léxico emocional", [("LEX_EMO_WORDS.pct", "palabras emocionales"), ("LEX_EMO_POS_PCT.pct", "emoción positiva"), ("LEX_EMO_NEG_PCT.pct", "emoción negativa")]),
 ("EMP Q2 contenido afectivo", [("AFF_SENTIMENT.pct_pos", "enunciados de tono positivo"), ("AFF_SENTIMENT.pct_neg", "enunciados de tono negativo"), ("AFF_SENTIMENT.pct_neu", "enunciados neutros"), ("AFF_LEX_VALENCE.media", "agrado del vocabulario")]),
 ("EMP Q3 / PS Q2 voz", [("ACU_ENERGY_STATS.de_bruto", "variación de la energía vocal"), ("ACU_JITTER.local_pct", "inestabilidad del tono (jitter)"), ("ACU_SHIMMER.local_pct", "inestabilidad de la intensidad (shimmer)"),
   ("ACU_HNR.db", "claridad de la voz (armónicos/ruido)"), ("ACU_INTENSITY_MEAN.db", "volumen de voz")]),
 ("PS Q1 dinámica temporal", [("TMP_ARTIC_RATE.silabas_s", "velocidad de articulación")]),
 ("PS Q3 prosodia", [("PRO_F0_MEAN.hz", "tono medio (vs. mismo sexo)"), ("PRO_F0_SD.st", "variación melódica"), ("PRO_F0.rango_st", "rango tonal"), ("PRO_EMO_PROSODY.arousal_media", "activación emocional en la voz"), ("PRO_EMO_PROSODY.valence_media", "valencia emocional en la voz")]),
 ("PS Q4 afectividad", [("AFF_AROUSAL.texto", "activación emocional del discurso"), ("AFF_VALENCE.texto", "balance emocional del discurso")]),
]
POR_MIC = ("ACU_", "PRO_", "AFF_AROUSAL.voz", "AFF_VALENCE.voz")
sexo = {}
roster = collections.defaultdict(set)
for p in (N / 'sessions').glob('sesion*.yaml'):
    t = p.read_text(encoding='utf-8')
    if 'DESCARTADO' in t[:400]: continue
    s = yaml.safe_load(t)
    for r in s.get('roster', []):
        if r['role'] == 'participante':
            roster[s['session_id']].add(r['speaker_id']); sexo[(s['session_id'], r['speaker_id'])] = r.get('sex', '')
V = collections.defaultdict(dict); dev = {}; prov = set()
for r in rows:
    if r['source_id'] != eleg[r['session_id']]: continue
    k = (r['session_id'], r['speaker_id']); dev[k] = r['device']
    if 'perfil_provisional' in (r['quality_flags'] or ''): prov.add(k)
    if r['value'] not in ('', 'nan'): V[k][f"{r['metric_id']}.{r['component']}"] = float(r['value'])
ok = [k for k in V if V[k].get('LEX_WORD_COUNT.n', 0) >= 50]
def nivel(k, key):
    v = V[k].get(key)
    if v is None: return None
    grupo = [j for j in ok if (not key.startswith(POR_MIC) or dev[j] == dev[k]) and (key != 'PRO_F0_MEAN.hz' or sexo.get(j) == sexo.get(k))]
    xs = sorted(V[j][key] for j in grupo if key in V[j])
    if len(xs) < 4: return "sin referencia suficiente"
    p = (bisect.bisect_left(xs, v) + bisect.bisect_right(xs, v)) / 2 / len(xs)
    return "muy bajo" if p < .1 else "bajo" if p < .3 else "medio" if p <= .7 else "alto" if p <= .9 else "muy alto"
def turnos(sid, src, p, maxn=14, maxw=45):
    d = O / sid / src
    T = json.load(open(d / '05_units/turns.json', encoding='utf-8'))['turns']
    W = json.load(open(d / '04_alignment/words.json', encoding='utf-8'))['words']
    ws = sorted((w['start'], w.get('speaker_id'), w.get('word') or w.get('text') or '') for w in W)
    ini = [w[0] for w in ws]
    out = []
    for i, t in enumerate(T):
        if t['speaker_id'] != p: continue
        a, b = bisect.bisect_left(ini, t['start'] - .05), bisect.bisect_right(ini, t['end'] + .05)
        txt = " ".join(w[2].strip() for w in ws[a:b] if w[1] == p).strip()
        if not txt: continue
        prev = next((T[j]['speaker_id'] for j in range(i - 1, -1, -1) if T[j]['speaker_id'] != p), None)
        quien = "moderador/a" if prev and prev.startswith('M') else "otra participante" if prev and prev.startswith('P') else "equipo/otro"
        out.append((len(txt.split()), t['start'], quien, " ".join(txt.split()[:maxw])))
    largos = sorted(out, reverse=True)[:maxn]
    return sorted(largos, key=lambda x: x[1]), len(out)
res = []
for sid in sorted(roster):
    for p in sorted(roster[sid]):
        k = (sid, p)
        h = f"### {sid} · {p} · sexo {sexo.get(k) or '?'}"
        if k not in V or V[k].get('LEX_WORD_COUNT.n') is None:
            res.append(h + "\nSIN DATOS: estuvo en el grupo pero no se captó su voz."); continue
        w = V[k]['LEX_WORD_COUNT.n']
        h += f" · micrófono {'Zoom H2n' if dev[k]=='h2n' else 'Jabra'}" + (" · PERFIL DE VOZ PROVISIONAL" if k in prov else "") + (" · DATOS ESCASOS (<50 palabras)" if w < 50 else "")
        lin = [h]
        for q, items in Q:
            lin.append(f"- {q}: " + "; ".join(f"{lab} {nivel(k, key)}" for key, lab in items if nivel(k, key)))
        src = eleg[sid]
        fr, n = turnos(sid, src, p)
        lin.append(f"- Fragmentos ({n} turnos en total; los más largos, en orden; entre corchetes quién habló antes):")
        lin += [f"  [{q}] {t}" for _, _, q, t in fr]
        res.append("\n".join(lin))
Path(sys.argv[1]).write_text("\n\n".join(res), encoding="utf-8")
print(len(res), "fichas")
