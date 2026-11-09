"""Gráficos del análisis con Matplotlib Pyplot, exportados como PNG."""

import os

import matplotlib

matplotlib.use("Agg")  # genera archivos sin abrir ventanas
import matplotlib.pyplot as plt

from src.indicadores import ANIO_FINAL, ANIO_PIB, PAIS_FOCO, promedio_ponderado_per_capita
from src.transformaciones import OCDE, PARES_LATAM

COLOR_CHILE = "#c0392b"
COLOR_BASE = "#2f6db3"
COLOR_GRIS = "#8a94a3"
COLORES_GRUPO = {
    "Chile": COLOR_CHILE,
    "America Latina (pares)": "#e08e0b",
    "OCDE": COLOR_BASE,
    "Resto del mundo": "#b0b7c3",
}


def estilo_ejes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e3e6ea", linewidth=0.8)
    ax.set_axisbelow(True)


def guardar(fig, carpeta, nombre):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    print(f"  Gráfico guardado: {ruta}")
    return ruta


def grafico_mayores_emisores(datos, carpeta):
    """Barras: los 10 países con más emisiones totales en el último año."""
    corte = datos[datos["anio"] == ANIO_FINAL].nlargest(10, "co2_mt").iloc[::-1]
    total = datos.loc[datos["anio"] == ANIO_FINAL, "co2_mt"].sum()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    barras = ax.barh(corte["pais"], corte["co2_mt"], color=COLOR_BASE, label="Emisiones del país")
    for barra, valor in zip(barras, corte["co2_mt"]):
        ax.text(valor + total * 0.004, barra.get_y() + barra.get_height() / 2,
                f"{valor:,.0f} Mt ({valor / total * 100:.1f} %)".replace(",", "."),
                va="center", fontsize=9)
    ax.set_title(f"Los 10 mayores emisores de CO2 en {ANIO_FINAL}", fontsize=13, weight="bold")
    ax.set_xlabel("Emisiones de CO2 (millones de toneladas, Mt)")
    ax.set_ylabel("País")
    ax.set_xlim(0, corte["co2_mt"].max() * 1.25)
    estilo_ejes(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#e3e6ea", linewidth=0.8)
    ax.legend(frameon=False, loc="lower right")
    return guardar(fig, carpeta, "grafico_01.png")


def grafico_evolucion_per_capita(datos, carpeta):
    """Líneas: CO2 per cápita de Chile frente a sus grupos de comparación."""
    series = {
        "Chile": datos[datos["iso_code"] == PAIS_FOCO].set_index("anio")["co2_per_capita_t"],
        "Pares latinoamericanos (promedio)": datos[datos["iso_code"].isin(PARES_LATAM)]
            .groupby("anio").apply(promedio_ponderado_per_capita),
        "OCDE (promedio, 38 países)": datos[datos["iso_code"].isin(OCDE)]
            .groupby("anio").apply(promedio_ponderado_per_capita),
        "Mundo (promedio)": datos.groupby("anio").apply(promedio_ponderado_per_capita),
    }
    estilos = {"Chile": (COLOR_CHILE, "-", 2.8), "Pares latinoamericanos (promedio)": ("#e08e0b", "-", 1.8),
               "OCDE (promedio, 38 países)": (COLOR_BASE, "-", 1.8), "Mundo (promedio)": (COLOR_GRIS, "--", 1.8)}
    fig, ax = plt.subplots(figsize=(9, 5))
    for nombre, serie in series.items():
        color, linea, ancho = estilos[nombre]
        ax.plot(serie.index, serie.values, color=color, linestyle=linea, linewidth=ancho, label=nombre)
    chile = series["Chile"]
    ax.annotate(f"{chile.iloc[-1]:.2f} t", (chile.index[-1], chile.iloc[-1]),
                xytext=(6, 0), textcoords="offset points", color=COLOR_CHILE, va="center", fontsize=9)
    ax.set_title("Evolución del CO2 per cápita: Chile frente a sus grupos de comparación (1990-2024)",
                 fontsize=12, weight="bold")
    ax.set_xlabel("Año")
    ax.set_ylabel("CO2 per cápita (toneladas por persona)")
    ax.set_ylim(0, None)
    estilo_ejes(ax)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 0.92), fontsize=9)
    return guardar(fig, carpeta, "grafico_02.png")


