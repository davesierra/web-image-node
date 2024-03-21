import cv2

video_capture = cv2.VideoCapture("./alient.mp4")
video_capture.set(cv2.CAP_PROP_FPS, './alient.mp4')

saved_frame_name = 0

while video_capture.isOpened():
    frame_is_read, frame = video_capture.read()

    if frame_is_read:
        cv2.imwrite(f"frame{str(saved_frame_name)}.jpg", frame)
        saved_frame_name += 1

    else:
        print("Could not read the frame.")