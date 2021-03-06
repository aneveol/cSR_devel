
import argparse
import pickle
import os
import sys
import traceback
import yaml

from sklearn import svm, linear_model, tree, ensemble, naive_bayes
from sklearn import decomposition
from sklearn import feature_selection, preprocessing
from sklearn.pipeline import Pipeline, FeatureUnion, make_pipeline

# TODO: the extras should probably be lazy-loaded
# There appears to be a versioning problem with Sofia ML?
#from pysofia.compat import RankSVM as SofiaSVM

from csr import Data
from csr.Data import DataStream
from csr.misc import ObjectBuilder, Prototype
from csr import Preprocess
from csr.Vocabulary import Vocabulary
from csr.ML.pipeline import FeatureBuilder, IdentityTransformer
from csr.ML.extra.Waterloo import TREC_BMI_Transformer
from csr.ML.models import DeepNetwork
from csr.ML.Train import Trainer, StaticModel, Runner, ActiveLearner, Split, TrainingSplit, SharedDataView
from csr.ML.LearnToRank import Pairwise
from csr.ML.Train import create_crossvalidation_splits, undersample
from csr.ML import meta
from csr.ML.meta import MetaClassifier
from csr import Log

# Shut up keras 'using XX backend'
#stderr = sys.stderr
#sys.stderr = open(os.devnull, 'w')
from keras import backend as keras_backend
from keras import layers as keras_layers
from keras import models as keras_models
import keras.regularizers
#sys.stderr = stderr

import numpy

