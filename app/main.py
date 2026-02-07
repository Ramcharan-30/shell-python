import sys


def main():
   builtin_commands = ["echo", "exit","type"]
   while(1): 
    sys.stdout.write("$ ")
    command = input()
    if command == "exit":
        sys.exit(0)
    elif command[0:4] == "echo":
        print(f'{command[5:]}')
    elif command[0:4] == "type":
        if command[5:] in builtin_commands:
            print(f'{command[5:]} is a shell builtin')
        else:
            print(f'{command[5:]} not found')
       
    else:
        print(f'{command}: command not found')
    pass


if __name__ == "__main__":
    main()
