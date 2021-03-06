
import sys, random, re
import collections

from bin.Data import DataStream
from bin import Import
from bin.ML.pipeline import Tokenizer
import nltk
from nltk.corpus import stopwords
import ftfy

#included_titles = DataStream('title')
#for title in open('data/raw/Jonnalagadda/Jonnalagadda_included_titles.txt'):
#    included_titles.append([title.strip()])

Y = DataStream.parse(open('data/full/Jonnalagadda/Jonnalagadda_Y.json').read())
Y.add_column('label', 'Y')

Pubmed_in = DataStream.parse(open('data/full/Jonnalagadda/Jonnalagadda_201906_pubmed.json').read())
IEEE_in   = DataStream.parse(open('data/full/Jonnalagadda/Jonnalagadda_201906_ieee.json').read())
ACMDL_in  = DataStream.parse(open('data/full/Jonnalagadda/Jonnalagadda_201906_acmdl.json').read())

headers = ['PMID', 'doi', 'title', 'abstract', 'year', 'journal', 'label']
Pubmed = DataStream(*headers)
for row in Pubmed_in:
#    pmid = row["Identifiers"].split(':')[1]
    pmid = row["EntrezUID"]
    doi_match = re.search("doi: ([A-z0-9/\.]*[A-z0-9])", row["Details"])
    if doi_match:
        doi = doi_match.group(1)
    else:
        doi = ""
    details = row['ShortDetails'].split()
    try:
        int(details[-1])
        journal = " ".join(details[:-1])
        year = details[-1]
    except ValueError:
        journal = " ".join(details)
        year = ""
    Pubmed.append([pmid, doi, row['Title'], "", year, journal, 'N'])
IEEE = DataStream(*headers)
for row in IEEE_in:
    pmid = ""
    doi = row["DOI"]
    title = row['Document Title']
    abstract = row["Abstract"]
    year = row["Publication_Year"]
    journal = ""
    IEEE.append([pmid, doi, title, abstract, year, journal, 'N'])
ACMDL = DataStream(*headers)
for row in ACMDL_in:
    pmid = ""
    doi = row["doi"]
    title = row["title"]
    abstract = ""
    year = row["year"]
    journal = row["journal"]
    ACMDL.append([pmid, doi, title, abstract, year, journal, 'N'])

# ~~~~~~ Definitions ~~~~~~

noop_sent_tokenize = lambda x: [x]
noop               = lambda x:  x
tokenize = Tokenizer(noop_sent_tokenize, nltk.word_tokenize, noop, stopwords.words('english'))
def normalize(text):
#    print("Pre-normalization: '%s'" % text)
    n_text = text
    n_text = ftfy.fix_text(n_text)
    n_text = re.sub('[^A-z ]', '', n_text)
    n_text = " ".join(tokenize(n_text.lower()))
#    print("Post-normalization: '%s'" % n_text)
    return n_text

def make_descriptor(row):
#    return (row.year, normalize(row.title))
    return (normalize(row.title),)
#    return (row.doi,)
#    return (row.journal, row.year, row.title)
def make_descriptors(data):
    return [make_descriptor(row) for row in data]

def assert_no_duplicates(data):
    descs = make_descriptors(data)
    desc_to_ref = {}
    for desc, row in zip(descs, data):
        if not desc in desc_to_ref: desc_to_ref[desc] = []
        desc_to_ref[desc].append(row)
    duplicates = [(desc, count) for desc, count in collections.Counter(descs).items() if count > 1]
    assert duplicates == [], "%i/%i duplicates in set: \n%s" % (len(duplicates),
                                                                len(descs),
                        '\n'.join(["Count %i: " % count + '\n'.join([str((ref.journal, ref.year, ref.title)) for ref in desc_to_ref[desc]]) for desc, count in duplicates]))
    

def assert_is_subset(data_sub, data_sup):
    descs_sup = set(make_descriptors(data_sup))
    descs_sub = set(make_descriptors(data_sub))
#    sub_items_in_sup = [desc in descs_sup for desc in descs_sub]
#    is_subset = all(sub_items_in_sup)
#    missing_descs = [desc for desc in descs_sub if not desc in descs_sup]
    sub_descs_not_in_sup = descs_sub - descs_sup
    is_subset = len(sub_descs_not_in_sup) == 0
    if not is_subset:
        print("%i references from other sources:\n%s" % (
            len(sub_descs_not_in_sup),
            '\n'.join(map(str, sub_descs_not_in_sup))
        ))

def check_in_set_and_add(items, item):
    prev_len = len(items)
    items.add(item)
    return len(items) == prev_len

def seen_already(items):
    return lambda row: check_in_set_and_add(items, make_descriptor(row))

# ~~~~~~ Definitions ~~~~~~

all_data = [Y,
            Pubmed,
            IEEE,
            ACMDL
]

# ~~~~~~ Remove refs without abstracts ~~~~~~

#for X in all_data:
#    print("Current size: %i" % len(X))
#    X.delete_if(lambda row: row.abstract == "")
#    print("Current size: %i" % len(X))

# ~~~~~~ Remove duplicates ~~~~~~

prev_descs = set([])
for X in all_data:
    X.delete_if(seen_already(prev_descs))
    assert_no_duplicates(X)

# ~~~~~~ Merge Data ~~~~~~

data = Pubmed
data.merge(IEEE)
data.merge(ACMDL)
data.merge(Y)
assert_no_duplicates(data)

# ~~~~~~ Construct splits ~~~~~~

#included_descs = make_descriptors(included_titles)
data.add_column('split', '')
for d in data:
    try:
        if int(d["year"]) < 2015:
            d.split = "original"
        else:
            d.split = "update"
    except ValueError:
        pass

# ~~~~~~ Construct CV splits ~~~~~~

data.add_column('cv_split', '')
for d in data:
    d.cv_split = "%s_%i" % (d.split, random.randint(0, 9))

#print("Total data: %i" % len(data))

print(data.marshall())