STATUS = Log.start_statusbar(sys.stderr)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description = '')
    # ~~~~~~ Basic Arguments ~~~~~~
    parser.add_argument('--data',             nargs  = '+', required = True,
                        help = 'Input files in DataStream format')
    parser.add_argument('--verbosity',        type = int, default = 0)
    parser.add_argument('--vocabulary',       type = str, default = None)
    parser.add_argument('--metrics',          nargs = '*', type = str, default = ['AUC'],
                        help = "Metric to use for diagnostic output. Integer k values denote score at rank k, floating k values denote score at confidence k. {AUC, AP, DCG@k, NDCG@k, P@k, R@k, F@k}")
    parser.add_argument('--output',           type = str,
                        help = 'Filepath to output to')
    parser.add_argument('--output_format',    type = str,
                        help = 'Data output format (TREC, DataStream)')
    parser.add_argument('--marshall',         type = str,
                        help = 'Filepath to marshall model to')
    parser.add_argument('--output_RF_data',   type = str,
                        help = 'Filepath to marshall relevance feedback data')

    # ~~~~~~ Training Mode ~~~~~~
    parser.add_argument('--mode',             type = str, default = "Y|MN")
    parser.add_argument('--translate_label',  nargs = '+', type = str, default = None)
    parser.add_argument('--RF_mode',          type = str, default = 'none')
    parser.add_argument('--sparse',           action = 'store_true')
    # ~~~~~~ Model specifications ~~~~~~
    parser.add_argument('--pipeline',         required = True,
                        help = 'Pipeline parameters encoded in YAML')
    parser.add_argument('--classifier',       required = True,
                        help = 'Classifier parameters encoded in YAML')
    parser.add_argument('--meta_classifier',  required = False,
                        help = "Classifier parameters encoded in YAML for meta-classification. Only has an effect if 'RF_mode' is set")
    parser.add_argument('--pickled_meta_classifier',  required = False,
                        help = "Classifier binary file. Only has an effect if 'RF_mode' is set")
    parser.add_argument('--static_models',    nargs = '*', required = False,
                        help = 'Pickled static model files to be used as helpers in meta-training')
    # ~~~~~~ Training Partitioning ~~~~~~
    parser.add_argument('--train_on',         nargs = '+', type = str, default = None,
                        help = 'Partition to use for training. This data will always be added to the training, even if cross-validation is used.')
    parser.add_argument('--cv_train_on',      nargs = '+', type = str, default = None,
                        help = 'Train set to use for cross-validation. If not set will default to the same as the test partition')
    parser.add_argument('--test_on',          nargs = '+', type = str, default = None,
                        help = 'Partition to use for testing')
    parser.add_argument('--cv_column',        type = str, default = None,
                        help = "Use the specified column for splitting the testing partition into cross-validation folds. Held-out folds in the cv train set will be added to the training partition. Held-in folds in the test set will used for testing.")
    parser.add_argument('--cv_n_folds',       type = int, default = None,
                        help = 'Number of folds to use for cross validation. Requires --train_on and --test_on to be the same')
    parser.add_argument('--test_postprocessing', nargs = '+',
                        help = 'Postprocessing to apply to the test set before training. Uses the same syntax as the set operation in the Data class.')
    parser.add_argument('--undersample_data', type = int, nargs = 2, default = [-1, -1],
                        help = 'The number of samples per class to read from the input data. If not set will use all data')
    parser.add_argument('--undersample_train',type = int, nargs = 2, default = [-1, -1],
                        help = 'The number of samples per class to use during training. If not set will use all data')
    parser.add_argument('--n_repetitions',    type = int, default = 1,
                        help = 'If set > 1, statistics will be averaged over multiple trials')
    
    args = parser.parse_args()
    
    Log.StatusBar.threshold = args.verbosity
    
    if args.undersample_data == [-1, -1]:
        undersample_data = None
    else:
        undersample_data = args.undersample_data
    if args.undersample_train == [-1, -1]:
        undersample_train = None
    else:
        undersample_train = args.undersample_train
    
    STATUS.status("Loading data...")
    
    records = []
    for filename in args.data:
        records.append(DataStream.parse(open(filename).read()))
    if type(records) == DataStream:
        records = [records]
    data = DataStream(*records[0].header)
    for d in records:
        data.merge(d)
    
    STATUS.status("Preprocessing data...")
    
    Preprocess.add_placeholder_for_missing_data(data)
    Preprocess.strip_numerals(data)
    Preprocess.clean_text(data)
    
    if args.vocabulary:
        # ~~~~~~ Use vocabulary ~~~~~~
        STATUS[10].status("Loading vocabulary...")
        vocabulary = Vocabulary.load(args.vocabulary)
    else:
        # ~~~~~~  No vocabulary ~~~~~~
        # Use the entire set of n-grams for training
        # This is extremely slow for standard methods,
        # but is useful with e.g. SGD optimization
        vocabulary = None
    
    STATUS.status("Translating labels...")
    if args.translate_label:
        for translation in args.translate_label:
            k_v = translation.split('=')
            if len(k_v) != 2:
                raise ValueError("Error parsing translation condition '%s'" % translation)
            label, gold_label = k_v
            for row in data:
                if row.label == label: row.label = gold_label
    
    STATUS.status("Undersampling input data...")
    if undersample_data:
        pos_indices = list(numpy.where(numpy.array(data.label) == 'Y')[0])
        neg_indices = list(numpy.where(numpy.array(data.label) != 'Y')[0])
        numpy.random.shuffle(pos_indices)
        numpy.random.shuffle(neg_indices)
        min_n = min(len(pos_indices), len(neg_indices))
        min_n = min(min_n, undersample_data[1])
        min_n = max(min_n, undersample_data[0])
        indices = pos_indices[:min_n] + neg_indices[:min_n]
        data = data[indices]
    
    STATUS.status("Partitioning data...")
    if args.train_on:
        train_condition = Data.parse_conditions(args.train_on)
        ind_train       = data.select_indices(train_condition)
        if len(ind_train) == 0:
            raise ValueError('Train set condition matched no rows in data')
    else:
        # Unspecified train set -- default to none
#        ind_train = range(len(data))
        ind_train = []
    
    if args.test_on:
        test_condition  = Data.parse_conditions(args.test_on)
        ind_test        = data.select_indices(test_condition)
        if len(ind_test) == 0:
            raise ValueError('Test set condition matched no rows in data')
    else:
        # Unspecified test set -- default to everything
        ind_test = range(len(data))
    
    if args.cv_train_on:
        cv_train_condition = Data.parse_conditions(args.cv_train_on)
        ind_cv_train       = data.select_indices(cv_train_condition)
        if len(ind_cv_train) == 0:
            raise ValueError('CV Train set condition matched no rows in data')
    else:
        # Unspecified cv train set -- default to test set
        ind_cv_train = ind_test[:]
    
    if set(ind_train) == set(ind_test):
        if not (args.cv_n_folds or args.cv_column):
            raise ValueError('Train and test sets are identical, but cross validation is not set')
    elif len(set(ind_train).intersection(set(ind_test))) > 0:
        if not (args.cv_n_folds or args.cv_column):
            raise ValueError('Train and test sets overlap, and cross validation is not set')
    # At this point we either have identical train and test sets
    # with CV, or no CV with non-overlapping sets
    
    STATUS.status("Postprocess data...")
    if args.test_postprocessing:
        for cmd in args.test_postprocessing:
            tokens = cmd.split('=')
            if len(tokens) != 2:
                raise ValueError("Expression is not an assignment: %s" % cmd)
            col = tokens[0].strip()
            value = tokens[1].strip()
            if not data.has_column(col): data.add_column(col)
            for i in ind_test:
                data[i][col] = value
    
    # ~~~~~~ Pipeline and classifier builder ~~~~~~
    # Note that the pipelines must not contain lambdas, or they
    # wont be pickleable
    # ~~~~~~ Pseudo classes ~~~~~~
