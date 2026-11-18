"""Expediente de cada grupo (y su sesión) para redactar las prescripciones de grupo y de sesión del tablero.

Usa la misma fuente que el tablero (Zoom si existe, si no Jabra). Imprime, por grupo: participación del equipo frente a
las participantes, reparto entre participantes, cómo se encadenan los turnos (participante → participante, equipo →
participante), solapamiento y fragmentos repartidos a lo largo de la sesión. Solo códigos, nunca nombres.
Uso: conda run -n naira-audio python expediente_grupos.py salida.md
"""
import bisect, collections, csv, json, sys
from pathlib import Path
import yaml

N = Path(__file__).resolve().parents[3] / "NAIRA"   # codigo -> proyecto -> Tablero_NAIRA - publico -> carpeta que contiene NAIRA
O = N / "outputs"
PREF = ["zoom01", "jabra01"]
rol = lambda s: "P" if s.startswith("P") else "equipo" if s[:1] in "MTA" else "?"
res = []
for ses in sorted((N / "sessions").glob("sesion*.yaml")):
    t = ses.read_text(encoding="utf-8")
    if "DESCARTADO" in t[:400]:
        continue
    s = yaml.safe_load(t); sid = s["session_id"]
    src = next((x for x in PREF if (O / sid / x / "05_units/turns.json").exists()), None)
    if not src:
        continue
    d = O / sid / src
    T = json.load(open(d / "05_units/turns.json", encoding="utf-8"))["turns"]
    W = sorted((w["start"], w.get("speaker_id") or "DESCONOCIDO", (w.get("word") or w.get("text") or "").strip())
               for w in json.load(open(d / "04_alignment/words.json", encoding="utf-8"))["words"])
    ini = [w[0] for w in W]
    segs = json.load(open(d / "02_enrollment/segments_identified.json", encoding="utf-8"))["segments"]
    dur = json.load(open(d / "00_ingest/qc.json", encoding="utf-8"))["duration_s"]
    habla = collections.Counter()
    for g in segs:
        habla[g.get("speaker_id") or "DESCONOCIDO"] += g["end"] - g["start"]
    tot = sum(habla.values()) or 1
    part = {k: v for k, v in habla.items() if k.startswith("P")}
    eq = sum(v for k, v in habla.items() if rol(k) == "equipo")
    seq = [x["speaker_id"] for x in T if x["speaker_id"] not in ("DESCONOCIDO", None)]
    trans = collections.Counter()
    for a, b in zip(seq, seq[1:]):
        if a != b:
            trans[f"{rol(a)}→{rol(b)}"] += 1
    ntr = sum(trans.values()) or 1
    ov = sum(float(r["value"]) for r in csv.DictReader(open(d / "07_metrics/metrics_long.csv", encoding="utf-8"))
             if r["speaker_id"] == "SESION" and r["metric_id"] == "CNV_OVERLAP" and r["component"] == "segundos")
    presentes = [r["speaker_id"] for r in s["roster"] if r["role"] == "participante"]
    lin = [f"### {sid} · micrófono {src} · {dur/60:.0f} min",
           f"- Participantes en el roster: {', '.join(presentes)}; con voz captada: {', '.join(sorted(part)) or 'ninguna'}",
           f"- Habla: participantes {100*sum(part.values())/tot:.0f} %, equipo {100*eq/tot:.0f} %, sin atribuir {100*habla['DESCONOCIDO']/tot:.0f} %",
           "- Reparto entre participantes: " + ", ".join(f"{k} {100*v/(sum(part.values()) or 1):.0f} %" for k, v in sorted(part.items(), key=lambda x: -x[1])),
           "- Encadenamiento de turnos: " + ", ".join(f"{k} {100*v/ntr:.0f} %" for k, v in trans.most_common()),
           f"- Habla superpuesta: {ov/60:.1f} min ({100*ov/dur:.0f} % de la sesión)",
           "- Fragmentos a lo largo de la sesión (el turno más largo de cada tramo; [hablante]):"]
    ventanas = 24
    for i in range(ventanas):
        a0, b0 = dur * i / ventanas, dur * (i + 1) / ventanas
        cand = []
        for x in T:
            if not (a0 <= x["start"] < b0) or x["speaker_id"] in ("DESCONOCIDO", None):
                continue
            a, b = bisect.bisect_left(ini, x["start"] - .05), bisect.bisect_right(ini, x["end"] + .05)
            txt = " ".join(w[2] for w in W[a:b] if w[1] == x["speaker_id"]).split()
            if txt:
                cand.append((len(txt), x["speaker_id"], " ".join(txt[:40])))
        if cand:
            n, sp, txt = max(cand)
            lin.append(f"  [{int(a0//60):02d} min · {sp if sp.startswith('P') else 'equipo'}] {txt}")
    res.append("\n".join(lin))
Path(sys.argv[1]).write_text("\n\n".join(res), encoding="utf-8")
print(len(res), "grupos")
