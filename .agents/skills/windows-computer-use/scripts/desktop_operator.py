#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desktop Operator: Production-grade Windows Desktop Automation Tool
Handles desktop sandbox escape (exebox -> Default), DPI awareness,
Windows ASFW focus unlocks, SendInput hardware simulation, and window capture.
"""

import sys
import os
import time
import argparse
import ctypes
from ctypes import wintypes
from typing import Optional, List, Dict, Tuple

try:
    import win32gui
    import win32ui
    import win32con
    import win32api
    import win32process
    import win32clipboard
    from PIL import Image
except ImportError as e:
    print(f"[Error] Required Windows libraries missing: {e}", file=sys.stderr)
    sys.exit(1)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 SendInput Structures
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]
    _anonymous_ = ("_i",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_i", _I),
    ]

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

def ensure_desktop_and_dpi():
    """Ensure process is Per-Monitor V2 DPI aware and bound to interactive Default desktop."""
    # 1. DPI Awareness (Per-Monitor V2)
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass

    # 2. Attach thread to user's interactive 'Default' desktop
    try:
        hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hDesk:
            user32.SetThreadDesktop(hDesk)
    except Exception as e:
        print(f"[Warning] Failed to switch thread desktop: {e}", file=sys.stderr)

def get_visible_windows(pattern: Optional[str] = None) -> List[Dict]:
    ensure_desktop_and_dpi()
    windows = []

    def enum_proc(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value
        
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        cls_name = cls_buf.value

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top

        # Filter out 0-sized tooltips or off-screen artifacts
        if w > 10 and h > 10:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pattern is None or pattern.lower() in title.lower() or pattern.lower() in cls_name.lower():
                windows.append({
                    "hwnd": hwnd,
                    "title": title,
                    "class": cls_name,
                    "pid": pid.value,
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": w,
                    "height": h,
                    "is_minimized": bool(user32.IsIconic(hwnd))
                })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if hDesk:
        user32.EnumDesktopWindows(hDesk, WNDENUMPROC(enum_proc), 0)
        user32.CloseDesktop(hDesk)
    else:
        user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
    return windows

def find_window(name_or_hwnd: str) -> Optional[Dict]:
    ensure_desktop_and_dpi()
    if name_or_hwnd.isdigit():
        hwnd = int(name_or_hwnd)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title_buf, 256)
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return {
            "hwnd": hwnd,
            "title": title_buf.value,
            "class": cls_buf.value,
            "pid": pid.value,
            "left": rect.left,
            "top": rect.top,
            "right": rect.right,
            "bottom": rect.bottom,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top,
            "is_minimized": bool(user32.IsIconic(hwnd))
        }

    wins = get_visible_windows(name_or_hwnd)
    if wins:
        # Prefer exact match or first match
        for w in wins:
            if w["title"].lower() == name_or_hwnd.lower():
                return w
        return wins[0]
    return None

def focus_window(hwnd: int) -> bool:
    """Forcefully bring window to foreground using the Alt-key unlock trick."""
    ensure_desktop_and_dpi()
    if not user32.IsWindow(hwnd):
        return False

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE

    # Bypass Windows AllowSetForegroundWindow (ASFW) via Alt-down state
    user32.keybd_event(0x12, 0, 0, 0)
    user32.ShowWindow(hwnd, 5)  # SW_SHOW
    res = user32.SetForegroundWindow(hwnd)
    user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
    user32.SetFocus(hwnd)
    time.sleep(0.2)
    return bool(res)

def capture_window(hwnd: int, output_path: str) -> Tuple[int, int]:
    ensure_desktop_and_dpi()
    if user32.IsIconic(hwnd):
        focus_window(hwnd)
        time.sleep(0.3)

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hwndDC = user32.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # Try PW_RENDERFULLCONTENT = 2, fallback to 0
    res = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
    if not res:
        user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    user32.ReleaseDC(hwnd, hwndDC)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    im.save(output_path)
    return im.size

def client_to_screen(hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
    ensure_desktop_and_dpi()
    pt = wintypes.POINT(client_x, client_y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y)

def mouse_click(screen_x: int, screen_y: int, button: str = "left", clicks: int = 1):
    ensure_desktop_and_dpi()
    user32.SetCursorPos(screen_x, screen_y)
    time.sleep(0.1)

    down_flag = MOUSEEVENTF_LEFTDOWN
    up_flag = MOUSEEVENTF_LEFTUP
    if button.lower() == "right":
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    elif button.lower() == "middle":
        down_flag = MOUSEEVENTF_MIDDLEDOWN
        up_flag = MOUSEEVENTF_MIDDLEUP

    for i in range(clicks):
        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_MOUSE
        inputs[0].mi.dwFlags = down_flag
        inputs[1].type = INPUT_MOUSE
        inputs[1].mi.dwFlags = up_flag
        user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
        if i < clicks - 1:
            time.sleep(0.08)

def send_key_chord(keys: List[str]):
    ensure_desktop_and_dpi()
    VK_MAP = {
        "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
        "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B,
        "space": 0x20, "backspace": 0x08, "back": 0x08, "del": 0x2E,
        "delete": 0x2E, "home": 0x24, "end": 0x23, "up": 0x26,
        "down": 0x28, "left": 0x25, "right": 0x27, "f4": 0x73, "f5": 0x74
    }

    down_vks = []
    for k in keys:
        k_lower = k.lower()
        if k_lower in VK_MAP:
            down_vks.append(VK_MAP[k_lower])
        elif len(k) == 1:
            down_vks.append(ord(k.upper()))

    # Key down
    for vk in down_vks:
        inp = (INPUT * 1)()
        inp[0].type = INPUT_KEYBOARD
        inp[0].ki.wVk = vk
        user32.SendInput(1, inp, ctypes.sizeof(INPUT))
        time.sleep(0.02)

    time.sleep(0.05)

    # Key up in reverse
    for vk in reversed(down_vks):
        inp = (INPUT * 1)()
        inp[0].type = INPUT_KEYBOARD
        inp[0].ki.wVk = vk
        inp[0].ki.dwFlags = KEYEVENTF_KEYUP
        user32.SendInput(1, inp, ctypes.sizeof(INPUT))
        time.sleep(0.02)

def type_text(text: str, press_enter: bool = False, use_clipboard: bool = True):
    ensure_desktop_and_dpi()
    # If clipboard mode or complex/non-ASCII characters: use clipboard + Ctrl+V
    has_unicode = any(ord(c) > 127 for c in text) or "\n" in text
    if use_clipboard or has_unicode:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()
        time.sleep(0.05)
        send_key_chord(["ctrl", "v"])
    else:
        for ch in text:
            send_key_chord([ch])
            time.sleep(0.02)

    if press_enter:
        time.sleep(0.15)
        send_key_chord(["enter"])

def main():
    # 中文 Windows 控制台默认 cp936，打印窗口标题里的非常用字会抛 UnicodeEncodeError
    # （表现为列表打到一半就 Traceback）。强制 UTF-8 输出，与 zhaw CLI 保持一致。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Production Windows Desktop Operator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-windows
    p_list = subparsers.add_parser("list-windows", help="List visible top-level windows")
    p_list.add_argument("--filter", "-f", help="Filter by title/class name")

    # focus
    p_focus = subparsers.add_parser("focus", help="Bring window to front")
    p_focus.add_argument("--target", "-t", required=True, help="Window title, class or HWND")

    # capture-window
    p_cap = subparsers.add_parser("capture-window", help="Capture window bitmap to PNG")
    p_cap.add_argument("--target", "-t", required=True, help="Window title, class or HWND")
    p_cap.add_argument("--output", "-o", required=True, help="Output PNG path")

    # click
    p_click = subparsers.add_parser("click", help="Click at physical screen coordinates")
    p_click.add_argument("--x", type=int, required=True, help="Physical X")
    p_click.add_argument("--y", type=int, required=True, help="Physical Y")
    p_click.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_click.add_argument("--clicks", type=int, default=1)

    # click-client
    p_click_c = subparsers.add_parser("click-client", help="Click relative to window client area")
    p_click_c.add_argument("--target", "-t", required=True, help="Window title or HWND")
    p_click_c.add_argument("--x", type=int, required=True, help="Client relative X")
    p_click_c.add_argument("--y", type=int, required=True, help="Client relative Y")
    p_click_c.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_click_c.add_argument("--clicks", type=int, default=1)

    # type
    p_type = subparsers.add_parser("type", help="Type text into current focused control")
    p_type.add_argument("--text", required=True, help="Text to type")
    p_type.add_argument("--enter", action="store_true", help="Press Enter after typing")
    p_type.add_argument("--direct", action="store_true", help="Send individual keystrokes without clipboard")

    # key
    p_key = subparsers.add_parser("key", help="Send key combinations (e.g. ctrl+v, enter, alt+f4)")
    p_key.add_argument("--chord", required=True, help="Key chord joined by + (e.g. enter, ctrl+c)")

    # dpi-info
    p_dpi = subparsers.add_parser("dpi-info", help="Get display resolution and virtual screen bounds")

    args = parser.parse_args()

    if args.command == "list-windows":
        wins = get_visible_windows(args.filter)
        print(f"Found {len(wins)} windows:")
        for w in wins:
            print(f"  [HWND {w['hwnd']}] PID={w['pid']} Rect=({w['left']},{w['top']},{w['width']}x{w['height']}) Class='{w['class']}' Title='{w['title']}'")

    elif args.command == "focus":
        win = find_window(args.target)
        if not win:
            print(f"Window not found: {args.target}", file=sys.stderr)
            sys.exit(1)
        ok = focus_window(win["hwnd"])
        print(f"Focus result: {ok} for HWND {win['hwnd']} ({win['title']})")

    elif args.command == "capture-window":
        win = find_window(args.target)
        if not win:
            print(f"Window not found: {args.target}", file=sys.stderr)
            sys.exit(1)
        size = capture_window(win["hwnd"], args.output)
        print(f"Saved window image {size[0]}x{size[1]} to: {args.output}")

    elif args.command == "click":
        mouse_click(args.x, args.y, args.button, args.clicks)
        print(f"Clicked {args.button} at physical ({args.x}, {args.y}) x{args.clicks}")

    elif args.command == "click-client":
        win = find_window(args.target)
        if not win:
            print(f"Window not found: {args.target}", file=sys.stderr)
            sys.exit(1)
        sx, sy = client_to_screen(win["hwnd"], args.x, args.y)
        mouse_click(sx, sy, args.button, args.clicks)
        print(f"Converted client ({args.x}, {args.y}) -> physical ({sx}, {sy}), clicked {args.button}")

    elif args.command == "type":
        type_text(args.text, press_enter=args.enter, use_clipboard=not args.direct)
        print(f"Typed text (enter={args.enter})")

    elif args.command == "key":
        chord = [k.strip() for k in args.chord.split("+")]
        send_key_chord(chord)
        print(f"Sent key chord: {args.chord}")

    elif args.command == "dpi-info":
        ensure_desktop_and_dpi()
        w = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        h = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        pw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        ph = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        print(f"Physical Screen: {pw}x{ph}, Virtual Screen: {w}x{h}")

if __name__ == "__main__":
    main()
