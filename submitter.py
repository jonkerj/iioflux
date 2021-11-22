import argparse
import datetime
import logging
import os
import os.path
import signal
import sys
import time

import iio
import environ

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import yaml

def convLoglevel(s):
	levels = ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG']

	if not s in levels:
			raise ValueError(f'{s} is not a valid log level. Valid are {"".join(choices)}')

	return s

def convertSensorconfig(s):
	if not os.path.exists(s):
		raise ValueError(f'Sensor config file "{s}" does not exist')

	with open(s, 'r') as f:
		sensorconfig = yaml.safe_load(f)
	
	if not 'hosts' in sensorconfig:
		raise ValueError('Sensor config does not contain "hosts" key')
	
	return sensorconfig

class IIOSubmitter(object):
	def match_device(self, match):
		for d in self.context.devices:
			matched = True
			for k, v in match.items():
				if not hasattr(d, k):
					matched = False
					break
				if not getattr(d, k) == v:
					matched = False
					break
			if matched:
				return d
		return None

	def __init__(self, remote_config, write_api, config, logger):
		self.name = remote_config['name']
		self.logger = logger.getChild(self.name)
		self.logger.info('Creating IIOSubmitter object')
		self.config = config
		self.write_api = write_api
		self.context = iio.Context(remote_config['uri'])
		self.devices = {}

		for device in remote_config['devices']:
			d = self.match_device(device['match'])
			if d:
				self.devices[device['name']] = d
		self.logger.info(f'Loaded devices: {",".join(self.devices.keys())}')

	def measurements(self):
		self.logger.info(f'Polling new measurements')
		ops = [
			('raw', lambda c, v: v),
			('input', lambda c, v: v),
			('offset', lambda c, v: c + v),
			('scale', lambda c, v: c * v)
		]
		zone = datetime.datetime.now(datetime.timezone.utc).astimezone()
		t = datetime.datetime.now().replace(tzinfo=zone.tzinfo)
		for name, device in self.devices.items():
			point = Point(name).time(t).tag('host', self.name)
			for channel in device.channels:
				c = 0
				for key, func in ops:
					if key in channel.attrs:
						c = func(c, float(channel.attrs[key].value))
				self.logger.debug(f'Making a field: {channel.id}={c}')
				point.field(channel.id, c)
			yield point
	
	def tick(self):
		for p in self.measurements():
			self.write_api.write(bucket=self.config.influxdb_bucket, record=p)

class SignalHandler(object):
	def __init__(self, logger):
		self.stop = False
		self.logger = logger.getChild('signalhandler')
		signal.signal(signal.SIGINT, self.exit_gracefully)
		signal.signal(signal.SIGTERM, self.exit_gracefully)
		self.logger.info(f'Signal handler installed')
	
	def exit_gracefully(self, signum, frame):
		self.logger.info(f'Signal {signum} caught, scheduling a stop')
		self.stop = True
	
	def sleep(self, t):
		t0 = time.time()
		self.logger.debug(f'Sleeping {t}s')
		while not self.stop and (time.time() - t0) < t:
			time.sleep(1)

@environ.config(prefix="IIO")
class Config:
	loglevel = environ.var('INFO', converter=convLoglevel)
	sensorconfig = environ.var(converter=convertSensorconfig)
	influxdb_bucket = environ.var('solar', name='INFLUXDB_V2_BUCKET')

def main(config):
	logger = logging.getLogger("iioflux")
	logging.basicConfig(format='%(asctime)s %(levelname)s:%(name)s - %(message)s', datefmt='%H:%M:%S', level=config.loglevel)
	logger.info(f'Connecting to InfluxDB')
	idb = InfluxDBClient.from_env_properties()
	write_api = idb.write_api(write_options=SYNCHRONOUS)

	bucket = config.influxdb_bucket

	submitters = [IIOSubmitter(host, write_api, config, logger) for host in config.sensorconfig['hosts']]
	
	logger.info(f'Ready for action')
	
	handler = SignalHandler(logger)
	while not handler.stop:
		for submitter in submitters:
			submitter.tick()
			write_api.write(bucket = bucket, record = [p.tag('host', submitter.name) for p in submitter.measurements()])
		handler.sleep(60)
	logger.info(f'Quitting')

if __name__ == '__main__':
	config = Config.from_environ()
	main(config)