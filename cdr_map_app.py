

import streamlit as st
import pandas as pd
import pydeck as pdk
import networkx as nx
import numpy as np
from pyvis.network import Network

st.title(" CDR Analysis & Mapping Tool")

uploaded = st.file_uploader("Upload CDR CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)

    st.write("### Preview", df.head())

    # date filter if needed
    df['start_time'] = pd.to_datetime(df['start_time'], format="%d-%m-%Y %H:%M")

    # Build a selectable list of dates and include an "All" option
    unique_dates = sorted(df['start_time'].dt.date.unique())
    date_options = ["All"] + [d.strftime("%Y-%m-%d") for d in unique_dates]

    selected_date_str = st.selectbox("Select date", date_options, index=0)

    if selected_date_str == "All":
        df_date = df.copy()
    else:
        sel_date = pd.to_datetime(selected_date_str).date()
        df_date = df[df['start_time'].dt.date == sel_date]

    # Search box: filter by caller or callee (substring match)
    search_query = st.text_input("Search number (caller or callee) — leave blank for all")
    if search_query:
        q = str(search_query)
        df_date = df_date[df_date['caller'].astype(str).str.contains(q, na=False) | df_date['callee'].astype(str).str.contains(q, na=False)]

    # Display selection summary
    if selected_date_str == "All":
        st.write("### Records for all dates", df_date)
    else:
        st.write(f"### Records on {selected_date_str}", df_date)

    df_merged = df_date

   # We already have lat/lon in df_date
    df_map = df_date.copy()

    # MAP VIEW
    if df_map.empty:
        st.warning("No records to display for the selected filters.")
    else:
        view_state = pdk.ViewState(
            latitude=df_map["lat"].mean(),
            longitude=df_map["lon"].mean(),
            zoom=9
        )

        # Scatter points (towers)
        points_layer = pdk.Layer(
            "ScatterplotLayer",
            df_map,
            get_position=["lon", "lat"],
            get_radius=120,
            get_fill_color=[255, 0, 0],
            pickable=True
        )

        # Prepare LINE DATA (caller -> callee)
        line_data = []

        for _, row in df_map.iterrows():
            line_data.append({
                "from_lon": row["lon"],
                "from_lat": row["lat"],
                "to_lon": row["lon"] + np.random.uniform(0.01, 0.03),   # simulating callee tower
                "to_lat": row["lat"] + np.random.uniform(0.01, 0.03),
                "caller": row["caller"],
                "callee": row["callee"]
            })

        line_df = pd.DataFrame(line_data)

        # Line layer
        line_layer = pdk.Layer(
            "LineLayer",
            line_df,
            get_source_position=["from_lon", "from_lat"],
            get_target_position=["to_lon", "to_lat"],
            get_color=[0, 255, 0],
            get_width=4,
            pickable=True
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[points_layer, line_layer],
                initial_view_state=view_state,
                tooltip={"text": "Caller: {caller}\nCallee: {callee}"}
            )
        )



    # Graph: Caller Relationships
    st.write("## 🔗 Call Network Graph")

    G = Network(height="600px", width="100%", notebook=False)
    # Build graph only if there are records
    if not df_date.empty:
        callers = df_date["caller"].astype(str)
        callees = df_date["callee"].astype(str)

        for c1, c2 in zip(callers, callees):
            G.add_node(c1, label=c1)
            G.add_node(c2, label=c2)
            G.add_edge(c1, c2)

    G.save_graph("cdr_graph.html")
    st.components.v1.html(open("cdr_graph.html", "r").read(), height=600)
