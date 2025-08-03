
import math
import streamlit as st
import pandas as pd
try:
    from CoolProp.CoolProp import PropsSI
    coolprop_available = True
except ImportError:
    coolprop_available = False

def air_properties_lookup(T_C):
    T_table = [0, 10, 20, 30, 40, 50, 60]
    mu_table = [1.71e-5, 1.75e-5, 1.81e-5, 1.87e-5, 1.92e-5, 1.98e-5, 2.03e-5]
    rho_table = [1.293, 1.247, 1.204, 1.165, 1.127, 1.093, 1.060]
    T_C = max(0, min(60, T_C))
    for i in range(len(T_table)-1):
        if T_table[i] <= T_C <= T_table[i+1]:
            frac = (T_C - T_table[i]) / (T_table[i+1] - T_table[i])
            mu = mu_table[i] + frac * (mu_table[i+1] - mu_table[i])
            rho = rho_table[i] + frac * (rho_table[i+1] - rho_table[i])
            return rho, mu
    return rho_table[-1], mu_table[-1]

def calculate_air_side_results(tube_od_mm, tube_pitch_mm, row_pitch_mm, fin_thickness_mm, fpi, num_rows, face_width_m, face_height_m, air_flow_cmh, air_temp_C, free_flow_percent):
    tube_od_m = tube_od_mm / 1000
    tube_pitch_m = tube_pitch_mm / 1000
    row_pitch_m = row_pitch_mm / 1000
    fin_thickness_m = fin_thickness_mm / 1000
    fins_per_m = fpi * 39.3701
    fin_spacing_m = 1 / fins_per_m
    frontal_area_m2 = face_width_m * face_height_m
    fin_depth_m = num_rows * row_pitch_m
    tubes_per_row = math.floor(face_width_m / tube_pitch_m)
    total_tubes = tubes_per_row * num_rows
    tube_ext_area = total_tubes * (math.pi * tube_od_m)
    fin_area_per_fin = 2 * face_width_m * fin_depth_m
    total_gross_fin_area = fin_area_per_fin * fins_per_m
    hole_area_per_tube = (math.pi / 4) * tube_od_m**2
    total_hole_area = hole_area_per_tube * total_tubes * fins_per_m
    net_fin_area = total_gross_fin_area - total_hole_area
    total_air_side_area = (tube_ext_area + net_fin_area) * face_height_m
    face_velocity = (air_flow_cmh / 3600) / frontal_area_m2

    if coolprop_available:
        T_K = air_temp_C + 273.15
        rho = PropsSI('D', 'T', T_K, 'P', 101325, 'Air')
        mu = PropsSI('V', 'T', T_K, 'P', 101325, 'Air')
        if mu <= 0 or math.isnan(mu):
            rho, mu = air_properties_lookup(air_temp_C)
    else:
        rho, mu = air_properties_lookup(air_temp_C)

    air_flow_m3s = air_flow_cmh / 3600
    m_dot = rho * air_flow_m3s
    free_flow_area = frontal_area_m2 * (free_flow_percent / 100)
    G = m_dot / free_flow_area
    u_max = face_velocity * tube_pitch_m / (tube_pitch_m - tube_od_m) if (tube_pitch_m - tube_od_m) > 0 else 0
    Re = (rho * u_max * tube_od_m) / mu if mu > 0 else 0

    passage_height = tube_pitch_m - tube_od_m
    passage_width = fin_spacing_m - fin_thickness_m
    A_min_cell = passage_height * passage_width
    P_wet_cell = 2 * (passage_height + passage_width)
    D_h = (4 * A_min_cell) / P_wet_cell if P_wet_cell > 0 else 0

    f = 0.03
    flow_depth = num_rows * row_pitch_m
    dP = f * (flow_depth / D_h) * (G**2) / (2 * rho) if D_h > 0 else 0

    return {
        "Tubes per row": tubes_per_row,
        "Total tubes": total_tubes,
        "Fin depth (m)": fin_depth_m,
        "Tube external area (m²)": tube_ext_area,
        "Net fin area (m²)": net_fin_area,
        "Total air side area (m²)": total_air_side_area,
        "Free flow area (m²)": free_flow_area,
        "Free flow area (%)": free_flow_percent,
        "Face velocity (m/s)": face_velocity,
        "Max velocity between tubes (m/s)": u_max,
        "Tube Pitch (m)": tube_pitch_m,
        "Tube OD (m)": tube_od_m,
        "Air density (kg/m³)": rho,
        "Air viscosity (Pa·s)": mu,
        "Hydraulic diameter (m)": D_h,
        "Mass flow rate (kg/s)": m_dot,
        "Mass flux (kg/m²·s)": G,
        "Reynolds number (OD-based)": Re,
        "Friction factor": f,
        "Air-side Pressure Drop (Pa)": dP
    }

