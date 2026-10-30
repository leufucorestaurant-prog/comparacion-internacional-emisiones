"""Conversión de tipos y creación de variables para el análisis."""

import pandas as pd

# Nombres con su unidad explícita (pendiente detectado en el Avance 1).
NOMBRES_CON_UNIDAD = {
    "country": "pais",
    "year": "anio",
    "population": "poblacion",
    "gdp": "pib_usd_ppa",
    "co2": "co2_mt",
    "co2_per_capita": "co2_per_capita_t",
    "co2_per_gdp": "co2_por_pib_kg_usd",
    "share_global_co2": "participacion_global_pct",
    "cumulative_co2": "co2_acumulado_mt",
    "coal_co2": "co2_carbon_mt",
    "oil_co2": "co2_petroleo_mt",
    "gas_co2": "co2_gas_mt",
    "consumption_co2": "co2_consumo_mt",
    "total_ghg": "gei_total_mt_co2e",
}

PARES_LATAM = ["ARG", "BRA", "MEX", "PER", "COL"]
OCDE = [
    "AUS", "AUT", "BEL", "CAN", "CHL", "COL", "CRI", "CZE", "DNK", "EST",
    "FIN", "FRA", "DEU", "GRC", "HUN", "ISL", "IRL", "ISR", "ITA", "JPN",
    "KOR", "LVA", "LTU", "LUX", "MEX", "NLD", "NZL", "NOR", "POL", "PRT",
    "SVK", "SVN", "ESP", "SWE", "CHE", "TUR", "GBR", "USA",
]

# Límites de los tramos de CO2 per cápita (t/persona). El promedio mundial
# 2024 es 4,7 t; el tramo "medio" lo contiene.
TRAMOS_PER_CAPITA = [0, 2, 5, 10, float("inf")]
ETIQUETAS_TRAMOS = ["bajo (<2 t)", "medio (2-5 t)", "alto (5-10 t)", "muy alto (>10 t)"]


def convertir_tipos(datos):
    """Población a entero con nulos, año a fecha y texto a categoría."""
    datos = datos.copy()
    datos["population"] = datos["population"].round().astype("Int64")
    datos["fecha"] = pd.to_datetime(datos["year"].astype(str), format="%Y")
    datos["decada"] = (datos["fecha"].dt.year // 10 * 10).astype("int64")
    datos["valor_atipico"] = datos["valor_atipico"].astype(bool)
    return datos


def crear_variables(datos):
    """Variables derivadas que responden a los objetivos específicos."""
    datos = datos.copy()

    # Cambio de unidad: personas a millones de personas.
    datos["poblacion_millones"] = (datos["population"].astype("float64") / 1e6).round(3)

    datos["pib_per_capita_usd"] = (datos["gdp"] / datos["population"].astype("float64")).round(0)

    # Participación del carbón en el total (objetivo específico 3).
    datos["pct_carbon"] = (datos["coal_co2"] / datos["co2"] * 100).round(2)

    combustibles = datos[["coal_co2", "oil_co2", "gas_co2"]].rename(
        columns={"coal_co2": "carbon", "oil_co2": "petroleo", "gas_co2": "gas"})
    principal = combustibles.fillna(-1).idxmax(axis=1)
    sin_dato = combustibles.isna().all(axis=1) | (combustibles.fillna(0).sum(axis=1) == 0)
    datos["combustible_principal"] = principal.where(~sin_dato, "desconocido")

    tramo = pd.cut(datos["co2_per_capita"], bins=TRAMOS_PER_CAPITA,
                   labels=ETIQUETAS_TRAMOS, right=False)
    datos["tramo_co2_per_capita"] = tramo.cat.add_categories("desconocido").fillna("desconocido")

    def grupo(iso):
        if iso == "CHL":
            return "Chile"
        if iso in PARES_LATAM:
            return "America Latina (pares)"
        if iso in OCDE:
            return "OCDE"
        return "Resto del mundo"

    datos["grupo_comparacion"] = datos["iso_code"].map(grupo)

    base_1990 = datos[datos["year"] == 1990].set_index("country")["co2"]
    base = datos["country"].map(base_1990)
    datos["variacion_co2_vs_1990_pct"] = ((datos["co2"] / base - 1) * 100).where(base > 0).round(2)
    return datos


def aplicar_transformaciones(datos):
    """Aplica conversiones, crea variables y deja nombres con unidad."""
    print("\n=== Transformaciones ===")
    columnas_antes = set(datos.columns)
    datos = convertir_tipos(datos)
    datos = crear_variables(datos)
    datos = datos.rename(columns=NOMBRES_CON_UNIDAD)

    for columna in ["pais", "iso_code", "combustible_principal", "grupo_comparacion"]:
        datos[columna] = datos[columna].astype("category")

    nuevas = [c for c in datos.columns
              if c not in columnas_antes and c not in NOMBRES_CON_UNIDAD.values()]
    print(f"  Variables nuevas ({len(nuevas)}): {nuevas}")
    return datos.sort_values(["pais", "anio"]).reset_index(drop=True), nuevas
