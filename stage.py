import thorlabs_apt as apt
import numpy as np

class Stage:

    def __init__(self, x_serial=27504145, y_serial=27504197, z_serial=27504259, min_pos=0, max_pos=0):
        devices = [d[1] for d in apt.list_available_devices()]
        assert x_serial in devices
        assert y_serial in devices
        assert z_serial in devices
        self.x_motor = apt.Motor(x_serial)
        self.y_motor = apt.Motor(y_serial)
        self.z_motor = apt.Motor(z_serial)
        # we are going to assume that all motors are the same model, all units in mm
        self.max_z_pos = 11
        self.min_z_pos = 9
        self.min_x_pos = 10
        self.max_x_pos = 30
        self.min_y_pos = 10
        self.max_y_pos = 30
        self.min_pos = min_pos
        self.max_pos = max_pos

    def home(self, x=False, y=False, z=False):
        if x:
            self.x_motor.move_home(True)
        if y:
            self.y_motor.move_home(True)
        if z:
            self.z_motor.move_home(True)

    def _move(self, pos, motor):
        if pos is None:
            return
        assert self.min_pos <= pos <= self.max_pos
        motor.move_to(pos, True)

    def move(self, x_pos=None, y_pos=None, z_pos=None):
        if x_pos is not None:
            if not (self.min_x_pos <= x_pos <= self.max_x_pos):
                x_pos = np.clip(x_pos, self.min_x_pos, self.max_x_pos)
                print(f"Clipping x_pos to {x_pos}")
            self.x_motor.move_to(x_pos, True)
        if y_pos is not None:
            if not (self.min_y_pos <= y_pos <= self.max_y_pos):
                y_pos = np.clip(y_pos, self.min_y_pos, self.max_y_pos)
                print(f"Clipping y_pos to {y_pos}")
            self.y_motor.move_to(y_pos, True)
        if z_pos is not None:
            if not (self.min_z_pos <= z_pos <= self.max_z_pos):
                z_pos = np.clip(z_pos, self.min_z_pos, self.max_z_pos)
                print(f"Clipping z_pos to {z_pos}")
            self.z_motor.move_to(z_pos, True)

    def get_pos(self):
        x_pos = self.x_motor.position
        y_pos = self.y_motor.position
        z_pos = self.z_motor.position
        return x_pos, y_pos, z_pos
