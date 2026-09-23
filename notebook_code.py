import numpy as np
import pandas as pd
import xarray as xr
import bokeh.io
from bokeh.io import output_notebook, show
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, CustomJS, Div, RangeSlider
from bokeh.plotting import figure
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import datetime
from run_opendrift import run_opendrift
import matplotlib.pyplot as plt
from bokeh.resources import INLINE
from time import sleep

from bokeh.io import output_notebook
output_notebook(resources=INLINE, notebook_type='jupyter') 

def initiate_widgets(input_file='https://thredds.met.no/thredds/dodsC/fou-hi/norkystv3_800m_m00_be', trajectory_file=None):
    notebook_widget(input_file=input_file, trajectory_file=trajectory_file)
    compare()

def plot_trajectories(ds_list):
    # Trajectory
    plt.figure(figsize=(10, 6))
    for i, ds in enumerate(ds_list):
        plt.scatter(ds.lon.isel(trajectory=0, time=0), ds.lat.isel(trajectory=0, time=0), s=150, c='black', marker='*', alpha=1, label=f'file {i+1} (start)', zorder=10)
        for j in range(ds.trajectory.size):
            plt.scatter(ds.lon.isel(trajectory=j), ds.lat.isel(trajectory=j), s=50, alpha=0.7, label=f'file {i+1}, trajectory {j+1}', zorder=9)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Trajectories')
    plt.legend()
    plt.show()

    # depth
    plt.figure(figsize=(10, 6))
    for i, ds in enumerate(ds_list):
        for j in range(ds.trajectory.size):
            plt.plot(ds.time, ds.z.isel(trajectory=j), label=f'file {i+1}, trajectory {j+1}')
    plt.xlabel('Time')
    plt.ylabel('Depth (m)')
    plt.title('Depth')
    plt.legend()
    plt.show()

    # salinity
    plt.figure(figsize=(10, 6))
    for i, ds in enumerate(ds_list):
        for j in range(ds.trajectory.size):
            plt.plot(ds.time, ds.sea_water_salinity.isel(trajectory=j), label=f'file {i+1}, trajectory {j+1}')
    plt.xlabel('Time')
    plt.ylabel('Salinity')
    plt.title('Salinity')
    plt.legend()
    plt.show()

    # temperature
    plt.figure(figsize=(10, 6))
    for i, ds in enumerate(ds_list):
        for j in range(ds.trajectory.size):
            plt.plot(ds.time, ds.sea_water_temperature.isel(trajectory=j), label=f'file {i+1}, trajectory {j+1}')
    plt.xlabel('Time')
    plt.ylabel('Temperature')
    plt.title('Temperature')
    plt.legend()
    plt.show()

