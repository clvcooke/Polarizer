import os

import numpy as np
import cv2 as cv
from tqdm import tqdm

from Polarizer.polarizer import Polarizer
from Polarizer.camera import Camera
from Polarizer.stage import Stage

VIZ_ANGLE = 0
POLAR_CHECK_ANGLE = 43
POLAR_CHECK_QUAD = 1
POLAR_CHECK_EXPOSURE = 100000
VIZ_EXPOSURE = 4500
POLAR_THRESH = 30
POLAR_CUTOFF = 0.1


class Scanner:

    def __init__(self, polar_port, save_location, verbose=True):
        """
        This class encapsulates all the scanning hardware and allows for complete control of the scanning system
        :param polar_port:
        :param stage_x_serial:
        :param stage_y_serial:
        :param stage_z_serial:
        """
        # check if the folder is empty
        folder_check = os.path.exists(save_location) and os.listdir(save_location)
        assert not folder_check, "Save location already exists and is non-empty, please pick a new folder"
        os.makedirs(save_location, exist_ok=True)

        # first we wll get access to all our hardware
        if verbose:
            print("initializing hardware")
        self.polarizer = Polarizer(polar_port)
        self.camera = Camera()
        self.stage = Stage()
        self.x_fov = 0.6
        self.y_fov = 0.65
        # pos is an x/y/z tuple
        self.curr_pos = self.stage.get_pos()
        self.save_location = save_location
        if verbose:
            print("Hardware Initialized")

    def autofocus(self, z_min, z_max, z_step=0.001, algo='binary'):
        """
        For a specific ara
        :param z_min:
        :param z_max:
        :param z_step:
        :param algo: only "binary" and "brute" are currently supported
        :return: best z
        """
        pass
        best_z = 0
        return best_z

    def _autofocus_brute(self, z_min, z_max, z_step):
        ## First capture every image
        z_positions = np.arange(z_min, z_max + z_step, z_step)
        freq_data = []
        for z_position in z_positions:
            self.stage.move(z_pos=z_position)
            frame = self.camera.acquire_frame(quadrants=(0,))

    def capture_fov(self, quadrants=(0, 1, 2, 3), exposure=4500):
        self.camera.change_exposure(exposure)
        frames = self.camera.acquire_frame(quadrants)
        return frames

    @staticmethod
    def _check_bif(image):
        # grabbing the green channel
        image_gray = image[:, :, 1]
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
        mo = cv.morphologyEx(image_gray.astype(np.uint8), cv.MORPH_OPEN, kernel, iterations=1)
        mean_image = np.mean(mo > POLAR_THRESH)
        if mean_image > POLAR_CUTOFF:
            return True
        else:
            return False

    def scan_area(self, start_x, end_x, start_y, end_y, overlap=0.1):
        """

        :param start_x:
        :param end_x:
        :param start_y:
        :param end_y:
        :param overlap: percent overlap between adjacent regions
        :return:
        """
        if start_x > end_x:
            x = start_x
            start_x = end_x
            end_x = x
        if start_y > end_y:
            y = start_y
            start_y = end_y
            end_y = y

        # we will get the range of FOVs
        x_positions = np.arange(start_x, end_x, self.x_fov * (1 - overlap))
        y_positions = np.arange(start_y, end_y, self.y_fov * (1 - overlap))

        # we will start by moving the stage to start_x and start_y
        self.stage.move(x_pos=start_x, y_pos=start_y)
        # now we will get an initial z position by autofocusing
        # TODO: need to specify a good z range
        AUTOFOCUS = False
        if AUTOFOCUS:
            initial_z = self.autofocus()
            z_positions = [initial_z]
        else:
            z_positions = [9.95, 9.955, 9.96, 9.965, 9.97, 9.975, 9.98, 9.985, 9.99, 9.995, 10.0]
        # then we begin the main capture loop
        print(x_positions)
        print(y_positions)
        for x_pos in tqdm(x_positions, desc=f"X-Scanning"):
            for y_pos in tqdm(y_positions, desc=f"Y-Scanning"):
                for z_pos in z_positions:
                    # MOVE
                    self.polarizer.move_absolute(VIZ_ANGLE)
                    self.stage.move(x_pos=x_pos, y_pos=y_pos, z_pos=z_pos)
                    # capture normal viz frame (low exp)
                    viz_quadrants = [0, 1, 2, 3]
                    viz_exposure = VIZ_EXPOSURE
                    viz_frames = self.capture_fov(quadrants=viz_quadrants, exposure=viz_exposure)
                    # TODO: allow both methods
                    # check if the area is birefringent
                    self.polarizer.move_absolute(POLAR_CHECK_ANGLE)
                    bif_frame = self.capture_fov(quadrants=(POLAR_CHECK_QUAD,), exposure=POLAR_CHECK_EXPOSURE)[0]
                    # this assumes we are all in focus....
                    HACK = True
                    if not HACK:
                        is_bif = self._check_bif(bif_frame)
                        if is_bif:
                            b_frames = []
                            polarization_angles = np.linspace(POLAR_CHECK_ANGLE - 2, POLAR_CHECK_ANGLE + 2, 0.5)
                            for polarization_angle in polarization_angles:
                                self.polarizer.move_absolute(polarization_angle)
                                b_frame = self.capture_fov(quadrants=(POLAR_CHECK_QUAD,),
                                                           exposure=POLAR_CHECK_EXPOSURE)[0]
                                b_frames.append(b_frame)
                    # SAVING OUR DATA
                    # one subfolder per position
                    position_folder = os.path.join(self.save_location, f"x_{x_pos:.3f}_y_{y_pos:.3f}_z_{z_pos:.3f}")
                    # MUST be a new folder
                    os.makedirs(position_folder, exist_ok=False)
                    # save the v_frames
                    for viz_frame, viz_quadrant in zip(viz_frames, viz_quadrants):
                        v_img_name = f"viz_exp_{viz_exposure}_quad_{viz_quadrant}_gen_{VIZ_ANGLE}.png"
                        v_path = os.path.join(position_folder, v_img_name)
                        cv.imwrite(v_path, viz_frame)
                    # save the bif frame
                    bif_img_name = f"bif_exp_{POLAR_CHECK_EXPOSURE}_quad_{POLAR_CHECK_QUAD}_gen_{POLAR_CHECK_ANGLE}.png"
                    bif_path = os.path.join(position_folder, bif_img_name)
                    cv.imwrite(bif_path, bif_frame)
