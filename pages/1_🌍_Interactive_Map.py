import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
from streamlit_folium import st_folium

# --- DB connection ---
engine = create_engine("postgresql+psycopg2://iuneripuneefgiujn:JyZ4ZOKy.#cUj88f$Vlg@gis-postgresql-v15.postgres.database.azure.com/cousteau", pool_recycle=5)

# --- Initialize map once ---
if "map" not in st.session_state:
    m = leafmap.Map(center=[37.8, -96], zoom=4)
    m.add_basemap("CartoDB.Positron")
    st.session_state["map"] = m
else:
    m = st.session_state["map"]

# --- Sidebar ---
st.sidebar.title("About")
st.sidebar.info("Use this page to view data in the geoSLOT database!")
st.sidebar.image("https://i.imgur.com/UbOXYAU.png")

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

        # --- Add to persistent map ---
        m.add_gdf(gdf_pg, layer_name=selected_layer)
        m.zoom_to_gdf(gdf_pg)

        # Save back to session state
        st.session_state["map"] = m

else:
    st.info("No spatial layers found in your PostGIS database. Is your VPN turned on?")

# --- Render map ---
st_folium(m, width=700, height=500)