def grafico_pib_vs_emisiones(datos, carpeta):
    """Dispersión: riqueza por habitante frente a emisiones por habitante."""
    corte = datos[datos["anio"] == ANIO_PIB].dropna(subset=["pib_per_capita_usd", "co2_per_capita_t"])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    etiquetas = {"America Latina (pares)": "América Latina (pares)"}
    for grupo in ["Resto del mundo", "OCDE", "America Latina (pares)", "Chile"]:
        sub = corte[corte["grupo_comparacion"] == grupo]
        ax.scatter(sub["pib_per_capita_usd"], sub["co2_per_capita_t"],
                   s=90 if grupo == "Chile" else 28, color=COLORES_GRUPO[grupo],
                   edgecolor="white", linewidth=0.5, label=etiquetas.get(grupo, grupo),
                   zorder=3 if grupo == "Chile" else 2)
    # Desplazamientos manuales para que los nombres no se superpongan.
    desplazamientos = {"Chile": (0, 22), "Argentina": (8, 10), "Mexico": (-48, 8),
                       "Brazil": (-8, -14), "Colombia": (-60, -4), "Peru": (-34, 9)}
    for _, fila in corte[corte["grupo_comparacion"].isin(["Chile", "America Latina (pares)"])].iterrows():
        ax.annotate(fila["pais"], (fila["pib_per_capita_usd"], fila["co2_per_capita_t"]),
                    xytext=desplazamientos.get(fila["pais"], (5, 3)), textcoords="offset points",
                    fontsize=8.5, weight="bold" if fila["pais"] == "Chile" else "normal",
                    arrowprops={"arrowstyle": "-", "color": COLOR_GRIS, "linewidth": 0.6})
    ax.set_xscale("log")
    ax.set_title(f"PIB per cápita y CO2 per cápita por país ({ANIO_PIB})", fontsize=13, weight="bold")
    ax.set_xlabel("PIB per cápita (dólares internacionales PPA, escala logarítmica)")
    ax.set_ylabel("CO2 per cápita (toneladas por persona)")
    estilo_ejes(ax)
    ax.legend(frameon=False, title="Grupo", loc="upper left")
    return guardar(fig, carpeta, "grafico_03.png")


def grafico_caja_grupos(datos, carpeta):
    """Caja: distribución del CO2 per cápita por grupo e identificación de extremos."""
    corte = datos[datos["anio"] == ANIO_FINAL].dropna(subset=["co2_per_capita_t"])
    latam = corte["grupo_comparacion"].isin(["Chile", "America Latina (pares)"])
    grupos = {
        "OCDE\n(sin Chile, COL, MEX)": corte.loc[corte["grupo_comparacion"] == "OCDE", "co2_per_capita_t"],
        "América Latina\n(Chile y pares)": corte.loc[latam, "co2_per_capita_t"],
        "Resto del mundo": corte.loc[corte["grupo_comparacion"] == "Resto del mundo", "co2_per_capita_t"],
    }
    fig, ax = plt.subplots(figsize=(9, 5.5))
    caja = ax.boxplot(list(grupos.values()), patch_artist=True, widths=0.5,
                      medianprops={"color": "black"}, flierprops={"markersize": 4, "markerfacecolor": COLOR_GRIS})
    ax.set_xticks(range(1, len(grupos) + 1), list(grupos.keys()))
    for parche, color in zip(caja["boxes"], [COLOR_BASE, "#e08e0b", "#b0b7c3"]):
        parche.set_facecolor(color)
        parche.set_alpha(0.75)
    chile = corte.loc[corte["iso_code"] == PAIS_FOCO, "co2_per_capita_t"].iloc[0]
    ax.scatter([2], [chile], color=COLOR_CHILE, s=70, zorder=3, label=f"Chile ({chile:.2f} t)")
    resto = corte[corte["grupo_comparacion"] == "Resto del mundo"].nlargest(3, "co2_per_capita_t")
    for (_, fila), dy in zip(resto.iterrows(), [0, 6, -6]):
        ax.annotate(f"{fila['pais']} ({fila['co2_per_capita_t']:.1f} t)", (3, fila["co2_per_capita_t"]),
                    xytext=(8, dy), textcoords="offset points", fontsize=8, va="center")
    ax.set_title(f"Distribución del CO2 per cápita por grupo de países ({ANIO_FINAL})",
                 fontsize=13, weight="bold")
    ax.set_xlabel("Grupo de países")
    ax.set_ylabel("CO2 per cápita (toneladas por persona)")
    estilo_ejes(ax)
    ax.legend(frameon=False, loc="upper left")
    return guardar(fig, carpeta, "grafico_04.png")


def grafico_combustibles_chile(datos, carpeta):
    """Área apilada: composición por combustible de las emisiones de Chile."""
    chile = datos[datos["iso_code"] == PAIS_FOCO].set_index("anio")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(chile.index, chile["co2_carbon_mt"], chile["co2_petroleo_mt"], chile["co2_gas_mt"],
                 labels=["Carbón", "Petróleo", "Gas"], colors=["#4d4d4d", "#e08e0b", COLOR_BASE], alpha=0.85)
    ax.plot(chile.index, chile["co2_mt"], color="black", linewidth=1.2, linestyle=":",
            label="Total (incluye cemento y otros)")
    ax.set_title("Chile: emisiones de CO2 por combustible (1990-2024)", fontsize=13, weight="bold")
    ax.set_xlabel("Año")
    ax.set_ylabel("Emisiones de CO2 (millones de toneladas, Mt)")
    estilo_ejes(ax)
    ax.legend(frameon=False, loc="upper left")
    return guardar(fig, carpeta, "grafico_05.png")


GRAFICOS = [grafico_mayores_emisores, grafico_evolucion_per_capita, grafico_pib_vs_emisiones,
            grafico_caja_grupos, grafico_combustibles_chile]


def generar_graficos(datos, carpeta):
    print("\n=== Gráficos ===")
    return [funcion(datos, carpeta) for funcion in GRAFICOS]
