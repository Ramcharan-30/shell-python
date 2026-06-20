import sys
import shutil
import subprocess
import os

try:
    import readline
except ImportError:
    readline = None

# Global list to track our command history
HISTORY_LIST = []
HISTORY_APPEND_INDEX = 0
BACKGROUND_JOBS = []

def get_jobs_output():
    output = ""
    for job in BACKGROUND_JOBS:
        # [1]+  Running                 sleep 10 &
        output += f"[{job['id']}]+  {'Running'.ljust(24)}{job['cmd']}\n"
    return output

def get_history_output(num=None):
    output = ""
    history_to_show = HISTORY_LIST
    start_num = 1
    
    if num is not None:
        try:
            num = int(num)
            if num < 0:
                raise ValueError
            
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
    
    if not args:
        return get_history_output(None)
        
    if args[0] == "-r":
        if len(args) > 1:
            filepath = args[1]
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        cmd = line.strip()
                        if cmd: 
                            HISTORY_LIST.append(cmd)
            except FileNotFoundError:
                pass
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        return "" 
        
    if args[0] == "-w":
        if len(args) > 1:
            filepath = args[1]
            with open(filepath, 'w') as f:
                for cmd in HISTORY_LIST:
                    f.write(f"{cmd}\n")
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        return ""

    if args[0] == "-a":
        if len(args) > 1:
            filepath = args[1]
            with open(filepath, 'a') as f: 
                for cmd in HISTORY_LIST[HISTORY_APPEND_INDEX:]:
                    f.write(f"{cmd}\n")
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        return ""

    return get_history_output(args[0])

def setup_autocompletion():
    if readline is None:
        return

    builtin_commands = ["echo", "exit", "type", "pwd", "cd", "history","jobs"]
    completion_matches = []

    def completer(text, state):
        nonlocal completion_matches 
        
        if state == 0:
            matches = set()
            line_buffer = readline.get_line_buffer()
            
            # --- COMMAND COMPLETION ---
            if readline.get_begidx() == 0 or line_buffer[:readline.get_begidx()].strip() == "":
                for cmd in builtin_commands:
                    if cmd.startswith(text):
                        matches.add(cmd + " ") # Add space for built-ins
                
                path_env = os.environ.get("PATH", "")
                if path_env:
                    for directory in path_env.split(os.pathsep):
                        if os.path.isdir(directory):
                            try:
                                for filename in os.listdir(directory):
                                    if filename.startswith(text):
                                        filepath = os.path.join(directory, filename)
                                        if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                                            matches.add(filename + " ") # Add space for executables
                            except Exception:
                                pass
            else:
                # --- FILE & DIRECTORY COMPLETION ---
                try:
                    if '/' in text:
                        dir_path = os.path.dirname(text)
                        prefix = os.path.basename(text)
                        search_dir = dir_path
                    else:
                        dir_path = ""
                        prefix = text
                        search_dir = "." # Default to current directory

                    if os.path.isdir(search_dir):
                        for filename in os.listdir(search_dir):
                            if filename.startswith(prefix):
                                full_path = os.path.join(search_dir, filename)
                                
                                # Check if the match is a directory or a file
                                if os.path.isdir(full_path):
                                    suffix = "/"  # Directories get a slash
                                else:
                                    suffix = " "  # Files get a space
                                    
                                if dir_path:
                                    matches.add(f"{dir_path}/{filename}{suffix}")
                                else:
                                    matches.add(f"{filename}{suffix}")
                except Exception:
                    pass
            
            completion_matches = sorted(list(matches))

        if state < len(completion_matches):
            # Return the exact string (the suffix is already baked in above!)
            return completion_matches[state]
        else:
            return None

    readline.set_completer_delims(' \t\n;')
    readline.set_completer(completer)

    if 'libedit' in (readline.__doc__ or ''):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

