import boto3
import streamlit as st

def test_s3_connection():
    s3 = boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["access_key"],
        aws_secret_access_key=st.secrets["aws"]["secret_key"],
        region_name=st.secrets["aws"]["region"]
    )
    try:
        # Intentamos solo ver si el archivo existe sin leerlo
        s3.head_object(Bucket='eafit-proyecto-integrador-simem', Key='gold/Generacion.parquet')
        return "¡Conexión y Permisos OK!"
    except Exception as e:
        return f"Error detectado: {e}"

st.write(test_s3_connection())
