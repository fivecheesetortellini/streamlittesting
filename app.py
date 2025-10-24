import streamlit as st
import leafmap
import leafmap.foliumap as leafmap
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
        elif uploaded_file.name.endswith(".kml"):
            try:
                # ✅ Parse the KML using fastkml instead of fiona
                k = kml.KML()
                with open(file_path, 'rt', encoding='utf-8') as f:
                    doc = f.read()
                k.from_string(doc.encode('utf-8'))

                features = []
                for feature in k.features:
                    for f2 in feature.features():
                        if hasattr(f2, "geometry") and f2.geometry is not None:
                            geom = shape(f2.geometry.__geo_interface__)
                            features.append({"geometry": geom, "name": f2.name})

                if features:
                    gdf = gpd.GeoDataFrame(features)
                    st.success(f"✅ Loaded {len(gdf)} features from KML")
                    m.add_gdf(gdf, layer_name="Uploaded KML")
                    m.zoom_to_gdf(gdf)
                else:
                    st.warning("⚠️ No valid features found in KML")

            except Exception as e:
                st.error(f"Error reading KML: {e}")

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

# ---- Show map ----
m.to_streamlit(height=700)
