"""Indicadores automatizados que responden la pregunta del proyecto."""

import numpy as np
import pandas as pd

from src.transformaciones import OCDE, PARES_LATAM

ANIO_FINAL = 2024
ANIO_BASE = 1990
ANIO_PIB = 2022
PAIS_FOCO = "CHL"


def promedio_ponderado_per_capita(corte):
    """CO2 per cápita de un grupo: suma de emisiones / suma de población."""
    con_poblacion = corte.dropna(subset=["poblacion"])
    return con_poblacion["co2_mt"].sum() * 1e6 / con_poblacion["poblacion"].sum()


def indicador(nombre, metodo, resultado, unidad, interpretacion):
    return {"indicador": nombre, "metodo_calculo": metodo,
            "resultado": round(float(resultado), 2), "unidad": unidad,
            "interpretacion": interpretacion}


def registros_validos(datos):
    validos = datos.dropna(subset=["co2_mt", "co2_per_capita_t"])
    paises = validos.loc[validos["anio"] == ANIO_FINAL, "pais"].nunique()
    return indicador(
        "Registros válidos para comparar",
        "Filas con co2_mt y co2_per_capita_t no nulos (1990-2024)",
        len(validos), "registros",
        f"{len(validos)} de {len(datos)} filas permiten comparar total y per cápita; "
        f"en {ANIO_FINAL} hay {paises} países comparables.")


def concentracion_top10(datos):
    corte = datos[datos["anio"] == ANIO_FINAL]
    top = corte.nlargest(10, "co2_mt")
    porcentaje = top["co2_mt"].sum() / corte["co2_mt"].sum() * 100
    return indicador(
        f"Concentración: % del CO2 emitido por los 10 mayores emisores ({ANIO_FINAL})",
        "Suma de co2_mt de los 10 países con más emisiones / suma de todos los países x 100",
        porcentaje, "%",
        f"10 de {len(corte)} países ({10 / len(corte) * 100:.1f} %) concentran el "
        f"{porcentaje:.1f} % del CO2; encabezan {', '.join(top['pais'].head(3))}.")


def posicion_chile_per_capita(datos):
    corte = datos[(datos["anio"] == ANIO_FINAL)].dropna(subset=["co2_per_capita_t"])
    ranking = corte["co2_per_capita_t"].rank(ascending=False, method="min")
    puesto = int(ranking[corte["iso_code"] == PAIS_FOCO].iloc[0])
    valor = corte.loc[corte["iso_code"] == PAIS_FOCO, "co2_per_capita_t"].iloc[0]
    percentil = (corte["co2_per_capita_t"] < valor).mean() * 100
    return indicador(
        f"Puesto de Chile en CO2 per cápita ({ANIO_FINAL})",
        "Ranking descendente de co2_per_capita_t entre todos los países del año",
        puesto, f"de {len(corte)}",
        f"Chile ({valor:.2f} t/persona) ocupa el puesto {puesto} de {len(corte)}: "
        f"emite más por habitante que el {percentil:.0f} % de los países.")


def brecha_chile_grupos(datos):
    corte = datos[datos["anio"] == ANIO_FINAL]
    chile = corte.loc[corte["iso_code"] == PAIS_FOCO, "co2_per_capita_t"].iloc[0]
    latam = promedio_ponderado_per_capita(corte[corte["iso_code"].isin(PARES_LATAM)])
    ocde = promedio_ponderado_per_capita(corte[corte["iso_code"].isin(OCDE)])
    mundo = promedio_ponderado_per_capita(corte)
    brecha = (chile / latam - 1) * 100
    return indicador(
        f"Brecha de CO2 per cápita de Chile frente a sus pares latinoamericanos ({ANIO_FINAL})",
        "(per cápita Chile / per cápita ponderado de ARG, BRA, MEX, PER y COL - 1) x 100",
        brecha, "%",
        f"Chile ({chile:.2f} t) emite {brecha:.0f} % más por habitante que sus pares "
        f"({latam:.2f} t), pero menos que la OCDE ({ocde:.2f} t) y el mundo ({mundo:.2f} t).")


def variacion_chile_vs_mundo(datos):
    chile = datos[datos["iso_code"] == PAIS_FOCO].set_index("anio")["co2_mt"]
    mundo = datos.groupby("anio")["co2_mt"].sum()
    var_chile = (chile[ANIO_FINAL] / chile[ANIO_BASE] - 1) * 100
    var_mundo = (mundo[ANIO_FINAL] / mundo[ANIO_BASE] - 1) * 100
    return indicador(
        f"Variación del CO2 de Chile {ANIO_BASE}-{ANIO_FINAL}",
        f"(co2_mt {ANIO_FINAL} / co2_mt {ANIO_BASE} - 1) x 100, comparado con la suma de países",
        var_chile, "%",
        f"Las emisiones de Chile crecieron {var_chile:.0f} % ({chile[ANIO_BASE]:.1f} a "
        f"{chile[ANIO_FINAL]:.1f} Mt), más del doble que el total mundial ({var_mundo:.0f} %).")


