import sys
import shutil
import subprocess
import os


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
        print(f"cd: {path}: No such file or directory")

def main():
    while(1): 
        sys.stdout.write("$ ")
        sys.stdout.flush()
        command = input()
        
        commands = parse_args(command)
        
        if not commands:
            continue
        redirect_file = None
        if ">" in commands or "1>" in commands:
            op = "1>" if "1>" in commands else ">"
            idx = commands.index(op)
            
            commands.pop(idx)                 
            redirect_file = commands.pop(idx) 
        original_stdout = sys.stdout
        output_file_handle = None

        if redirect_file:
            output_file_handle = open(redirect_file, "w")
            sys.stdout = output_file_handle 

        
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
                if output_file_handle:
                    subprocess.run(commands, stdout=output_file_handle) 
                else:
                    subprocess.run(commands)
            else:
                
                if output_file_handle:
                    sys.stdout = original_stdout
                print(f'{commands[0]}: command not found')
                if output_file_handle:
                    sys.stdout = output_file_handle
                    
        finally:
            if output_file_handle:
                sys.stdout = original_stdout
                output_file_handle.close()

if __name__ == "__main__":
    main()