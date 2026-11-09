# Quick start: ASPIRE in the browser

This guide leads from a computer without Python to the running web app of ASPIRE (`aspire web`),
on Windows, Linux and macOS. The web app conducts an interactive session in the browser: a
language-model agent identifies closed-form models from a data table, and the user answers its
questions, reads the results and requests further rounds. Everything else about the software is
in [aspire/README.md](aspire/README.md).

Steps 1 to 5 are made once per computer and take about ten minutes, most of it downloads. Every
later start is step 6 alone.

| Step | Windows | Linux | macOS |
|---|---|---|---|
| 1. Python 3.11 or later | `winget install Python.Python.3.12` | `sudo apt install python3 python3-venv` | `brew install python@3.12` |
| 2. Repository | `git clone`, then `cd` into it | the same | the same |
| 3. Harness | `py -3.12 -m venv .venv`, then `pip install -e "aspire[runner]"` | `python3 -m venv .venv`, then the same | `python3.12 -m venv .venv`, then the same |
| 4. API key | file `.env` with `OPENAI_API_KEY=...` | the same | the same |
| 5. Agent's environment | `aspire experiment agent-env` | the same | the same |
| 6. Start | `aspire web` | the same | the same |

The table is an overview; the exact commands are given in the sections below.

**What was verified.** Steps 3, 5 and 6 were run on Windows 11 with Python 3.12.10 on 2026-10-07,
in a new virtual environment: the installation succeeded, step 5 took 217 s, and the web app
served its start page with the tasks of `tasks/`. The harness has also been run on Linux with
Python 3.11.15 (`aspire/README.md`). The macOS commands are those of Linux and have not been
run by the authors.

## Requirements

- **Git**, to obtain the repository.
- **Python 3.11 or later.** Version 3.12 is recommended, because it is the version of the
  verified runs.
- **An OpenAI API key** whose account has access to the model `gpt-6.1-sol`, the model that a
  session uses by default.
- **Internet access**, for the installation and for the requests to the language model.

## 1. Install Python

**Windows** (PowerShell):

    winget install Python.Python.3.12
    py -3.12 --version

Open a new terminal after the installation, so that the launcher `py` is found. The installer
from <https://www.python.org/downloads/> gives the same result.

**Linux** (Debian and Ubuntu; other distributions use their own package manager):

    sudo apt install python3 python3-venv git
    python3 --version

The printed version must be 3.11 or later; Ubuntu 24.04 provides 3.12 and Debian 12 provides
3.11. Where the distribution provides an older version, install a newer one beside it and use its
name (for example `python3.12`) in step 3. The package `python3-venv` is required: without it,
step 3 stops with the message that `ensurepip` is not available.

