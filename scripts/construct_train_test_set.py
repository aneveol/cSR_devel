
import argparse
import numpy

from bin.Data import DataStream

parser = argparse.ArgumentParser(description = '')
parser.add_argument('--data',             required = True,
                    help = 'Input Datastream file')
parser.add_argument('--col',              required = True, type = str,
                    help = 'Column to use for splitting')
parser.add_argument('--train_out',        required = True, type = str,
                    help = 'Filepath to output training set')
parser.add_argument('--dev_out',          required = True, type = str,
                    help = 'Filepath to output development set')
#parser.add_argument('--test_out',         required = True, type = str,
#                    help = 'Filepath to output test set')
args = parser.parse_args()

data = DataStream.parse(open(args.data).read())

labels = data[args.col]
labels = numpy.unique(labels)

print("Input labels:\n%s" % '\n'.join(labels))

#ii = set(numpy.random.choice(range(len(labels)), len(labels)//2, replace=False))
#train_labels  = [l for i, l in enumerate(labels) if not i in ii]
#ii = set(numpy.random.choice(range(len(train_labels)), len(train_labels)//2, replace=False))
#dev_labels    = set([l for i, l in enumerate(train_labels) if i in ii])
#train_labels  = set([l for i, l in enumerate(train_labels) if not i in ii])

dev_labels = [
    'CD010705',
    'CD008081',
    'CD010360',
    'CD009647',
    'CD008760',
    'CD008054',
    'CD010173',
    'CD009372',
    'CD010653',
    'CD007427',
    'CD010339',
    'CD008782',
    'CD011420',
    'CD008892',
    'CD007394',
]

#print("Split train:\n%s" % '\n'.join(train_labels))
print("Split dev:\n%s" % '\n'.join(dev_labels))

train_set = DataStream(*data.header)
dev_set   = DataStream(*data.header)
test_set  = DataStream(*data.header)
for row in data:
    if row[args.col] in dev_labels:
        dev_set.append([row[x] for x in data.header])
    else:
        train_set.append([row[x] for x in data.header])

with open(args.train_out, 'w') as out:
    out.write(train_set.marshall())
with open(args.dev_out, 'w') as out:
    out.write(dev_set.marshall())
#with open(args.test_out, 'w') as out:
#    out.write(test_set.marshall())
