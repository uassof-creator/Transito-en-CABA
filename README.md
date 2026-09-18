# Tránsito en Vivo — Ciudad de Buenos Aires

Aplicación web interactiva (Python + Streamlit) que muestra el **estado del tránsito en tiempo real de la Ciudad de Buenos Aires**, coloreando los tramos viales afectados según su nivel de congestión e indicando los incidentes activos.

## Funcionalidades

- **Mapa interactivo** de la Ciudad de Buenos Aires con el estado del tránsito pintado **tramo por tramo**:
  - 🔵 **Celeste** → tramos con flujo tranquilo
  - 🟠 **Naranja** → tramos congestionados
  - 🔴 **Rojo** → tramos trabados o bloqueados
- **Zoom total**: acercarse y alejarse con la **rueda del mouse** o con los botones **+ / −** que aparecen en el mapa.
- **Iconos de incidentes** sobre las zonas afectadas:
  - ⚠️ **Accidentes** (rojo, ícono de exclamación)
  - 🔧 **Obras / trabajadores en la vía** (naranja, ícono de llave)
- **Actualización automática cada 30 segundos**, con botón para forzar la actualización manualmente.
- **Leyenda** en el mapa y en el panel lateral para identificar cada color e ícono.
- **Siempre datos reales**: la app se conecta a la API pública gratuita de TomTom Traffic. Si la API key no está configurada, muestra un aviso instructivo (no genera datos simulados).

## Requisitos previos

- Python 3.9 o superior
- pip
- Una **API key gratuita de TomTom** (plan gratis de la API pública). Sin ella la app no muestra datos reales: no existe ninguna API de tránsito de CABA completamente abierta (la oficial de la Ciudad está suspendida desde hace tiempo).

## Cómo obtener una API key gratuita (TomTom)

1. Ingresá a [https://developer.tomtom.com](https://developer.tomtom.com) y registrate (plan gratuito).
2. Creá una app y copiá tu **Primary Key**.
3. Cargala en el archivo `.streamlit/secrets.toml` dentro de esta carpeta:

```toml
tomtom_key = "TU_CLAVE_PRIMARY"
```

> También puede cargarse mediante la variable de entorno `TOMTOM_KEY` en el sistema.
>
> 🔒 **Importante (seguridad)**: el archivo `.streamlit/secrets.toml` **no debe subirse a GitHub ni compartirse**. Este proyecto incluye un `.gitignore` que excluye la carpeta `.streamlit/`. Si subís el repositorio a GitHub, borrá el `secrets.toml` del historial y **rotá la clave** en el dashboard de TomTom (aparece expuesta). Si desplegás en Streamlit Cloud, configurá la clave en *Settings → Secrets* de la app, no en el código.
>
> ⚠️ Nota sobre cuota gratuita: el plan free de TomTom limita la cantidad de llamadas mensuales (~2500). Un refresco continuo cada 30 segundos puede agotar la cuota rápidamente. Para uso extendido, aumentá el intervalo de refresco o evaluá un plan superior.

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

1. **Ver el estado del tránsito**: cada tramo de los principales corredores viales de CABA (Av. 9 de Julio, Rivadavia, Corrientes, Santa Fe, Cabildo, General Paz, autopistas AU1, AU6, presidente Illia, etc.) se pinta con el color de su nivel de congestión. Hacé clic sobre una línea para ver la velocidad actual vs. la velocidad libre.
2. **Navegar el mapa**: usá la rueda del mouse sobre el mapa o los botones **+ / −** de la esquina para hacer zoom. Podés arrastrar para moverte por la ciudad.
3. **Ver incidentes**: los íconos rojos (accidente) y naranjas (obras) muestran descripción y demora estimada.
4. **Actualizar**: la app se refresca sola cada 30 segundos; también podés pulsar *"Forzar actualización ahora"* en el panel lateral.

## Fuente de datos

| Dato                  | Fuente                                     | Descripción                                             |
|-----------------------|--------------------------------------------|---------------------------------------------------------|
| Velocidad/Congestión  | TomTom Traffic Flow (Flow Segment Data)    | Velocidad actual vs. libre por tramo de vía             |
| Incidentes            | TomTom Traffic Incidents (Incident Details)| Accidentes y obras dentro del perímetro de CABA         |

## Arquitectura y decisiones técnicas

1. **Consulta de flujo (congestión)**: por cada tramo de los corredores viales de la ciudad se consulta la API `flowSegmentData`, que devuelve la geometría del tramo, la velocidad actual y la velocidad en flujo libre. Con la relación `velocidad_actual / velocidad_libre` se clasifica:
   - `ratio >= 0.75` → **celeste** (fluido)
   - `0.45 <= ratio < 0.75` → **naranja** (congestionado)
   - `ratio < 0.45` o cierre de calle → **rojo** (trabado)

2. **Consulta de incidentes**: la API `incidentDetails` devuelve todos los incidentes dentro del bounding box de CABA. Se filtran las categorías:
   - `2` (accidente) → ícono ⚠️ rojo
   - `8`, `9`, `10` (carril cerrado, ruta cerrada, obras) → ícono 🔧 naranja

3. **Zoom en el mapa**: el mapa se crea con `scroll_wheel_zoom=True`, lo que habilita el zoom con la rueda del mouse. Los controles **+ / −** de Leaflet vienen habilitados por defecto (zoom control estándar), con límites `min_zoom` y `max_zoom` para evitar alejarse demasiado.

4. **Auto-refresco**: `streamlit-autorefresh` vuelve a ejecutar la app cada **30 segundos**. Las consultas a las APIs usan caché con TTL de 30 s (`@st.cache_data(ttl=30)`), evitando llamadas redundantes.

5. **Sin datos falsos**: no existe ningún modo de demostración ni datos simulados. El mapa se construye exclusivamente con las respuestas en tiempo real de TomTom. Si la clave no está configurada o la consulta falla, la app avisa al usuario en lugar de inventar información.

## Archivos del proyecto

```
transito-ba/
├── app.py              # Código fuente principal
├── requirements.txt    # Dependencias de Python
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
- La cuota gratuita de TomTom puede resultar insuficiente para un refresco continuo de 30 s durante mucho tiempo.
- La API oficial de tránsito del Gobierno de la Ciudad (GCBA) está suspendida; por eso se usa TomTom como fuente pública.

## Licencia

Proyecto de uso libre, con fines educativos. Los datos de tráfico pertenecen a sus respectivas fuentes (TomTom).