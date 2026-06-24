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
#include <signal.h>
#include <deque>

using namespace std;

// -----------------------------------------------------------------
// GLOBALS & DATA STRUCTURES
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
deque<string> cmd_history;

// -----------------------------------------------------------------
// PARSER UTILITIES
// -----------------------------------------------------------------
vector<char*> parse_command(const string& input) {
    vector<char*> args;
    string current = "";
    bool in_quotes = false;
    char quote_char = 0;

    for (size_t i = 0; i < input.size(); i++) {
        char c = input[i];
        if ((c == '"' || c == '\'') && (i == 0 || input[i-1] != '\\')) {
            if (!in_quotes) { in_quotes = true; quote_char = c; } 
            else if (c == quote_char) { in_quotes = false; quote_char = 0; } 
            else { current += c; }
        } 
        else if (isspace(c) && !in_quotes) {
            if (!current.empty()) {
                char* arg = new char[current.size() + 1];
                strcpy(arg, current.c_str());
                args.push_back(arg);
                current = "";
            }
        } 
        else { current += c; }
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
    for (char* arg : args) { if (arg != nullptr) delete[] arg; }
}

vector<string> split_by_pipe(const string& input) {
    vector<string> commands;
    stringstream ss(input);
    string cmd;
    while (getline(ss, cmd, '|')) commands.push_back(cmd);
    return commands;
}

// -----------------------------------------------------------------
// EXECUTION ENGINES 
// -----------------------------------------------------------------
bool execute_process(vector<char*>& raw_args, bool is_background) {
    if (raw_args.empty() || raw_args[0] == nullptr) return true;

    if (strcmp(raw_args[0], "exit") == 0) {
        cout << "Exiting shell safely..." << endl;
        _exit(0); 
    }
    if (strcmp(raw_args[0], "cd") == 0) {
        int res = -1;
        if (raw_args[1] != nullptr) res = chdir(raw_args[1]);
        else {
            const char* home = getenv("HOME");
            if (home != nullptr) res = chdir(home);
        }
        if (res != 0) perror("cd failed");
        return res == 0; 
    }
    if (strcmp(raw_args[0], "history") == 0) {
        for (size_t i = 0; i < cmd_history.size(); i++) {
            cout << "  " << (i + 1) << "  " << cmd_history[i] << endl;
        }
        return true;
    }

    string input_file = "", output_file = "";
    vector<char*> clean_args;
    for (size_t i = 0; raw_args[i] != nullptr; i++) {
        if (strcmp(raw_args[i], ">") == 0 && raw_args[i+1] != nullptr) { output_file = raw_args[i+1]; i++; } 
        else if (strcmp(raw_args[i], "<") == 0 && raw_args[i+1] != nullptr) { input_file = raw_args[i+1]; i++; } 
        else { clean_args.push_back(raw_args[i]); }
    }
    clean_args.push_back(nullptr);

    auto start_time = chrono::high_resolution_clock::now();
    pid_t pid = fork();

    if (pid < 0) {
        perror("Fork failed");
        return false;
    } else if (pid == 0) {
        // CHILD
        signal(SIGINT, SIG_DFL);

        if (!output_file.empty()) {
            int fd = open(output_file.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
            dup2(fd, STDOUT_FILENO); close(fd);
        }
        if (!input_file.empty()) {
            int fd = open(input_file.c_str(), O_RDONLY);
            dup2(fd, STDIN_FILENO); close(fd);
        }
        if (execvp(clean_args[0], clean_args.data()) == -1) {
            perror("Command not found");
            // CRITICAL FIX: Use _exit(1) to avoid multithreaded destructor deadlocks
            _exit(1); 
        }
    } else {
        // PARENT
        int status;
        if (is_background) {
            struct rusage usage;
            wait4(pid, &status, 0, &usage); 
            auto end_time = chrono::high_resolution_clock::now();
            chrono::duration<double> wall = end_time - start_time;
            double u_cpu = usage.ru_utime.tv_sec + (usage.ru_utime.tv_usec / 1e6);
            double s_cpu = usage.ru_stime.tv_sec + (usage.ru_stime.tv_usec / 1e6);
            cout << "\n=== [Background Job Finished] ===\n"
                 << "Wall-Clock : " << wall.count() << " s\n"
                 << "User CPU   : " << u_cpu << " s\n"
                 << "System CPU : " << s_cpu << " s\n"
                 << "Peak RAM   : " << usage.ru_maxrss << " KB\n"
                 << "=================================\n$ " << flush;
        } else {
            waitpid(pid, &status, 0); 
        }
        return WIFEXITED(status) && (WEXITSTATUS(status) == 0);
    }
    return false;
}

bool execute_pipeline(const vector<string>& string_cmds) {
    int num_cmds = string_cmds.size();
    int pipefds[2 * (num_cmds - 1)];
    for (int i = 0; i < num_cmds - 1; i++) { pipe(pipefds + i * 2); }

    int final_status = 0;
    pid_t last_pid = -1;

    for (int i = 0; i < num_cmds; i++) {
        pid_t pid = fork();
        if (pid == 0) {
            signal(SIGINT, SIG_DFL); 
            if (i > 0) dup2(pipefds[(i - 1) * 2], STDIN_FILENO);
            if (i < num_cmds - 1) dup2(pipefds[i * 2 + 1], STDOUT_FILENO);
            for (int j = 0; j < 2 * (num_cmds - 1); j++) close(pipefds[j]);

            vector<char*> args = parse_command(string_cmds[i]);
            if (execvp(args[0], args.data()) == -1) {
                perror("Pipeline command not found");
                _exit(1);
            }
        }
        if (i == num_cmds - 1) last_pid = pid; 
    }

    for (int i = 0; i < 2 * (num_cmds - 1); i++) close(pipefds[i]);
    
    for (int i = 0; i < num_cmds; i++) {
        int status;
        pid_t wpid = wait(&status);
        if (wpid == last_pid) final_status = status;
    }
    return WIFEXITED(final_status) && (WEXITSTATUS(final_status) == 0);
}

// -----------------------------------------------------------------
// LOGICAL EVALUATOR
// -----------------------------------------------------------------
struct LogicNode {
    string cmd;
    int op; 
};

bool execute_logic_chain(string input, bool is_bg) {
    vector<LogicNode> chain;
    string cur = "";
    int cur_op = 0;

    for (size_t i = 0; i < input.size(); i++) {
        if (i + 1 < input.size() && input[i] == '&' && input[i+1] == '&') {
            chain.push_back({cur, cur_op});
            cur = ""; cur_op = 1; i++;
        } else if (i + 1 < input.size() && input[i] == '|' && input[i+1] == '|') {
            chain.push_back({cur, cur_op});
            cur = ""; cur_op = 2; i++;
        } else {
            cur += input[i];
        }
    }
    chain.push_back({cur, cur_op});

    bool prev_success = true;
    for (const auto& node : chain) {
        if (node.op == 1 && !prev_success) continue; 
        if (node.op == 2 && prev_success) continue;  

        if (node.cmd.find('|') != string::npos) {
            vector<string> cmds = split_by_pipe(node.cmd);
            prev_success = execute_pipeline(cmds);
        } else {
            vector<char*> args = parse_command(node.cmd);
            prev_success = execute_process(args, is_bg);
            cleanup_args(args);
        }
    }
    return prev_success;
}

// -----------------------------------------------------------------
// WORKER THREAD & MAIN
// -----------------------------------------------------------------
void worker_thread_loop(int thread_id) {
    Job job;
    while (true) {
        bg_queue.pop(job); 
        execute_logic_chain(job.command, true);
        fflush(stdout);
    }
}

int main() {
    signal(SIGINT, SIG_IGN);

    vector<thread> thread_pool;
    for (int i = 0; i < 4; i++) thread_pool.push_back(thread(worker_thread_loop, i));
    for (auto& t : thread_pool) t.detach();

    cout << "Systems C++ Shell [Ultimate Edition]. Type 'exit' to quit." << endl;
    string input;

    while (true) {
        cout << "$ " << flush;
        if (!getline(cin, input)) { cout << endl; break; }
        if (input.empty()) continue;     

        if (input[0] == '!' && input.length() > 1) {
            try {
                int idx = stoi(input.substr(1)) - 1;
                if (idx >= 0 && idx < cmd_history.size()) {
                    input = cmd_history[idx];
                    cout << input << endl; 
                } else {
                    cout << "history: event not found" << endl;
                    continue;
                }
            } catch (...) {
                cout << "history: invalid syntax" << endl;
                continue;
            }
        }
        cmd_history.push_back(input);

        bool is_background = false;
        string cmd_to_run = input;
        size_t last_char_pos = input.find_last_not_of(" \t");
        
        if (last_char_pos != string::npos && input[last_char_pos] == '&' && 
           (last_char_pos == 0 || input[last_char_pos-1] != '&')) {
            is_background = true;
            cmd_to_run = input.substr(0, last_char_pos);
        }

        if (is_background) {
            bg_queue.push({job_counter++, cmd_to_run});
        } else {
            execute_logic_chain(cmd_to_run, false);
            fflush(stdout);
        }
    }
    return 0;
}