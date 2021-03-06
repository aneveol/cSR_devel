
import hashlib
import sys
from time import time

import numpy

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn import feature_selection

from csr import Preprocess
from csr.ML.misc import ItemSelector
from csr.Data import DataStream

class Vocabulary:
    def __init__(self,
                 f_selectors,
                 ngram_range = (1, 5)):

        section = 'title OR abstract'
        steps = [
                ('selector', ItemSelector(key = section)),
                ('vectorizer', CountVectorizer(ngram_range = ngram_range,
                                               binary = True,
                                               lowercase = True))
                ]
        i = 0
        for f_selector in f_selectors:
            i += 1
            steps.append(('feature_selection_%i' % i, f_selector))
        self.pipeline = Pipeline(steps)

    @staticmethod
    def load(filename):
        try:
            terms = open(filename).read().split('\n')
            vocabulary = Vocabulary([])
            vocabulary.terms = terms
            return vocabulary
        except IOError:
#            sys.stderr.write("Could not find vocabulary file: %s\n" % filename)
            raise IOError("Missing vocabulary file: ''" % filename)
    
    def fit_or_load(self, data, force_load = False):
        # Phased out version left for back-compatibility
        # MD5 is a poor hash function but it is enough for our purposes here
        fingerprint = hashlib.md5(data.marshall()).hexdigest()[:8].upper()

        try:
            if force_load: raise IOError() # Ugly, but less ugly than branching twice
            self.terms = open('cache/vocab_%s' % (fingerprint)).read().split('\n')
            sys.stderr.write("Loaded data with fingerprint: %s\n" % fingerprint)
        except IOError:
            sys.stderr.write("No cached vocabulary with fingerprint: %s\n" % fingerprint)
            sys.stderr.write("Constructing new vocabulary... (this can take a while)\n")
            self.pipeline.fit(data, data.label)
            terms_i = self.pipeline.named_steps['vectorizer'].get_feature_names()
            self.terms = numpy.asarray(terms_i)
            sys.stderr.write("Vocabulary reduction step 0: %i\n" % (len(self.terms)))
            i = 0
            for step in self.pipeline.steps[2:]:
                i += 1
                self.terms = self.terms[step[1].get_support()]
                sys.stderr.write("Vocabulary reduction step %i: %i\n" % (i, len(self.terms)))

            with open('cache/vocab_%s' % (fingerprint), 'w') as out:
                out.write('%s' % '\n'.join(self.terms).encode('utf8'))

    def fit(self, data):
        sys.stderr.write("Constructing vocabulary... (this can take a while)\n")
        self.pipeline.fit(data, data.label)
        terms_i = self.pipeline.named_steps['vectorizer'].get_feature_names()
        self.terms = numpy.asarray(terms_i)
        sys.stderr.write("Vocabulary reduction step 0: %i\n" % (len(self.terms)))
        i = 0
        for step in self.pipeline.steps[2:]:
            i += 1
            self.terms = self.terms[step[1].get_support()]
            sys.stderr.write("Vocabulary reduction step %i: %i\n" % (i, len(self.terms)))

    def get_terms(self):
        return self.terms
    
    '''
    def create():
        sys.stderr.write("Loading vocabulary...\n")
        t_0 = time()
        # First flush: discard all terms except those with frequency
        #              p < f < 1-p
        p = 0.00025
        f_selector_1 = feature_selection.VarianceThreshold(threshold = (p * (1 - p)))
        # Second: Select the n features with the highest mutual information
        f_method_2   = feature_selection.mutual_info_classif
        f_selector_2 = feature_selection.SelectKBest(f_method_2, k = 10000)
        vocabulary = Vocabulary(f_selectors = [f_selector_1, f_selector_2])
        vocabulary.fit(data)
        sys.stderr.write("Done in %0.2f s\n" % (time() - t_0))
        return vocabulary
    '''

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description = '''
Module for constructing and handling vocabularies for training.
When run on the commandline, constructs a vocabulary from the given input data.
''')
#    parser.add_argument('--input',  type = str, required = True)
    parser.add_argument('--data',   nargs  = '+')
#    parser.add_argument('--labels', type = str, nargs  = '+')
    parser.add_argument('--output', type = str, required = True)
    
    args = parser.parse_args()
    
    records = []
    for filename in args.data:
        records.append(DataStream.parse(open(filename).read()))
    if type(records) == DataStream:
        records = [records]
    data = DataStream(*records[0].header)
    for d in records:
        data.merge(d)
    
    Preprocess.add_placeholder_for_missing_data(data)
    Preprocess.strip_numerals(data)
    
    t_0 = time()
    # First flush: discard all terms except those with frequency
    #              p < f < 1-p
    p = 0.00025
    f_selector_1 = feature_selection.VarianceThreshold(threshold = (p * (1 - p)))
    # Second: Select the n features with the highest mutual information
    
    f_method_2   = feature_selection.mutual_info_classif
    f_selector_2 = feature_selection.SelectKBest(f_method_2, k = 10000)
    vocabulary = Vocabulary(f_selectors = [f_selector_1, f_selector_2])
    vocabulary.fit(data)
    sys.stderr.write("Done in %0.2f s\n" % (time() - t_0))
    
    with open(args.output, 'w') as out:
        out.write('%s' % '\n'.join(vocabulary.get_terms()).encode('utf8'))
