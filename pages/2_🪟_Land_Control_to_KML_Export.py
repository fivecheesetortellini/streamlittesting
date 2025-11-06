import streamlit as st
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import leafmap.foliumap as leafmap
import tempfile
import simplekml

st.title("Parcel Lookup & Export")


engine = create_engine("postgresql+psycopg2://iuneripuneefgiujn:JyZ4ZOKy.#cUj88f$Vlg@gis-postgresql-v15.postgres.database.azure.com/fisher", pool_recycle=5)


projects = pd.read_sql("SELECT DISTINCT project_name FROM parcels.masterparcel ORDER BY project_name;", engine)
selected_project = st.selectbox("Select a project:", projects["project_name"])

if selected_project:
    sql = f"SELECT * FROM parcels.masterparcel WHERE project_name = '{selected_project}'"
    gdf = gpd.read_postgis(sql, engine, geom_col="shape")
    st.success(f"Found {len(gdf)} parcels for {selected_project}")


    m = leafmap.Map()
    m.add_gdf(gdf, layer_name=selected_project)
    m.zoom_to_gdf(gdf)
    m.to_streamlit(height=600)

if st.button("Export to KML"):
    kml = simplekml.Kml()
    root_folder = kml.newfolder(name=selected_project)

 
    red_statuses = [
        "Not Interested / Declined",
        "Opposition",
        "Signed with Competition"
    ]
    yellow_statuses = [
        "Contacted",
        "Other Parcel Signed",
        "Attempted Contact",
        "Interested",
        "Negotiations Started",
        "Executable Contract Out to Land Owner"
    ]
    green_statuses = [
        "Signed Lease",
        "Multiple Agreements Signed",
        "QC Check Required",
        "Signed Neighbor Agreement",
        "Signed Other Agreement"
    ]


    color_mapping = {
        "Red": simplekml.Color.changealphaint(100, simplekml.Color.red),
        "Yellow": simplekml.Color.changealphaint(100, simplekml.Color.yellow),
        "Green": simplekml.Color.changealphaint(100, simplekml.Color.green),
    }

 
    folders = {
        "Red": root_folder.newfolder(name="🟥 Red - Not Interested / Declined / Opposition / Signed with Competition"),
        "Yellow": root_folder.newfolder(name="🟨 Yellow - Contacted / Interested / Negotiations / etc."),
        "Green": root_folder.newfolder(name="🟩 Green - Signed / QC Check / Agreements"),
    }


    def get_color_category(status):
        if status in red_statuses:
            return "Red"
        elif status in yellow_statuses:
            return "Yellow"
        elif status in green_statuses:
            return "Green"
        else:
            return None

    def extract_coords(geom_part):
        coords = []
        for x, y, *rest in geom_part.exterior.coords:
            coords.append((x, y))
        return coords


    for _, row in gdf.iterrows():
        geom = row["shape"]
        owner = row.get("owner", "Unknown Owner")
        parcel_id = row.get("parcel_id", "Unknown ID")
        parcel_status = row.get("parcel_status", "Unknown Status")
        agreement_type = row.get("agreement_type", "Unknown")
        sf_url = row.get("sf_url", "N/A")

        color_cat = get_color_category(parcel_status)
        if color_cat is None:
            continue  

        folder = folders[color_cat]
        color = color_mapping[color_cat]

        description = (
            f"<b>Owner:</b> {owner}<br>"
            f"<b>Parcel ID:</b> {parcel_id}<br>"
            f"<b>Parcel Status:</b> {parcel_status}<br>"
            f"<b>Agreement Type:</b> {agreement_type}<br>"
            f"<b>Salesforce URL:</b> "
            f"<a href='{sf_url}' target='_blank'>{sf_url}</a>"
        )

        if geom.geom_type == "Polygon":
            coords = extract_coords(geom)
            pol = folder.newpolygon(name=f"Parcel {parcel_id}")
            pol.outerboundaryis = coords
            pol.description = description
            pol.style.polystyle.color = color
            pol.style.linestyle.width = 2

        elif geom.geom_type == "MultiPolygon":
            for part in geom.geoms:
                coords = extract_coords(part)
                pol = folder.newpolygon(name=f"Parcel {parcel_id}")
                pol.outerboundaryis = coords
                pol.description = description
                pol.style.polystyle.color = color
                pol.style.linestyle.width = 2

    # Save and provide download link
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp:
        kml.save(tmp.name)
        with open(tmp.name, "rb") as file:
            st.download_button(
                label="Download KML",
                data=file,
                file_name=f"{selected_project}_parcels_by_color.kml",
                mime="application/vnd.google-earth.kml+xml"
            )



