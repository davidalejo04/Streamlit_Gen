import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración inicial
st.set_page_config(page_title="Dashboard Generación EAFIT", layout="wide")

@st.cache_data
def load_data_optimized():
    # URL de S3 en formato protocolo
    path = "s3://eafit-proyecto-integrador-simem/gold/Generacion.parquet"
    
    # 1. ESPECIFICAR COLUMNAS: Esto reduce drásticamente el uso de RAM
    columnas_necesarias = ["fechahora", "tipogeneracion", "valor"]
    
    try:
        df = pd.read_parquet(
            path,
            columns=columnas_necesarias,
            storage_options={
                "key": st.secrets["aws"]["access_key"],
                "secret": st.secrets["aws"]["secret_key"],
                "client_kwargs": {"region_name": st.secrets["aws"]["region"]}
            },
            engine='pyarrow'
        )
        
        # 2. OPTIMIZACIÓN DE TIPOS (Downcasting)
        # Convertimos 'valor' a float32 para ahorrar el 50% de espacio en esa columna
        df["valor"] = pd.to_numeric(df["valor"], downcast="float")
        df["fechahora"] = pd.to_datetime(df["fechahora"])
        
        return df
    except Exception as e:
        st.error(f"Error al conectar con S3: {e}")
        return None

# Ejecución de la carga
df_raw = load_data_optimized()

if df_raw is not None:
    st.title("⚡ Análisis de Generación Real - Proyecto Integrador")

    # 3. FILTROS LATERALES PARA REDUCIR DATOS EN PANTALLA
    st.sidebar.header("Filtros de Visualización")
    tecnologias = st.sidebar.multiselect(
        "Selecciona Tecnologías", 
        options=df_raw["tipogeneracion"].unique(),
        default=df_raw["tipogeneracion"].unique()
    )

    # Filtrado dinámico
    mask = df_raw["tipogeneracion"].isin(tecnologias)
    df_filtered = df_raw[mask]

    # 4. AGREGACIÓN TEMPORAL (Crucial para no congelar el navegador)
    # En lugar de graficar cada punto, graficamos el promedio por hora o día
    st.subheader("Tendencia Temporal (Agregada)")
    
    df_resumen = df_filtered.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()

    # Gráfica Bonita con Plotly
    fig = px.line(
        df_resumen, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        title="Generación Total Diaria por Tipo",
        template="plotly_white",
        labels={"valor": "Generación (kWh)", "fechahora": "Fecha"}
    )
    
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Mostrar métricas clave rápidas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Generado (Periodo)", f"{df_filtered['valor'].sum():,.0f} kWh")
    with col2:
        st.metric("Registros Procesados", f"{len(df_filtered):,}")

else:
    st.info("Esperando conexión con el Data Lake de AWS S3...")
