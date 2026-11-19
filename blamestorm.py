#!/usr/bin/env python3
"""
Blamestorm — AI-Powered Git & GitHub Assistant (Django Edition)

Launcher script:
Run this script inside any repository to immediately start the local web application
and open it in your web browser.

Usage:
    python blamestorm.py
    python blamestorm.py --repo /path/to/my-repo
    python blamestorm.py --port 8000 --no-browser
"""

import sys
import os
import argparse
import subprocess
import webbrowser
import time
import socket


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the specified port is already open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Blamestorm — AI-Powered Git & GitHub Assistant Web App"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Path to the local Git repository (defaults to current working directory)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the Django web server on (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically"
    )
    args = parser.parse_args()

    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    target_repo = args.repo or os.getcwd()
    target_repo = os.path.abspath(target_repo)

    os.environ["ZIT_REPO_PATH"] = target_repo

    url = f"http://{args.host}:{args.port}/"

    print("\n" + "=" * 65)
    print("  ⚡ Blamestorm — AI-Powered Git & GitHub Assistant (Django Edition)")
    print("=" * 65)
    print(f"  Target Repository : {target_repo}")
    print(f"  Web Interface     : {url}")
    print(f"  AI Provider       : Google Gemini API")
    print("=" * 65 + "\n")

    if not args.no_browser:
        import threading
        def open_browser():
            time.sleep(1.5)
            print(f"  Opening browser to {url} ...")
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    cmd = [sys.executable, "manage.py", "runserver", f"{args.host}:{args.port}"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n  Blamestorm server stopped. Goodbye!")


if __name__ == "__main__":
    main()
