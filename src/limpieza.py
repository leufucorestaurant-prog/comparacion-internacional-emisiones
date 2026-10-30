"""Normalización, duplicados, registros fuera de rango y tratamiento de nulos."""

import re

import pandas as pd

from src.carga import COMPONENTES_CO2

ANIO_INICIO = 1990
ANIO_FIN = 2024

# Nombres de país con sufijos aclaratorios de OWID que no corresponden a
# otra entidad; se dejan con su nombre corto habitual.
NOMBRES_PAIS = {
    "Micronesia (country)": "Micronesia",
    "Sint Maarten (Dutch part)": "Sint Maarten",
}

# Países reales sin código ISO en OWID. Kosovo usa el código provisional
# XKX asignado por la Comisión Europea y el FMI (no es parte de ISO 3166).
ISO_RECUPERADOS = {"Kosovo": "XKX"}

# Las emisiones del registro anómalo se conservan (ocurrieron), pero sus
# indicadores relativos se anulan para no distorsionar las comparaciones.
INDICADORES_RELATIVOS = ["co2_per_capita", "co2_per_gdp"]


def registrar(registro, etapa, criterio, filas, justificacion):
    """Agrega una entrada al registro de eliminaciones y cambios."""
    registro.append({
        "etapa": etapa,
        "criterio": criterio,
        "filas_afectadas": int(filas),
        "justificacion": justificacion,
    })
    print(f"  - {etapa}: {criterio} -> {filas} filas")


def normalizar_columnas(datos):
    """Nombres en minúsculas, sin espacios extremos y en formato snake_case."""
    datos = datos.copy()
    datos.columns = [
        re.sub(r"[^0-9a-z]+", "_", str(c).strip().lower()).strip("_")
        for c in datos.columns
    ]
    return datos


def eliminar_espacios(datos):
    """Quita espacios al inicio/fin y espacios dobles en columnas de texto."""
    datos = datos.copy()
    for columna in datos.select_dtypes(include=["object", "string"]).columns:
        datos[columna] = datos[columna].str.strip().str.replace(r"\s+", " ", regex=True)
    if "iso_code" in datos.columns:
        datos["iso_code"] = datos["iso_code"].str.upper()
    return datos


def corregir_categorias(datos, registro):
    datos = datos.copy()
    cambios = datos["country"].isin(NOMBRES_PAIS.keys()).sum()
    datos["country"] = datos["country"].replace(NOMBRES_PAIS)
    registrar(registro, "Limpieza", "Nombres de país con sufijo de OWID unificados",
              cambios, "Sufijos como '(country)' o '(Dutch part)' no agregan "
              "información y dificultan las uniones con otras fuentes.")
    return datos


def recuperar_identificadores(datos, registro):
    """Asigna ISO a países reales que OWID deja sin código."""
    datos = datos.copy()
    for pais, codigo in ISO_RECUPERADOS.items():
        mascara = (datos["country"] == pais) & datos["iso_code"].isna()
        datos.loc[mascara, "iso_code"] = codigo
        registrar(registro, "Identificadores", f"iso_code recuperado para {pais} ({codigo})",
                  mascara.sum(), "Kosovo es un país, no un agregado; sin código "
                  "se eliminaría junto con las regiones.")
    return datos


def eliminar_agregados(datos, registro):
    """Elimina regiones y grupos (iso_code vacío) para no contar dos veces."""
    agregados = datos["iso_code"].isna()
    entidades = sorted(datos.loc[agregados, "country"].unique())
    registrar(registro, "Limpieza", f"Agregados sin iso_code ({len(entidades)} entidades)",
              agregados.sum(), "World, continentes, grupos de ingreso y versiones "
              "'(GCP)' suman países que ya están en el conjunto; incluirlos "
              "duplicaría emisiones en rankings y totales.")
    return datos[~agregados].copy(), entidades


