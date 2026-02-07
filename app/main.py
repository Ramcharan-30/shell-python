import sys


def main():
    
    sys.stdout.write("$ ")
    command = input()
    print(f'Command not found: {command}')
    pass


if __name__ == "__main__":
    main()
