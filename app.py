import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la Aplicación
st.set_page_config(page_title="EDA Generación 10% S3", layout="wide")

@st.cache_data
def load_data_from_s3():
    """Carga datos desde S3 y retorna una muestra aleatoria del 10%"""
    path = "s3://eafit-proyecto-integrador-simem/gold/Generacion.parquet"
    
    try:
        # Cargamos solo columnas esenciales para ahorrar memoria
        df = pd.read_parquet(
            path,
            columns=["fechahora", "tipogeneracion", "valor", "nombreunidad"],
            storage_options={
                "key": st.secrets["aws"]["access_key"],
                "secret": st.secrets["aws"]["secret_key"],
                "client_kwargs": {"region_name": st.secrets["aws"]["region"]}
            },
            engine='pyarrow'
        )
        
        # Muestreo aleatorio del 10% (Garantiza fluidez en Streamlit)
        df_sample = df.sample(frac=0.10, random_state=42)
        
        # Formateo de tipos
        df_sample["fechahora"] = pd.to_datetime(df_sample["fechahora"])
        df_sample["valor"] = pd.to_numeric(df_sample["valor"], downcast="float")
        
        return df_sample

    except Exception as e:
        # Si algo falla en la conexión, mostramos el error técnico
        st.error(f"Error de conexión a S3: {e}")
        return None

# --- CUERPO PRINCIPAL ---
st.title("⚡ Análisis de Generación Eléctrica")
st.markdown("### Fuente: AWS S3 (Muestra aleatoria del 10%)")

# Intentar cargar los datos
df = load_data_from_s3()

if df is not None:
    st.success(f"Conexión exitosa. Procesando {len(df):,} registros.")

    # --- FILTROS ---
    st.sidebar.header("Filtros de Análisis")
    tecnologias = df["tipogeneracion"].unique()
    seleccion = st.sidebar.multiselect("Tipos de Tecnología", tecnologias, default=tecnologias)
    
    df_filtered = df[df["tipogeneracion"].isin(seleccion)]

    # --- VISUALIZACIONES EDA ---
    
    # Gráfica 1: Área Apilada (Composición en el tiempo)
    st.subheader("Evolución Temporal de la Matriz")
    df_daily = df_filtered.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()
    
    fig_area = px.area(
        df_daily, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        title="Generación Diaria Acumulada",
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # Gráfica 2: Facetas (Comparativa individual)
    st.subheader("Tendencias por Fuente Energética")
    fig_facet = px.line(
        df_daily, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        facet_col="tipogeneracion", 
        facet_col_wrap=2,
        title="Comparativa de Comportamiento"
    )
    fig_facet.update_yaxes(matches=None) # Escalas libres para apreciar variaciones pequeñas
    st.plotly_chart(fig_facet, use_container_width=True)

else:
    # Este bloque se ejecuta si load_data_from_s3() retorna None
    st.warning("⚠️ No hay datos disponibles. Revisa tus Access Keys en Streamlit Cloud Settings.")
