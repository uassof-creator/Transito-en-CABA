import os
import time
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

CABA_CENTER = [-34.6037, -58.3816]
CABA_BBOX = {"west": -58.5400, "south": -34.7100, "east": -58.3300, "north": -34.5300}

CORRIDORS = {
    "Av. 9 de Julio": [(-34.5900, -58.3812), (-34.6030, -58.3812), (-34.6170, -58.3805), (-34.6279, -58.3800)],
    "Av. Corrientes": [(-34.6038, -58.4130), (-34.6038, -58.3900), (-34.6038, -58.3700), (-34.6040, -58.3490)],
    "Av. Sta. Fe / Cabildo": [(-34.6080, -58.4470), (-34.5960, -58.4220), (-34.5910, -58.4060), (-34.5900, -58.3900)],
    "Av. Rivadavia": [(-34.6080, -58.4560), (-34.6120, -58.4300), (-34.6150, -58.4080), (-34.6175, -58.3730)],
    "Av. del Libertador": [(-34.5660, -58.4720), (-34.5850, -58.4320), (-34.5950, -58.3900), (-34.5960, -58.3610)],
    "Av. Córdoba": [(-34.5990, -58.4050), (-34.5985, -58.3850), (-34.5985, -58.3650), (-34.5985, -58.3500)],
    "Av. Belgrano": [(-34.6170, -58.4050), (-34.6140, -58.3880), (-34.6110, -58.3720)],
    "Av. Independencia": [(-34.6220, -58.4380), (-34.6210, -58.4150), (-34.6210, -58.3900), (-34.6205, -58.3680)],
    "Av. San Juan": [(-34.6280, -58.4400), (-34.6270, -58.4180), (-34.6270, -58.3960), (-34.6265, -58.3750)],
    "Av. Pueyrredón": [(-34.5890, -58.4100), (-34.6040, -58.4100), (-34.6190, -58.4100), (-34.6300, -58.4100)],
    "Av. Boedo - La Plata": [(-34.6190, -58.4620), (-34.6240, -58.4400), (-34.6310, -58.4100), (-34.6330, -58.3830)],
    "Av. General Paz": [(-34.5480, -58.5300), (-34.6200, -58.5350), (-34.6800, -58.5400), (-34.7055, -58.4700)],
    "Aut. 25 de Mayo (AU1)": [(-34.6340, -58.3720), (-34.6280, -58.3950), (-34.6220, -58.4150), (-34.6200, -58.4250)],
    "Aut. Perito Moreno (AU6)": [(-34.6500, -58.4500), (-34.6580, -58.4560), (-34.6660, -58.4600)],
    "Aut. Pres. Illia": [(-34.5760, -58.3900), (-34.5680, -58.4060), (-34.5580, -58.4250), (-34.5490, -58.4420)],
    "Av. Juan B. Justo": [(-34.6070, -58.4520), (-34.6220, -58.4590), (-34.6370, -58.4690)],
    "Av. Boedo": [(-34.6190, -58.4170), (-34.6220, -58.4220), (-34.6270, -58.4300)],
    "Av. Directorio": [(-34.6370, -58.4470), (-34.6360, -58.4250), (-34.6350, -58.4030)],
    "Av. Mayo": [(-34.6080, -58.3820), (-34.6075, -58.3740)],
}

FLOW_COLORS = {"fluido": "#38c0ff", "congestionado": "#ff8c00", "bloqueado": "#d32f2f"}
FLOW_LABELS = {"fluido": "Flujo tranquilo", "congestionado": "Congestionado", "bloqueado": "Trabado / bloqueado"}
ACCIDENT_CATEGORIES = {2}
ROADWORKS_CATEGORIES = {8, 9, 10}
CATEGORY_LABELS = {
    1: "Desconocido",
    2: "Accidente",
    3: "Niebla",
    4: "Condiciones peligrosas",
    5: "Lluvia",
    6: "Hielo",
    7: "Embudo / atasco",
    8: "Carril cerrado",
    9: "Carretera cerrada",
    10: "Obras en la vía",
    11: "Viento",
    12: "Inundación",
    13: "Desvío",
    14: "Conglomeración",
    15: "Vehículo averiado",
}


def leer_secretos(key: str) -> str:
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""


