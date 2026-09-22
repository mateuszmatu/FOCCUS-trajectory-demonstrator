import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import cKDTree
from bokeh.io import output_notebook, show, push_notebook
from bokeh.layouts import column, row
from bokeh.models import ColorBar, ColumnDataSource, CustomJS, Div, LinearColorMapper, RangeSlider, Select
from bokeh.plotting import figure
from bokeh.resources import CDN
import ipywidgets as widgets
from IPython.display import display
import datetime
from run_opendrift import run_opendrift
import concurrent.futures
import matplotlib.pyplot as plt
output_notebook()

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

def notebook_widget():
    locations = pd.read_csv("Sites_aquaculture.csv", names=['ID', 'lon', 'lat'])
    input_file = xr.open_dataset('https://thredds.met.no/thredds/dodsC/fou-hi/norkystv3_800m_m00_be')
    x_min, x_max = float(input_file.lon.min()), float(input_file.lon.max())
    y_min, y_max = float(input_file.lat.min()), float(input_file.lat.max())

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

    # Use CDN rendering for the plot inside the notebook
    from bokeh.resources import CDN
    from bokeh.io import output_notebook
    output_notebook(resources=CDN)
    main_layout = column(x_slider, y_slider, selected_text, plot)

    # Show plot with a notebook handle so we can push updates from Python
    bokeh_handle = show(main_layout, notebook_handle=True)

    timestamp_frame = pd.DataFrame({'timestamp': pd.to_datetime(input_file.time.values)})
    timestamp_frame['year'] = timestamp_frame['timestamp'].dt.strftime('%Y')
    timestamp_frame['month'] = timestamp_frame['timestamp'].dt.strftime('%m')
    timestamp_frame['day'] = timestamp_frame['timestamp'].dt.strftime('%d')
    timestamp_frame['hour'] = timestamp_frame['timestamp'].dt.strftime('%H')

    def labeled(label, widget):
        return widgets.VBox([widgets.Label(label), widget])

    year_dropdown = widgets.Dropdown()
    month_dropdown = widgets.Dropdown()
    day_dropdown = widgets.Dropdown()
    hour_dropdown = widgets.Dropdown()
    number_input = widgets.BoundedIntText(value=1, min=1, max=99999, step=1)
    duration_input = widgets.BoundedIntText(value=24, min=1, max=9999, step=1)
    depth_input = widgets.BoundedIntText(value=0, min=0, max=9999, step=1)
    radius_input = widgets.BoundedIntText(value=0, min=0, max=9999, step=1)
    timestep_input = widgets.BoundedIntText(value=30, min=5, max=9999, step=15)
    timestep_output_input = widgets.BoundedIntText(value=60, min=5, max=9999, step=15)
    outfile_input = widgets.Text(value='output.nc')
    inputfile_input = widgets.Text(value='https://thredds.met.no/thredds/dodsC/fou-hi/norkystv3_800m_m00_be')
    selected_site_id = widgets.Text(value='', layout=widgets.Layout(width='1px', height='1px', visibility='hidden'))
    selected_lon_input = widgets.Text(value='', layout=widgets.Layout(width='1px', height='1px', visibility='hidden'))
    selected_lat_input = widgets.Text(value='', layout=widgets.Layout(width='1px', height='1px', visibility='hidden'))
    selected_site_id.add_class('selected-site-id-proxy')
    selected_lon_input.add_class('selected-lon-proxy')
    selected_lat_input.add_class('selected-lat-proxy')

    def month_options(year):
        return sorted(timestamp_frame.loc[timestamp_frame['year'] == year, 'month'].unique())

    def day_options(year, month):
        mask = (timestamp_frame['year'] == year) & (timestamp_frame['month'] == month)
        return sorted(timestamp_frame.loc[mask, 'day'].unique())

    def hour_options(year, month, day):
        mask = (
            (timestamp_frame['year'] == year)
            & (timestamp_frame['month'] == month)
            & (timestamp_frame['day'] == day)
        )
        return sorted(timestamp_frame.loc[mask, 'hour'].unique())

    def sync_months(*_):
        options = month_options(year_dropdown.value)
        month_dropdown.options = options
        if month_dropdown.value not in options:
            month_dropdown.value = options[0]

    def sync_days(*_):
        options = day_options(year_dropdown.value, month_dropdown.value)
        day_dropdown.options = options
        if day_dropdown.value not in options:
            day_dropdown.value = options[0]

    def sync_hours(*_):
        options = hour_options(year_dropdown.value, month_dropdown.value, day_dropdown.value)
        hour_dropdown.options = options
        if hour_dropdown.value not in options:
            hour_dropdown.value = options[0]

    year_dropdown.options = sorted(timestamp_frame['year'].unique())
    year_dropdown.value = year_dropdown.options[0]

    sync_months()
    sync_days()
    sync_hours()

    update_input_file_button = widgets.Button(
        description='Update input file',
        layout=widgets.Layout(width='200px', height='36px'),
        style={'font_weight': '700', 'button_color': '#dbeafe'}
    )
    update_input_file_status = widgets.Output()

    def on_update_input_file(_):
        global timestamp_frame
        with update_input_file_status:
            update_input_file_status.clear_output(wait=True)
            try:
                new_ds = xr.open_dataset(inputfile_input.value)
                timestamp_frame = pd.DataFrame({'timestamp': pd.to_datetime(new_ds.time.values)})
                timestamp_frame['year'] = timestamp_frame['timestamp'].dt.strftime('%Y')
                timestamp_frame['month'] = timestamp_frame['timestamp'].dt.strftime('%m')
                timestamp_frame['day'] = timestamp_frame['timestamp'].dt.strftime('%d')
                timestamp_frame['hour'] = timestamp_frame['timestamp'].dt.strftime('%H')
                year_dropdown.options = sorted(timestamp_frame['year'].unique())
                year_dropdown.value = year_dropdown.options[0]
                sync_months()
                sync_days()
                sync_hours()
                new_x_min = float(new_ds.lon.min())
                new_x_max = float(new_ds.lon.max())
                new_y_min = float(new_ds.lat.min())
                new_y_max = float(new_ds.lat.max())
                x_slider.start = new_x_min
                x_slider.end = new_x_max
                x_slider.value = (new_x_min, new_x_max)
                y_slider.start = new_y_min
                y_slider.end = new_y_max
                y_slider.value = (new_y_min, new_y_max)
                plot.x_range.start = new_x_min
                plot.x_range.end = new_x_max
                plot.y_range.start = new_y_min
                plot.y_range.end = new_y_max
                domain_source.data = {'left': [new_x_min], 'right': [new_x_max], 'bottom': [new_y_min], 'top': [new_y_max]}
                # push updates to the notebook Bokeh output
                try:
                    # schedule push_notebook on the notebook I/O loop so calls
                    # from background threads are executed in the main thread
                    from tornado import ioloop
                    ioloop.IOLoop.current().add_callback(lambda: push_notebook(handle=bokeh_handle))
                except Exception as e:
                    # fallback: try direct push and log failures
                    try:
                        push_notebook(handle=bokeh_handle)
                    except Exception as e2:
                        err = f'push_notebook scheduling failed: {e}; direct push failed: {e2}'
                        print(err)
                        try:
                            with open('/tmp/foccus_bokeh_debug.log', 'a') as fh:
                                fh.write(err + '\n')
                        except Exception:
                            pass
                print(f'Input file updated: {inputfile_input.value}')
            except Exception as e:
                print(f'Error loading input file: {e}')

    update_input_file_button.on_click(on_update_input_file)

    button = widgets.Button(
        description='Run trajectories',
        layout=widgets.Layout(width='320px', height='72px'),
        style={'font_weight': '700', 'button_color': '#dbeafe'},
    )
    button.style.font_size = '24px'
    output_box = widgets.Output()

    # run simulation in a background thread and update the Bokeh ColumnDataSource
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def on_run_sim_click(_):
        selected_datetime = datetime.datetime.strptime(
            f'{year_dropdown.value}-{month_dropdown.value}-{day_dropdown.value} {hour_dropdown.value}:00:00',
            '%Y-%m-%d %H:%M:%S',
        )
        selected_lon = selected_lon_input.value.strip()
        selected_lat = selected_lat_input.value.strip()

        with output_box:
            output_box.clear_output(wait=True)
            if selected_lon and selected_lat:
                print('Running trajectory simulation (background)...')
                sim_ready = True
            else:
                sim_ready = False
                print('lon: no point selected')
                print('lat: no point selected')
                print('Please select a location from the aggriculture sites map before running the simulation.')

        if not sim_ready:
            return

        def _run_and_update(output_box=output_box, bokeh_handle=bokeh_handle):
            try:
                # run the long OpenDrift job
                run_opendrift(
                    file=inputfile_input.value,
                    start_time=selected_datetime,
                    N=number_input.value,
                    duration=duration_input.value,
                    outfile=outfile_input.value,
                    lon=float(selected_lon),
                    lat=float(selected_lat),
                    z=-depth_input.value,
                    radius=radius_input.value,
                    time_step=timestep_input.value,
                    time_step_output=timestep_output_input.value,
                    vertical_mixing=True,
                    vertical_advection=True,
                    track_vars=['sea_water_temperature', 'sea_water_salinity'],
                )

                # read output and update data source
                with output_box:
                    print('Simulation completed. Output saved to:', outfile_input.value)
                with xr.open_dataset(outfile_input.value) as output_ds:
                    lon_vals = np.array(output_ds.lon.values).ravel().tolist()
                    lat_vals = np.array(output_ds.lat.values).ravel().tolist()

                if len(lon_vals) and len(lat_vals):
                    # Debug: show counts and sample values
                    try:
                        print(f'len(lon_vals)={len(lon_vals)}, len(lat_vals)={len(lat_vals)}')
                        if len(lon_vals) > 0:
                            print('sample lon,lat:', lon_vals[0], lat_vals[0])
                    except Exception:
                        pass

                    def _apply_update():
                        try:
                            sim_source.data = {'lon': lon_vals, 'lat': lat_vals}
                            try:
                                push_notebook(handle=bokeh_handle)
                                with output_box:
                                    print('Bokeh plot updated with simulation output.')
                            except Exception as e_push:
                                with output_box:
                                    print('push_notebook direct failed inside main loop:', e_push)
                        except Exception as e_set:
                            with output_box:
                                print('Failed to set sim_source.data on main loop:', e_set)

                    # Schedule the update on the notebook I/O loop (main thread)
                    try:
                        from tornado import ioloop
                        ioloop.IOLoop.current().add_callback(_apply_update)
                        with output_box:
                            print('Scheduled sim_source update on notebook I/O loop.')
                    except Exception as e:
                        # Fallback: set directly and try pushing
                        try:
                            sim_source.data = {'lon': lon_vals, 'lat': lat_vals}
                            try:
                                push_notebook(handle=bokeh_handle)
                                with output_box:
                                    print('Bokeh plot updated with simulation output (fallback).')
                            except Exception as e2:
                                with output_box:
                                    print('Direct push failed in fallback:', e2)
                                try:
                                    with open('/tmp/foccus_bokeh_debug.log', 'a') as fh:
                                        fh.write(f'Fallback direct push failed: {e2}\n')
                                except Exception:
                                    pass
                        except Exception as e_set2:
                            with output_box:
                                print('Fallback failed to set sim_source.data:', e_set2)

                # also produce matplotlib trajectory plots
                with xr.open_dataset(outfile_input.value) as output_ds:
                    plot_trajectories([output_ds])

            except Exception as e:
                with output_box:
                    print('Simulation failed:', e)

        # Submit the callable to the executor (do not call it here)
        executor.submit(_run_and_update(output_box=output_box, bokeh_handle=bokeh_handle))

    button.on_click(on_run_sim_click)

    input_file_controls = widgets.VBox([
        widgets.HBox([labeled('Input file', inputfile_input), update_input_file_button]),
        update_input_file_status,
    ])

    date_controls = widgets.HBox([labeled('Year', year_dropdown), labeled('Month', month_dropdown), labeled('Day', day_dropdown), labeled('Hour', hour_dropdown)])
    simulation_controls_upper = widgets.HBox([labeled('Number of particles', number_input), labeled('Duration (h)', duration_input), labeled('Depth (m)', depth_input), labeled('Radius (m)', radius_input)])
    simulation_controls_lower = widgets.HBox([labeled('Timestep (minutes)', timestep_input), labeled('Timestep output (minutes)', timestep_output_input), labeled('Output file', outfile_input)])
    selection_state = widgets.HBox(
        [selected_site_id, selected_lon_input, selected_lat_input],
        layout=widgets.Layout(width='1px', height='1px', overflow='hidden'),
    )

    # controls (already shown below the plot)
    display(widgets.VBox([input_file_controls, date_controls, simulation_controls_upper, simulation_controls_lower, button, output_box, selection_state]))

    # Export key objects into the interactive IPython user namespace so
    # diagnostic cells in the notebook can access them directly.
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if ip is not None:
            ip.push({
                'sim_source': sim_source,
                'bokeh_handle': bokeh_handle,
                'plot': plot,
                'selected_lon_input': selected_lon_input,
                'selected_lat_input': selected_lat_input,
                'output_box': output_box,
                'site_source': site_source,
                'x_slider': x_slider,
                'y_slider': y_slider,
            })
    except Exception:
        pass

    stored_text_entries = []

    text_input = widgets.Text(
        value="",
        placeholder="Provide trajectory file",
        description="Input:",
        layout=widgets.Layout(width="420px"),
    )

    save_button = widgets.Button(
        description="Add file",
        layout=widgets.Layout(width='320px', height='72px'),
        style={'font_weight': '700', 'button_color': '#dbeafe', 'font_size': '24px'},
    )

    reset_button = widgets.Button(
        description="Reset Input",
        layout=widgets.Layout(width='320px', height='72px'),
        style={'font_weight': '700', 'button_color': '#dbeafe', 'font_size': '24px'},
    )

    run_sim_button = widgets.Button(
        description="Compare runs",
        layout=widgets.Layout(width='320px', height='72px'),
        style={'font_weight': '700', 'button_color': '#dbeafe', 'font_size': '24px'},
    )

    status = widgets.Output()


    def save_text(_):
        text = text_input.value.strip()
        with status:
            status.clear_output()
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
        with status:
            status.clear_output()
            print("Input reset and saved entries cleared.")


    def run_sim(_):
        with status:
            status.clear_output()
            if not stored_text_entries:
                print("No entries stored yet.")
                return

            print("Running comparison with provided entries")
            ds_list = [xr.open_dataset(entry) for entry in stored_text_entries]
            plot_trajectories(ds_list)


    save_button.on_click(save_text)
    reset_button.on_click(reset_input)
    save_button.on_click(save_text)
    run_sim_button.on_click(run_sim)

    display(
        widgets.VBox(
            [text_input, widgets.HBox([save_button, reset_button, run_sim_button]), status],
        )
    )