# ============================================
# IMPORTS
# ============================================

import pandas as pd
import numpy as np

from inline_sql import sql

import matplotlib.pyplot as plt
from matplotlib import ticker
import seaborn as sns


# ============================================
# PATH CONFIGURATION
# ============================================

DATA_PATH = "data/raw/"
PROCESSED_PATH = "data/processed/"
REPORTS_PATH = "outputs/reports/"
FIGURES_PATH = "outputs/figures/"


# ============================================
# DATA LOADING
# ============================================

lista_secciones = pd.read_csv(
    DATA_PATH + "lista-secciones.csv"
)

lista_sedes = pd.read_csv(
    DATA_PATH + "lista-sedes.csv"
)

lista_sedes_datos = pd.read_csv(
    DATA_PATH + "lista-sedes-datos.csv",
    on_bad_lines="skip"
)

migraciones = pd.read_csv(
    DATA_PATH + "migraciones.csv"
)


# ============================================
# DATA CLEANING
# ============================================

# --------------------------------------------
# lista_secciones
# --------------------------------------------

consulta_sql = """
SELECT
    sede_id,
    sede_desc_castellano AS sede,
    tipo_seccion
FROM lista_secciones
WHERE sede_id IS NOT NULL;
"""

lista_secciones_clean = sql ^ consulta_sql


# --------------------------------------------
# lista_sedes
# --------------------------------------------

consulta_sql = """
SELECT
    sede_id,
    sede_desc_castellano AS sede,
    pais_castellano AS pais,
    ciudad_castellano AS ciudad,
    estado,
    sede_tipo,
    pais_iso_3 AS iso_3
FROM lista_sedes;
"""

lista_sedes_clean = sql ^ consulta_sql


# --------------------------------------------
# lista_sedes_datos
# --------------------------------------------

consulta_sql = """
SELECT
    sede_id,
    sede_desc_castellano AS sede,
    pais_castellano AS pais,
    redes_sociales,
    pais_iso_3 AS iso_3,
    region_geografica
FROM lista_sedes_datos;
"""

sedes_data_clean = sql ^ consulta_sql


# --------------------------------------------
# migraciones - remove nulls
# --------------------------------------------

consulta_sql = """
SELECT
    CountryOriginName AS pais_origen,
    CountryOriginCode AS codigo_origen,
    CountryDestName AS pais_destino,
    CountryDestCode AS codigo_destino,
    sesentas,
    setentas,
    ochentas,
    noventas,
    dosmil
FROM migraciones
WHERE
    sesentas IS NOT NULL
    AND setentas IS NOT NULL
    AND ochentas IS NOT NULL
    AND noventas IS NOT NULL
    AND dosmil IS NOT NULL;
"""

migraciones_no_null = sql ^ consulta_sql


# --------------------------------------------
# migraciones - remove '..'
# --------------------------------------------

consulta_sql = """
SELECT
    pais_origen,
    codigo_origen,
    pais_destino,
    codigo_destino,
    CAST(sesentas AS INT) AS sesentas,
    CAST(setentas AS INT) AS setentas,
    CAST(ochentas AS INT) AS ochentas,
    CAST(noventas AS INT) AS noventas,
    CAST(dosmil AS INT) AS dosmil
FROM (
    SELECT
        pais_origen,
        codigo_origen,
        pais_destino,
        codigo_destino,
        CAST(sesentas AS STRING) AS sesentas,
        CAST(setentas AS STRING) AS setentas,
        CAST(ochentas AS STRING) AS ochentas,
        CAST(noventas AS STRING) AS noventas,
        CAST(dosmil AS STRING) AS dosmil
    FROM migraciones_no_null
) AS subquery
WHERE
    sesentas != '..'
    AND setentas != '..'
    AND ochentas != '..'
    AND noventas != '..'
    AND dosmil != '..';
"""

migraciones_clean = sql ^ consulta_sql


# --------------------------------------------
# migraciones - remove zero rows
# --------------------------------------------

consulta_sql = """
SELECT
    pais_origen,
    codigo_origen,
    pais_destino,
    codigo_destino,
    sesentas AS "1960",
    setentas AS "1970",
    ochentas AS "1980",
    noventas AS "1990",
    dosmil AS "2000"
FROM migraciones_clean
WHERE
    sesentas != 0
    AND setentas != 0
    AND ochentas != 0
    AND noventas != 0
    AND dosmil != 0;
"""

migraciones_clean = sql ^ consulta_sql


# ============================================
# MIGRATION ANALYSIS
# ============================================

# --------------------------------------------
# Average sections by country
# --------------------------------------------

consulta_sql = """
SELECT
    AVG(cantidad_secciones) AS promedio_secciones,
    iso_3
FROM (
    SELECT
        COUNT(tipo_seccion) AS cantidad_secciones,
        lista_secciones_clean.sede_id,
        iso_3
    FROM lista_secciones_clean
    INNER JOIN sedes_data_clean
        ON lista_secciones_clean.sede_id = sedes_data_clean.sede_id
    WHERE tipo_seccion = 'Seccion'
    GROUP BY lista_secciones_clean.sede_id, iso_3
)
GROUP BY iso_3;
"""

promedio_secciones = sql ^ consulta_sql


# --------------------------------------------
# Number of offices by country
# --------------------------------------------

consulta_sql = """
SELECT
    promedio_secciones.promedio_secciones,
    promedio_secciones.iso_3,
    sedes
FROM promedio_secciones
INNER JOIN (
    SELECT
        iso_3,
        COUNT(*) AS sedes
    FROM sedes_data_clean
    GROUP BY iso_3
) AS cantidad_sedes
ON promedio_secciones.iso_3 = cantidad_sedes.iso_3;
"""