def obtener_clave() -> str:
    valor = os.environ.get("TOMTOM_KEY", "").strip()
    if valor:
        return valor
    valor = leer_secretos("TOMTOM_KEY") or leer_secretos("tomtom_key")
    if valor:
        return valor
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                for linea in f:
                    if "=" not in linea:
                        continue
                    k, v = linea.strip().split("=", 1)
                    if k.strip().strip('"').strip("'") == "tomtom_key":
                        return v.strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def muestrear_corredor(puntos, cantidad):
    if len(puntos) < 2:
        return list(puntos)
    largos = []
    total = 0.0
    for i in range(len(puntos) - 1):
        d = ((puntos[i + 1][0] - puntos[i][0]) ** 2 + (puntos[i + 1][1] - puntos[i][1]) ** 2) ** 0.5
        largos.append(d)
        total += d
    resultado = []
    for k in range(cantidad):
        objetivo = (total * k / (cantidad - 1)) if cantidad > 1 else total / 2
        acum = 0.0
        for i in range(len(puntos) - 1):
            if acum + largos[i] >= objetivo or i == len(puntos) - 2:
                t = ((objetivo - acum) / largos[i]) if largos[i] else 0.0
                t = max(0.0, min(1.0, t))
                resultado.append((
                    puntos[i][0] + (puntos[i + 1][0] - puntos[i][0]) * t,
                    puntos[i][1] + (puntos[i + 1][1] - puntos[i][1]) * t,
                ))
                break
            acum += largos[i]
    return resultado


def puntos_ciudad():
    pts = []
    for nombre, corredor in CORRIDORS.items():
        pts.extend(muestrear_corredor(corredor, 2))
    return pts


