import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Monitor de Generación", layout="wide")

# Función para cargar datos con caché (evita recargas lentas)
@st.cache_data
def load_data():
    # Acceder a credenciales desde los secretos de Streamlit
    aws_creds = st.secrets["aws"]
    
    # Ruta del archivo Parquet en S3
    # Si Spark generó varios archivos, apunta a la carpeta o al archivo .parquet específico
    s3_uri = "eafit-proyecto-integrador-simem.s3.us-east-1.amazonaws.com/gold/Generacion.parquet"
    
    df = pd.read_parquet(
        s3_uri,
        storage_options={
            "key": aws_creds["access_key"],
            "secret": aws_creds["secret_key"],
            "client_kwargs": {"region_name": aws_creds["region"]}
        }
    )
    return df

# Ejecución
try:
    df = load_data()
    st.success("Conexión con S3 exitosa")
    # Aquí irían tus gráficas de serie temporal
    st.line_chart(df.set_index('fechahora')['valor']) 
except Exception as e:
    st.error(f"Error de conexión: {e}")
