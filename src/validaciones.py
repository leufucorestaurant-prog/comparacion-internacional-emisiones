"""Diagnóstico de calidad y comprobación de columnas, tipos y rangos."""

import pandas as pd

CLAVE = ["country", "year"]

# Rangos válidos por variable (mínimo, máximo); None = sin límite.
# co2_per_capita: ningún país supera ~80 t/persona salvo eventos
# extraordinarios (Kuwait 1991, incendios petroleros), por eso el límite
# es 100 t. co2_per_gdp: la mediana es 0,24 kg/USD; 10 kg/USD es 40 veces
# la mediana y solo lo supera un registro anómalo.
RANGOS = {
    "year": (1750, 2024),
    "population": (1, None),
    "gdp": (0, None),
    "co2": (0, None),
    "co2_per_capita": (0, 100),
    "co2_per_gdp": (0, 10),
    "share_global_co2": (0, 100),
    "cumulative_co2": (0, None),
    "coal_co2": (0, None),
    "oil_co2": (0, None),
    "gas_co2": (0, None),
    "consumption_co2": (0, None),
}


def mascara_fuera_de_rango(datos, rangos=None):
    """Retorna un DataFrame booleano: True donde el valor viola su rango."""
    rangos = rangos or RANGOS
    mascara = pd.DataFrame(False, index=datos.index, columns=[])
    for columna, (minimo, maximo) in rangos.items():
        if columna not in datos.columns:
            continue
        serie = pd.to_numeric(datos[columna], errors="coerce").astype("float64")
        fuera = pd.Series(False, index=datos.index)
        if minimo is not None:
            fuera |= serie < minimo
        if maximo is not None:
            fuera |= serie > maximo
        mascara[columna] = fuera.fillna(False).astype(bool)
    return mascara


def diagnosticar_calidad(datos, nombre="conjunto", clave=None, rangos=None):
    """Calcula los indicadores de calidad pedidos y los imprime."""
    nulos = datos.isna().sum()
    fuera = mascara_fuera_de_rango(datos, rangos)
    resumen = pd.DataFrame({
        "tipo": datos.dtypes.astype(str),
        "nulos": nulos,
        "porcentaje_nulos": (nulos / len(datos) * 100).round(2),
    })
    resumen["fuera_de_rango"] = fuera.sum().reindex(resumen.index).fillna(0).astype(int)

    clave = clave or CLAVE
    indicadores = {
        "filas": len(datos),
        "columnas": datos.shape[1],
        "valores_nulos": int(nulos.sum()),
        "filas_duplicadas": int(datos.duplicated().sum()),
        "claves_repetidas": int(datos.duplicated(subset=clave).sum()),
        "valores_fuera_de_rango": int(fuera.values.sum()),
        "filas_con_valores_fuera_de_rango": int(fuera.any(axis=1).sum()),
    }

    print(f"\n=== Diagnóstico de calidad: {nombre} ===")
    for clave_ind, valor in indicadores.items():
        print(f"  {clave_ind}: {valor}")
    print("\n  Detalle por columna:")
    print(resumen.to_string())
    return indicadores, resumen


def detalle_fuera_de_rango(datos):
    """Lista los registros fuera de rango para revisarlos uno a uno."""
    fuera = mascara_fuera_de_rango(datos)
    filas = []
    for columna in fuera.columns:
        for indice in datos.index[fuera[columna]]:
            filas.append({
                "country": datos.at[indice, "country"],
                "year": datos.at[indice, "year"],
                "variable": columna,
                "valor": datos.at[indice, columna],
            })
    return pd.DataFrame(filas)


def validar_columnas(datos, esperadas):
    faltantes = [c for c in esperadas if c not in datos.columns]
    return len(faltantes) == 0, f"columnas faltantes: {faltantes}" if faltantes else "todas presentes"


def validar_tipos(datos, tipos_esperados):
    errores = [f"{c} es {datos[c].dtype}, se esperaba {t}"
               for c, t in tipos_esperados.items()
               if c in datos.columns and str(datos[c].dtype) != t]
    return len(errores) == 0, "; ".join(errores) or "tipos correctos"


def validar_rangos(datos, rangos):
    fuera = mascara_fuera_de_rango(datos, rangos)
    total = int(fuera.values.sum())
    return total == 0, f"{total} valores fuera de rango"


def validar_clave_unica(datos, clave):
    repetidas = int(datos.duplicated(subset=clave).sum())
    return repetidas == 0, f"{repetidas} claves {clave} repetidas"


def validar_sin_nulos(datos, columnas):
    nulos = datos[columnas].isna().sum()
    con_nulos = nulos[nulos > 0].to_dict()
    return not con_nulos, f"nulos en variables obligatorias: {con_nulos}" if con_nulos else "sin nulos en variables obligatorias"


def validar_dataset_final(datos, columnas, tipos, rangos, clave, obligatorias):
    """Ejecuta todas las comprobaciones y detiene el pipeline si alguna falla."""
    comprobaciones = {
        "Columnas": validar_columnas(datos, columnas),
        "Tipos": validar_tipos(datos, tipos),
        "Rangos": validar_rangos(datos, rangos),
        "Clave única": validar_clave_unica(datos, clave),
        "Obligatorias": validar_sin_nulos(datos, obligatorias),
    }
    print("\n=== Validación del conjunto final ===")
    for nombre, (ok, detalle) in comprobaciones.items():
        print(f"  [{'OK' if ok else 'ERROR'}] {nombre}: {detalle}")
    if not all(ok for ok, _ in comprobaciones.values()):
        raise ValueError("La validación falló; no se exporta el conjunto.")
    return comprobaciones
