# Blamestorm — AI-Powered Git & GitHub Assistant (Django Edition)

> Reverse-engineered from [JUSTMEETPATEL/zit](https://github.com/JUSTMEETPATEL/zit), transformed into a full-featured **Django Web Application** named **Blamestorm**, powered by **Google Gemini API** (replacing AWS Bedrock) and styled with responsive, developer-grade **Django Templates** with single-key shortcuts.

---

## 🌟 Overview

**Blamestorm** is a local, AI-powered Git and GitHub manager. When you download and run it in any local repository, it spins up a local web application on `localhost:8000` that interacts directly with your Git repository, providing:

- **15+ Git & GitHub Views**: Staging, Conventional Commits, Visual Branching, Timeline & Graphs, Safe Time Travel (Reset/Restore), Reflog Recovery, Stashes, 3-Way Merge Resolution, Git Bisect, Cherry-Pick, Visual GitHub Actions Workflow Builder, and GitHub Remotes/PRs.
- **⚡ Autonomous AI Agent Mode (`A`)**: Conversational Git operations loop where Google Gemini understands your plain English intent, plans exact Git commands, requests permission for destructive commands (e.g. `--force`, `reset --hard`), executes safe commands, and inspects results.
- **🤖 AI Mentor (`a`)**: Explain repository state, ask any Git question, safe action recommendations, error explainer & troubleshooter, staged diff code reviewer, Git concept teacher, and `.gitignore` generator.
- **🔒 Built-in Secret Scanner**: 20+ signature rules detecting AWS keys, Google API keys, GitHub tokens, Slack/Discord tokens, Stripe keys, Private Keys, JWTs, and database URIs before staging or committing.
- **⌨️ Single-Key Shortcuts**: Lightning-fast terminal TUI keybindings (`s`, `c`, `b`, `l`, `t`, `r`, `x`, `m`, `B`, `p`, `w`, `g`, `a`, `A`, `?`) right in the browser.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Git installed on your system

### 2. Installation
Clone or download this repository, then install requirements:
```bash
pip install -r requirements.txt
```

### 3. Start the Web App
Run inside your repository:
```bash
python blamestorm.py
```
Or on Windows:
```cmd
start.bat
```
Or via standard Django command:
```bash
python manage.py runserver
```

Open your browser to [http://localhost:8000](http://localhost:8000).

---

## 🧠 Google Gemini AI Setup

Instead of Amazon Bedrock (used in the original Rust Lambda backend), this application runs directly on **Google Gemini API** (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`, or **any custom / experimental Gemini model ID** entered in Settings).

### Option A: Via Settings UI
1. Navigate to **Settings** (`⚙️` icon in navbar or `/settings/`)
2. Enter your free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/apikey)
3. Select a preset Gemini model or choose **`-- Custom / Other Gemini Model --`** to type any experimental, preview, or fine-tuned model ID (e.g. `gemini-2.0-flash-thinking-exp`, `gemini-exp-1206`, `tunedModels/my-model`)
4. Click **Test API Connection** to verify and then click **Save Settings**

### Option B: Environment Variable
```bash
export GEMINI_API_KEY="AIzaSy..."
```
On Windows PowerShell:
```powershell
$env:GEMINI_API_KEY="AIzaSy..."
```

*Note: All core Git features (Staging, Commits, Branches, Log, Reset, Reflog, Stash, Merge, Bisect, Workflow Builder) work 100% offline without an API key.*

---

## 📋 Complete Feature Tour

| Feature | Key | Description |
|---|---|---|
| **Repository Dashboard** | | At-a-glance branch, dirty status, ahead/behind counts, quick stash, and recent commits |
| **Smart Staging** | `s` | Interactive staging, unstaging, discard changes, unified diffs, and hunk-level staging |
| **Guided Commits** | `c` | Conventional commit builder (feat, fix, docs, etc.), 50-char validation counter, and **✨ Gemini AI suggestions** |
| **Visual Branching** | `b` | List local & remote branches, checkout, create, safe/force delete, rename, and merge |
| **Commit Timeline** | `l` | Visual commit graph (`--graph`), search commits by message or author, inspect commit diffs |
| **Time Travel** | `t` | Safe reset (soft, mixed, hard with confirmation dialog), file restore, and tag manager |
| **Reflog Recovery** | `r` | Browse git reflog, recover "lost" commits, and checkout or reset to previous HEAD states |
| **Stash Manager** | `x` | Save uncommitted work with messages, pop, apply, drop, clear, and inspect stash diffs |
| **Merge Resolve** | `m` | 3-way conflict view, resolve with Ours, Theirs, Both, or **🤖 Gemini AI Intelligent Resolution** |
| **Git Bisect** | `B` | Interactive binary search debugger to find the exact commit that introduced a bug |
| **Cherry Pick** | `p` | Browse commits from other branches and cherry-pick them into the current branch |
| **Workflow Builder** | `w` | Visual GitHub Actions CI/CD designer: add steps/uses, triggers, and export YAML |
| **GitHub Integration**| `g` | Push, pull, fetch, sync with upstream, remote management, and quick PR links |
| **🤖 AI Mentor** | `a` | Explain repo, ask Git questions, recommendations, error troubleshooter, and code review |
| **⚡ Agent Mode** | `A` | Autonomous conversational Git operations with safe command approvals |
| **🔒 Secret Scanner** | | Real-time scanner blocking accidental leaks of credentials, tokens, and keys |
| **Keyboard Help** | `?` | Context-sensitive keyboard shortcut cheat sheet |

---

## 🏗️ Architecture & Reverse Engineering Comparison

| Component | Original `zit` | Django Edition `zit` |
|---|---|---|
| **Platform** | Rust Terminal TUI (ratatui + crossterm) | **Django Web Application (Django 6.1)** |
| **User Interface** | Terminal ANSI escape sequences | **Django Templates + Modern Dark CSS3** |
| **AI Backend** | AWS Lambda + Amazon Bedrock (Claude 3 Sonnet) | **Google Gemini API (`google.genai` SDK + REST)** |
| **Git Execution** | Native `git` CLI subprocess runner | **Python `subprocess` Git Engine** |
| **Secret Scanner** | Rust Regex engine (20+ rules) | **Python Regex engine (20+ rules + allowlist)** |
| **Agent Mode** | Terminal chat with tool use blocks | **Interactive Web Chat with Approval Modals** |
| **Storage / State** | Config TOML + OS Keychain | **Django SQLite Database + Session State** |

---

## ⌨️ Single-Key Shortcuts

Press any of the following keys anywhere in the web app (outside text inputs):

- `s` → Smart Staging
- `c` → Guided Commit
- `b` → Branch Manager
- `l` → Commit Timeline & Graph
- `t` → Time Travel (Reset & Restore)
- `r` → Reflog Recovery
- `x` → Stash Manager
- `m` → Merge Conflict Resolver
- `B` → Git Bisect
- `p` → Cherry Pick
- `w` → Workflow Builder
- `g` → GitHub Integration
- `a` → AI Mentor
- `A` → Autonomous Agent Mode
- `?` → Open Shortcuts Help Dialog
- `Esc` → Close active modal

---

## 📄 License
MIT License
