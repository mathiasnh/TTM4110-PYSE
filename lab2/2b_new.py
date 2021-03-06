import numpy as np
import simpy
import matplotlib.pyplot as plt
import math

P_DELAY = 0.5
SIM_TIME = 86400
MU_DELAY = 60
FIRST_PLANE = 5 #AM

T_guard = 60 # seconds
T_LANDING = 60 # seconds
T_TAKEOFF = 60 # seconds
MU_TURNAROUND = 45*60 # seconds

def get_scheduled_time(time):
    if time < 18000:
        return None
    elif time < 28800:
        return np.random.exponential(120)
    elif time < 39600:
        return np.random.exponential(30)
    elif time < 54000:
        return np.random.exponential(150)
    elif time < 72000:
        return np.random.exponential(30)
    elif time <= 86400:
        return np.random.exponential(120)

def is_delayed():
    return np.random.choice([True, False], p=[P_DELAY, 1 - P_DELAY])

def get_delayed_time():
    return np.random.gamma(3, MU_DELAY)

def get_turnaround_time():
    return np.random.gamma(7, MU_TURNAROUND)

def take_means(planes, what):
    prev = FIRST_PLANE
    means = [0]*FIRST_PLANE
    thing = []
    for plane in planes:
        hour = math.floor(plane.arrival_time/3600)
        if hour < 24:
            if hour == prev:
                if what == "landing":
                    thing.append(plane.landing_q_time)
                elif what == "takeoff":
                    thing.append(plane.takeoff_q_time)
            else:
                means.append(sum(thing)/len(thing))
                if what == "landing":
                    thing = [plane.landing_q_time]
                elif what == "takeoff":
                    thing = [plane.takeoff_q_time]
                
                prev = hour
    means.append(sum(thing)/len(thing))
    return means

class Plane:
    def __init__(self, env, scheduled, delay, runways):
        self.env = env
        self.scheduled = scheduled
        self.arrival_time = scheduled + delay
        self.delay = delay
        self.runways = runways
        self.landing_q_time = 0
        self.takeoff_q_time = 0
        env.process(self.land())

    def land(self):
        yield self.env.timeout(self.delay)

        landing_start = self.env.now

        # Request runway for landing (high priority)
        with self.runways.request(priority=1) as req:
            yield req
            yield self.env.timeout(T_LANDING)

        landing_end = self.env.now
        
        yield self.env.timeout(get_turnaround_time())

        takeoff_start = self.env.now

        # Request runway for take-off (low priority)
        with self.runways.request(priority=2) as req:
            yield req
            yield self.env.timeout(T_TAKEOFF)
        
        takeoff_end = self.env.now

        self.landing_q_time = (landing_end - landing_start) - T_LANDING
        self.takeoff_q_time = (takeoff_end - takeoff_start) - T_TAKEOFF

class PlaneGenerator:
    def __init__(self, env, runways):
        self.env = env
        self.runways = runways
        self.planes = []
        env.process(self.generate())

    def generate(self):
        delay = 0
        while True:
            t = self.env.now
            T = get_scheduled_time(t)

            if T is not None:
                if is_delayed():
                    delay = get_delayed_time()
                else:
                    delay = 0

                self.planes.append(Plane(self.env, t, delay, self.runways))
                hold_time = np.maximum(T_guard, T)
                yield self.env.timeout(hold_time)
            else:
                yield self.env.timeout(1)


def simulate():
    env = simpy.Environment()

    runways = simpy.PriorityResource(env, capacity=2)
    gen = PlaneGenerator(env, runways)

    env.run(until=SIM_TIME)

    gen.planes.sort(key=lambda x:x.arrival_time)

    landing_means = take_means(gen.planes, "landing")
    takeoff_means = take_means(gen.planes, "takeoff")

    return landing_means, takeoff_means

legends = []

"""
MU_DELAYS = [0, 3600*1.5]
i = 0
for delay in MU_DELAYS:
    MU_DELAY = delay
    landing_means, takeoff_means = simulate()
    if len(MU_DELAYS) == 1:
        plt.plot([i for i in range(len(landing_means))], landing_means)
        plt.plot([i for i in range(len(takeoff_means))], takeoff_means)
    elif i == 0:
        plt.plot([i for i in range(len(landing_means))], landing_means, "m")
        plt.plot([i for i in range(len(takeoff_means))], takeoff_means, "m--")
    else:
        plt.plot([i for i in range(len(landing_means))], landing_means, "g")
        plt.plot([i for i in range(len(takeoff_means))], takeoff_means, "g--")
        
    legends.append("Landing, µ = " + str(delay/3600) + " hour(s)")
    legends.append("Take-off, µ = " + str(delay/3600) + " hour(s)")
    
    i+=1
"""
P_DELAYS = [0.1, 0.9]
i = 0
for delay in P_DELAYS:
    P_DELAY = delay
    landing_means, takeoff_means = simulate()
    if len(P_DELAYS) == 1:
        plt.plot([i for i in range(len(landing_means))], landing_means)
        plt.plot([i for i in range(len(takeoff_means))], takeoff_means)
    elif i == 0:
        plt.plot([i for i in range(len(landing_means))], landing_means, "m")
        plt.plot([i for i in range(len(takeoff_means))], takeoff_means, "m--")
    else:
        plt.plot([i for i in range(len(landing_means))], landing_means, "g")
        plt.plot([i for i in range(len(takeoff_means))], takeoff_means, "g--")
        
    legends.append("Landing, P_delay = " + str(delay))
    legends.append("Take-off, P_delay = " + str(delay))
    
    i+=1

plt.legend(['Landing', 'Take-off'])
plt.xlabel('Hour of day')
plt.ylabel('Queue time (seconds)')
plt.legend(legends)
plt.title('Mean landing and take-off times', fontsize=16)

plt.show()