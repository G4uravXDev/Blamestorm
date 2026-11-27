
# Blamestorm — AI-Powered Git & GitHub Studio

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django 6.1](https://img.shields.io/badge/Django-6.1-092E20.svg)](https://www.djangoproject.com/)
[![Google Gemini API](https://img.shields.io/badge/AI-Google%20Gemini-8E75C2.svg)](https://aistudio.google.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-informational.svg)]()
[![Standalone Executable](https://img.shields.io/badge/Binary-Zero--Dependency%20EXE-success.svg)]()

**A developer-grade, AI-powered Git and GitHub manager with an interactive 3-pane Code Studio, autonomous agent operations, built-in credential scanning, and a zero-dependency standalone CLI executable.**

[Features](#-core-features) •
[Standalone Executable](#-standalone-executable-zero-dependencies) •
[CLI Usage](#-cli-command-line-interface) •
[AI Mentor Studio](#-ai-mentor-code-studio-3-pane-workspace) •
[Autonomous Agent](#-autonomous-ai-agent--strict-safety-protocol) •
[Quick Start](#-developer-quick-start-from-source) •
[Shortcuts](#-single-key-keyboard-shortcuts)

</div>

---

## 🌟 Overview

**Blamestorm** bridges the gap between terminal Git proficiency and graphical IDE power. Designed to run directly against any local repository on your machine, Blamestorm delivers:

- 🖥️ **Dual Interface**: A lightning-fast **command-line repository inspector** for quick terminal status and a local **developer web studio** with single-key shortcuts.
- 📦 **Zero-Dependency Portable Binary**: Packaged into a standalone `blamestorm.exe` that runs anywhere globally without requiring Python, pip, or virtual environments.
- 🤖 **AI Mentor Code Studio**: A 3-pane interactive workspace featuring your active file, an embedded CMD terminal with retro pixelated thinking feedback, and real-time suggested code updates with 1-click file application.
- ⚡ **Autonomous AI Agent Mode**: Conversational Git assistant powered by Google Gemini that can plan and execute multi-step Git workflows while enforcing **strict autonomous commit and destructive operation prohibitions**.
- 🔒 **Zero-Leak Secret Engine**: Pre-stage and pre-commit scanner with 20+ signature rules catching API keys, private tokens, and credentials before they reach version control.
- 🎨 **Developer-Grade UI**: Built with pure Django templates, custom dark styling, and crisp SVG vector icons (no cartoon emojis).

---

## 📦 Standalone Executable (Zero Dependencies)

Blamestorm compiles into a completely self-contained binary (`blamestorm.exe`) containing the WSGI server, Django framework, SQLite database engine, Google Gemini SDK, templates, and static assets.

### 1-Click Global Installation (Windows)
Run the automated installer included in the repository:
```cmd
install_cli.bat
```
*This copies `blamestorm.exe` directly to `%LOCALAPPDATA%\Microsoft\WindowsApps\blamestorm.exe`, making `blamestorm` available in every command prompt, PowerShell window, and terminal globally.*

### Building from Source (PyInstaller)
To recompile the standalone binary from source at any time:
```bash
pip install pyinstaller
pyinstaller blamestorm.spec
```
The compiled output is generated at `dist/blamestorm.exe`.

---

## 💻 CLI (Command Line Interface)

Run `blamestorm` in any terminal inside **any Git repository** to instantly inspect status or open the web studio:

### 1. Active Repository Inspector (`--info`)
Quickly view your active repository health, branch tracking, working tree state, and staged/unstaged breakdown without opening a browser:

```bash
blamestorm --info
# or
blamestorm -i
```

**Terminal Output Example:**
```text
============================================================================
  >> BLAMESTORM -- Active Repository Inspector
============================================================================
  Target Folder     : C:\Users\dev\projects\my-app
  Repository Root   : C:\Users\dev\projects\my-app
  Current Branch    : main (tracking: origin/main | +0 ahead / -0 behind)
  Working Tree      : [DIRTY] 3 uncommitted change(s)

  [+] Staged Changes (1 file(s)):
     * [M] src/auth.py

  [*] Unstaged Changes (2 file(s)):
     * [M] src/api.py
     * [M] tests/test_auth.py

  [?] Untracked Files (0 file(s)):
     (no untracked files)

  [@] Configured Remotes (1):
     * origin -> https://github.com/developer/my-app.git

  [>] Recent Commits on main:
     * 7b8e1a2 (2 hours ago) [Dev] feat(auth): add OAuth2 refresh token flow
     * c4f92d1 (Yesterday)   [Dev] fix(api): resolve payload serialization bug

  [AI] AI Engine    : Google Gemini -- Configured (gemini-2.5-flash)
============================================================================
```

### 2. Launch Local Web Studio
```bash
# Launch server and automatically open browser on default port (8000 or next open port)
blamestorm

# Target a specific repository folder from anywhere
blamestorm --repo "D:\Work\another-project"

# Specify a custom port
blamestorm --port 8080

# Headless / server mode (do not launch browser)
blamestorm --no-browser
```

---

## 🎨 AI Mentor Code Studio (3-Pane Workspace)

Accessible from the **Smart Staging** action bar (`AI Mentor`), the 3-pane Code Studio provides an IDE-grade environment to troubleshoot, explain, and refactor code with Google Gemini:

```text
┌──────────────────────────┬──────────────────────────┬──────────────────────────┐
│      CURRENT CODE        │       CMD TERMINAL       │      SUGGESTED CODE      │
│  zit_app/views.py        │  cmd.exe — Active Repo   │  Complete Updated Code   │
│                          │                          │                          │
│ 1  import os             │ C:\projects\repo> refactor │ 1  import os             │
│ 2  from django...        │ [■ ■ ■ ■ ■] thinking...  │ 2  from django...        │
│ 3                        │                          │ 3  # Refactored with docs│
│ 4  def staging_view():   │ ┌──────────────────────┐ │ 4  def staging_view():   │
│                          │ │ AI Mentor: Gemini    │ │                          │
│                          │ │ Optimized error handling│                          │
│                          │ └──────────────────────┘ │                          │
│                          │                          │ [Apply to File] [Copy]   │
└──────────────────────────┴──────────────────────────┴──────────────────────────┘
             ↕ Draggable Resizer      ↕ Draggable Resizer
```

- **Left Pane (Current Code)**: Sticky line numbering, unified single horizontal scroll, and syntax display of the active file.
- **Middle Pane (CMD Terminal)**:
  - Clean Windows prompt initialized directly to your active repository path (`C:\repo>`).
  - Accepts native shell and Git commands, quick action pills (`Explain File`, `Detect Bugs`, `Refactor & Update`, `Add Types & Docs`), or natural language inquiries.
  - User commands persist in the scrollback buffer.
  - Features a **retro pixelated thinking loader** (`[■ ■ ■ ■ ■] thinking...`) on the next line while processing requests.
  - Formatted AI response cards with copyable code snippets and structured summaries.
- **Right Pane (Suggested Code)**:
  - Displays complete, production-ready replacement code generated by Gemini.
  - **1-Click Apply to File**: Overwrites the file on disk, updates the left pane immediately, and adds a success log to the terminal so changes can be inspected in Smart Staging.
- **Interactive Splitters**: Draggable splitter handles with hover glow and title tooltips (`Drag to resize... Double-click to reset`). Layout dimensions are automatically remembered in `localStorage`.

---

## 🛡️ Autonomous AI Agent & Strict Safety Protocol

Blamestorm includes a conversational **Autonomous Agent (`A`)** capable of running chained Git operations based on natural language objectives (e.g., *"clean untracked temp files, sync with main, and prepare release branch"*).

### Strict Safety Enforcement
To protect your repositories from unintended state corruption:
1. **Autonomous Commit Prohibition**: The AI Agent is **strictly prohibited from executing `git commit` autonomously**. Committing changes is reserved exclusively for the human user through the Conventional Commit UI or verified manual input.
2. **Approval Gate for Destructive Actions**: Commands classified as dangerous—such as `git reset --hard`, `git push --force`, `git clean -f`, and branch deletion (`git branch -D`)—are trapped before execution and require explicit modal approval.
3. **Safe Command Execution**: Non-destructive commands (`git status`, `git diff`, `git log`, `git fetch`, `git branch -a`) execute automatically with real-time terminal output streaming.

---

## 📋 Core Features

| Feature | Key | Description |
|---|:---:|---|
| **Repository Dashboard** | | At-a-glance branch health, ahead/behind counters, uncommitted file totals, quick stash, and recent commits. |
| **Smart Staging** | `s` | Multi-file staging, unstaging, file discarding, diff inspection, and granular hunk-by-hunk staging. |
| **Guided Commit** | `c` | Conventional commit builder (feat, fix, refactor, chore), 50-char validation counter, breaking change flag, and expanded diffstat preview. |
| **AI Mentor Code Studio** | | 3-pane interactive code explainer, bug detector, and refactor studio with an integrated CMD terminal. |
| **Branch Manager** | `b` | Visual branch listing, branch creation, fast checkout, safe/force deletion, rename, and upstream branch tracking. |
| **Commit Timeline & Graph** | `l` | Visual ASCII/SVG commit graph (`--graph`), SHA copy, message filtering, author search, and detailed commit diffs. |
| **Time Travel / Safe Reset** | `t` | Soft, mixed, and hard resets with safety dialogs, file rollback, and repository tag management. |
| **Reflog Recovery** | `r` | Browse Git reflog history to safely recover "lost" commits, orphaned trees, or accidental rebases. |
| **Stash Manager** | `x` | Save uncommitted working tree state with custom notes, pop, apply, drop, and inspect stash diffs. |
| **3-Way Merge Resolver** | `m` | Side-by-side conflict resolver with **Ours**, **Theirs**, **Both**, or **Gemini AI Intelligent Conflict Resolution**. |
| **Git Bisect Debugger** | `B` | Interactive binary search tool to locate the exact commit that introduced a test regression. |
| **Cherry Pick** | `p` | Browse commits across external branches and selectively cherry-pick them into your current branch. |
| **Workflow Builder** | `w` | Visual GitHub Actions CI/CD designer: add triggers, jobs, and steps with 1-click YAML export. |
| **GitHub Integration** | `g` | Push, pull, fetch, upstream synchronization, remote configuration, and quick GitHub PR links. |
| **Secret Scanner** | | Pre-stage and pre-commit scanner checking 20+ signature patterns for tokens, keys, and private credentials. |
| **Autonomous Agent** | `A` | Multi-step conversational AI Git operator with strict human verification gates. |
| **Keyboard Cheat Sheet** | `?` | Instant keyboard shortcut cheat sheet accessible anywhere. |

---

## ⚡ Single-Key Keyboard Shortcuts

Blamestorm supports Vim/TUI-style single-key navigation across all views (active when not focusing an input field):

| Key | Destination | Key | Destination |
|:---:|---|:---:|---|
| `s` | Smart Staging & Diffs | `m` | Merge Conflict Resolver |
| `c` | Guided Conventional Commit | `B` | Git Bisect Debugger |
| `b` | Branch Manager | `p` | Cherry Pick Commits |
| `l` | Commit Log & Graph | `w` | Workflow Builder (CI/CD) |
| `t` | Time Travel / Safe Reset | `g` | GitHub Integration & Remotes |
| `r` | Reflog Recovery | `A` | Autonomous Agent Mode |
| `x` | Stash Manager | `?` | Open Keyboard Help Modal |

---

## 🚀 Developer Quick Start (From Source)

### 1. Prerequisites
- **Python**: 3.10, 3.11, or 3.12
- **Git**: Installed and available on your system `PATH`

### 2. Clone and Setup
```bash
git clone https://github.com/G4uravXDev/Blamestorm.git
cd Blamestorm
pip install -r requirements.txt
```

### 3. Run the Development Server
On Windows:
```cmd
start.bat
```
On Linux / macOS:
```bash
./start.sh
```
Or directly via Python:
```bash
python blamestorm.py
```
Open your browser at [http://localhost:8000](http://localhost:8000).

---

## 🧠 Google Gemini AI Configuration

Blamestorm connects directly to the **Google Gemini API** (`google-genai` SDK and REST fallbacks).

### Setup via Settings UI
1. Open **Settings** (`⚙️` in the navigation bar or `/settings/`).
2. Paste your free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/apikey).
3. Select your model (`gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`, or any custom model ID).
4. Click **Test API Connection** $\rightarrow$ **Save Settings**.

### Setup via Environment Variable
```bash
# Linux / macOS
export GEMINI_API_KEY="AIzaSy..."

# Windows PowerShell
$env:GEMINI_API_KEY="AIzaSy..."

# Windows Command Prompt
set GEMINI_API_KEY=AIzaSy...
```
*(Note: All core Git operations, including Staging, Commits, Branching, Logs, Resets, Stashing, and Merge resolution, function 100% offline without an API key).*

---

## 🔒 Secret Scanner Signatures

Before files are staged or committed, Blamestorm's regex engine analyzes changed hunks for accidental credential exposure across 20+ signature rules:

- **Cloud & Infrastructure**: AWS Access Key ID (`AKIA...`), AWS Secret Keys, Google Cloud API Keys (`AIzaSy...`).
- **Development & Version Control**: GitHub Personal Access Tokens (`ghp_...`), GitHub Fine-Grained Tokens (`github_pat_...`), GitLab Personal Access Tokens (`glpat-...`).
- **Communications & SaaS**: Slack Bot & User Tokens (`xoxb-...`, `xoxp-...`), Discord Bot Tokens, Stripe Live/Test API Keys (`sk_live_...`, `rk_live_...`).
- **Security & Cryptography**: RSA, DSA, EC, and OpenSSH Private Key Headers (`-----BEGIN ... PRIVATE KEY-----`).
- **Authentication & Databases**: JSON Web Tokens (JWT), Database Connection URIs (`postgres://`, `mysql://`, `mongodb+srv://`).

---

## 🧪 Testing

Run the comprehensive unit test suite:
```bash
python manage.py test
```
All 13 core test suites verify repository discovery, commit safety classification, branch tracking, diff parsing, and secret detection.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
