# ⚡ Concurrent POSIX Task Scheduler & Systems Shell

A high-performance, multithreaded UNIX shell and background task scheduler engineered entirely from scratch in C++. 

This project bypasses high-level standard libraries to directly interface with the Linux Kernel via raw POSIX system calls. It demonstrates advanced systems architecture, including memory management, inter-process communication (IPC), asynchronous signal handling, and thread synchronization.

## 🧠 Architectural Highlights

* **The Execution Engine:** Implements the classic `fork()`, `execvp()`, and `waitpid()` architecture to spawn and reap child processes dynamically without memory leaks or zombie processes.
* **Concurrent Thread Pool:** Background jobs (triggered by `&`) are delegated to a custom, fixed-size Thread Pool. Threads are synchronized using `std::mutex` and `std::condition_variable` to completely eliminate race conditions and CPU busy-waiting (0% idle CPU usage).
* **Inter-Process Communication (IPC):** Dynamically wires file descriptors across multiple processes using `pipe()` and `dup2()`, allowing seamless stdout-to-stdin data streaming (e.g., `ls -la | grep cpp | wc -l`).
* **Kernel Interrupt Routing:** Overrides default Linux process group signals using `sigaction()` / `signal(SIGINT, SIG_IGN)`, ensuring `Ctrl+C` cleanly terminates foreground processes without crashing the main shell.
* **Hardware Profiling:** Utilizes the `wait4()` and `getrusage()` system calls to generate precise receipts for background jobs, detailing Wall-Clock time, System/User CPU Time, and Peak RAM footprint.

## 🛠️ Core Features

- **Pipelining (`|`):** Chain infinitely many commands together using shared memory buffers.
- **I/O Redirection (`>`, `<`):** Route command input/output safely to hard drive files.
- **Logical Operators (`&&`, `||`):** Conditional execution state-machine based on raw OS exit codes (`WIFEXITED`, `WEXITSTATUS`).
- **Session History:** In-memory ring buffer (using `std::deque`) to track session history, accessible via the `history` built-in and re-executable via `!N`.
- **Advanced Parsing:** Custom C-style string parser that cleanly handles space-delimited arguments wrapped in single or double quotes.
- **Safe State Built-ins:** Natively handles main-thread state changes like `cd` (using `chdir()`) and `exit` (using `_exit()` to prevent multithreaded destructor deadlocks).

## 🚀 Getting Started

### Prerequisites
Requires a Linux/UNIX environment (or WSL on Windows) and a modern C++ compiler (C++17 or higher).

### Compilation
Compile the shell with the `pthread` flag to enable the background task scheduler:
```bash
g++ -std=c++17 shell.cpp -o myshell -pthread
