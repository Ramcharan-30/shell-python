import sys


def main():
    
    sys.stdout.write("$ ")
    command = input()
    print(f'{command}:Command not found')
    pass


if __name__ == "__main__":
    main()
