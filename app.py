import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Análisis Generación - GitHub Data", layout="wide")

@st.cache_data
def load_data_from_github():
    # REEMPLAZA ESTA URL con la que copiaste en el paso 1 (el botón 'Raw' de GitHub)
    url = "https://raw.githubusercontent.com/davidalejo04/Streamlit_Gen/refs/heads/main/untitled%20(2).csv"
    
    try:
        # Cargamos el CSV completo
        df = pd.read_csv(url)
        
        # Selección aleatoria del 10% para optimizar rendimiento
        df_sample = df.sample(frac=0.10, random_state=42)
        
        # Limpieza y conversión de tipos basada en tu archivo
        if 'fechahora' in df_sample.columns:
            df_sample["fechahora"] = pd.to_datetime(df_sample["fechahora"])
        
        if 'valor' in df_sample.columns:
            df_sample["valor"] = pd.to_numeric(df_sample["valor"], errors='coerce').fillna(0)
            
        return df_sample
    except Exception as e:
        st.error(f"Error al cargar el CSV desde GitHub: {e}")
        return None

# Ejecución
st.title("⚡ Dashboard de Generación (Fuente: GitHub CSV)")
df = load_data_from_github()

if df is not None:
    st.info(f"Visualizando una muestra aleatoria del 10% ({len(df):,} registros) para optimizar el rendimiento.")

    # --- MÉTRICAS ---
    m1, m2, m3 = st.columns(3)
    with m1:
        total_gen = df['valor'].sum()
        st.metric("Generación Total (Muestra)", f"{total_gen:,.2f} kWh")
    with m2:
        plantas = df['codigoplanta'].nunique() if 'codigoplanta' in df.columns else "N/A"
        st.metric("Plantas en Muestra", plantas)
    with m3:
        tipos = df['tipogeneracion'].nunique() if 'tipogeneracion' in df.columns else "N/A"
        st.metric("Tipos de Energía", tipos)

    # --- GRÁFICA DE SERIE TEMPORAL ---
    st.subheader("Evolución Temporal de la Generación")
    if 'fechahora' in df.columns and 'valor' in df.columns:
        # Agrupamos por día para que la gráfica no sea pesada
        df_diario = df.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()
        
        fig = px.line(df_diario, x="fechahora", y="valor", color="tipogeneracion",
                      title="Generación Diaria por Tecnología",
                      labels={"valor": "Generación (kWh)", "fechahora": "Fecha"})
        st.plotly_chart(fig, use_container_width=True)

    # --- DISTRIBUCIÓN ---
    st.subheader("Distribución por Fuente")
    fig_pie = px.sunburst(df, path=['tipogeneracion', 'nombreunidad'], values='valor',
                          title="Jerarquía de Generación (Muestra)")
    st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.warning("No se pudo cargar la base de datos. Verifica la URL de GitHub Raw.")
