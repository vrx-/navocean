import requests
from requests.auth import HTTPBasicAuth
import numpy as np
from datetime import datetime, timedelta
import pytz
eastern = pytz.timezone('US/Eastern')

import pandas as pd
from matplotlib import pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cmocean import cm as ccmo


def gen_url(telemetry='min', BB3='min', CI='min', CT='min', O2='min',
			path=None, date_interval=None, limit=100):

	## Returns string for URL ans list of names date type variables requested

	## base strings and querry dictionaries

	if limit > 30000:
		print("WARNING: requesting %i records. \n This will stress navocean's server. Pleaseresubmit with limit=%i records" % (limit, 10000))
	
	group_options = {'telemetry': telemetry, 'BB3': BB3, 'CI': CI, 'CT': CT, 'O2': O2}

	querry = {
	'telemetry' : {
		'all': ['GPSTimeStamp', '2CLon', '2CLat', '2CSpeed', '2CTrack', '2CHeading', '2CPitch', '2CRoll', '2CWindTrueSpeed', '2CWindTrueDir', '2CPressureInches', '2CAirTemp'],
        'min': ['GPSTimeStamp', '2CLon', '2CLat', '2CTrack', '2CHeading']
                    },
    'BB3' : {
    	'all' : ['2CBB3+%5BTime+UTC%5D', '2CBb%28470%29+%5Bcounts%5D', '2CBb%28532%29+%5Bcounts%5D', '2CBb%28650%29+%5Bcounts%5D', '2CBb%28470%29+%5BNTU%5D', '2CBb%28532%29+%5BNTU%5D', '2CBb%28650%29+%5BNTU%5D'],
        'min' : ['2CBb%28470%29+%5BNTU%5D', '2CBb%28532%29+%5BNTU%5D','2CBb%28650%29+%5BNTU%5D']
            },
    'CI' : {
    		'all': ['2CCI+%5BTime+UTC%5D', '2CChl.+a+%5Bcounts%5D', '2CCDOM+%5Bcounts%5D', '2CPhycocyanin+%5Bcounts%5D', '2CCDOM+%5BQSU%5D', '2CChl.+a+%5Bppb%5D', '2CPhycocyanin+%5Bppb%5D'],
            'min': ['2CCDOM+%5BQSU%5D', '2CChl.+a+%5Bppb%5D', '2CPhycocyanin+%5Bppb%5D']
            },
    'CT' : {
    		'all': ['2CCT+%5BTime+UTC%5D', '2CConductivity+%5BmS+cm-1%5D', '2CTemperature+%5Bdeg+C%5D'],
            'min': ['2CConductivity+%5BmS+cm-1%5D', '2CTemperature+%5Bdeg+C%5D']
            },
    'O2' : {
    		'all': ['2CO2+%5BTime+UTC%5D', '2CO2+Concentration+%5Bmicromolar%5D', '2CO2+Saturation+%5B%25%5D', '2CO2+Temperature+%5Bdeg+C%5D'],
            'min': ['2CO2+Concentration+%5Bmicromolar%5D']
            }
    }

	time_dic = {'GPSTimeStamp': 'GPSTimeStamp', '2CBB3+%5BTime+UTC%5D': 'BB3 [Time UTC]', '2CCI+%5BTime+UTC%5D': 'CI [Time UTC]', '2CO2+%5BTime+UTC%5D': 'CT [Time UTC]'}

	root_url = 'http://portal.navocean.com/services/nav.php?req=data&id=VELA'
	fmtt = 'format=csv&output=file'
	limit = 'limit=%i' % limit
	token= 'token=5e5c4d86-3fd9-11eb-904e-06ad0ec96835'


	# build string for variable request

	columns = []
	if group_options['telemetry']:
		columns.extend(querry['telemetry'][group_options['telemetry']])
	if group_options['BB3']:
		columns.extend(querry['BB3'][group_options['BB3']])
	if group_options['CI']:
		columns.extend(querry['CI'][group_options['CI']])
	if group_options['CT']:
		columns.extend(querry['CT'][group_options['CT']])
	if group_options['O2']:
		columns.extend(querry['O2'][group_options['O2']])
	columns = 'columns='+'%'.join(columns)


    # build string for date request

	if date_interval:
		time = 'start='+date_interval[0]+"+00%3A00%3A00&end="+date_interval[1]+"+00%3A00%3A00"
		url = '&'.join([root_url, columns, fmtt, time, token]), date_vars
	else:
		url = '&'.join([root_url, columns, fmtt, limit, token])

	# get date type variables for parser

	date_cols = []
	for time_key in time_dic:
		if time_key in url:
			date_cols.append(time_dic[time_key])
	print('Data variables are:', date_cols)

	return url, date_cols


def load_csv(path, date_vars=False):
	parse_dates = date_vars
	date_parser=lambda x: pd.to_datetime(x, errors="coerce")

	return pd.read_csv(path, skipinitialspace=True, parse_dates=parse_dates, date_parser=date_parser,
		index_col='Id').replace(r'^\s*$', np.nan, regex=True)


