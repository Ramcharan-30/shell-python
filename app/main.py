import sys
import shutil
import subprocess
import re
import os



def echo(args):
    print(args)

def type(args):
    builtin_commands = ["echo", "exit","type"]
    if args in builtin_commands:
            print(f'{args} is a shell builtin')
    elif path := shutil.which(args):
        print(f"{args} is {path}")
    else:
            print(f'{args} not found')

def printdirectory():
    print(os.getcwd())


    


def main():
   
   while(1): 
    sys.stdout.write("$ ")
    command = input()
    commands = re.split(r'\s+', command)
    if command == "exit":
        sys.exit(0)
    elif commands[0] == "echo":
        echo(commands[1])
    elif commands[0] == "type":
        type(commands[1])
    elif path := shutil.which(commands[0]):
        subprocess.run(command.split())
    elif commands[0] == "pwd":
        printdirectory()
    else:
        print(f'{command}: command not found')
    pass


if __name__ == "__main__":
    main()
