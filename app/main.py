import sys
import shutil
import subprocess
import os
import readline 
def multipipelines(commands):
    builtin_commands = ["echo", "exit", "type", "pwd", "cd"]

    for i in range(len(commands)-1):
        if commands[i] == "|":
            left_cmd = commands[:i]
            right_cmd = commands[i + 1:] 
            if left_cmd[0] in builtin_commands or right_cmd[0] in builtin_commands:
                try:
                    # 1. EXECUTE LEFT COMMAND (Capture Output)
                    if left_cmd[0] in builtin_commands:
                        if left_cmd[0] == "echo":
                            output = " ".join(left_cmd[1:]) + "\n"
                        elif left_cmd[0] == "pwd":
                            output = os.getcwd() + "\n"
                        elif left_cmd[0] == "cd":
                            change_directory(left_cmd[1] if len(left_cmd) > 1 else None)
                            output = ""
                        elif left_cmd[0] == "type":
                            # Replicate type logic to generate a string instead of printing
                            arg = left_cmd[1] if len(left_cmd) > 1 else ""
                            if not arg:
                                output = "type: usage: type name\n"
                            elif arg in builtin_commands:
                                output = f"{arg} is a shell builtin\n"
                            elif p := shutil.which(arg):
                                output = f"{arg} is {p}\n"
                            else:
                                output = f"{arg} not found\n"
                    else:
                        # External command on the left
                        output = subprocess.check_output(left_cmd, text=True)

                    # 2. EXECUTE RIGHT COMMAND
                    if right_cmd[0] in builtin_commands:
                        # Built-ins ignore stdin in Unix! Just run them normally.
                        if right_cmd[0] == "echo":
                            echo(right_cmd[1:])
                        elif right_cmd[0] == "type":
                            type_command(right_cmd[1] if len(right_cmd) > 1 else "")
                        elif right_cmd[0] == "pwd":
                            printdirectory()
                        elif right_cmd[0] == "cd":
                            change_directory(right_cmd[1] if len(right_cmd) > 1 else None)
                    else:
                        
                        subprocess.run(right_cmd, input=output, text=True)
            
            try:
                p1 = subprocess.Popen(left_cmd, stdout=subprocess.PIPE)
                p2 = subprocess.Popen(right_cmd, stdin=p1.stdout)
                p1.stdout.close()
                p2.communicate()
            except FileNotFoundError:
                missing_cmd = left_cmd[0] if not shutil.which(left_cmd[0]) else right_cmd[0]
                print(f'{missing_cmd}: command not found', file=sys.stderr)
            except Exception as e:
                print(str(e), file=sys.stderr)
            
            break
def setup_autocompletion():
    builtin_commands = ["echo", "exit", "type", "pwd", "cd"]
    completion_matches = []

    def completer(text, state):
        nonlocal completion_matches 
        
        if state == 0:
            matches = set()
            
            for cmd in builtin_commands:
                if cmd.startswith(text):
                    matches.add(cmd)
            
            # 2. Add matching external executables from PATH
            path_env = os.environ.get("PATH", "")
            if path_env:
                for directory in path_env.split(os.pathsep):
                    if os.path.isdir(directory):
                        try:
                            for filename in os.listdir(directory):
                                if filename.startswith(text):
                                    filepath = os.path.join(directory, filename)
                                    if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                                        matches.add(filename)
                        except Exception:
                            pass
            
            completion_matches = sorted(list(matches))

        if state < len(completion_matches):
            return completion_matches[state] + " "
        else:
            return None

    # THE CRITICAL MISSING LINE: Tell readline to actually use our function!
    readline.set_completer(completer)

    # Bind the tab key
    if 'libedit' in readline.__doc__:
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

    builtin_commands = ["echo", "exit", "type", "pwd", "cd"]
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

def main():
    builtin_commands = ["echo", "exit", "type", "pwd", "cd"]
    setup_autocompletion()

    while(1): 
        # UPDATED: Use input("$ ") instead of sys.stdout.write. 
        # This allows readline to redraw the line correctly without deleting the prompt.
        try:
            command = input("$ ")
        except EOFError:
            break # Exits cleanly if the tester sends an EOF signal
        
        commands = parse_args(command)
        
        if not commands:
            continue

        redirect_file = None
        redirect_stream = None 
        operation = None
        
        # REDIRECTION LOGIC
        # REDIRECTION LOGIC
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
                sys.exit(0)
            elif commands[0] == "echo":
                echo(commands[1:])
            elif commands[0] == "type":
                type_command(commands[1] if len(commands) > 1 else "")
            elif commands[0] == "pwd":
                printdirectory()
            elif commands[0] == "cd":
                change_directory(commands[1] if len(commands) > 1 else None)
            elif path := shutil.which(commands[0]):
                if redirect_stream == "stdout":
                    subprocess.run(commands, stdout=output_file_handle) 
                elif redirect_stream == "stderr":
                    subprocess.run(commands, stderr=output_file_handle)
                else:
                    subprocess.run(commands)
            else:
                print(f'{commands[0]}: command not found', file=sys.stderr)
                    
        finally:
            if output_file_handle:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                output_file_handle.close()

if __name__ == "__main__":
    main()