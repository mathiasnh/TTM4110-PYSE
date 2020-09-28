import random
import numpy as np
import simpy as sp

ARRIVAL_RATE = 1/2
MAX_DELAY = 3
TRANS_DELAY = 0.2
SIM_TIME = 300

def arrival_time():
    return np.random.exponential(ARRIVAL_RATE)

def service_time():
    return np.random.gamma(3,1/3)

class Generator:
    def __init__(self, env, routers):
        self.env = env
        self.routers = routers
        self.generated = 0
        env.process(self.generate())

    def generate(self):
        while True:
            Packet(self.env, routers)
            self.generated += 1
            at = arrival_time()
            yield self.env.timeout(at)

class Packet:
    def __init__(self, env, routers):
        self.env = env
        self.routers = routers
        self.timestamp = env.now
        self.ttl = True
        self.routed = False
        env.process(self.run())

    def run(self):
        r = self.routers[random.randint(0,1)]
        #r.q_packet(self)
        yield r.env.process(r.route(self))

        if(self.ttl):
            yield self.env.timeout(TRANS_DELAY)
            r3 = self.routers[2]
            #r3.q_packet(self)
            yield r3.env.process(r3.route(self))
        

class Router:
    def __init__(self, env, num):
        self.env = env
        self.num = num
        self.packets = []
        
        # Stats
        self.lost = 0
        self.tot_e2e_delay = 0
        self.min_delay = float('inf')
        self.max_delay = float('-inf')
        
        #env.process(self.route())

    def q_packet(self, packet):
        packet.routed = False
        self.packets.append(packet)

    def route_(self):
        if(self.packets != []):
            p = self.packets.pop(0)
            if(self.env.now > p.timestamp + MAX_DELAY):
                p.ttl = False
                self.lost += 1
            else:
                st = service_time()
                yield self.env.timeout(st)
            p.routed = True

            # Stats
            if(self.num == 3):
                self.processed += 1
                e2e_delay = self.env.now - p.timestamp
                self.tot_e2e_delay += e2e_delay
                if(e2e_delay < self.min_delay):
                    self.min_delay = e2e_delay
                if(e2e_delay > self.max_delay):
                    self.max_delay = e2e_delay

    def route(self, p):
        if(self.env.now > p.timestamp + MAX_DELAY):
            p.ttl = False
            self.lost += 1
        else:
            st = service_time()
            yield self.env.timeout(st)
        p.routed = True

        # Stats
        if(self.num == 3):
            e2e_delay = self.env.now - p.timestamp
            self.tot_e2e_delay += e2e_delay
            if(e2e_delay < self.min_delay):
                self.min_delay = e2e_delay
            if(e2e_delay > self.max_delay):
                self.max_delay = e2e_delay

env = sp.Environment()

r1 = Router(env, 1)
r2 = Router(env, 2)
r3 = Router(env, 3)

routers = [r1, r2, r3]

gen = Generator(env, routers)

env.run(until=SIM_TIME)

packets_lost = 0
for r in gen.routers:
    packets_lost += r.lost

print("Packets lost:                            {}/{}".format(packets_lost, gen.generated))
print("Percentage of packets lost:              {:.2f}%".format(packets_lost/gen.generated*100))
print("Mean end-to-end delay:                   {:.2f}s".format(r3.tot_e2e_delay/gen.generated))
print("Minimal delay experienced by a packet:   {:.2f}s".format(r3.min_delay))
print("Maximal delay experienced by a packet:   {:.2f}s".format(r3.max_delay))