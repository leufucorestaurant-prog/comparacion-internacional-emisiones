"""Series de tiempo por país o grupo y modelos simples de proyección."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.transformaciones import OCDE, PARES_LATAM

# Variable -> (etiqueta, unidad, cómo se agrega un grupo de países).
# "suma": se suman los países; "razon": suma del numerador / suma del denominador.
VARIABLES = {
    "co2_mt": ("CO2 total", "Mt", ("suma", None, None)),
    "co2_per_capita_t": ("CO2 per cápita", "t/persona", ("razon", "co2_mt", "poblacion", 1e6)),
    "co2_carbon_mt": ("CO2 por carbón", "Mt", ("suma", None, None)),
    "co2_petroleo_mt": ("CO2 por petróleo", "Mt", ("suma", None, None)),
    "co2_gas_mt": ("CO2 por gas", "Mt", ("suma", None, None)),
    "co2_por_pib_kg_usd": ("CO2 por PIB", "kg/USD", ("razon", "co2_mt", "pib_usd_ppa", 1e9)),
}

GRUPOS = {
    "Pares latinoamericanos (promedio)": PARES_LATAM,
    "OCDE (promedio)": OCDE,
    "Mundo (suma de países)": None,
}

MODELOS = ["Regresión lineal", "Promedio móvil", "Tasa de crecimiento promedio"]


def serie_entidad(datos, entidad, variable):
    """Serie anual de una variable para un país o un grupo (índice = año)."""
    if entidad not in GRUPOS:
        fila = datos[datos["pais"] == entidad].set_index("anio")[variable]
        return fila.dropna().sort_index()

    miembros = datos if GRUPOS[entidad] is None else datos[datos["iso_code"].isin(GRUPOS[entidad])]
    tipo = VARIABLES[variable][2]
    if tipo[0] == "suma":
        serie = miembros.groupby("anio")[variable].sum(min_count=1)
    else:
        _, numerador, denominador, escala = tipo
        validos = miembros.dropna(subset=[numerador, denominador])
        agregado = validos.groupby("anio")[[numerador, denominador]].sum()
        serie = agregado[numerador] * escala / agregado[denominador]
    return serie.dropna().sort_index()


# ---------- Modelos ----------
# Todos reciben la serie de entrenamiento (índice = año) y una lista de años
# futuros, y retornan una Serie con los valores proyectados.

def proyectar_lineal(serie, anios_futuros):
    """y = b0 + b1 * año, ajustado por mínimos cuadrados (LinearRegression)."""
    modelo = LinearRegression()
    modelo.fit(serie.index.to_numpy().reshape(-1, 1), serie.to_numpy())
    pred = modelo.predict(np.array(anios_futuros).reshape(-1, 1))
    return pd.Series(pred, index=anios_futuros)


def proyectar_promedio_movil(serie, anios_futuros, ventana=5):
    """Cada año futuro es el promedio de los `ventana` años anteriores
    (incluidos los ya proyectados), como rolling(ventana).mean() recursivo."""
    valores = list(serie.to_numpy())
    resultado = []
    for _ in anios_futuros:
        siguiente = pd.Series(valores).rolling(ventana).mean().iloc[-1]
        valores.append(siguiente)
        resultado.append(siguiente)
    return pd.Series(resultado, index=anios_futuros)


def tasa_crecimiento_promedio(serie):
    """Tasa anual compuesta: (valor final / valor inicial)^(1/n) - 1."""
    inicio, fin = serie.iloc[0], serie.iloc[-1]
    n = serie.index[-1] - serie.index[0]
    if inicio <= 0 or fin <= 0 or n <= 0:
        return 0.0
    return (fin / inicio) ** (1 / n) - 1


def proyectar_crecimiento(serie, anios_futuros):
    """y(t) = y(último año) * (1 + g)^(t - último año)."""
    g = tasa_crecimiento_promedio(serie)
    ultimo_anio, ultimo_valor = serie.index[-1], serie.iloc[-1]
    return pd.Series([ultimo_valor * (1 + g) ** (a - ultimo_anio) for a in anios_futuros],
                     index=anios_futuros)


def proyectar(serie, modelo, anios_futuros, ventana=5):
    if modelo == "Regresión lineal":
        pred = proyectar_lineal(serie, anios_futuros)
    elif modelo == "Promedio móvil":
        pred = proyectar_promedio_movil(serie, anios_futuros, ventana)
    else:
        pred = proyectar_crecimiento(serie, anios_futuros)
    return pred.clip(lower=0)  # las emisiones no pueden ser negativas


def r2_lineal(serie):
    """Coeficiente de determinación del ajuste lineal sobre los datos de entrenamiento."""
    x = serie.index.to_numpy().reshape(-1, 1)
    return LinearRegression().fit(x, serie.to_numpy()).score(x, serie.to_numpy())


def evaluar_modelos(serie, anios_entrenamiento, anios_prueba=5, ventana=5):
    """Validación retrospectiva: se ocultan los últimos `anios_prueba` años,
    se proyectan con cada modelo y se compara con lo que realmente ocurrió."""
    if len(serie) < anios_prueba + 4:
        return pd.DataFrame()
    prueba = serie.iloc[-anios_prueba:]
    entrenamiento = serie.iloc[:-anios_prueba].iloc[-anios_entrenamiento:]
    filas = []
    for modelo in MODELOS:
        pred = proyectar(entrenamiento, modelo, list(prueba.index), ventana)
        error = pred.to_numpy() - prueba.to_numpy()
        filas.append({
            "modelo": modelo,
            "MAE": np.mean(np.abs(error)),
            "MAPE_%": np.mean(np.abs(error) / np.abs(prueba.to_numpy())) * 100,
        })
    return pd.DataFrame(filas).sort_values("MAPE_%").reset_index(drop=True)
