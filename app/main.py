import sys
import shutil
import subprocess
import re
import os

def parse_args(command_string):
    args = []
    current_token = []
    in_quote = False
    has_token = False 
    
    for char in command_string:
        if char == "'" and not in_quote:
            in_quote = True
            has_token = True 
        elif char == "'" and in_quote:
            in_quote = False
        elif char == ' ' and not in_quote:
            if has_token:
                args.append("".join(current_token))
                current_token = []
                has_token = False
        else:
            current_token.append(char)
            has_token = True 
            
    if has_token:
        args.append("".join(current_token))
        
    return args

def echo(args):
    print(" ".join(args))

def type_command(args):
    builtin_commands = ["echo", "exit", "type", "pwd", "cd"]
    if args in builtin_commands:
        print(f'{args} is a shell builtin')
    elif path := shutil.which(args):
        print(f"{args} is {path}")
    else:
        print(f'{args} not found')

def printdirectory():
    print(os.getcwd())

def change_directory(path):
    if path == "~":
        path = os.path.expanduser("~")
        os.chdir(path)
    else:
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

        if commands[0] == "exit":
            sys.exit(0)
        elif commands[0] == "echo":
            echo(commands[1:])
        elif commands[0] == "type":
            type_command(commands[1])
        elif commands[0] == "pwd":
            printdirectory()
        elif commands[0] == "cd":
            change_directory(commands[1])
        elif path := shutil.which(commands[0]):
            
            subprocess.run(commands) 
        else:
            print(f'{commands[0]}: command not found')

if __name__ == "__main__":
    main()