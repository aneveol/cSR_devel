
# ~~~~~~                    Import                  ~~~~~~

import itertools

import nltk

import tensorflow as tf
import numpy as np

from sklearn.base import BaseEstimator, TransformerMixin

# ~~~~~~                  Definitions               ~~~~~~

def _pad(x, n):
    ret_val = ['']*(n-len(x)) + x[:n]
    assert len(ret_val) == n
    return ret_val

def _gen(x):
    for x_i in x:
        yield x_i

class ElmoVectorizer(BaseEstimator, TransformerMixin):
    
    def __init__(self, seq_length, capacity = 16000):
        import tensorflow_hub as hub
        tf.logging.set_verbosity(tf.logging.ERROR)
        self._model      = hub.Module('https://tfhub.dev/google/elmo/2')
        tf.logging.set_verbosity(tf.logging.WARN)
        self._capacity   = capacity
        self._seq_length = seq_length
        self._n_batch    = capacity // seq_length
        
    def _embeddings_from_sentences(self, s):
        return self._model(s,
                           signature="default",
                           as_dict=True)["elmo"]
        
    def _embeddings_from_tokens(self, s):
        return self._model(inputs = {
                             "tokens": s,
                             "sequence_len": list(map(len, s))
                           },
                           signature="tokens",
                           as_dict=True)["elmo"]

    def _run_in_session(self, func, x):
#        x = map(lambda x_i: _pad(x_i, self._seq_length), x)
        tf.logging.set_verbosity(tf.logging.ERROR)
        xs = []
        with tf.Session() as sess:
            sess.run([tf.global_variables_initializer(), tf.tables_initializer()])
            g = _gen(x)
            x_i = list(itertools.islice(g, self._n_batch))
            while x_i:
                xs.append(sess.run(func(x_i)))
                x_i = list(itertools.islice(g, self._n_batch))
        tf.logging.set_verbosity(tf.logging.WARN)
        return np.vstack(xs)
            
    def from_tokens(self, x):
        return self._run_in_session(self._embeddings_from_tokens, x)
            
    def from_sentences(self, x):
        return self._run_in_session(self._embeddings_from_sentences, x)

    def transform(self, X, y = None, **fit_params):
        X = map(nltk.word_tokenize, X)
        X = map(lambda x: _pad(x, self._seq_length), X)
        return self.from_tokens(X)
    def fit_transform(self, X, y = None, **fit_params):
        self.fit(X, y, **fit_params)
        return self.transform(X)
    def fit(self, X, y, **fit_params):
        return self
                                    