def consultar_flujo(lat: float, lng: float, key: str):
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json"
    params = {"point": f"{lat},{lng}", "unit": "kmph", "openLr": "false", "key": key}
    respuesta = requests.get(url, params=params, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()["flowSegmentData"]
    geometria = [(p["latitude"], p["longitude"]) for p in datos["coordinates"]["coordinate"]]
    return {
        "geometria": geometria,
        "velocidad_actual": datos.get("currentSpeed"),
        "velocidad_libre": datos.get("freeFlowSpeed"),
        "cierre": datos.get("roadClosure", False),
        "frc": datos.get("frc", ""),
    }


def nivel_congestion(segmento):
    if segmento.get("cierre"):
        return "bloqueado"
    libre = segmento.get("velocidad_libre") or 0
    actual = segmento.get("velocidad_actual") or 0
    ratio = (actual / libre) if libre else 1.0
    if ratio >= 0.75:
        return "fluido"
    if ratio >= 0.45:
        return "congestionado"
    return "bloqueado"


def consultar_incidentes(key: str):
    url = "https://api.tomtom.com/traffic/services/5/incidentDetails"
    bbox = f"{CABA_BBOX['west']},{CABA_BBOX['south']},{CABA_BBOX['east']},{CABA_BBOX['north']}"
    params = {
        "bbox": bbox,
        "projection": "EPSG4326",
        "language": "en-GB",
        "timeValidityFilter": "present",
        "key": key,
    }
    respuesta = requests.get(url, params=params, timeout=15)
    respuesta.raise_for_status()
    incidentes = respuesta.json().get("incidents", []) or []
    procesados = []
    for inc in incidentes:
        props = inc.get("properties", {})
        geo = inc.get("geometry", {})
        coords = geo.get("coordinates") if geo else None
        if not coords:
            continue
        categoria = props.get("iconCategory", 0)
        if categoria in ACCIDENT_CATEGORIES:
            tipo = "accidente"
        elif categoria in ROADWORKS_CATEGORIES:
            tipo = "obras"
        else:
            continue
        geometria = []
        tipo_geo = geo.get("type", "")
        if tipo_geo == "Point":
            lng, lat = coords[0], coords[1]
            geometria = [(lat, lng)]
        else:
            geometria = [(p[1], p[0]) for p in coords]
            lat, lng = geometria[len(geometria) // 2]
        procesados.append({
            "lat": lat,
            "lng": lng,
            "tipo": tipo,
            "categoria": categoria,
            "descripcion": CATEGORY_LABELS.get(categoria, f"Categoría {categoria}"),
            "demora_min": props.get("delay", 0),
            "geometria": geometria,
        })
    return procesados


@st.cache_data(ttl=30, show_spinner="Consultando tránsito en CABA...")
def obtener_datos(key: str):
    flujo = []
    errores = 0
    for lat, lng in puntos_ciudad():
        try:
            flujo.append(consultar_flujo(lat, lng, key))
        except Exception:
            errores += 1
            continue
    try:
        incidentes = consultar_incidentes(key)
    except Exception:
        incidentes = []
    return flujo, incidentes, errores


def construir_mapa(flujo, incidentes):
    mapa = folium.Map(
        location=CABA_CENTER,
        zoom_start=12,
        min_zoom=10,
        max_zoom=18,
        tiles="OpenStreetMap",
        control_scale=True,
        scroll_wheel_zoom=True,
    )
    folium.Element('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>').add_to(mapa.get_root().html)

    for seg in flujo:
        geo = seg.get("geometria") or []
        if len(geo) < 2:
            continue
        nivel = nivel_congestion(seg)
        espesor = 5 if seg.get("frc", "").startswith("FRC0") or seg.get("frc", "").startswith("FRC1") else 3
        popup = folium.Popup(f"<b>{FLOW_LABELS[nivel]}</b><br>Velocidad: {seg.get('velocidad_actual', '?')} km/h vs libre {seg.get('velocidad_libre', '?')} km/h", max_width=260)
        folium.PolyLine(geo, color=FLOW_COLORS[nivel], weight=espesor, opacity=0.85, popup=popup).add_to(mapa)

    for inc in incidentes:
        geo_inc = inc.get("geometria") or []
        if inc["tipo"] == "accidente":
            color, icono = "red", "exclamation-triangle"
        else:
            color, icono = "orange", "wrench"
        texto = (f"<b>{inc['descripcion']}</b><br>"
                 f"Categoría: {CATEGORY_LABELS.get(inc['categoria'], 'N/D')}<br>"
                 f"Demora estimada: {inc['demora_min']} min")
        if len(geo_inc) >= 2:
            folium.PolyLine(geo_inc, color=color, weight=6, opacity=0.8, dash_array="10 6",
                            popup=folium.Popup(texto, max_width=280)).add_to(mapa)
        folium.Marker(
            [inc["lat"], inc["lng"]],
            icon=folium.Icon(color=color, icon=icono, prefix="fa"),
            popup=folium.Popup(texto, max_width=280),
        ).add_to(mapa)

    leyenda = """
    <div style="position:fixed; bottom:30px; left:60px; z-index:9999; background:white;
                padding:8px 12px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,.3);
                font-family:sans-serif; font-size:12px; line-height:1.6">
      <b>Estado del tránsito</b><br>
      <span style="color:#38c0ff">—</span> Fluido (tranquilo)<br>
      <span style="color:#ff8c00">—</span> Congestionado<br>
      <span style="color:#d32f2f">—</span> Trabado / bloqueado<br>
      <span style="color:red">⚠</span> Accidente &nbsp; <span style="color:darkorange">🔧</span> Obras
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(leyenda))
    return mapa


def main():
    st.set_page_config(page_title="Tránsito en Vivo — CABA", page_icon="🚦", layout="wide")
    st_autorefresh(interval=30000, key="refresco_transito")

    key = obtener_clave()

    st.title("🚦 Estado del Tránsito en Vivo — Ciudad de Buenos Aires")
    st.caption("Datos de tráfico en tiempo real de la API pública gratuita de TomTom Traffic. "
               "Actualización automática cada 30 segundos. Zoom con la rueda del mouse o con los botones + / − del mapa.")

    if not key:
        st.error("No hay API key de TomTom configurada. "
                 "La app usa los datos en tiempo real de la API pública TomTom Traffic y **no genera datos de demostración**, "
                 "por lo que sin clave no puede mostrar el mapa.")
        st.markdown(
            "### Cómo activar los datos en tiempo real\n"
            "1. Registrate gratis en [developer.tomtom.com](https://developer.tomtom.com) y copiá tu **Primary Key**.\n"
            "2. Creá el archivo `.streamlit/secrets.toml` dentro de la carpeta `transito-ba` con el contenido:\n"
            "```toml\n"
            "tomtom_key = \"TU_CLAVE_PRIMARY\"\n"
            "```\n"
            "3. Reiniciá la app con `streamlit run app.py`."
        )
        st.stop()

    with st.sidebar:
        st.header("Configuración")
        st.success("API key de TomTom configurada. Mostrando datos de tránsito en tiempo real.")
        if st.button("🔄 Forzar actualización ahora"):
            obtener_datos.clear()
            st.rerun()
        st.divider()
        st.subheader("Leyenda")
        st.markdown(
            "- <span style='color:#38c0ff'>━━</span> Fluido (tranquilo)\n"
            "- <span style='color:#ff8c00'>━━</span> Congestionado\n"
            "- <span style='color:#d32f2f'>━━</span> Trabado / bloqueado\n"
            "- <span style='color:red'>⚠</span> Accidente\n"
            "- <span style='color:darkorange'>🔧</span> Obras / trabajadores",
            unsafe_allow_html=True,
        )

    flujo, incidentes, errores = obtener_datos(key)
    mapa = construir_mapa(flujo, incidentes)

    st_folium(mapa, width="100%", height=620)

    ultima = time.strftime("%H:%M:%S")
    st.caption(f"Última actualización: {ultima} — {len(flujo)} tramos viales monitoreados · "
               f"{len(incidentes)} incidentes activos"
               + (f" · ⚠️ {errores} tramos sin datos en esta consulta" if errores else ""))


if __name__ == "__main__":
    main()