import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Análisis Generación 10%", layout="wide")

@st.cache_data
def load_data_s3_sample():
    # Ruta al archivo Parquet en S3
    path = "s3://eafit-proyecto-integrador-simem/gold/Generacion.parquet"
    
    try:
        # 1. Cargamos solo las columnas necesarias para ahorrar RAM
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
        
        # 2. Tomamos el 10% aleatorio inmediatamente
        df_sample = df.sample(frac=0.10, random_state=42)
        
        # 3. Formateo de tipos para asegurar gráficas bonitas
        df_sample["fechahora"] = pd.to_datetime(df_sample["fechahora"])
        df_sample["valor"] = pd.to_numeric(df_sample["valor"], downcast="float")
        
        return df_sample
        
    except Exception as e:
        st.error(f"Error crítico de conexión o permisos: {e}")
        return None

# --- CUERPO DE LA APP ---
st.title("⚡ Dashboard de Generación (Muestra Aleatoria 10%)")

df = load_data_s3_sample()

if df is not None:
    st.success(f"Datos cargados exitosamente. Analizando {len(df):,} registros.")

    # Sidebar para filtros
    st.sidebar.header("Filtros de Exploración")
    tipos = df["tipogeneracion"].unique()
    seleccion = st.sidebar.multiselect("Tipos de Energía", tipos, default=tipos)
    
    # Filtrado
    df_filtered = df[df["tipogeneracion"].isin(seleccion)]

    # --- VISUALIZACIONES EDA ---
    
    # 1. Evolución Temporal (Área Apilada) - MEJOR QUE TORTA
    st.subheader("Evolución de la Matriz Energética")
    # Agregamos por día para suavizar líneas
    df_daily = df_filtered.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()
    
    fig_area = px.area(
        df_daily, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        title="Generación Diaria Total por Tecnología",
        color_discrete_sequence=px.colors.qualitative.Bold,
        template="plotly_dark"
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # 2. Comparativa de Tendencias (Facetas)
    st.subheader("Desempeño Individual por Fuente")
    fig_facet = px.line(
        df_daily, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        facet_col="tipogeneracion", 
        facet_col_wrap=2,
        title="Comparativa de Curvas de Generación"
    )
    fig_facet.update_yaxes(matches=None) # Escalas independientes para ver mejor las pequeñas
    st.plotly_chart(fig_facet, use_container_width=True)

    # 3. Resumen de Unidades
    st.subheader("Top 10 Unidades con Mayor Aporte")
    top_units = df_filtered.groupby("nombreunidad")["valor"].sum().nlargest(10).reset_index()
    fig_bar = px.bar(top_units, x="valor", y="nombreunidad", orientation='h', color="valor")
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.warning("⚠️ No se pudieron obtener datos. Verifica las nuevas Access Keys en los Secrets de Streamlit.")