def notebook_widget(input_file='https://thredds.met.no/thredds/dodsC/fou-hi/norkystv3_800m_m00_be', trajectory_file=None):
    locations = pd.read_csv("Sites_aquaculture.csv", names=['ID', 'lon', 'lat'])
    ds = xr.open_dataset(input_file, engine='netcdf4')
    x_min, x_max = float(ds.lon.min()), float(ds.lon.max())
    y_min, y_max = float(ds.lat.min()), float(ds.lat.max())
    output_box = widgets.Output()
    from cartopy.io import shapereader

    site_source = ColumnDataSource({
        'id': locations['ID'].astype(str).to_numpy(),
        'lon': locations['lon'].to_numpy(),
        'lat': locations['lat'].to_numpy(),
        'display_lon': locations['lon'].to_numpy(),
        'display_lat': locations['lat'].to_numpy(),
    })
    sim_source = ColumnDataSource({'lon': [], 'lat': []})
    domain_source = ColumnDataSource({'left': [x_min], 'right': [x_max], 'bottom': [y_min], 'top': [y_max]})

    land_path = shapereader.natural_earth(
        resolution='10m',
        category='physical',
        name='land',
    )
    land_reader = shapereader.Reader(land_path)

    land_xs = []
    land_ys = []
    for geom in land_reader.geometries():
        minx, miny, maxx, maxy = geom.bounds
        if maxx < x_min or minx > x_max or maxy < y_min or miny > y_max:
            continue

        if geom.geom_type == 'Polygon':
            polygons = [geom]
        elif geom.geom_type == 'MultiPolygon':
            polygons = geom.geoms
        else:
            continue

        for polygon in polygons:
            xs, ys = polygon.exterior.xy
            land_xs.append(np.asarray(xs).tolist())
            land_ys.append(np.asarray(ys).tolist())

    land_source = ColumnDataSource({'xs': land_xs, 'ys': land_ys})


    coastline_path = shapereader.natural_earth(
        resolution='10m',
        category='physical',
        name='coastline',
    )
    coastline_reader = shapereader.Reader(coastline_path)

    coastline_xs = []
    coastline_ys = []
    for geom in coastline_reader.geometries():
        minx, miny, maxx, maxy = geom.bounds
        if maxx < x_min or minx > x_max or maxy < y_min or miny > y_max:
            continue

        if geom.geom_type == 'LineString':
            xs, ys = geom.xy
            coastline_xs.append(np.asarray(xs).tolist())
            coastline_ys.append(np.asarray(ys).tolist())
        elif geom.geom_type == 'MultiLineString':
            for part in geom.geoms:
                xs, ys = part.xy
                coastline_xs.append(np.asarray(xs).tolist())
                coastline_ys.append(np.asarray(ys).tolist())

    coastline_source = ColumnDataSource({'xs': coastline_xs, 'ys': coastline_ys})

    selected_text = Div(
        text='Click a red point to see ID, lon, and lat.',
        styles={'font-size': '18px', 'font-weight': '600'}
    )

    plot = figure(
        width=900,
        height=700,
        x_range=(x_min, x_max),
        y_range=(y_min, y_max),
        tools='pan,box_zoom,reset,save,tap',
        match_aspect=True,
        title='Aquaculture Sites in Norway',
    )

    plot.background_fill_color = '#d7ecff'

    plot.patches(
        xs='xs',
        ys='ys',
        source=land_source,
        fill_color='#d8c3a5',
        fill_alpha=0.95,
        line_alpha=0,
    )

    plot.multi_line(
        xs='xs',
        ys='ys',
        source=coastline_source,
        line_color='#7b6650',
        line_width=1.0,
        line_alpha=0.9,
    )

    sites = plot.scatter(
        'display_lon',
        'display_lat',
        source=site_source,
        color='red',
        size=10,
        legend_label='Aquaculture Sites',
    )

    if trajectory_file is not None:
        ds_trajectory = xr.open_dataset(trajectory_file, engine='netcdf4')
        sim_source.data = {
            'lon': ds_trajectory.lon.values.flatten(),
            'lat': ds_trajectory.lat.values.flatten(),
        }

    sim_points = plot.scatter(
        'lon',
        'lat',
        source=sim_source,
        color="#000000",
        size=7,
        alpha=0.9,
        legend_label='Simulation output',
    )

    plot.quad(
        left='left',
        right='right',
        bottom='bottom',
        top='top',
        source=domain_source,
        fill_alpha=0,
        line_color='#1e40af',
        line_width=2,
        line_dash='dashed',
        legend_label='Model domain',
    )

    plot.legend.location = 'top_right'

    plot.xaxis.axis_label = 'Longitude'
    plot.yaxis.axis_label = 'Latitude'

    x_slider = RangeSlider(start=x_min, end=x_max, value=(x_min, x_max), step=0.05, title='Longitude range')
    y_slider = RangeSlider(start=y_min, end=y_max, value=(y_min, y_max), step=0.05, title='Latitude range')

    x_slider.js_on_change(
        'value',
        CustomJS(args=dict(plot=plot), code="""
            plot.x_range.start = cb_obj.value[0];
            plot.x_range.end = cb_obj.value[1];
        """)
    )
    y_slider.js_on_change(
        'value',
        CustomJS(args=dict(plot=plot), code="""
            plot.y_range.start = cb_obj.value[0];
            plot.y_range.end = cb_obj.value[1];
        """)
    )

    site_source.selected.js_on_change(
        'indices',
        CustomJS(args=dict(
            source=site_source,
            selected_text=selected_text,
            x_slider=x_slider,
            y_slider=y_slider,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max
        ), code="""
            function syncWidgetValue(cssClass, value) {
                const host = document.querySelector(`.${cssClass}`);
                if (!host) {
                    return;
                }
                const input = host.querySelector('input');
                if (!input) {
                    return;
                }
                input.value = value;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }

            const indices = cb_obj.indices;
            if (indices.length === 0) {
                syncWidgetValue('selected-site-id-proxy', '');
                syncWidgetValue('selected-lon-proxy', '');
                syncWidgetValue('selected-lat-proxy', '');
                return;
            }
            const idx = indices[0];
            const id = source.data.id[idx];
            const lon = source.data.lon[idx];
            const lat = source.data.lat[idx];

            selected_text.text = `Selected point: ID=${id}, lon=${lon.toFixed(6)}, lat=${lat.toFixed(6)}`;
            syncWidgetValue('selected-site-id-proxy', `${id}`);
            syncWidgetValue('selected-lon-proxy', `${lon}`);
            syncWidgetValue('selected-lat-proxy', `${lat}`);

            const currentXSpan = x_slider.value[1] - x_slider.value[0];
            const currentYSpan = y_slider.value[1] - y_slider.value[0];
            const targetXSpan = Math.max(currentXSpan * 0.35, 1.0);
            const targetYSpan = Math.max(currentYSpan * 0.35, 0.75);

            let newXStart = lon - targetXSpan / 2;
            let newXEnd = lon + targetXSpan / 2;
            let newYStart = lat - targetYSpan / 2;
            let newYEnd = lat + targetYSpan / 2;

            if (newXStart < x_min) {
                newXEnd += x_min - newXStart;
                newXStart = x_min;
            }
            if (newXEnd > x_max) {
                newXStart -= newXEnd - x_max;
                newXEnd = x_max;
            }
            if (newYStart < y_min) {
                newYEnd += y_min - newYStart;
                newYStart = y_min;
            }
            if (newYEnd > y_max) {
                newYStart -= newYEnd - y_max;
                newYEnd = y_max;
            }

            x_slider.value = [Math.max(x_min, newXStart), Math.min(x_max, newXEnd)];
            y_slider.value = [Math.max(y_min, newYStart), Math.min(y_max, newYEnd)];
        """)
    )

    main_layout = column(x_slider, y_slider, selected_text, plot)
    show(main_layout, notebook_handle=True)

    # Create hidden proxy widgets so the CustomJS in `site_source.selected` can
    # write values into the notebook DOM. Observe their `.value` changes and
    # export the latest coordinates as module-level globals `selected_lon` and
    # `selected_lat` so other functions can access them directly.
    selected_site_id = widgets.Text(value='', layout=widgets.Layout(width='1px', height='1px', visibility='hidden'))
    selected_lon_input = widgets.Text(value='', layout=widgets.Layout(width='1px', height='1px', visibility='hidden'))
    selected_lat_input = widgets.Text(value='', layout=widgets.Layout(width='1px', height='1px', visibility='hidden'))
    selected_site_id.add_class('selected-site-id-proxy')
    selected_lon_input.add_class('selected-lon-proxy')
    selected_lat_input.add_class('selected-lat-proxy')

    # Display the hidden inputs so they exist in the DOM for the CustomJS
    display(widgets.HBox([selected_site_id, selected_lon_input, selected_lat_input], layout=widgets.Layout(width='1px', height='1px', overflow='hidden')))

    def _on_lon_change(change):
        try:
            globals()['selected_lon'] = change.get('new', '').strip()
        except Exception:
            pass

    def _on_lat_change(change):
        try:
            globals()['selected_lat'] = change.get('new', '').strip()
        except Exception:
            pass

    selected_lon_input.observe(_on_lon_change, names='value')
    selected_lat_input.observe(_on_lat_change, names='value')

    # Also export the widget objects into the IPython user namespace for
    # convenience and debugging in notebook cells.

    def labeled(label, w):
        return widgets.VBox([widgets.Label(label), w])

    times = pd.to_datetime(ds['time'].values)
    s = pd.Series(times)

    year = widgets.Dropdown(options=[])
    month = widgets.Dropdown(options=[])
    day = widgets.Dropdown(options=[])
    hour = widgets.Dropdown(options=[])

    year.options = sorted(s.dt.strftime('%Y').unique())
    month.options = sorted(s.dt.strftime('%m').unique())
    day.options = sorted(s.dt.strftime('%d').unique())
    hour.options = sorted(s.dt.strftime('%H').unique())

    year.value = year.options[0]
    month.value = month.options[0]
    day.value = day.options[0]
    hour.value = hour.options[0]

    number_of_particles = widgets.BoundedIntText(value=1, min=1, max=99999, step=1)
    duration = widgets.BoundedIntText(value=24, min=1, max=9999, step=1)
    depth = widgets.BoundedIntText(value=0, min=0, max=9999, step=1)
    radius = widgets.BoundedIntText(value=0, min=0, max=9999, step=1)
    timestep = widgets.BoundedIntText(value=30, min=5, max=9999, step=15)
    timestep_output = widgets.BoundedIntText(value=60, min=5, max=9999, step=15)

    outfile = widgets.Text(value='output.nc', description='Outfile')

    run_btn = widgets.Button(description='Run trajectories')

    # Layout and display: keep a reference so we can close the whole widget
    controls_box = widgets.VBox([
        widgets.HBox([labeled('Year', year), labeled('Month', month), labeled('Day', day), labeled('Hour', hour)]),
        widgets.HBox([labeled('Number of particles', number_of_particles), labeled('Duration (h)', duration), labeled('Depth (m)', depth), labeled('Radius (m)', radius)]),
        widgets.HBox([labeled('Timestep (min)', timestep), labeled('Timestep output (min)', timestep_output)]),
        widgets.HBox([outfile, run_btn]),
        output_box,
    ])
    display(controls_box)

    # Close the whole displayed controls when update is pressed
    
    run_btn.on_click(lambda _: run_sim(output_box, 
                                       inputfile.value, 
                                       year.value, 
                                       month.value, 
                                       day.value, 
                                       hour.value, 
                                       number_of_particles.value, 
                                       duration.value, 
                                       outfile.value, 
                                       float(selected_lon_input.value.strip()) if selected_lon_input.value.strip() else None, 
                                       float(selected_lat_input.value.strip()) if selected_lat_input.value.strip() else None, 
                                       -depth.value, 
                                       radius.value, 
                                       timestep.value, 
                                       timestep_output.value))
    
    

