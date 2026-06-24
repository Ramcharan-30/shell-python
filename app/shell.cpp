#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cstring>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <fcntl.h>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <chrono>
#include <cctype>

using namespace std;

// -----------------------------------------------------------------
// THREAD-SAFE JOB QUEUE
// -----------------------------------------------------------------
struct Job {
    int id;
    string command;
};

class JobQueue {
private:
    queue<Job> q;
    mutex mtx;
    condition_variable cv;
public:
    void push(const Job& job) {
        lock_guard<mutex> lock(mtx);
        q.push(job);
        cv.notify_one(); 
    }
    bool pop(Job& job) {
        unique_lock<mutex> lock(mtx);
        cv.wait(lock, [this]() { return !q.empty(); });
        job = q.front();
        q.pop();
        return true;
    }
};

JobQueue bg_queue;
int job_counter = 1;

// -----------------------------------------------------------------
// UPGRADED PARSER: Handles and strips quotes (" " and ' ')
// -----------------------------------------------------------------
vector<char*> parse_command(const string& input) {
    vector<char*> args;
    string current = "";
    bool in_quotes = false;
    char quote_char = 0;

    for (size_t i = 0; i < input.size(); i++) {
        char c = input[i];

        // Toggle quote state
        if ((c == '"' || c == '\'') && (i == 0 || input[i-1] != '\\')) {
            if (!in_quotes) {
                in_quotes = true;
                quote_char = c;
            } else if (c == quote_char) {
                in_quotes = false;
                quote_char = 0;
            } else {
                current += c;
            }
        } 
        // Handle space delimiters outside of quotes
        else if (isspace(c) && !in_quotes) {
            if (!current.empty()) {
                char* arg = new char[current.size() + 1];
                strcpy(arg, current.c_str());
                args.push_back(arg);
                current = "";
            }
        } 
        else {
            current += c;
        }
    }
    
    if (!current.empty()) {
        char* arg = new char[current.size() + 1];
        strcpy(arg, current.c_str());
        args.push_back(arg);
    }
    
    args.push_back(nullptr); 
    return args;
}

void cleanup_args(vector<char*>& args) {
    for (char* arg : args) {
        if (arg != nullptr) delete[] arg; 
    }
}

vector<string> split_by_pipe(const string& input) {
    vector<string> commands;
    stringstream ss(input);
    string cmd;
    while (getline(ss, cmd, '|')) {
        commands.push_back(cmd);
    }
    return commands;
}

// -----------------------------------------------------------------
// CORE EXECUTION LOGIC
// -----------------------------------------------------------------
void execute_process(vector<char*>& raw_args, bool is_background) {
    if (raw_args.empty() || raw_args[0] == nullptr) return;

    // FIX: Using _exit(0) to bypass thread cleanup deadlocks
    if (strcmp(raw_args[0], "exit") == 0) {
        cout << "Exiting shell safely..." << endl;
        _exit(0); 
    }
    
    if (strcmp(raw_args[0], "cd") == 0) {
        if (raw_args[1] != nullptr) {
            if (chdir(raw_args[1]) != 0) perror("cd failed");
        } else {
            const char* home = getenv("HOME");
            if (home != nullptr) chdir(home);
        }
        return; 
    }

    string input_file = "";
    string output_file = "";
    vector<char*> clean_args;

    for (size_t i = 0; raw_args[i] != nullptr; i++) {
        if (strcmp(raw_args[i], ">") == 0 && raw_args[i+1] != nullptr) {
            output_file = raw_args[i+1];
            i++; 
        } 
        else if (strcmp(raw_args[i], "<") == 0 && raw_args[i+1] != nullptr) {
            input_file = raw_args[i+1];
            i++; 
        } 
        else {
            clean_args.push_back(raw_args[i]);
        }
    }
    clean_args.push_back(nullptr);

    auto start_time = chrono::high_resolution_clock::now();
    pid_t pid = fork();

    if (pid < 0) {
        perror("Fork failed");
    } else if (pid == 0) {
        if (!output_file.empty()) {
            int fd = open(output_file.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd < 0) { perror("Failed to open output file"); exit(1); }
            dup2(fd, STDOUT_FILENO);
            close(fd);
        }
        if (!input_file.empty()) {
            int fd = open(input_file.c_str(), O_RDONLY);
            if (fd < 0) { perror("Failed to open input file"); exit(1); }
            dup2(fd, STDIN_FILENO);
            close(fd);
        }

        if (execvp(clean_args[0], clean_args.data()) == -1) {
            perror("Command not found");
            exit(1);
        }
    } else {
        int status;
        if (is_background) {
            struct rusage usage;
            wait4(pid, &status, 0, &usage); 

            auto end_time = chrono::high_resolution_clock::now();
            chrono::duration<double> wall_clock = end_time - start_time;
            double user_cpu = usage.ru_utime.tv_sec + (usage.ru_utime.tv_usec / 1000000.0);
            double sys_cpu = usage.ru_stime.tv_sec + (usage.ru_stime.tv_usec / 1000000.0);

            cout << "\n\n=== [Background Job Finished] ===" << endl;
            cout << "Wall-Clock : " << wall_clock.count() << " seconds" << endl;
            cout << "User CPU   : " << user_cpu << " seconds" << endl;
            cout << "System CPU : " << sys_cpu << " seconds" << endl;
            cout << "Peak RAM   : " << usage.ru_maxrss << " KB" << endl;
            cout << "=================================\n$ " << flush;
        } else {
            waitpid(pid, &status, 0); 
        }
    }
}

