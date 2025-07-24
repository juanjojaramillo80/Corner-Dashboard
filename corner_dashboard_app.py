import streamlit as st
import pandas as pd
import requests
import io
import matplotlib.pyplot as plt
import seaborn as sns

# API config
API_KEY = "27a352c146f8b04e852628573858b3f8"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Principales ligas por país (primera y segunda división donde aplique)
LEAGUES = {
    "Inglaterra": [39, 40],
    "España": [140, 141],
    "Italia": [135, 136],
    "Alemania": [78, 79],
    "Francia": [61, 62],
    "Países Bajos": [88],
    "Portugal": [94],
    "Brasil": [71, 72],
    "Argentina": [128],
    "Colombia": [76],
    "Estados Unidos": [253],
    "México": [262],
    "Bélgica": [144],
    "Japón": [98],
    "Corea del Sur": [292]
}

# Obtener historial de córners y % de over 8.5

def get_corner_stats(team_id):
    url = f"{BASE_URL}/fixtures"
    params = {"team": team_id, "last": 10}
    response = requests.get(url, headers=HEADERS, params=params)
    fixtures = response.json().get("response", [])

    total_corners = 0
    weighted_sum = 0
    over_count = 0
    match_count = 0
    historial = []
    fechas = []
    corners_tendencia = []

    for i, fixture in enumerate(fixtures):
        fid = fixture["fixture"]["id"]
        stats_url = f"{BASE_URL}/fixtures/statistics"
        stats_params = {"fixture": fid}
        stats_resp = requests.get(stats_url, headers=HEADERS, params=stats_params)
        stats_data = stats_resp.json().get("response", [])

        match_corners = 0
        corners_validos = True

        for team_stats in stats_data:
            for s in team_stats.get("statistics", []):
                if s.get("type") == "Corner Kicks":
                    if s.get("value") is None:
                        corners_validos = False
                    else:
                        match_corners += s["value"]

        if not corners_validos:
            continue

        total_corners += match_corners
        weight = (10 - i)
        weighted_sum += match_corners * weight
        match_count += 1
        if match_corners > 8.5:
            over_count += 1
        fecha = fixture["fixture"]["date"][:10]

        if match_corners > 8.5:
            color = "🟢"
        elif match_corners >= 7:
            color = "🟡"
        else:
            color = "🔴"

        historial.append({
            "Fecha": fecha,
            "Rival": fixture["teams"]["home"]["name"] if fixture["teams"]["away"]["id"] == team_id else fixture["teams"]["away"]["name"],
            "Córners totales": match_corners,
            "Over 8.5": f"{color} {match_corners}"
        })
        fechas.append(fecha)
        corners_tendencia.append((fecha, match_corners, color))

    promedio = round(total_corners / match_count, 2) if match_count else 0
    promedio_ponderado = round(weighted_sum / (sum(range(1, 11))), 2) if match_count else 0
    porcentaje_over = round((over_count / match_count) * 100, 1) if match_count else 0
    return promedio, promedio_ponderado, porcentaje_over, historial, fechas, corners_tendencia

# Mostrar resumen por liga

def resumen_por_liga(liga_id):
    equipos_url = f"{BASE_URL}/teams"
    params = {"league": liga_id, "season": 2024}
    resp = requests.get(equipos_url, headers=HEADERS, params=params)
    equipos = resp.json().get("response", [])

    resumen = []
    for eq in equipos:
        try:
            equipo_id = eq["team"]["id"]
            nombre = eq["team"]["name"]
            promedio, ponderado, over_pct, *_ = get_corner_stats(equipo_id)
            resumen.append({
                "Equipo": nombre,
                "Prom. córners": promedio,
                "Prom. ponderado": ponderado,
                "% Over 8.5": over_pct
            })
        except:
            continue

    df = pd.DataFrame(resumen).sort_values("% Over 8.5", ascending=False)
    return df

