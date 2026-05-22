import traceback
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="EDA Generación 10%",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Cargando datos desde S3...")
def load_data() -> Optional[pd.DataFrame]:
    """
    Carga el parquet desde S3, convierte tipos y retorna
    una muestra aleatoria del 10% (reproducible con random_state=42).
    """
    path = "s3://eafit-proyecto-integrador-simem/gold/Generacion.parquet"
    try:
        df = pd.read_parquet(
            path,
            columns=["fechahora", "tipogeneracion", "valor", "nombreunidad"],
            storage_options={
                "key": st.secrets["aws"]["access_key"],
                "secret": st.secrets["aws"]["secret_key"],
                "client_kwargs": {"region_name": st.secrets["aws"]["region"]},
            },
        )

        # Conversión de tipos dentro del caché (se ejecuta solo una vez)
        df["fechahora"] = pd.to_datetime(df["fechahora"], errors="coerce")
        # valor viene como kWh — convertir a MWh
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce") / 1000.0
        df = df.dropna(subset=["fechahora", "valor"])

        # Muestra aleatoria del 10% — reproducible
        return df.sample(frac=0.10, random_state=42).reset_index(drop=True)

    except Exception as e:
        st.error(f"❌ Error al conectar con S3: {e}")
        st.code(traceback.format_exc())
        st.info("Verifica las Access Keys en **Settings › Secrets**.")
        return None


# ── Título ────────────────────────────────────────────────────────────────────
st.title("📊 Análisis de Generación Eléctrica")
st.caption("Muestra aleatoria del 10% del dataset · Fuente: SIMEM · Unidad: MWh")

data = load_data()

if data is None:
    st.stop()

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Filtros")

    all_tecs = sorted(data["tipogeneracion"].dropna().unique())
    tecs = st.multiselect(
        "Tecnologías",
        options=all_tecs,
        default=all_tecs,
    )

    fecha_min = data["fechahora"].min().date()
    fecha_max = data["fechahora"].max().date()
    fecha_rango = st.date_input(
        "Rango de fechas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
    )

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df_f = data[data["tipogeneracion"].isin(tecs)].copy()

if isinstance(fecha_rango, (list, tuple)) and len(fecha_rango) == 2:
    f_inicio = pd.Timestamp(fecha_rango[0])
    f_fin = pd.Timestamp(fecha_rango[1])
    df_f = df_f[(df_f["fechahora"] >= f_inicio) & (df_f["fechahora"] <= f_fin)]

if df_f.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados.")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros (muestra)", f"{len(df_f):,}")
col2.metric("Tecnologías", df_f["tipogeneracion"].nunique())
col3.metric("Generación total (MWh)", f"{df_f['valor'].sum():,.0f}")
col4.metric("Promedio por registro (MWh)", f"{df_f['valor'].mean():,.1f}")

st.divider()

# ── Agrupación diaria ─────────────────────────────────────────────────────────
# Usamos resample sobre el índice datetime — compatible con pandas 2.2 y 3.x
df_daily = (
    df_f
    .set_index("fechahora")
    .groupby("tipogeneracion", observed=True)["valor"]
    .resample("D")
    .sum()
    .reset_index()
)

# ── 1. Evolución temporal — Área apilada ──────────────────────────────────────
st.subheader("📈 Evolución Temporal por Tecnología")
fig1 = px.area(
    df_daily,
    x="fechahora",
    y="valor",
    color="tipogeneracion",
    labels={
        "fechahora": "Fecha",
        "valor": "Generación (MWh)",
        "tipogeneracion": "Tecnología",
    },
    template="plotly_dark",
)
fig1.update_layout(
    legend_title_text="Tecnología",
    hovermode="x unified",
    margin=dict(t=30, b=30),
)
st.plotly_chart(fig1, use_container_width=True)

# ── 2. Detalle por tecnología — Facetas ───────────────────────────────────────
st.subheader("🔍 Detalle por Tecnología")
n_tecs = df_daily["tipogeneracion"].nunique()
fig2 = px.line(
    df_daily,
    x="fechahora",
    y="valor",
    color="tipogeneracion",
    facet_col="tipogeneracion",
    facet_col_wrap=min(2, n_tecs),
    labels={"fechahora": "Fecha", "valor": "MWh", "tipogeneracion": "Tecnología"},
    template="plotly_dark",
)
fig2.update_yaxes(matches=None, showticklabels=True)
fig2.update_xaxes(showticklabels=True)
fig2.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig2.update_layout(showlegend=False, margin=dict(t=40, b=30))
st.plotly_chart(fig2, use_container_width=True)

# ── 3. Distribución — Boxplot ─────────────────────────────────────────────────
st.subheader("📦 Distribución de Valores por Tecnología")
# Excluimos ceros para que el boxplot sea más informativo
df_nonzero = df_f[df_f["valor"] > 0]
fig3 = px.box(
    df_nonzero,
    x="tipogeneracion",
    y="valor",
    color="tipogeneracion",
    labels={"tipogeneracion": "Tecnología", "valor": "Generación (MWh)"},
    template="plotly_dark",
)
fig3.update_layout(showlegend=False, margin=dict(t=30, b=30))
st.plotly_chart(fig3, use_container_width=True)

# ── 4. Top unidades generadoras ───────────────────────────────────────────────
st.subheader("🏆 Top 10 Unidades Generadoras")
top_unidades = (
    df_f.groupby("nombreunidad", observed=True)["valor"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)
fig4 = px.bar(
    top_unidades,
    x="valor",
    y="nombreunidad",
    orientation="h",
    labels={"valor": "Generación total (MWh)", "nombreunidad": "Unidad"},
    template="plotly_dark",
    color="valor",
    color_continuous_scale="Blues",
)
fig4.update_layout(
    yaxis=dict(categoryorder="total ascending"),
    coloraxis_showscale=False,
    margin=dict(t=30, b=30),
)
st.plotly_chart(fig4, use_container_width=True)