#    def select_from_model(func):
#        return lambda **args: feature_selection.SelectFromModel(func(**args))
    class SelectFromModelDecorator:
        def __init__(self, classifier_type):
            self.classifier_type = classifier_type
        def __call__(self, *args, **kv_args):
            return feature_selection.SelectFromModel(self.classifier_type(*args, **kv_args))
    class SelectKFeaturesDecorator:
        def __init__(self, classifier_type):
            self.classifier_type = classifier_type
        def __call__(self, *args, **kv_args):
            return feature_selection.SelectKBest(self.classifier_type, *args, **kv_args)
    def make_feature_union(*l):
        return FeatureUnion(list(l))
    class TransformerTupleDecorator:
        # Equivalent to "lambda *args: (name, transformer_type(*args))"
        # but pickleable
        def __init__(self, name, transformer_type):
            self.name             = name
            self.transformer_type = transformer_type
        def __call__(self, *args, **kv_args):
            return (self.name, self.transformer_type(*args, **kv_args))
    # ~~~~~~ Translations from definition names to class names ~~~~~~
    feature = FeatureBuilder(data = data, vocabulary = vocabulary, sparse = args.sparse)
    type_defs = {
        
        # Structure
        'Identity': IdentityTransformer,
        'Sequence': make_pipeline,
        'Parallel': make_feature_union,
        'Network':  DeepNetwork,
        
        # Replication of previous literature
        # The feature extraction script used by Waterloo
        # for their baseline model implementation in TREC
        # Total Recall, and in their CLEF participation
#        'TREC_BMI_features': lambda *args: ("TREC_BMI", TREC_BMI_Transformer(*args)),
        'TREC_BMI_features': TransformerTupleDecorator("TREC_BMI", TREC_BMI_Transformer),
        
        # Standard feature extraction factories
        'Text':         feature.text,
        'n-gram':       feature.text,
        'CSV':          feature.csv,
        'WordSequence': feature.word_sequence,
        'EmbSequence':  feature.emb_sequence,

        # Metaclassifiers
        'Pairwise':           Pairwise,
        # Sklearn
        # Classifiers
        'SVM':                svm.SVC,
        'SGD':                linear_model.SGDClassifier,
        'LogisticRegression': linear_model.LogisticRegression,
        'PassiveAggressive':  linear_model.PassiveAggressiveClassifier,
        # Feature selectors
#        'LinearSVC':          select_from_model(svm.LinearSVC),
        'LinearSVC':          SelectFromModelDecorator(svm.LinearSVC),
        'SelectByChi2':       SelectKFeaturesDecorator(feature_selection.chi2),
        'SelectByMI':         SelectKFeaturesDecorator(feature_selection.mutual_info_classif),
        'VarianceThreshold':  feature_selection.VarianceThreshold,
        # Postprocessing
        'PCA':                decomposition.PCA,
        'TruncatedSVD':       decomposition.TruncatedSVD,
        "Normalizer":         preprocessing.Normalizer,
        "RobustScaler":       preprocessing.RobustScaler,
        
        # Extra
        # Sofia ML classifiers
#        'SofiaSVM':           SofiaSVM,
        
        # Deep learning primitives
        'LSTM':            keras_layers.LSTM,
        'Bidirectional':   keras_layers.Bidirectional,
        'TimeDistributed': keras_layers.TimeDistributed,
        'Dropout':         keras_layers.Dropout,
        'Dense':           keras_layers.Dense,
        'Conv1D':          keras_layers.Conv1D,
        'MaxPooling1D':    keras_layers.MaxPooling1D,
        'Flatten':         keras_layers.Flatten,
        # Deep learning misc
        'L1_Regularizer':  keras.regularizers.l1,
        'L2_Regularizer':  keras.regularizers.l2
    }
    builder = ObjectBuilder(type_defs)
    
    STATUS.status("Reading model definitions...")
    with open(args.pipeline, 'r') as pipeline_file:
        pipeline_def = yaml.load(pipeline_file, Loader=yaml.FullLoader)
        pipeline = Prototype(builder.parse)(pipeline_def)
    with open(args.classifier, 'r') as classifier_file:
        classifier_def = yaml.load(classifier_file, Loader=yaml.FullLoader)
        classifier = Prototype(builder.parse)(classifier_def)

    STATUS.status("Loading static models...")
    static_models = []
    if args.static_models:
        for model_filename in args.static_models:
            with open(model_filename, 'rb') as model_file:
                loaded_model = pickle.load(model_file)
                assert len(loaded_model) == 2
                STATUS[7]("Loading static model from file: %s" % model_filename)
                static_models.append(StaticModel(pipeline   = loaded_model[0],
                                                 classifier = loaded_model[1]))
                STATUS[7]("Done")
        
    if args.meta_classifier:
        STATUS.status("Loading meta-classifier...")
        with open(args.meta_classifier, 'r') as classifier_file:
