"""
摄像头检测工具 - 列出所有可用的摄像头
Camera Detection Tool - Lists all available cameras
"""

import cv2
import platform


def test_camera(index: int, timeout_ms: int = 3000) -> dict:
    """
    测试指定索引的摄像头是否可用
    Test if a camera at the specified index is available

    Args:
        index: Camera index to test
        timeout_ms: Timeout in milliseconds for opening camera

    Returns:
        dict with camera info if available, None otherwise
    """
    cap = cv2.VideoCapture(index)

    # 设置超时时间（仅在支持的平台上）
    # Set timeout (only on supported platforms)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)

    if not cap.isOpened():
        return None

    # 尝试读取一帧来确认摄像头真的可用
    # Try to read a frame to confirm camera is actually working
    ret, frame = cap.read()

    if not ret:
        cap.release()
        return None

    # 获取摄像头信息
    # Get camera information
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    backend = cap.getBackendName()

    # 尝试获取摄像头名称（不是所有平台都支持）
    # Try to get camera name (not supported on all platforms)
    camera_name = None
    try:
        # 某些 OpenCV 版本支持这个属性
        # Some OpenCV versions support this property
        camera_name = cap.get(cv2.CAP_PROP_DESCRIPTION)
    except:
        pass

    cap.release()

    return {
        'index': index,
        'width': width,
        'height': height,
        'fps': fps if fps > 0 else 'Unknown',
        'backend': backend,
        'name': camera_name if camera_name else 'Unknown'
    }


def list_all_cameras(max_index: int = 10):
    """
    列出所有可用的摄像头
    List all available cameras

    Args:
        max_index: Maximum camera index to check (default: 10)
    """
    print("=" * 80)
    print("摄像头检测工具 / Camera Detection Tool")
    print("=" * 80)
    print(f"系统平台 / Platform: {platform.system()} {platform.release()}")
    print(f"OpenCV 版本 / Version: {cv2.__version__}")
    print("=" * 80)
    print(f"\n正在扫描摄像头索引 0-{max_index}...")
    print(f"Scanning camera indices 0-{max_index}...\n")

    available_cameras = []

    for i in range(max_index + 1):
        print(f"检测索引 {i}... ", end='', flush=True)

        camera_info = test_camera(i)

        if camera_info:
            available_cameras.append(camera_info)
            print(f"✓ 可用 / Available")
        else:
            print(f"✗ 不可用 / Not available")

    print("\n" + "=" * 80)
    print(f"找到 {len(available_cameras)} 个可用摄像头 / Found {len(available_cameras)} available camera(s)")
    print("=" * 80)

    if not available_cameras:
        print("\n⚠️  未找到可用摄像头！")
        print("⚠️  No available cameras found!")
        print("\n可能的原因 / Possible reasons:")
        print("1. 摄像头未连接 / Camera not connected")
        print("2. 摄像头权限未授予 / Camera permission not granted")
        print("3. 摄像头被其他程序占用 / Camera in use by another program")
        return

    print("\n详细信息 / Details:\n")

    for cam in available_cameras:
        print(f"┌─ 摄像头索引 / Camera Index: {cam['index']}")
        print(f"│  名称 / Name:     {cam['name']}")
        print(f"│  分辨率 / Resolution: {cam['width']}x{cam['height']}")
        print(f"│  帧率 / FPS:      {cam['fps']}")
        print(f"│  后端 / Backend:  {cam['backend']}")
        print("└" + "─" * 60)
        print()

    print("=" * 80)
    print("使用说明 / Instructions:")
    print("=" * 80)
    print(f"要使用指定摄像头，请修改 config.json 文件中的 camera.index 值")
    print(f"To use a specific camera, modify the camera.index value in config.json")
    print()
    print("例如 / Example:")
    print('  "camera": {')
    print(f'    "index": {available_cameras[0]["index"]},  ← 修改这个数字 / Change this number')
    print('    "width": 640,')
    print('    "height": 480,')
    print('    "fps": 30')
    print('  }')
    print("=" * 80)

    # 在 Mac 上给出额外提示
    # Give additional tips on Mac
    if platform.system() == "Darwin":
        print("\n💡 Mac 用户提示 / Mac User Tips:")
        print("─" * 80)
        print("• 内置摄像头通常是索引 0 / Built-in camera is usually index 0")
        print("• 外置摄像头可能是索引 1 或更高 / External cameras may be index 1 or higher")
        print("• 首次运行时可能需要授予摄像头权限 / May need to grant camera permission on first run")
        print("  (系统偏好设置 > 安全性与隐私 > 摄像头)")
        print("  (System Preferences > Security & Privacy > Camera)")
        print("─" * 80)


if __name__ == "__main__":
    try:
        list_all_cameras(max_index=10)
    except KeyboardInterrupt:
        print("\n\n中断 / Interrupted")
    except Exception as e:
        print(f"\n错误 / Error: {e}")
        import traceback
        traceback.print_exc()
