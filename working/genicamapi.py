
from harvesters.core import Harvester
from genicam.genapi import EInterfaceType, EAccessMode, EVisibility

from threading import Thread
import json
import time
import cv2


_readable_access_modes = [EAccessMode.RW, EAccessMode.RO, EAccessMode.WO]
_writable_access_modes = [EAccessMode.RW, EAccessMode.WO]

_readable_nodes = [
    EInterfaceType.intfIBoolean,
    EInterfaceType.intfIEnumeration,
    EInterfaceType.intfIFloat,
    EInterfaceType.intfIInteger,
    EInterfaceType.intfIString,
    EInterfaceType.intfIRegister,
]


def initdriver(driverpath):
    h = Harvester()
    h.add_file(driverpath)
    h.update() 
    return h


def getdeviceinfo(device_info_list):
    res = {}

    res['id'] = device_info_list.id_
    res['model'] = device_info_list.model
    res['serial_number'] = device_info_list.serial_number
    res['tl_type'] = device_info_list.tl_type
    res['vendor'] = device_info_list.vendor
    res['version'] = device_info_list.version
    res['display_name'] = device_info_list._device_info.display_name
    return res


def getdevicesinfo(h,index = -1):
    devicesinfo = h.device_info_list

    if index >= 0 and len(devicesinfo) > index:
        res = getdeviceinfo(devicesinfo[index])
    else:
        res = []
        for device in devicesinfo:
            res.append(getdeviceinfo(device))

    return res


def opendevice(h,index = 0, serial = None, size_buffer = 1):

    if serial is not None:
        ia = h.create_image_acquirer(serial_number=serial)
    else:
        ia = h.create_image_acquirer(list_index= index)

    ia.num_buffers = size_buffer

    return ia

    
def getTreeItems(features, parent_item):
    for feature in features:

        ele = {}
        name = feature.node.name
        
        interface_type = feature.node.principal_interface_type

        ele['name'] = name
        ele['displayname'] = feature.node.display_name
        ele['tooltip'] = feature.node.tooltip
        ele['description'] = feature.node.description

        if interface_type == EInterfaceType.intfICategory:

            ele['type'] = 'category'

            child = {}
            getTreeItems(feature.features, child)
            ele['child'] = child

            parent_item[name] = ele  

        else:
            accessmode = feature.node.get_access_mode()

            if accessmode not in \
                    _readable_access_modes:
                value = '[Not accessible]'
            else:
                try:

                    ele['accessmode'] = accessmode

                    value = feature.value

                    itype = ''

                    if interface_type == EInterfaceType.intfIInteger:
                        itype = 'int'

                        ele['min'] = feature.min
                        ele['max'] = feature.max
                        ele['inc'] = feature.inc
 
                    elif interface_type == EInterfaceType.intfIBoolean:
                        itype = 'bool'
                    elif interface_type == EInterfaceType.intfIEnumeration:
                        itype = 'enum'
                        enumvalues = []

                        # this for all available options:
                        #for item in feature.entries:
                        #    enumvalues.append({'symbolic': item.symbolic})
                        # this for only valid options:
                        for item in feature.symbolics:
                            enumvalues.append({'symbolic': item})
                        ele['enums'] = enumvalues

                    elif interface_type == EInterfaceType.intfIString:
                        itype = 'string'
                    elif interface_type == EInterfaceType.intfIFloat:
                        itype = 'float'
                        value = float(feature.value) 

                    ele['type'] = itype
                    ele['value'] = value

                    parent_item[name] = ele 

                except:
                    # TODO: Specify appropriate exceptions
                    pass    

def getconfigurationfromdevice(node_map):

    nodes = {}
    getTreeItems(node_map.Root.features,nodes)

    return nodes

def setTreeItems(features, parent_item):
    for feature in features:

        name = feature.node.name

        if name in parent_item:
            ele = parent_item[name]

            interface_type = feature.node.principal_interface_type
            
            if interface_type == EInterfaceType.intfICategory:
                if 'child' in ele:
                    setTreeItems(feature.features, ele['child'])
            else:
                if 'value' in ele:
                    try:
                        accessmode =  feature.node.get_access_mode()

                        if accessmode in _writable_access_modes:

                            value = ele['value']

                            if interface_type == EInterfaceType.intfIFloat:
                                value = float(value)

                            if feature.value != value:
                                feature.value = value
                                print('Written: ' + str(value) + ' in ' + name + ' [' + str(accessmode) + ']')

                    except Exception as e:
                        print('Not Written: ' + str(value) + ' in ' + name + ' [' + str(accessmode) + ']')
                        print(str(e))


def setconfigurationtodevice(node_map,nodes):

    setTreeItems(node_map.Root.features,nodes)

    return nodes

