import folium
import streamlit as st
from streamlit_folium import st_folium

from summarize import summarize_location_for_building_category, initial_summary

# Set default coordinates
st.session_state.lat = 22.5549
st.session_state.lng = 88.3504

# Use a map
folium_map = folium.Map(location=[st.session_state.lat, st.session_state.lng], zoom_start=12)
folium_map.add_child(folium.LatLngPopup())

# Create two-column layout
st.set_page_config(layout='wide')
location, summary = st.columns(2)

with location:
    # Show map
    st.header("Choose a location")
    map_data = st_folium(folium_map, height=500, width=704)

    # Click Button for summarizing
    summarize = st.button("Summarize this location")

with summary:
    if summarize:
        lat = st.session_state.lat
        lng = st.session_state.lng
        if map_data['last_clicked'] is not None:
            lat = map_data['last_clicked']['lat']
            lng = map_data['last_clicked']['lng']
        st.header("Summary of this location:")

        st.write(initial_summary((lat, lng)))
        for category in range(8):
            st.write(summarize_location_for_building_category((lat, lng), category))

