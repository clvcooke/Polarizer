import pypylon as pylon


class Camera(object):

    def __init__(self, open=False):
        self.camera = None
        if open:
            self.open()

    def open(self):
        self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        self.camera.Open()
        return True

    def close(self):
        self.camera.Close()