def saveconfigurationjson(data,filename = 'data.json'):

    res = False
    try:
        with open(filename, 'w') as f:
            #f.write(json.dumps(data, indent=4, sort_keys=True))
            #json.dump(data, f)
            json.dump(data, f, indent=4)
            res = True

    except Exception as e:
        print(str(e))

    return res

def loadconfigurationjson(filename = 'data.json'):

    res = None
    try:
        with open(filename) as json_file:
            res = json.load(json_file)

    except Exception as e:
        print(str(e))

    return res

def parsebuffer2d(buffer):
    component = buffer.payload.components[0]
    channels = int(component.num_components_per_pixel)

    data_format = component.data_format

    if channels == 1:
        img2d = component.data.reshape(component.height, component.width)
    else:
        img2d = component.data.reshape(component.height, component.width,channels)

    return img2d, data_format


def cameratocv(buffer,out = 'BGR'):
    img, data_format = parsebuffer2d(buffer)

    if out == 'BGR':
        if data_format == 'Mono8':
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif data_format == 'YUV422_8_UYVY':
            img = cv2.cvtColor(img, cv2.COLOR_YUV2BGR_UYVY)  
        elif data_format == 'YUV422_8':
            img = cv2.cvtColor(img, cv2.COLOR_YUV2BGR_YUY2)
        elif data_format == 'BayerRG12':
            img = cv2.cvtColor(img, cv2.COLOR_BayerRG2BGR)
        elif data_format == 'BayerRG12Packed':
            img = cv2.cvtColor(img, cv2.COLOR_BayerRG2BGR)

    return img



class genicammanager():

    def __init__(self,driverpath):
        self.h = None
        self.ia = None
        self.cfg = None
        self.index = -1
        self.lasterror = ''
        self.continueloop = False
        self.looprunning = False
        self.driverpath = driverpath

    def parseError(self,e,message = ''):
        err = str(e)
        self.lasterror = err
        print('Error: ' + message + ' ' + err)

    def initdriver(self):
        try:
            self.h = initdriver(self.driverpath)
            return True

        except Exception as e:
            self.parseError(e,'initdriver')
            return False

    def getdevicesinfo(self,index = -1):
        try:
            res = getdevicesinfo(self.h,index)
            return res

        except Exception as e:
            self.parseError(e,'getdevicesinfo')
            return None


    def getconfigurationfromdevice(self):
        self.cfg = getconfigurationfromdevice(self.ia.remote_device.node_map)
        return self.cfg


    def opendevice(self,index = 0, serial = None):
        try:
            self.ia = opendevice(self.h,index,serial)
            self.getconfigurationfromdevice()
            self.index = index
            return True

        except Exception as e:
            err = str(e)
            self.lasterror = err
            return False


    def saveconfigurationjson(self,filename = 'data.json'):
        return saveconfigurationjson(self.cfg ,filename)


    def applyconfigurationjson(self,filename = 'data.json'):
        cfg = self.loadconfigurationjson(filename)
        if cfg is not None:
            return self.setconfigurationtodevice(cfg)
        else:
            return False


    def loadconfigurationjson(self,filename = 'data.json'):
        return loadconfigurationjson(filename)


    def setconfigurationtodevice(self,cfg = None):
        try:
            cfgtoset = cfg if cfg is not None else self.cfg
            setconfigurationtodevice(self.ia.remote_device.node_map,cfgtoset) 
            self.getconfigurationfromdevice() 
            return True

        except Exception as e:
            err = str(e)
            self.lasterror = err
            return False

    def on_image(self,buffer):
        pass


    def mainloop(self,ia,callback):
        ia.start_acquisition()

        self.looprunning = True
        self.continueloop = True

        while self.continueloop:
            try:
                with ia.fetch_buffer() as buffer:
                    callback(buffer)

            except Exception as e:
                err = str(e)
                pass
                # err = str(e)
                # self.lasterror = err

        ia.stop_acquisition()
        self.looprunning = False

        
    def islooprunning(self):
        return self.looprunning
        

    def stopacq(self):
        self.continueloop = False

        while self.islooprunning():
            time.sleep(0.1)
        
        return True

    def parsebuffer2d(self,buffer):
        return parsebuffer2d(buffer)


    def cameratocv(self,buffer,out = 'BGR'):
        return cameratocv(buffer,out)

       
    def startacq(self,callback = None, asyncreadmode = False):
        ia = self.ia

        if callback is None:
            callback = self.on_image

        if ia is None:
            return False
        else:
            if asyncreadmode:
                th = Thread(target=self.mainloop, args=(ia,callback))
                th.start()
            else:
                self.mainloop(ia,callback)

    def campars(self):
        return self.ia.remote_device.node_map

    def close(self):

        self.stopacq()

        if self.ia is not None:
            self.ia.destroy()
            self.ia = None

        if self.h is not None:
            self.h.reset()
            self.h = None

