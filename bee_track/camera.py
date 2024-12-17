import numpy as np
from QueueBuffer import QueueBuffer
from configurable import Configurable
from multiprocessing import Value, Queue
import threading
import multiprocessing
import pickle
import datetime
import os

def downscale(img,blocksize):
    k = int(img.shape[0] / blocksize)
    l = int(img.shape[1] / blocksize)    
    maxes = img[:k*blocksize,:l*blocksize].reshape(k,blocksize,l,blocksize).max(axis=(-1,-3)) #from https://stackoverflow.com/questions
    return maxes


def downscalecolour(img,blocksize):
    k = int(img.shape[0] / blocksize)
    l = int(img.shape[1] / blocksize)    
    maxes = img[:k*blocksize,:l*blocksize,:].reshape(k,blocksize,l,blocksize,3).max(axis=(-2,-4)) #from https://stackoverflow.com/questions
    return maxes
    
class Camera(Configurable):
    def setup_camera(self):
        """To implement for specific cameras"""
        pass
        
    def __init__(self,message_queue,record,cam_trigger,cam_id=None):
        """
        Pass record list from trigger
        """
        super().__init__(message_queue)
        self.photo_queue = QueueBuffer(10) 
        self.record = record
        self.label = multiprocessing.Array('c',100)
        self.index = Value('i',0)
        self.savephotos = Value('b',True)
        self.fastqueue = Value('b',False) ###THIS WILL STOP PROCESSING
        self.test = Value('b',False)
        self.cam_trigger = cam_trigger
        self.colour_camera = Value('b',False)
        self.return_full_colour = Value('b',False) #if it returns RGB or just raw data.
        self.cam_id = cam_id
        self.config_camera_queue = Queue()
        self.info = False
        self.debug = False

        #Gets device id (copied from core.py)
        try:
            print("Trying to get our ID")
            devid = open('device_id.txt','r').read()
        except FileNotFoundError:
            print("Failed to find ID")
            devid = '9999'

        self.devid = Value('i',int(devid))

    def config_camera(self, param, value):
        """Implement for specific cameras
        param = 'exposure', 'delay' or 'predelay'
        """
        self.config_camera_queue.put([param,value])
        
        
    def camera_config_worker(self):
        """implements whatever configures the camera (E.g. setting the exposure)"""
        pass
        
    def camera_trigger(self):
        """implement whatever triggers the camera
        e.g. self.cam_trigger.wait()
        """
        pass        
        
    def get_photo(self,getraw=False):
        """Blocking
        
            Returns tuple of
            - a numpy array of the 'raw' image (either unsigned 8-bit - if getraw True, otherwise a float).
            - the timestamp
        """
        print("NOT IMPLEMENTED")
        pass
        
    def worker(self):
        print("Camera worker started.")
        self.setup_camera()
        t = threading.Thread(target=self.camera_trigger)
        t.start()
        t = threading.Thread(target=self.camera_config_worker)
        t.start()
        print("Camera setup complete")
        last_photo_object = None
        while True:
            photo,timestamp = self.get_photo(getraw=self.fastqueue.value)
            print(".",end="",flush=True)

            if photo is None:
                print("Photo failed")

            rec = None
            for r in self.record:
                if r['index'] == self.index.value:
                    rec = r
                    break
            if rec is None:
                print("WARNING: Failed to find associated photo record")
            
            
            photo_object = {'index':self.index.value,'record':rec,'camera_timestamp':timestamp}
            
    

            if photo is not None:
                photo = photo.astype(np.ubyte)
            photo_object['img'] = photo
            
            last_photo_object = photo_object

            try:
                labelstring = self.label.value.decode('utf-8')
                [session_name, set_name] = labelstring.split(',') 
            except ValueError:
                #probably no comma included in string...
                session_name = 'unnamed_session'
                if len(labelstring)>0:
                    set_name = labelstring
                else:
                    set_name = 'unnamed_set'

            if self.cam_id is not None:
                camidstr = self.cam_id[-11:]

            else:
                camidstr = ''
                            
            photo_object['session_name'] = session_name
            photo_object['set_name'] = set_name
            photo_object['dev_id'] = self.devid.value
            photo_object['camid'] = camidstr
            

                
            if rec is not None:
                triggertime_string = photo_object['record']['triggertimestring']

                filename = '%s_%04i.np' % (triggertime_string.replace(":","+"),self.index.value)
                photo_object['filename'] = filename
            else:
                filename = 'photo_object_%s_%s.np' % (camidstr,datetime.datetime.now().strftime("%Y%m%d_%H+%M+%S.%f"))                   
                self.message_queue.put("FAILED TO FIND ASSOCIATED RECORD! SAVED AS %s")
                photo_object['filename'] = filename
                
            
            self.photo_queue.put(photo_object)

            if self.savephotos.value:
                self.try_save(photo_object,filename,camidstr)
                self.message_queue.put("Saved Photo: %s" % filename)
                
                

            self.index.value = self.index.value + 1

    def try_save(self, photo_object, filename, camid):
        parents = "/home/pi/beephotos/%s/%s/%s/%s/%s/" % (datetime.date.today(),photo_object['session_name'],photo_object['set_name'],photo_object['dev_id'],photo_object['camid'])
        path = parents + filename

        try:
            pickle.dump(photo_object, open(path,'wb'))
        except FileNotFoundError:
            print("Parent Directory not found")
            os.makedirs(parents)
            pickle.dump(photo_object, open(path,'wb'))

                
    def close(self):
        """
        shutdown camera, etc
        """
        pass    
