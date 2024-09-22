#######Algorithm Scanning######

 ################################
 #   Developer-Akshat Sharma    # 
 #   Date:12-September-2024     #
 ################################

1->Setup the Motor (P1)
2->Map the coordinate (x,y) For a Sample(P2)

####After Doing 1,2 Step we Reacded At The Starting          Position####

Scanning 25x28 Matrix For 700 Images


########Scanning####### (P3)
"""
Scanning Starts
"""
1->AutoFocus Function for j%3==0 for every Third indeices Autofocus function is Called 

2->Autofocus function (P4)


#######Autofocus Function Starts########
def auto(self):
        obj_value = 10
        z_positions = []
        variances = []
        max_variance = 0
        max_z = self.z
        
        
        ####Adding Picamera2 Configuration_4_sept
        
        
        
        preview_config = self.camera.create_preview_configuration(main={"size": (320,240)}, raw={"format": "SBGGR10_CSI2P"})
        self.camera.configure(preview_config)

      
       

       
        step_size = 50 if obj_value == 4 else 25 # 45
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
                  
                    command="zcclk"
                    self.motor_control(command,step_size)
                elif i < initial_steps * 2:
                   
                    command="zclk"
                    self.motor_control(command,step_size)
                else:
                    # Determine the direction based on the initial steps
                    if variances[initial_steps - 1] > variances[-1]:  # Upward direction is better
                        direction = 1
                        print("Direction: Upward")
                    else:  # Downward direction is better
                        direction = -1
                        print("Direction: Downward")

            if direction is not None:
                if direction == 1:
                    #self.movezanticlock(step_size) #12_Aug
                    command="zcclk"
                    self.motor_control(command,step_size)
                else:
                    # self.movezclock(step_size)     #12_Aug
                    command="zclk"
                    self.motor_control(command,step_size)

            # Check if the improvement in variance is below the threshold
     
            if(len(variances)>=4):
                variance_diff_1=abs(variances[-1]-variances[-2])
                variance_diff_2=abs(variances[-3]-variances[-4])
                if variance_diff_1<threshold and variance_diff_2<threshold:
                    print("Variance Change below threshold stop Autofocus")
                    break
            
            
           
            # Adjust the step size dynamically after a few iterations
            if i > 5:
                step_size = max(5, step_size - 5)
        
        # Adjust to the position with the maximum variance
        adjust_steps = self.z - max_z
        if adjust_steps > 0:
           
            command="zclk"
            self.motor_control(command,abs(adjust_steps))
        else:
           
            command="zcclk"
            self.motor_control(command,abs(adjust_steps))

      
        self.camera.stop() #PB
      
        
        #Save The file in full configuration_4_September
        
        capture_config = self.camera.create_still_configuration()
       
        print("Still configuration initialised")
        
        self.camera.configure(capture_config)
        self.camera.switch_mode_and_capture_image(capture_config)
        print("Image saved")
     
        
       


Calculating Variance()
1-> Preprocessing The image 
 #### def preprocess_image(self, image):
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply a median filter to reduce noise
        filtered = cv2.medianBlur(gray, 5)
        return filtered
##### Calculating The Variance
def variance(self, image):
    bg = cv2.GaussianBlur(image, (11, 11), 0)
    v = cv2.Laplacian(bg, cv2.CV_64F).var()
    return v


def capture_image(self):
        
        
        stream = io.BytesIO()
        self.camera.capture_file(stream, format='jpeg')
        stream.seek(0)
        image = np.frombuffer(stream.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        return image

def capture_and_save_image(self, dir_path, i, j):
        
        image = self.capture_image()
        image_path = "{}/imagerow{},{}.tiff".format(dir_path, i, j)
        image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        image_pil.save(image_path, format='TIFF')
      



########AutoFocus Function Ends



"""
Scanning Ends
"""







