import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="EDA Generación Energética", layout="wide")

@st.cache_data
def load_data():
    # URL RAW proporcionada
    url = "https://raw.githubusercontent.com/davidalejo04/Streamlit_Gen/refs/heads/main/untitled%20(2).csv"
    
    try:
        # Cargamos los datos
        df = pd.read_csv(url)
        
        # Convertimos fechas y optimizamos tipos
        df["fechahora"] = pd.to_datetime(df["fechahora"])
        df["valor"] = pd.to_numeric(df["valor"], errors='coerce').fillna(0)
        
        # Tomamos una muestra aleatoria del 10% para agilidad
        df_sample = df.sample(frac=0.10, random_state=42)
        return df_sample
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return None

df = load_data()

if df is not None:
    st.title("🚀 Análisis Exploratorio de Generación")
    st.markdown("Evolución temporal discriminada por tecnología (Muestra aleatoria del 10%)")

    # --- FILTROS ---
    st.sidebar.header("Opciones de Visualización")
    lista_tecnologias = df["tipogeneracion"].unique().tolist()
    seleccion = st.sidebar.multiselect("Filtrar Tecnologías", lista_tecnologias, default=lista_tecnologias)
    
    df_filtered = df[df["tipogeneracion"].isin(seleccion)]

    # --- AGREGACIÓN TEMPORAL ---
    # Agrupamos por día para una visualización más limpia y "bonita"
    df_daily = df_filtered.groupby([pd.Grouper(key="fechahora", freq="D"), "tipogeneracion"])["valor"].sum().reset_index()

    # --- GRAFICA 1: ÁREA APILADA (COMPOSICIÓN DE LA MATRIZ) ---
    st.subheader("1. Composición de la Matriz Energética en el Tiempo")
    st.info("Este gráfico permite ver el aporte de cada energía al total diario acumulado.")
    
    fig_area = px.area(
        df_daily, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        line_group="tipogeneracion",
        title="Generación Total Diaria por Tipo de Energía (Apilada)",
        color_discrete_sequence=px.colors.qualitative.Safe,
        labels={"valor": "Generación (kWh)", "fechahora": "Fecha"}
    )
    fig_area.update_layout(hovermode="x unified", legend_title="Tecnología")
    st.plotly_chart(fig_area, use_container_width=True)

    # --- GRAFICA 2: FACETAS (EVOLUCIÓN INDIVIDUAL) ---
    st.subheader("2. Evolución Individual por Tipo de Energía")
    st.info("Aquí puedes comparar las tendencias y escalas de cada tecnología por separado.")
    
    fig_facets = px.line(
        df_daily, 
        x="fechahora", 
        y="valor", 
        color="tipogeneracion",
        facet_col="tipogeneracion", 
        facet_col_wrap=2, # Máximo 2 columnas para que se vean grandes
        title="Tendencias Individuales de Generación",
        labels={"valor": "kWh"}
    )
    # Ajustes estéticos para que no se vea amontonado
    fig_facets.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig_facets.update_yaxes(matches=None) # Permite que cada escala sea independiente si hay mucha diferencia
    st.plotly_chart(fig_facets, use_container_width=True)

    # --- GRAFICA 3: MAPA DE CALOR (INTENSIDAD POR HORA/DÍA) ---
    st.subheader("3. Intensidad de Generación (Heatmap)")
    # Extraemos hora para ver patrones intradiarios
    df_filtered['hora'] = df_filtered['fechahora'].dt.hour
    df_heatmap = df_filtered.groupby(['hora', 'tipogeneracion'])['valor'].mean().reset_index()
    
    fig_heat = px.density_heatmap(
        df_heatmap, 
        x="hora", 
        y="tipogeneracion", 
        z="valor",
        color_continuous_scale="Viridis",
        title="Promedio de Generación por Hora del Día",
        labels={"hora": "Hora del Día", "valor": "Promedio kWh"}
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # --- TABLA RESUMEN ---
    with st.expander("Ver Resumen Estadístico"):
        st.write(df_filtered.groupby("tipogeneracion")["valor"].describe())

else:
    st.warning("No se pudo cargar la información desde GitHub. Verifica la URL.")