**macOS** (with [Homebrew](https://brew.sh)):

    brew install python@3.12 git
    python3.12 --version

## 2. Obtain the repository

    git clone https://github.com/erik-derner/aspire-sysid.git
    cd aspire-sysid

All later commands are run in this folder, the repository root.

## 3. Install the harness

The harness is the software part of ASPIRE (folder `aspire/`, console script `aspire`). It is
installed into a virtual environment `.venv` in the repository root, which git ignores.

**Windows:**

    py -3.12 -m venv .venv
    .venv\Scripts\python -m pip install -e "aspire[runner]"
    .venv\Scripts\aspire --version

**Linux and macOS** (on macOS, write `python3.12` in place of `python3` in the first line):

    python3 -m venv .venv
    .venv/bin/python -m pip install -e "aspire[runner]"
    .venv/bin/aspire --version

The last command prints `aspire-sysid 0.1.0.dev0`. The option `-e` (editable installation) is
required, because the harness finds its configuration files relative to the folder `aspire/`. The
extra `runner` installs the software of the language-model vendors.

The commands of this guide name the programs of `.venv` by their path, so that the environment
need not be activated. After activation (`.venv\Scripts\Activate.ps1` on Windows, `source
.venv/bin/activate` elsewhere) the short form `aspire` is sufficient.

## 4. Store the API key

Create a text file named `.env` in the repository root with one line:

    OPENAI_API_KEY=<your key>

Create it with a text editor (`notepad .env` on Windows, `nano .env` on Linux and macOS), not
with a shell command that contains the key, because the shell would keep the key in its history.
Git ignores `.env`; never commit it.

The harness reads the file as UTF-8, with or without a byte-order mark, or as UTF-16 with a
byte-order mark; these are the forms that Notepad and Windows PowerShell write. A file in another
encoding stops the start with a message that names the file.

The harness also accepts the key from the environment variable `OPENAI_API_KEY`. The file is
preferred, because a key read from `.env` is never placed in the environment of a process, where
a command of the agent could read it (`aspire/README.md`, section "Interactive operation").

## 5. Create the agent's environment

**Windows:**

    .venv\Scripts\aspire experiment agent-env

**Linux and macOS:**

    .venv/bin/aspire experiment agent-env

The command creates a second virtual environment outside the repository
(`%LOCALAPPDATA%\aspire\agent-env` on Windows, `~/.local/share/aspire/agent-env` elsewhere) and
installs into it the packages that the agent's programs use: numpy, scipy, sympy, pandas,
matplotlib, scikit-learn, gplearn and pysindy. It takes a few minutes and prints nothing until it
ends with a line of the form

    created <folder>: Python 3.12.10; harness importable: False

The two lines that follow it concern `aspire experiment run` and are not needed here.

This environment is required. The agent runs its commands with an interpreter in which the
harness is not installed, because the harness can open the test data, which the agent must not
reach. A session with a real language model refuses to start when it finds no such environment.

## 6. Start the web app

**Windows:**

    .venv\Scripts\aspire web

**Linux and macOS:**

    .venv/bin/aspire web

Run the command in the repository root: the web app looks for the tasks in `tasks/` and writes
the session records to `sessions/` under the current folder. It prints the address of the page
and opens it in the browser:

    ASPIRE web app: http://127.0.0.1:<port>/t/<token>/
    Open this address in a browser on this computer (it works on this computer only). Stop with Ctrl+C.

The start page offers two ways of starting a session:

- **a task of the repository**, for example `turtlebot` (motion model of a TurtleBot 2 mobile
  robot); the definition of the task (`task.yaml`) can be read and edited on the page;
- **your own data files** (training data required; validation and test data optional): an agent
  first prepares the task definition in a conversation with you, the task interview, and the
  identification starts after you confirm the task brief.

**Cost and duration.** A session sends requests to the OpenAI API, which are charged to the
account of the key. The limits are those of the task (`budget` in its `task.yaml`): for
`turtlebot`, one identification round is limited to 60 responses of the agent, 3600 s and 10 USD,
and a session to 30 USD. The task interview is limited to 5 USD in addition. A round can exceed its cost limit by
the cost of the request during which the limit was reached.

**Results.** The record of a session is the folder `sessions/<task>-<date>-<n>/`; its report is
`report/index.html` in that folder, which the page also links at the end of the session.

Stop the web app with Ctrl+C in the terminal. One session runs at a time.

## If a step fails

| Message or symptom | Cause and remedy |
|---|---|
| `py` or `python3.12` is not found | The terminal was opened before Python was installed; open a new one. |
| `ensurepip is not available` (Linux, step 3) | Install the package `python3-venv` (step 1). |
| `OPENAI_API_KEY is not set in the environment and no .env file holds it` | The file `.env` is missing from the repository root, has another name (for example `.env.txt`), or does not contain the line of step 4. |
| `the file ... cannot be read as text in UTF-8` | The file `.env` is in another encoding; save it in UTF-8 with a text editor (step 4). |
| `no environment for the agent's commands was found` | Step 5 was not made, or it was made by another user of the computer. |
| `... exists and is not empty` (step 5) | The agent's environment already exists; step 5 is complete. To create it again, delete the named folder first. |
| The start page lists no task | `aspire web` was not started in the repository root; start it there, or name the folder with `--tasks`. |
| The session ends shortly after its start with an error of the request to the language model | The key is not valid, or its account has no access to `gpt-6.1-sol`; the page shows the vendor's message. Another model is chosen with `aspire web --model <identifier>`, where the identifier is one that `aspire prices` lists. |

In the web app, an error of a session is shown on the page at the end of the session, not on the
terminal.

## Further reading

- [aspire/README.md](aspire/README.md), sections "Interactive operation" (sessions, the task
  interview, the web app) and "Experiments" (autonomous, repeated runs).
- [tasks/GUIDE.md](tasks/GUIDE.md): how to define a task, with the commented examples
  `tasks/example-static` and `tasks/example-dynamic`.