st.title("Air-Side and Refrigerant Heat Load Calculator")

st.sidebar.header("Air-Side Parameters")
tube_od_mm = st.sidebar.number_input("Tube Outer Diameter (mm)", value=9.525)
tube_pitch_mm = st.sidebar.number_input("Tube Pitch (mm)", value=25.4)
row_pitch_mm = st.sidebar.number_input("Row Pitch (mm)", value=25.4)
fin_thickness_mm = st.sidebar.number_input("Fin Thickness (mm)", value=0.12)
fpi = st.sidebar.number_input("Fins Per Inch (FPI)", value=12)
num_rows = st.sidebar.number_input("Number of Rows", value=4)
face_width_m = st.sidebar.number_input("Coil Face Width (m)", value=1.0)
face_height_m = st.sidebar.number_input("Coil Face Height (m)", value=1.0)
air_flow_cmh = st.sidebar.number_input("Air Flow Rate (m³/h)", value=10000)
air_temp_C = st.sidebar.number_input("Air Temperature (°C)", value=35.0)
free_flow_percent = st.sidebar.slider("Free Flow Area (%)", min_value=10, max_value=100, value=25)

if st.sidebar.button("Calculate Air-Side"):
    results = calculate_air_side_results(
        tube_od_mm, tube_pitch_mm, row_pitch_mm,
        fin_thickness_mm, fpi, num_rows,
        face_width_m, face_height_m,
        air_flow_cmh, air_temp_C, free_flow_percent
    )
    df = pd.DataFrame(list(results.items()), columns=["Parameter", "Value"])
    df["Value"] = df["Value"].apply(lambda x: f"{x:.6f}" if isinstance(x, float) else x)
    st.subheader("Air-Side Calculation Results")
    st.table(df)

st.sidebar.header("Refrigerant Heat Load Inputs")
fluid = st.sidebar.selectbox("Select Refrigerant", ["R134a", "R407C"])
P_cond_bar = st.sidebar.number_input("Condensing Pressure (bar abs)", value=23.52)
T_superheat = st.sidebar.number_input("Inlet Superheated Temp (°C)", value=95.0)
T_subcool = st.sidebar.number_input("Outlet Subcooled Liquid Temp (°C)", value=52.7)
m_dot_ref = st.sidebar.number_input("Refrigerant Mass Flow Rate (kg/s)", value=0.599)

if st.sidebar.button("Calculate Heat Load"):
    try:
        P_cond = P_cond_bar * 1e5
        T1 = T_superheat + 273.15
        T3 = T_subcool + 273.15
        T_sat = PropsSI("T", "P", P_cond, "Q", 0, fluid)
        h1 = PropsSI("H", "P", P_cond, "T", T1, fluid) if T1 > T_sat else PropsSI("H", "P", P_cond, "Q", 1, fluid)
        h2 = PropsSI("H", "P", P_cond, "Q", 1, fluid)
        h3 = PropsSI("H", "P", P_cond, "Q", 0, fluid)
        h4 = PropsSI("H", "P", P_cond, "T", T3, fluid) if T3 < T_sat else h3
        Q_sensible = m_dot_ref * (h1 - h2) / 1000
        Q_latent = m_dot_ref * (h2 - h3) / 1000
        Q_subcool = m_dot_ref * (h3 - h4) / 1000
        Q_total = Q_sensible + Q_latent + Q_subcool
        st.subheader("Refrigerant Heat Load Results")
        st.write(f"**Desuperheating:** {Q_sensible:.2f} kW")
        st.write(f"**Condensing:** {Q_latent:.2f} kW")
        st.write(f"**Subcooling:** {Q_subcool:.2f} kW")
        st.write(f"**Total Heat Removed:** {Q_total:.2f} kW")
    except Exception as e:
        st.error(f"Calculation error: {e}")



