import subprocess
import json
import sys
import os
import time

def parse_output(out):
    res = {}
    for line in out.splitlines():
        line = (" ".join(line.split())).split()
        if len(line)==2:
            m, s = line[1].split('m')
            s = s.split('s')[0]
            res[line[0]]=float(m)*60+float(s)
            #print(line[0] + ':' + line[1])
        #print('-')
    return res

batch_sizes = [1,5,10,20,50,100,200,300,500, 700, 1000]
batch_sizes = batch_sizes[::-1]
#batch_sizes = [100,200,300]
result = {}
os.system("mprof clean")
for batch_size in batch_sizes:
    print(batch_size)
    output = ''
    start = time.monotonic()
    try:
        output = subprocess.check_output("time mprof run python3 ../main.py ../data/pl-eval -b " + str(batch_size) + " --eval ../data/latimes > result_" + str(batch_size) + ".txt", stderr=subprocess.STDOUT, shell=True).decode(sys.stdout.encoding)
        out = parse_output(output)
        print(out)
    except Exception as e:
        print(e)
    duration = time.monotonic() - start
    print(duration)
    #result[batch_size]= out
    result[batch_size]= {'user':duration}


with open('measure_results.json', 'w') as outfile:
    json.dump(result, outfile, indent=4)

os.system("mprof list > mem_measures.txt")
