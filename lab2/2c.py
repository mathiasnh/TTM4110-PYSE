import numpy as np
import simpy
import matplotlib.pyplot as plt
import math

P_DELAY = 0.5
SIM_TIME = 86400
MU_DELAY = 3600*0
MU_TURNAROUND = 60*45
BAD_WEATHER = 3600*1
GOOD_WEATHER = 3600*2
SNOW_TIME = 60*45
NUM_RUNWAYS = 2
NUM_PLOW_TRUCKS = 1
NUM_DEICING_TRUCKS = 10
T_guard = 60
T_LANDING = 60
T_TAKEOFF = 60
T_PLOW = 60*10*NUM_RUNWAYS/NUM_PLOW_TRUCKS
T_DEICE = 60*10*1
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
    elif time <= 86400:
        return np.random.exponential(120)

def is_delayed():
    return np.random.choice([True, False], p=[P_DELAY, 1 - P_DELAY])

def get_delayed_time():
    return np.random.gamma(3, MU_DELAY)

def get_turnaround_time():
    return np.random.gamma(7, MU_TURNAROUND)

def get_snow_time():
    return np.random.exponential(BAD_WEATHER)

def get_clear_time():
    return np.random.exponential(GOOD_WEATHER)

def get_runway_fill_time():
    return np.random.exponential(SNOW_TIME)

def take_means(planes, what):
    prev = 5
    means = [0,0,0,0,0]
    thing = []
    for plane in planes:
        hour = math.floor(plane.arrival_time/3600)
        if hour < 24:
            if hour == prev:
                if what == "landing":
                    thing.append(plane.landing_q_time)
                elif what == "takeoff":
                    thing.append(plane.takeoff_q_time)
                elif what == "deicing":
                    thing.append(plane.deicing_q_time)
            else:
                means.append(sum(thing)/len(thing))
                if what == "landing":
                    thing = [plane.landing_q_time]
                elif what == "takeoff":
                    thing = [plane.takeoff_q_time]
                elif what == "deicing":
                    thing.append(plane.deicing_q_time)
                
                prev = hour
    means.append(sum(thing)/len(thing))
    return means

class Plane:
    def __init__(self, env, scheduled, delay, runways, deicing_trucks):
        self.env = env
        self.scheduled = scheduled
        self.arrival_time = scheduled + delay
        self.delay = delay
        self.runways = runways
        self.deicing_trucks = deicing_trucks
        self.landing_q_time = 0
        self.takeoff_q_time = 0
        self.deicing_q_time = 0
        env.process(self.land())

    def land(self):
        yield self.env.timeout(self.delay)

        landing_start = self.env.now

        with runways.request(priority=1) as req:
            yield req
            yield self.env.timeout(T_LANDING)

        landing_end = self.env.now
        
        yield self.env.timeout(get_turnaround_time())

        deicing_start = self.env.now

        with deicing_trucks.request(priority=1) as req:
            yield req
            yield self.env.timeout(T_DEICE)

        deicing_end = self.env.now
        
        takeoff_start = self.env.now

        with runways.request(priority=2) as req:
            yield req
            yield self.env.timeout(T_TAKEOFF)
        
        takeoff_end = self.env.now

        self.landing_q_time = (landing_end - landing_start) - T_LANDING
        self.takeoff_q_time = (takeoff_end - takeoff_start) - T_TAKEOFF
        self.deicing_q_time = (deicing_end - deicing_start) - T_DEICE

class PlaneGenerator:
    def __init__(self, env, runways, deicing_trucks):
        self.env = env
        self.runways = runways
        self.deicing_trucks = deicing_trucks
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

                self.planes.append(Plane(self.env, t, delay, self.runways, self.deicing_trucks))
                hold_time = np.maximum(T_guard, T)
                yield self.env.timeout(hold_time)
            else:
                yield self.env.timeout(1)

class PlowTruck:
    def __init__(self, env, runways, deployed):
        self.env = env
        self.runways = runways
        self.deployed = deployed/3600

        env.process(self.plow())

    def plow(self):
        with runways.request(priority=0) as req:
            yield req
            yield self.env.timeout(T_PLOW)

class PlowTruckGenerator:
    def __init__(self, env, runways):
        self.env = env
        self.runways = runways
        self.trucks = []
        env.process(self.generate())
    
    def generate(self):
        while True:
            # Snows for a certain amount of time
            yield self.env.timeout(get_snow_time())

            """
                In order to close all runways after snowing, we schedule NUM_RUNWAYS amount of trucks;
                however, only NUM_PLOW_TRUCKS trucks are allowed to operate at a time in order to uphold 
                the contraints. This is achieved by increase or decrease the plowing time depending on the 
                runway-to-plowtruck ratio (NUM_RUNWAYS/NUM_PLOW_TRUCKS). E.g. if we have one plow truck and three runways, we have to 'deploy'
                three plow trucks to stop all plane traffic on the runways, but we have to increase the plowing
                time my a magnitude of 3 to simulate only one plow truck operating.  
            """
            for i in range(NUM_RUNWAYS):
                self.trucks.append(PlowTruck(env, runways, self.env.now))

            # Skies are clear for a certain amount of time
            yield self.env.timeout(get_clear_time())

if __name__ == "__main__":
    env = simpy.Environment()

    runways = simpy.PriorityResource(env, capacity=NUM_RUNWAYS)
    deicing_trucks = simpy.PriorityResource(env, capacity=NUM_DEICING_TRUCKS)
    plane_gen = PlaneGenerator(env, runways, deicing_trucks)
    plow_gen = PlowTruckGenerator(env, runways)

    env.run(until=SIM_TIME)

    means = []

    prev_hour = FIRST_PLANE
    inter_arrival = []

    plane_gen.planes.sort(key=lambda x:x.arrival_time)

    time = []

    for i in range(len(plane_gen.planes) - 1):
        calc_time = (plane_gen.planes[i+1].arrival_time+plane_gen.planes[i].arrival_time)/2/3600

        if calc_time < 24:
            time.append((plane_gen.planes[i+1].arrival_time+plane_gen.planes[i].arrival_time)/2/3600)
            inter_arrival.append([plane_gen.planes[i+1].arrival_time - plane_gen.planes[i].arrival_time])

    landing_means = take_means(plane_gen.planes, "landing")
    takeoff_means = take_means(plane_gen.planes, "takeoff")
    deicing_means = take_means(plane_gen.planes, "deicing")

    print("{} plow trucks deployed".format(len(plow_gen.trucks)))
    i = 0
    for truck in plow_gen.trucks:
        print("Truck {} deployed at hour {}".format(i, truck.deployed))
        i += 1

    plt.plot([i for i in range(len(landing_means))], landing_means, "y")
    plt.plot([i for i in range(len(takeoff_means))], takeoff_means, "r")
    plt.plot([i for i in range(len(deicing_means))], deicing_means, "b--")
    plt.legend(['Landing', 'take-off', "deicing"])
    plt.xlabel('Hour of day')
    plt.ylabel('Qeueu time (seconds)')
    plt.title('Mean landing and take-off times', fontsize=16)

    plt.show()