def caida_carbon_chile(datos):
    chile = datos[datos["iso_code"] == PAIS_FOCO].set_index("anio")
    anio_max = int(chile["co2_carbon_mt"].idxmax())
    maximo = chile.loc[anio_max, "co2_carbon_mt"]
    final = chile.loc[ANIO_FINAL, "co2_carbon_mt"]
    caida = (final / maximo - 1) * 100
    return indicador(
        f"Variación del CO2 por carbón de Chile desde su máximo ({anio_max}-{ANIO_FINAL})",
        "(co2_carbon_mt 2024 / máximo histórico de co2_carbon_mt - 1) x 100",
        caida, "%",
        f"El CO2 por carbón cayó de {maximo:.1f} Mt ({anio_max}) a {final:.1f} Mt; su "
        f"participación bajó a {chile.loc[ANIO_FINAL, 'pct_carbon']:.1f} % del total por el "
        "retiro de centrales a carbón.")


def paises_sobre_promedio(datos):
    corte = datos[datos["anio"] == ANIO_FINAL].dropna(subset=["co2_per_capita_t"])
    mundo = promedio_ponderado_per_capita(corte)
    porcentaje = (corte["co2_per_capita_t"] > mundo).mean() * 100
    return indicador(
        f"% de países sobre el promedio mundial per cápita ({ANIO_FINAL})",
        "Países con co2_per_capita_t > (suma CO2 / suma población) / total de países x 100",
        porcentaje, "%",
        f"Solo el {porcentaje:.0f} % de los países supera el promedio mundial de {mundo:.2f} t: "
        "pocos países de altas emisiones elevan el promedio.")


def combustible_mas_frecuente(datos):
    corte = datos[datos["anio"] == ANIO_FINAL]
    conteo = corte["combustible_principal"].value_counts()
    porcentaje = conteo.iloc[0] / conteo.sum() * 100
    nombre = {"petroleo": "petróleo", "carbon": "carbón"}.get(conteo.index[0], conteo.index[0])
    return indicador(
        f"Combustible principal más frecuente ({ANIO_FINAL})",
        "Moda de combustible_principal entre los países",
        porcentaje, f"% ({nombre})",
        f"El {nombre} es la principal fuente de CO2 en {conteo.iloc[0]} países "
        f"({porcentaje:.0f} %); el carbón domina en {conteo.get('carbon', 0)}.")


def maximo_per_capita(datos):
    corte = datos[datos["anio"] == ANIO_FINAL].dropna(subset=["co2_per_capita_t"])
    fila = corte.loc[corte["co2_per_capita_t"].idxmax()]
    mediana = corte["co2_per_capita_t"].median()
    return indicador(
        f"Máximo CO2 per cápita y país asociado ({ANIO_FINAL})",
        "Máximo de co2_per_capita_t y país de esa fila",
        fila["co2_per_capita_t"], f"t/persona ({fila['pais']})",
        f"{fila['pais']} emite {fila['co2_per_capita_t']:.1f} t por habitante, "
        f"{fila['co2_per_capita_t'] / mediana:.0f} veces la mediana mundial ({mediana:.2f} t).")


def intensidad_chile_vs_ocde(datos):
    corte = datos[datos["anio"] == ANIO_PIB].dropna(subset=["co2_por_pib_kg_usd"])
    chile = corte.loc[corte["iso_code"] == PAIS_FOCO, "co2_por_pib_kg_usd"].iloc[0]
    ocde = corte[corte["iso_code"].isin(OCDE)]
    mediana = ocde["co2_por_pib_kg_usd"].median()
    return indicador(
        f"Intensidad de carbono de Chile frente a la mediana OCDE ({ANIO_PIB})",
        "(co2_por_pib_kg_usd Chile / mediana OCDE - 1) x 100",
        (chile / mediana - 1) * 100, "%",
        f"Chile emite {chile:.3f} kg por dólar de PIB y la mediana OCDE es {mediana:.3f} kg: "
        f"es {'más' if chile > mediana else 'menos'} intensivo en carbono que el país OCDE típico.")


INDICADORES = [
    registros_validos, concentracion_top10, posicion_chile_per_capita,
    brecha_chile_grupos, variacion_chile_vs_mundo, caida_carbon_chile,
    paises_sobre_promedio, combustible_mas_frecuente, maximo_per_capita,
    intensidad_chile_vs_ocde,
]


def calcular_indicadores(datos):
    tabla = pd.DataFrame([funcion(datos) for funcion in INDICADORES])
    tabla.insert(0, "n", np.arange(1, len(tabla) + 1))
    print("\n=== Indicadores automatizados ===")
    for _, fila in tabla.iterrows():
        print(f"  {fila.n:>2}. {fila.indicador}: {fila.resultado} {fila.unidad}")
        print(f"      {fila.interpretacion}")
    return tabla
