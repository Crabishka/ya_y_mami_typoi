import json

import matplotlib

from utility import calculate_critical_times, ActivityListSampler, ActivityListDecoder
import matplotlib.pyplot as plt

matplotlib.use('TkAgg')

# SLK - по возрастанию общего резерва
# MIS - по убыванию числа прямых последователей;
# ROT - по убыванию суммы отношений затрат неисчерпаемых ресурсов каждого вида к его запасам, делённой на продолжительность работы

with open('data.json', 'r') as f:
    data = json.load(f)

activities = data['activities']
predecessors = [activity['predecessors'] for activity in activities]
modes = [activity['modes'] for activity in activities]

durations = []
renewable_demands = []
renewable_capacities = [15, 17]


def SFM(modes):
    min_mode = min(modes, key=lambda mode: mode['duration'])
    return min_mode


def LNRD(modes):
    min_mode = min(modes, key=lambda mode: sum(mode['nonrenewable_demand']))
    return min_mode


def lrp_ratio(mode):
    ratios = []
    for demand, capacity in zip(mode['renewable_demand'], renewable_capacities):
        if capacity > 0:
            ratios.append(demand / capacity)
        else:
            ratios.append(float('inf'))
    return max(ratios)


def LRP(modes):
    min_mode = min(modes, key=lrp_ratio)
    return min_mode


def SLK(activity_index):
    return latest_finish[activity_index] - earliest_start[activity_index] - durations[activity_index]


def MIS(activity_index):
    activity = activities[activity_index]
    result = len(activity['predecessors'])
    return result


def ROT(activity_index):
    activity = activities[activity_index]
    mode = activity['modes'][0]
    duration = mode['duration']
    if duration > 0:
        first = mode['renewable_demand'][0] / renewable_capacities[0]
        second = mode['renewable_demand'][1] / renewable_capacities[1]
        return (first + second) / int(mode['duration'])
    else:
        return 0


def RND():
    return ':)'


for heuristic in [SFM, LNRD, LRP]:
    for poryadok in [SLK, MIS, ROT, RND]:
        durations = []
        renewable_demands = []
        for activity in activities:
            modes = activity['modes']
            durations.append(heuristic(modes)['duration'])
            renewable_demands.append(heuristic(modes)['renewable_demand'])
        earliest_start, latest_finish = calculate_critical_times(durations, predecessors)
        sampler = ActivityListSampler(predecessors)
        decoder = ActivityListDecoder()
        heuristic_activity_list = []
        if poryadok is RND:
            heuristic_activity_list = sampler.generate_random()
        else:
            heuristic_activity_list = sampler.generate_by_min_rule(lambda j: poryadok(j))
        start_times = decoder.decode(heuristic_activity_list, durations, predecessors, renewable_demands,
                                         renewable_capacities)
        title = heuristic.__name__ + ' ' + poryadok.__name__
        fig, gnt = plt.subplots()
        gnt.set_xlim(0, max(start_times) + max(durations) + 5)
        for i, (start_times2, duration) in enumerate(zip(start_times, durations)):
                gnt.broken_barh([(start_times2, duration)], (i - 0.4, 0.8), facecolor='blue')
        plt.title(title)
        plt.xlabel('Время')
        plt.ylabel('Задачи')
        matplotlib.pyplot.savefig('Gant ' + title)