#            meta_classifier = pickle.load(classifier_file)
            classifier_def = yaml.load(classifier_file)
            meta_classifier = Prototype(builder.parse)(classifier_def)
    else:
        meta_classifier = None
    if args.pickled_meta_classifier:
        STATUS.status("Loading pickled meta-classifier...")
        with open(args.pickled_meta_classifier, 'rb') as classifier_file:
            meta_classifier = pickle.load(classifier_file)
            meta_classifier = MetaClassifier(meta_classifier,
                                             data,
                                             data.label,
                                             static_models,
                                             [], [])

    STATUS.status("Creating data model...")
    shared_data_view = SharedDataView(pipeline, data)
    STATUS.status("Creating trainer...")
    trainer = Prototype(Trainer)(shared_data_view,
                                 data.label,
                                 classifier,
                                 mode = args.mode,
                                 undersample_range = undersample_train)
    
    if args.cv_n_folds or args.cv_column:
        
        STATUS.status("Constructing CV splits...")
        if args.cv_column:
            ind_train_set = set(ind_train)
            ind_cv_train_set = set(ind_cv_train)
            ind_test_set = set(ind_test)
            splits = []
            entries = numpy.array(data[args.cv_column])
            labels  = numpy.array(data.label)
            unique_entries = numpy.unique(entries[ind_cv_train])
            if args.cv_n_folds: num_splits = args.cv_n_folds
            else:               num_splits = len(unique_entries)
            # We could one-line this loop with groupby, but it gets messy
            groups = []
            i = 0
            for entry in unique_entries:
                if len(groups) <= i: groups.append([])
                groups[i].append(entry)
                i = (i + 1) % num_splits
            for i, group in enumerate(groups):
                if len(group) == 1:
                    value_desc = group[0]
                else:
                    value_desc = 'split %i' % (i+1)
                if len(value_desc) > 10: value_desc = value_desc[:9] + '.'

                # Calculate hold-in and hold-out for test set on this fold
                ind_test_hold_out = numpy.where(numpy.isin(entries, group))[0]
                ind_test_hold_out = [ind for ind in ind_test_hold_out if ind in ind_test_set]
                
                ind_cv_train_hold_in = numpy.where(numpy.isin(entries, group, invert = True))[0]
                ind_cv_train_hold_in = [ind for ind in ind_cv_train_hold_in if ind in ind_cv_train_set]

                ind_train_fold = list(ind_train_set.union(set(ind_cv_train_hold_in)))
                ind_test_fold = ind_test_hold_out
                    
                # Check that we have at least one of each label
                train_labels = numpy.unique(labels[ind_train_fold])
                test_labels  = numpy.unique(labels[ind_test_fold])
                
                # We cannot skip folds with no Y since this would mean
                # a portion of the data would not be output to file
                # TODO: Check that not only one fold has Y, in which
                # case training would break when that fold is held-in
