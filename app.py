import traceback
from typing import Optional
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Configuración de página
st.set_page_config(
    page_title="EDA Generación 10%",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data(show_spinner="Cargando datos desde S3...")
def load_data() -> Optional[pd.DataFrame]:
    path = "s3://eafit-proyecto-integrador-simem/gold/Generacion_10.parquet"
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
        
        # Procesamiento
        df["fechahora"] = pd.to_datetime(df["fechahora"], errors="coerce")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce") / 1000.0
        df = df.dropna(subset=["fechahora", "valor"])
        
        # Muestra aleatoria del 10%
        return df.sample(frac=0.10, random_state=42).reset_index(drop=True)

    except Exception as e:
        st.error(f"❌ Error al conectar con S3: {e}")
        st.code(traceback.format_exc())
        return None

# --- LÓGICA PRINCIPAL ---
st.title("📊 Análisis de Generación Eléctrica")
st.caption("Muestra aleatoria del 10% del dataset · Fuente: SIMEM · Unidad: MWh")

data = load_data()

# Si no hay datos, detenemos la ejecución de forma limpia
if data is None:
    st.info("Por favor, verifica tus credenciales en los Secrets.")
    st.stop()

# --- SIDEBAR - FILTROS ---
with st.sidebar:
    st.header("🔧 Filtros")
    all_tecs = sorted(data["tipogeneracion"].dropna().unique())
    tecs = st.multiselect("Tecnologías", options=all_tecs, default=all_tecs)

    f_min, f_max = data["fechahora"].min().date(), data["fechahora"].max().date()
    fecha_rango = st.date_input("Rango de fechas", value=(f_min, f_max), min_value=f_min, max_value=f_max)

# --- APLICAR FILTROS ---
df_f = data[data["tipogeneracion"].isin(tecs)].copy()

if isinstance(fecha_rango, (list, tuple)) and len(fecha_rango) == 2:
    df_f = df_f[(df_f["fechahora"].dt.date >= fecha_rango[0]) & (df_f["fechahora"].dt.date <= fecha_rango[1])]

if df_f.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados.")
    st.stop()

# --- VISUALIZACIONES ---
st.subheader("📈 Evolución Temporal por Tecnología")
df_daily = df_f.set_index("fechahora").groupby("tipogeneracion")["valor"].resample("D").sum().reset_index()

fig1 = px.area(df_daily, x="fechahora", y="valor", color="tipogeneracion", template="plotly_dark")
fig1.update_layout(hovermode="x unified")
labels={"fechahora": "Mes-Año", "valor": "Generación [MW/H]", "tipogeneracion": "Tipo de generación"})
st.plotly_chart(fig1, use_container_width=True)

st.subheader("🔍 Detalle por Tecnología")
fig2 = px.line(df_daily, x="fechahora", y="valor", color="tipogeneracion", 
               facet_col="tipogeneracion", facet_col_wrap=2, template="plotly_dark")
               labels={"fechahora": "Mes-Año", "valor": "Generación [MW/H]", "tipogeneracion": "Tipo de generación"})
fig2.update_yaxes(matches=None)
fig2.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
st.plotly_chart(fig2, use_container_width=True)

st.subheader("🏆 Top 10 Unidades")
top_10 = df_f.groupby("nombreunidad")["valor"].sum().nlargest(10).reset_index()
fig3 = px.bar(top_10, x="valor", y="nombreunidad", orientation="h", color="valor", template="plotly_dark")
st.plotly_chart(fig3, use_container_width=True)
