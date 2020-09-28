import numpy as np
import simpy
import matplotlib.pyplot as plt
import math

T_guard = 60
T_LANDING = 60
T_TAKEOFF = 60
P_DELAY = 0.5
MU_DELAY = 0
MU_TURNAROUND = 45
SIM_TIME = 86400

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
    elif time < 86400:
        return np.random.exponential(120)

def is_delayed():
    return np.random.choice([True, False], p=[P_DELAY, 1 - P_DELAY])

def get_delayed_time():
    return np.random.gamma(3, MU_DELAY)

def get_turnaround_time():
    return np.random.gamma(7, MU_TURNAROUND)

def take_means(planes, what):
    prev = 5
    means = [0,0,0,0,0]
    thing = []
    for plane in planes:
        hour = math.floor(plane.scheduled)
        print(hour)
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
    def __init__(self, env, scheduled, inter_arrival, delay, runways):
        self.scheduled = scheduled
        self.inter_arrival = inter_arrival + delay
        self.delay = delay
        self.env = env
        self.landing_q_time = 0
        self.takeoff_q_time = 0
        env.process(self.land())

    def land(self):
        yield self.env.timeout(self.delay)

        landing_start = self.env.now

        with runways.request(priority=1) as req:
            yield req
            yield self.env.timeout(T_LANDING)

        landing_end = self.env.now
        
        yield self.env.timeout(get_turnaround_time())

        takeoff_start = self.env.now

        with runways.request(priority=2) as req:
            yield req
            yield self.env.timeout(T_TAKEOFF)
        
        takeoff_end = self.env.now

        self.landing_q_time = (landing_end - landing_start) - T_LANDING
        self.takeoff_q_time = (takeoff_end - takeoff_start) - T_TAKEOFF

        #print(landing_q_time, takeoff_q_time)


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
                inter_arrival = np.maximum(T_guard, T)
                
                if is_delayed():
                    delay = get_delayed_time()
                else:
                    delay = 0

                self.planes.append(Plane(env, t/3600, inter_arrival, delay, runways))
                # TODO: Schedule plane

                yield self.env.timeout(inter_arrival)
            else:
                #self.planes.append(Plane(t/3600, 0,))
                yield self.env.timeout(1)

env = simpy.Environment()

runways = simpy.PriorityResource(env, capacity=2)
gen = PlaneGenerator(env, runways)


env.run(until=SIM_TIME)

landing_means = take_means(gen.planes, "landing")
takeoff_means = take_means(gen.planes, "takeoff")

plt.plot([i for i in range(len(landing_means))], landing_means)
plt.plot([i for i in range(len(takeoff_means))], takeoff_means)
plt.legend(['Landing', 'take-off'])
plt.xlabel('Hour')
plt.ylabel('Qeueu time (seconds)')
plt.title('Mean landing and take-off times', fontsize=16)

plt.show()

