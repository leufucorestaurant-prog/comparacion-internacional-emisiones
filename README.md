# Comparación internacional de emisiones de CO₂

Proyecto Final Integrador – Programación Avanzada (Grupo 7).
Integrantes: Sebastián Quidel, Daniel Retamal, Luis Vázquez.
Repositorio: https://github.com/leufucorestaurant-prog/comparacion-internacional-emisiones

**Pregunta:** ¿Cómo se comparan las emisiones de CO₂ totales, per cápita y por
unidad de PIB entre países entre 1990 y 2024, y qué posición ocupa Chile frente
a América Latina y la OCDE?

## Datos

- **Fuente:** *CO₂ and Greenhouse Gas Emissions*, Our World in Data
  (https://github.com/owid/co2-data), licencia CC BY 4.0.
- **Original (no se modifica):** `datos/originales/owid-co2-data.csv`
  (50.411 filas × 79 columnas).
- **Procesado (lo genera `main.py`):** `datos/procesados/dataset_limpio.csv`
  (7.539 filas × 25 columnas; 216 países, 1990–2024).

Para volver a descargar el original:

```bash
curl -L -o datos/originales/owid-co2-data.csv https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv
```

## Ejecución

Desde la raíz del proyecto:

```bash
pip install -r requirements.txt
python main.py
```

El programa usa solo rutas relativas. Al terminar genera:

- `datos/procesados/dataset_limpio.csv`: conjunto limpio y validado.
- `reportes/evidencias/*.csv`: diagnóstico inicial y final, registro de
  limpieza, tratamiento de nulos y comparación antes/después.

Si alguna validación falla, el programa se detiene y no exporta el archivo.

## Pipeline

```
Datos originales → Carga → Diagnóstico → Limpieza → Tratamiento de nulos
→ Transformaciones → Validación → Exportación
```

| Archivo                   | Responsabilidad                                |
|---------------------------|------------------------------------------------|
| `src/carga.py`            | Lectura y carga del conjunto                   |
| `src/limpieza.py`         | Nulos, duplicados y normalización              |
| `src/transformaciones.py` | Conversión y creación de variables             |
| `src/validaciones.py`     | Diagnóstico y comprobación de columnas, tipos y rangos |
| `main.py`                 | Ejecución ordenada del pipeline                |

## Principales decisiones

- Se eliminan los 35 agregados (World, continentes, grupos de ingreso,
  versiones “(GCP)”) para no contar emisiones dos veces. Kosovo se conserva
  asignándole el código XKX.
- Se analiza el período 1990–2024.
- Se eliminan las filas sin `co2` (Mónaco, San Marino y Vaticano se reportan
  dentro de Francia e Italia).
- En combustibles se imputa 0 solo cuando el `co2` total ya cuadra con la suma
  de los demás componentes; PIB, consumo y GEI se mantienen nulos.
- Kuwait 1991 (incendios petroleros) se marca con `valor_atipico` y se anulan
  sus indicadores per cápita y por PIB.

## Reportes

- `reportes/avance_1.pdf`: definición del problema y carga inicial.
- `reportes/avance_2.pdf`: limpieza, nulos, transformaciones y validación.
