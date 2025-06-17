import streamlit as st
import osmnx as ox
import networkx as nx
import requests
import folium
from folium.plugins import HeatMap
import pandas as pd
import tempfile

# ---------------------- Config ----------------------
st.set_page_config(page_title="🚨 Emergency Dispatch AI", layout="wide")
api_key = "YOUR_TOMTOM_API_KEY_HERE"

# ---------------------- Header ----------------------
st.title("🚨 AI Emergency Response Optimization")
st.markdown("Compare live ETA from multiple vehicles & visualize traffic.")

# ---------------------- Inputs ----------------------
st.sidebar.header("Incident Location")
incident_lat = st.sidebar.number_input("Latitude", value=19.0760, format="%.6f")
incident_lon = st.sidebar.number_input("Longitude", value=72.8777, format="%.6f")

vehicles = {
    'Vehicle A': (19.0913, 72.8549),
    'Vehicle B': (19.0760, 72.8777),
    'Vehicle C': (19.1136, 72.8697)
}

# ---------------------- Load Map ----------------------
@st.cache_resource
def load_graph(city_name="Mumbai, India"):
    return ox.graph_from_place(city_name, network_type='drive')

G = load_graph()

# ---------------------- Functions ----------------------
def get_eta(vehicle_point, incident_point):
    try:
        vehicle_node = ox.nearest_nodes(G, X=vehicle_point[1], Y=vehicle_point[0])
        incident_node = ox.nearest_nodes(G, X=incident_point[1], Y=incident_point[0])
        route = nx.shortest_path(G, vehicle_node, incident_node, weight='length')
        route_length_km = nx.shortest_path_length(G, vehicle_node, incident_node, weight='length') / 1000

        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={vehicle_point[0]},{vehicle_point[1]}&unit=KMPH&key={api_key}"
        r = requests.get(url).json()

        if 'flowSegmentData' in r:
            speed = r['flowSegmentData']['currentSpeed']
            eta = (route_length_km / speed) * 60 if speed > 0 else float('inf')
            return round(eta, 2), speed, route_length_km
        else:
            return float('inf'), 0, route_length_km
    except Exception as e:
        return float('inf'), 0, 0

# ---------------------- ETA Calculations ----------------------
incident_point = (incident_lat, incident_lon)
results = []

for name, loc in vehicles.items():
    eta, speed, dist = get_eta(loc, incident_point)
    results.append({'Vehicle': name, 'ETA (min)': eta, 'Speed (km/h)': speed, 'Distance (km)': dist})

df = pd.DataFrame(results).sort_values(by="ETA (min)")
best_vehicle = df.iloc[0]['Vehicle']

# ---------------------- Output ----------------------
st.subheader("🚗 ETA Comparison")
st.dataframe(df, use_container_width=True)

st.success(f"🟢 **Best Vehicle to Dispatch: {best_vehicle}**")

# ---------------------- Heatmap ----------------------
if st.button("Generate Traffic Heatmap"):
    sample_points = list(vehicles.values()) + [incident_point]
    heat_data = []
    for lat, lon in sample_points:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={lat},{lon}&unit=KMPH&key={api_key}"
        r = requests.get(url).json()
        if 'flowSegmentData' in r:
            speed = r['flowSegmentData']['currentSpeed']
            heat_data.append([lat, lon, speed])

    m = folium.Map(location=[incident_lat, incident_lon], zoom_start=12)
    HeatMap(heat_data, min_opacity=0.4, radius=25).add_to(m)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        m.save(f.name)
        st.success("✅ Heatmap generated.")
        st.download_button("📥 Download Heatmap", data=open(f.name, 'rb'), file_name="heatmap.html")

