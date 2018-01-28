import pty
from os import waitpid, execv, read, write, path
import json

class MinerPerf():
    def __init__(self, host):

        self.execute = "cgminer-api -o stats"
        self.host = host
        configs = json.load(open( path.join(path.dirname(path.realpath(__file__)),'config.json') ))
        self.user, self.password = configs['miner_user'], configs['miner_pwd']
        self.password = "admin"
        self.askpass = True

    def get(self):
        output = self.run_ssh_query()
        return self.parse(output)

    def parse(self, input):
        try:
            stats = input.split('|')[2]
            dict = {rows.split("=")[0]:rows.split("=")[1] for rows in stats.split(",") }
            miner_stats={
                'pcb_temp': {
                    0: dict["temp1"],
                    1: dict["temp2"],
                    2: dict["temp3"],
                    3: dict["temp4"],
                },
                'chip_temp': {
                    0: dict["temp2_1"],
                    1: dict["temp2_2"],
                    2: dict["temp2_3"],
                    3: dict["temp2_4"],
                },
                'miner_speed': {
                    'GHS 5s': dict["GHS 5s"],
                    'GHS av': dict["GHS av"],
                }
            }
        except:
            return None
        return miner_stats

    def run_ssh_query(self):
        command = [
                '/usr/bin/ssh',
                self.user+'@'+self.host,
                self.execute,
        ]

        # PID = 0 for child, and the PID of the child for the parent
        pid, child_fd = pty.fork()

        if not pid: # Child process
            # Replace child process with our SSH process
            execv(command[0], command)

        ## if we havn't setup pub-key authentication
        ## we can loop for a password promt and "insert" the password.
        while self.askpass:
            try:
                output = read(child_fd, 2048).strip()
            except:
                break
            lower = output.lower()
            # Write the password
            if b'password:' in lower:
                write(child_fd, self.password + '\n')
            else:
                return output


            waitpid(pid, 0)
