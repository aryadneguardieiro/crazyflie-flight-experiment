"""" 
Creates a  class that has three main functions. Each will run in a separated thread.
	1 - Sends information to the crazyflie, based on the paramters readed 
		(Base code - https://github.com/bitcraze/crazyflie-lib-python/blob/master/examples/ramp.py)
	2 - Prints the current value of the variables time elapsed, roll, pitch, yaw and thrust
	3 - Reads the values from the TOC table 
		(Base code - https://github.com/bitcraze/crazyflie-lib-python/blob/master/examples/basicparam.py)

Author: Aryadne Rezende - aryadneccomp@gmail.com
Date: May 15, 2016
Aedes Aegypti crazyflie research
"""
import logging
import time
from threading import Timer

from threading import Thread
import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
import cflib
from datetime import timedelta

#graphic 
import numpy as np 
import pylab as pl

class Control:
	def __init__(self, link_uri):
		self.nthrust = 0
		self.nroll = 0
		self.npitch = 0
		self.nyaw = 0
		self.init_time = 0
		self.time_elapsed = 0
		# to plot graphics
		self.thrust_v = [] 
		self.roll_v = [] 
		self.pitch_v = []
		self.yaw_v = []
		self.time_v = []
        # Create a Crazyflie object without specifying any cache dirs
		self._cf = Crazyflie()
 		
 		# Connect some callbacks from the Crazyflie API
		self._cf.connected.add_callback(self._connected)
		self._cf.disconnected.add_callback(self._disconnected)
		self._cf.connection_failed.add_callback(self._connection_failed)
		self._cf.connection_lost.add_callback(self._connection_lost)
        
		print('Connecting to %s' % link_uri)
 
        # Try to connect to the Crazyflie
		self._cf.open_link(link_uri)
		self.is_connected = True

	""" This callback is called form the Crazyflie API when a Crazyflie
	has been connected and the TOCs have been downloaded."""
	"""Callback when disconnected after a connection has been made (i.e
	Crazyflie moves out of range)"""
	def _connected(self, link_uri):

		#initial time to be shown in the screen
		self.init_time = time.time()

		#Threat 1 that will control the quadridrone
		Thread(target=self._ramp_motors).start() 
		
		#Thread 2 that will show results in the screen
		Thread(target=self._show_values).start() 


		self._lg_stab = LogConfig(name='Stabilizer', period_in_ms=30)
		#self._lg_stab.addVariable(LogVariable("stabilizer.thrust", "uint16_t"))
		self._lg_stab.add_variable('stabilizer.roll', 'float')
		self._lg_stab.add_variable('stabilizer.pitch', 'float')
		self._lg_stab.add_variable('stabilizer.yaw', 'float')
		self._lg_stab.add_variable('stabilizer.thrust', "uint16_t")

		# Adding the configuration cannot be done until a Crazyflie is
		# connected, since we need to check that the variables we
		# would like to log are in the TOC.
		try:
			self._cf.log.add_config(self._lg_stab)
			# This callback will receive the data
			self._lg_stab.data_received_cb.add_callback(self._stab_log_data)
			# This callback will be called on errors
			self._lg_stab.error_cb.add_callback(self._stab_log_error)
			#Thread 3 that will read from the TOC table, and start the logging
			self._lg_stab.start()
		except KeyError as e:
			print('Could not start log configuration, {} not found in TOC'.format(str(e)))
		except AttributeError:
			print('Could not add Stabilizer log config, bad configuration.')


	def _ramp_motors(self):
		thrust_step = 400
		self.nthrust = 37500
		#thrust = 30500
		self.npitch = 0.31
		self.nroll = 0.56
		yawrate = 0
		nthrust_mult = 1
		desired_roll = 1
		desired_thrust = 35000 #40300
		desired_pitch = 0.28
		#desired_yaw = 0
		gama = 0.3

		# Unlock startup thrust protection
		self._cf.commander.send_setpoint(0, 0, 0, 0)
        
		while (self.nthrust > 0) and (self.time_elapsed < 13):              			
			
		#	if self.time_elapsed > 8:
		#		 nthrust_mult = -1
			
			#self.nthrust = self.nthrust + (nthrust_mult * thrust_step)
			
			if (self.time_elapsed >= 4) and (self.time_elapsed < 8):
				desired_thrust = 20000#27400#32767

			if self.time_elapsed > 8:
				desired_thrust = 0
			
			st = self.nthrust
			delta_thrust = desired_thrust - st
			new_thrust = int(st + (delta_thrust*gama))

			sr = self.nroll
			delta_roll = desired_roll - sr
			new_roll = sr + (delta_roll*gama) 
			#new_roll = sr * (-0.8) + 2

			sp = self.npitch
			delta_pitch = desired_pitch - sp
			new_pitch = sp + (delta_pitch*gama)
			#new_pitch = sp * (-0.8) -2 
		
			self._cf.commander.send_setpoint(new_roll, new_pitch, yawrate, new_thrust) 
			time.sleep(0.05)                             
			
			#self._cf.param.set_value("flightmode.althold", "True") 
			#time.sleep(0.2)   

		self._cf.commander.send_setpoint(0, 0, 0, 0)
		print("Send point 0 0 0 0")
		time.sleep(0.1)
		self._cf.close_link()
		self.is_connected = False
		print("Connection closed")
		#pl.plot(self.time_v, self.thrust_v, 'b')
		#pl.plot(self.time_v, self.roll_v, 'r')
		#pl.plot(self.time_v, self.pitch_v, 'p')
		#pl.plot(self.time_v, self.yaw_v, 'y')
		#pl.show()#

	"""Show values like time, npitch, nyaw, nroll and nthrust from the class"""
	def _show_values(self):
		while(self.is_connected):        
			self.time_elapsed = time.time() - self.init_time 
			print("Time: %.2f\tnroll: %.2f\tnpitch: %.2f\tnyaw: %.2f\tnthrust: %d" % (self.time_elapsed, self.nroll, self.npitch, self.nyaw, self.nthrust))
			self.thrust_v = self.thrust_v + [self.nthrust] 
			self.roll_v = self.roll_v + [self.nroll] 
			self.pitch_v = self.pitch_v + [self.npitch]
			self.yaw_v = self.yaw_v + [self.nyaw]
			self.time_v = self.time_v + [self.time_elapsed]
			time.sleep(0.1)


	
	"""Callback when the Crazyflie is disconnected (called in all cases)"""
	def _disconnected(self, link_uri):
		print('Disconnected from %s' % link_uri)
		self.is_connected = False

        
	"""Callback when connection initial connection fails (i.e no Crazyflie
	at the specified address)"""
	def _connection_failed(self, link_uri, msg):
		print('Connection to %s failed: %s' % (link_uri, msg))

	"""Callback when disconnected after a connection has been made (i.e
	Crazyflie moves out of range)"""        
	def _connection_lost(self, link_uri, msg):
		print('Connection to %s lost: %s' % (link_uri, msg))
		self.is_connected = False

	def _stab_log_error(self, logconf, msg):
		"""Callback from the log API when an error occurs"""
		print('Error when logging %s: %s' % (logconf.name, msg))

	def _stab_log_data(self, timestamp, data, logconf):
		"""Callback froma the log API when data arrives"""
		self.nroll = data.get('stabilizer.roll', None)
		self.npitch = data.get('stabilizer.pitch', None)
		self.nyaw = data.get('stabilizer.yaw', None)
		self.nthrust = data.get('stabilizer.thrust', None)


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
	cflib.crtp.init_drivers(enable_debug_driver=False)

	#invoques the class
	le = Control("radio://0/80/250K")
    
  
    # The Crazyflie lib doesn't contain anything to keep the application alive,
    # so this is where your application should do something. In our case we
    # are just waiting until we are disconnected.
	while (le.is_connected):
		time.sleep(1)