def compare():
    compare_box = widgets.Output()
    stored_text_entries = []

    text_input = widgets.Text(
        value="",
        placeholder="Provide trajectory file",
        description="Input:",
        layout=widgets.Layout(width="420px"),
    )

    save_button = widgets.Button(
        description="Save Input",
    )

    reset_button = widgets.Button(
        description="Reset Input",
    )

    run_sim_button = widgets.Button(
        description="Plot run(s)",
    )

    def save_text(_):
        text = text_input.value.strip()
        with compare_box:
            compare_box.clear_output()
            if not text:
                print("Please enter some text before saving.")
                return

            stored_text_entries.append(text)
            print(f"To compare:")
            for i in stored_text_entries:
                print(f"- {i}")

        text_input.value = ""


    def reset_input(_):
        text_input.value = ""
        stored_text_entries.clear()
        with compare_box:
            compare_box.clear_output(wait=True)
            print("Input reset and saved entries cleared.")


    def run_sim(_):
        with compare_box:
            compare_box.clear_output()
            if not stored_text_entries:
                print("No entries stored yet.")
                return

            print("Plotting provided entries")
            ds_list = [xr.open_dataset(entry) for entry in stored_text_entries]
            plot_trajectories(ds_list)

    
    save_button.on_click(save_text)
    reset_button.on_click(reset_input)
    save_button.on_click(save_text)
    run_sim_button.on_click(run_sim)
    

    display(
        widgets.VBox(
            [text_input, widgets.HBox([save_button, reset_button, run_sim_button]), compare_box],
        )
    )

