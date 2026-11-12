"""Dashboard interactivo de emisiones de CO2 (Avance 4).

Ejecutar desde la raíz del repositorio:

    streamlit run app.py

Requiere datos/procesados/dataset_limpio.csv (lo genera python main.py).
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.estadisticas import cargar_dataset_limpio
from src.proyeccion import (GRUPOS, MODELOS, VARIABLES, evaluar_modelos, proyectar,
                            r2_lineal, serie_entidad, tasa_crecimiento_promedio)

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a la raíz del repositorio
RUTA_LIMPIO = os.path.join("datos", "procesados", "dataset_limpio.csv")
VISTAS = ["Exploración histórica", "Proyección", "Interpretación"]
COLOR_PRINCIPAL = "#c0392b"
COLORES = ["#2f6db3", "#e08e0b", "#5b8c5a", "#8a5ab3", "#8a94a3", "#2a9d8f"]
COLORES_MODELO = {"Regresión lineal": "#2f6db3", "Promedio móvil": "#e08e0b",
                  "Tasa de crecimiento promedio": "#5b8c5a"}

st.set_page_config(page_title="Emisiones de CO2 · Grupo 7", page_icon="🌎", layout="wide")


def num(valor, decimales=2):
    """Número con formato chileno: 12.345,67."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def parametro_url(nombre, opciones, defecto):
    """Valor inicial desde la URL (?vista=...), útil para compartir una vista."""
    valor = st.query_params.get(nombre)
    return opciones.index(valor) if valor in opciones else opciones.index(defecto)


@st.cache_data
def cargar():
    return cargar_dataset_limpio(RUTA_LIMPIO)


def mostrar(fig):
    st.pyplot(fig)
    plt.close(fig)  # libera memoria: Streamlit vuelve a ejecutar el script en cada cambio


def estilo(ax, titulo, ylabel, xlabel="Año"):
    ax.set_title(titulo, fontsize=12, weight="bold", loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e3e6ea")
    ax.set_axisbelow(True)


if not os.path.exists(RUTA_LIMPIO):
    st.error("No se encontró datos/procesados/dataset_limpio.csv. Ejecuta primero: python main.py")
    st.stop()

datos = cargar()
paises = sorted(datos["pais"].unique())

# ======================= Barra lateral: filtros y parámetros =======================
st.sidebar.title("🌎 Emisiones de CO2")
vista = st.sidebar.radio("Vista", VISTAS, index=parametro_url("vista", VISTAS, VISTAS[0]))

st.sidebar.header("Filtros")
claves_var = list(VARIABLES)
variable = st.sidebar.selectbox(
    "Variable analizada", claves_var, index=parametro_url("variable", claves_var, "co2_per_capita_t"),
    format_func=lambda v: f"{VARIABLES[v][0]} ({VARIABLES[v][1]})")
etiqueta, unidad, _ = VARIABLES[variable]
pais = st.sidebar.selectbox("País principal", paises, index=parametro_url("pais", paises, "Chile"))
opciones_comparar = list(GRUPOS) + [p for p in paises if p != pais]
comparar = st.sidebar.multiselect(
    "Comparar con (grupos o países)", opciones_comparar,
    default=["Pares latinoamericanos (promedio)", "OCDE (promedio)", "Mundo (suma de países)"])
anio_max_datos = 2022 if variable == "co2_por_pib_kg_usd" else 2024
desde, hasta = st.sidebar.slider("Período", 1990, anio_max_datos, (1990, anio_max_datos))

st.sidebar.header("Parámetros de proyección")
opciones_modelo = MODELOS + ["Comparar los tres"]
modelo = st.sidebar.radio("Modelo", opciones_modelo,
                          index=parametro_url("modelo", opciones_modelo, "Comparar los tres"))
horizonte = st.sidebar.slider("Años a proyectar", 1, 2050 - hasta, min(11, 2050 - hasta))
anios_base = st.sidebar.slider("Años de historia usados para ajustar", 5, hasta - desde + 1,
                               min(15, hasta - desde + 1),
                               help="Pocos años captan la tendencia reciente; muchos, la de largo plazo.")
ventana = st.sidebar.slider("Ventana del promedio móvil (años)", 2, 10, 5)
st.sidebar.caption("Datos: Our World in Data (CC BY 4.0) · Grupo 7, Programación Avanzada")

# ======================= Cálculos comunes =======================
serie = serie_entidad(datos, pais, variable).loc[desde:hasta]
if len(serie) < 3:
    st.warning(f"{pais} no tiene suficientes datos de {etiqueta} en el período elegido.")
    st.stop()
entrenamiento = serie.iloc[-anios_base:]
anios_futuros = list(range(serie.index[-1] + 1, serie.index[-1] + horizonte + 1))
modelos_activos = MODELOS if modelo == "Comparar los tres" else [modelo]
proyecciones = {m: proyectar(entrenamiento, m, anios_futuros, ventana) for m in modelos_activos}

st.title(f"{etiqueta} de {pais}, {desde}–{hasta}")
st.caption("¿Cómo se comparan las emisiones de CO2 entre países y qué posición ocupa Chile frente a "
           "América Latina y la OCDE? Cambia los filtros de la izquierda para explorar.")

# ======================= Indicadores dinámicos =======================
inicio, final = serie.iloc[0], serie.iloc[-1]
variacion = (final / inicio - 1) * 100 if inicio else float("nan")
cagr = tasa_crecimiento_promedio(serie) * 100
anio_maximo = int(serie.idxmax())
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"Valor {serie.index[-1]} ({unidad})", num(final),
          f"{num(final - serie.iloc[-2])} vs año anterior", delta_color="inverse")
