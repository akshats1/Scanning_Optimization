import serial
import cv2
from time import sleep
from datetime import datetime
import subprocess
import logging
from picamera2 import Picamera2, Preview
from PIL import Image
import io
import numpy as np
import os
import time
import threading
import concurrent.futures  # For parallel image saving
import gpiod

# Initialize global variables
x_axis = 0
y_axis = 0
z_axis = 0
camera_lock = threading.Lock()
start_time_auto=0





"""
29.5 Minutes Scanning 700 images
x translation 6 steps 0.103 seconds
Autofocus+Capturing Saving 1 row 1.8 minutes
Autofocus_Time_Taken->4.28 seconds(Avg) 2.82 seconds(Best)
"""





import io
import time
import numpy as np
import concurrent.futures
import subprocess
import logging
import os
from datetime import datetime
from picamera2 import Picamera2
import cv2
import gpiod

class Microscope:
    def __init__(self):
        # Initialize camera and pins
        self.camera = Picamera2()
        self.x = 0
        self.y = 0
        self.z = 4000
        self.start_time_auto=0
        self.end_time_auto=0
        self.is_camera_running = False  # Flag to track camera state
        self.scan_count = 0
        self.ControlPinX = [18, 23, 24, 25]
        self.ControlPinY = [5, 6, 13, 19]
        self.ControlPinZ = [21, 20, 2, 16]
        self.STEPS_PER_MM_X = 10
        self.STEPS_PER_MM_Y = 10
        self.STEPS_PER_MM_Z = 10
        self.delay = 0.0004  # Reduced delay for faster motor movement
        self.seg_right = [
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [0, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 1],
            [0, 0, 0, 1],
            [1, 0, 0, 1]
        ]
        self.seg_left = [
            [0, 0, 0, 1],
            [0, 0, 1, 1],
            [0, 0, 1, 0],
            [0, 1, 1, 0],
            [0, 1, 0, 0],
            [1, 1, 0, 0],
            [1, 0, 0, 0],
            [1, 0, 0, 1]
        ]
        self.setup_gpio()

    def setup_gpio(self):
        # Initialize GPIO
        self.chip = gpiod.Chip('gpiochip0')
        self.lines_x = [self.chip.get_line(pin) for pin in self.ControlPinX]
        self.lines_y = [self.chip.get_line(pin) for pin in self.ControlPinY]
        self.lines_z = [self.chip.get_line(pin) for pin in self.ControlPinZ]
        self.ms_line = self.chip.get_line(17)
        self.ms_line.request(consumer='stepper', type=gpiod.LINE_REQ_DIR_OUT)
        self.ms_line.set_value(0)
        for line in self.lines_x + self.lines_y + self.lines_z:
            try:
                line.request('stepper_motor', gpiod.LINE_REQ_DIR_OUT, 0)
            except OSError as e:
                print(f"Error requesting line: {e}")
                
    
    def set_all_pins_low(self):
        """Set all control pins to low."""
        for line in self.lines_x + self.lines_y + self.lines_z:
            line.set_value(0)
    
    
                
    def move_x(self, forward, steps):
        direction = self.seg_right if forward else self.seg_left
        self.run_motor(self.lines_x, direction, steps)

    def move_y(self, forward, steps):
        direction = self.seg_right if forward else self.seg_left
        self.run_motor(self.lines_y, direction, steps)

    def move_z(self, forward, steps):
        direction = self.seg_right if forward else self.seg_left
        self.run_motor(self.lines_z, direction, steps)

    def run_motor(self, lines, direction, steps):
        steps = int(steps)
        for _ in range(steps):
            for halfstep in range(8):
                for pin in range(4):
                    lines[pin].set_value(direction[halfstep][pin])
                    time.sleep(self.delay)

    def motor_control(self, command, steps):
        try:
            if command.startswith("xclk"):
                self.move_x(forward=True, steps=steps)
                self.x -= steps
            elif command.startswith("xcclk"):
                self.move_x(forward=False, steps=steps)
            elif command.startswith("yclk"):
                self.move_y(forward=True, steps=steps)
            elif command.startswith("ycclk"):
                self.move_y(forward=False, steps=steps)
            elif command.startswith("zclk"):
                self.z -= steps
                self.move_z(forward=True, steps=steps)
            elif command.startswith("zcclk"):
                self.z += steps
                self.move_z(forward=False, steps=steps)
            elif command == "init":
                self.home_all_axes()
            elif command == "status":
                print(self.check_endstops())
            else:
                print("Unknown command")
        except (IndexError, ValueError) as e:
            print(f"Error processing command: {e}")
                
                
    def variance(self, image):
        bg = cv2.GaussianBlur(image, (11, 11), 0)
        v = cv2.Laplacian(bg, cv2.CV_64F).var()
        return v
        
        
        #cv2.Laplacian(image, cv2.CV_64F).var()

    def preprocess_image(self, image):
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply a median filter to reduce noise
        filtered = cv2.medianBlur(gray, 5)
        return filtered
        #cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
    def save_image(self, image, image_path):
        image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        image_pil.save(image_path, format='TIFF')

    def configure_camera_for_autofocus(self):
        if self.is_camera_running:
            self.camera.stop()
            self.is_camera_running = False
        preview_config = self.camera.create_preview_configuration(
            main={"size": (320, 240)}, raw={"format": "SBGGR10_CSI2P"}
        )
        self.camera.configure(preview_config)
        self.camera.start(show_preview=False)
        self.is_camera_running = True

    def configure_camera_for_full_resolution(self):
        if self.is_camera_running:
            self.camera.stop()
            self.is_camera_running = False
        full_res_config = self.camera.create_still_configuration(
            main={"size": (4056, 3040)}, raw={"format": "SBGGR10_CSI2P"}
        )
        self.camera.configure(full_res_config)
        self.camera.start(show_preview=False)
        self.is_camera_running = True

    def capture_image(self):
        # time.sleep(0.005)
        stream = io.BytesIO()
        self.camera.capture_file(stream, format='jpeg')
        stream.seek(0)
        image = np.frombuffer(stream.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        return image

    def auto(self):
        start_time_Auto =time.perf_counter()
        obj_value = 10
        z_positions = []
        variances = []
        max_variance = 0
        max_z = self.z

    # Configure camera for autofocus
        self.configure_camera_for_autofocus()

        step_size = 50 if obj_value == 4 else 25
        max_iterations = 7
        initial_steps = 2  # Number of steps to check in each direction
        threshold = 0.1  # Variance threshold to stop autofocus
        direction = None

        for i in range(max_iterations):
            stream = io.BytesIO()
            self.camera.capture_file(stream, format='jpeg')
            stream.seek(0)
            image = np.frombuffer(stream.getvalue(), dtype=np.uint8)
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)

            preprocessed_image = self.preprocess_image(image)
            current_variance = self.variance(preprocessed_image)
            variances.append(current_variance)
            z_positions.append(self.z)

            print(f"Iteration {i + 1}: x_axis={self.x}, y_axis={self.y}, z_axis={self.z}, variance={current_variance}")

            if current_variance > max_variance:
                max_variance = current_variance
                max_z = self.z

        # If direction has not been determined, try both directions
            if direction is None:
                if i < initial_steps:
                    command = "zcclk"
                    self.motor_control(command, step_size)
                elif i < initial_steps * 2:
                    command = "zclk"
                    self.motor_control(command, step_size)
                else:
                # Determine the direction based on the initial steps
                    if variances[initial_steps - 1] > variances[-1]:  # Upward direction is better
                        direction = 1
                        print("Direction: Upward")
                    else:  # Downward direction is better
                        direction = -1
                        print("Direction: Downward")

        # Move the z-axis based on the determined direction
            if direction is not None:
                command = "zcclk" if direction == 1 else "zclk"
                self.motor_control(command, step_size)

        # Check if the improvement in variance is below the threshold
            if len(variances) >= 4:
                variance_diff_1 = abs(variances[-1] - variances[-2])
                variance_diff_2 = abs(variances[-3] - variances[-4])
                if variance_diff_1 < threshold and variance_diff_2 < threshold:
                    print("Variance Change below threshold. Stopping autofocus.")
                    break

        # Dynamically adjust the step size after a few iterations
        #if i > 5:
         #   step_size = max(5, step_size - 5)

    # Adjust to the position with the maximum variance
        adjust_steps = self.z - max_z
        command = "zclk" if adjust_steps > 0 else "zcclk"
        self.motor_control(command, abs(adjust_steps))
        end_time_Auto =time.perf_counter()
        print("AutoFocus duration:", end_time_Auto - start_time_Auto, "seconds")
        
      

    


    def scan(self):
        cur_time = datetime.now()
        dir_path = "/media/rasp5/New Volume5/Images_Scan/Test_5/scan_{}".format(cur_time.strftime("%Y%m%d_%H%M"))
        subprocess.run(["mkdir", dir_path])
       

        # Use a thread pool for saving images in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            save_futures = []
            start_time_row_1 =time.perf_counter()
            for i in range(25):
                image_row = []
                for j in range(28):
                    if j % 3 == 0:
                        self.camera.stop()
                       
                        self.auto()  # Autofocus at every 3rd position
                        
                    self.configure_camera_for_full_resolution()  # Switch to full resolution before capture
                    image = self.capture_image()
                    image_row.append(image)

                    image_path = os.path.join(dir_path, "img_{}_{}.tiff".format(i, j))
                    future = executor.submit(self.save_image, image, image_path)
                    save_futures.append(future)

                    # Simulate scanning progress in UI
                    progress = (i * 18 + j + 1) / (10 * 18) * 100
                    print(f"Scanning progress: {progress:.2f}%")

                    # Move the x-axis in alternating directions
                   
                    
                    if i % 2 == 0:
                        start_time=time.perf_counter()
                        self.motor_control("xcclk", 6)
                        end_time=time.perf_counter()
                        print(end_time-start_time,"Duration_x_step")
                    
                    
                    else:
                        

                        
                        self.motor_control("xclk", 6)

                # Move the y-axis after completing the row
                end_time_row_1 = time.perf_counter()
                print("First row scanning duration:", end_time_row_1 - start_time_row_1, "seconds")
                        
                self.motor_control("yclk", 8)
                logging.info("[Scan] Changing y Pos")

            # Ensure all images are saved before proceeding
            for future in save_futures:
                future.result()
        
   

        print("Scanning completed.")

if __name__ == '__main__':
    microscope = Microscope()
    microscope.scan()


if __name__ == '__main__':
    start_time = time.perf_counter()
    #main()
    
    microscope = Microscope()
    microscope.scan()
    end_time = time.perf_counter()
    print(end_time - start_time, "Total_Duration")

