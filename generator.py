#1.IMPORTS
import numpy as np
import pandas as pd

def generate_es_stream(configs, waypoints, speed_mps):
    #2. INITIALIZE VARIABLES
    all_pulses = []
    METERS_PER_DEGREE = 111320.0 # 1 degree of latitude is approximately 111,320 meters

    #3. COMPUTE TOTAL MISSION TIME FROM WAYPOINTS
    #Compute Flight Distance (sum of segments between waypoints)
    #Compute Total Mission Time

    total_path_m = 0.0
    for i in range(len(waypoints) - 1):
        p1 = np.array(waypoints[i], dtype=np.float64)
        p2 = np.array(waypoints[i + 1], dtype=np.float64)
        total_path_m += np.linalg.norm(p2 - p1) * METERS_PER_DEGREE

    mission_time_sec = total_path_m / speed_mps
    mission_time_us = mission_time_sec * 1e6

    #4. GENERATE PULSES FOR EACH RADAR (For the entire duration of flight)
    for radar_id, cfg in enumerate(configs):

        #5. Radar Parameters Extraction
        r_lat, r_lon = cfg.get("lat", 0.0), cfg.get("lon", 0.0)

        base_f = cfg.get("freq", 1000.0)
        f_type = cfg.get("f_type", "Fixed")
        f_range = cfg.get("f_range", 0.0)
        f_batch = cfg.get("f_batch", 5)

        p_levels = cfg.get("pri_levels", [100.0])
        p_type = cfg.get("p_type", "Fixed")
        p_batch = cfg.get("p_batch", 5)
        p_jitter_pc = cfg.get("p_jitter_pc", 10.0)

        pw_val = cfg.get("pw", 10.0)

        #6.Radar-local clock initialization
        current_time_us = 0.0
        pulse_index = 0

        #7.Pulse Generation Loop
        while current_time_us <= mission_time_us:

            #8.AIRCRAFT KINEMATICS
            time_sec = current_time_us / 1e6
            dist_moved_m = speed_mps * time_sec

            #8.1 Initial Assumptions
            accum_dist = 0.0
            ac_lat, ac_lon = waypoints[0]
            heading_deg = 0.0

            #8.2 Determine Current Aircraft Position Along Waypoints
            for j in range(len(waypoints) - 1):
                p1 = np.array(waypoints[j], dtype=np.float64)
                p2 = np.array(waypoints[j + 1], dtype=np.float64)

                seg_dist_m = np.linalg.norm(p2 - p1) * METERS_PER_DEGREE

                if dist_moved_m <= accum_dist + seg_dist_m:
                    ratio = (dist_moved_m - accum_dist) / seg_dist_m
                    current_pos = p1 + ratio * (p2 - p1)

                    ac_lat, ac_lon = current_pos[0], current_pos[1]

                    #8.3 Aircraft heading (direction of motion)
                    dlat = p2[0] - p1[0]
                    dlon = p2[1] - p1[1]
                    heading_deg = (np.degrees(np.arctan2(dlon, dlat)) + 360) % 360
                    break

                accum_dist += seg_dist_m
            else:
                ac_lat, ac_lon = waypoints[-1]

            # 9.4 AIRCRAFT-REFERENCED DOA (0–360 deg)
            d_lat = r_lat - ac_lat
            d_lon = r_lon - ac_lon

            bearing_deg = (np.degrees(np.arctan2(d_lon, d_lat)) + 360) % 360
            doa_deg = (bearing_deg - heading_deg + 360) % 360

            # FREQUENCY LOGIC
            if f_type == "Fixed":
                freq = base_f
            elif f_type == "Agile":
                freq = base_f + np.random.uniform(-f_range, f_range)
            elif f_type == "Pulse-to-Pulse":
                freq = np.random.uniform(1000, 18000)
            elif f_type == "Batch-to-Batch":
                batch_num = pulse_index // f_batch
                np.random.seed(radar_id + batch_num)
                freq = base_f + np.random.uniform(-f_range, f_range)
            else:
                freq = base_f

            # PRI LOGIC
            if p_type == "Fixed":
                pri = p_levels[0]
            elif p_type == "Staggered":
                pri = p_levels[pulse_index % len(p_levels)]
            elif p_type == "Switcher":
                batch_index = (pulse_index // p_batch) % len(p_levels)
                pri = p_levels[batch_index]
            elif p_type == "Jitter":
                center_pri = p_levels[0]
                margin = center_pri * (p_jitter_pc / 100.0)
                pri = center_pri + np.random.uniform(-margin, margin)
            else:
                pri = p_levels[0]

            # AMPLITUDE (placeholder)
            amp = 1.0

            # PDW
            all_pulses.append({
                "Emitter_ID": f"Radar_{radar_id}",
                "TOA_us": round(current_time_us, 3),
                "Freq_MHz": round(freq, 2),
                "PW_us": round(pw_val, 2),
                "Amplitude": round(amp, 4),
                "AC_Lat": round(ac_lat, 8),
                "AC_Lon": round(ac_lon, 8),
                "DOA_deg": round(doa_deg, 6),
            })

            current_time_us += pri
            pulse_index += 1

    # 10. RECEIVER INTERLEAVES ALL PULSES BY TIME
    df = pd.DataFrame(all_pulses).sort_values(by="TOA_us").reset_index(drop=True)
    return df
