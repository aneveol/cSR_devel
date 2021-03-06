
from Data import DataStream

records = DataStream('PMID', 'label', 'source')

for line in file('epc-ir.clean.tsv'):
    line = line.strip()
    d = line.split('\t')
    if d[4].strip() == 'I':
        label = 'Y'
    elif d[3].strip() == 'I':
        label = 'M'
    else: label = 'N'
    source = d[0]
    pmid = d[2]
    records.append([pmid, label, source])

print records.marshall()
