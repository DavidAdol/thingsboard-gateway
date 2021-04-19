# To specifically ignore ConvergenceWarnings:
import warnings

from scipy.stats import zscore
from collections import defaultdict
from functools import partial
from json import load
from os import path
import numpy as np
from statsmodels.tools.sm_exceptions import ConvergenceWarning
warnings.simplefilter('ignore', ConvergenceWarning)

# time series - statsmodels
# Seasonality decomposition
from statsmodels.tsa.seasonal import seasonal_decompose

# holt winters
# single exponential smoothing
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

# double and triple exponential smoothing
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from tsmoothie import ExponentialSmoother


import threading
from time import sleep


import logging
import logging.config
import logging.handlers

log = logging.getLogger('service')


class DataCleaning:

	log = logging.getLogger('service')

	indexOfDeviceName = 0
	indexOfSensorName = 1
	indexOfTelemetry = 2
	indexOfTimeSeries = 3
	indexOfSeries = 4
	obviousOutlier = 999999

	cleaningConfig = None

	def __init__(self):
		t = threading.Thread(target=self.get_cleaning_config)
		t.start()
		print("thread started")

	def createDevice(self, deviceList, data):	
		try:
			#self.get_cleaning_config()
			newDeviceQueue = []
			for telemetry in data["telemetry"]["values"]:
				newDeviceQueue.append(self.getTelemetryData(data, telemetry))
			return newDeviceQueue
		except Exception as e:
			log.exception(e)
		
	def doesDeviceExist(self, deviceList, data):
		try:
			index = -1
			for i in range(len(deviceList)):
				if data["deviceName"] == deviceList[i][0][self.indexOfDeviceName]:
					index = i
			return index																		# return -1 if device does not exist
		except Exception as e:
			log.exception(e)

	def getTelemetryData(self, data, telemetry):
		try:
			#print("adding device")
			deviceArray = []
			telemetryArray = []
			timeseriesArray = []

			deviceArray.append(data["deviceName"])
			deviceArray.append(telemetry)

			telemetryArray.append(self.check_type(data["telemetry"]["values"][telemetry]))		# return obvious deviation if data point is NaN
			timeseriesArray.append(data["telemetry"]["ts"])

			series = defaultdict(partial(np.ndarray, shape=(1, 1), dtype='float32'))

			deviceArray.append(telemetryArray)
			deviceArray.append(timeseriesArray)
			deviceArray.append(series)

			return deviceArray
		except Exception as e:
			log.exception(e)

	def addTelemetry(self, deviceList, data, deviceIndex):
		try:
			i = 0
			cleaning_array_length = 20
			window_len = 20
			time_series_length = len(deviceList[deviceIndex][i][self.indexOfTelemetry])

			# controls size of list
			if (time_series_length >= cleaning_array_length):
				self.removeFirstElements(deviceList, deviceIndex)

			for telemetry in data["telemetry"]["values"]:
				series = deviceList[deviceIndex][i][self.indexOfSeries]

				# Control data type for observed value.
				data_point = self.check_type(data["telemetry"]["values"][telemetry])

				cleaningMethod, window_len = self.get_cleaning_method(deviceList, deviceIndex, telemetry)

				#TODO: get window_len and other params from config

				# begin cleaning when length is bigger than...
				if (len(deviceList[deviceIndex][i][self.indexOfTelemetry]) > window_len):

					if(cleaningMethod == "holt_winters"):
						pass

					if True:
						data_point = self._exponentialSmoother(data_point, series, window_len)

				series['original'] = np.insert(series['original'], series['original'].size, [[data_point]])

				if series['original'].size > window_len * 2:
					series['original'] = series['original'][series['original'].size - window_len * 2:]

				# No cleaning if length to short, just add data point
				deviceList[deviceIndex][i][self.indexOfTelemetry].append(data_point)
				deviceList[deviceIndex][i][self.indexOfTimeSeries].append(data["telemetry"]["ts"])  # adding timeseries

				i += 1
		except Exception as e:
			log.exception(e)
	
	def removeFirstElements(self, deviceList, deviceIndex):
		try:
			for i in range(len(deviceList[deviceIndex])):
				deviceList[deviceIndex][i][self.indexOfTelemetry].pop(0)
				deviceList[deviceIndex][i][self.indexOfTimeSeries].pop(0)
		except Exception as e:
			log.exception(e)


	def check_type(self, data_point):
		if isinstance(data_point, str):
			if data_point == "NaN":
				return self.obviousOutlier
			else:
				return float(data_point)
		else:
			return data_point

	def get_cleaning_config(self):
		try:
			config_file = path.abspath("thingsboard_gateway/config/cleaning.json")
			with open(config_file) as conf:
				self.cleaningConfig = load(conf)
		except Exception as e:
			log.exception(e)
		print("updated config-files")
		sleep(60)
		self.get_cleaning_config()
	
	def check_if_cleaning_is_specified_for_all(self, deviceList):
		try:
			i = 0
			for mpoint in deviceList:
				j = 0
				for attribute in deviceList[i][0]:
					if(isinstance(attribute, str) and j == 0):
						#print(attribute)
						if(not self.check_if_cleaning_is_specified(attribute)):
							exceptionString = "cleaning.json does does not specify cleaning for the endpoint " + attribute
							log.exception(exceptionString)
					j += 1
				i += 1
		except Exception as e:
			log.exception(e)

	def check_if_cleaning_is_specified(self, attribute):
		try:
			i = 0
			for mpoint in self.cleaningConfig["devicesWithCleaning"]:
				if(self.cleaningConfig["devicesWithCleaning"][i]["datatypeName"] != ""):
					nameOfDevice = self.cleaningConfig["devicesWithCleaning"][i]["mpointName"] + ", " + self.cleaningConfig["devicesWithCleaning"][i]["datatypeName"]
				else:
					nameOfDevice = self.cleaningConfig["devicesWithCleaning"][i]["mpointName"]
				if(nameOfDevice == attribute):
					return True

				i += 1
			return False
		except Exception as e:
			log.exception(e)
	
	def get_cleaning_method(self, deviceList, deviceIndex, telemetry):
		try:
			deviceNameToCheck = deviceList[deviceIndex][0][self.indexOfDeviceName]

			i = 0
			for mpoint in self.cleaningConfig["devicesWithCleaning"]:
				if(self.cleaningConfig["devicesWithCleaning"][i]["datatypeName"] != ""):
					nameOfDevice = self.cleaningConfig["devicesWithCleaning"][i]["mpointName"] + ", " + self.cleaningConfig["devicesWithCleaning"][i]["datatypeName"]
				else:
					nameOfDevice = self.cleaningConfig["devicesWithCleaning"][i]["mpointName"]
				if(nameOfDevice == deviceNameToCheck):
					j = 0
					for specificCleaning in self.cleaningConfig["devicesWithCleaning"][i]["sensorsWithSpecificCleaning"]:
						if(telemetry == specificCleaning["sensorName"]):
							return specificCleaning["cleaningMethod"], specificCleaning["windowLen"]
						j += 1
				i += 1
			return self.cleaningConfig["devicesWithCleaning"][deviceIndex]["defaultCleaning"], self.cleaningConfig["devicesWithCleaning"][deviceIndex]["defaultWindowLen"]
		except Exception as e:
			log.exception(e)


	def _exponentialSmoother(self, data_point, series, window_len):
		smoother = ExponentialSmoother(window_len=window_len // 2, alpha=0.4)
		smoother.smooth(series['original'][-window_len:])

		series['smooth'] = np.insert(series['smooth'], series['smooth'].size, smoother.smooth_data[-1][-1])

		_low, _up = smoother.get_intervals('sigma_interval', n_sigma=5)
		series['low'] = np.insert(series['low'], series['low'].size, _low[-1][-1])
		series['up'] = np.insert(series['up'], series['up'].size, _up[-1][-1])

		is_anomaly = np.logical_or(
			series['original'][-1] > series['up'][-1],
			series['original'][-1] < series['low'][-1]
		).reshape(-1, 1)

		if is_anomaly.any():
			if series['original'][-1] > series['up'][-1]:
				data_point = series['up'][-1]
			elif series['original'][-1] < series['low'][-1]:
				data_point = series['low'][-1]
			print("ANOMALY DETECTED: ", round(data_point, 4))

		if series['smooth'].size > window_len:
			series['smooth'] = series['smooth'][series['smooth'].size - window_len:]
			series['low'] = series['low'][series['low'].size - window_len:]
			series['up'] = series['up'][series['up'].size - window_len:]

		return data_point
