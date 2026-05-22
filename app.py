import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="EDA Generación - S3", layout="wide")

@st.cache_data
def load_data_from_s3():
    # Ruta oficial en S3
    path = "s3://eafit-proyecto-integrador-simem/gold/Generacion.parquet"
    
    try:
        # Cargamos columnas clave para no saturar la RAM
        df = pd.read_parquet(
            path,
            columns=["fechahora", "tipogeneracion", "valor", "nombreunidad"],
            storage_options={
                "key": st.secrets["aws"]["access_key"],
                "secret": st.secrets["aws"]["secret_key"],
                "client_kwargs": {"region_name": st.secrets["aws"]["region"]}
            }
        )
        
        # Muestreo aleatorio del 10%
        df_sample = df.sample(frac=0.10, random_state=42)
        
        # Formateo de tipos
        df_sample["fechahora"] = pd.to_datetime(df_sample["fechahora"])
        df_sample["valor"] = pd.to_numeric(df_sample["valor"], downcast="float")
        
        return df_sample
    
    except Exception as e:
        st.error(f"Error de conexión a S3: {e}")
        return None

# --- LÓGICA PRINCIPAL ---
st.title("🚀 Análisis de Generación (AWS S3)")
df = load_data_from_s3()

if df is not None:
    st.success("Conexión exitosa con Amazon S3")
    
    # 1. Filtros
    tecnologias = st.sidebar.multiselect(
        "Seleccionar Tecnologías", 
        options=df["tipogeneracion"].unique(),
        default=df["tipogeneracion"].unique()
    )
    df_filtered = df[df["tipogeneracion"].isin(tecnologias)]

    # 2. Análisis Evolución Temporal (Área Apilada)
    st.subheader("Evolución de la Matriz Energética")
    df_daily = df_filtered.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()
    
    fig_area = px.area(
        df_daily, x="fechahora", y="valor", color="tipogeneracion",
        title="Generación Diaria por Tecnología (Muestra 10%)",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # 3. Comparativa Individual (Facetas)
    st.subheader("Tendencias Individuales")
    fig_sep = px.line(
        df_daily, x="fechahora", y="valor", color="tipogeneracion",
        facet_col="tipogeneracion", facet_col_wrap=2
    )
    fig_sep.update_yaxes(matches=None)
    st.plotly_chart(fig_sep, use_container_width=True)

else:
    # Este es el 'else' que te daba error, ahora está correctamente alineado con el 'if df is not None'
    st.info("A la espera de datos... Revisa que los Secrets en Streamlit Cloud tengan las nuevas Access Keys.")
