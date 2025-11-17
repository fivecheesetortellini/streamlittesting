import streamlit as st
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import leafmap.foliumap as leafmap
import tempfile
import simplekml
import xml.sax.saxutils as sax

st.title("Parcel Lookup & Export")

# Database connection
engine = create_engine(
    "postgresql+psycopg2://iuneripuneefgiujn:JyZ4ZOKy.#cUj88f$Vlg@gis-postgresql-v15.postgres.database.azure.com/fisher",
    pool_recycle=5
)


projects = pd.read_sql(
    "SELECT DISTINCT project_name FROM parcels.masterparcel ORDER BY project_name;", engine
)
selected_project = st.selectbox("Select a project:", projects["project_name"])


symbology_type = st.selectbox(
    "Select Symbology Type:",
    ["Red / Yellow / Green", "Land Control Status"]
)


if symbology_type == "Land Control Status":
    lc_folder_structure = st.selectbox(
        "Select Folder Structure:",
        ["By Status", "By Owner"]
    )

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

    red_statuses = ["Not Interested / Declined", "Opposition", "Signed with Competition"]
    yellow_statuses = [
        "Contacted", "Other Parcel Signed", "Attempted Contact",
        "Interested", "Negotiations Started", "Executable Contract Out to Land Owner"
    ]
    green_statuses = ["Signed Lease", "Multiple Agreements Signed", "QC Check Required",
                      "Signed Neighbor Agreement", "Signed Other Agreement"]

    red_yellow_green_hex = {
    "Red": "e41a1c",      
    "Yellow": "ffff33",   
    "Green": "4daf4a",   
    }

    land_control_hex = {
        "Signed Lease": "4daf4a",
        "Contacted": "b6ecfc",
        "Opposition": "e41a1c",
        "Interested": "ffff33",
        "Not Interested / Declined": "e41a1c",
        "Negotiations Started": "ffff33",
        "Signed Neighbor Agreement": "ff7f00",
        "Multiple Agreements Signed": "4daf4a",
        "QC Check Required": "4daf4a",
        "Signed with Competition": "984ea3",
        "Attempted Contact": "FFFF00",
        "Executable Contract Out to Land Owner": "0d7a9e",
        "Other Parcel Signed": "686D68",
        "Signed Other Agreement": "4daf4a"
    }

  
    if symbology_type == "Red / Yellow / Green":
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

    else:  # Land Control Status
        if lc_folder_structure == "By Status":
            folders = {status: root_folder.newfolder(name=status) for status in gdf["parcel_status"].unique()}
        else:  # By Owner
            folders = {owner: root_folder.newfolder(name=owner) for owner in gdf["owner"].unique()}


    def extract_coords(geom_part):
        coords = []
        for x, y, *rest in geom_part.exterior.coords:
            coords.append((x, y))
        return coords

  

    def create_polygon(folder, geom, color, description, parcel_id):
        pol = folder.newpolygon(name=parcel_id)
        pol.description = description

        if geom.geom_type == "Polygon":
            coords = extract_coords(geom)
            pol.outerboundaryis = coords
        elif geom.geom_type == "MultiPolygon":
            for part in geom.geoms:
                coords = extract_coords(part)
                pol.outerboundaryis = coords

        if color.lower() in ["#ffffff", "ffffff"]:
            pol.style.polystyle.color = simplekml.Color.changealphaint(0, simplekml.Color.white)
        else:
            pol.style.polystyle.color = simplekml.Color.changealphaint(
                215, simplekml.Color.hex(color)
            )

        pol.style.linestyle.color = simplekml.Color.black
        pol.style.linestyle.width = 1

   


    for _, row in gdf.iterrows():
        geom = row["shape"]
        owner = row.get("owner", "Unknown Owner")
        parcel_id = row.get("parcel_id", "Unknown ID")
        parcel_status = row.get("parcel_status", "Unknown Status")
        agreement_type = row.get("agreement_type", "Unknown")
        sf_url = row.get("sf_url", "N/A")

        description = (
            f"<b>Owner:</b> {owner}<br>"
            f"<b>Parcel ID:</b> {parcel_id}<br>"
            f"<b>Parcel Status:</b> {parcel_status}<br>"
            f"<b>Agreement Type:</b> {agreement_type}<br>"
            f"<b>Salesforce URL:</b> <a href='{sf_url}' target='_blank'>{sf_url}</a>"
        )

        if symbology_type == "Red / Yellow / Green":
            folder_key = get_color_category(parcel_status)
            if folder_key is None:
                continue
            folder = folders[folder_key]
            color = red_yellow_green_hex[folder_key]
        else:  # Land Control Status
            folder = folders[parcel_status] if lc_folder_structure == "By Status" else folders[owner]
            color = land_control_hex.get(parcel_status, "#ffffff")
      

        create_polygon(folder, geom, color, description, parcel_id)

   
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmp:
        kml.save(tmp.name)
        with open(tmp.name, "rb") as file:
            st.download_button(
                label="Download KML",
                data=file,
                file_name=f"{selected_project}_parcels.kml",
                mime="application/vnd.google-earth.kml+xml"
            )