def parse_args(command_string):
    args = []
    current_token = []
    quote_char = None
    escaped = False

    for char in command_string:
        if escaped:
            if quote_char == '"' and char not in ('"', '\\', '$', '\n'):
                current_token.append('\\') 
            current_token.append(char)
            escaped = False
        elif char == "\\" and quote_char is None:
            escaped = True
        elif char == "\\" and quote_char == '"':
            escaped = True
        elif char in ('"', "'"):
            if quote_char is None:
                quote_char = char
            elif quote_char == char:
                quote_char = None
            else:
                current_token.append(char)
        elif char == " " and quote_char is None:
            if current_token:
                args.append("".join(current_token))
                current_token = []
        else:
            current_token.append(char)
    
    if current_token:
        args.append("".join(current_token))

    return args

def echo(args):
    print(" ".join(args))

def type_command(args):
    if not args:
        print("type: usage: type name")
        return

    builtin_commands = ["echo", "exit", "type", "pwd", "cd", "history", "jobs"]
    if args in builtin_commands:
        print(f"{args} is a shell builtin")
    elif path := shutil.which(args):
        print(f"{args} is {path}")
    else:
        print(f"{args} not found")

def printdirectory():
    print(os.getcwd())

def change_directory(path=None):
    if not path or path == "~":
        path = os.path.expanduser("~")

    try:
        os.chdir(path)
    except FileNotFoundError:
        print(f"cd: {path}: No such file or directory", file=sys.stderr)

def load_history_on_startup():
    global HISTORY_APPEND_INDEX
    histfile = os.environ.get("HISTFILE")
    if histfile:
        try:
            with open(histfile, 'r') as f:
                for line in f:
                    cmd = line.strip()
                    if cmd: 
                        HISTORY_LIST.append(cmd)
            HISTORY_APPEND_INDEX = len(HISTORY_LIST)
        except FileNotFoundError:
            pass 

def save_history_on_exit():
    histfile = os.environ.get("HISTFILE")
    if histfile:
        try:
            with open(histfile, 'a') as f:
                for cmd in HISTORY_LIST[HISTORY_APPEND_INDEX:]:
                    f.write(f"{cmd}\n")
        except Exception:
            pass 

def multipipelines(commands):
    builtin_commands = ["echo", "exit", "type", "pwd", "cd", "history","jobs"]
    
    chunks = []
    temp = []
    for token in commands:
        if token == "|":
            chunks.append(temp)
            temp = []
        else:
            temp.append(token)
    chunks.append(temp)

    processes = []
    prev_process = None
    prev_output_str = None  

    for i, cmd in enumerate(chunks):
        is_last_command = (i == len(chunks) - 1)

        if cmd[0] in builtin_commands:
            if prev_process:
                prev_process.stdout.close()
                prev_process = None 

            output_str = ""
            if cmd[0] == "echo":
                output_str = " ".join(cmd[1:]) + "\n"
            elif cmd[0] == "pwd":
                output_str = os.getcwd() + "\n"
            elif cmd[0] == "cd":
                change_directory(cmd[1] if len(cmd) > 1 else None)
            elif cmd[0] == "exit":
                save_history_on_exit() 
                sys.exit(0)
            elif cmd[0] == "history":
                output_str = run_history(cmd[1:])
            elif commands[0] == "history":
                output = run_history(commands[1:])
                if output:
                    print(output, end="")
            elif cmd[0] == "jobs":                        # UPDATED
                output_str = get_jobs_output()
            elif cmd[0] == "type":
                arg = cmd[1] if len(cmd) > 1 else ""
                if not arg:
                    output_str = "type: usage: type name\n"
                elif arg in builtin_commands:
                    output_str = f"{arg} is a shell builtin\n"
                elif p := shutil.which(arg):
                    output_str = f"{arg} is {p}\n"
                else:
                    output_str = f"{arg} not found\n"

            if is_last_command:
                sys.stdout.write(output_str)
                sys.stdout.flush()
            else:
                prev_output_str = output_str

        else:
            try:
                stdin_stream = None
                if prev_process:
                    stdin_stream = prev_process.stdout
                elif prev_output_str is not None:
                    stdin_stream = subprocess.PIPE 

                stdout_stream = None if is_last_command else subprocess.PIPE

                p = subprocess.Popen(cmd, stdin=stdin_stream, stdout=stdout_stream)

                if prev_process:
                    prev_process.stdout.close()
                elif prev_output_str is not None:
                    p.stdin.write(prev_output_str.encode())
                    p.stdin.close()
                    prev_output_str = None

                prev_process = p
                processes.append(p)

            except FileNotFoundError:
                print(f"{cmd[0]}: command not found", file=sys.stderr)
                return
            except Exception as e:
                print(str(e), file=sys.stderr)
                return
                
    for p in processes:
        p.wait()