c2.metric(f"Variación {serie.index[0]}–{serie.index[-1]}", f"{num(variacion, 1)} %")
c3.metric("Crecimiento anual promedio", f"{num(cagr, 2)} %")
c4.metric(f"Promedio del período ({unidad})", num(serie.mean()))
c5.metric(f"Máximo, en {anio_maximo} ({unidad})", num(serie.max()))

# ======================= Vista 1: exploración histórica =======================
if vista == "Exploración histórica":
    col_izq, col_der = st.columns([3, 2])
    with col_izq:
        fig, ax = plt.subplots(figsize=(8, 4.4))
        ax.plot(serie.index, serie.values, color=COLOR_PRINCIPAL, linewidth=2.8, label=pais)
        for i, entidad in enumerate(comparar):
            otra = serie_entidad(datos, entidad, variable).loc[desde:hasta]
            ax.plot(otra.index, otra.values, color=COLORES[i % len(COLORES)], linewidth=1.6, label=entidad)
        estilo(ax, f"Evolución histórica: {etiqueta}", f"{etiqueta} ({unidad})")
        ax.set_ylim(0, None)
        ax.legend(frameon=False, fontsize=8)
        mostrar(fig)

    with col_der:
        anio_ranking = serie.index[-1]
        corte = datos[datos["anio"] == anio_ranking].dropna(subset=[variable])
        top = corte.nlargest(10, variable)
        if pais not in top["pais"].values:
            top = pd.concat([top, corte[corte["pais"] == pais]])
        top = top.iloc[::-1]
        puesto = int(corte[variable].rank(ascending=False, method="min")[corte["pais"] == pais].iloc[0])
        fig, ax = plt.subplots(figsize=(5.6, 6.2))
        ax.barh(top["pais"], top[variable],
                color=[COLOR_PRINCIPAL if p == pais else "#9fb4cf" for p in top["pais"]])
        estilo(ax, f"Ranking {anio_ranking}: {pais} en el puesto {puesto} de {len(corte)}",
               "País", f"{etiqueta} ({unidad})")
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color="#e3e6ea")
        mostrar(fig)

    pais_datos = datos[(datos["pais"] == pais) & datos["anio"].between(desde, hasta)].set_index("anio")
    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.stackplot(pais_datos.index, pais_datos["co2_carbon_mt"].fillna(0), pais_datos["co2_petroleo_mt"].fillna(0),
                 pais_datos["co2_gas_mt"].fillna(0), labels=["Carbón", "Petróleo", "Gas"],
                 colors=["#4d4d4d", "#e08e0b", "#2f6db3"], alpha=0.85)
    estilo(ax, f"Composición de las emisiones de {pais} por combustible", "CO2 (Mt)")
    ax.legend(frameon=False, loc="upper left", ncol=3)
    mostrar(fig)

    with st.expander("Ver y descargar los datos filtrados"):
        tabla = pd.DataFrame({pais: serie})
        for entidad in comparar:
            tabla[entidad] = serie_entidad(datos, entidad, variable).loc[desde:hasta]
        st.dataframe(tabla.round(3), width="stretch")
        st.download_button("Descargar CSV", tabla.to_csv().encode("utf-8"),
                           file_name=f"{variable}_{pais}_{desde}_{hasta}.csv", mime="text/csv")

