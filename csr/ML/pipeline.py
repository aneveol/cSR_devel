
# ~~~~~~                    Import                  ~~~~~~

from future.utils import iteritems

import re
import string
import sys

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.pipeline import Pipeline, FeatureUnion, make_pipeline
from sklearn import preprocessing

from gensim.models.keyedvectors import KeyedVectors

import numpy

import nltk
from nltk.corpus import stopwords
try: nltk.data.find('corpora/stopwords')
except LookupError: nltk.download('stopwords')

from csr.Log import start_statusbar

# ~~~~~~                    Setup                   ~~~~~~

default_stemmer = nltk.stem.porter.PorterStemmer()

STATUS = start_statusbar(sys.stderr)

# ~~~~~~                  Definitions               ~~~~~~

# Identity transformer, does nothing
# To be used where we assume that a transformer will be used but
# we want to skip the step for some reason, for instance because
# we want to check the baseline performance, or because the step
# (feature selection for instance) is not necessary for our data
class IdentityTransformer(BaseEstimator, TransformerMixin):
#    def __init__(self): pass
    def fit(self, x, y = None): return self
    def transform(self, data): return data

class TypecastTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, target_type): self.target_type = target_type
    def fit(self, x, y = None): return self
    def transform(self, data): return data.astype(self.target_type)

# Dense transformer
class DenseTransformer(BaseEstimator, TransformerMixin):
    def transform(self, X, y = None, **fit_params):
        return X.todense()
    def fit_transform(self, X, y = None, **fit_params):
        self.fit(X, y, **fit_params)
        return self.transform(X)
    def fit(self, X, y, **fit_params):
        return self

# Sparse transformer
class SparseTransformer(BaseEstimator, TransformerMixin):
    def transform(self, X, y = None, **fit_params):
        return X.tosparse()
    def fit_transform(self, X, y = None, **fit_params):
        self.fit(X, y, **fit_params)
        return self.transform(X)
    def fit(self, X, y, **fit_params):
        return self

# Text to word index transformer
class WordSequencer(BaseEstimator, TransformerMixin):
    def __init__(self, max_seq_length, embeddings):
        assert embeddings == None
        from keras.preprocessing.text import Tokenizer

        self.max_seq_length = max_seq_length
        self.tokenizer = Tokenizer(num_words = max_seq_length)
        
    def transform(self, X, y = None, **fit_params):
        from keras.preprocessing.sequence import pad_sequences
        sequences = self.tokenizer.texts_to_sequences(X)
        sequences = pad_sequences(sequences, self.max_seq_length)
        print(sequences)
        return sequences
    def fit_transform(self, X, y = None, **fit_params):
        self.fit(X, y, **fit_params)
        return self.transform(X)
    def fit(self, X, y, **fit_params):
        self.tokenizer.fit_on_texts(X)
        return self

# Text to word index transformer
class Word2Vec_WordSequencer(BaseEstimator, TransformerMixin):
    def __init__(self, max_seq_length = 100, embeddings = None, emb_size = None):
        
        self.embedding_vectors = KeyedVectors.load_word2vec_format(embeddings,
#                                                                   binary = True,
#                                                                   unicode_errors='ignore',
                                                                   limit = emb_size)
        self.max_seq_length = max_seq_length
        self.embeddings     = embeddings
        self.emb_size       = emb_size
        #        from keras.preprocessing.text import Tokenizer
        
        #        self.max_seq_length = max_seq_length
        #        self.tokenizer = Tokenizer(num_words = max_seq_length)
            
    def transform(self, X, y = None, **fit_params):
        from keras.preprocessing.sequence import pad_sequences
        ret_val = []
#        STATUS[5]('WordSequencer received input of size %i' % len(X))
        oov_n   = 0
        total_n = 0
        for x in X:
            res = []
            i = 0
            for token in nltk.word_tokenize(x):
                i += 1
                if i > self.max_seq_length: break
                if token in self.embedding_vectors.vocab:
                    index = self.embedding_vectors.vocab[token].index
                    vec = self.embedding_vectors.get_vector(token)
#                    STATUS[10]("Transforming token '%s' -> '%i' -> (%s, ...)" % (token,
#                                                                                 index,
#                                                         ', '.join([str(v) for v in vec[:3]])))
                else:
                    index = -1 # Use the least frequent word for OOV terms
                    oov_n += 1
                    STATUS[10]("OOV term: '%s' using token '%s'" % (token,
                                                        self.embedding_vectors.index2word[0]))
                total_n += 1
                res.append(index)
            ret_val.append(res)
        STATUS[5]('OOV vectors: %i / %i (%.1f%%)' % (oov_n, total_n, 100.0*(oov_n/total_n)))
#        STATUS[5]('Vectors of len (%i, %i)' % (min(map(len, ret_val)), max(map(len, ret_val))))
        ret_val = pad_sequences(ret_val, self.max_seq_length)
