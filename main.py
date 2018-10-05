from os import listdir
from os.path import isfile, join

words = {}
files = [f for f in listdir('./data/subset/') if isfile(join('./data/subset/', f))]

for f in files:
    text = open('./data/subset/' + f, "r")
    n_words = 0
    for line in text:
        for w in line.split(' '):
            w = w.lower()
            n_words += 1
            if w not in words:
                words[w] = {}
            if f not in words[w]:
                words[w][f] = 0
            words[w][f] += 1
    for w in words:
        if f in words[w]:
            words[w][f] = words[w][f]/n_words

print(words['the'])
