#1.IMPORTS
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from generator import generate_es_stream

#2.Page Configuration 
st.set_page_config(page_title="Radar ES Simulator", layout="wide")
st.title("🛡️ Radar ES Signal Simulator")

# 3.Aircraft Kinematics Inputs(Sidebar)
st.sidebar.header("✈️ Aircraft Kinematics")

ac_speed_mach = st.sidebar.number_input(
    "Aircraft Speed (Mach)",
    min_value=0.1,
    max_value=10.0,
    value=2.0
)
speed_mps = ac_speed_mach * 340.3

# 4.Waypoints (Definition)
num_waypoints = st.sidebar.slider("Number of Waypoints", 1, 32, 3)

default_waypoints = [
    (12.0000, 77.0000),
    (12.0000, 77.2000),
    (12.2000, 77.2000),
]

waypoints = []

#4.1 Waypoint Inputs
with st.sidebar.expander("📍 Define Waypoints", expanded=True):
    for i in range(num_waypoints):
        col_lat, col_lon = st.columns(2)
        w_lat = col_lat.number_input(
            "Lat",
            value=default_waypoints[i][0] if i < len(default_waypoints) else 12.0,
            key=f"wlat_{i}",
            format="%.4f",
        )
        w_lon = col_lon.number_input(
            "Lon",
            value=default_waypoints[i][1] if i < len(default_waypoints) else 77.0,
            key=f"wlon_{i}",
            format="%.4f",
        )
        waypoints.append((w_lat, w_lon))

# 5.Radar emitter Initialization (Default : 2 Radars) -->
if "emitter_configs" not in st.session_state:
    st.session_state.emitter_configs = [
        {
            "id": 0,
            "freq": 3000.0,
            "f_type": "Fixed",
            "f_range": 0.0,
            "f_batch": 5,
            "pri_levels": "50000",
            "p_type": "Fixed",
            "pw": 10.0,
            "scan": "Constant",
            "lat": 12.0500,
            "lon": 77.3500,
        },
        {
            "id": 1,
            "freq": 9000.0,
            "f_type": "Fixed",
            "f_range": 0.0,
            "f_batch": 5,
            "pri_levels": "50000",
            "p_type": "Fixed",
            "pw": 8.0,
            "scan": "Constant",
            "lat": 12.3500,
            "lon": 77.2000,
        },
    ]

#6.Add Emitter Function 
def add_emitter():
    new_id = max(cfg["id"] for cfg in st.session_state.emitter_configs) + 1
    st.session_state.emitter_configs.append(
        {
            "id": new_id,
            "freq": 4000.0,
            "f_type": "Fixed",
            "f_range": 0.0,
            "f_batch": 5,
            "pri_levels": "50000",
            "p_type": "Fixed",
            "pw": 10.0,
            "scan": "Constant",
            "lat": 12.0,
            "lon": 77.0,
        }
    )

#7.Emitter Management
st.sidebar.divider()
st.sidebar.button("➕ Add New Emitter", on_click=add_emitter, width="stretch")

#8.Processed configuration controller
processed_configs = []