def get_data(path, date_vars=['GPSTimeStamp']):
# Output: dataframe:
# Input: either navocean url, or a lists of filenames
# Names of date type variables to parse
	if type(path) is str:
		if 'http' in path:
			request = requests.get(path, auth=HTTPBasicAuth('okeechobee', 'cleanwater'), stream=True)
			file = request.raw
		else:	
			file = path
		return load_csv(path, date_vars=date_vars)

	elif type(path) is list:
		li = []
		for f in path:
			df = load_csv(f, date_vars=date_vars)
			li.append(df)
		df = pd.concat(li, axis=0, ignore_index=True)
	
	df['local time'] = df['GPSTimeStamp'].dt.tz_localize('utc').dt.tz_convert(eastern)

	return df

def select_times(df, start_date=False, end_date=False):
	if start_date:
		start_date_val = check_date_frmt(start_date)
		df = df[df['local time']>=start_date_val]
	if end_date:
		end_date_val = heck_date_frmt(end_date)
		df = df[df['local time']<=end_date_val]
	return df

def check_date_frmt(date_str):
	try:
		date = datetime.strptime(date_str, '%Y-%m-%d').tz_localize(eastern)
		return date
	except:
		raise ValueError('date must be string YYYY-mm-dd')
		return

def check_name(name):

	variable_to_column_name = {'time' : 'GPSTimeStamp', 'lon': 'Lon', 'lat': 'Lat',
	                        'speed': 'Speed', 'track': 'Track', 'heading': 'Heading', 
	                        'pitch': 'Pitch', 'roll': ' Roll',
	                        'wind speed': 'WindTrueSpeed', 'wind dir': 'WindTrueDir',
	                        'pressure': 'PressureInches', 'air temp': 'AirTemp', 
	                        'bb3 time': 'BB3 [Time UTC]',
	                        'bb470 counts': 'Bb(470) [counts]', 
	                        'bb532 counts': 'Bb(532) [counts]',
	                        'bb650  counts':'Bb(650) [counts]',
	                        'bb470': 'Bb(470) [NTU]',
	                        'bb532': 'Bb(532) [NTU]',
	                        'bb650': 'Bb(650) [NTU]', 
	                        'ci time': 'CI [Time UTC]',
	                        'chla counts': 'Chl. a [counts]',
	                        'cdom counts': 'CDOM [counts]',
	                        'phyco counts': 'Phycocyanin [counts]',
	                        'chla': 'Chl. a [ppb]',
	                        'cdom': 'CDOM [QSU]',
	                        'phyco': 'Phycocyanin [ppb]',
	                        'ct time': 'CT [Time UTC]',
	                        'cond': 'Conductivity [mS cm-1]',
	                        'temp': 'Temperature [deg C]',
	                        'O2 time': 'O2 [Time UTC]',
	                        'O2':'O2 Concentration [micromolar]',
	                        'O2 sat':'O2 Saturation [%]',
	                        'O2 temp': 'O2 Temperature [deg C]',
	                       }
	if name in variable_to_column_name.keys():
		return variable_to_column_name[name]
	else:
		return name


def scatter(df, x_var, y_var, z_var='bb470',cmap='jet',
	start_date=False, end_date=False, **kwargs):
	x_name = check_name(x_var)
	y_name = check_name(y_var)

	if z_var:
		z_name = check_name(z_var)
	else:
		z_name = None
	
	if any([start_date, end_date]):
		df = select_times(start_date=start_date, end_date=end_date)

	df.plot.scatter(x_name, y_name, c=z_name, cmap=cmap, **kwargs)


def background(extent = [-81.15, -80.51,26.65, 27.24],
			request = cimgt.GoogleTiles(style='satellite'),
			ax=None,  projection=None, out = False):
	# Plots lake O background map

	if request is None:
		projection = projection
		image = False
	else:
		projection = request.crs
		image = True

	if ax is None:
		fig = plt.figure(figsize=(10, 10))
		ax = plt.axes(projection=projection)

	ax.set_extent(extent)

	try:
		gl = ax.gridlines(draw_labels=True, alpha=0.2)
		gl.xlabels_top = gl.ylabels_right = False
		gl.xformatter = LONGITUDE_FORMATTER
		gl.yformatter = LATITUDE_FORMATTER    
	except:
		print('Projection does not allow gridlines')

	if image:
		ax.add_image(request, 10)

	if out is True:
		return fig, ax


def plot_path(df, var, start_date=False, end_date=False, ax=None, colorbar=True, **kwargs,): 

	var_column_name = check_name(var)

	if any([start_date, end_date]):
		df = select_times(df, start_date=start_date, end_date=end_date)

	if ax is None:
		fig, ax = background(out=True,)

	mapp = ax.scatter(df['Lon'], df['Lat'], c=df[var_column_name],
		transform=ccrs.PlateCarree(), **kwargs)
	if colorbar:
		plt.colorbar(mapp, label=var_column_name)

	return mapp

