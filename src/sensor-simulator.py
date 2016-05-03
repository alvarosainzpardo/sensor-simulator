#!/usr/bin/env python

# Copyright 2016 Telefonica Soluciones, S.A.U
# Developed by Alvaro Sainz-Pardo (@asainzp), Mar 2016.

from __future__ import division
import ConfigParser
from datetime import datetime
import json
from math import cos, sin, asin, sqrt, radians
import random
import requests
import sys
from threading import Timer

class Sensor:
	def __init__(self, id):
		self._ready = False
		self.is_on = False
		self.id = id
		self._timer = None
		self.timeout = None
		self.runtime = None
		self.host = None
		self.port = None
		self.apikey = None
		self.measures = None

	def _new_measures(self):
		_streetline_availability = 0

		for measure in self.measures:
			if measure['method'] in ['datetime', 'time']:
				measure['value'] = self.now.isoformat()
			if measure['method'] in ['sequence', 'seq']:
				measure['value'] += 1
			elif measure['method'] in ['increment', 'inc', 'incr']:
				measure['value'] += measure['by']
			elif measure['method'] in ['counter', 'count']:
				measure['value'] += measure['by']
				if measure['value'] > measure['to']:
					measure['value'] = measure['from']
			elif measure['method'] in ['randint', 'random_int']:
				measure['value'] = random.randint(measure['from'], measure['to'])
			elif measure['method'] in ['randfloat', 'rand_float', 'random_float']:
				measure['value'] = float('{0:.2f}'.format(random.uniform(measure['from'], measure['to'])))
			elif measure['method'] in ['randval', 'randomval', 'random_val', 'random_value']:
				measure['value'] = random.choice(measure['values'])
			elif measure['method'] in ['listval', 'list_val']:
				index = measure['index']
				if index < len(measure['values']) - 1:
					index += 1
				measure['index'] = index
				measure['value'] = measure['values'][index]
			elif measure['method'] in ['incrandint', 'increment_randint', 'increment_random_int']:
				measure['value'] += random.randint(measure['from'], measure['to'])
			elif measure['method'] in ['incrandfloat', 'increment_randfloat', 'increment_random_float']:
				measure['value'] += float('{0:.2f}'.format(random.uniform(measure['from'], measure['to'])))
			elif measure['method'] in ['cyclerandint', 'cycle_randint', 'cycle_rand_int', 'cycle_random_int']:
				measure['value'] += random.randint(0, measure['by'])
				if measure['value'] > measure['to']:
					measure['value'] = measure['from']
			elif measure['method'] in ['cyclerandfloat', 'cycle_randfloat', 'cycle_rand_float', 'cycle_random_float']:
				measure['value'] += float('{0:.2f}'.format(random.uniform(0, measure['by'])))
				if measure['value'] > measure['to']:
					measure['value'] = measure['from']
      # Time sequence : a sequence of datetime instants with value
			elif measure['method'] in ['timeseqint', 'timeseq_int', 'time_seq_int',
										'timeseqfloat', 'timeseq_float', 'time_seq_float']:
				index = 0
				datapoints = measure['datapoints']
				if self.now <= datapoints[0]['datetime']:
					_tmp_value = datapoints[0]['value']
					value = float('{0:.2f}'.format(_tmp_value + random.uniform(-_tmp_value/40, _tmp_value/40)))
				elif self.now >= datapoints[-1]['datetime']:
					_tmp_value = datapoints[-1]['value']
					value = float('{0:.2f}'.format(_tmp_value + random.uniform(-_tmp_value/40, _tmp_value/40)))
				else:
					while datapoints[index]['datetime'] < self.now:
						index += 1
					value_delta = float(datapoints[index]['value'] - datapoints[index-1]['value'])
					time_delta = datapoints[index]['datetime'] - datapoints[index-1]['datetime']
					seconds_delta_period = time_delta.days*86400 + time_delta.seconds + time_delta.microseconds/1000000
					time_delta = self.now - datapoints[index-1]['datetime']
					seconds_delta_now = time_delta.days*86400 + time_delta.seconds + time_delta.microseconds/1000000
					delta = (value_delta / seconds_delta_period) * seconds_delta_now
					value = float('{0:.2f}'.format(datapoints[index-1]['value'] + delta))
					# Add some random noise (+-5%)
					value = float('{0:.2f}'.format(value + random.uniform(-value/40, value/40)))
        # We round to int only for int type sensor measure
				if measure['method'] in ['timeseqint', 'timeseq_int', 'time_seq_int']:
					measure['value'] = int(round(value))
				else:
					measure['value'] = value
      # Day sequence : a sequence of time instants with value that repeats each day
			elif measure['method'] in ['dayseqfloat', 'dayseq_float', 'day_seq_float',
									'dayseqint', 'dayseq_int', 'day_seq_int']:
				index = 0
				datapoints = measure['datapoints']
				if self.now.time() <= datapoints[0]['time']:
					_tmp_value = datapoints[0]['value']
					value = float('{0:.2f}'.format(_tmp_value + random.uniform(-_tmp_value/40, _tmp_value/40)))
				elif self.now.time() >= datapoints[-1]['time']:
					_tmp_value = datapoints[-1]['value']
					value = float('{0:.2f}'.format(_tmp_value + random.uniform(-_tmp_value/40, _tmp_value/40)))
				else:
					while datapoints[index]['time'] < self.now.time():
						index += 1
					value_delta = float(datapoints[index]['value'] - datapoints[index-1]['value'])
					seconds_delta_period = time_in_seconds(datapoints[index]['time']) - time_in_seconds(datapoints[index-1]['time'])
					seconds_delta_now = time_in_seconds(self.now.time()) - time_in_seconds(datapoints[index-1]['time'])
					delta = (value_delta / seconds_delta_period) * seconds_delta_now
					value = float('{0:.2f}'.format(datapoints[index-1]['value'] + delta))
					# Add some random noise (+-5%)
					value = float('{0:.2f}'.format(value + random.uniform(-value/40, value/40)))
        # We round to int only for int type sensor measure
				if measure['method'] in ['dayseqint', 'dayseq_int', 'day_seq_int']:
					measure['value'] = int(round(value))
				else:
					measure['value'] = value

			# Special method for specific types of sensors

			# Moving sensor with GPS coordinates along a line of GPS points
			elif measure['method'] in ['gps_line']:
				index = measure['index']
				# We have not reached the end of the list of gps points
				if index < len(measure['gpspoints']) - 1:
					lat1 = float(measure['value'].split(',')[0].strip())
					lon1 = float(measure['value'].split(',')[1].strip())
					lat2 = float(measure['gpspoints'][index+1].split(',')[0].strip())
					lon2 = float(measure['gpspoints'][index+1].split(',')[1].strip())
					# radius of the Earth in meters
					R = 6371000
					# convert decimal degrees to radians
					rlat1, rlon1, rlat2, rlon2 = map(radians, [lat1, lon1, lat2, lon2])
    			# haversine formula
					dlon = rlon2 - rlon1
					dlat = rlat2 - rlat1
					a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
					c = 2 * asin(sqrt(a))
					# distance between points using haversine formula
					distance_to_next_point = R * c
					# distance run with _velocity in timeout time
					distance_run = ((_velocity * 1000) / 3600) * self.timeout
					# if the moving thing with _velocity moves farther than next point
					# in timeout time
					if distance_run >= distance_to_next_point:
						# move the thin directly to the next point
						# and advance the index
						index += 1
						measure['index'] = index
						measure['value'] = measure['gpspoints'][index]
					else:
						dlat = lat2 - lat1
						dlon = lon2 - lon1
						ratio_run = distance_run / distance_to_next_point
						inclat = dlat * ratio_run
						inclon = dlon * ratio_run
						measure['value'] = '{0:.6f},{1:.6f}'.format(lat1+inclat, lon1+inclon)

			# Moving sensor with GPS coordinates along a polygon of GPS points
			elif measure['method'] in ['gps_pol', 'gps_polygon']:
				index = measure['index']
				lat1 = float(measure['value'].split(',')[0].strip())
				lon1 = float(measure['value'].split(',')[1].strip())
				# We have not reached the end of the list of gps points
				if index < len(measure['gpspoints']) - 1:
					lat2 = float(measure['gpspoints'][index+1].split(',')[0].strip())
					lon2 = float(measure['gpspoints'][index+1].split(',')[1].strip())
				# End of list: next element is first
				else:
					lat2 = float(measure['gpspoints'][0].split(',')[0].strip())
					lon2 = float(measure['gpspoints'][0].split(',')[1].strip())
				# radius of the Earth in meters
				R = 6371000
				# convert decimal degrees to radians
				rlat1, rlon1, rlat2, rlon2 = map(radians, [lat1, lon1, lat2, lon2])
    		# haversine formula
				dlon = rlon2 - rlon1
				dlat = rlat2 - rlat1
				a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
				c = 2 * asin(sqrt(a))
				# distance between points using haversine formula
				distance_to_next_point = R * c
				# distance run with _velocity in timeout time
				distance_run = ((_velocity * 1000) / 3600) * self.timeout
				# if the moving thing with _velocity moves farther than next point
				# in timeout time
				if distance_run >= distance_to_next_point:
					# move the thin directly to the next point
					# and advance the index
					# taking into account if we are or not at the end of the list
					if index < len(measure['gpspoints']) - 1:
						index += 1
					else:
						index = 0
					measure['index'] = index
					measure['value'] = measure['gpspoints'][index]
				else:
					dlat = lat2 - lat1
					dlon = lon2 - lon1
					ratio_run = distance_run / distance_to_next_point
					inclat = dlat * ratio_run
					inclon = dlon * ratio_run
					measure['value'] = '{0:.6f},{1:.6f}'.format(lat1+inclat, lon1+inclon)
