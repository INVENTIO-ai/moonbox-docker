from genicamapi import genicammanager
import cv2

driverpath = '/opt/pylon5/lib64/gentlproducer/gtl/ProducerGEV-1.4.0.cti'

def parseimage(buffer):

    img = cammanager.cameratocv(buffer)
    print('image acq')

print('init driver..')
cammanager = genicammanager(driverpath)
cammanager.initdriver()
info = cammanager.getdevicesinfo()
print('cams found: ' + str(info))

print('Open cam..')
if cammanager.opendevice(0):

    cammanager.saveconfigurationjson()

    print('Set parameters..')
    cammanager.campars().PixelFormat.value = 'BayerRG12Packed' #'BayerRG12' #'YUV422_YUYV_Packed' #'YUV422Packed' #'Mono8' #'YUV422Packed' #'Mono8'

    print('Start acq..')
    cammanager.startacq(parseimage)
else:

    print('fail open cam: ' + cammanager.lasterror)


