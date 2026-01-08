# 1. IMPORTS
import numpy as np
import pandas as pd

# 2. CONSTANTS
METERS_PER_DEGREE = 111320.0
C = 3e8  # Speed of light (m/s)

# 3. MISSION GEOMETRY
def compute_mission_time(waypoints, speed_mps):
    """Compute total mission time from waypoint path length."""
    total_path_m = 0.0

    for i in range(len(waypoints) - 1):
        p1 = np.array(waypoints[i], dtype=np.float64)
        p2 = np.array(waypoints[i + 1], dtype=np.float64)
        total_path_m += np.linalg.norm(p2 - p1) * METERS_PER_DEGREE

    mission_time_sec = total_path_m / speed_mps
    return mission_time_sec * 1e6  # microseconds

# 4. AIRCRAFT KINEMATICS
def compute_aircraft_state(waypoints, speed_mps, time_us):
    """Return aircraft lat, lon, and heading at given time."""
    time_sec = time_us / 1e6
    dist_moved_m = speed_mps * time_sec

    accum_dist = 0.0
    ac_lat, ac_lon = waypoints[0]
    heading_deg = 0.0

    for i in range(len(waypoints) - 1):
        p1 = np.array(waypoints[i], dtype=np.float64)
        p2 = np.array(waypoints[i + 1], dtype=np.float64)

        seg_dist_m = np.linalg.norm(p2 - p1) * METERS_PER_DEGREE

        if dist_moved_m <= accum_dist + seg_dist_m:
            ratio = (dist_moved_m - accum_dist) / seg_dist_m
            pos = p1 + ratio * (p2 - p1)

            ac_lat, ac_lon = pos[0], pos[1]

            dlat = p2[0] - p1[0]
            dlon = p2[1] - p1[1]
            heading_deg = (np.degrees(np.arctan2(dlon, dlat)) + 360) % 360
            break

        accum_dist += seg_dist_m
    else:
        ac_lat, ac_lon = waypoints[-1]

    return ac_lat, ac_lon, heading_deg


# 5. DOA COMPUTATION (AIRCRAFT-REFERENCED)
def compute_doa(r_lat, r_lon, ac_lat, ac_lon, heading_deg):
    """Compute aircraft-referenced DOA (0–360°)."""
    d_lat = r_lat - ac_lat
    d_lon = r_lon - ac_lon

    bearing_deg = (np.degrees(np.arctan2(d_lon, d_lat)) + 360) % 360
    return (bearing_deg - heading_deg + 360) % 360


# 6. FREQUENCY LOGIC
def compute_frequency(cfg, pulse_index, radar_id):
    base_f = cfg.get("freq", 1000.0)
    f_type = cfg.get("f_type", "Fixed")
    f_range = cfg.get("f_range", 0.0)
    f_batch = cfg.get("f_batch", 5)

    if f_type == "Fixed":
        return base_f
    elif f_type == "Agile":
        return base_f + np.random.uniform(-f_range, f_range)
    elif f_type == "Pulse-to-Pulse":
        return np.random.uniform(1000, 18000)
    elif f_type == "Batch-to-Batch":
        batch_num = pulse_index // f_batch
        np.random.seed(radar_id + batch_num)
        return base_f + np.random.uniform(-f_range, f_range)

    return base_f

# 7. PRI LOGIC
def compute_pri(cfg, pulse_index):
    p_levels = cfg.get("pri_levels", [100.0])
    p_type = cfg.get("p_type", "Fixed")
    p_batch = cfg.get("p_batch", 5)
    p_jitter_pc = cfg.get("p_jitter_pc", 10.0)

    if p_type == "Fixed":
        return p_levels[0]
    elif p_type == "Staggered":
        return p_levels[pulse_index % len(p_levels)]
    elif p_type == "Switcher":
        batch_index = (pulse_index // p_batch) % len(p_levels)
        return p_levels[batch_index]
    elif p_type == "Jitter":
        center = p_levels[0]
        margin = center * (p_jitter_pc / 100.0)
        return center + np.random.uniform(-margin, margin)

    return p_levels[0]

# 8. ES AMPLITUDE (ONE-WAY RADAR EQUATION)
def compute_amplitude(cfg, freq_mhz, r_lat, r_lon, ac_lat, ac_lon):
    pt_w = cfg.get("pt_w", 10000.0)

    Gt = 10 ** (30 / 10)
    Gr = 10 ** (30 / 10)
    L = 1.0

    delta_lat_m = (r_lat - ac_lat) * METERS_PER_DEGREE
    delta_lon_m = (r_lon - ac_lon) * METERS_PER_DEGREE
    R = np.sqrt(delta_lat_m**2 + delta_lon_m**2)

    freq_hz = freq_mhz * 1e6
    wavelength = C / freq_hz

    return (np.sqrt(pt_w * Gt * Gr) * wavelength) / (4 * np.pi * R * np.sqrt(L))

# 9. MAIN GENERATOR
def generate_es_stream(configs, waypoints, speed_mps):
    all_pulses = []

    mission_time_us = compute_mission_time(waypoints, speed_mps)

    for radar_id, cfg in enumerate(configs):
        r_lat, r_lon = cfg.get("lat", 0.0), cfg.get("lon", 0.0)
        pw_val = cfg.get("pw", 10.0)

        current_time_us = 0.0
        pulse_index = 0

        while current_time_us <= mission_time_us:
            ac_lat, ac_lon, heading_deg = compute_aircraft_state(
                waypoints, speed_mps, current_time_us
            )

            doa_deg = compute_doa(r_lat, r_lon, ac_lat, ac_lon, heading_deg)

            freq = compute_frequency(cfg, pulse_index, radar_id)
            pri = compute_pri(cfg, pulse_index)

            amplitude = compute_amplitude(
                cfg, freq, r_lat, r_lon, ac_lat, ac_lon
            )

            all_pulses.append({
                "Emitter_ID": f"Radar_{radar_id}",
                "TOA_us": round(current_time_us, 3),
                "Freq_MHz": round(freq, 2),
                "PW_us": round(pw_val, 2),
                "Amplitude": amplitude,
                "AC_Lat": round(ac_lat, 8),
                "AC_Lon": round(ac_lon, 8),
                "DOA_deg": round(doa_deg, 6),
            })

            current_time_us += pri
            pulse_index += 1

    return pd.DataFrame(all_pulses).sort_values(by="TOA_us").reset_index(drop=True)