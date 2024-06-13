import sys
import time
import numpy as np
from gi.repository import Aravis
import pickle
import ctypes
from multiprocessing import Queue
import threading
import gc
from datetime import datetime as dt
import os

from camera import Camera

    
class Dummy_Camera(Camera):
    def setup_camera(self):
        self.message_queue.put('Dummy camera (real camera probably not found)')
        print("Dummy Camera (real camera probably not found)")

 
    def camera_config_worker(self):
        while True:
            config = self.config_camera_queue.get()
            self.message_queue.put('Dummy camera - cannot set configuration')
            print('Dummy camera - cannot set configuration')
    
    def camera_trigger(self):
        while True:            
            self.cam_trigger.wait()
            self.message_queue.put('Dummy camera - cannot trigger')
            print('Dummy camera - cannot trigger')

#    def get_photo(self,getraw=False):
#        time.sleep(100000000) #we will never get a photo (this method will block forever)
#        return None, None
        
    def worker(self):
        while True:
            self.message_queue.put('Dummy camera (real camera probably not found)')
            time.sleep(5)
            
    def close(self):
        pass    

