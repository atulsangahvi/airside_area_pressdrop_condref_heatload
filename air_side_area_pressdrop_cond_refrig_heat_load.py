
import math
import streamlit as st
import pandas as pd
from CoolProp.CoolProp import PropsSI, get_global_param_string

st.title("Air-Side + Refrigerant Heat Load Calculator")

# -----------------------------
# Air-Side Coil Parameters
# -----------------------------
st.header("Air-Side Coil Parameters")

tube_od_mm = st.number_input("Tube Outer Diameter (mm)", value=9.525)
tube_thickness_mm = st.number_input("Tube Wall Thickness (mm)", value=0.35)
row_pitch_mm = st.number_input("Row Pitch (mm)", value=25.4)
tube_pitch_mm = st.number_input("Tube to Tube Pitch (mm)", value=25.4)
fin_thickness_mm = st.number_input("Fin Thickness (mm)", value=0.12)
fpi = st.number_input("Fins per Inch (FPI)", value=12, step=1)
num_rows = st.number_input("Number of Rows", value=4, step=1)
face_width_m = st.number_input("Coil Face Width (m)", value=1.0, step=0.0254)
face_height_m = st.number_input("Coil Face Height (m)", value=1.0, step=0.0127)
air_flow_cmh = st.number_input("Air Flow Rate (m³/h)", value=10000, step=50)
air_temp_C = st.number_input("Air Temperature (°C)", value=35.0, step=0.5)
free_area_percent = st.slider("Free Flow Area (%)", min_value=10, max_value=100, value=25)

# Calculations
tube_od_m = tube_od_mm / 1000
row_pitch_m = row_pitch_mm / 1000
tube_pitch_m = tube_pitch_mm / 1000
fin_thickness_m = fin_thickness_mm / 1000
fins_per_m = fpi * 39.3701
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

net_free_flow_area = frontal_area_m2 * (free_area_percent / 100)
air_flow_m3s = air_flow_cmh / 3600
air_velocity_ms = air_flow_m3s / net_free_flow_area if net_free_flow_area > 0 else 0

T_K = air_temp_C + 273.15
rho = PropsSI('D', 'T', T_K, 'P', 101325, 'Air')
mu = PropsSI('V', 'T', T_K, 'P', 101325, 'Air')

Re = rho * air_velocity_ms * tube_od_m / mu
f = 0.25 * Re ** -0.25 if Re > 0 else 0
dP = (f * num_rows * rho * air_velocity_ms**2) / 2

st.subheader("Air-Side Results")
st.write(f"**Tubes per Row:** {tubes_per_row}")
st.write(f"**Total Tubes:** {total_tubes}")
st.write(f"**Tube External Area:** {tube_ext_area:.4f} m²")
st.write(f"**Net Fin Area:** {net_fin_area:.4f} m²")
st.write(f"**Total Air-Side Area:** {total_air_side_area:.4f} m²")
st.write(f"**Free Flow Area:** {net_free_flow_area:.4f} m²")
st.write(f"**Air Velocity:** {air_velocity_ms:.2f} m/s")
st.write(f"**Air Density:** {rho:.3f} kg/m³")
st.write(f"**Air Viscosity:** {mu:.7f} Pa·s")
st.write(f"**Reynolds Number:** {Re:.2f}")
st.write(f"**Friction Factor:** {f:.4f}")
st.write(f"**Air-side Pressure Drop:** {dP:.2f} Pa")

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