def filtrar_periodo(datos, registro, inicio=ANIO_INICIO, fin=ANIO_FIN):
    fuera = ~datos["year"].between(inicio, fin)
    registrar(registro, "Limpieza", f"Años fuera de {inicio}-{fin}", fuera.sum(),
              "Antes de 1990 la cobertura es baja (41,7 % de nulos en co2) y no "
              "hay emisiones por consumo; el análisis compara 1990-2024.")
    return datos[~fuera].copy()


def eliminar_duplicados(datos, registro, clave=("country", "year")):
    exactos = datos.duplicated()
    datos = datos[~exactos]
    registrar(registro, "Duplicados", "Filas idénticas", exactos.sum(),
              "Una fila repetida contaría dos veces las mismas emisiones.")
    repetidas = datos.duplicated(subset=list(clave), keep="first")
    datos = datos[~repetidas]
    registrar(registro, "Duplicados", "Claves país-año repetidas", repetidas.sum(),
              "Cada país debe tener un solo registro por año.")
    return datos.copy()


def corregir_fuera_de_rango(datos, registro, maximo_per_capita=100):
    """Marca registros anómalos y anula sus indicadores relativos."""
    datos = datos.copy()
    anomalos = datos["co2_per_capita"] > maximo_per_capita
    datos["valor_atipico"] = anomalos
    detalle = ", ".join(f"{p} {a}" for p, a in datos.loc[anomalos, ["country", "year"]].values)
    datos.loc[anomalos, INDICADORES_RELATIVOS] = pd.NA
    registrar(registro, "Fuera de rango",
              f"co2_per_capita > {maximo_per_capita} t ({detalle}): indicadores relativos a nulo",
              anomalos.sum(), "Kuwait 1991 refleja los incendios petroleros de la "
              "Guerra del Golfo (365 t/persona, 82,6 kg/USD). La emisión total se "
              "conserva, pero los indicadores per cápita y por PIB se excluyen.")
    return datos


