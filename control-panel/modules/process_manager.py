"""
Manages subprocess lifecycle for face tracker and Unity app.
"""

import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_conda() -> str:
    """Find conda executable, checking common installation paths."""
    conda = shutil.which("conda")
    if conda:
        return conda

    home = os.path.expanduser("~")
    candidates = [
        "/opt/miniconda3/bin/conda",
        "/opt/anaconda3/bin/conda",
        "/opt/homebrew/anaconda3/bin/conda",
        "/opt/homebrew/miniconda3/bin/conda",
        f"{home}/anaconda3/bin/conda",
        f"{home}/miniconda3/bin/conda",
        f"{home}/opt/anaconda3/bin/conda",
        f"{home}/opt/miniconda3/bin/conda",
        "/usr/local/anaconda3/bin/conda",
        "/usr/local/miniconda3/bin/conda",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    return "conda"  # fallback, will fail with a clear error


class ProcessManager:
    def __init__(self):
        self._processes: dict[str, subprocess.Popen] = {}
        self._log_queues: dict[str, queue.Queue] = {}

    def _start(self, name: str, cmd: list[str], cwd: Optional[str] = None,
               extra_env: Optional[dict] = None) -> bool:
        if self.is_running(name):
            return False

        log_q: queue.Queue = queue.Queue(maxsize=500)
        self._log_queues[name] = log_q

        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)

        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,  # puts process in its own group so we can kill it entirely
            env=env,
        )
        self._processes[name] = proc

        # Reader thread: forwards stdout lines into the queue
        t = threading.Thread(
            target=self._reader_thread,
            args=(name, proc, log_q),
            daemon=True,
        )
        t.start()
        return True

    def _reader_thread(self, name: str, proc: subprocess.Popen, log_q: queue.Queue):
        try:
            for line in iter(proc.stdout.readline, ""):
                stripped = line.strip()
                if stripped:
                    try:
                        log_q.put_nowait(stripped)
                    except queue.Full:
                        pass
        except Exception:
            pass

    def stop(self, name: str) -> bool:
        proc = self._processes.get(name)
        if proc and proc.poll() is None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    proc.kill()
            return True
        return False

    def is_running(self, name: str) -> bool:
        proc = self._processes.get(name)
        return proc is not None and proc.poll() is None

    def drain_logs(self, name: str) -> list[str]:
        """Return all pending log lines without blocking."""
        log_q = self._log_queues.get(name)
        if not log_q:
            return []
        lines = []
        while True:
            try:
                lines.append(log_q.get_nowait())
            except queue.Empty:
                break
        return lines

    # --- Module-specific launchers ---

    def start_face_tracker(self) -> bool:
        conda = find_conda()
        return self._start(
            "face_tracker",
            [conda, "run", "-n", "Vtuber", "python", "main.py", "--no-interactive"],
            cwd=os.path.join(PROJECT_ROOT, "PythonFaceTracker"),
        )

    def start_text_driver(self) -> bool:
        conda = find_conda()
        return self._start(
            "text_driver",
            [conda, "run", "-n", "Vtuber", "python", "main.py"],
            cwd=os.path.join(PROJECT_ROOT, "PythonTextDriver"),
        )

    def start_unity(self, app_path: str) -> tuple[bool, str]:
        """Launch the packaged Unity app as a tracked subprocess."""
        if not app_path or not os.path.exists(app_path):
            return False, "路径不存在"
        if self.is_running("unity"):
            return False, "已在运行"

        if sys.platform == "darwin" and app_path.endswith(".app"):
            binary = _find_app_binary(app_path)
            if not binary:
                return False, "在 .app 包内找不到可执行文件"
            cmd = [binary]
        else:
            cmd = [app_path]

        ok = self._start("unity", cmd)
        return ok, "" if ok else "启动失败"



def _find_app_binary(app_path: str) -> Optional[str]:
    """Find the executable binary inside a macOS .app bundle."""
    macos_dir = os.path.join(app_path, "Contents", "MacOS")
    if not os.path.isdir(macos_dir):
        return None
    # Try the conventional name first (same as .app without extension)
    app_name = os.path.basename(app_path).replace(".app", "")
    candidate = os.path.join(macos_dir, app_name)
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    # Fallback: first executable found in Contents/MacOS
    for entry in os.scandir(macos_dir):
        if entry.is_file() and os.access(entry.path, os.X_OK):
            return entry.path
    return None


# Directories to skip when scanning for app bundles
_SKIP_DIRS = {
    "Library", "Temp", ".git", "__pycache__", "node_modules",
    "Logs", "obj", "Packages", "ProjectSettings",
}


def discover_apps(root: str = PROJECT_ROOT) -> list[str]:
    """
    Scan root (2 levels deep) for launchable app bundles / executables.
    Returns absolute paths sorted alphabetically.
    """
    found = []
    if sys.platform == "darwin":
        _scan_for_apps_mac(root, depth=0, results=found)
    elif sys.platform == "win32":
        _scan_for_exes(root, depth=0, results=found)
    else:
        _scan_for_exes(root, depth=0, results=found)
    return sorted(set(found))


def _scan_for_apps_mac(directory: str, depth: int, results: list):
    if depth > 2:
        return
    try:
        for entry in os.scandir(directory):
            if entry.name.startswith(".") or entry.name in _SKIP_DIRS:
                continue
            if "DoNotShip" in entry.name or "BurstDebugInformation" in entry.name:
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name.endswith(".app"):
                    results.append(entry.path)
                else:
                    _scan_for_apps_mac(entry.path, depth + 1, results)
    except PermissionError:
        pass


def _scan_for_exes(directory: str, depth: int, results: list):
    if depth > 2:
        return
    try:
        for entry in os.scandir(directory):
            if entry.name.startswith(".") or entry.name in _SKIP_DIRS:
                continue
            if entry.is_file() and entry.name.endswith(".exe"):
                results.append(entry.path)
            elif entry.is_dir(follow_symlinks=False):
                _scan_for_exes(entry.path, depth + 1, results)
    except PermissionError:
        pass
