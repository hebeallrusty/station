import pyowm
import configparser
import os
from Bearing import Bearing # converts compass point to bearing such as SW or NE
from app.modules.Database.DBUtils import *
import json
import time

CWD = os.getcwd()

# Config file location has to be static
KEY_FILE=''.join([CWD,'/config/key.ini'])
CONFIG_FILE=''.join([CWD,'/config/config.ini'])

config = configparser.ConfigParser()
config._interpolation = configparser.ExtendedInterpolation()

# get api key from file
config.read(KEY_FILE)

# INI format is as follows:
# [OpenWeatherMap]
# API_Key=**api key**
OWM_Key=config.get('OpenWeatherMap','API_Key')

# read config file
config.read(CONFIG_FILE)

DATABASE = ''.join([CWD,config.get('files','WeatherDatabase')])
FORECAST_JSON = ''.join([CWD,config.get('files','ForecastJSON')])

UPDATE_INTERVAL = int(config.get('general','UpdateInterval'))


#get longitude and latitude from config file and convert to floats as required by owm
Longitude = float(config.get('location','Longitude'))
Latitude = float(config.get('location','Latitude'))


# start loop

var = 1
while var > 0:
	# set object as call on OWM with user api key
	print("entering API key")
	owm = pyowm.OWM(OWM_Key)
	print("Key entered")

	# get observation at coords saved in config file.
	observation = owm.weather_at_coords(Latitude,Longitude)

	# get current weather and allow object to be interrogated for conditions
	w = observation.get_weather()

	# get uv data
	uv = owm.uvindex_around_coords(Latitude,Longitude)

	# put current conditions into variables for use later
	ConditionsAt = w.get_reference_time('iso')
	CurrentConditions = w.get_detailed_status()
	Temperature = w.get_temperature('celsius')['temp']
	Humidity = w.get_humidity()
	UVIndex = uv.get_value()
	Wind = w.get_wind(unit='miles_hour')
	# convert Wind Speed from m/s to mph
	WindSpeed = Wind['speed']
	print(WindSpeed)
	# convert Wind direction to compass point
	WindDirection = int(Wind['deg'])
	WindBearing = Bearing(WindDirection)
	Clouds = w.get_clouds()
	Rain = w.get_rain()
	print(Clouds)
	print(Rain)

	# create dict object with all conditions for exporting to JSON file
	#CurrentWeather = {'At':ConditionsAt,'Current':CurrentConditions,'Temperature':Temperature,'Humidity':Humidity,'UV':UVIndex,'WindSpeed':WindSpeed,'WindBearing':WindBearing,'CloudCover':Clouds,'Rain':Rain}
	# print(CurrentWeather)

	# insert values into database
	db = db_connect(DATABASE)
	insert_weather(db,'Current',float(Temperature), float(Humidity), 0, CurrentConditions, WindSpeed, WindBearing,UVIndex)
	db.commit()
	db.close

	# create a forecast object with observations at 3hr intervals
	fc = owm.three_hours_forecast_at_coords(Latitude,Longitude)
	# print(forecast)

	# create object of weathers. To be enumerated through each of the 3hr intervals
	f = fc.get_forecast()
	# print(f.get_weathers())


	# open up database for dumping in the data
	# database should have following fields (in order)
	# KEY,date/time,Status,Temperature,Humidity,Wind

	# enumerate through the list of weathers to pick out the forecast element
	n = 0
	ForecastWeather = {}
	for x in f:	
		ForecastWeather[n] = []

		# make adjustments for the wind
		fcWind = x.get_wind(unit='miles_hour')
		fcWindSpeed = fcWind['speed']
		fcWindBearing = Bearing(int(fcWind['deg']))
		ForecastWeather[n].append({'Time':x.get_reference_time('iso'), 'Condition':x.get_detailed_status(), 'Temperature':x.get_temperature('celsius')['temp'], 'Humidity':x.get_humidity(), 'WindSpeed':fcWindSpeed,'WindBearing':fcWindBearing})

		# Advance counter on by one	
		n = n + 1

	# write current conditions to JSON file
	with open(FORECAST_JSON,'w') as outfile:
		json.dump(ForecastWeather,outfile)


	# print(ForecastWeather[2])

	# sleep before re-running the script
	time.sleep(UPDATE_INTERVAL)
