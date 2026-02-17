"""
VibeVtuber Face Tracker - Main Entry Point
Captures webcam feed, processes with MediaPipe, and sends data to Unity via UDP
"""

import cv2
import json
import time
import os
import sys
from face_tracker import FaceTracker
from network_sender import NetworkSender


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        return json.load(f)


def test_camera(index: int, timeout_ms: int = 2000) -> dict:
    """
    Test if a camera at the specified index is available

    Args:
        index: Camera index to test
        timeout_ms: Timeout in milliseconds for opening camera

    Returns:
        dict with camera info if available, None otherwise
    """
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)

    if not cap.isOpened():
        return None

    # Try to read a frame to confirm camera is actually working
    ret, frame = cap.read()

    if not ret:
        cap.release()
        return None

    # Get camera information
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    backend = cap.getBackendName()

    cap.release()

    return {
        'index': index,
        'width': width,
        'height': height,
        'fps': fps if fps > 0 else 'Unknown',
        'backend': backend
    }


def select_camera(config_camera_index: int, max_index: int = 10) -> int:
    """
    Scan for available cameras and let user select one

    Args:
        config_camera_index: Camera index from config.json
        max_index: Maximum camera index to check

    Returns:
        Selected camera index
    """
    print("\n" + "=" * 70)
    print("摄像头检测 / Camera Detection")
    print("=" * 70)
    print(f"正在扫描摄像头 (索引 0-{max_index})...")
    print(f"Scanning cameras (index 0-{max_index})...\n")

    available_cameras = []

    # Scan all cameras
    for i in range(max_index + 1):
        # Suppress OpenCV warnings during scanning
        camera_info = test_camera(i, timeout_ms=1500)

        if camera_info:
            available_cameras.append(camera_info)

    if not available_cameras:
        print("❌ 未找到可用摄像头！")
        print("❌ No available cameras found!")
        print("\n可能的原因 / Possible reasons:")
        print("  • 摄像头未连接 / Camera not connected")
        print("  • 摄像头权限未授予 / Camera permission not granted")
        print("  • 摄像头被其他程序占用 / Camera in use by another program")
        print("=" * 70)
        return None

    print(f"找到 {len(available_cameras)} 个可用摄像头 / Found {len(available_cameras)} camera(s)\n")
    print("=" * 70)

    # Display available cameras
    for i, cam in enumerate(available_cameras):
        is_config_default = cam['index'] == config_camera_index
        default_marker = " ← 配置文件默认 (config default)" if is_config_default else ""

        print(f"[{i+1}] 索引 {cam['index']}: {cam['width']}x{cam['height']} @ {cam['fps']}fps "
              f"({cam['backend']}){default_marker}")

    print("=" * 70)

    # Check if config camera is available
    config_cam_available = any(cam['index'] == config_camera_index for cam in available_cameras)

    # User selection
    if config_cam_available:
        print(f"\n配置文件中的摄像头 (索引 {config_camera_index}) 可用")
        print(f"Config camera (index {config_camera_index}) is available")
        print(f"\n请选择 / Select:")
        print(f"  [Enter] - 使用配置文件中的摄像头 {config_camera_index} / Use config camera {config_camera_index}")
        print(f"  [1-{len(available_cameras)}] - 选择其他摄像头 / Select another camera")
        print(f"  [q] - 退出程序 / Quit")
    else:
        print(f"\n⚠️  配置文件中的摄像头 (索引 {config_camera_index}) 不可用")
        print(f"⚠️  Config camera (index {config_camera_index}) is not available")
        print(f"\n请选择摄像头 [1-{len(available_cameras)}] 或 [q] 退出 / Select camera [1-{len(available_cameras)}] or [q] to quit:")

    while True:
        try:
            choice = input("\n选择 / Choice: ").strip()

            # Quit
            if choice.lower() == 'q':
                print("退出程序 / Exiting...")
                return None

            # Use config default (if available)
            if choice == '' and config_cam_available:
                selected_index = config_camera_index
                print(f"✓ 使用配置摄像头 {selected_index}")
                print(f"✓ Using config camera {selected_index}")
                return selected_index

            # Select by number
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_cameras):
                selected_index = available_cameras[choice_num - 1]['index']
                print(f"✓ 已选择摄像头 {selected_index}")
                print(f"✓ Selected camera {selected_index}")
                return selected_index
            else:
                print(f"❌ 无效选择，请输入 1-{len(available_cameras)} / Invalid choice, enter 1-{len(available_cameras)}")

        except ValueError:
            print(f"❌ 无效输入 / Invalid input")
        except KeyboardInterrupt:
            print("\n\n退出程序 / Exiting...")
            return None


