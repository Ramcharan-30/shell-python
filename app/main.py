import sys
import shutil
import subprocess



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

def exec(args):
    if

    


def main():
   
   while(1): 
    sys.stdout.write("$ ")
    command = input()
    fcommand = command.split(None, 1)[0]
    if command == "exit":
        sys.exit(0)
    elif command[0:4] == "echo":
        echo(command[5:])
    elif command[0:4] == "type":
        type(command[5:])
    elif path := shutil.which(fcommand):
        subprocess.run(command.split(), shell=True)
       
    else:
        print(f'{command}: command not found')
    pass


if __name__ == "__main__":
    main()
