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
    La conversión de tipos ocurre dentro del caché para que no se
    repita en cada interacción del usuario.
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
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").astype("float32")
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
st.caption("Muestra aleatoria del 10% del dataset · Fuente: SIMEM")

data = load_data()

if data is None:
    st.stop()

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Filtros")

    # Filtro de tecnología
    all_tecs = sorted(data["tipogeneracion"].dropna().unique())
    tecs = st.multiselect(
        "Tecnologías",
        options=all_tecs,
        default=all_tecs,
    )

    # Filtro de rango de fechas
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

# ── Agrupación diaria — API pandas 3.x compatible ────────────────────────────
# Se usa resample con on= en lugar de pd.Grouper para máxima compatibilidad
df_daily = (
    df_f
    .groupby("tipogeneracion", observed=True)
    .apply(
        lambda g: g.resample("D", on="fechahora")["valor"].sum(),
        include_groups=False,
    )
    .reset_index()
    .rename(columns={"fechahora": "fechahora"})
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
fig3 = px.box(
    df_f,
    x="tipogeneracion",
    y="valor",
    color="tipogeneracion",
    labels={"tipogeneracion": "Tecnología", "valor": "Generación (MWh)"},
    template="plotly_dark",
)
fig3.update_layout(showlegend=False, margin=dict(t=30, b=30))
st.plotly_chart(fig3, use_container_width=True)
