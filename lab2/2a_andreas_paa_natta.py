import numpy as np
import simpy
import matplotlib.pyplot as plt
import math

T_guard = 60
P_DELAY = 0.5
SIM_TIME = 86400
MU_DELAY = 3600*5
FIRST_PLANE = 5 #AM

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

class Plane:
    def __init__(self, arrival_time):
        self.arrival_time = arrival_time

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
                self.planes.append(Plane(t + delay))
                # Schedule plane
                if is_delayed():
                    delay = get_delayed_time()
                else:
                    delay = 0

                hold_time = np.maximum(T_guard, T)
                yield self.env.timeout(hold_time)
            else:
                yield self.env.timeout(1)

env = simpy.Environment()

gen = PlaneGenerator(env)

env.run(until=SIM_TIME)

means = []

prev_hour = FIRST_PLANE
inter_arrival = []

gen.planes.sort(key=lambda x:x.arrival_time)

"""
for i in range(len(gen.planes) - 1):
    hour = math.floor((gen.planes[i+1].arrival_time+gen.planes[i].arrival_time)/2/3600)

    if hour == prev_hour:
        inter_arrival.append(gen.planes[i+1].arrival_time - gen.planes[i].arrival_time)
    else:
        means.append(sum(inter_arrival)/len(inter_arrival))
        inter_arrival = [gen.planes[i+1].arrival_time - gen.planes[i].arrival_time]
        prev_hour = hour

means.append(sum(inter_arrival)/len(inter_arrival))

plt.plot([i for i in range(FIRST_PLANE,len(means)+FIRST_PLANE)], means)
"""

time = []

for i in range(len(gen.planes) - 1):
    inter_arrival.append([gen.planes[i+1].arrival_time - gen.planes[i].arrival_time])
    time.append((gen.planes[i+1].arrival_time+gen.planes[i].arrival_time)/2/3600)

plt.plot(time, inter_arrival)

plt.xlabel('Time of day [Hours]')
plt.ylabel('Inter-arrival time [seconds]')
plt.title('Mean inter-arrival time per hour (µ_delay=' + str(MU_DELAY) + ")", fontsize=16)
plt.xlim(5,24)
plt.ylim(0,1000)
plt.show()