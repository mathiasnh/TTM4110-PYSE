import numpy as np
import simpy
import matplotlib.pyplot as plt
import math

T_guard = 60
P_DELAY = 0.5
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
    return np.random.gamma(3, 0)

def take_means(planes):
    prev = 0
    means = []
    IAs = []
    for plane in planes:
        hour = math.floor(plane.scheduled)
        if hour == prev:
            IAs.append(plane.inter_arrival)
        else:
            means.append(sum(IAs)/len(IAs))
            IAs = [plane.inter_arrival]
            prev = hour
    return means



class Plane:
    def __init__(self, scheduled, inter_arrival):
        self.scheduled = scheduled
        self.inter_arrival = inter_arrival
        

class PlaneGenerator:
    def __init__(self, env):
        self.env = env
        self.planes = []
        env.process(self.generate())

    def generate(self):
        delay = 0
        while True:
            t = self.env.now
            T = get_scheduled_time(t)

            if T is not None:
                inter_arrival = np.maximum(T_guard, T)
                self.planes.append(Plane(t/3600, inter_arrival + delay))
                
                if is_delayed():
                    delay = get_delayed_time()
                else:
                    delay = 0

                # TODO: Schedule plane

                yield self.env.timeout(inter_arrival)
            else:
                self.planes.append(Plane(t/3600, 0))
                yield self.env.timeout(1)

env = simpy.Environment()

gen = PlaneGenerator(env)

env.run(until=SIM_TIME)

means = take_means(gen.planes)

plt.plot([i for i in range(len(means))], means)

plt.show()

