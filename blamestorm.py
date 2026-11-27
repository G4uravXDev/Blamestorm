#!/usr/bin/env python3
"""
Blamestorm — AI-Powered Git & GitHub Assistant (Django Edition)

Standalone Executable & CLI Entrypoint:
Run this command inside any local repository to inspect repository details
and launch the interactive local web dashboard.

Usage:
    blamestorm                          # Start web app for current repository
    blamestorm --info                   # Print full active repo details and exit
    blamestorm --repo /path/to/my-repo  # Target a specific repository
    blamestorm --port 8000              # Specify web server port
    blamestorm --no-browser             # Do not open the browser automatically
"""

import sys
import os
import argparse
import socket
import threading
import time
import webbrowser

# Ensure UTF-8 console output on Windows to prevent charmap/cp1252 encoding crashes
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the specified port is already open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port: int = 8000, host: str = "127.0.0.1", max_attempts: int = 30) -> int:
    """Find the first open port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port, host):
            return port
    return start_port


def print_active_repo_details(target_repo: str, web_url: str = None):
    """Print comprehensive, formatted details of the active git repository."""
    from blame_app.git_engine.runner import is_git_repo, get_repo_root
    from blame_app.git_engine.status import get_status
    from blame_app.git_engine.log import get_commit_history
    from blame_app.git_engine.remote import get_remotes
    from blame_app.models import BlameConfig

    is_valid = is_git_repo(target_repo)
    repo_root = get_repo_root(target_repo) if is_valid else target_repo

    sep = "=" * 76
    print("\n" + sep)
    print("  >> BLAMESTORM -- Active Repository Inspector")
    print(sep)
    print(f"  Target Folder     : {target_repo}")
    print(f"  Repository Root   : {repo_root}")

    if not is_valid:
        print("  Git Status        : [!] NOT a Git repository")
        print("  Recommendation    : Run 'git init' or open the web studio to initialize Git.")
        if web_url:
            print(f"  Web Studio        : {web_url}")
        print(sep + "\n")
        return

    status = get_status(target_repo)
    commits = get_commit_history(max_count=5, cwd=target_repo)
    remotes = get_remotes(cwd=target_repo)

    # Branch & Tracking info
    branch_line = f"  Current Branch    : {status.branch}"
    if status.upstream:
        branch_line += f" (tracking: {status.upstream} | +{status.ahead} ahead / -{status.behind} behind)"
    print(branch_line)

    # Working Tree State
    if status.is_clean:
        print("  Working Tree      : [OK] CLEAN (no uncommitted changes)")
    else:
        print(f"  Working Tree      : [DIRTY] {status.total_changed_files} uncommitted change(s)")

    # Staged changes
    print(f"\n  [+] Staged Changes ({len(status.staged)} file(s)):")
    if status.staged:
        for f in status.staged[:12]:
            print(f"     * [{f.status_code}] {f.path}")
        if len(status.staged) > 12:
            print(f"     ... and {len(status.staged) - 12} more staged file(s)")
    else:
        print("     (no files staged for commit)")

    # Unstaged modifications
    print(f"\n  [*] Unstaged Changes ({len(status.unstaged)} file(s)):")
    if status.unstaged:
        for f in status.unstaged[:12]:
            print(f"     * [{f.status_code}] {f.path}")
        if len(status.unstaged) > 12:
            print(f"     ... and {len(status.unstaged) - 12} more modified file(s)")
    else:
        print("     (no unstaged modifications)")

    # Untracked files
    print(f"\n  [?] Untracked Files ({len(status.untracked)} file(s)):")
    if status.untracked:
        for f in status.untracked[:8]:
            print(f"     * [?] {f.path}")
        if len(status.untracked) > 8:
            print(f"     ... and {len(status.untracked) - 8} more untracked file(s)")
    else:
        print("     (no untracked files)")

    # Saved Stashes
    if status.stash_count > 0:
        print(f"\n  [#] Saved Stashes   : {status.stash_count} stash(es) available")

    # Remotes
    if remotes:
        print(f"\n  [@] Configured Remotes ({len(remotes)}):")
        for r in remotes:
            url_str = r.fetch_url or r.push_url or "no-url"
            print(f"     * {r.name} -> {url_str}")
    else:
        print("\n  [@] Configured Remotes: (none)")

    # Recent Commits
    if commits:
        print(f"\n  [>] Recent Commits on {status.branch}:")
        for c in commits:
            print(f"     * {c.short_hash} ({c.relative_date}) [{c.author_name}] {c.subject}")

    # AI Configuration Status
    try:
        config = BlameConfig.get_solo()
        api_key = config.gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        ai_status = f"Configured [Model: {config.gemini_model}]" if api_key else "Not configured (set in Settings or GEMINI_API_KEY)"
        print(f"\n  [AI] AI Engine      : Google Gemini -- {ai_status}")
    except Exception:
        pass

    if web_url:
        print(f"\n  [URL] Web Studio    : {web_url}")
        print("  [KEY] Shortcuts     : Press '?' in the browser for full keyboard shortcuts cheat sheet")
    print(sep + "\n")


def main():
    # 1. Capture current working directory immediately before any other calls
    initial_cwd = os.getcwd()

    parser = argparse.ArgumentParser(
        description="Blamestorm — AI-Powered Git & GitHub Assistant (Executable Edition)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  blamestorm                       Launch web studio in current repo
  blamestorm --info                Print active repo details to terminal and exit
  blamestorm --repo D:\\MyProject    Open Blamestorm on a specific repository
  blamestorm --port 8080           Run web interface on custom port
        """
    )
    parser.add_argument(
        "--repo", "-r",
        type=str,
        default=None,
        help="Path to the Git repository (defaults to current working directory)"
    )
    parser.add_argument(
        "--info", "--status", "-i",
        action="store_true",
        dest="show_info",
        help="Print all details related to the active repository in terminal and exit"
    )
    parser.add_argument(
        "--port", "-p",
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
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run database migrations and exit"
    )
    args = parser.parse_args()

    # 2. Determine target repository
    target_repo = os.path.abspath(args.repo or initial_cwd)
    os.environ["BLAME_REPO_PATH"] = target_repo
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blame_core.settings")

    # 3. Setup Django environment in-process
    import django
    django.setup()

    # 4. Auto-run database migrations quietly
    from django.core.management import call_command
    try:
        call_command("migrate", interactive=False, verbosity=0)
    except Exception as e:
        sys.stderr.write(f"Migration note: {e}\n")

    if args.migrate:
        print("[✓] Database migrations completed successfully.")
        return

    # 5. Resolve open port
    active_port = args.port
    if not args.show_info and is_port_in_use(active_port, args.host):
        active_port = find_available_port(args.port, args.host)
        if active_port != args.port:
            print(f"  Note: Port {args.port} in use, using port {active_port} instead.")

    web_url = f"http://{args.host}:{active_port}/"

    # 6. Print rich active repository details
    print_active_repo_details(target_repo, web_url=web_url if not args.show_info else None)

    # 7. Exit if user only requested repo details
    if args.show_info:
        return

    # 8. Start automatic browser launch thread
    if not args.no_browser:
        def open_browser():
            time.sleep(1.2)
            print(f"  Opening browser to {web_url} ...")
            webbrowser.open(web_url)
        threading.Thread(target=open_browser, daemon=True).start()

    # 9. Start in-process Django WSGI server
    print(f"  Starting Blamestorm local web server on {web_url} ...")
    print("  Press Ctrl+C to stop the server.\n")

    try:
        call_command("runserver", f"{args.host}:{active_port}", use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n  ⚡ Blamestorm server stopped. Goodbye!")
    except Exception as e:
        print(f"\n  [ERROR] Server error: {e}")


if __name__ == "__main__":
    main()