secciones_sedes = sql ^ consulta_sql


# --------------------------------------------
# Net migration flow
# --------------------------------------------

consulta_sql = """
SELECT
    (cantidad_inmigracion - cantidad_emigracion)
    AS flujo_migratorio_neto,
    codigo_origen AS iso_3,
    pais_origen AS pais
FROM (
    SELECT
        pais_origen,
        codigo_origen,
        SUM("2000") AS cantidad_emigracion
    FROM migraciones_clean
    GROUP BY pais_origen, codigo_origen
) AS emigracion
INNER JOIN (
    SELECT
        pais_destino,
        codigo_destino,
        SUM("2000") AS cantidad_inmigracion
    FROM migraciones_clean
    GROUP BY pais_destino, codigo_destino
) AS inmigracion
ON emigracion.codigo_origen =
   inmigracion.codigo_destino;
"""

flujo_migratorio = sql ^ consulta_sql


# --------------------------------------------
# Final report
# --------------------------------------------

consulta_sql = """
SELECT
    pais,
    sedes,
    promedio_secciones,
    flujo_migratorio_neto
FROM secciones_sedes
INNER JOIN flujo_migratorio
ON secciones_sedes.iso_3 = flujo_migratorio.iso_3
ORDER BY sedes DESC, pais ASC;
"""

reporte_final = sql ^ consulta_sql


# ============================================
# EXPORT REPORTS
# ============================================

reporte_final.to_excel(
    REPORTS_PATH + "migration_report.xlsx",
    index=False
)


# ============================================
# SAVE CLEAN DATASETS
# ============================================

lista_secciones_clean.to_csv(
    PROCESSED_PATH + "lista_secciones_clean.csv",
    index=False
)

lista_sedes_clean.to_csv(
    PROCESSED_PATH + "lista_sedes_clean.csv",
    index=False
)

sedes_data_clean.to_csv(
    PROCESSED_PATH + "sedes_data_clean.csv",
    index=False
)

migraciones_clean.to_csv(
    PROCESSED_PATH + "migraciones_clean.csv",
    index=False
)


# ============================================
# VISUALIZATIONS
# ============================================

# --------------------------------------------
# Offices by geographic region
# --------------------------------------------

consulta_sql = """
SELECT
    region_geografica,
    COUNT(sede) AS cantidad_sedes
FROM sedes_data_clean
GROUP BY region_geografica;
"""

sedes_region = sql ^ consulta_sql

sedes_region = sedes_region.sort_values(
    by="cantidad_sedes",
    ascending=False
)

fig, ax = plt.subplots(figsize=(10, 6))

ax.bar(
    sedes_region["region_geografica"],
    sedes_region["cantidad_sedes"]
)

ax.set_xlabel("Geographic Region")
ax.set_ylabel("Number of Offices")

ax.tick_params(axis="x", rotation=90)

ax.bar_label(ax.containers[0], fontsize=8)

plt.tight_layout()

plt.savefig(
    FIGURES_PATH + "offices_by_region.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


# ============================================
# BOXPLOT - MIGRATION FLOW
# ============================================

migraciones_arg = (
    (migraciones_clean["codigo_origen"].astype(str) == "ARG")
    |
    (migraciones_clean["codigo_destino"].astype(str) == "ARG")
)

migraciones_argentina = migraciones_clean[
    migraciones_arg
]

consulta_sql = """
SELECT
    (cantidad_inmigracion - cantidad_emigracion)
    AS flujo_migratorio_neto,
    codigo_origen AS iso_3
FROM (
    SELECT
        codigo_origen,
        (
            "1960" + "1970" + "1980" +
            "1990" + "2000"
        ) AS cantidad_emigracion
    FROM migraciones_argentina
    WHERE pais_destino = 'Argentina'
) AS emigracion
INNER JOIN (
    SELECT
        codigo_destino,
        (
            "1960" + "1970" + "1980" +
            "1990" + "2000"
        ) AS cantidad_inmigracion
    FROM migraciones_argentina
    WHERE pais_origen = 'Argentina'
) AS inmigracion
ON emigracion.codigo_origen =
   inmigracion.codigo_destino;
"""

flujo_total = sql ^ consulta_sql


consulta_sql = """
SELECT
    AVG(flujo_migratorio_neto) AS flujo_migratorio,
    region_geografica,
    flujo_total.iso_3
FROM flujo_total
INNER JOIN (
    SELECT DISTINCT
        region_geografica,
        iso_3
    FROM sedes_data_clean
) AS region
ON flujo_total.iso_3 = region.iso_3
GROUP BY region_geografica, flujo_total.iso_3;
"""

migracion_region = sql ^ consulta_sql


medianas = (
    migracion_region
    .groupby("region_geografica")["flujo_migratorio"]
    .median()
    .sort_values()
)

migracion_region["region_geografica"] = pd.Categorical(
    migracion_region["region_geografica"],
    categories=medianas.index,
    ordered=True
)

plt.figure(figsize=(10, 6))

sns.boxplot(
    x="region_geografica",
    y="flujo_migratorio",
    data=migracion_region
)

plt.title("Migration Flow by Geographic Region")

plt.xlabel("Region")
plt.ylabel("Migration Flow")

plt.xticks(rotation=60)

plt.gca().yaxis.set_major_formatter(
    ticker.FuncFormatter(
        lambda x, _: f"{int(x):,}"
    )
)

plt.tight_layout()

plt.savefig(
    FIGURES_PATH + "migration_boxplot.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()