#				print 'coche: ', self.id, ' index: ', measure['index'],' coords: ', measure['value']

			# Streetline parking sensor
			elif measure['method'] in ['streetline_state', 'parking_state']:
				measure['value'] = random.choice(measure['values'])
				if measure['value'] == 'OCCUPIED':
					_streetline_availability = 0
				else:
					_streetline_availability = 1
			elif measure['method'] in ['streetline_availability', 'parking_availabiliy']:
				measure['value'] = _streetline_availability

			# We store the velocity of moving objetcs
			if measure['name'] in ['vel', 'velocity', 'velocidad']:
				_velocity = measure['value']

	def _send_measures(self):
		url = 'http://'+self.host+':'+self.port+'/iot/d?k='+self.apikey+'&i='+self.id
		payload = ''
		first_measure = True
		for measure in self.measures:
			if not first_measure:
				payload += '|'
			else:
				first_measure = False
			payload += measure['name'] + '|' + str(measure['value'])
		r = requests.post(url, data=payload, headers='')
#		print url
#		print payload
#		print str(r.status_code) + r.text

	def _run(self):
		self.runtime += self.timeout
		self.now = datetime.now()
		self._new_measures()
		self._send_measures()

	def _runtimer(self):
		self._timer = Timer(self.timeout, self._runtimer)
		self._timer.start()
		self._run()

	def configure(self, config):
		self.host = get_sensor_option(config, self.id, 'host')
		self.port = get_sensor_option(config, self.id, 'port')
		self.apikey = get_sensor_option(config, self.id, 'apikey')
		self.timeout = eval(get_sensor_option(config, self.id, 'timeout'))
		self.measures = eval(get_sensor_option(config, self.id, 'measures'))
		for measure in self.measures:
			if measure['method'] in ['listval', 'list_val']:
				measure['index'] = -1
			if measure['method'] in ['timeseqfloat', 'timeseq_float', 'time_seq_float',
									'timeseqint', 'timeseq_int', 'time_seq_int',
									'timeseqvalue', 'timeseq_value', 'time_seq_value']:
				measure['datapoints'] = eval(config.get('data', measure['datapoints']))
				for datapoint in measure['datapoints']:
					datapoint['datetime'] = datetime.strptime(datapoint['datetime'], '%Y-%m-%dT%H:%M:%S')
			if measure['method'] in ['dayseqfloat', 'dayseq_float', 'day_seq_float',
									'dayseqint', 'dayseq_int', 'day_seq_int',
									'dayseqvalue', 'dayseq_value', 'day_seq_value']:
				measure['datapoints'] = eval(config.get('data', measure['datapoints']))
				for datapoint in measure['datapoints']:
					datapoint['time'] = datetime.strptime(datapoint['time'], '%H:%M:%S').time()
			if measure['method'] in ['gps_line', 'gps_pol', 'gps_polygon']:
				measure['gpspoints'] = json.loads(config.get('data', measure['gpspoints']))
				measure['index'] = 0
				measure['value'] = measure['gpspoints'][0]
		self.runtime = 0
		self._ready = True

	def turnon(self):
		if self._ready and not self.is_on:
			self.is_on = True
			self._run()
			self._timer = Timer(self.timeout, self._runtimer)
			self._timer.start()

	def turnoff(self):
		self._timer.cancel()
		self.is_on = False

