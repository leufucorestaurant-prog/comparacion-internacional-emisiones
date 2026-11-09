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
- `resultados/estadisticas.csv`: estadísticas descriptivas (n, media, mediana,
  mínimo, máximo, rango, desviación estándar, cuartiles).
- `resultados/frecuencias.csv`: frecuencias de las variables categóricas.
- `resultados/indicadores.csv`: diez indicadores con método e interpretación.
- `resultados/graficos/grafico_01.png` a `grafico_05.png`: gráficos del análisis.

Si alguna validación falla, el programa se detiene y no exporta el archivo.

## Pipeline

```
Datos originales → Carga → Diagnóstico → Limpieza → Tratamiento de nulos
→ Transformaciones → Validación → Exportación
→ Estadísticas descriptivas → Indicadores → Gráficos
```

| Archivo                   | Responsabilidad                                |
|---------------------------|------------------------------------------------|
| `src/carga.py`            | Lectura y carga del conjunto                   |
| `src/limpieza.py`         | Nulos, duplicados y normalización              |
| `src/transformaciones.py` | Conversión y creación de variables             |
| `src/validaciones.py`     | Diagnóstico y comprobación de columnas, tipos y rangos |
| `src/estadisticas.py`     | Estadísticas descriptivas y frecuencias        |
| `src/indicadores.py`      | Indicadores automatizados del proyecto         |
| `src/visualizaciones.py`  | Gráficos con Matplotlib Pyplot (PNG)           |
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
- `reportes/avance_3.pdf`: estadística descriptiva, indicadores y gráficos.

## Gráficos (Avance 3)

| Archivo          | Tipo         | Contenido                                            |
|------------------|--------------|------------------------------------------------------|
| `grafico_01.png` | Barras       | Los 10 mayores emisores de CO₂ en 2024               |
| `grafico_02.png` | Líneas       | CO₂ per cápita de Chile vs pares, OCDE y mundo       |
| `grafico_03.png` | Dispersión   | PIB per cápita vs CO₂ per cápita (2022)              |
| `grafico_04.png` | Caja         | Distribución del CO₂ per cápita por grupo (2024)     |
| `grafico_05.png` | Área apilada | CO₂ de Chile por combustible, 1990–2024              |
