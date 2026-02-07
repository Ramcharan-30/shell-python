import sys


def main():
   while(1): 
    sys.stdout.write("$ ")
    command = input()
    if command == "exit":
        sys.exit(0)
    else:
        print(f'{command}: command not found')
    pass


if __name__ == "__main__":
    main()
