import streamlit as st
import folium
from streamlit_folium import st_folium

st.title("🌍 My Folium Map in Streamlit")

# Create a base map centered on the U.S.
m = folium.Map(location=[39.5, -98.35], zoom_start=4)

# Add a marker
folium.Marker(
    location=[37.7749, -122.4194],
    popup="San Francisco",
    tooltip="Click for more info"
).add_to(m)

# Render the map inside Streamlit
st_data = st_folium(m, width=700, height=500)

# Optional: display click info
if st_data["last_clicked"]:
    st.write("You clicked at:", st_data["last_clicked"])