# ======================= Vista 2: proyección =======================
elif vista == "Proyección":
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(serie.index, serie.values, color="#14213d", linewidth=2.4, label=f"{pais} (histórico)")
    ax.axvspan(entrenamiento.index[0], entrenamiento.index[-1], color="#2f6db3", alpha=0.07,
               label=f"Años usados para ajustar ({entrenamiento.index[0]}–{entrenamiento.index[-1]})")
    orden = sorted(proyecciones, key=lambda m: proyecciones[m].iloc[-1], reverse=True)
    for m, pred in proyecciones.items():
        x = [serie.index[-1]] + list(pred.index)
        y = [serie.iloc[-1]] + list(pred.values)
        ax.plot(x, y, color=COLORES_MODELO[m], linewidth=2.2, linestyle="--", label=f"Proyección: {m}")
        # etiquetas separadas verticalmente para que no se monten
        ax.annotate(f"{num(pred.iloc[-1])}", (pred.index[-1], pred.iloc[-1]), xytext=(6, 9 - 9 * orden.index(m)),
                    textcoords="offset points", color=COLORES_MODELO[m], fontsize=9, va="center", weight="bold")
    ax.axvline(serie.index[-1] + 0.5, color="#8a94a3", linewidth=0.8)
    estilo(ax, f"Proyección de {etiqueta} de {pais} hasta {anios_futuros[-1]}", f"{etiqueta} ({unidad})")
    ax.set_ylim(0, None)
    ax.legend(frameon=True, facecolor="white", edgecolor="none", fontsize=9, loc="lower right")
    mostrar(fig)

    cols = st.columns(len(proyecciones))
    for col, (m, pred) in zip(cols, proyecciones.items()):
        cambio = (pred.iloc[-1] / serie.iloc[-1] - 1) * 100
        col.metric(f"{m} → {pred.index[-1]}", f"{num(pred.iloc[-1])} {unidad}",
                   f"{num(cambio, 1)} % vs {serie.index[-1]}", delta_color="inverse")

    st.subheader("¿Qué tan confiable es cada modelo?")
    evaluacion = evaluar_modelos(serie, anios_base, anios_prueba=5, ventana=ventana)
    izq, der = st.columns([2, 3])
    with izq:
        if evaluacion.empty:
            st.info("El período es demasiado corto para validar los modelos.")
        else:
            st.dataframe(evaluacion.assign(MAE=evaluacion["MAE"].round(3),
                                           **{"MAPE_%": evaluacion["MAPE_%"].round(1)}),
                         hide_index=True, width="stretch")
            st.caption("Validación retrospectiva: se ocultan los últimos 5 años, cada modelo los "
                       "proyecta y se mide el error. MAPE = error porcentual promedio (menor es mejor).")
        st.metric("R² del ajuste lineal", num(r2_lineal(entrenamiento), 3),
                  help="Qué parte de la variación histórica explica una línea recta (1 = perfecta).")
    with der:
        tabla = pd.DataFrame(proyecciones)
        tabla.index.name = "Año"
        st.dataframe(tabla.round(3), width="stretch", height=260)
        st.download_button("Descargar proyección (CSV)", tabla.to_csv().encode("utf-8"),
                           file_name=f"proyeccion_{variable}_{pais}.csv", mime="text/csv")

# ======================= Vista 3: interpretación =======================
else:
    evaluacion = evaluar_modelos(serie, anios_base, anios_prueba=5, ventana=ventana)
    tendencia_reciente = tasa_crecimiento_promedio(serie.iloc[-6:]) * 100
    st.subheader("Respuesta a la pregunta del proyecto")
    filas = []
    for entidad in [pais] + comparar:
        s = serie_entidad(datos, entidad, variable).loc[desde:hasta]
        if len(s):
            filas.append({"País o grupo": entidad, f"{s.index[-1]} ({unidad})": round(s.iloc[-1], 3),
                          f"Variación {s.index[0]}–{s.index[-1]} (%)": round((s.iloc[-1] / s.iloc[0] - 1) * 100, 1)})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")

    st.markdown(f"""
**¿Qué tendencia histórica se observa?** Entre {serie.index[0]} y {serie.index[-1]}, el {etiqueta} de
{pais} pasó de {num(inicio)} a {num(final)} {unidad} ({num(variacion, 1)} %, un promedio de {num(cagr, 2)} % por año).
Su máximo fue en {anio_maximo}. En los últimos cinco años la tendencia es de {num(tendencia_reciente, 2)} % anual,
{"a la baja" if tendencia_reciente < 0 else "al alza"}.

**¿Qué proyecta el modelo?** Al año {anios_futuros[-1]}: """ + "; ".join(
        f"{m.lower()}, {num(p.iloc[-1])} {unidad}" for m, p in proyecciones.items()) + ".")

    if not evaluacion.empty:
        mejor = evaluacion.iloc[0]
        st.markdown(f"""
**¿Qué tan confiable es la proyección?** Al ocultar los últimos 5 años, el modelo con menor error fue
**{mejor['modelo'].lower()}** (MAPE de {num(mejor['MAPE_%'], 1)} %). El R² de la recta ajustada con {anios_base} años
es {num(r2_lineal(entrenamiento), 3)}. Son modelos de una sola variable (el tiempo): sirven como escenarios, no como
pronósticos, porque no consideran políticas, crecimiento económico ni shocks como la pandemia de 2020.

**¿Qué método entrega resultados más razonables?** Para este problema, el que mejor reproduce los últimos años es
**{mejor['modelo'].lower()}**. La regresión lineal y la tasa de crecimiento extienden la tendencia de los años de
ajuste: si se usan 1990–2024 proyectan un aumento que ya no se observa desde 2019; el promedio móvil supone que el
nivel reciente se mantiene, lo que es más prudente para una serie que cambió de dirección.
""")
    st.markdown("""
**¿Qué información faltante podría mejorar los resultados?** PIB y población proyectados, el plan de retiro de
centrales a carbón, la participación de energías renovables y las metas de la NDC, además de datos de 2023–2024
consolidados (las cifras de 2024 son preliminares y el PIB llega solo a 2022).
""")
