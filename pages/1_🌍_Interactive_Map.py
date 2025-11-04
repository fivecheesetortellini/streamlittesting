import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
from streamlit_folium import st_folium


#Connect to Postgres
engine = create_engine("postgresql+psycopg2://iuneripuneefgiujn:JyZ4ZOKy.#cUj88f$Vlg@gis-postgresql-v15.postgres.database.azure.com/cousteau", pool_recycle=5)

#Start the Session State to keep layers in map thru user clicks 
if "added_layers" not in st.session_state:
    st.session_state["added_layers"] = []

if "selected_basemap" not in st.session_state:
    st.session_state["selected_basemap"] = "CartoDB.Positron"

if "map_state" not in st.session_state:
    st.session_state["map_state"] = {
        "center": [37.8, -96],
        "zoom": 4
    }
st.sidebar.subheader("🗺️ Basemap Options")
basemaps = ["CartoDB.Positron",
            "OpenStreetMap",
            "TERRAIN",
            "ROADMAP",
            "SATELLITE",
            "HYBRID"]
selected_basemap = st.sidebar.selectbox("Select a basemap:", basemaps, index=basemaps.index(st.session_state["selected_basemap"]))
st.session_state["selected_basemap"] = selected_basemap

# Create the Map
m = leafmap.Map(center=[37.8, -96], zoom=4)
m.add_basemap(selected_basemap)



# Sidebar Panel Information
st.sidebar.title("About")
st.sidebar.info("Using this page, the user can edit data that they have access to from the geoSLOT. If you have any questions, reach out to the GSYNC team, shown below.")
st.sidebar.image("C:/Users/AbbyHildebrandt/GSYNC.png", use_column_width=True)

# --- Main UI ---
st.title("View Data From geoSLOT")
st.subheader("📚 Available PostGIS Layers")

def list_postgis_layers(engine):
    query = """
    SELECT f_table_schema AS schema,
           f_table_name AS name,
           f_geometry_column AS geom_column,
           srid,
           type
    FROM public.geometry_columns
    ORDER BY f_table_schema, f_table_name;
    """
    return pd.read_sql(query, engine)

layers_df = list_postgis_layers(engine)
st.dataframe(layers_df)

# --- User selection ---
st.subheader("🗺 Add a PostGIS Layer to the Map")

if not layers_df.empty:
    selected_layer = st.selectbox(
        "Select a spatial layer:",
        [f"{r['schema']}.{r['name']}" for _, r in layers_df.iterrows()]
    )

    if st.button("Add Selected Layer"):
        schema, table = selected_layer.split(".")
        geom_col = layers_df.loc[
            (layers_df["schema"] == schema) & (layers_df["name"] == table),
            "geom_column"
        ].values[0]

        sql = f'SELECT * FROM "{schema}"."{table}"'
        gdf_pg = gpd.read_postgis(sql, engine, geom_col=geom_col)

        st.success(f"✅ Loaded {len(gdf_pg)} features from {selected_layer}")
        
        # Save to session state
        st.session_state["added_layers"].append({
            "name": selected_layer,
            "gdf": gdf_pg
        })

for lyr in st.session_state["added_layers"]:
    m.add_gdf(lyr["gdf"], layer_name=lyr["name"])

# --- Fit to last layer added ---
if st.session_state["added_layers"]:
    m.zoom_to_gdf(st.session_state["added_layers"][-1]["gdf"])

# --- Render map ---
map_data= st_folium(m, width=700, height=500)

if map_data and map_data.get("center") and map_data.get("zoom"):
    st.session_state["map_state"]["center"] = [
        map_data["center"]["lat"],
        map_data["center"]["lng"]
    ]
    st.session_state["map_state"]["zoom"] = map_data["zoom"]