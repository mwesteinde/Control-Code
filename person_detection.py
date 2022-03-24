## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2015-2017 Intel Corporation. All Rights Reserved.

###############################################
##      Open CV and Numpy integration        ##
###############################################

#For rubbermaid lid: 0-4, 160-255, 29-128
#pants: 0-180, 121-255, 184-255

import pyrealsense2 as rs
import numpy as np
import cv2

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()

# Get device product line for setting a supporting resolution
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
device_product_line = str(device.get_info(rs.camera_info.product_line))

found_rgb = False
for s in device.sensors:
    if s.get_info(rs.camera_info.name) == 'RGB Camera':
        found_rgb = True
        break
if not found_rgb:
    print("The demo requires Depth camera with Color sensor")
    exit(0)

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

if device_product_line == 'L500':
    config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 30)
else:
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
pipeline.start(config)

# define a null callback function for Trackbar
def null(x):
    pass

# create six trackbars for H, S and V - lower and higher masking limits
cv2.namedWindow('HSV')
# arguments: trackbar_name, window_name, default_value, max_value, callback_fn
cv2.createTrackbar("HL", "HSV", 0, 180, null)
cv2.createTrackbar("HH", "HSV", 180, 180, null)
cv2.createTrackbar("SL", "HSV", 121, 255, null)
cv2.createTrackbar("SH", "HSV", 255, 255, null)
cv2.createTrackbar("VL", "HSV", 184, 255, null)
cv2.createTrackbar("VH", "HSV", 255, 255, null)



try:
    while True:

        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        color_image = cv2.resize(color_image, (320,280))
        depth_image = cv2.resize(depth_image, (320,280))

        img = color_image

        # convert BGR image to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # read the Trackbar positions
        hl = cv2.getTrackbarPos('HL','HSV')
        hh = cv2.getTrackbarPos('HH','HSV')
        sl = cv2.getTrackbarPos('SL','HSV')
        sh = cv2.getTrackbarPos('SH','HSV')
        vl = cv2.getTrackbarPos('VL','HSV')
        vh = cv2.getTrackbarPos('VH','HSV')

        # create a manually controlled mask
        # arguments: hsv_image, lower_trackbars, higher_trackbars
        mask = cv2.inRange(hsv, np.array([hl, sl, vl]), np.array([hh, sh, vh]))
        # derive masked image using bitwise_and method
        final = cv2.bitwise_and(img, img, mask=mask)

        # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

        depth_colormap_mask = cv2.bitwise_and(depth_colormap, depth_colormap, mask=mask)
        color_image_mask = cv2.bitwise_and(color_image, color_image, mask=mask)

        depth_colormap_dim = depth_colormap.shape
        color_colormap_dim = color_image.shape

        # calculate moments of binary image
        M = cv2.moments(mask)
        # calculate x,y coordinate of center
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            # put text and highlight the center
            cv2.circle(color_image_mask, (cX, cY), 5, (255, 255, 255), -1)
            cv2.putText(color_image_mask, "centroid", (cX - 25, cY - 25),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # If depth and color resolutions are different, resize color image to match depth image for display
        if depth_colormap_dim != color_colormap_dim:
            resized_color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]), interpolation=cv2.INTER_AREA)
            images = np.hstack((resized_color_image, depth_colormap))
        else:
            images = np.hstack((color_image_mask, depth_colormap_mask))


        # display image, mask and masked_image
        cv2.imshow('Original', img)
        cv2.imshow('Mask', mask)
        cv2.imshow('Masked Image', final)
        # Show images
        cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('RealSense', images)


        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
    cv2.destroyAllWindows()


finally:

    # Stop streaming
    pipeline.stop()