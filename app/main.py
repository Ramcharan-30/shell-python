import sys
import shutil
import subprocess
import re
import os



def echo(args):
    result = []
    word = []
    in_quote = False
    parsing_word = False
    
    for char in args:
        if char == "'":
            in_quote = not in_quote
            parsing_word = True
        elif char == ' ' and not in_quote:
            if parsing_word:
                result.append("".join(word))
                word = []
                parsing_word = False
        else:
            word.append(char)
            parsing_word = True
            
    if parsing_word:
        result.append("".join(word))
        
    print(" ".join(result))

def type(args):
    builtin_commands = ["echo", "exit","type","pwd","cd"]
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
    command = input()
    commands = re.split(r'\s+', command)
    if command == "exit":
        sys.exit(0)
    elif commands[0] == "echo":
        echo(command[5:])
    elif commands[0] == "type":
        type(commands[1])
    elif path := shutil.which(commands[0]):
        subprocess.run(command.split())
    elif commands[0] == "pwd":
        printdirectory()
    elif commands[0] == "cd":
        change_directory(commands[1])
    else:
        print(f'{command}: command not found')
    pass


if __name__ == "__main__":
    main()
