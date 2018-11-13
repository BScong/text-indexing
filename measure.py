import subprocess
import json
import sys

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

batch_sizes = [1,5,10,20,50,100,200,300]
#batch_sizes = [100,200,300]
result = {}
for batch_size in batch_sizes:
    print(batch_size)
    output = subprocess.check_output("time python3 main.py ./data/pl-eval -b " + str(batch_size) + " --eval ./data/subset", stderr=subprocess.STDOUT, shell=True).decode(sys.stdout.encoding)

    out = parse_output(output)
    result[batch_size]= out
    print(out)

with open('measure_results.json', 'w') as outfile:
    json.dump(result, outfile, indent=4)
