"""Pipeline del Avance 2: carga, diagnóstico, limpieza, nulos,
transformaciones, validación y exportación. Ejecutar desde la raíz:

    python main.py
"""

import os

import pandas as pd

from src.carga import VARIABLES_ANALISIS, cargar_datos, seleccionar_variables
from src.limpieza import limpiar_datos, tratar_nulos
from src.transformaciones import NOMBRES_CON_UNIDAD, aplicar_transformaciones
from src.validaciones import (detalle_fuera_de_rango, diagnosticar_calidad,
                              validar_dataset_final)

RUTA_ORIGINAL = os.path.join("datos", "originales", "owid-co2-data.csv")
RUTA_LIMPIO = os.path.join("datos", "procesados", "dataset_limpio.csv")
CARPETA_EVIDENCIAS = os.path.join("reportes", "evidencias")

COLUMNAS_FINALES = [
    "pais", "iso_code", "anio", "fecha", "decada", "grupo_comparacion",
    "poblacion", "poblacion_millones", "pib_usd_ppa", "pib_per_capita_usd",
    "co2_mt", "co2_per_capita_t", "tramo_co2_per_capita", "co2_por_pib_kg_usd",
    "participacion_global_pct", "co2_acumulado_mt", "variacion_co2_vs_1990_pct",
    "co2_carbon_mt", "co2_petroleo_mt", "co2_gas_mt", "pct_carbon",
    "combustible_principal", "co2_consumo_mt", "gei_total_mt_co2e", "valor_atipico",
]

TIPOS_ESPERADOS = {
    "pais": "category", "iso_code": "category", "anio": "int64",
    "fecha": "datetime64[us]", "poblacion": "Int64", "co2_mt": "float64",
    "co2_per_capita_t": "float64", "tramo_co2_per_capita": "category",
    "grupo_comparacion": "category", "valor_atipico": "bool",
}

RANGOS_FINALES = {
    "anio": (1990, 2024),
    "poblacion": (1, None),
    "co2_mt": (0, None),
    "co2_per_capita_t": (0, 100),
    "co2_por_pib_kg_usd": (0, 10),
    "participacion_global_pct": (0, 100),
    "pct_carbon": (0, 100.01),
    "co2_carbon_mt": (0, None),
    "co2_petroleo_mt": (0, None),
    "co2_gas_mt": (0, None),
}


def guardar_evidencia(tabla, nombre):
    os.makedirs(CARPETA_EVIDENCIAS, exist_ok=True)
    tabla.to_csv(os.path.join(CARPETA_EVIDENCIAS, nombre), index=False, encoding="utf-8")


def main():
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 30)

    # 1. Carga
    datos_originales = cargar_datos(RUTA_ORIGINAL)
    if datos_originales is None:
        print("El programa finalizó sin procesar los datos.")
        return
    print(f"Carga realizada: {datos_originales.shape[0]} filas y "
          f"{datos_originales.shape[1]} columnas en el archivo original.")
    datos = seleccionar_variables(datos_originales)

    # 2. Diagnóstico (sobre las 15 variables del análisis)
    indicadores_antes, resumen_antes = diagnosticar_calidad(
        datos[VARIABLES_ANALISIS], "conjunto original (15 variables)")
    guardar_evidencia(resumen_antes.reset_index(names="variable"), "diagnostico_inicial.csv")
    guardar_evidencia(detalle_fuera_de_rango(datos[VARIABLES_ANALISIS]), "fuera_de_rango_inicial.csv")

    # 3. Limpieza
    registro = []
    datos, agregados = limpiar_datos(datos, registro)
    print(f"  Agregados eliminados: {agregados}")
    print(f"  Conjunto tras limpieza: {datos.shape}")

    # 4. Tratamiento de nulos
    print("\n=== Tratamiento de nulos ===")
    datos, tabla_nulos = tratar_nulos(datos, registro)
    print(f"  {'variable':<16}{'iniciales':>10}{'finales':>9}  estrategia")
    for _, fila in tabla_nulos.iterrows():
        print(f"  {fila.variable:<16}{fila.nulos_iniciales:>10}{fila.nulos_finales:>9}  {fila.estrategia}")

    # 5. Transformaciones
    datos, nuevas = aplicar_transformaciones(datos)
    datos = datos[COLUMNAS_FINALES]

    # 6. Validación
    validar_dataset_final(
        datos, COLUMNAS_FINALES, TIPOS_ESPERADOS, RANGOS_FINALES,
        clave=["pais", "anio"], obligatorias=["pais", "iso_code", "anio", "co2_mt"])
    indicadores_despues, resumen_despues = diagnosticar_calidad(
        datos, "conjunto limpio", clave=["pais", "anio"], rangos=RANGOS_FINALES)

    # 7. Exportación (el archivo original nunca se sobrescribe)
    os.makedirs(os.path.dirname(RUTA_LIMPIO), exist_ok=True)
    datos.to_csv(RUTA_LIMPIO, index=False, encoding="utf-8")
    print(f"\nDataset limpio exportado en {RUTA_LIMPIO} ({datos.shape[0]} filas x {datos.shape[1]} columnas).")

    nuevas_finales = [c for c in COLUMNAS_FINALES if c in nuevas or c == "valor_atipico"]
    comparacion = pd.DataFrame({
        "indicador": ["Filas", "Columnas", "Valores nulos", "Filas duplicadas",
                      "Valores fuera de rango", "Variables transformadas", "Variables nuevas"],
        "antes": [indicadores_antes["filas"], indicadores_antes["columnas"],
                  indicadores_antes["valores_nulos"], indicadores_antes["filas_duplicadas"],
                  indicadores_antes["valores_fuera_de_rango"], 0, 0],
        "despues": [indicadores_despues["filas"], indicadores_despues["columnas"],
                    indicadores_despues["valores_nulos"], indicadores_despues["filas_duplicadas"],
                    indicadores_despues["valores_fuera_de_rango"], len(NOMBRES_CON_UNIDAD),
                    len(nuevas_finales)],
    })
    print("\n=== Comparación antes y después ===")
    print(comparacion.to_string(index=False))
    print(f"  Variables nuevas: {nuevas_finales}")

    guardar_evidencia(pd.DataFrame(registro), "registro_limpieza.csv")
    guardar_evidencia(tabla_nulos, "tratamiento_nulos.csv")
    guardar_evidencia(resumen_despues.reset_index(names="variable"), "diagnostico_final.csv")
    guardar_evidencia(comparacion, "comparacion_antes_despues.csv")
    print(f"Evidencias guardadas en {CARPETA_EVIDENCIAS}/")


if __name__ == "__main__":
    main()
