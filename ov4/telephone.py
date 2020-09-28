import numpy as np
import simpy 

# Seconds
NEXT_CALL = 30*60
MAX_CONNECTION_TIME = 15
FIXED_CONNECTION_TIME = 0.2
DISCONNECT_TIME = 0.2
AVG_VARIABLE_CONNECTION = 3
AVG_CONVERSATION_TIME = 3*60

SIM_TIME = 30*24*60*60 # 30 days in seconds

def time_to_next_call():
    return np.random.exponential(NEXT_CALL)

def time_for_connection():
    return np.random.exponential(AVG_VARIABLE_CONNECTION)

def time_for_conv():
    return np.random.exponential(AVG_CONVERSATION_TIME)

class Subscriber: 
    def __init__(self, env, name):
        self.env = env
        self.name = name
        self.interrupted = False
        self.process = env.process(self.inititate_call())
        self.calls = 0 
        self.lost_calls = 0
        self.total_duration = 0
        self.attempts = 0


    def inititate_call(self):
        while True:
            yield self.env.timeout(time_to_next_call())
            
            timer = Timer(env, self)
            conn_time = FIXED_CONNECTION_TIME + time_for_connection()
            try:
                yield self.env.timeout(conn_time)
                timer.process.interrupt()
                t = time_for_conv()
                self.calls += 1
                self.total_duration += t
                yield self.env.timeout(t)
            except simpy.Interrupt:
                self.lost_calls += 1
            
            self.attempts += 1
            yield self.env.timeout(DISCONNECT_TIME)


class Timer:
    def __init__(self, env, sub):
        self.env = env
        self.sub = sub
        self.process = env.process(self.timing())

    def timing(self):
        try:
            yield self.env.timeout(MAX_CONNECTION_TIME)
            self.sub.process.interrupt()
        except simpy.Interrupt:
            pass


env = simpy.Environment()

subs = [Subscriber(env, "Subscriber {}".format(i)) for i in range(20)]

env.run(until=SIM_TIME)

for sub in subs:
    print("{} had {}/{} lost calls. Mean duration for calls: {:.2f} seconds".format(sub.name, sub.lost_calls, sub.attempts, sub.total_duration/sub.calls))
    


