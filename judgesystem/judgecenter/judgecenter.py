### http://www.binarytides.com/python-socket-server-code-example/
import os
import socket
import select
import config
import psycopg2
import psycopg2.extras
import ftp
import sys
import json
import time
from myredis import MyRedis
from map import *
import datetime
import errno

SOCK_AVAILABLE_CMD = ['token', 'type', 'judged']
class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)

class JudgeCenter:
    def __init__(self):
        self.rs = MyRedis(host=config.redis_host, port=config.redis_port, db=config.redis_db)
        self.db = psycopg2.connect( host=config.db_host, dbname=config.db_dbname, user=config.db_user, password=config.db_password) 
        self.db.autocommit = True
        # self.ftp = ftp.FTP(config.ftp_server, config.ftp_port, config.ftp_user, config.ftp_password)

        self.recv_buffer_len = 4
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.setblocking(0)
        self.s.bind(('0.0.0.0', config.judgecenter_port))
        self.s.listen(config.judgecenter_listen)
        self.pool = [sys.stdin, self.s]
        self.client_pool = []
        self.submission_queue = []
        self.submissioning_queue = []

        self.client = {}

    def cursor(self):
        return self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    class CLIENT():
        def __init__(self, addr):
            self.type = map_sock_type['unauth']
            self.addr = addr
            self.lock = 0
       
    def receive(self, sock):
        data = ""
        sock.setblocking(0)
        while True:
            try:
                tmp = sock.recv(self.recv_buffer_len)
            except Exception as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    break
                else:
                    self.close_socket(sock)
                    return []
            else:
                data += tmp.decode()
                if len(data)==0:
                    client = self.client[sock]
                    if client.lock != 0:
                        self.submission_queue.append(client.lock)
                        self.submissioning_queue.remove(client.lock)
                    self.close_socket(sock)
                    return []
        data = data.split("\r\n")
        res = []
        for x in data:
            if len(x):
                try:
                    res.append(json.loads(x))
                except:
                    print("err: %s" % x)
        return res

    def gen_submission_meta(self, submission_id):
        res = {}
        res['cmd'] = 'judge'
        msg = res['msg'] = {}
        msg['submission_id'] = submission_id
        cur = self.cursor()
        cur.execute('SELECT s.problem_id, p.verdict_id, s.execute_type_id, s.file_name FROM submissions as s, problems as p WHERE s.id=%s;', (submission_id,))
        msg.update(dict(cur.fetchone()))
        cur.execute('SELECT * FROM execute_types WHERE id=%s;', (msg['execute_type_id'],))
        msg['execute_type'] = dict(cur.fetchone())
        cur.execute('SELECT * FROM execute_steps WHERE execute_type_id=%s ORDER BY id;', (msg['execute_type_id'],))
        msg['execute_steps'] = [dict(x) for x in cur]
        cur.execute('SELECT id, time_limit, memory_limit, updated_at, score FROM testdata WHERE problem_id=%s ORDER BY id;', (msg['problem_id'],))
        msg['testdata'] = [dict(x) for x in cur]
        cur.execute('SELECT * FROM verdicts WHERE id=%s', (msg['verdict_id'],))
        msg['verdict'] = dict(cur.fetchone())
        cur.execute('SELECT * FROM execute_types WHERE id=%s;', (msg['verdict']['execute_type_id'],))
        msg['verdict']['execute_type'] = dict(cur.fetchone())
        cur.execute('SELECT * FROM execute_steps WHERE execute_type_id=%s ORDER BY id;', (msg['verdict']['execute_type_id'],))
        msg['verdict']['execute_steps'] = [dict(x) for x in cur]
        return res
    
    def send(self, sock, msg):
        try: sock.sendall((json.dumps(msg, cls=DatetimeEncoder)+'\r\n').encode())
        except socket.error: self.close_socket(sock)
        except Exception as e: print(e, 'send msg error')

    def get_submission(self):
        cur = self.cursor()
        delete_cur = self.cursor()
        cur.execute("SELECT * FROM wait_submissions")
        for x in cur:
            if x['submission_id'] not in self.submission_queue and x['submission_id'] not in self.submissioning_queue:
                self.submission_queue.append(x['submission_id'])

    def CommandHandler(self, cmd):
        param = cmd.lower().split(' ')
        cmd = param[0]
        if cmd == "exit":
            while len(self.client_pool):
                self.close_socket(self.client_pool[0])
            sys.exit()
        elif cmd == "insert":
            self.insert_submission(int(param[1]))
        elif cmd == "restart":
            os.execv("/usr/bin/python3", ("python3", __file__,))
        else:
            print("Unkown commnad: ", param)

    def close_socket(self, sock):
        self.pool.remove(sock)
        sock.close()
        self.client_pool.remove(sock)

    def sock_auth_token(self, sock, token):
        cur = self.cursor()
        cur.execute('SELECT * FROM judge_token WHERE token=%s;', (token,))
        if cur.rowcount == 1:
            self.client[sock].type = map_sock_type['undefined']
            print('Client from addr: %s passed auth'%(self.client[sock].addr,))
            return True
        else:
            print('Client from addr: %s failed auth'%(self.client[sock].addr,))
            return False

    def sock_set_type(self, sock, type):
        if type in map_sock_type.values():
            self.client[sock].type = type
            return True
        else:
            return False

    def sock_send_type(self, sock):
        self.send(sock, {'cmd': 'type', 'msg': self.client[sock].type})

    def sock_update_submission(self, id):
        cur = self.cursor()
        cur.execute("SELECT * FROM map_submission_testdata WHERE submission_id=%s", (id,))
        testdata = [dict(x) for x in cur]
        time = 0
        memory = 0
        score = 0
        verdict_priority = 999999
        for x in testdata:
            if x['time_usage']: time += x['time_usage']
            if x['memory_usage']: memory = max(memory, x['memory_usage'])
            if x['score']: score += x['score']
            verdict_priority = min(verdict_priority, self.map_verdict_priority[x['verdict']])
        if verdict_priority == 999999:
            verdict_priority = self.map_verdict_priority[2]
        verdict = self.map_priority_verdict[verdict_priority]
        if memory == 0:
            cur.execute("UPDATE submissions SET verdict=%s, score=%s WHERE id=%s", (verdict_priority, score,id))
        else:
            cur.execute("UPDATE submissions SET verdict=%s, score=%s, time_usage=%s, memory_usage=%s WHERE id=%s", (verdict_priority, score,time,memory, id,))
        cur.execute("DELETE FROM wait_submissions WHERE submission_id=%s", (id,))

    def sock_update_submission_testdata(self, msg):
        cur = self.cursor()
        cur.execute("INSERT INTO map_submission_testdata (submission_id, testdata_id, verdict) VALUES (%s, %s, %s) RETURNING id", (msg['submission_id'], msg['testdata_id'], msg['verdict'],))
        x = cur.fetchone()
        if 'time_usage' in msg:
            cur.execute("UPDATE map_submission_testdata SET time_usage=%s, memory_usage=%s, score=%s WHERE id=%s", (msg['time_usage'],msg['memory_usage'],msg['score'],x[0],))
        pass

    def sock_send_submission(self, sock, submission_id):
        msg = self.gen_submission_meta(submission_id)
        self.send(sock, msg)

    def ReadSockHandler(self, sock):
        client = self.client[sock]
        MSGS = self.receive(sock)
        print(MSGS)
        for msg in MSGS:
            print('READ: ', msg, client.type)
            if msg is None: return
            if msg['cmd'] == 'type' and msg['msg'] == '':
                self.sock_send_type(sock)
            elif client.type == map_sock_type['unauth']:
                if msg['cmd'] == 'token':
                    res = self.sock_auth_token(sock, msg['msg'])
                else:
                    print('not auth')
            elif client.type == map_sock_type['undefined']:     # undefined
                if msg['cmd'] == 'type':
                    self.sock_set_type(sock, msg['msg'])
                else:
                    print('undefined')
            elif client.type == map_sock_type['judge']:   # judge
                if msg['cmd'] == 'judged_testdata':
                    self.sock_update_submission_testdata(msg['msg'])
                elif msg['cmd'] == 'judged':
                    self.sock_update_submission(client.lock)
                    self.submissioning_queue.remove(client.lock)
                    client.lock = 0
                else:
                    print('unkown cmd')
            elif client.type == map_sock_type['web']:   # web
                pass
            else:
                print("error")

    def WriteSockHandler(self, sock):
        if sock not in self.client: return
        client = self.client[sock]
        if client.type == map_sock_type['unauth']:
            pass
        elif client.type == map_sock_type['undefined']:
            pass
        elif client.type == map_sock_type['judge']:
            if len(self.submission_queue) and client.lock == 0:
                id = self.submission_queue.pop(0)
                self.submissioning_queue.append(id)
                self.sock_send_submission(sock, id)
                client.lock = id
        elif client.type == map_sock_type['web']:
            pass
        else:
            print('error')
            self.close_socket(sock)

    def insert_submission(self, submission_id):
        cur = self.cursor()
        try:
            cur.execute("INSERT INTO wait_submissions (submission_id) VALUES (%s);", (submission_id,))
            print("succ insert %s"%str(submission_id))
        except:
            print("insert failed")
        
    def run(self):
        cur = self.cursor()
        cur.execute("SELECT * FROM map_verdict_string")
        map_verdict_string = [dict(x) for x in cur]
        self.map_verdict_priority = {}
        self.map_priority_verdict = {}
        for x in map_verdict_string:
            self.map_priority_verdict[x['priority']] = x['id']
            self.map_verdict_priority[x['id']] = x['priority']
        print(self.map_verdict_priority)

        while True:
            try:
                self.get_submission()
            except:
                pass
            read_sockets, write_sockets, error_sockets = select.select(self.pool, [], [], 0.1)
            for sock in read_sockets:
                if sock == self.s:
                    sockfd, addr = sock.accept()
                    self.pool.append(sockfd)
                    self.client_pool.append(sockfd)
                    self.client[sockfd] = self.CLIENT(addr)
                    self.send(sockfd, {
                        "cmd": "map_verdict_string",
                        "msg": map_verdict_string
                    })
                    print("client (%s, %s) connected" % addr)
                elif sock == sys.stdin:
                    self.CommandHandler(input())
                else:
                    self.ReadSockHandler(sock)
            for sock in self.client_pool:
                self.WriteSockHandler(sock)

if __name__ == "__main__":
    print("====start====")
    judgecenter = JudgeCenter()
    #judgecenter.insert_submission()
    judgecenter.run()