#        STATUS[5]('Vectors of len (%i, %i)' % (min(map(len, ret_val)), max(map(len, ret_val))))
        ret_val = numpy.array(ret_val)
#        STATUS[5]('WordSequencer output size %s' % (str(ret_val.shape)))
        return ret_val
#        return numpy.transpose(ret_val)
        '''
        sequence_input = keras_layers.Input(shape = (seq_length,), dtype = 'int32')
        embedding_layer = self.embedding_vectors.get_keras_embedding(train_embeddings = False)
        x = embedding_layer(sequence_input)
        self._model = keras_models.Model(sequence_input, x)
        self._model.compile(loss = 'hinge',
                            optimizer = 'rmsprop')
        '''
    def fit_transform(self, X, y = None, **fit_params):
        self.fit(X, y, **fit_params)
        return self.transform(X)
    def fit(self, X, y, **fit_params):
        return self
    
#def stem_tokens(tokens, stemmer):
#    stemmed = []
#    for item in tokens:
#        stemmed.append(stemmer.stem(item))
#    return stemmed

class Tokenizer:
    
    def __init__(self, sent_tokenize, word_tokenize, stem, stop_words):
        self.sent_tokenize = sent_tokenize
        self.word_tokenize = word_tokenize
        self.stem          = stem
        # Note: stop_words should be STEMMED forms
        self.stop_words    = frozenset(stop_words)
    
    def __call__(self, text):
        tokens = [word for sent in self.sent_tokenize(text) for word in self.word_tokenize(sent)]
        # In order for sklearn not to issue stupid consistency warnings
        # (stemmed) stop words must be invariant under tokenization,
        # which generally implies that the tokenizer must know the stop
        # words and treat them differently, which means the consistenty
        # cannot tell if the stop words are stemmed or not to begin with
#        STATUS[10]("Pre-tokenization: '%s'" % text)
        tokens = [self.stem(token) for token in tokens if self.stem(token) not in self.stop_words]
#        STATUS[10]("Post-tokenization: '%s'" % " ".join(tokens))
        return tokens

