import os
import json
import time
import random
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

CABA_CENTER = [-34.6037, -58.3816]
CABA_BBOX = {"west": -58.5400, "south": -34.7100, "east": -58.3300, "north": -34.5300}
CONTROLS_FILE = os.path.join(os.path.dirname(__file__), "controles.json")

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


def leer_secretos(key: str) -> str:
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""


def cargar_controles():
    if not os.path.exists(CONTROLS_FILE):
        return []
    with open(CONTROLS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def guardar_controles(controles):
    with open(CONTROLS_FILE, "w", encoding="utf-8") as f:
        json.dump(controles, f, ensure_ascii=False, indent=2)


def en_caba(lat: float, lng: float) -> bool:
    return (
        CABA_BBOX["south"] <= lat <= CABA_BBOX["north"]
        and CABA_BBOX["west"] <= lng <= CABA_BBOX["east"]
    )


def muestrear_corredor(puntos, cantidad):
    resultado = []
    for i in range(len(puntos) - 1):
        a, b = puntos[i], puntos[i + 1]
        tramo = cantidad - 1 if i == len(puntos) - 2 else max(1, cantidad // (len(puntos) - 1))
        for j in range(tramo):
            t = j / tramo
            resultado.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    if puntos:
        resultado.append(puntos[-1])
    return resultado


def puntos_ciudad():
    pts = []
    for nombre, corredor in CORRIDORS.items():
        pts.extend(muestrear_corredor(corredor, 4))
    return pts


def consultar_flujo(lat: float, lng: float, key: str):
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative/0"
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
        "language": "es",
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
        eventos = props.get("events") or []
        descripcion = eventos[0].get("description", "") if eventos else ""
        procesados.append({
            "lat": coords[1],
            "lng": coords[0],
            "tipo": tipo,
            "categoria": categoria,
            "descripcion": descripcion or "Sin descripción",
            "demora_min": props.get("delay", 0),
            "desde": props.get("from", ""),
            "hasta": props.get("to", ""),
        })
    return procesados


def flujo_demo(lat, lng):
    rnd = random.random()
    if rnd < 0.15:
        nivel = "bloqueado"
    elif rnd < 0.4:
        nivel = "congestionado"
    else:
        nivel = "fluido"
    return {
        "geometria": [(lat, lng), (lat + 0.0007, lng + 0.0009)],
        "velocidad_actual": 20 if nivel == "bloqueado" else 40 if nivel == "congestionado" else 62,
        "velocidad_libre": 60,
        "cierre": nivel == "bloqueado",
        "frc": "FRC4",
    }


def incidentes_demo():
    base = [
        ("accidente", -34.5912, -58.3891, "Choque múltiple sobre Av. 9 de Julio", 35),
        ("obras", -34.6138, -58.4300, "Trabajos de pavimentación en Av. Corrientes", 20),
        ("accidente", -34.6200, -58.3750, "Colisión entre auto y moto", 15),
        ("obras", -34.5908, -58.4110, "Reparación de semáforos y señalización", 10),
    ]
    resultado = []
    for tipo, lat, lng, desc, demora in base:
        if random.random() < 0.75:
            resultado.append({"lat": lat, "lng": lng, "tipo": tipo, "descripcion": desc, "demora_min": demora, "desde": "", "hasta": ""})
    return resultado


@st.cache_data(ttl=30, show_spinner="Consultando tránsito en CABA...")
def obtener_datos(key: str):
    if key:
        flujo = []
        for lat, lng in puntos_ciudad():
            try:
                flujo.append(consultar_flujo(lat, lng, key))
            except Exception:
                continue
        try:
            incidentes = consultar_incidentes(key)
        except Exception:
            incidentes = []
        modo = "real"
    else:
        flujo = [flujo_demo(lat, lng) for lat, lng in puntos_ciudad()]
        incidentes = incidentes_demo()
        modo = "demo"
    return flujo, incidentes, modo


def construir_mapa(flujo, incidentes, controles):
    mapa = folium.Map(location=CABA_CENTER, zoom_start=12, tiles="cartodbpositron", control_scale=True)
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
        if inc["tipo"] == "accidente":
            color, icono = "red", "exclamation-triangle"
        else:
            color, icono = "darkorange", "wrench"
        texto = (f"<b>{'Accidente' if inc['tipo'] == 'accidente' else 'Obras / trabajadores'}</b><br>"
                 f"{inc['descripcion']}<br>Demora estimada: {inc['demora_min']} min")
        folium.Marker(
            [inc["lat"], inc["lng"]],
            icon=folium.Icon(color=color, icon=icono, prefix="fa"),
            popup=folium.Popup(texto, max_width=280),
        ).add_to(mapa)

    for c in controles:
        texto = f"<b>{c.get('tipo', 'Control policial')}</b><br>{c.get('descripcion', '')}"
        folium.Marker(
            [c["lat"], c["lng"]],
            icon=folium.Icon(color="blue", icon="shield-halved", prefix="fa"),
            popup=folium.Popup(texto, max_width=280),
            tooltip="Control reportado por usuarios",
        ).add_to(mapa)

    leyenda = """
    <div style="position:fixed; bottom:30px; left:60px; z-index:9999; background:white;
                padding:8px 12px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,.3);
                font-family:sans-serif; font-size:12px; line-height:1.6">
      <b>Estado del tránsito</b><br>
      <span style="color:#38c0ff">—</span> Fluido (tranquilo)<br>
      <span style="color:#ff8c00">—</span> Congestionado<br>
      <span style="color:#d32f2f">—</span> Trabado / bloqueado<br>
      <span style="color:red">⚠</span> Accidente &nbsp; <span style="color:darkorange">🔧</span> Obras<br>
      <span style="color:blue">🛡</span> Control reportado
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(leyenda))
    return mapa


def main():
    st.set_page_config(page_title="Tránsito en Vivo — CABA", page_icon="🚦", layout="wide")
    st_autorefresh(interval=30000, key="refresco_transito")

    key = leer_secretos("TOMTOM_KEY") or leer_secretos("tomtom_key") or os.environ.get("TOMTOM_KEY", "").strip()
    controles = cargar_controles()

    st.title("🚦 Estado del Tránsito en Vivo — Ciudad de Buenos Aires")
    st.caption("Datos públicos de tráfico en tiempo real (TomTom Traffic). Se actualiza automáticamente cada 30 segundos.")

    with st.sidebar:
        st.header("Configuración")
        if key:
            st.success("API key de TomTom configurada. Modo: **tiempo real**.")
        else:
            st.warning("Sin API key. Modo **DEMO** con datos simulados. "
                       "Obtené tu clave gratis en https://developer.tomtom.com y cargala en "
                       "`.streamlit/secrets.toml` como `tomtom_key` o en la variable de entorno `TOMTOM_KEY`.")
        if st.button("🔄 Forzar actualización ahora"):
            obtener_datos.clear()
            st.rerun()
        st.divider()
        st.subheader("Controles reportados")
        if controles:
            st.write(f"Total: {len(controles)}")
            for c in controles:
                col_a, col_b = st.columns([4, 1])
                col_a.write(f"**{c.get('tipo','')}** ({c.get('lat',0):.4f}, {c.get('lng',0):.4f})")
                if col_b.button("🗑", key=f"del_{c['id']}"):
                    controles = [x for x in controles if x["id"] != c["id"]]
                    guardar_controles(controles)
                    st.rerun()
        else:
            st.write("Todavía no hay controles reportados.")

    flujo, incidentes, modo = obtener_datos(key)
    mapa = construir_mapa(flujo, incidentes, controles)

    col_map, col_panel = st.columns([3, 1])
    with col_map:
        resultado_mapa = st_folium(mapa, width="100%", height=620)
        ultima = time.strftime("%H:%M:%S")
        st.caption(f"Última actualización: {ultima} — Modo: {'tiempo real' if modo == 'real' else 'demo'} — "
                   f"{len(flujo)} tramos viales · {len(incidentes)} incidentes · {len(controles)} controles reportados")

    click = resultado_mapa.get("click_data") if resultado_mapa else None
    lat_click = click.get("lat") if click else None
    lng_click = click.get("lng") if click else None

    with col_panel:
        st.subheader("📍 Reportar control policial")
        st.write("Hacé clic sobre el mapa para marcar la ubicación, o ingresala manualmente.")
        if lat_click is not None:
            st.info(f"Marcaste el punto ({lat_click:.5f}, {lng_click:.5f})")
        with st.form("reporte_control"):
            lat_in = st.number_input("Latitud", value=lat_click if lat_click is not None else CABA_CENTER[0], format="%.6f")
            lng_in = st.number_input("Longitud", value=lng_click if lng_click is not None else CABA_CENTER[1], format="%.6f")
            tipo = st.selectbox("Tipo de control", ["Control policial", "Alcoholemia", "Radar fijo", "Radar móvil", "Otro"])
            desc = st.text_input("Descripción (opcional)")
            enviado = st.form_submit_button("Guardar reporte")
            if enviado:
                if not en_caba(lat_in, lng_in):
                    st.error("Las coordenadas están fuera de la Ciudad de Buenos Aires.")
                else:
                    controles.append({
                        "id": int(time.time() * 1000),
                        "lat": lat_in,
                        "lng": lng_in,
                        "tipo": tipo,
                        "descripcion": desc.strip() or "Sin descripción",
                        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    guardar_controles(controles)
                    obtener_datos.clear()
                    st.success("Reporte guardado. Se muestra en el mapa al actualizar.")
                    st.rerun()


if __name__ == "__main__":
    main()