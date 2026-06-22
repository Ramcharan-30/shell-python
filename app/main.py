import sys
import shutil
import subprocess
import os
import time # NEW: We need this to yield to the OS

try:
    import readline
except ImportError:
    readline = None

# Global state for background jobs
HISTORY_LIST = []
HISTORY_APPEND_INDEX = 0
BACKGROUND_JOBS = {}
JOB_ORDER = []

def get_marker(job_id):
    if len(JOB_ORDER) >= 1 and JOB_ORDER[-1] == job_id:
        return "+"
    elif len(JOB_ORDER) >= 2 and JOB_ORDER[-2] == job_id:
        return "-"
    else:
        return " "

def reap_and_format_jobs(display_done=True):
    # NEW: Give the OS 50ms to clean up terminating processes before we check them
    if BACKGROUND_JOBS:
        time.sleep(0.05) 
        
    output = ""
    done_jobs = []

    # 1. Identify finished jobs
    for job_id in sorted(BACKGROUND_JOBS.keys()):
        if BACKGROUND_JOBS[job_id]['process'].poll() is not None:
            BACKGROUND_JOBS[job_id]['status'] = 'Done'
            done_jobs.append(job_id)

    # 2. Build output for 'jobs' command
    for job_id in sorted(BACKGROUND_JOBS.keys()):
        job = BACKGROUND_JOBS[job_id]
        marker = get_marker(job_id)
        status_padded = job['status'].ljust(24)
        cmd_string = job['cmd']
        
        if job['status'] == 'Done' and cmd_string.endswith(" &"):
            cmd_string = cmd_string[:-2]
            
        output += f"[{job_id}]{marker}  {status_padded}{cmd_string}\n"

    # 3. Print 'Done' automatically if enabled
    if display_done:
        for job_id in done_jobs:
            job = BACKGROUND_JOBS[job_id]
            marker = get_marker(job_id)
            status_padded = "Done".ljust(24)
            cmd_string = job['cmd']
            if cmd_string.endswith(" &"):
                cmd_string = cmd_string[:-2]
            # NEW: flush=True ensures it prints immediately before the prompt
            print(f"[{job_id}]{marker}  {status_padded}{cmd_string}", flush=True) 

    # 4. Remove finished jobs
    for job_id in done_jobs:
        del BACKGROUND_JOBS[job_id]
        JOB_ORDER.remove(job_id)

    return output

def get_history_output(num=None):
    output = ""
    history_to_show = HISTORY_LIST
    start_num = 1
    if num is not None:
        try:
            num = int(num)
            if num < 0: raise ValueError
            start_index = max(0, len(HISTORY_LIST) - num)
            history_to_show = HISTORY_LIST[start_index:]
            start_num = start_index + 1
        except ValueError:
            return "history: usage: history [n]\n"
    for i, cmd in enumerate(history_to_show, start_num):
        output += f"{i:>5}  {cmd}\n"
    return output

def run_history(args):
    global HISTORY_APPEND_INDEX
    if not args: return get_history_output(None)
    if args[0] == "-r":
        if len(args) > 1:
            try:
                with open(args[1], 'r') as f:
                    for line in f:
                        if line.strip(): HISTORY_LIST.append(line.strip())
            except FileNotFoundError: pass
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        return "" 
    if args[0] == "-w":
        if len(args) > 1:
            with open(args[1], 'w') as f:
                for cmd in HISTORY_LIST: f.write(f"{cmd}\n")
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        return ""
    if args[0] == "-a":
        if len(args) > 1:
            with open(args[1], 'a') as f:
                for cmd in HISTORY_LIST[HISTORY_APPEND_INDEX:]: f.write(f"{cmd}\n")
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        return ""
    return get_history_output(args[0])

def setup_autocompletion():
    if readline is None: return
    builtin_commands = ["echo", "exit", "type", "pwd", "cd", "history", "jobs"]
    completion_matches = []
    def completer(text, state):
        nonlocal completion_matches 
        if state == 0:
            matches = set()
            line_buffer = readline.get_line_buffer()
            if readline.get_begidx() == 0 or line_buffer[:readline.get_begidx()].strip() == "":
                for cmd in builtin_commands:
                    if cmd.startswith(text): matches.add(cmd + " ")
                path_env = os.environ.get("PATH", "")
                if path_env:
                    for directory in path_env.split(os.pathsep):
                        if os.path.isdir(directory):
                            try:
                                for filename in os.listdir(directory):
                                    if filename.startswith(text):
                                        filepath = os.path.join(directory, filename)
                                        if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                                            matches.add(filename + " ")
                            except Exception: pass
            else:
                try:
                    search_dir = os.path.dirname(text) if '/' in text else "."
                    prefix = os.path.basename(text) if '/' in text else text
                    if os.path.isdir(search_dir):
                        for filename in os.listdir(search_dir):
                            if filename.startswith(prefix):
                                full_path = os.path.join(search_dir, filename)
                                suffix = "/" if os.path.isdir(full_path) else " "
                                matches.add(f"{text[:text.rfind('/')+1] if '/' in text else ''}{filename}{suffix}")
                except Exception: pass
            completion_matches = sorted(list(matches))
        return completion_matches[state] if state < len(completion_matches) else None
    readline.set_completer_delims(' \t\n;')
    readline.set_completer(completer)
    if 'libedit' in (readline.__doc__ or ''): readline.parse_and_bind("bind ^I rl_complete")
    else: readline.parse_and_bind("tab: complete")