def time_in_seconds(time):
	return time.second + (time.minute*60) + (time.hour*3600) + (time.microsecond / 10**6)

def get_sensor_option(config, sensor_id, attribute):
	if config.has_option(sensor_id, attribute):
		option = config.get(sensor_id, attribute)
	elif config.has_option('idas', attribute):
		option = config.get('idas', attribute)
	elif config.has_option('sensor_defaults', attribute):
		option = config.get('sensor_defaults', attribute)
	else:
		option = None
	return option

# main program
if __name__ == '__main__':
	NUM_ARG=len(sys.argv)
	COMMAND=sys.argv[0]

	if NUM_ARG == 2:
		CONFIG_FILE = sys.argv[1]
	else:
		CONFIG_FILE = 'config.ini'

	# Load the configuration file
	with open(CONFIG_FILE,'r+') as f:
		config = ConfigParser.RawConfigParser(allow_no_value=True)
		config.readfp(f)
		f.close()

	random.seed()
	sensor_list = []

	# We create a sensor for every option which is not in 'idas', 'sensor_defaults' or 'data' sections
	for sensor_id in config.sections():
		if sensor_id not in ['idas', 'sensor_defaults', 'data']:
			sensor_list.append(Sensor(sensor_id))
	# We configure the sensors (and abort if there are syntax errors in config file)
	for sensor in sensor_list:
		sensor.configure(config)
	# Every sensor is well configured, so we turn on all of them
	for sensor in sensor_list:
		sensor.turnon()