#9.Emitter Configuration UI
for i, cfg in enumerate(st.session_state.emitter_configs):
    uid = cfg["id"]
    with st.expander(f"📡 Emitter {i+1} Configuration", expanded=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 0.5])

        #9.1 Frequency
        with col1:
            f_type = st.selectbox(
                "Frequency Mode",
                ["Fixed", "Agile", "Pulse-to-Pulse", "Batch-to-Batch"],
                index=["Fixed", "Agile", "Pulse-to-Pulse", "Batch-to-Batch"].index(cfg["f_type"]),
                key=f"f_type_{uid}",
            )
            f_val = st.number_input(
                "Base Frequency (MHz)", 1000.0, 18000.0, cfg["freq"], key=f"f_val_{uid}"
            )
            f_range = cfg.get("f_range", 0.0)
            f_batch = cfg.get("f_batch", 5)
        
        #9.2 PRI
        with col2:
            p_type = st.selectbox(
                "PRI Mode",
                ["Fixed", "Staggered", "Switcher", "Jitter"],
                index=["Fixed", "Staggered", "Switcher", "Jitter"].index(cfg["p_type"]),
                key=f"p_type_{uid}",
            )

            p_input = st.text_input(
                "PRI Levels (μs)",
                cfg["pri_levels"],
                key=f"pri_{uid}"
            )

            # Additional PRI Controls
            p_batch = cfg.get("p_batch", 5)
            p_jitter_pc = cfg.get("p_jitter_pc", 10.0)

            if p_type == "Switcher":
                p_batch = st.number_input(
                    "PRI Batch Size (pulses)",
                    min_value=1,
                    max_value=1000,
                    value=p_batch,
                    key=f"p_batch_{uid}"
                )

            if p_type == "Jitter":
                p_jitter_pc = st.number_input(
                    "Jitter Range (%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=p_jitter_pc,
                    step=1.0,
                    key=f"p_jitter_{uid}"
                )

        #9.3 Pulse Width + Scan Type
        with col3:
            pw_val = st.number_input("PW (μs)", 0.1, 1000.0, cfg["pw"], key=f"pw_{uid}")
            scan = st.selectbox(
                "Scan Type",
                ["Circular", "Sector", "Constant", "Lock-on", "Conical"],
                index=["Circular", "Sector", "Constant", "Lock-on", "Conical"].index(cfg["scan"]),
                key=f"scan_{uid}",
            )
        
        #9.4 Radar Position
        with col4:
            lat = st.number_input("Radar Lat", -90.0, 90.0, cfg["lat"], format="%.4f", key=f"lat_{uid}")
            lon = st.number_input("Radar Lon", -180.0, 180.0, cfg["lon"], format="%.4f", key=f"lon_{uid}")
        
        #9.5 Remove Emitter Button
        with col5:
            if st.button("🗑️", key=f"rem_{uid}", width="stretch"):
                if len(st.session_state.emitter_configs) > 1:
                    st.session_state.emitter_configs = [
                        c for c in st.session_state.emitter_configs if c["id"] != uid
                    ]
                    st.rerun()
        
        #9.6 PRI Parsing + Config assembly
        try:
            pri_list = [float(x.strip()) for x in p_input.split(",")]
        except ValueError:
            pri_list = [50000.0]

        processed_configs.append(
            {
                "freq": f_val,
                "f_type": f_type,
                "f_range": f_range,
                "f_batch": f_batch,
                "pri_levels": pri_list,
                "p_type": p_type,
                "p_batch": p_batch,          # ✅ NEW
                "p_jitter_pc": p_jitter_pc,  # ✅ NEW
                "pw": pw_val,
                "scan": scan,
                "lat": lat,
                "lon": lon,
            }
        )


#10.Run Simulation
if st.button("🚀 Start Mission Simulation", width="stretch"):
    st.session_state.df = generate_es_stream(
        processed_configs,
        waypoints=waypoints,
        speed_mps=speed_mps,
    )
    st.session_state.generated = True

#11.Display Results
if "generated" in st.session_state and st.session_state.generated:
    df = st.session_state.df

    st.subheader("📋 Captured PDW Stream")
    st.dataframe(df, width="stretch")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Mission CSV",
        data=csv,
        file_name="radar_mission_data.csv",
        mime="text/csv",
        width="stretch",
    )

    # 11.1 Visualization
    st.divider()
    st.subheader("🗺️ Aircraft Path, Radar Locations & Signal Reception Points")

    fig, ax = plt.subplots(figsize=(10, 8))

    wp_lats, wp_lons = zip(*waypoints)
    ax.plot(wp_lons, wp_lats, "--", color="black", linewidth=2, label="Flight Path")

    radar_colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]

    for idx in range(len(processed_configs)):
        radar_id = f"Radar_{idx}"
        sub = df[df["Emitter_ID"] == radar_id]
        ax.scatter(
            sub["AC_Lon"],
            sub["AC_Lat"],
            s=30,
            alpha=0.7,
            color=radar_colors[idx % len(radar_colors)],
            label=f"{radar_id} Pulses",
        )

    for idx, cfg in enumerate(processed_configs):
        ax.scatter(
            cfg["lon"],
            cfg["lat"],
            marker="^",
            s=220,
            color=radar_colors[idx % len(radar_colors)],
            edgecolor="black",
            label=f"Radar {idx} Location",
        )

    METERS_PER_DEGREE = 111320.0
    for i in range(len(waypoints) - 1):
        lat1, lon1 = waypoints[i]
        lat2, lon2 = waypoints[i + 1]

        dist_m = np.linalg.norm(
            np.array([lat2 - lat1, lon2 - lon1])
        ) * METERS_PER_DEGREE
        dist_km = dist_m / 1000.0

        ax.text(
            (lon1 + lon2) / 2,
            (lat1 + lat2) / 2,
            f"{dist_km:.1f} km",
            fontsize=9,
            ha="center",
            va="center",
            bbox=dict(facecolor="white", alpha=0.6),
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Aircraft Path, Radar Locations & Signal Reception Points")
    ax.grid(True, linestyle=":")
    ax.legend(loc="upper right")

    st.pyplot(fig)