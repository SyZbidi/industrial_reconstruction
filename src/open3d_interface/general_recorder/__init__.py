# Open3D: www.open3d.org
# The MIT License (MIT)
# See license file or visit www.open3d.org for details

import rospkg
import rospy
import tf
from os import makedirs
from os.path import exists, join
from sensor_msgs.msg import Image, CameraInfo
from message_filters import ApproximateTimeSynchronizer, Subscriber
from open3d_interface.utility.file import make_clean_folder
from open3d_interface.srv import StartRecording, StopRecording, ReconstructSurface
from open3d_interface.srv import StartRecordingResponse, StopRecordingResponse
from open3d_interface.utility.ros import reconstructSystemCallback, save_camera_info_intrinsic_as_json

# ROS Image message -> OpenCV2 image converter
from cv_bridge import CvBridge, CvBridgeError
# OpenCV2 for saving an image
import cv2

bridge = CvBridge()

tf_listener = None
path_output = "/tmp"
path_depth = join(path_output, "depth")
path_color = join(path_output, "color")
path_pose = join(path_output, "pose")

camera_info_topic = '/camera/rgb/camera_info'
tracking_frame = ''
relative_frame = ''

record = False
enable_tracking = False
frame_count = 0

def startRecordingCallback(req):
  global record, enable_tracking, path_output, path_depth, path_color, path_pose, frame_count

  rospy.loginfo(rospy.get_caller_id() + "Start Recording")

  enable_tracking = req.enable_tracking

  path_output = req.directory
  path_depth = join(path_output, "depth")
  path_color = join(path_output, "color")

  make_clean_folder(path_output)
  make_clean_folder(path_depth)
  make_clean_folder(path_color)

  if enable_tracking:
    tracking_frame = req.tracking_frame
    relative_frame = req.relative_frame
    path_pose = join(path_output, "pose")
    make_clean_folder(path_pose)

  frame_count = 0
  record = True

  return StartRecordingResponse(True)

def stopRecordingCallback(req):
  global record
  rospy.loginfo(rospy.get_caller_id() + "Stop Recording")
  record = False
  return StopRecordingResponse(True)

def cameraCallback(depth_image_msg, rgb_image_msg):
  global frame_count, record, path_output, path_depth, path_color, path_pose, tracking_frame, relative_frame

  if record:
    try:
        # Convert your ROS Image message to OpenCV2
        cv2_depth_img = bridge.imgmsg_to_cv2(depth_image_msg, desired_encoding="passthrough")
        cv2_rgb_img = bridge.imgmsg_to_cv2(rgb_image_msg, "bgr8")
        if enable_tracking:
          (rgb_t,rgb_r) = tf_listener.lookupTransform(relative_frame, tracking_frame, rgb_image_msg.header.stamp)
    except CvBridgeError:
        print(e)
    else:
        # Get camera intrinsic from camera info
        if frame_count == 0:
            camera_info = rospy.wait_for_message(camera_info_topic, CameraInfo)
            save_camera_info_intrinsic_as_json(join(path_output, "camera_intrinsic.json"), camera_info)

        # Save your OpenCV2 image as a jpeg
        cv2.imwrite("%s/%06d.png" % (path_depth, frame_count), cv2_depth_img)
        cv2.imwrite("%s/%06d.jpg" % (path_color, frame_count), cv2_rgb_img)

        if enable_tracking:
          rgb_pose = tf.transformations.quaternion_matrix(rgb_r)
          rgb_pose[0,3] = rgb_t[0]
          rgb_pose[1,3] = rgb_t[1]
          rgb_pose[2,3] = rgb_t[2]

          write_pose("%s/%06d.pose" % (path_pose, frame_count), rgb_pose)

        frame_count += 1

def main():
  global camera_info_topic

  rospy.init_node('open3d_recorder', anonymous=True)

  # Create TF listener
  tf_listener = tf.TransformListener()

  # TODO: Make these ros parameters
  depth_image_topic = '/camera/depth_registered/image'
  rgb_image_topic = '/camera/rgb/image_raw'
  camera_info_topic = '/camera/rgb/camera_info'
  cache_count = 10
  slop = 0.01 # The delay (in seconds) with which messages can be synchronized.
  allow_headerless = False #allow storing headerless messages with current ROS time instead of timestamp

  depth_sub = Subscriber(depth_image_topic, Image)
  rgb_sub = Subscriber(rgb_image_topic, Image)
  tss = ApproximateTimeSynchronizer([depth_sub, rgb_sub], cache_count, slop, allow_headerless)
  tss.registerCallback(cameraCallback)

  start_server = rospy.Service('start_recording', StartRecording, startRecordingCallback)
  stop_server = rospy.Service('stop_recording', StopRecording, stopRecordingCallback)
  stop_server = rospy.Service('reconstruct', ReconstructSurface, reconstructSystemCallback)

  rospy.spin()