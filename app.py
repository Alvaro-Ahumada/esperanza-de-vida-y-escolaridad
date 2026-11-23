from pathlib import Path
import hashlib
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile, BadZipFile
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Esperanza de vida | Life Expectancy (WHO)", layout="wide")

@st.cache_data
def cargar():
    ruta = Path(__file__).with_name("Life Expectancy Data.csv")
    if ruta.exists():
        contenido = ruta.read_bytes()
    else:
        url = "https://www.kaggle.com/api/v1/datasets/download/kumarajarshi/life-expectancy-who?datasetVersionNumber=1"
        with urlopen(url, timeout=30) as respuesta:
            with ZipFile(BytesIO(respuesta.read())) as archivo:
                contenido = archivo.read(ruta.name)
    if hashlib.sha256(contenido).hexdigest() != "872125dd1dd0f9140fbead61df20585a815f5cf47db68f08bf54efaf87963b11":
        raise ValueError("El CSV difiere del utilizado en el análisis original.")
    datos = pd.read_csv(BytesIO(contenido))
    datos.columns = datos.columns.str.strip()
    return datos

def mostrar(fig):
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

def numero(valor):
    return f"{valor:.2f}".replace(".", ",") if pd.notna(valor) else "Sin estimación"

@st.cache_data
def serie_anual(datos):
    panel = datos.pivot(index="Country", columns="Year", values="Life expectancy").dropna()
    return panel.mean()

try:
    df = cargar()
except (OSError, ValueError, KeyError, BadZipFile):
    st.error("No se pudo cargar la base original. Actualiza la página para volver a intentarlo.")
    st.stop()
categorias = {"Developed": "Desarrollados", "Developing": "En desarrollo"}
st.title("Esperanza de vida y escolaridad")
st.caption("Life Expectancy (WHO) · 193 países · 2000 a 2015")
st.sidebar.header("Selección de datos")
categoria = st.sidebar.selectbox("Categoría de desarrollo", ["Todas", *categorias], format_func=lambda x: categorias.get(x,x))
periodo = st.sidebar.slider("Intervalo de años", 2000, 2015, (2000,2015))
pais = st.sidebar.selectbox("País", ["Todos", *sorted(df.Country.unique())])
vista = df.loc[df.Year.between(*periodo)]
if categoria != "Todas":
    vista = vista.loc[vista.Status.eq(categoria)]
if pais != "Todos":
    vista = vista.loc[vista.Country.eq(pais)]
vida = vista["Life expectancy"]
st.header("Exploración de datos")
a,b,c = st.columns(3)
a.metric("Registros país-año",len(vista))
b.metric("Esperanza de vida media (años)",numero(vida.mean()))
c.metric("Desviación estándar (años)",numero(vida.std()))
st.caption(f"Hay {vida.count()} registros con esperanza de vida disponible. La desviación estándar resume cuánto se dispersan las esperanzas de vida alrededor de la media, en años. Su cálculo requiere dos valores como mínimo.")
with st.expander("Consultar tabla de la selección"):
    st.dataframe(vista,hide_index=True)
st.header("Visualizaciones de la selección")
if vista.empty:
    st.info("Esta combinación no tiene registros. Amplía el período o cambia el país.")
else:
    counts=vista.Status.map(categorias).value_counts()
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].bar(counts.index,counts,color="#236887")
    axes[0].set(title="Registros por categoría",ylabel="Número de registros país-año")
    axes[1].pie(counts,labels=counts.index,autopct="%1.1f%%",colors=[{"Desarrollados": "#e0ba76", "En desarrollo": "#53859e"}[grupo] for grupo in counts.index])
    axes[1].set_title("Proporción de la selección")
    mostrar(fig)
    fig,ax=plt.subplots(figsize=(8,3.8))
    ax.scatter(vista["infant deaths"],vista["under-five deaths"],alpha=.45,color="#236887")
    ax.set(title="Mortalidad infantil y de menores de cinco años",xlabel="Muertes infantiles (escala del archivo)",ylabel="Muertes antes de los cinco años (escala del archivo)")
    mostrar(fig)
st.header("Validación estadística")
st.write("Corte original de 2015, independiente de los filtros. La esperanza de vida media fue de 80,71 años en los 32 países clasificados como desarrollados y de 69,69 en los 151 países en desarrollo. La diferencia observada fue de 11,02 años.")
with st.expander("Consultar prueba e interpretación"):
    st.write("Prueba bilateral de Welch, una observación por país. H₀: igualdad de medias. H₁: medias distintas. t = 12,753224 y p = 7,09333 × 10⁻²³. Con un umbral de 0,05, se rechaza la igualdad de medias bajo los supuestos de la prueba. La selección de países y sus posibles vínculos geográficos limitan la generalización.")
st.header("Hallazgos del análisis original")
st.caption("Las dos figuras siguientes utilizan la base original independientemente de la selección lateral.")
st.subheader("¿Qué analicé?")
st.write("El archivo reúne indicadores de salud, educación y economía de 193 países entre 2000 y 2015. Cada fila representa un país en un año. Una media calculada sobre esas filas da el mismo peso a cada registro con información disponible. Por eso resulta importante indicar cuántos países y años intervienen en cada comparación.")
st.subheader("¿Qué encontré?")
st.write("Entre los 183 países con una serie completa, la esperanza de vida media pasó de 66,75 a 71,62 años. El aumento de 4,87 años resume la evolución del conjunto. Cada país tuvo el mismo peso durante todo el período.")
serie = serie_anual(df)
fig,ax=plt.subplots(figsize=(8,3.5))
ax.plot(serie.index,serie,marker="o",color="#236887")
ax.set(title="Esperanza de vida media de los mismos 183 países",xlabel="Año",ylabel="Esperanza de vida (años)")
mostrar(fig)
st.write("En los 2.768 registros país-año con ambos datos, una mayor escolaridad suele ir acompañada de una mayor esperanza de vida. Para comparar dos países, conviene seleccionar el mismo año y revisar si ambos tienen información disponible. El gráfico de 2015 permite ver cuánto difieren países con niveles educativos parecidos.")
fig,ax=plt.subplots(figsize=(8,3.5))
for cat,grupo in df.loc[df.Year.eq(2015)].groupby("Status"):
    ax.scatter(grupo.Schooling,grupo["Life expectancy"],label=categorias[cat],alpha=.7,marker="o" if cat=="Developing" else "x")
ax.set(title="Escolaridad y esperanza de vida de los países en 2015",xlabel="Escolaridad (años)",ylabel="Esperanza de vida (años)")
ax.legend()
mostrar(fig)
st.subheader("¿Qué significa?")
st.write("Las diferencias entre países orientan preguntas sobre las condiciones en las que vive su población. Los promedios nacionales pueden ocultar diferencias dentro de un país. La comparación tampoco permite calcular cuántos años de vida ganaría una persona si estudiara un año más.")
st.subheader("¿Qué se recomendaría?")
st.write("Antes de seleccionar países para una comparación más detallada, conviene fijar un mismo año, revisar cuántos valores están disponibles y observar la dispersión dentro de cada grupo. Para valorar una intervención concreta harían falta datos adicionales sobre la población, su contexto y los cambios ocurridos durante el período.")