# Visualización de historial con codificación de color

def mostrar_historial(historial, corners_tendencia):
    df_historial = pd.DataFrame(historial)
    st.subheader("Historial de Córners (últimos 10 partidos)")
    def color_over(val):
        if "🟢" in val:
            return 'background-color: #d4edda'
        elif "🟡" in val:
            return 'background-color: #fff3cd'
        elif "🔴" in val:
            return 'background-color: #f8d7da'
        return ''
    st.dataframe(df_historial.style.applymap(color_over, subset=["Over 8.5"]))

    st.subheader("Tendencia de Córners por Partido")
    fig, ax = plt.subplots()
    fechas, valores, colores = zip(*corners_tendencia[::-1])
    color_map = {"🟢": '#28a745', "🟡": '#ffc107', "🔴": '#dc3545'}
    barras = ax.bar(fechas, valores, color=[color_map[c] for c in colores[::-1]])
    ax.axhline(y=8.5, color='gray', linestyle='--', linewidth=1, label='Línea Over 8.5')
    ax.set_ylabel("Córners totales")
    ax.set_xlabel("Fecha")
    ax.set_title("Historial de Córners con Codificación de Color")
    ax.legend()
    plt.xticks(rotation=45)

    for bar, valor in zip(barras, valores[::-1]):
        altura = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, altura + 0.3, str(valor), ha='center', va='bottom')

    st.pyplot(fig)

# Interfaz principal
st.title("Análisis de Córners por Equipo")

st.subheader("Seleccionar liga por país")
paises = list(LEAGUES.keys())
pais_seleccionado = st.selectbox("País", paises)
ligas_ids = LEAGUES[pais_seleccionado]
ligas_seleccionadas = st.multiselect("Ligas disponibles", ligas_ids, default=ligas_ids)

st.subheader("Buscar equipo por nombre")
equipo_nombre = st.text_input("Nombre del equipo")
porcentaje_minimo = st.slider("% mínimo de partidos Over 8.5 para mostrar resultados", min_value=0, max_value=100, value=0, step=5)
equipo_id = None

if equipo_nombre:
    search_url = f"{BASE_URL}/teams"
    search_params = {"search": equipo_nombre}
    search_resp = requests.get(search_url, headers=HEADERS, params=search_params)
    equipos = search_resp.json().get("response", [])
    if equipos:
        nombres = [f"{eq['team']['name']} ({eq['team']['id']})" for eq in equipos]
        seleccion = st.selectbox("Seleccione el equipo", nombres)
        if seleccion:
            equipo_id = int(seleccion.split('(')[-1].strip(')'))

if equipo_id:
    try:
        promedio, promedio_ponderado, porcentaje_over, historial, fechas, corners_tendencia = get_corner_stats(equipo_id)
        if porcentaje_over >= porcentaje_minimo:
            st.metric("Promedio de córners", promedio)
            st.metric("Promedio ponderado de córners", promedio_ponderado)
            st.metric("% Over 8.5", f"{porcentaje_over}%")
            mostrar_historial(historial, corners_tendencia)
        else:
            st.warning(f"Este equipo tiene solo un {porcentaje_over}% de partidos Over 8.5, por debajo del umbral mínimo seleccionado ({porcentaje_minimo}%).")
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")

# Resumen por liga
st.subheader("Resumen por liga seleccionada")
ligas_para_resumen = st.multiselect("Seleccione ligas para resumen", ligas_ids, default=ligas_ids)
if st.button("Generar resumen"):
    resumen_completo = pd.DataFrame()
    for lid in ligas_para_resumen:
        df_liga = resumen_por_liga(lid)
        resumen_completo = pd.concat([resumen_completo, df_liga])
    if not resumen_completo.empty:
        st.dataframe(resumen_completo.sort_values("% Over 8.5", ascending=False))
    else:
        st.info("No se encontraron datos para las ligas seleccionadas.")