def tratar_nulos(datos, registro):
    """Aplica una estrategia distinta a cada variable y retorna la tabla resumen."""
    datos = datos.copy()
    iniciales = datos.isna().sum()
    filas = []

    def agregar(variable, estrategia, justificacion, inicial=None):
        filas.append({
            "variable": variable,
            "nulos_iniciales": int(iniciales.get(variable, 0) if inicial is None else inicial),
            "estrategia": estrategia,
            "justificacion": justificacion,
        })

    # co2: es la variable principal; una fila sin co2 no aporta al análisis.
    sin_co2 = datos["co2"].isna()
    paises = ", ".join(datos.loc[sin_co2, "country"].value_counts().index[:4])
    datos = datos[~sin_co2].copy()
    registrar(registro, "Nulos", "Filas sin co2", sin_co2.sum(),
              f"Sin la variable principal la fila no sirve para comparar ({paises}...). "
              "Monaco, San Marino y Vaticano se reportan dentro de Francia e Italia.")
    agregar("co2", "Eliminar registros",
            "Variable principal; imputarla inventaría emisiones. Monaco, San Marino "
            "y Vaticano están incluidos en Francia/Italia.")

    # Recalcular las variables que dependen de co2 tras eliminar filas.
    # share_global_co2 y cumulative_co2 vienen calculadas por OWID.
    for variable in ["share_global_co2", "cumulative_co2"]:
        agregar(variable, "Eliminar registros (junto con co2)",
                "Sus nulos coinciden con las filas sin co2.")

    # Combustibles: si co2 ya iguala la suma de los demás componentes, el
    # combustible faltante no aporta emisiones, por lo que vale 0.
    for combustible in ["coal_co2", "oil_co2", "gas_co2"]:
        otros = [c for c in COMPONENTES_CO2 if c != combustible]
        suma_otros = datos[otros].sum(axis=1, min_count=1)
        cuadra = (datos["co2"] - suma_otros).abs() < 0.01
        imputar = datos[combustible].isna() & cuadra
        datos.loc[imputar, combustible] = 0.0
        agregar(combustible, f"Imputar 0 si co2 = suma del resto ({imputar.sum()} filas)",
                "El total ya cuadra sin este combustible: el país no lo usa. "
                "Si no cuadra, se mantiene nulo (no se imputa sin evidencia).")

    # population: interpolación lineal dentro de cada país solo en huecos
    # internos; si el país no tiene ningún dato, el nulo significa que no
    # hay población permanente (por ejemplo, Antártica).
    antes = datos["population"].isna().sum()
    datos["population"] = datos.groupby("country")["population"].transform(
        lambda s: s.interpolate(limit_area="inside"))
    agregar("population", f"Interpolar huecos internos ({antes - datos['population'].isna().sum()} filas); "
            "mantener nulo si el país no tiene datos", "Los nulos restantes son Antártica e "
            "Isla de Navidad, sin población permanente registrada: el nulo tiene "
            "significado y no se inventa una población.", inicial=antes)

    # Indicadores relativos: se recuperan calculándolos desde sus componentes
    # (fuente válida: la misma definición de OWID), salvo en registros atípicos.
    normales = ~datos["valor_atipico"]
    calculo_pc = datos["co2"] * 1e6 / datos["population"]
    recuperar = datos["co2_per_capita"].isna() & calculo_pc.notna() & normales
    datos.loc[recuperar, "co2_per_capita"] = calculo_pc[recuperar].round(3)
    agregar("co2_per_capita", f"Recalcular co2 / population donde sea posible ({recuperar.sum()} filas); "
            "resto nulo", "Es una razón de dos variables; los nulos restantes son los "
            "países sin población y Kuwait 1991 (atípico anulado).")

    calculo_pib = datos["co2"] * 1e9 / datos["gdp"]
    recuperar = datos["co2_per_gdp"].isna() & calculo_pib.notna() & normales
    datos.loc[recuperar, "co2_per_gdp"] = calculo_pib[recuperar].round(3)
    agregar("gdp", "Mantener nulo", "OWID publica PIB solo hasta 2022 y no para "
            "algunos territorios; imputar PIB futuro sería un pronóstico.")
    agregar("co2_per_gdp", f"Recalcular co2 / gdp donde sea posible ({recuperar.sum()} filas); "
            "resto nulo", "Depende del PIB: donde no hay PIB (2023-2024) el indicador no existe.")

    agregar("consumption_co2", "Mantener nulo", "OWID solo estima emisiones de consumo "
            "para países con tablas de comercio; el nulo significa 'no estimado'.")

    antes = datos["total_ghg"].isna().sum()
    datos["total_ghg"] = datos.groupby("country")["total_ghg"].transform(
        lambda s: s.interpolate(limit_area="inside"))
    agregar("total_ghg", f"Interpolar huecos internos ({antes - datos['total_ghg'].isna().sum()} filas); "
            "mantener nulo", "Los nulos son territorios completos sin inventario de GEI "
            "(Groenlandia, Bermudas, etc.): no hay base para estimarlos. Es una "
            "variable complementaria.", inicial=antes)

    tabla = pd.DataFrame(filas).drop_duplicates("variable").set_index("variable")
    finales = datos.isna().sum()
    tabla["nulos_finales"] = [int(finales.get(v, 0)) for v in tabla.index]
    return datos, tabla.reset_index()


def limpiar_datos(datos, registro):
    """Ejecuta la limpieza estructural en orden y retorna el conjunto limpio."""
    print("\n=== Limpieza ===")
    datos = normalizar_columnas(datos)
    datos = eliminar_espacios(datos)
    datos = corregir_categorias(datos, registro)
    datos = recuperar_identificadores(datos, registro)
    datos, agregados = eliminar_agregados(datos, registro)
    datos = filtrar_periodo(datos, registro)
    datos = eliminar_duplicados(datos, registro)
    datos = corregir_fuera_de_rango(datos, registro)
    return datos, agregados
