[![progress-banner](https://backend.codecrafters.io/progress/shell/264d4502-ba88-44e4-85a8-1935f4707252)](https://app.codecrafters.io/users/Ramcharan-30?r=2qF)

# Custom Python Shell

A lightweight, fully-functional Unix-like shell implemented entirely in Python. This project was built as a comprehensive exercise in understanding operating system interactions, process management, and command-line parsing.

## 🚀 Features

* **Command Execution:** Run standard external commands and executables found in your system's `$PATH`.
* **Built-in Commands:** * `cd`, `pwd`: Navigate the file system.
  * `echo`, `type`: Print text and identify command types/locations.
  * `exit`: Safely terminate the shell.
* **I/O Redirection:** Route standard output and standard error to files using `>`, `>>`, `1>`, `1>>`, `2>`, and `2>>`.
* **Pipelining:** Chain multiple commands together using `|` (e.g., `ls -l | grep ".py" | wc -l`).
* **Background Jobs:** * Run processes in the background using `&`.
  * Track active background processes using the `jobs` builtin.
  * Automatic, silent zombie process reaping before every new prompt.
* **Advanced Tab Autocompletion:**
  * Auto-completes builtins, executables in `$PATH`, and local files/directories.
  * **Programmable Completion:** Use the `complete -C <script> <cmd>` builtin to register custom external scripts for context-aware, dynamic autocompletion.
* **Command History:** * Tracks session history and persists it across sessions via the `$HISTFILE` environment variable.
  * Manage history dynamically using `history -r`, `-w`, and `-a`.
* **Variables & Parameter Expansion:** * Declare custom shell variables using `declare foo=bar`.
  * Evaluate variables inline using standard `$VAR` or braced `${VAR}` expansion formats.

## 🛠️ Prerequisites

* **Python 3.8+**
* `readline` library (Included in the Python standard library on Linux/macOS. Windows users may need to install `pyreadline3`).

## 💻 Usage

Clone the repository and run the main Python script to start the interactive shell:

```bash
git clone [https://github.com/yourusername/your-shell-repo.git](https://github.com/yourusername/your-shell-repo.git)
cd your-shell-repo
python3 shell.py