#                if not 'Y' in train_labels or not 'N' in train_labels:
#                    continue
#                if not 'Y' in test_labels or not 'N' in test_labels:
#                    continue
                splits.append(TrainingSplit("<%s = %s>" % (args.cv_column, value_desc),
                                            ind_train_fold, ind_test_fold, data.label))
            assert(len(splits) > 0)
        else: # TODO factor into the standard case, by generating 'entries' randomly
            num_splits = args.cv_n_folds
            assert(set(ind_train) == set(ind_test))
            data = data[ind_train]
            splits = create_crossvalidation_splits(data, num_splits)
    else:
        # Partitions do not overlap
        assert len(set(ind_train).intersection(set(ind_test))) == 0
        splits = [TrainingSplit("<%s|%s>" % (' AND '.join(args.train_on),
                                             ' AND '.join(args.test_on)),
                                ind_train, ind_test, data.label)]
    
    STATUS.status("Starting training...")
    if args.RF_mode == 'train_metaclassifier':
        train_sources = numpy.unique([row.source for row in data if row.split == 'train'])
        test_sources  = numpy.unique([row.source for row in data if row.split == 'test'])
        metatrain_sources = test_sources[:len(test_sources) // 2]
        metatest_sources  = test_sources[len(test_sources) // 2:]
        
        STATUS[10]("Trained on sources:")
        for s in train_sources: STATUS[10]("    %s" % s)
        STATUS[10]("Metatraining on sources:")
        for s in metatrain_sources: STATUS[10]("    %s" % s)
        STATUS[10]("Metatesting on sources:")
        for s in metatest_sources: STATUS[10]("    %s" % s)
#        train_sources = ['CD010771', 'CD011134', 'CD011548']
#        test_sources  = ['CD010705', 'CD010772', 'CD010775']
        assert(len(set(train_sources).intersection(set(test_sources))) == 0)
        assert(len(set(metatrain_sources).intersection(set(metatest_sources))) == 0)
        # TODO move this into bin/ML/meta and factor out the data preprocessing
        # parts of this file so it can be shared
        RF_data_train = []
        for source in metatrain_sources:
            try:
                with open('../runs/CLEF/RF_data/20180610/RF_%s' % source, 'rb') as input_file:
                    RF_data_train += pickle.load(input_file)
            except FileNotFoundError: pass
        RF_data_test = []
        for source in metatest_sources:
            try:
                with open('../runs/CLEF/RF_data/20180610/RF_%s' % source, 'rb') as input_file:
                    RF_data_test += pickle.load(input_file)
            except FileNotFoundError: pass
        meta_classifier = MetaClassifier(meta_classifier,
                                         data,
                                         data.label,
                                         static_models,
                                         RF_data_train, RF_data_test)
        meta_classifier.train()

        filename = args.marshall
        STATUS.status('Writing file %s' % filename)
        with open(filename, 'wb') as output:
            pickle.dump(meta_classifier._classifier, output)
        sys.exit(0)
        
    elif args.RF_mode == 'meta_RF':
        
        train_sources = numpy.unique([row.source for row in data if row.split == 'train'])
        test_sources  = numpy.unique([row.source for row in data if row.split == 'test'])
        metatrain_sources = test_sources[:len(test_sources) // 2]
        metatest_sources  = test_sources[len(test_sources) // 2:]
        
#        train_sources = ['CD010771', 'CD011134', 'CD011548']
#        test_sources  = ['CD010705', 'CD010772', 'CD010775']
#        metatrain_sources = ['CD011134']
#        metatest_sources  = ['CD010772']
        STATUS[10]("Trained on sources:")
        for s in train_sources: STATUS[10]("    %s" % s)
        STATUS[10]("Metatraining on sources:")
        for s in metatrain_sources: STATUS[10]("    %s" % s)
        STATUS[10]("Metatesting on sources:")
        for s in metatest_sources: STATUS[10]("    %s" % s)
        assert(len(set(train_sources).intersection(set(test_sources))) == 0)
        assert(len(set(metatrain_sources).intersection(set(metatest_sources))) == 0)
        
        metatrain_splits = []
        for source in metatrain_sources:
            ind_train = numpy.where([d.source == source and d.split == 'seed' for d in data])[0]
            ind_test  = numpy.where([d.source == source and d.split != 'seed' for d in data])[0]
            metatrain_splits.append(TrainingSplit("<%s>" % (source),
                                                  ind_train.tolist(),
                                                  ind_test.tolist(),
                                                  data.label))
        metatest_splits  = []
        for source in metatest_sources:
            ind_train = numpy.where([d.source == source and d.split == 'seed' for d in data])[0]
            ind_test  = numpy.where([d.source == source and d.split != 'seed' for d in data])[0]
            metatest_splits.append(TrainingSplit("<%s>" % (source),
                                                 ind_train.tolist(),
                                                 ind_test.tolist(),
                                                 data.label))
        
        meta_ranker = None
        finished = False
        
        while not finished:
            # Build metatrain data
            runner = Runner(trainer, metatrain_splits, args.n_repetitions)
            runner = ActiveLearner(runner, RF_mode = args.RF_mode,
                                   static_models   = static_models,
                                   meta_classifier = meta_ranker)
            runner.run(verbosity = args.verbosity)
            RF_data_train = runner.RF_data
            
            scores = []
            # Build metatest data
            runner = Runner(trainer, metatest_splits, args.n_repetitions)
            runner = ActiveLearner(runner, RF_mode = args.RF_mode,
                                   static_models   = static_models,
                                   meta_classifier = meta_ranker)
            scores = runner.run(verbosity = args.verbosity)
            RF_data_test = runner.RF_data
            STATUS[0]('Score after metatraining: %.3f' % numpy.mean(scores))
            
#            meta_classifier.rebuild_classifier()
            meta_ranker = MetaClassifier(meta_classifier,
                                         data,
                                         data.label,
                                         static_models,
                                         RF_data_train, RF_data_test)
            meta_ranker.train()
        
    else:
        runner = Runner(trainer, splits, args.n_repetitions)
        if args.RF_mode == 'none':
            runner.run(verbosity = args.verbosity, eval_metrics = args.metrics)
        else:
            runner = ActiveLearner(runner, RF_mode = args.RF_mode,
                                   static_models   = static_models,
                                   meta_classifier = meta_classifier)
            runner.run(verbosity = args.verbosity)
    '''
    for trainer in runner.trainers():
        X_p = trainer._classifier.get_activation_pattern(shared_data_view.transform(data[ind_test]))
        for i in range(X_p.shape[0]):
            x_p = X_p[i, :].tolist()[0]
            STATUS[5]("X_prime: %.3f +- %.3f in range (%.3f, %.3f)" % (numpy.median(x_p),
                                                                       numpy.std(x_p),
                                                                       min(x_p),
                                                                       max(x_p)))
    '''
    if args.output:
        assert args.output_format in ['TREC', 'DataStream']
        
        for run_name, ranked_X in runner.get_ranked_test_data():
            filename = "%s[%s]" % (args.output, run_name)
            STATUS.status('Writing file %s' % filename)

            with open(filename, 'w') as output:
                if args.output_format == 'TREC':
                    interaction = "NF"
                    i = 0
                    for row in ranked_X:
                        i += 1
                        out_string = "%s %s %s %i %.3f %s\n" % (row.source,
                                                                interaction,
                                                                row.PMID,
                                                                i,
                                                                row.confidence,
                                                                args.marshall)
                        output.write(out_string)
                else: # DataStream
                    output.write(ranked_X.marshall())
        STATUS.status('')
    
    if args.marshall:
        i = 0
        for trainer in runner.trainers():
            i += 1
            filename = "%s[%i]" % (args.marshall, i)
            STATUS.status('Writing file %s' % filename)

            with open(filename, 'wb') as output:
                # All the trainers will have the same transformer, but it will
                # just get messy to try to make them shared across files.
                # The standard use case should just output one trainer anyway
                output_data = [trainer._shared_data_view._transformer, trainer._classifier]
                pickle.dump(output_data, output)
        STATUS.status('')
    
    # Marshall relevance feedback data to be used to train meta classifiers
    if args.output_RF_data:
#        from itertools import chain
#        RF_data = list(chain.from_iterable([trainer.RF_data for trainer in runner.trainers()]))
        filename = args.output_RF_data
        STATUS.status('Writing file %s' % filename)
        with open(filename, 'wb') as output:
            pickle.dump(runner.RF_data, output)
        STATUS.status('')

    STATUS[1]('Done.')

#    input()
#    keras_backend.get_session().close()
