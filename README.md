# Tránsito en Vivo — Ciudad de Buenos Aires

Aplicación web interactiva (Python + Streamlit) que muestra el **estado del tránsito en tiempo real de la Ciudad de Buenos Aires**, junto con incidentes de tráfico y controles policiales reportados por los usuarios (estilo Waze).

## Funcionalidades

- **Mapa interactivo** de la Ciudad de Buenos Aires con el estado del tránsito por tramo vial, pintado según la congestión:
  - 🔵 **Celeste** → vías tranquilas (flujo libre)
  - 🟠 **Naranja** → vías congestionadas
  - 🔴 **Rojo** → vías trabadas o bloqueadas
- **Iconos de incidentes** en las zonas afectadas:
  - ⚠️ **Accidentes** (rojo, ícono de exclamación)
  - 🔧 **Obras / trabajadores en la vía** (naranja, ícono de llave)
- **Controles policiales reportados por usuarios** (estilo Waze): se marcan haciendo clic sobre el mapa o cargando coordenadas manualmente. Se guardan de forma persistente en `controles.json`.
- **Actualización automática cada 30 segundos** con botón para forzar la actualización manualmente.
- **Leyenda** integrada en el mapa para identificar cada color e ícono.

## Requisitos previos

- Python 3.9 o superior
- pip
- (Opcional) Una **API key gratuita de TomTom** para ver datos en tiempo real real. Sin ella, la app funciona en **modo demo** con datos simulados.

## Cómo obtener una API key gratuita (TomTom)

1. Ingresá a [https://developer.tomtom.com](https://developer.tomtom.com) y registrate (plan gratuito).
2. Creá una app y copiá tu **Primary Key**.
3. Cargala en el archivo `.streamlit/secrets.toml` dentro de esta carpeta:

```toml
tomtom_key = "TU_CLAVE_PRIMARY"
```

> También puede cargarse mediante la variable de entorno `TOMTOM_KEY` en el sistema.
>
> ⚠️ Nota sobre cuota gratuita: el plan free de TomTom limita la cantidad de llamadas mensuales (~2500). Un refresco continuo cada 30 segundos puede agotar la cuota rápidamente. Para uso extendido, aumentá el intervalo de refresco o evaluá un plan superior. Sin clave, la app corre en modo demo sin consumir llamadas.

## Instalación

1. Entrá a la carpeta del proyecto de tránsito:

```bash
cd transito-ba
```

2. (Opcional) Creá y activá un entorno virtual:

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
```

3. Instalá las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

Se abrirá automáticamente el navegador en `http://localhost:8501`.

## Cómo usar la aplicación

1. **Ver el estado del tránsito**: el mapa se pinta con los colores de congestión de los principales corredores viales de CABA (Av. 9 de Julio, Rivadavia, Corrientes, Santa Fe, Cabildo, General Paz, autopistas AU1, AU6, presidentes Illia, etc.). Hacé clic sobre cualquier línea para ver la velocidad actual vs. la velocidad libre.
2. **Ver incidentes**: los íconos rojos (accidente) y naranjas (obras) muestran detalles como descripción y demora estimada.
3. **Reportar un control policial**: hacé clic sobre el mapa en el punto del control, completá el tipo (control policial, alcoholemia, radar fijo/móvil, otro) y una descripción opcional, y pulsá *"Guardar reporte"*. El marcador azul 🛡 queda visible para todos los usuarios de la app.
4. **Eliminar reportes**: desde el panel lateral podés borrar cualquier control reportado.

## Fuente de datos

| Dato                  | Fuente                                     | Descripción                                             |
|-----------------------|--------------------------------------------|---------------------------------------------------------|
| Velocidad/Congestión  | TomTom Traffic Flow (Flow Segment Data)    | Velocidad actual vs. libre por segmento de vía          |
| Incidentes            | TomTom Traffic Incidents (Incident Details)| Accidentes y obras dentro del perímetro de CABA         |
| Controles policiales  | Reportes de usuarios locales               | Guardados en `controles.json` (persistencia local)      |

## Arquitectura y decisiones técnicas

1. **Consulta de flujo (congestión)**: por cada tramo de los corredores viales de la ciudad se consulta la API `flowSegmentData`, que devuelve la geometría del tramo, la velocidad actual y la velocidad en flujo libre. Con la relación `velocidad_actual / velocidad_libre` se clasifica:
   - `ratio >= 0.75` → **celeste** (fluido)
   - `0.45 <= ratio < 0.75` → **naranja** (congestionado)
   - `ratio < 0.45` o cierre de calle → **rojo** (trabado)

2. **Consulta de incidentes**: la API `incidentDetails` devuelve todos los incidentes dentro del bounding box de CABA. Se filtran las categorías:
   - `2` (accidente) → ícono ⚠️ rojo
   - `8`, `9`, `10` (carril cerrado, ruta cerrada, obras) → ícono 🔧 naranja

3. **Auto-refresco**: `streamlit-autorefresh` vuelve a ejecutar la app cada **30 segundos**. Las consultas a las APIs usan caché con TTL de 30 s (`@st.cache_data(ttl=30)`), evitando llamadas redundantes.

4. **Reportes de usuarios (estilo Waze)**: la interacción de clic del mapa la captura el componente `streamlit-folium` (`click_data`). Los reportes aceptados (coordenadas dentro de CABA) se guardan en `controles.json` y se dibujan como marcadores azules. La persistencia en JSON hace que los reportes sobrevivan a los reinicios.

5. **Modo demo**: si no hay API key configurada, la app genera datos de tránsito e incidentes simulados de forma aleatoria para poder visualizar y probar todas las funciones sin conectarse a internet ni consumir cuota.

## Archivos del proyecto

```
transito-ba/
├── app.py              # Código fuente principal
├── requirements.txt    # Dependencias de Python
├── controles.json      # Persistencia de controles reportados por usuarios
└── README.md           # Este archivo
```

## Dependencias

| Paquete               | Descripción                                       |
|-----------------------|---------------------------------------------------|
| streamlit             | Framework para crear apps web en Python           |
| streamlit-autorefresh | Refresco automático de la app cada X milisegundos |
| requests              | Cliente HTTP para consultar las APIs de tránsito  |
| folium                | Creación de mapas interactivos (Leaflet)          |
| streamlit-folium      | Integración de folium dentro de Streamlit         |

## Limitaciones

- La cobertura de vías pintadas está limitada a los principales corredores viales configurados (no todas las calles de la ciudad).
- En modo demo los datos no son reales; solo sirven para evaluar la interfaz.
- La cuota gratuita de TomTom puede resultar insuficiente para un refresco continuo de 30 s durante mucho tiempo.

## Licencia

Proyecto de uso libre, con fines educativos. Los datos de tráfico pertenecen a sus respectivas fuentes (TomTom).