#!/usr/bin/env python

# Copyright 2016 Telefonica Soluciones, S.A.U
# Developed by Alvaro Sainz-Pardo (@asainzp), Mar 2016.

import requests
import sys
import ConfigParser
from threading import Timer
import datetime
import random

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
				measure['value'] = datetime.datetime.now().isoformat()
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
			elif measure['method'] in ['incrandint', 'increment_randint', 'increment_random_int']:
				measure['value'] += random.randint(measure['from'], measure['to'])
			elif measure['method'] in ['incrandfloat', 'increment_randfloat', 'increment_random_float']:
				measure['value'] += float('{0:.2f}'.format(random.uniform(measure['from'], measure['to'])))
			elif measure['method'] in ['cyclerandint', 'cycle_randint', 'cycle_random_int']:
				measure['value'] += random.randint(0, measure['by'])
				if measure['value'] > measure['to']:
					measure['value'] = measure['from']
			elif measure['method'] in ['cyclerandfloat', 'cycle_randfloat', 'cycle_random_float']:
				measure['value'] += float('{0:.2f}'.format(random.uniform(0, measure['by'])))
				if measure['value'] > measure['to']:
					measure['value'] = measure['from']
			elif measure['method'] in ['dayint', 'day_int']:
				measure['value']
			# Special method for specific types of sensors

			# Streetline parking sensor
			elif measure['method'] in ['streetline_state', 'parking_state']:
				measure['value'] = random.choice(measure['values'])
				if measure['value'] == 'OCCUPIED':
					_streetline_availability = 0
				else:
					_streetline_availability = 1
			elif measure['method'] in ['streetline_availability', 'parking_availabiliy']:
				measure['value'] = _streetline_availability

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
#		print str(r.status_code) + r.text
	
	def _run(self):
		self.runtime += self.timeout
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
			if measure['method'] in ['dayint', 'day_int']:
				for datapoint in measure['datapoints']:
					print datapoint
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

for sensor_id in config.sections():
	if sensor_id not in ['idas', 'sensor_defaults', 'data']:
		sensor_list.append(Sensor(sensor_id))
	
for sensor in sensor_list:
	sensor.configure(config)
	sensor.turnon()
