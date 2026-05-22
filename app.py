import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="EDA Generación - Muestra 10%", layout="wide")

@st.cache_data
def load_data_sample():
    # URL de S3 (ajusta según tu bucket y archivo final)
    path = "s3://eafit-proyecto-integrador-simem/gold/"
    
    try:
        # Cargamos el 10% aleatorio usando el motor pyarrow
        # Nota: read_parquet no tiene 'sample' nativo, cargamos columnas clave y luego muestreamos
        # para ser ultra eficientes con la memoria de Streamlit
        df = pd.read_parquet(
            path,
            columns=["fechahora", "tipogeneracion", "valor", "nombreunidad", "codigoplanta"],
            storage_options={
                "key": st.secrets["aws"]["access_key"],
                "secret": st.secrets["aws"]["secret_key"],
                "client_kwargs": {"region_name": st.secrets["aws"]["region"]}
            }
        )
        
        # Selección aleatoria del 10%
        df_sample = df.sample(frac=0.10, random_state=42)
        
        # Formateo de tipos
        df_sample["fechahora"] = pd.to_datetime(df_sample["fechahora"])
        df_sample["valor"] = pd.to_numeric(df_sample["valor"], downcast="float")
        
        return df_sample
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# Carga de la muestra
df = load_data_sample()

if df is not None:
    st.title("📊 Análisis Exploratorio (Muestra Aleatoria 10%)")
    st.markdown(f"Trabajando con una muestra representativa de **{len(df):,}** registros.")

    # --- MÉTRICAS RÁPIDAS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Generación Total (Muestra)", f"{df['valor'].sum():,.2f} kWh")
    m2.metric("Plantas Únicas", df["codigoplanta"].nunique())
    m3.metric("Tipos de Tecnología", df["tipogeneracion"].nunique())

    # --- VISUALIZACIÓN EXPLORATORIA ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribución por Tecnología")
        fig_pie = px.pie(df, names='tipogeneracion', values='valor', 
                         hole=0.4, title="Participación en la Generación")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Top 10 Unidades Generadoras")
        top_unidades = df.groupby("nombreunidad")["valor"].sum().nlargest(10).reset_index()
        fig_bar = px.bar(top_unidades, x="valor", y="nombreunidad", orientation='h',
                         color="valor", color_continuous_scale="Viridis")
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- ANÁLISIS TEMPORAL ---
    st.subheader("Evolución de la Generación en el Tiempo")
    # Agrupamos por día para suavizar la gráfica y mejorar el rendimiento del navegador
    df_ts = df.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()
    
    fig_ts = px.line(df_ts, x="fechahora", y="valor", color="tipogeneracion",
                     title="Tendencia Diaria por Fuente de Energía")
    st.plotly_chart(fig_ts, use_container_width=True)

    # --- TABLA DE DATOS CRUDA (MUESTRA) ---
    with st.expander("Ver datos de la muestra"):
        st.dataframe(df.head(100))

else:
    st.warning("No se pudieron cargar los datos. Verifica tus credenciales en Secrets y la ruta de S3.")
