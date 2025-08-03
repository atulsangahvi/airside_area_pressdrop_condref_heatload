import math
import numpy as np
import streamlit as st
import pandas as pd
from CoolProp.CoolProp import PropsSI, get_global_param_string

st.title("Air-Side + Refrigerant Heat Load Calculator")

# -----------------------------
# Updated Air-Side Pressure Drop (Mass-Flux Method)
# -----------------------------
st.header("Air-Side Coil Parameters")

tube_od_mm = st.number_input("Tube Outer Diameter (mm)", value=9.525)
tube_pitch_mm = st.number_input("Tube to Tube Pitch (mm)", value=25.4)
fin_thickness_mm = st.number_input("Fin Thickness (mm)", value=0.12)
fpi = st.number_input("Fins per Inch (FPI)", value=12, step=1)
num_rows = st.number_input("Number of Tube Rows", value=4, step=1)
face_width_m = st.number_input("Coil Face Width (m)", value=1.0, step=0.0254)
face_height_m = st.number_input("Coil Face Height (m)", value=1.0, step=0.0127)
air_flow_cmh = st.number_input("Air Flow Rate (m³/h)", value=10000, step=50)
air_temp_C = st.number_input("Air Temperature (°C)", value=35.0, step=0.5)

tube_od_m = tube_od_mm / 1000
tube_pitch_m = tube_pitch_mm / 1000
fin_thickness_m = fin_thickness_mm / 1000
fins_per_m = fpi * 39.3701
fin_spacing_m = 1 / fins_per_m
tubes_per_row = math.floor(face_width_m / tube_pitch_m)
tube_blockage_area = tubes_per_row * (math.pi / 4) * tube_od_m**2 * face_height_m
flow_area_per_fin = face_width_m * (fin_spacing_m - fin_thickness_m)
total_open_area = flow_area_per_fin * fins_per_m * face_height_m
A_min = total_open_area - tube_blockage_area

T_K = air_temp_C + 273.15
rho = PropsSI('D', 'T', T_K, 'P', 101325, 'Air')
mu = PropsSI('V', 'T', T_K, 'P', 101325, 'Air')
air_flow_m3s = air_flow_cmh / 3600
m_dot_air = rho * air_flow_m3s
G = m_dot_air / A_min

D_h = 4 * (fin_spacing_m * (tube_pitch_m - tube_od_m)) / (
    2 * (fin_spacing_m + (tube_pitch_m - tube_od_m))
)

Re = G * D_h / mu

Re_data = [300, 500, 800, 1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000]
f_data =  [0.11, 0.08, 0.06, 0.052, 0.043, 0.037, 0.03, 0.025, 0.021, 0.018, 0.015]
f = np.interp(Re, Re_data, f_data)

delta_P = f * (G**2) / (2 * rho)

st.subheader("Air-Side Pressure Drop Results")
st.write(f"**Free Flow Area A_min:** {A_min:.4f} m²")
st.write(f"**Mass Velocity G:** {G:.2f} kg/m²·s")
st.write(f"**Hydraulic Diameter D_h:** {D_h*1000:.2f} mm")
st.write(f"**Reynolds Number:** {Re:.0f}")
st.write(f"**Friction Factor (Interpolated):** {f:.4f}")
st.write(f"**Estimated Pressure Drop:** {delta_P:.2f} Pa")


# -----------------------------
# Refrigerant Heat Load Section
# -----------------------------
st.header("Refrigerant Heat Load Calculator")

fluid_list = get_global_param_string("FluidsList").split(',')
refrigerants = sorted([f for f in fluid_list if f.startswith("R")])
fluid = st.selectbox("Select Refrigerant", refrigerants, index=refrigerants.index("R134a") if "R134a" in refrigerants else 0)

P_cond_bar = st.number_input("Condensing Pressure (bar abs)", value=23.52, min_value=1.0, max_value=35.0, step=0.1)
T_superheat = st.number_input("Inlet Superheated Temp (°C)", value=95.0)
T_subcool = st.number_input("Outlet Subcooled Liquid Temp (°C)", value=52.7)
m_dot = st.number_input("Mass Flow Rate (kg/s)", value=0.599)

P_cond = P_cond_bar * 1e5
T1 = T_superheat + 273.15
T3 = T_subcool + 273.15

try:
    T_sat = PropsSI("T", "P", P_cond, "Q", 0, fluid)
    h1 = PropsSI("H", "P", P_cond, "T", T1, fluid) if T1 > T_sat else PropsSI("H", "P", P_cond, "Q", 1, fluid)
    h2 = PropsSI("H", "P", P_cond, "Q", 1, fluid)
    h3 = PropsSI("H", "P", P_cond, "Q", 0, fluid)
    h4 = PropsSI("H", "P", P_cond, "T", T3, fluid) if T3 < T_sat else h3

    q_sensible = h1 - h2
    q_latent = h2 - h3
    q_subcool = h3 - h4
    Q_sensible = m_dot * q_sensible / 1000
    Q_latent = m_dot * q_latent / 1000
    Q_subcool = m_dot * q_subcool / 1000
    Q_total = Q_sensible + Q_latent + Q_subcool

    st.subheader("Heat Load Results")
    st.write(f"**Saturation Temp (°C):** {T_sat - 273.15:.2f}")
    st.write(f"**h1 (Inlet Superheated):** {h1:.2f} J/kg")
    st.write(f"**h2 (Saturated Vapor):** {h2:.2f} J/kg")
    st.write(f"**h3 (Saturated Liquid):** {h3:.2f} J/kg")
    st.write(f"**h4 (Subcooled Liquid):** {h4:.2f} J/kg")
    st.write(f"**Sensible Cooling:** {Q_sensible:.2f} kW")
    st.write(f"**Latent Condensation:** {Q_latent:.2f} kW")
    st.write(f"**Subcooling:** {Q_subcool:.2f} kW")
    st.write(f"**Total Heat Removed:** {Q_total:.2f} kW")

    if T3 >= T_sat:
        st.warning("Subcooling temperature is higher than or equal to bubble point. No subcooling occurs.")

except Exception as e:
    st.error(f"Calculation error: {e}")
