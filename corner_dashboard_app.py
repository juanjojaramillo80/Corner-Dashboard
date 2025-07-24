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

# Principales ligas por país
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

def get_teams_in_league(league_id):
    url = f"{BASE_URL}/teams"
    params = {"league": league_id, "season": 2024}  # temporada actual
    res = requests.get(url, headers=HEADERS, params=params)
    return res.json().get("response", [])

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
    cuotas = []

    for i, fixture in enumerate(fixtures):
        fid = fixture["fixture"]["id"]
        stats_url = f"{BASE_URL}/fixtures/statistics"
        stats_params = {"fixture": fid}
        stats_resp = requests.get(stats_url, headers=HEADERS, params=stats_params)
        stats_data = stats_resp.json().get("response", [])

        odds_url = f"{BASE_URL}/odds"
        odds_params = {"fixture": fid, "bet": "Over/Under"}
        odds_resp = requests.get(odds_url, headers=HEADERS, params=odds_params)
        odds_data = odds_resp.json().get("response", [])

        cuota_over_75 = None
        for bookie in odds_data:
            for bet in bookie.get("bookmakers", []):
                for bet_type in bet.get("bets", []):
                    if bet_type.get("name") in ["Corners", "Over/Under"]:
                        for value in bet_type.get("values", []):
                            if value.get("value") == "Over 7.5":
                                cuota_over_75 = value.get("odd")
                                break

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
        if match_corners > 7.5:
            over_count += 1
        fecha = fixture["fixture"]["date"][:10]

        if match_corners > 7.5:
            color = "🟢"
        elif match_corners >= 6:
            color = "🟡"
        else:
            color = "🔴"

        historial.append({
            "Fecha": fecha,
            "Rival": fixture["teams"]["home"]["name"] if fixture["teams"]["away"]["id"] == team_id else fixture["teams"]["away"]["name"],
            "Córners totales": match_corners,
            "Over 7.5": f"{color} {match_corners}",
            "Cuota Over 7.5": cuota_over_75
        })
        fechas.append(fecha)
        corners_tendencia.append((fecha, match_corners, color))
        cuotas.append(cuota_over_75)

    promedio = round(total_corners / match_count, 2) if match_count else 0
    promedio_ponderado = round(weighted_sum / (sum(range(1, 11))), 2) if match_count else 0
    porcentaje_over = round((over_count / match_count) * 100, 1) if match_count else 0
    return promedio, promedio_ponderado, porcentaje_over, historial, fechas, corners_tendencia

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
    st.dataframe(df_historial.style.applymap(color_over, subset=["Over 7.5"]))

    st.subheader("Tendencia de Córners por Partido")
    fig, ax = plt.subplots()
    fechas, valores, colores = zip(*corners_tendencia[::-1])
    color_map = {"🟢": '#28a745', "🟡": '#ffc107', "🔴": '#dc3545'}
    barras = ax.bar(fechas, valores, color=[color_map[c] for c in colores[::-1]])
    ax.axhline(y=7.5, color='gray', linestyle='--', linewidth=1, label='Línea Over 7.5')
    ax.set_ylabel("Córners totales")
    ax.set_xlabel("Fecha")
    ax.set_title("Historial de Córners con Codificación de Color")
    ax.legend()
    plt.xticks(rotation=45)

    for bar, valor in zip(barras, valores[::-1]):
        altura = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, altura + 0.3, str(valor), ha='center', va='bottom')

    st.pyplot(fig)
    st.subheader("Tabla Detallada con Cuotas")
    st.dataframe(df_historial)

# --- UI APP ---

st.title("Dashboard de Over 7.5 Córners")

col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("Selecciona un país", list(LEAGUES.keys()))
with col2:
    umbral = st.slider("% mínimo de partidos Over 7.5", 0, 100, 85)

ligas = LEAGUES[pais]
equipos_data = []

with st.spinner("Cargando equipos y estadísticas..."):
    for lid in ligas:
        equipos = get_teams_in_league(lid)
        for equipo in equipos:
            team_id = equipo["team"]["id"]
            team_name = equipo["team"]["name"]
            try:
                prom, prom_p, porc, historial, fechas, tendencia = get_corner_stats(team_id)
                if porc >= umbral:
                    equipos_data.append({
                        "ID": team_id,
                        "Equipo": team_name,
                        "% Over 7.5": porc,
                        "Promedio": prom,
                        "Prom. Ponderado": prom_p,
                        "Historial": historial,
                        "Tendencia": tendencia
                    })
            except:
                continue

if not equipos_data:
    st.warning("No se encontraron equipos con el porcentaje mínimo de Over 7.5 requerido.")
else:
    df_resumen = pd.DataFrame(equipos_data)[["Equipo", "% Over 7.5", "Promedio", "Prom. Ponderado"]].sort_values(by="% Over 7.5", ascending=False)
    st.subheader("Equipos que cumplen con el criterio")
    selected_team = st.selectbox("Selecciona un equipo para ver detalle", df_resumen["Equipo"])
    st.dataframe(df_resumen)

    equipo_detalle = next(e for e in equipos_data if e["Equipo"] == selected_team)
    mostrar_historial(equipo_detalle["Historial"], equipo_detalle["Tendencia"])


    mostrar_historial(historial_sel, tendencia_sel)
else:
    st.warning("⚠️ No hay equipos que cumplan el umbral mínimo de Over 8.5 en esta liga.")

