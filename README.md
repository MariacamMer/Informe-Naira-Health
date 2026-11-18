# Tablero NAIRA

Métricas computacionales del habla de adultos mayores en sesiones grupales, organizadas según la
metodología GQM de la tesis.

**→ [Abrir el tablero](https://mariacammer.github.io/Informe-Naira-Health/)**

El tablero es un único archivo HTML autocontenido (`index.html`): lleva Plotly incrustado, no pide nada a
internet y se abre igual con doble clic o enviándolo por correo.

## Qué contiene

Un **Resumen** con las cifras generales, la síntesis descriptiva de cada grupo y de cada participante, el
reparto del habla y la tabla de participaciones; y una pestaña por cada **subproceso de la cognición social**
(teoría de la mente, empatía, percepción social, conducta social). Dentro de cada subproceso, cada pregunta GQM
se presenta como un recorrido de cinco pasos: procedimiento de análisis, datos utilizados, métricas
computacionales, resultado e interpretación.

Desde el menú **Opciones** se puede reorganizar las pestañas por familia de variables (temporales,
conversacionales, léxicas, semánticas, acústicas, prosódicas), cambiar el tema y exportar lo filtrado a
Markdown, JSON o CSV.

## Privacidad

Los participantes se identifican **solo por su código de enrolamiento** (P01, P02, …). El archivo no contiene
nombres reales en ningún momento: ni en los gráficos, ni en las tablas, ni en las síntesis, ni en las
exportaciones.

Aun así, el tablero describe a personas identificables por su código, así que es de uso interno del equipo. Si
la página no debe ser pública, conviene un repositorio privado en lugar de GitHub Pages abierto.

Las síntesis descriptivas están redactadas con IA a partir de las métricas, de fragmentos de transcripción y
de la documentación del proyecto. Son un complemento del tablero: no forman parte del flujo de NAIRA ni de la
tesis, y no constituyen diagnóstico.

## Cómo se regenera

El tablero se arma a partir de los resultados de NAIRA, que vive fuera de este repositorio:

```
cd proyecto/codigo
conda run -n naira-audio python generar_tablero.py
```

El script lee `NAIRA/outputs/metrics_all.csv` y el resto de los insumos **sin modificar nada dentro de NAIRA**, y
escribe `index.html` en la raíz.

## Estructura

| Ruta | Qué es |
|---|---|
| `index.html` | El tablero, listo para abrir. Lo único que queda a la vista. |
| `proyecto/codigo/` | `generar_tablero.py` y los dos scripts que preparan el material para redactar las síntesis. |
| `proyecto/diseno/` | `plantilla.html` (estructura, estilos y gráficos) y la copia local de Plotly 2.35.2. |
| `proyecto/datos/` | `gqm.yaml` (metodología GQM) y `prescripciones.json` (textos de las síntesis). |
| `proyecto/LEEME.txt` | Documentación detallada y registro de cambios. |

> `index.html` se genera: no se edita a mano. Los cambios de diseño o de texto van en
> `proyecto/diseno/plantilla.html` y se vuelve a ejecutar el generador.

## Publicar los cambios

Una sola vez, en GitHub: **Settings → Pages → Source: Deploy from a branch → rama `main`, carpeta `/ (root)`**.
Después, cada `git push` a `main` actualiza la página publicada en uno o dos minutos.
