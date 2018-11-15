import json
import pandas as pd
import matplotlib.pyplot as plt

time = pd.Series()
mem = pd.Series()
keys = []
directory = './measures_1_clean/'
with open(directory + 'measure_results.json') as f:
    data = json.load(f)
    for key in data:
        time.at[int(key)] = float(data[key]['user'])
        keys.append(int(key))
print(time)
plt.scatter(time.index, time, marker='+')
plt.plot(time.index, time)
plt.xlabel('Batch size')
plt.ylabel('Running time (in seconds)')
plt.suptitle('Time', fontsize=16)
plt.title('Running time depending on batch size')
plt.show()

with open(directory + 'mem_measures.txt') as mem_measures:
    data = mem_measures
    for line in data:
        id, file, time, date = line.split()
        with open(directory+file) as f:
            mem_data = f
            maxi = 0.0
            for measure in mem_data:
                measure_data = measure.split()
                if len(measure_data)==3:
                    a, value, t = measure_data
                    maxi = max(float(value), maxi)
        mem.at[keys[int(id)]] = float(maxi)
mem = mem.sort_index()
print(mem)
plt.scatter(mem.index, mem, marker='+')
plt.plot(mem.index, mem)
plt.suptitle('Memory', fontsize=16)
plt.xlabel('Batch size')
plt.ylabel('Memory used (in MiB)')
plt.title('Memory consumption depending on batch size')
plt.show()
