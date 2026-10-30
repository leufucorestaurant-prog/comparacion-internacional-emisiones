"""Lectura y carga del conjunto de datos de emisiones (Our World in Data)."""

import os

import pandas as pd

# Variables documentadas en el diccionario de datos del Avance 1.
VARIABLES_ANALISIS = [
    "country", "year", "iso_code", "population", "gdp",
    "co2", "co2_per_capita", "co2_per_gdp", "share_global_co2",
    "cumulative_co2", "coal_co2", "oil_co2", "gas_co2",
    "consumption_co2", "total_ghg",
]

# Componentes que suman el co2 total; se usan solo para validar los
# nulos de combustibles y luego se descartan.
COMPONENTES_CO2 = [
    "coal_co2", "oil_co2", "gas_co2",
    "cement_co2", "flaring_co2", "other_industry_co2",
]


def cargar_datos(ruta):
    """Lee CSV, JSON o Excel según la extensión y retorna un DataFrame."""
    extension = os.path.splitext(ruta)[1].lower()
    try:
        if extension == ".csv":
            datos = pd.read_csv(ruta, encoding="utf-8")
        elif extension == ".json":
            datos = pd.read_json(ruta)
        elif extension in (".xlsx", ".xls", ".xlsm"):
            datos = pd.read_excel(ruta)
        else:
            print(f"Error: el formato '{extension}' no está soportado.")
            return None
        return datos
    except FileNotFoundError:
        print(f"Error: no se encontró el archivo '{ruta}'.")
    except pd.errors.EmptyDataError:
        print("Error: el archivo no contiene datos.")
    except pd.errors.ParserError:
        print("Error: no fue posible interpretar el archivo.")
    except UnicodeDecodeError:
        print("Error: la codificación del archivo no es compatible.")
    return None


def seleccionar_variables(datos, variables=None):
    """Deja solo las variables del análisis más los componentes de co2.

    Avisa si alguna columna esperada no existe (por ejemplo, si OWID
    cambia un nombre en una actualización).
    """
    variables = variables or list(dict.fromkeys(VARIABLES_ANALISIS + COMPONENTES_CO2))
    faltantes = [v for v in variables if v not in datos.columns]
    if faltantes:
        print(f"Advertencia: columnas no encontradas: {faltantes}")
    presentes = [v for v in variables if v in datos.columns]
    return datos[presentes].copy()