import math
import streamlit as st
import pandas as pd
try:
    from CoolProp.CoolProp import PropsSI
    coolprop_available = True
except ImportError:
    coolprop_available = False

def air_properties_lookup(T_C):
    T_table = [0, 10, 20, 30, 40, 50, 60]
    mu_table = [1.71e-5, 1.75e-5, 1.81e-5, 1.87e-5, 1.92e-5, 1.98e-5, 2.03e-5]
    rho_table = [1.293, 1.247, 1.204, 1.165, 1.127, 1.093, 1.060]
    T_C = max(0, min(60, T_C))
    for i in range(len(T_table)-1):
        if T_table[i] <= T_C <= T_table[i+1]:
            frac = (T_C - T_table[i]) / (T_table[i+1] - T_table[i])
            mu = mu_table[i] + frac * (mu_table[i+1] - mu_table[i])
            rho = rho_table[i] + frac * (rho_table[i+1] - rho_table[i])
            return rho, mu
    return rho_table[-1], mu_table[-1]

def safe_props(fluid, P, T=None, Q=None):
    try:
        if T is not None:
            return PropsSI("H", "P", P, "T", T, fluid)
        elif Q is not None:
            return PropsSI("H", "P", P, "Q", Q, fluid)
    except:
        return None

st.title("Air-Side and Refrigerant Heat Load Calculator")

st.sidebar.header("Refrigerant Heat Load Inputs")
fluid = st.sidebar.selectbox("Select Refrigerant", ["R134a", "R407C"])
P_cond_bar = st.sidebar.number_input("Condensing Pressure (bar abs)", value=23.52)
T_superheat = st.sidebar.number_input("Inlet Superheated Temp (°C)", value=95.0)
T_subcool = st.sidebar.number_input("Outlet Subcooled Liquid Temp (°C)", value=52.7)
m_dot_ref = st.sidebar.number_input("Refrigerant Mass Flow Rate (kg/s)", value=0.599)

if st.sidebar.button("Calculate Heat Load"):
    try:
        P_cond = P_cond_bar * 1e5
        T1 = T_superheat + 273.15
        T3 = T_subcool + 273.15

        T_bubble, T_dew = None, None
        try:
            T_bubble = PropsSI("T", "P", P_cond, "Q", 0, fluid)
            T_dew = PropsSI("T", "P", P_cond, "Q", 1, fluid)
        except:
            pass

        h1 = safe_props(fluid, P_cond, T=T1) if (T_bubble and T1 > T_bubble) else safe_props(fluid, P_cond, Q=1)
        h2 = safe_props(fluid, P_cond, Q=1)
        h3 = safe_props(fluid, P_cond, Q=0)
        h4 = safe_props(fluid, P_cond, T=T3) if (T_bubble and T3 < T_bubble) else h3

        if None in [h1, h2, h3, h4]:
            raise ValueError("One or more enthalpy values could not be retrieved for the selected fluid.")

        Q_sensible = m_dot_ref * (h1 - h2) / 1000
        Q_latent = m_dot_ref * (h2 - h3) / 1000
        Q_subcool = m_dot_ref * (h3 - h4) / 1000
        Q_total = Q_sensible + Q_latent + Q_subcool

        st.subheader("Refrigerant Heat Load Results")
        st.write(f"**Desuperheating:** {Q_sensible:.2f} kW")
        st.write(f"**Condensing:** {Q_latent:.2f} kW")
        st.write(f"**Subcooling:** {Q_subcool:.2f} kW")
        st.write(f"**Total Heat Removed:** {Q_total:.2f} kW")
    except Exception as e:
        st.error(f"Calculation error: {e}")