def parse_args(command_string):
    args, current_token, quote_char, escaped = [], [], None, False
    for char in command_string:
        if escaped: current_token.append(char); escaped = False
        elif char == "\\": escaped = True
        elif char in ('"', "'"):
            if quote_char is None: quote_char = char
            elif quote_char == char: quote_char = None
            else: current_token.append(char)
        elif char == " " and quote_char is None:
            if current_token: args.append("".join(current_token)); current_token = []
        else: current_token.append(char)
    if current_token: args.append("".join(current_token))
    return args

def multipipelines(commands):
    builtin_commands = ["echo", "exit", "type", "pwd", "cd", "history", "jobs"]
    chunks, temp = [], []
    for token in commands:
        if token == "|": chunks.append(temp); temp = []
        else: temp.append(token)
    chunks.append(temp)
    processes, prev_process, prev_output_str = [], None, None
    for i, cmd in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        if cmd[0] in builtin_commands:
            if prev_process: prev_process.stdout.close(); prev_process = None
            out = ""
            if cmd[0] == "echo": out = " ".join(cmd[1:]) + "\n"
            elif cmd[0] == "pwd": out = os.getcwd() + "\n"
            elif cmd[0] == "cd": change_directory(cmd[1] if len(cmd) > 1 else None)
            elif cmd[0] == "exit": sys.exit(0)
            elif cmd[0] == "history": out = run_history(cmd[1:])
            elif cmd[0] == "jobs": out = reap_and_format_jobs(display_done=False)
            elif cmd[0] == "type":
                arg = cmd[1] if len(cmd) > 1 else ""
                if not arg: out = "type: usage: type name\n"
                elif arg in builtin_commands: out = f"{arg} is a shell builtin\n"
                elif p := shutil.which(arg): out = f"{arg} is {p}\n"
                else: out = f"{arg} not found\n"
            if is_last: sys.stdout.write(out); sys.stdout.flush()
            else: prev_output_str = out
        else:
            try:
                stdin = prev_process.stdout if prev_process else (subprocess.PIPE if prev_output_str else None)
                p = subprocess.Popen(cmd, stdin=stdin, stdout=None if is_last else subprocess.PIPE)
                if prev_process: prev_process.stdout.close()
                elif prev_output_str: p.stdin.write(prev_output_str.encode()); p.stdin.close(); prev_output_str = None
                prev_process = p; processes.append(p)
            except Exception as e: print(str(e), file=sys.stderr); return
    for p in processes: p.wait()

def main():
    setup_autocompletion()
    while True:
        reap_and_format_jobs(display_done=True)
        try: command = input("$ ")
        except EOFError: break
        if not command.strip(): continue
        commands = parse_args(command)
        orig_str = " ".join(commands)
        is_bg = False
        if commands[-1] == "&": is_bg = True; commands.pop()
        if not commands: continue
        
        try:
            if commands[0] == "exit": sys.exit(0)
            elif commands[0] == "echo": print(" ".join(commands[1:]))
            elif commands[0] == "cd": change_directory(commands[1] if len(commands) > 1 else None)
            elif commands[0] == "history": print(run_history(commands[1:]), end="")
            elif commands[0] == "jobs": print(reap_and_format_jobs(display_done=False), end="")
            elif path := shutil.which(commands[0]):
                p = subprocess.Popen(commands)
                if is_bg:
                    job_id = 1
                    while job_id in BACKGROUND_JOBS: job_id += 1
                    print(f"[{job_id}] {p.pid}")
                    BACKGROUND_JOBS[job_id] = {'id': job_id, 'pid': p.pid, 'cmd': orig_str, 'process': p, 'status': 'Running'}
                    JOB_ORDER.append(job_id)
                else: p.wait()
            else: print(f'{commands[0]}: command not found', file=sys.stderr)
        except Exception as e: print(e, file=sys.stderr)

if __name__ == "__main__": main()