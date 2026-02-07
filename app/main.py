import sys


def main():
   while(1): 
    sys.stdout.write("$ ")
    command = input()
    if command == "exit":
        sys.exit(0)
    elif command[0:4] == "echo":
        print(f'{command[5:]}')
    else:
        print(f'{command}: command not found')
    pass


if __name__ == "__main__":
    main()
