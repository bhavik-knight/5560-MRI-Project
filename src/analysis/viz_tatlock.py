import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

def generate_tatlock_viz_interactive():
    print("Generating Interactive Tatlock Visualization (Plotly)...")
    
    # 1. Load Data
    try:
        pat_df = pd.read_csv('results/patient_performance.csv')
        mag_df = pd.read_csv('results/magnet_events.csv')
    except FileNotFoundError:
        print("Error: Results files not found. Run batch simulation first.")
        return

    # 2. Aggregate Averages
    avg_reg = pat_df['reg_time'].mean()
    avg_change = pat_df['change_time'].mean()
    avg_iv_prep = pat_df['prep_time'].mean()
    
    mag_metrics = mag_df.groupby('Type')['Duration'].mean().to_dict()
    avg_scan = mag_metrics.get('scan', 0)
    avg_setup = mag_metrics.get('setup', 0)
    avg_flip = mag_metrics.get('flip', 0)
    avg_handover = mag_metrics.get('handover', 0)
    avg_exit = mag_metrics.get('exit', 0)
    
    # 3. Structure Data
    tasks = [
        {'Zone': 'Zone 1: Reception', 'Task': 'Registration', 'Duration': avg_reg},
        {'Zone': 'Zone 2: Prep', 'Task': 'Changing', 'Duration': avg_change},
        {'Zone': 'Zone 2: Prep', 'Task': 'IV / Interview', 'Duration': avg_iv_prep},
        {'Zone': 'Zone 3 & 4: Magnet', 'Task': 'Handover (Hot Seat)', 'Duration': avg_handover},
        {'Zone': 'Zone 3 & 4: Magnet', 'Task': 'Bed Flip / Cleaning', 'Duration': avg_flip},
        {'Zone': 'Zone 3 & 4: Magnet', 'Task': 'Patient Setup', 'Duration': avg_setup},
        {'Zone': 'Zone 3 & 4: Magnet', 'Task': 'Scan Execution', 'Duration': avg_scan},
        {'Zone': 'Zone 3 & 4: Magnet', 'Task': 'Patient Exit', 'Duration': avg_exit},
    ]
    df = pd.DataFrame(tasks)
    
    # 4. Color Mapping (matching previous aesthetics)
    task_colors = {
        'Registration': '#95a5a6',
        'Changing': '#f39c12',
        'IV / Interview': '#e67e22',
        'Handover (Hot Seat)': '#c0392b', 
        'Bed Flip / Cleaning': '#a93226',
        'Patient Setup': '#d35400',
        'Scan Execution': '#2ecc71',
        'Patient Exit': '#8e44ad'
    }

    # 5. Create Plotly Figure with Dropdown (Slicer) logic
    fig = go.Figure()

    # Get list of unique zones
    zones = df['Zone'].unique()

    # Add traces for ALL zones first (Visibility: True for 'All')
    # Actually, let's add specific traces per zone-task to allow granular control?
    # Simpler approach: One bar trace per Task, filtering via buttons? 
    # Or One trace per Zone?? 
    # Best approach for "Slicer": Add a trace for each Zone group. 
    # But we want bars colored by Task. 
    # Plotly Express is easier for this.
    
    fig = px.bar(
        df, 
        x="Duration", 
        y="Task", 
        color="Task", 
        orientation='h',
        color_discrete_map=task_colors,
        text_auto='.1f',
        category_orders={"Task": [t['Task'] for t in tasks]} # Maintain order?
    )
    
    # Update layout to add Dropdown
    # We need to filter the dataframe? Plotly Dropdowns operate on Trace visibility.
    # To make this work with px, we usually use transforms (deprecated) or just standard visibility toggling.
    # Let's rebuild traces manually for clean visibility toggling.
    
    fig = go.Figure()
    
    # We will add data for EACH ZONE as a separate set of traces (or a single trace per zone if checking grouping).
    # Ideally we want the chart to UPDATE data based on selection.
    
    # Strategy: Add ALL data as one trace (default), but that doesn't allow filtering logic easily without JS or Dash.
    # Pure Plotly method: Create a trace for EACH Zone.
    
    # Problem: If I have multiple traces (one for each task color), "Visibility" toggles define which SET of traces is shown.
    # Let's just do: One Trace per Task, but add a custom dimension? No.
    # Let's do: One Trace Group per Zone.
    
    # Actually, simpler: Use `transforms` is allowed but maybe complex.
    # Let's just create different traces for each Zone.
    
    # Group data by Zone
    zone_traces = {}
    
    # We want bars colored by Task. So within each Zone, we might have multiple Tasks.
    # To keep colors correct, we iterate tasks.
    
    # Let's simplify: 
    # Just standard bar chart, but use SEARCH BAR? No.
    # Updatemenus with 'filter' method is not standard. 'update' or 'restyle' is used.
    
    # Let's add ONE trace per Task per Zone? Too many traces.
    # Let's add ONE trace per Zone, but color array? 
    # Yes: One trace per Zone where x=durations, y=tasks, marker_color=[mapped_colors].
    
    for zone in zones:
        z_df = df[df['Zone'] == zone]
        fig.add_trace(go.Bar(
            x=z_df['Duration'],
            y=z_df['Task'],
            orientation='h',
            name=zone,
            marker_color=[task_colors.get(t, 'grey') for t in z_df['Task']],
            text=z_df['Duration'].apply(lambda x: f"{x:.1f} m"),
            textposition='auto',
            visible=True # Initially all visible? Or just first?
        ))

    # Layout Updates
    fig.update_layout(
        title="Average Task Durations by Zone (Switch Zones using Dropdown)",
        xaxis_title="Duration (Minutes)",
        yaxis_title="",
        height=600,
        showlegend=False, # Colors are self-explanatory or we add a dummy legend? Markers handle it.
        margin=dict(l=200) # Space for long labels
    )
    
    # Create Dropdown Buttons
    buttons = []
    
    # Button: "All Zones"
    buttons.append(dict(
        label="All Zones",
        method="update",
        args=[{"visible": [True] * len(zones)},
              {"title": "Average Task Durations - All Zones"}]
    ))
    
    for i, zone in enumerate(zones):
        # Create visibility list: Only the i-th trace is True
        vis = [False] * len(zones)
        vis[i] = True
        
        buttons.append(dict(
            label=zone,
            method="update",
            args=[{"visible": vis},
                  {"title": f"Average Task Durations - {zone}"}]
        ))
    
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=buttons,
                x=1.15,
                y=1,
                xanchor='right',
                yanchor='top'
            )
        ]
    )

    # Save
    os.makedirs('results/plots', exist_ok=True)
    outfile = 'results/plots/task_durations_interactive.html'
    fig.write_html(outfile)
    print(f"Saved {outfile}")

if __name__ == "__main__":
    generate_tatlock_viz_interactive()