def tokenize_DEPR(text):
#    text = "".join([ch for ch in text if ch not in string.punctuation])
#    tokens = nltk.word_tokenize(sent)
    tokens = [word for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
#    stems = stem_tokens(tokens, stemmer)
    return [default_stemmer.stem(token) for token in tokens]

def csv_tokenizer(s):
    return s.split('; ')

def csv_ngram_analyzer(s):
    for value in s.split('; '):
        tokens = re.findall(r'\w{2,}', value.lower())
        # Come up with a better way to do this
        for unigram in tokens:
            yield '%s' % unigram
        for bigram in zip(tokens, tokens[1:]):
            yield '%s %s' % bigram
        for trigram in zip(tokens, tokens[1:], tokens[2:]):
            yield '%s %s %s' % trigram



# Selection transformer
# Takes dict-like objects and extracts the value for the specified
# key
# TODO make this work for list-like objects too (using indices)
# TODO change the constructor to (optionally) take lists of keys
class ItemSelector(BaseEstimator, TransformerMixin):
    def __init__(self, key):
        self.key = key
        self.keys = key.split(' OR ')
    def fit(self, x, y = None): return self
    def transform(self, data):
        # Given data of length n, construct keys x n size table
        blocks = [data[key] for key in self.keys]
        # Merge column by column, resulting in a 1 x n size vector
        return ['\n'.join(block) for block in zip(*blocks)]

class QueryFeatureBuilder:
    def __init__(self):
        self.foo = False

class FeatureBuilder:
    def __init__(self, data = None, vocabulary = None, sparse = False):
        self.vocabulary = vocabulary
        self.data       = data
        self.sparse     = sparse

    def emb_sequence(self, field, **args):
        default_args = {
            'embeddings': 'ELMo',
            'throughput': 16000,
            'seq_length': 40
            }
        default_args.update(args)
        args = default_args
        arg_desc = ','.join(['%s=%s' % (key, val) for key, val in iteritems(args) if val])
        pipeline = []
        pipeline.append(('selector', ItemSelector(key = field)))
        if args['embeddings'].lower() == 'elmo':
            from csr.ML.embeddings import ElmoVectorizer
            pipeline.append(('embedding', ElmoVectorizer(seq_length = args['seq_length'],
                                                         capacity = args['throughput']
            )))
        else:
            raise ArgumentError('Unknown embedding type: %s' % args['embeddings'])

        pipeline = Pipeline(pipeline)
        def _get_feature_names(self):
            return self.named_steps['embedding'].get_feature_names()
        pipeline.get_feature_names = _get_feature_names.__get__(pipeline)
        return ('%s[%s]' % (field, arg_desc), pipeline)
    
    def word_sequence(self, field, **args):
        default_args = {
            'embeddings': None
            }
        default_args.update(args)
        args = default_args
        arg_desc = ','.join(['%s=%s' % (key, val) for key, val in iteritems(args) if val])
        pipeline = []
        pipeline.append(('selector', ItemSelector(key = field)))
        if args['embeddings']:
            pipeline.append(('tokenizer', Word2Vec_WordSequencer(**args)))
        else:
            pipeline.append(('tokenizer', WordSequencer(**args)))

        pipeline = Pipeline(pipeline)
        def _get_feature_names(self):
            return self.named_steps['tokenizer'].get_feature_names()
        pipeline.get_feature_names = _get_feature_names.__get__(pipeline)
        return ('%s[%s]' % (field, arg_desc), pipeline)
        
    def text(self, field, **args):
        default_args = {
            'ngram_max': 5,
            'stop_words': None,
            'binary': False,
            'stem': False,
            'lowercase': False,
            'tfidf': False,
            'theta': 0,
            'normalize': True,
            'analyzer': 'word'
            }

        default_args.update(args)
        args = default_args
        arg_desc = ','.join(['%s=%s' % (key, val) for key, val in iteritems(args) if val])

        noop = lambda x: x
        stem = args['stem'] and default_stemmer.stem or noop
        tokenizer = Tokenizer(nltk.sent_tokenize, nltk.word_tokenize, stem, [])
        
        if args['stop_words']:
            try:
                processed_stop_words = stopwords.words(args['stop_words'])
            except OSError: # Yes, NLTK seriously throws OSError for unknown languages...
                processed_stop_words = frozenset(args['stop_words'])
        else:
            processed_stop_words = []
        if args['stem'] and processed_stop_words:
            processed_stop_words = tokenizer(' '.join(processed_stop_words))
#            from pprint import pprint
#            pprint(sorted(processed_stop_words))
            
        tokenizer = Tokenizer(nltk.sent_tokenize, nltk.word_tokenize, stem, processed_stop_words)
            
        pipeline = []
        pipeline.append(('selector', ItemSelector(key = field)))
        pipeline.append(('vectorizer', CountVectorizer(ngram_range = (1, args['ngram_max']),
                                                       tokenizer   = tokenizer,
#                                                       stop_words  = processed_stop_words,
                                                       vocabulary  = self.vocabulary,
                                                       analyzer    = args['analyzer']
                                                       )))
        if args['tfidf']:
            pipeline.append(('tf-idf', TfidfTransformer()))
        if args['theta'] > 0:
            pipeline.append(('f_selector', feature_selection.VarianceThreshold(threshold = args['theta'])))
        if not self.sparse:
            pipeline.append(('densify', DenseTransformer()))
        pipeline.append(('typecast<float>', TypecastTransformer('float_')))
        if args['normalize']:
            if self.sparse:
                # RobustScaler can apparently only be fitted on dense matrices at present
                # see: https://github.com/scikit-learn/scikit-learn/issues/8796
                # and: https://github.com/scikit-learn/scikit-learn/pull/4125#r30829145
                
#            pipeline.append(('scaling', preprocessing.RobustScaler(with_centering = False)))
                # TODO: switch to RobustScaler if/when the issue gets resolved
#            pipeline.append(('scaling', preprocessing.StandardScaler(with_mean = False)))
                pipeline.append(('scaling', preprocessing.Normalizer()))
            else:
                pipeline.append(('scaling', preprocessing.RobustScaler()))
        
        pipeline = Pipeline(pipeline)
        def _get_feature_names(self):
            return self.named_steps['vectorizer'].get_feature_names()
        pipeline.get_feature_names = _get_feature_names.__get__(pipeline)
        return ('%s[%s]' % (field, arg_desc), pipeline)

    def csv(self, field, *args):
        default_args = {
            'theta': 0,
            'normalize': True
            }
        default_args.update(args)
        args = default_args
        arg_desc = ','.join(['%s=%s' % (key, val) for key, val in iteritems(args) if val])
        pipeline = []
        pipeline.append(('selector', ItemSelector(key = field)))
        pipeline.append(('vectorizer', CountVectorizer(analyzer = csv_ngram_analyzer,
                                                       binary = True)))
        if args['theta'] > 0:
            pipeline.append(('f_selector', feature_selection.VarianceThreshold(threshold = args['theta'])))
        if not self.sparse:
            pipeline.append(('densify', DenseTransformer()))
        pipeline.append(('typecast<float>', TypecastTransformer('float_')))
        if args['normalize']:
            if self.sparse:
                pipeline.append(('scaling', preprocessing.Normalizer()))
            else:
                pipeline.append(('scaling', preprocessing.RobustScaler()))
        
        pipeline = Pipeline(pipeline)
        def _get_feature_names(self):
            return self.named_steps['vectorizer'].get_feature_names()
        pipeline.get_feature_names = _get_feature_names.__get__(pipeline)
        return ('%s[%s]' % (field, arg_desc), pipeline)

