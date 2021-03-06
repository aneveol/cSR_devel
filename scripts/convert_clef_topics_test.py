
import glob

from Data import DataStream

records = DataStream('PMID', 'label', 'source')

files = glob.glob('data/raw/clef_test/topics_test/*')

for filename in files:
    on_pmid_list = False
    source = None
    label = 'U'
    for line in file(filename):
        line = line.strip()
        if on_pmid_list:
            pmid = line
            records.append([pmid, label, source])
        else:
            if line == 'Pids:':
                on_pmid_list = True
            else:
                d = line.split()
                if d and d[0] == 'Topic:':
                    source = d[1]

print records.marshall()
