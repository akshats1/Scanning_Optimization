def auto(self):
    start_time_Auto = time.perf_counter()
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

        # Update the maximum variance and position
        if current_variance > max_variance:
            max_variance = current_variance
            max_z = self.z
        else:
            # If variance stops improving, break the loop early
            if i >= initial_steps and current_variance < max_variance - threshold:
                print(f"Variance stopped improving at iteration {i + 1}. Breaking early.")
                break

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

    # Move back to the position with the maximum variance
    adjust_steps = self.z - max_z
    command = "zclk" if adjust_steps > 0 else "zcclk"
    self.motor_control(command, abs(adjust_steps))

    end_time_Auto = time.perf_counter()
    print("AutoFocus duration:", end_time_Auto - start_time_Auto, "seconds")

