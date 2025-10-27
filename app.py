import streamlit as st
import leafmap
import leafmap.foliumap as leafmap
from streamlit_folium import st_folium
import geopandas as gpd
from fastkml import kml
import tempfile
import zipfile
import os
from shapely.geometry import shape
import tempfile
import io
import pandas as pd
from shapely.geometry import Point

# ---- Streamlit setup ----
st.set_page_config(page_title="Map Viewer", layout="wide")
st.title("🌎 Map Viewer with Upload Support")

# ---- Create Leafmap Map ----
m = leafmap.Map(center=[37.8, -96], zoom=4)
m.add_basemap("CartoDB.Positron")

st.sidebar.header("📂 Upload Spatial Data")

# ---- File uploader ----


uploaded_file = st.sidebar.file_uploader(
    "Upload a Shapefile (.zip), KML, GeoJSON, or CSV file",
    type=["zip", "kml", "geojson", "csv"]
)

# ---- Handle uploads ----
if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, uploaded_file.name)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # Case 1: Shapefile (.zip)
        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
            shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if shp_files:
                gdf = gpd.read_file(shp_files[0])
                st.success(f"✅ Loaded {len(gdf)} features from Shapefile")
                m.add_gdf(gdf, layer_name="Uploaded Shapefile")
                m.zoom_to_gdf(gdf)
            else:
                st.error("No .shp file found in the ZIP archive.")

        # Case 2: KML
        elif uploaded_file.name.endswith('.kml'):
            gdf = gpd.read_file(uploaded_file, driver='KML')
            if gdf.crs is None or gdf.crs.to_string() != 'EPSG:4326':
                gdf = gdf.set_crs(epsg=4326, allow_override=True)
            gdf = gdf[gdf.geometry.notnull()]
            gdf = gdf.explode(index_parts=False, ignore_index=True)
            if st.success(f"✅ Loaded {len(gdf)} features from KML"):
                st.write(gdf.geom_type.value_counts())
                m.add_gdf(gdf, layer_name="Uploaded KML")
                m.zoom_to_gdf(gdf)
            else: 
                st.error("Error adding KML to map.")
            
        # Case 3: GeoJSON
        elif uploaded_file.name.endswith(".geojson"):
            gdf = gpd.read_file(file_path)
            st.success(f"✅ Loaded {len(gdf)} features from GeoJSON")
            m.add_gdf(gdf, layer_name="Uploaded GeoJSON")
            m.zoom_to_gdf(gdf)

        # Case 4: CSV with lat/lon columns
        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(file_path)
            st.info("📄 CSV detected — looking for lat/lon columns...")

            lat_cols = [col for col in df.columns if 'lat' in col.lower()]
            lon_cols = [col for col in df.columns if 'lon' in col.lower()]

            if lat_cols and lon_cols:
                lat_col = lat_cols[0]
                lon_col = lon_cols[0]
                gdf = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
                    crs="EPSG:4326"
                )
                st.success(f"✅ Loaded {len(gdf)} points from CSV")
                m.add_gdf(gdf, layer_name="Uploaded CSV")
                m.zoom_to_gdf(gdf)
            else:
                st.error("Could not find latitude/longitude columns in CSV.")

        # Show attribute table
        if "gdf" in locals():
            st.subheader("📋 Attribute Table")
            st.dataframe(gdf.head())

st_folium(m, width=700, height=500)

# ---- Show map ----
#m.to_streamlit(height=700)
