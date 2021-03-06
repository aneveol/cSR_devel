
import sys, random

from Data import DataStream
import Import

from itertools import cycle

records = DataStream.parse(file('data/full/EMBASE1000_U').read())
records_dict = {}
for row in records:
    records_dict[row.PMID] = row

partitions = []
for i in range(8): partitions.append([])
ii = range(1000)
random.shuffle(ii)
allocation = dict(zip(ii, cycle(range(8))))
i = 0
for line in open('log/trec_EMBASE_sorted_test'):
    d = line.strip().split()
    pmid = d[2]
    row = records_dict[pmid]
    data = [row.author, row.year, row.journal, row.title, row.abstract, '', '']
    data = ['"%s"' % v.replace('"', "'") for v in data]
    partitions[allocation[i]].append(', '.join(data).encode('utf8'))
    i += 1

for i in range(4):
    random.shuffle(partitions[i])

for i in range(8):
    with open('log/EMBASE_split_%i.csv' % (i+1), 'w') as out:
        for line in partitions[i]:
            out.write('%s\n' % line)