void execute_pipeline(const vector<string>& string_cmds) {
    int num_cmds = string_cmds.size();
    int pipefds[2 * (num_cmds - 1)];

    for (int i = 0; i < num_cmds - 1; i++) {
        if (pipe(pipefds + i * 2) < 0) {
            perror("Pipe creation failed");
            return;
        }
    }

    for (int i = 0; i < num_cmds; i++) {
        pid_t pid = fork();
        if (pid == 0) {
            if (i > 0) dup2(pipefds[(i - 1) * 2], STDIN_FILENO);
            if (i < num_cmds - 1) dup2(pipefds[i * 2 + 1], STDOUT_FILENO);

            for (int j = 0; j < 2 * (num_cmds - 1); j++) close(pipefds[j]);

            vector<char*> args = parse_command(string_cmds[i]);
            if (execvp(args[0], args.data()) == -1) {
                perror("Pipeline command not found");
                exit(1);
            }
        }
    }

    for (int i = 0; i < 2 * (num_cmds - 1); i++) close(pipefds[i]);
    for (int i = 0; i < num_cmds; i++) wait(NULL);
}

void worker_thread_loop(int thread_id) {
    Job job;
    while (true) {
        bg_queue.pop(job); 
        if (job.command.find('|') != string::npos) {
            vector<string> cmds = split_by_pipe(job.command);
            execute_pipeline(cmds);
            cout << "\n\n=== [Background Pipeline Finished] ===\n$ " << flush;
        } else {
            vector<char*> args = parse_command(job.command);
            execute_process(args, true); 
            cleanup_args(args);
        }
    }
}

// -----------------------------------------------------------------
// MAIN: REPL
// -----------------------------------------------------------------
int main() {
    vector<thread> thread_pool;
    for (int i = 0; i < 4; i++) {
        thread_pool.push_back(thread(worker_thread_loop, i));
    }
    for (auto& t : thread_pool) t.detach();

    cout << "Systems C++ Shell [Engine Ready]. Type 'exit' to quit." << endl;
    string input;

    while (true) {
        cout << "$ ";
        if (!getline(cin, input)) break; 
        if (input.empty()) continue;     

        // Direct interception of exit command in main thread
        if (input == "exit") {
            cout << "Exiting shell safely..." << endl;
            _exit(0);
        }

        bool is_background = false;
        string cmd_to_run = input;
        
        size_t last_char_pos = input.find_last_not_of(" \t");
        if (last_char_pos != string::npos && input[last_char_pos] == '&') {
            is_background = true;
            cmd_to_run = input.substr(0, last_char_pos);
            last_char_pos = cmd_to_run.find_last_not_of(" \t");
            if (last_char_pos != string::npos) {
                cmd_to_run = cmd_to_run.substr(0, last_char_pos + 1);
            }
        }

        if (is_background) {
            bg_queue.push({job_counter++, cmd_to_run});
        } 
        else {
            if (cmd_to_run.find('|') != string::npos) {
                vector<string> cmds = split_by_pipe(cmd_to_run);
                execute_pipeline(cmds);
            } else {
                vector<char*> args = parse_command(cmd_to_run);
                execute_process(args, false); 
                cleanup_args(args);
            }
        }
    }
    return 0;
}