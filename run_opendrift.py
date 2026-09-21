"""
Author: Mateusz Matuszak
"""

#import sys
#sys.path.insert(0, str("submodules/opendrift"))

from datetime import datetime, timedelta
import os
import numpy as np
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def run_opendrift(file, lon=None, lat=None, rls=None, geojson=None, netCDF=None, traj_time_index=-1, z=0, N=1, radius=0, start_time=None, duration=12, time_step=30, time_step_output=60, outfile='sample_file.nc', depth_type='z', vertical_mixing=False, vertical_advection=False, coastline=None, track_vars=None, density_grid=None, max_age_seconds=None, particle_type=None, **kwargs):
    """
        A wrapper for running OpenDrift. https://opendrift.github.io/
        NOTE: Function starting to grow pretty long with many args. Maybe split up into smaller parts. 
    Args:
        file                [str]                           :   Model netCDF file containing ocean current data.
        lon                 [float]                         :   Longitude seed position
        lat                 [float]                         :   Latitude seed position
        rls                 [str]                           :   .rls file with seed positions
        geojson             [str]                           :   .geojson file with seed positions
        netCDF              [str]                           :   result file from previous OpenDrift run
        traj_time_index     [int]                           :   Time index of netCDF file. 
        z                   [float|list]                    :   Seed depth
        N                   [int]                           :   Number of particles. Scales with length of seed depths.
        radius              [float]                         :   Seed radius.
        start_time          [str|datetime|list of datetime] :   Start time(s). String must follow %Y-%m-%dT%H:%M:%S format
        duration            [int]                           :   Simulation duration hours.
        time_step           [int]                           :   Simulation time step minutes
        time_step_output    [int]                           :   Output frequency minutes
        outfile             [str]                           :   Name of output file
        depth_type          [str]                           :   Vertical grid type of provided ocean current data. 'z' or 's'
        vertical_mixing     [bool]                          :   Turn on vertical mixing
        vertical_advection  [bool]                          :   Turn on vertical advection
        coastline           [str|list]                      :   Custom coastline (landmask). "Model" will use model landmask. 
        track_vars          [str|list]                      :   Track additional variables along trajectory. Strict naming, see https://github.com/OpenDrift/opendrift/blob/master/opendrift/readers/reader_ROMS_native.py
        density_grid        [int]                           :   Create density map of trajectories with specified grid size.
        max_age_seconds     [int]                           :   Particle lifetime.
        particle_type       [str]                           :   OceanDrift or LarvalFish
    """
    #TODO consider moving some parts into its own functions as the script is becoming quite long
    from opendrift.models.oceandrift import OceanDrift
    from opendrift.models.larvalfish import LarvalFish
    ### Track additional variables #### (KF said there is a better way)
    if track_vars is not None:
        if isinstance(track_vars, str):
            track_vars = [track_vars]
        if not isinstance(track_vars, list) and not all(isinstance(item, str) for item in track_vars):
            raise TypeError('Argument track_vars must be either a string or a list of strings.')
        
        else:
            for var in track_vars:
                OceanDrift.required_variables.update(
                    {
                        var: {'fallback': 0} 
                    }
                )

    #### Particle Type ####
    #General tracers
    loglevel=20
    if particle_type is None or particle_type == 'tracer':
        logger.info('Using general particle type OceanDrift')
        o = OceanDrift(
            loglevel=loglevel,
            seed=0
        )

    #Fish Eggs and Larvea
    if particle_type == 'LarvalFish':
        logger.info('Using particle type LarvalFish')
        o = LarvalFish(
            loglevel=loglevel,
            seed=0
        )

    #### Load reader ####
    if isinstance(file, list):
        pass
    elif os.path.isdir(file):
        file = [file+'/*']
    elif os.path.exists(file) or 'thredds' in file:
        file = [file]
    else:
        raise ValueError(f'File or directory {file} not found.')
        
    if depth_type == 'z':
        from opendrift.readers import reader_netCDF_CF_generic
        r = [reader_netCDF_CF_generic.Reader(f) for f in file]
    elif depth_type == 's':
        from opendrift.readers import reader_ROMS_native
        r = [reader_ROMS_native.Reader(f) for f in file]
    else:
        raise ValueError(f'Supported depth types are [z, s], got {depth_type}')

    #### Landmask ####
    if coastline is not None:
        if isinstance(coastline, str):
            coastline = [coastline]
        if not isinstance(coastline, list) and not all(isinstance(item, str) for item in coastline):
            raise TypeError('Argument coastline must be either a string or a list of strings.')
        
        o.set_config("general:use_auto_landmask", False)
        o.set_config("environment:fallback:land_binary_mask", 0)
            
        if coastline[0] == 'Model':
            pass

        else: 
            from opendrift.readers import reader_shape
            for c in coastline:
                r.append(reader_shape.Reader.from_shpfiles(c))
    o.add_reader(r)
    
    #### Config options ####
    o.set_config('general:seafloor_action', 'lift_to_seafloor')
    o.set_config('general:coastline_action', 'previous')
    #o.set_config('environment:constant:horizontal_diffusivity', horizontal_diffusivity)
    o.set_config('drift:vertical_mixing', vertical_mixing)
    o.set_config('drift:vertical_advection', vertical_advection)
    o.set_config('drift:vertical_mixing_at_surface', vertical_mixing)
    o.set_config('drift:vertical_advection_at_surface', vertical_advection)
    o.set_config('vertical_mixing:diffusivitymodel', 'environment')
    # Using default Euler scheme for advection for the presentation. Runge-Kutta4 is more accurate but slower.
    #o.set_config('drift:advection_scheme', 'runge-kutta4')
    
    if max_age_seconds is not None:
        o.set_config('drift:max_age_seconds', max_age_seconds)

    #### Start time ####
    if start_time is None:
        start_time = [r[0].start_time]
    elif isinstance(start_time, str):
        try:
            start_time = [datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')]
        except:
            raise ValueError('Provided start time does not follow required format. Try %Y-%m-%dT%H:%M:%S')
    elif (isinstance(start_time, list) and all(isinstance(item, datetime) for item in start_time) 
        or isinstance(start_time, np.ndarray) and all(isinstance(item, datetime) for item in start_time)):
        start_time=list(start_time)
    elif isinstance(start_time, datetime):
        start_time=[start_time]
    else:
        raise TypeError('Type of start_time is not supported.')
    
    #### Depth ####
    if isinstance(z, float) or isinstance(z, int) or isinstance(z, str):
        z = [z]
    elif isinstance(z, list):
        z = z
    elif isinstance(z, np.ndarray):
        z = list(z)

    #### Seeding elements ####

    #This whole seeding part might be done prettier later. 
    #Ask Knut-Frode for some tips here, so that I don't seed with a for loop
    if lon is not None and lat is not None:
        logger.info('Using positions from provided lon lat')
        o.seed_elements(lon=lon,
                        lat=lat,
                        z=z*N*len(start_time),
                        number=N*len(z)*len(start_time),
                        radius=radius,
                        time=start_time*len(z)*N,
                        **kwargs)
        
    if rls is not None:
        import pandas as pd
        logger.info('Using positions from provided .rls file')
        #From Knut-Frode, testing with provided file
        p = pd.read_csv(rls, sep='\t', names=['time', 'lon', 'lat', 'a'])
        
        start_time = pd.to_datetime(p['time']).dt.to_pydatetime()

        for _z in z:
            o.seed_elements(lon=p['lon'],
                            lat=p['lat'],
                            time=start_time,
                            z=_z,
                            **kwargs)

    if geojson is not None:
        logger.info('Using positions from provided .geojson file')
        #From Knut-Frode
        import geopandas as gdp
        gdf = gdp.read_file(geojson)
        
        #this loop could be removed. 
        for _z in z:
            for time in start_time:
                o.seed_from_geopandas(gdf,
                                    z=_z,
                                    number=N,
                                    time=time,
                                    **kwargs)
    
    if netCDF is not None:
        o.seed_from_file(netCDF, trajectory_time_index=traj_time_index)
    
    #### Run OpenDrift ####
    o.run(duration=timedelta(hours=duration),
          time_step=timedelta(minutes=time_step),
          time_step_output=timedelta(minutes=time_step_output),
          outfile=outfile,
          export_buffer_length=50,
          )
    
    #### Postprocess ####
    if density_grid is not None and isinstance(density_grid, int):
        concentration(outfile, density_grid)

def concentration(file, density_grid):
    """
        Creates a concentration field of particles from OpenDrift run adds it to OpenDrift netcdf file. 
    Args:
        file            [str]   :   An OpenDrift output file. 
        density_grid    [int]   :   Grid size in the concentration field. 
    """
    import trajan
    import xarray as xr
    ds = xr.open_dataset(file)
    os.system(f'rm {file}')
    grid = ds.traj.make_grid(dx=density_grid)
    ds_c = ds.traj.concentration(grid)
    ds = ds.assign_coords({
    "c_lon": ds_c.lon.values, 
    "c_lat": ds_c.lat.values
    })
    ds = ds.assign({
        "number": (['time', 'c_lat', 'c_lon'], ds_c.number.values),
        "cell_area": (['c_lat', 'c_lon'], ds_c.cell_area.values),
        "number_area_concentration": (['time', 'c_lat', 'c_lon'], ds_c.number_area_concentration.values),
    })
    ds.to_netcdf(file)
    return ds

if __name__ == "__main__":
    #TODO update this
    import argparse
    parser = argparse.ArgumentParser(
        prog='opendrift'
    )
    parser.add_argument(
        '-f', '--file', type=str, required=True, help='Input file or directory.'
    )
    parser.add_argument(
        '-lon', '--longitude', type=float, required=True, help='Initial longitude position of particles.'
    )
    parser.add_argument(
        '-lat', '--latitude', type=float, required=True, help='Initial latitude position of particles.'
    )
    parser.add_argument(
        '-z', '--depth_level', type=float, default=0, help='Intial depth level of particles in meters.'
    )
    parser.add_argument(
        '-N', '--number', type=int, default=1, help='Number of particles.'
    )
    parser.add_argument(
        '-r', '--radius', type=float, default=0, help='Radius for particle spread around initial lon lat position.'
    )
    parser.add_argument(
        '-st', '--start_time', type=str, default=None, help='Start time as ISO string. <year-month-dayThour:minutes:seconds.'
    )
    parser.add_argument(
        '-dur', '--duration', type=int, default=12, help='Duration of simulation in hours.'
    )
    parser.add_argument(
        '-ts', '--time_step', type=int, default=30, help='Computation time step during simulation in minutes.'
    )
    parser.add_argument(
        '-tso', '--time_step_output', type=int, default=60, help='Output frequency of simulation in minutes.'
    )
    parser.add_argument(
        '-o', '--outfile', type=str, default='sample_file.nc', help='Name of output file.'
    )
    parser.add_argument(
        '-dt', '--depth_type', default='z', choices=['z', 's'], type=str, help='Chose depth type of input data.'
    )
    parser.add_argument(
        '-vm', '--vertical_mixing', default=False, action=argparse.BooleanOptionalAction, help='When used, will turn on vertical mixing.'
    )
    parser.add_argument(
        '-hd', '--horizontal_diffusivity', default=0, type=float, help='Set horizontal diffusivity value.'
    )
    parser.add_argument(
        '-c' '--coastline', default=None, help='Provide custom coastline from file(s).'
    )
    parser.add_argument(
        '-tv' '--track_vars', default=None, help='Additional variables to output along particle trajectory.'
    )
    parser.add_argument(
        '-dg' '--density_grid', type=int, help='Create a density map of particles. This arg specifies grid size for map.'
    )
    args = parser.parse_args()
    run_opendrift(file=args.file,
                  lon=args.longitude,
                  lat=args.latitude,
                  z=args.depth_level,
                  N=args.number,
                  radius=args.radius,
                  start_time=args.start_time, 
                  duration=args.duration,
                  time_step=args.time_step,
                  time_step_output=args.time_step_output,
                  outfile=args.outfile,
                  depth_type=args.depth_type,
                  vertical_mixing=args.vertical_mixing,
                  horizontal_diffusivity=args.horizontal_diffusivity,
                  coastline=args.coastline,
                  track_vars=args.track_vars,
                  density_grid=args.density_grid)