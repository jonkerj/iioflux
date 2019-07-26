import argparse
import datetime
import logging
import os
import os.path
import signal
import sys
import time
import influxdb
import iio
import yaml

logging.basicConfig(
	format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
	level=logging.INFO,
	datefmt="%H:%M:%S",
	stream=sys.stderr,
)
logger = logging.getLogger("iio-influx")

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

	def __init__(self, config, influx_client):
		self.name = config['name']
		self.logger = logger.getChild(self.name)
		self.logger.info('Creating IIOSubmitter object')
		self.context = iio.Context(config['uri'])
		self.devices = {}
		self.idb = influx_client

		for device in config['devices']:
			d = self.match_device(device['match'])
			if d:
				self.devices[device['name']] = d
		self.logger.info(f'Loaded devices {",".join(self.devices.keys())}')

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
			point = {
				'measurement': name,
				'time': t,
				'fields': {},
			}
			for channel in device.channels:
				c = 0
				for key, func in ops:
					if key in channel.attrs:
						c = func(c, float(channel.attrs[key].value))
				point['fields'][channel.id] = c
			yield point

class SignalHandler(object):
	def __init__(self):
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
		while not self.stop and (time.time() - t0) < t:
			time.sleep(1)

def main(config):
	logger.info(f'Connecting to InfluxDB')
	idb = influxdb.InfluxDBClient(**config['influxdb']['connection'])
	submitters = [IIOSubmitter(host, idb) for host in config['hosts']]
	logger.info(f'Ready for action')
	handler = SignalHandler()
	while not handler.stop:
		for submitter in submitters:
			idb.write_points(tags={'host': submitter.name}, points=list(submitter.measurements()))
		handler.sleep(60)
	logger.info(f'Quitting')

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config', required=True, dest='config', help='Config file to use')
	parser.add_argument('-s', '--secrets', required=True, dest='secrets', help='Path to mounted secrets')
	args = parser.parse_args()

	assert os.path.exists(args.config), f'configfile ({args.config}) does not exist'
	config = yaml.load(open(args.config, 'r'))
	for key in ['hosts', 'influxdb']:
		assert key in config, f'Configuration does not have "{key}" section'
	
	assert os.path.exists(args.secrets), f'secrets dir ({args.secrets}) does not exist'
	assert os.path.isdir(args.secrets), f'secrets path ({args.secrets}) is not a directory'
	
	# merge secret values (eg: influxdb.connection.username) into config hash
	for key in os.listdir(args.secrets):
		if key.startswith('..'):
			continue
		logger.debug(f'merging {key}')
		parts = key.split('.')
		current = config
		for k in parts[:-1]:
			current = current[k]
		current[parts[-1]] = open(os.path.join(args.secrets, key), 'r').read().strip()
	
	main(config)
