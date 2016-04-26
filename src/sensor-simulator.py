#!/usr/bin/env python

# Copyright 2016 Telefonica Soluciones, S.A.U
# Developed by Alvaro Sainz-Pardo (@asainzp), Mar 2016.

import ConfigParser
from datetime import datetime
from __future__ import division
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

			# Moving sensor with GPS coordinates
			elif measure[method'] in ['gps_line', 'gps_pol', 'gps_polygon']:

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
