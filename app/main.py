import sys
import shutil
import subprocess
import re
import os



def echo(args):
    
    if args[0] == "'" and args[-1] == "'":
        for i in range(1, len(args)-1):
            if args[i] =="'":
                continue
            else:
             print(args[i])
    
    else:
        for i in range(1, len(args)):
            if args[i]==" " and args[i-1]==" ":
                continue
            elif args[i]=="'":
                continue
            else:                print(args[i])

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
