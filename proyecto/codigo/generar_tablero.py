"""Genera index.html con las métricas de los PARTICIPANTES de todas las sesiones procesadas en NAIRA.

Los participantes se identifican solo por su código de enrolamiento (P1, P2, …): el tablero no incluye nombres reales.

Lee (sin modificar nada dentro de NAIRA):
  - NAIRA/outputs/metrics_all.csv            tabla global que NAIRA actualiza al final de cada corrida
  - NAIRA/outputs/<grupo>/<fuente>/02_enrollment/segments_identified.json   tramos de voz de cada participante
  - NAIRA/outputs/<grupo>/<fuente>/00_ingest/qc.json                        duración de la grabación
  - NAIRA/configs/metrics_catalog.yaml       nombre, categoría y estado de cada variable
  - NAIRA/docs/05_guias/metricas_explicadas.md   «qué significa», «cómo leerla» y código de la tesis de cada variable
  - NAIRA/sessions/*.yaml                    sexo de cada participante (para comparar el tono entre personas del mismo sexo)
  - ../datos/gqm.yaml                        metodología GQM de la tesis: subproceso → objetivo → preguntas (las métricas de
                                             cada pregunta salen de pregunta_gqm en el catálogo)

Uso, después de procesar una sesión o grupo nuevo, desde esta carpeta (proyecto/codigo):
    conda run -n naira-audio python generar_tablero.py
Escribe ../../index.html, el único archivo que queda a la vista (se llama index.html para que GitHub Pages lo abra al entrar al repositorio). Se abre con doble clic y lleva Plotly
incrustado, así que es un único archivo y funciona aunque se copie a otro computador.
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path

import yaml

# La carpeta está ordenada por lo que es cada archivo: codigo/ (estos .py), diseno/ (la plantilla
# y Plotly) y datos/ (la metodología GQM y los textos de las síntesis). Afuera solo queda index.html.
CODIGO = Path(__file__).resolve().parent                 # Tablero_NAIRA - publico/proyecto/codigo
PROYECTO = CODIGO.parent
PUBLICO = PROYECTO.parent                                # ahí queda el tablero, solo
# NAIRA vive fuera de este repositorio. Por omisión se busca como carpeta hermana; si está en otro
# sitio (por ejemplo cuando este repositorio se clona en otra ruta), se indica con la variable de
# entorno NAIRA_DIR: NAIRA_DIR="C:/ruta/a/NAIRA" python generar_tablero.py
NAIRA = Path(os.environ.get("NAIRA_DIR") or (PUBLICO.parent / "NAIRA")).expanduser()
CSV = NAIRA / "outputs" / "metrics_all.csv"
CATALOGO = NAIRA / "configs" / "metrics_catalog.yaml"
EXPLICADAS = NAIRA / "docs" / "05_guias" / "metricas_explicadas.md"
SESIONES = NAIRA / "sessions"
PLANTILLA = PROYECTO / "diseno" / "plantilla.html"
PLOTLY = PROYECTO / "diseno" / "lib" / "plotly-2.35.2.min.js"   # se incrusta en el tablero: un solo archivo
GQM = PROYECTO / "datos" / "gqm.yaml"
PRESCRIPCIONES = PROYECTO / "datos" / "prescripciones.json"     # síntesis redactadas con IA (Claude); solo códigos
SALIDA = PUBLICO / "index.html"             # index.html: GitHub Pages lo sirve al abrir el repositorio
# Si un grupo se grabó con los dos micrófonos, el tablero usa UNA sola fuente: la primera de esta lista que tenga resultados.
# (La comparación entre micrófonos está aparte, en ../../../Comparativo_Microfonos.)
FUENTE_PREFERIDA = ["zoom01", "jabra01"]


def sesion_grupo(session_id: str) -> tuple[str, str]:
    m = re.match(r"sesion(\d+)_grupo(\d+)", session_id)
    return (f"Sesión {m.group(1)}", f"Grupo {m.group(2)}") if m else (session_id, "—")


def limpiar(t: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


# metricas_explicadas.md mezcla dos públicos: lo que el usuario final necesita para leer un gráfico y las
# salvedades de quien calcula la métrica. El tablero es para el usuario final, así que estas últimas se
# quitan de «qué significa» y «cómo leerla»: no le sirve saber que Whisper omite palabras cortas ni cómo
# se llama internamente una marca de calidad. Lo que sí importa sigue estando donde corresponde: el estado
# de cada métrica (exploratoria, sustituto) se ve como etiqueta en su tarjeta; las salvedades de método,
# en «Interpretación y limitaciones» de cada pregunta GQM y en las notas metodológicas del pie.
NOTAS_TECNICAS = [
    (r"\s*Ojo:[^.]*\.", ""),                                           # «Ojo: Whisper a veces omite…»
    (r"\s*(?:Exploratoria|Sustituto|Provisional|Experimental):[^.]*\.", ""),   # ya está como etiqueta
    (r"\s*Si la cobertura es baja[^.]*\.",                             # la cautela sí importa; el código de la marca, no
     " Si el léxico cubre pocas de sus palabras, el valor se apoya en una base pequeña y conviene leerlo con cautela."),
    (r"\s*Lleva su cobertura\.", ""),
    (r" ?\(marca [a-z_]+(?:,[^)]*)?\)", ""),                           # «(marca no_valida_por_dsp)»
]


def sin_notas_tecnicas(t: str) -> str:
    """Quita de un texto las notas dirigidas a quien desarrolla el tablero, no a quien lo lee."""
    for patron, reemplazo in NOTAS_TECNICAS:
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def explicaciones() -> dict[str, dict]:
    """Por variable: qué significa, cómo leerla y códigos de la tesis, desde metricas_explicadas.md."""
    if not EXPLICADAS.exists():
        return {}
    out: dict[str, dict] = {}
    bloques = re.split(r"\n(?=### )", EXPLICADAS.read_text(encoding="utf-8"))
    for b in bloques:
        cab = b.split("\n", 1)[0]
        campos: dict[str, str] = {}
        actual = None
        for linea in b.split("\n")[1:]:
            m = re.match(r"- \*\*(.+?):\*\* ?(.*)", linea)
            if m:
                actual = m.group(1).strip()
                campos[actual] = m.group(2)
            elif actual and linea.startswith("  "):
                campos[actual] += " " + linea.strip()
            elif not linea.strip():
                actual = None
        m = re.match(r"### ([A-Z0-9_]+) —", cab)
        if m:
            tesis = re.findall(r"(TdM\d+|EMP\d+|PS\d+|CS\d+)", campos.get("Tesis", ""))
            out[m.group(1)] = {"que": limpiar(campos.get("Qué significa", "")), "leer": limpiar(campos.get("Cómo leerla", "")), "tesis": tesis}
            continue
        # bloques en tabla (pronombres, palabras emocionales): una fila por variable
        intro = limpiar(" ".join(l for l in b.split("\n")[1:] if l and not l.startswith(("|", "-"))).split(". ")[0] + ".")
        leer = limpiar(campos.get("Cómo leerlas", ""))
        for fila in re.findall(r"^\| `([A-Z0-9_]+)` \|(.+)$", b, flags=re.M):
            celdas = [c.strip() for c in fila[1].split("|") if c.strip()]
            tesis = re.findall(r"(TdM\d+|EMP\d+|PS\d+|CS\d+)", celdas[0]) if celdas else []
            que = celdas[3] if len(celdas) > 3 else ""
            if len(celdas) > 4 and celdas[4] != "—":
                que += f" (por ejemplo: {celdas[4]})"
            out[fila[0]] = {"que": limpiar(que[:1].upper() + que[1:] + ". " + intro), "leer": leer, "tesis": tesis}
    return out


def sexos() -> dict[str, str]:
    out = {}
    for p in SESIONES.glob("*.yaml"):
        try:
            t = p.read_text(encoding="utf-8")
            if "DESCARTADO" in t[:400]:
                continue
            s = yaml.safe_load(t)
        except Exception:
            continue
        for r in (s or {}).get("roster", []) or []:
            if r.get("sex"):
                out[f"{s.get('session_id')}|{r['speaker_id']}"] = r["sex"]
    return out


def presentes() -> list[list[str]]:
    """Participantes del roster de cada grupo real (aunque no se haya captado su voz)."""
    out = []
    for p in sorted(SESIONES.glob("sesion*.yaml")):
        t = p.read_text(encoding="utf-8")
        if "DESCARTADO" in t[:400]:
            continue
        s = yaml.safe_load(t) or {}
        out += [[s["session_id"], r["speaker_id"]] for r in s.get("roster", []) if r.get("role") == "participante"]
    return out


def segmentos(elegida: dict[str, str]) -> dict[str, dict]:
    """Tramos de voz de cada participante por grupo, para la línea de tiempo del Resumen.

    Lee (sin modificarlos) 02_enrollment/segments_identified.json de la fuente elegida de cada grupo
    y 00_ingest/qc.json para la duración de la grabación. Igual que el resto del tablero, conserva
    solo el rol «participante»: moderadores, técnica, acompañantes y voces sin atribuir quedan fuera.
    """
    out: dict[str, dict] = {}
    for sid, dev in sorted(elegida.items()):
        base = NAIRA / "outputs" / sid / dev
        f = base / "02_enrollment" / "segments_identified.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8")) or {}
        tramos: dict[str, list] = {}
        ultimo = 0.0
        for s in d.get("segments", []):
            if "start" not in s or "end" not in s:
                continue
            ini, fin = float(s["start"]), float(s["end"])
            ultimo = max(ultimo, fin)
            if s.get("role") != "participante" or not s.get("speaker_id"):
                continue
            tramos.setdefault(s["speaker_id"], []).append([round(ini, 1), round(fin, 1)])
        if not tramos:
            continue
        qc = base / "00_ingest" / "qc.json"
        dur = float((json.loads(qc.read_text(encoding="utf-8")) or {}).get("duration_s") or 0) if qc.exists() else 0.0
        out[sid] = {"dur": round(dur or ultimo, 1), "tramos": {k: tramos[k] for k in sorted(tramos)}}
    return out


def main() -> None:
    catalogo = {v["id"]: {"nombre": v["nombre"], "familia": v["familia"], "estado": v["estado"], "definicion": v.get("definicion", ""),
                          "preguntas": v.get("pregunta_gqm") or [], "motivo": v.get("motivo_estado") or "", "metodo": v.get("metodo", ""),
                          "insumos": v.get("insumos") or [], "unidad": v.get("unidad", ""), "micro": v.get("fuente_audio_valida") == "h2n"}
                for v in yaml.safe_load(CATALOGO.read_text(encoding="utf-8"))["variables"]
                if v["estado"] != "no_disponible"}      # fuera del modelo de métricas: requieren un insumo que las sesiones no produjeron
    gqm = yaml.safe_load(GQM.read_text(encoding="utf-8"))
    for d in gqm["subprocesos"]:                     # métricas de cada pregunta, desde el catálogo
        todas_dim = [k for k, v in catalogo.items() if any(q.startswith(d["id"] + " ") for q in v["preguntas"])]
        d["preguntas"] = [q for q in d["preguntas"] if not q.get("asociacion")]   # la pregunta de asociación con el desempeño no se muestra
        for q in d["preguntas"]:
            q["metricas"] = [k for k, v in catalogo.items() if f'{d["id"]} {q["id"]}' in v["preguntas"]]
        d["metricas"] = todas_dim                    # lista completa del subproceso (tabla de todos los valores)
        d["n_metricas"] = len(todas_dim)
    gqm.pop("nota_asociacion", None)
    with CSV.open(encoding="utf-8") as f:
        todas = [r for r in csv.DictReader(f)
                 if r["role"] == "participante"        # sin moderadores, técnica, acompañantes ni voces desconocidas
                 and r["metric_id"] in catalogo]       # sin las variables descartadas del modelo de métricas
    fuentes: dict[str, set] = {}
    for r in todas:
        fuentes.setdefault(r["session_id"], set()).add(r["source_id"])
    rango = lambda s: FUENTE_PREFERIDA.index(s) if s in FUENTE_PREFERIDA else len(FUENTE_PREFERIDA)
    elegida = {sid: min(srcs, key=lambda s: (rango(s), s)) for sid, srcs in fuentes.items()}
    filas = []
    for r in todas:
        if r["source_id"] != elegida[r["session_id"]]:
            continue
        ses, gru = sesion_grupo(r["session_id"])
        v = r["value"]
        filas.append([r["session_id"], ses, gru, r["speaker_id"], r["device"], r["metric_id"], r["component"],
                      float(v) if v not in ("", "nan") else None, r["unit"], r["quality_flags"]])
    exp = {k: v for k, v in explicaciones().items() if k in catalogo}   # solo las variables del modelo de métricas
    for k, v in catalogo.items():                    # respaldo: la definición del catálogo
        exp.setdefault(k, {"que": v["definicion"], "leer": "", "tesis": []})
    notas_quitadas = 0                               # se informa abajo: si NAIRA cambia la redacción, el patrón
    for v in exp.values():                           # deja de coincidir y el aviso volvería a salir sin avisar
        for campo in ("que", "leer"):
            limpio = sin_notas_tecnicas(v[campo])
            if limpio != v[campo]:
                notas_quitadas += 1
                v[campo] = limpio
    datos = {"generado": datetime.now().strftime("%d-%m-%Y %H:%M"), "catalogo": catalogo, "explicacion": exp, "sexo": sexos(), "gqm": gqm,
             "prescripciones": json.loads(PRESCRIPCIONES.read_text(encoding="utf-8")) if PRESCRIPCIONES.exists() else None,
             "presentes": presentes(), "segmentos": segmentos(elegida),
             "columnas": ["sid", "sesion", "grupo", "p", "dev", "m", "c", "v", "u", "f"], "filas": filas}
    html = PLANTILLA.read_text(encoding="utf-8").replace("/*__DATOS__*/null", json.dumps(datos, ensure_ascii=False))
    etiqueta = '<script src="lib/plotly-2.35.2.min.js"></script>'
    assert html.count(etiqueta) == 1, "la plantilla ya no enlaza Plotly como esperaba"
    html = html.replace(etiqueta, "<script>" + PLOTLY.read_text(encoding="utf-8") + "</script>")
    SALIDA.write_text(html, encoding="utf-8")
    personas = {(x[0], x[3]) for x in filas}
    print("fuente por grupo: " + ", ".join(f"{k}={v}" for k, v in sorted(elegida.items())))
    print(f"tablero: {SALIDA}  ({SALIDA.stat().st_size / 1e6:.1f} MB, un solo archivo)\n{len(personas)} participante-sesión, {len({x[0] for x in filas})} grupos, {len(filas)} valores, "
          f"{sum(1 for k in catalogo if exp[k]['que'])}/{len(catalogo)} variables con explicación, {notas_quitadas} notas técnicas ocultas al usuario final\n"
          "GQM: " + ", ".join(f'{d["id"]} {d["n_metricas"]} métricas' for d in gqm["subprocesos"]))


if __name__ == "__main__":
    main()
