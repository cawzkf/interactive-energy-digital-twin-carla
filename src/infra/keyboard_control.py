"""
Direct (zero-delay) keyboard reader for manual CARLA control on Windows.

Polls the global key state via GetAsyncKeyState (no window focus, no extra
dependency). Joystick/gamepad works too when mapped to WASD by JoyToKey/Xpadder.
Windows-only; imported lazily by the CARLA acquisition.
"""
import ctypes

_user32 = ctypes.windll.user32

_VK = {"W": 0x57, "A": 0x41, "S": 0x53, "D": 0x44, "P": 0x50}


def _is_down(vk: int) -> bool:
    return (_user32.GetAsyncKeyState(vk) & 0x8000) != 0


def read_control() -> dict:
    """WASD -> control. W=forward, S=reverse, A/D=steer, P=toggle autopilot."""
    w, a, s, d = (_is_down(_VK[k]) for k in ("W", "A", "S", "D"))
    steer = (0.5 if d else 0.0) - (0.5 if a else 0.0)
    return {
        "throttle": 0.7 if (w or s) else 0.0,
        "reverse": bool(s and not w),
        "brake": 0.0,
        "steer": steer,
        "toggle": _is_down(_VK["P"]),
    }