def main():
    print("=" * 70)
    print("VibeVtuber Face Tracker")
    print("=" * 70)

    # Load configuration
    try:
        config = load_config()
        print("[Config] Loaded configuration from config.json")
    except Exception as e:
        print(f"[Error] Failed to load config: {e}")
        return

    # Select camera
    selected_camera_index = select_camera(config['camera']['index'], max_index=10)

    if selected_camera_index is None:
        print("[Info] No camera selected, exiting...")
        return

    # Update camera index in config
    config['camera']['index'] = selected_camera_index

    # Check if model file exists
    model_path = config['mediapipe']['model_path']
    if not os.path.exists(model_path):
        print(f"[Error] MediaPipe model not found at: {model_path}")
        print("Please download 'face_landmarker_v2_with_blendshapes.task' from:")
        print("https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task")
        print(f"And place it in: {os.path.dirname(model_path)}/")
        return

    # Initialize face tracker
    print("\n[MediaPipe] Initializing face landmarker...")
    try:
        tracker = FaceTracker(
            model_path=model_path,
            min_detection_confidence=config['mediapipe']['min_detection_confidence'],
            min_tracking_confidence=config['mediapipe']['min_tracking_confidence'],
            num_faces=config['mediapipe']['num_faces']
        )
        print("[MediaPipe] Face landmarker initialized successfully")
    except Exception as e:
        print(f"[Error] Failed to initialize face tracker: {e}")
        return

    # Initialize network sender
    network = NetworkSender(
        host=config['network']['host'],
        port=config['network']['port']
    )

    # Initialize webcam
    print(f"\n[Camera] Opening camera {config['camera']['index']}...")
    cap = cv2.VideoCapture(config['camera']['index'])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['camera']['width'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['camera']['height'])
    cap.set(cv2.CAP_PROP_FPS, config['camera']['fps'])

    if not cap.isOpened():
        print("[Error] Failed to open camera")
        tracker.close()
        network.close()
        return

    print("[Camera] Camera opened successfully")
    print(f"[Info] Resolution: {config['camera']['width']}x{config['camera']['height']} @ {config['camera']['fps']}fps")
    print(f"[Info] Sending data to {config['network']['host']}:{config['network']['port']}")
    print("\nKeyboard Controls:")
    print("  'q' - Quit")
    print("  's' - Toggle debug window")
    print("  'd' - Toggle detailed terminal output (shows ALL parameters sent to Unity)")
    print("=" * 70)

    # Main loop variables
    show_window = config['debug']['show_window']
    print_fps = config['debug']['print_fps']
    detailed_output = False  # Toggle for detailed terminal output
    fps_update_interval = 1.0  # Print FPS every second
    last_fps_time = time.time()
    frame_count = 0
    fps = 0.0

    try:
        while True:
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                print("[Warning] Failed to read frame from camera")
                time.sleep(0.1)
                continue

            # Process frame with MediaPipe
            face_data = tracker.process_frame(frame, alpha=config['smoothing']['alpha'])

            # Send data to Unity
            network.send_face_data(face_data)

            # Calculate FPS
            frame_count += 1
            current_time = time.time()
            elapsed = current_time - last_fps_time

            if elapsed >= fps_update_interval:
                fps = frame_count / elapsed
                frame_count = 0
                last_fps_time = current_time

                if print_fps:
                    if face_data:
                        bs = face_data['blendshapes']
                        jaw = bs.get('jawOpen', 0.0)
                        smile = (bs.get('mouthSmileLeft', 0.0) + bs.get('mouthSmileRight', 0.0)) / 2.0
                        blink_l = bs.get('eyeBlinkLeft', 0.0)
                        blink_r = bs.get('eyeBlinkRight', 0.0)

                        if detailed_output:
                            # Detailed output with ALL parameters sent to Unity
                            hr = face_data['head_rotation']

                            print(f"\n{'='*60}")
                            print(f"[Status] FPS: {fps:.1f} | FACE DETECTED")
                            print(f"{'='*60}")

                            # Head rotation
                            print(f"HEAD ROTATION:")
                            print(f"  Yaw={hr['yaw']:6.1f}° | Pitch={hr['pitch']:6.1f}° | Roll={hr['roll']:6.1f}°")

                            # Mouth parameters
                            print(f"\nMOUTH:")
                            print(f"  JawOpen={bs.get('jawOpen', 0.0):.3f}")
                            print(f"  SmileL={bs.get('mouthSmileLeft', 0.0):.3f} | SmileR={bs.get('mouthSmileRight', 0.0):.3f}")
                            print(f"  FrownL={bs.get('mouthFrownLeft', 0.0):.3f} | FrownR={bs.get('mouthFrownRight', 0.0):.3f}")
                            print(f"  Pucker={bs.get('mouthPucker', 0.0):.3f}")
                            print(f"  Left={bs.get('mouthLeft', 0.0):.3f} | Right={bs.get('mouthRight', 0.0):.3f}")

                            # Eye blink
                            print(f"\nEYE BLINK:")
                            print(f"  BlinkL={bs.get('eyeBlinkLeft', 0.0):.3f} | BlinkR={bs.get('eyeBlinkRight', 0.0):.3f}")
                            print(f"  SquintL={bs.get('eyeSquintLeft', 0.0):.3f} | SquintR={bs.get('eyeSquintRight', 0.0):.3f}")
                            print(f"  WideL={bs.get('eyeWideLeft', 0.0):.3f} | WideR={bs.get('eyeWideRight', 0.0):.3f}")

                            # Eye look direction
                            print(f"\nEYE LOOK LEFT:")
                            print(f"  Up={bs.get('eyeLookUpLeft', 0.0):.3f} | Down={bs.get('eyeLookDownLeft', 0.0):.3f}")
                            print(f"  In={bs.get('eyeLookInLeft', 0.0):.3f} | Out={bs.get('eyeLookOutLeft', 0.0):.3f}")

                            print(f"\nEYE LOOK RIGHT:")
                            print(f"  Up={bs.get('eyeLookUpRight', 0.0):.3f} | Down={bs.get('eyeLookDownRight', 0.0):.3f}")
                            print(f"  In={bs.get('eyeLookInRight', 0.0):.3f} | Out={bs.get('eyeLookOutRight', 0.0):.3f}")

                            # Eyebrow parameters (separated L/R)
                            print(f"\nEYEBROWS:")
                            print(f"  InnerUp={bs.get('browInnerUp', 0.0):.3f}")
                            print(f"  OuterUpL={bs.get('browOuterUpLeft', 0.0):.3f} | OuterUpR={bs.get('browOuterUpRight', 0.0):.3f}")
                            print(f"  DownL={bs.get('browDownLeft', 0.0):.3f} | DownR={bs.get('browDownRight', 0.0):.3f}")
                            print(f"{'='*60}")
                        else:
                            # Compact output
                            print(f"[Status] FPS: {fps:.1f} | FACE | "
                                  f"Jaw: {jaw:.2f} | Smile: {smile:.2f} | "
                                  f"BlinkL: {blink_l:.2f} | BlinkR: {blink_r:.2f}")
                    else:
                        print(f"[Status] FPS: {fps:.1f} | NO FACE")

            # Debug visualization
            if show_window:
                # Draw face detection status
                status_text = f"FPS: {fps:.1f}"
                color = (0, 255, 0) if face_data else (0, 0, 255)
                cv2.putText(frame, status_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                if face_data:
                    bs = face_data['blendshapes']  # Blendshapes dictionary
                    hr = face_data['head_rotation']
                    y_pos = 60
                    line_height = 25

                    # Head rotation info
                    cv2.putText(frame, "=== HEAD ROTATION ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height
                    cv2.putText(frame, f"Yaw:   {hr['yaw']:6.1f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height
                    cv2.putText(frame, f"Pitch: {hr['pitch']:6.1f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height
                    cv2.putText(frame, f"Roll:  {hr['roll']:6.1f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height + 10

                    # Mouth parameters
                    cv2.putText(frame, "=== MOUTH ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height

                    jaw_open = bs.get('jawOpen', 0.0)
                    cv2.putText(frame, f"JawOpen: {jaw_open:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    # Visual bar for jaw open
                    bar_width = int(jaw_open * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (0, 255, 0), -1)
                    y_pos += line_height

                    smile_l = bs.get('mouthSmileLeft', 0.0)
                    smile_r = bs.get('mouthSmileRight', 0.0)
                    smile_avg = (smile_l + smile_r) / 2.0
                    cv2.putText(frame, f"Smile:   {smile_avg:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(smile_avg * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (0, 255, 255), -1)
                    y_pos += line_height

                    frown_l = bs.get('mouthFrownLeft', 0.0)
                    frown_r = bs.get('mouthFrownRight', 0.0)
                    frown_avg = (frown_l + frown_r) / 2.0
                    cv2.putText(frame, f"Frown:   {frown_avg:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(frown_avg * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (255, 100, 100), -1)
                    y_pos += line_height

                    pucker = bs.get('mouthPucker', 0.0)
                    cv2.putText(frame, f"Pucker:  {pucker:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height + 10

                    # Eye blink parameters
                    cv2.putText(frame, "=== EYES ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height

                    blink_l = bs.get('eyeBlinkLeft', 0.0)
                    cv2.putText(frame, f"BlinkL:  {blink_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(blink_l * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (255, 200, 0), -1)
                    y_pos += line_height

                    blink_r = bs.get('eyeBlinkRight', 0.0)
                    cv2.putText(frame, f"BlinkR:  {blink_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(blink_r * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (255, 200, 0), -1)
                    y_pos += line_height + 10

                    # Eyebrow parameters (LEFT and RIGHT separated)
                    cv2.putText(frame, "=== EYEBROWS ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height

                    # Inner brow (center)
                    brow_inner = bs.get('browInnerUp', 0.0)
                    cv2.putText(frame, f"InnerUp: {brow_inner:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(brow_inner * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (200, 150, 255), -1)
                    y_pos += line_height

                    # Left brow
                    brow_outer_l = bs.get('browOuterUpLeft', 0.0)
                    cv2.putText(frame, f"OuterL:  {brow_outer_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(brow_outer_l * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (150, 200, 255), -1)
                    y_pos += line_height

                    # Right brow
                    brow_outer_r = bs.get('browOuterUpRight', 0.0)
                    cv2.putText(frame, f"OuterR:  {brow_outer_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(brow_outer_r * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (150, 200, 255), -1)
                    y_pos += line_height

                    # Brow down left
                    brow_down_l = bs.get('browDownLeft', 0.0)
                    cv2.putText(frame, f"DownL:   {brow_down_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(brow_down_l * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (100, 150, 200), -1)
                    y_pos += line_height

                    # Brow down right
                    brow_down_r = bs.get('browDownRight', 0.0)
                    cv2.putText(frame, f"DownR:   {brow_down_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    bar_width = int(brow_down_r * 100)
                    cv2.rectangle(frame, (180, y_pos - 15), (180 + bar_width, y_pos - 5), (100, 150, 200), -1)
                    y_pos += line_height + 10

                    # Eye look direction (LEFT eye)
                    cv2.putText(frame, "=== EYE LOOK (LEFT) ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height

                    eye_look_up_l = bs.get('eyeLookUpLeft', 0.0)
                    cv2.putText(frame, f"Up:      {eye_look_up_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_look_down_l = bs.get('eyeLookDownLeft', 0.0)
                    cv2.putText(frame, f"Down:    {eye_look_down_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_look_in_l = bs.get('eyeLookInLeft', 0.0)
                    cv2.putText(frame, f"In:      {eye_look_in_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_look_out_l = bs.get('eyeLookOutLeft', 0.0)
                    cv2.putText(frame, f"Out:     {eye_look_out_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height + 10

                    # Eye look direction (RIGHT eye)
                    cv2.putText(frame, "=== EYE LOOK (RIGHT) ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height

                    eye_look_up_r = bs.get('eyeLookUpRight', 0.0)
                    cv2.putText(frame, f"Up:      {eye_look_up_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_look_down_r = bs.get('eyeLookDownRight', 0.0)
                    cv2.putText(frame, f"Down:    {eye_look_down_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_look_in_r = bs.get('eyeLookInRight', 0.0)
                    cv2.putText(frame, f"In:      {eye_look_in_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_look_out_r = bs.get('eyeLookOutRight', 0.0)
                    cv2.putText(frame, f"Out:     {eye_look_out_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height + 10

                    # Eye squint/wide
                    cv2.putText(frame, "=== EYE SQUINT/WIDE ===", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                    y_pos += line_height

                    eye_squint_l = bs.get('eyeSquintLeft', 0.0)
                    cv2.putText(frame, f"SquintL: {eye_squint_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_squint_r = bs.get('eyeSquintRight', 0.0)
                    cv2.putText(frame, f"SquintR: {eye_squint_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_wide_l = bs.get('eyeWideLeft', 0.0)
                    cv2.putText(frame, f"WideL:   {eye_wide_l:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_pos += line_height

                    eye_wide_r = bs.get('eyeWideRight', 0.0)
                    cv2.putText(frame, f"WideR:   {eye_wide_r:.3f}", (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                else:
                    cv2.putText(frame, "NO FACE DETECTED", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                cv2.imshow('VibeVtuber Face Tracker', frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[Info] Quit requested")
                break
            elif key == ord('s'):
                show_window = not show_window
                if not show_window:
                    cv2.destroyAllWindows()
                print(f"[Debug] Window display: {'ON' if show_window else 'OFF'}")
            elif key == ord('d'):
                detailed_output = not detailed_output
                print(f"[Debug] Detailed terminal output: {'ON' if detailed_output else 'OFF'}")

    except KeyboardInterrupt:
        print("\n[Info] Interrupted by user")

    finally:
        # Cleanup
        print("[Cleanup] Releasing resources...")
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()
        network.close()
        print("[Cleanup] Done")
        print("=" * 60)


if __name__ == "__main__":
    main()
