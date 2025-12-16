
import streamlit as st
import pandas as pd
import plotly.express as px
from src.engine import MRISimulation

# Page Config
st.set_page_config(page_title="MRI Efficiency Digital Twin (Modular)", layout="wide")

st.title("MRI Department Digital Twin [Modular]")
st.markdown("""
This dashboard simulates the workflow of an MRI suite using the **modular architecture**.
Compare **Current State (Serial)** vs **Future State (Parallel Workflows)**.
""")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Simulation Parameters")

staff_count = st.sidebar.slider("Staff Count (Techs + Porters)", min_value=3, max_value=6, value=4)
bed_flip_time = st.sidebar.slider("Bed Flip Time (KB Cleaning) [min]", min_value=1.0, max_value=10.0, value=5.0)
parallel_mode = st.sidebar.checkbox("Enable Parallel Processing (Future State)", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("**Scenario Description**")
if parallel_mode:
    st.sidebar.success("✅ **Future State (Parallel)**: \n\nPatient prep happens in Zone 2. Magnet focuses on scanning.")
else:
    st.sidebar.warning("⚠️ **Current State (Serial)**: \n\nPatient prep happens *inside* the MRI room.")

# --- RUN SIMULATION ---
if st.button("Run Simulation", type="primary"):
    with st.spinner("Simulating 12-hour shift..."):
        # Instantiate Engine with dynamic parameters
        sim = MRISimulation(
            simulation_hours=12,
            parallel_mode=parallel_mode,
            staff_count=staff_count,
            bed_flip_time=bed_flip_time
        )
        
        results = sim.run()
        
    patient_logs = pd.DataFrame(results['patient_logs'])
    spatial_df = results['spatial_data']

    if patient_logs.empty:
        st.error("No patients processed!")
    else:
        # --- METRICS CALCULATION ---
        throughput = len(patient_logs) # Total processed (or started?)
        # Let's count 'exit_time' not null for completed throughput
        completed = patient_logs[patient_logs['exit_time'].notna()]
        throughput_val = len(completed)
        
        # Idle Time Calculation
        # Same logic as analysis.py
        def calc_busy(row):
            if row['scenario'] == 'Serial':
                if pd.notnull(row['prep_start']) and pd.notnull(row['exit_time']):
                    return row['exit_time'] - row['prep_start']
            else:
                if pd.notnull(row['scan_start']) and pd.notnull(row['exit_time']):
                     return row['exit_time'] - row['scan_start']
            return 0.0

        patient_logs['Busy_Duration'] = patient_logs.apply(calc_busy, axis=1)
        total_busy = patient_logs['Busy_Duration'].sum()
        total_time = 12 * 60
        util_pct = (total_busy / total_time) * 100
        idle_pct = 100 - util_pct
        
        # --- KPI METRICS ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Throughput (Patients)", throughput_val)
        col2.metric("Magnet Busy % (Value Added)", f"{util_pct:.1f}%")
        col3.metric("Magnet Idle %", f"{idle_pct:.1f}%", delta_color="inverse")

        # --- GANTT CHART ---
        st.subheader("Resource Utilization Timeline (Magnet)")
        
        # Prepare Gantt Data
        gantt_rows = []
        for _, row in patient_logs.iterrows():
            scenario = row['scenario']
            p_id = row['p_id']
            
            # Prep (Serial only shows as 'task' on magnet, Parallel prep is off-magnet)
            if scenario == 'Serial' and pd.notnull(row['prep_start']) and pd.notnull(row['scan_start']):
                gantt_rows.append({
                    'Start': row['prep_start'],
                    'Finish': row['scan_start'],
                    'Task': 'Prep (Idle)',
                    'Patient': f"P{p_id}"
                })
            
            # Scan + Flip
            if pd.notnull(row['scan_start']) and pd.notnull(row['exit_time']):
                gantt_rows.append({
                    'Start': row['scan_start'],
                    'Finish': row['exit_time'],
                    'Task': 'Scan + Flip',
                    'Patient': f"P{p_id}"
                })
                
        if gantt_rows:
            df_gantt = pd.DataFrame(gantt_rows)
            # Fake date for Plotly Timeline
            base_date = pd.Timestamp("2025-01-01 07:00")
            df_gantt['Start_Time'] = base_date + pd.to_timedelta(df_gantt['Start'], unit='m')
            df_gantt['Finish_Time'] = base_date + pd.to_timedelta(df_gantt['Finish'], unit='m')
            
            fig_gantt = px.timeline(
                df_gantt, 
                x_start="Start_Time", 
                x_end="Finish_Time", 
                y="Task", 
                color="Task",
                hover_data=['Patient'],
                color_discrete_map={'Prep (Idle)': 'red', 'Scan + Flip': 'green'},
                height=300
            )
            fig_gantt.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_gantt, use_container_width=True)
            
        # --- DIGITAL TWIN ANIMATION ---
        st.subheader("Spatial Digital Twin (Zone Flow)")
        if not spatial_df.empty:
            # Map State Colors
            state_colors = {
                'Arrived/Waiting': '#FF4B4B', # Red
                'Prepping': '#FFA15A',        # Orange
                'Changed': '#FFA15A', 
                'Scanning': '#00CC96',        # Green
                'Done': '#636EFA'             # Blue
            }
            
            fig_anim = px.scatter(
                spatial_df, 
                x="X", 
                y="Y", 
                animation_frame="Minute", 
                animation_group="Patient_ID",
                color="State",
                color_discrete_map=state_colors,
                hover_name="State",
                range_x=[-0.5, 3.5],
                range_y=[0, 5],
                title="Patient Flow Animation (1 min steps)",
                height=600
            )
            
            fig_anim.update_layout(
                xaxis=dict(
                    tickmode='array',
                    tickvals=[0, 1, 2, 3],
                    ticktext=['Zone 1', 'Zone 2', 'Zone 4', 'Exit']
                ),
                yaxis=dict(showticklabels=False),
                showlegend=True
            )
            
            # Simple Shapes
            fig_anim.add_vrect(x0=-0.5, x1=0.5, fillcolor="red", opacity=0.1, annotation_text="Wait")
            fig_anim.add_vrect(x0=0.5, x1=1.5, fillcolor="orange", opacity=0.1, annotation_text="Prep")
            fig_anim.add_vrect(x0=1.5, x1=2.5, fillcolor="green", opacity=0.1, annotation_text="Scan")
            
            st.plotly_chart(fig_anim, use_container_width=True)
