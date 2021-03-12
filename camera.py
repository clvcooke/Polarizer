import PySpin
import numpy as np

class Camera(object):

    def __init__(self):
        # get a reference to the system singleton (they basically write C code in python...)
        self.system_instance = PySpin.System.GetInstance()
        self.camera = self.find_camera(self.system_instance)
        self.camera.Init()
        self.nodemap = self.camera.GetNodeMap()
        self.open = True
        # TODO: this is an assumption
        self.mode = 'Single'
        # TODO: this is an assumption, idk how it gets set initially
        self.exposure = 1
        self.pix_fmt = PySpin.PixelFormat_BayerRGPolarized8

    def change_exposure(self, exposure_time):
        """
        :param exposure_time: exposure time in microseconds
        :return:
        """
        if self.camera.ExposureAuto.GetAccessMode() != PySpin.RW:
            raise RuntimeError("Unable to disable automatic exposure. Aborting...")
        if self.camera.ExposureTime.GetAccessMode() != PySpin.RW:
            raise RuntimeError("Unable to set exposure time, aborting....")
        max_exp = self.camera.ExposureTime.GetMax()
        if max_exp < exposure_time:
            raise RuntimeError("Exposure time set beyond maximum")
        elif exposure_time <= 0:
            raise RuntimeError("Exposure time is below minimum (0)")

        self.camera.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        self.camera.ExposureTime.SetValue(exposure_time)
        self.exposure = exposure_time

    def acquire_frame(self, timeout=1000):
        if timeout < self.exposure/1000:
            print("WARNING: timeout is set lower than exposure time")
        self.camera.BeginAcquisition()
        image = self.camera.GetNextImage(timeout)
        # check if the image is "complete" whatever FLIR means by that
        assert not image.IsIncomplete(), 'Image is incomplete'
        converted_image = image.Convert(self.pix_fmt, PySpin.HQ_LINEAR)

        return converted_image.GetNDArray()

    def change_mode(self, new_mode):
        # TODO: maybe add others
        assert new_mode in ['Continous', 'Single']
        node_acquisition_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            raise RuntimeError('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
        node_acquisition_mode_value = node_acquisition_mode.GetEntryByName(new_mode)
        acquisition_mode_value = node_acquisition_mode_value.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_value)
        self.mode = new_mode

    @staticmethod
    def find_camera(system):
        camera = None
        iface_list = system.GetInterfaces()
        cam_list = system.GetCameras()
        num_cams = cam_list.GetSize()
        if num_cams > 1:
            print("More than one camera is unsupported....")
        elif num_cams == 0:
            print("No cameras found")
        else:
            interface = iface_list[0]
            nodemap_interface = interface.GetTLNodeMap()
            interface.UpdateCameras()
            cam_list = interface.GetCameras()
            # Retrieve number of cameras
            num_cams = cam_list.GetSize()
            if num_cams != 0:
                print(f"{num_cams} cameras is unsupported")
            else:
                camera = cam_list[0]
            cam_list.Clear()
        # since they write horrible code we need to "clear" the arrays if we don't end up using them
        iface_list.Clear()
        # Clear interface list before releasing system
        #
        # *** NOTES ***
        # Interface lists must be cleared manually prior to a system release call.
        iface_list.Clear()
        return camera

    def close(self):
        self.camera.DeInit()
        self.system_instance.ReleaseInstance()

    def __del__(self):
        if self.open:
            self.close()