def main():
    load_history_on_startup()
    setup_autocompletion()

    while(1): 
        try:
            command = input("$ ")
            if command.strip():  
                HISTORY_LIST.append(command)
        except EOFError:
            save_history_on_exit() 
            break 
        
        commands = parse_args(command)
        
        if not commands:
            continue

        # --- NEW: BACKGROUND JOB LOGIC ---
        original_cmd_str = " ".join(commands)
        
        is_background = False
        if commands[-1] == "&":
            is_background = True
            commands.pop()
            
        if not commands:
            continue
        redirect_file = None
        redirect_stream = None 
        operation = None
        
        if "|" in commands:
            multipipelines(commands)
            continue
            
        elif "2>" in commands:
            idx = commands.index("2>")
            redirect_stream = "stderr"
            commands.pop(idx)
            redirect_file = commands.pop(idx)
            operation = "w"
            
        elif "2>>" in commands:
            idx = commands.index("2>>")
            redirect_stream = "stderr"
            commands.pop(idx)
            redirect_file = commands.pop(idx)
            operation = "a"
            
        elif ">" in commands or "1>" in commands:
            op = "1>" if "1>" in commands else ">"
            idx = commands.index(op)
            redirect_stream = "stdout"
            commands.pop(idx)
            redirect_file = commands.pop(idx)
            operation = "w"
            
        elif ">>" in commands or "1>>" in commands:
            op = "1>>" if "1>>" in commands else ">>"
            idx = commands.index(op)
            redirect_stream = "stdout"
            commands.pop(idx)
            redirect_file = commands.pop(idx)
            operation = "a"
        
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        output_file_handle = None

        if redirect_file:
            output_file_handle = open(redirect_file, operation)
            if redirect_stream == "stdout":
                sys.stdout = output_file_handle
            elif redirect_stream == "stderr":
                sys.stderr = output_file_handle

        try:
            if commands[0] == "exit":
                save_history_on_exit() 
                sys.exit(0)
            elif commands[0] == "echo":
                echo(commands[1:])
            elif commands[0] == "type":
                type_command(commands[1] if len(commands) > 1 else "")
            elif commands[0] == "pwd":
                printdirectory()
            elif commands[0] == "cd":
                change_directory(commands[1] if len(commands) > 1 else None)
            elif commands[0] == "history":
                output = run_history(commands[1:])
                if output:
                    print(output, end="")
            elif commands[0] == "history":
                output = run_history(commands[1:])
                if output:
                    print(output, end="")
            elif commands[0] == "jobs":                   # UPDATED
                output = get_jobs_output()
                if output:
                    print(output, end="")
            elif path := shutil.which(commands[0]):
                if redirect_stream == "stdout":
                    p = subprocess.Popen(commands, stdout=output_file_handle) 
                elif redirect_stream == "stderr":
                    p = subprocess.Popen(commands, stderr=output_file_handle)
                else:
                    p = subprocess.Popen(commands)
                    
                if is_background:
                    job_id = len(BACKGROUND_JOBS) + 1
                    print(f"[{job_id}] {p.pid}")
                    # NEW: Save it to our tracking list!
                    BACKGROUND_JOBS.append({
                        'id': job_id,
                        'pid': p.pid,
                        'cmd': original_cmd_str,
                        'process': p
                    })
                else:
                    p.wait() # Block the shell only if it's NOT a background job
            else:
                print(f'{commands[0]}: command not found', file=sys.stderr)
                    
        finally:
            if output_file_handle:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                output_file_handle.close()

if __name__ == "__main__":
    main()