def run_sim(output_box, file, year, month, day, hour, N, duration, outfile, lon, lat, z, radius, time_step, time_step_output):

    if lon is None or lat is None:
        with output_box:
            output_box.clear_output(wait=True)
            print('lon: no point selected')
            print('lat: no point selected')
            print('Please select a location from the aggriculture sites map before running the simulation.')
        return

    selected_datetime = datetime.datetime.strptime(
            f'{year}-{month}-{day} {hour}:00:00',
            '%Y-%m-%d %H:%M:%S',
        )
    
    with output_box:
        output_box.clear_output(wait=True)
        print('Running trajectory simulation (background)...')

    run_opendrift(
                file=file,
                start_time=selected_datetime,
                N=N,
                duration=duration,
                outfile=outfile,
                lon=lon,
                lat=lat,
                z=z,
                radius=radius,
                time_step=time_step,
                time_step_output=time_step_output,
                vertical_mixing=True,
                vertical_advection=True,
                track_vars=['sea_water_temperature', 'sea_water_salinity'],
                )

    with output_box:
        print('Simulation completed')

    trajectories.value = outfile
    update_btn.click()


output = widgets.Output()
inputfile = widgets.Textarea(
    value='https://thredds.met.no/thredds/dodsC/fou-hi/norkystv3_800m_m00_be',
    description='Input file',
    layout=widgets.Layout(width='800px'),
    style={'description_width': '120px'},
    rows=2
)
trajectories = widgets.Textarea(
    value='',
    description='Trajectory file',
    layout=widgets.Layout(width='800px'),
    style={'description_width': '120px'},
    rows=2
)
update_btn = widgets.Button(description='Update map',
                           layout=widgets.Layout(width='200px', height='60px'),
                            )
update_btn.style.font_size = '20px'
update_btn.style.font_weight = 'bold'

def on_click(b):
    with output:
        output.clear_output()
        if trajectories.value:
            initiate_widgets(input_file=inputfile.value, trajectory_file=trajectories.value)
        else:
            initiate_widgets(input_file=inputfile.value)

update_btn.on_click(on_click)

controls_box = widgets.VBox([
    widgets.HBox([update_btn]),
    widgets.HBox([inputfile]),
    widgets.HBox([trajectories]),
    output
])
display(controls_box)

update_btn.click()
