import numpy as np
import simpy
import matplotlib.pyplot as plt
import math

T_guard = 60
P_DELAY = 0.5
SIM_TIME = 86400
FIRST_PLANE = 5 #AM
MU_DELAY = 0

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
    return np.random.gamma(shape = 3, scale = MU_DELAY)

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
                # Schedule plane
                if is_delayed():
                    delay = get_delayed_time()
                else:
                    delay = 0

                self.planes.append(Plane(t + delay))
                hold_time = np.maximum(T_guard, T)
                yield self.env.timeout(hold_time)
            else:
                yield self.env.timeout(1)

def find_means_per_clock_hour(average_hours, inter_arrivals):
    prev = FIRST_PLANE
    means = []
    IAs = []
    for inter_arrival, average_hour in zip(inter_arrivals, average_hours):
        hour = math.floor(average_hour)

        if hour == prev:
            IAs.append(inter_arrival[0])
        else:
            means.append(sum(IAs)/len(IAs))
            IAs = [inter_arrival[0]]
            prev = hour

    means.append(sum(IAs)/len(IAs))

    return means

def simulate():
    env = simpy.Environment()

    gen = PlaneGenerator(env)

    env.run(until=SIM_TIME)

    inter_arrival = []

    gen.planes.sort(key=lambda x:x.arrival_time)

    time = []

    for i in range(len(gen.planes) - 1):
        calc_time = (gen.planes[i+1].arrival_time+gen.planes[i].arrival_time)/2/3600

        if calc_time < 24:
            time.append((gen.planes[i+1].arrival_time+gen.planes[i].arrival_time)/2/3600)
            inter_arrival.append([gen.planes[i+1].arrival_time - gen.planes[i].arrival_time])

    return find_means_per_clock_hour(time, inter_arrival)


MU_DELAYS = [0, 5400]


for delay in MU_DELAYS:
    MU_DELAY = delay
    means = simulate()
    plt.plot([i for i in range(FIRST_PLANE, len(means)+FIRST_PLANE)], means)


plt.xlabel('Time of day [Hours]')
plt.ylabel('Inter-arrival time [seconds]')

legends = ["µ_delay = " + str(delay/3600) + " hour(s)" for delay in MU_DELAYS]

plt.legend(legends)
plt.title('Mean inter-arrival time per hour', fontsize=16)
plt.show()