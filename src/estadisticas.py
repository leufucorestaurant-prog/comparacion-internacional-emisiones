"""Estadísticas descriptivas del dataset limpio."""

import numpy as np
import pandas as pd

# Variable, unidad y año de corte. Las variables con PIB se miden en 2022
# porque OWID no publica PIB para 2023-2024.
VARIABLES_NUMERICAS = [
    ("co2_mt", "Mt CO2", 2024),
    ("co2_per_capita_t", "t CO2/persona", 2024),
    ("co2_por_pib_kg_usd", "kg CO2/USD PPA", 2022),
    ("pib_per_capita_usd", "USD PPA/persona", 2022),
    ("poblacion_millones", "millones de personas", 2024),
    ("pct_carbon", "% del CO2 total", 2024),
    ("variacion_co2_vs_1990_pct", "% respecto de 1990", 2024),
]

VARIABLES_CATEGORICAS = ["tramo_co2_per_capita", "combustible_principal", "grupo_comparacion"]


def cargar_dataset_limpio(ruta):
    """Lee el CSV del Avance 2 y excluye los registros marcados como atípicos."""
    datos = pd.read_csv(ruta, parse_dates=["fecha"])
    return datos[~datos["valor_atipico"]].copy()


def describir_variable(serie):
    """Medidas de tendencia central, dispersión y posición de una serie."""
    valores = serie.dropna().to_numpy(dtype=float)
    q1, mediana, q3 = np.percentile(valores, [25, 50, 75])
    return {
        "n": len(valores),
        "media": np.mean(valores),
        "mediana": mediana,
        "minimo": np.min(valores),
        "maximo": np.max(valores),
        "rango": np.ptp(valores),
        "desv_estandar": np.std(valores, ddof=1),
        "q1": q1,
        "q3": q3,
        "rango_intercuartil": q3 - q1,
        "coef_variacion_pct": np.std(valores, ddof=1) / np.mean(valores) * 100,
    }


def calcular_estadisticas(datos):
    """Tabla con una fila por variable numérica, medida en su año de corte."""
    filas = []
    for variable, unidad, anio in VARIABLES_NUMERICAS:
        corte = datos.loc[datos["anio"] == anio, variable]
        filas.append({"variable": variable, "unidad": unidad, "anio": anio,
                      **describir_variable(corte)})
    tabla = pd.DataFrame(filas)
    columnas = tabla.columns.drop(["variable", "unidad", "anio", "n"])
    tabla[columnas] = tabla[columnas].round(3)
    return tabla


def calcular_frecuencias(datos, anio=2024):
    """Frecuencia absoluta y relativa de las variables categóricas en un año."""
    corte = datos[datos["anio"] == anio]
    tablas = []
    for variable in VARIABLES_CATEGORICAS:
        conteo = corte[variable].value_counts()
        tablas.append(pd.DataFrame({
            "variable": variable,
            "categoria": conteo.index,
            "frecuencia": conteo.values,
            "porcentaje": (conteo.values / conteo.sum() * 100).round(2),
        }))
    return pd.concat(tablas, ignore_index=True)


def verificar_con_describe(datos, tabla):
    """Compara los cálculos con NumPy contra describe() de Pandas."""
    diferencia_maxima = 0.0
    for _, fila in tabla.iterrows():
        resumen = datos.loc[datos["anio"] == fila["anio"], fila["variable"]].describe()
        pares = [(fila["media"], resumen["mean"]), (fila["mediana"], resumen["50%"]),
                 (fila["desv_estandar"], resumen["std"]), (fila["q1"], resumen["25%"]),
                 (fila["q3"], resumen["75%"]), (fila["minimo"], resumen["min"]),
                 (fila["maximo"], resumen["max"])]
        diferencia_maxima = max(diferencia_maxima, *(abs(a - b) for a, b in pares))
    print(f"\n  Verificación NumPy vs describe(): diferencia máxima = {diferencia_maxima:.4f} "
          "(solo redondeo a 3 decimales)")
    return diferencia_maxima


def calcular_correlacion(datos, anio=2022):
    """Correlación entre log10 del PIB per cápita y el CO2 per cápita."""
    corte = datos[datos["anio"] == anio].dropna(subset=["pib_per_capita_usd", "co2_per_capita_t"])
    r = np.corrcoef(np.log10(corte["pib_per_capita_usd"]), corte["co2_per_capita_t"])[0, 1]
    print(f"  Correlación log10(PIB per cápita) vs CO2 per cápita ({anio}, n={len(corte)}): r = {r:.3f}")
    return r


def mostrar_estadisticas(tabla, frecuencias):
    print("\n=== Estadísticas descriptivas ===")
    print(tabla.drop(columns=["unidad"]).to_string(index=False))
    print("\n=== Frecuencias de variables categóricas (2024) ===")
    print(frecuencias.to_string(index=False))
