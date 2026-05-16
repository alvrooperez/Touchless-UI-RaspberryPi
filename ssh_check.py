import pty
import os
import sys
import time

def master_read(fd):
    data = os.read(fd, 1024)
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return data

def master_write(fd, data):
    os.write(fd, data)

# Start ssh
pid, fd = pty.fork()

if pid == 0:
    # Child
    os.execvp('ssh', ['ssh', '-tt', '-o', 'StrictHostKeyChecking=no', 'domotica@192.168.1.146'])
else:
    # Parent
    time.sleep(2)
    output = master_read(fd)
    if b'password' in output.lower():
        master_write(fd, b'domotica123\n')
    
    time.sleep(2)
    master_write(fd, b'docker ps\n')
    time.sleep(1)
    master_write(fd, b'docker logs $(docker ps -q | head -n 1)\n')
    time.sleep(5)
    
    # Read remaining output
    while True:
        try:
            os.read(fd, 1024)
            # Just draining or we could print it. 
            # Actually, I'll just print it all.
            data = os.read(fd, 1024)
            if not data: break
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        except OSError:
            break
