#!bin/bash

#PIPELINE="data/param/pipeline/word_sequence_128.yaml"
#CLASSIFIER="data/param/classifier/LSTM_128_noemb.yaml"

PIPELINE="data/param/pipeline/sparse_terminology_with_context.yaml"
#CLASSIFIER="data/param/classifier/Neural_LogReg.yaml"
CLASSIFIER="data/param/classifier/SGD_pairwise.yaml"
#CLASSIFIER="data/param/classifier/SGD.yaml"
VERBOSITY="4"
OUTPUT_NAME="../runs/CL_extraction/static_ngram_20190212"

DATA_FILE="annotated_UMLS"

# Distant supervision

python -m bin.Train --data data/full/CL_extraction/distant_UMLS_1_dev.json data/full/CL_extraction/"${DATA_FILE}"_1.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator!=Auto \
       --output "${OUTPUT_NAME}_item1_distant.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/distant_UMLS_2_dev.json data/full/CL_extraction/"${DATA_FILE}"_2.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator!=Auto \
       --output "${OUTPUT_NAME}_item2_distant.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/distant_UMLS_3_dev.json data/full/CL_extraction/"${DATA_FILE}"_3.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator!=Auto \
       --output "${OUTPUT_NAME}_item3_distant.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# Supervision, CV splits

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_1.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator=Mariska \
       --output "${OUTPUT_NAME}_item1_Mariska.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_2.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator=Mariska \
       --output "${OUTPUT_NAME}_item2_Mariska.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_3.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator=Mariska \
       --output "${OUTPUT_NAME}_item3_Mariska.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY


python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_1.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator=Rene \
       --output "${OUTPUT_NAME}_item1_Rene.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_2.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator=Rene \
       --output "${OUTPUT_NAME}_item2_Rene.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_3.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator=Rene \
       --output "${OUTPUT_NAME}_item3_Rene.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY


python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_1.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator!=Unk \
       --output "${OUTPUT_NAME}_item1_all.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_2.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator!=Unk \
       --output "${OUTPUT_NAME}_item2_all.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_3.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --test_on annotator!=Unk \
       --output "${OUTPUT_NAME}_item3_all.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_1.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --cv_train_on annotator=Mariska \
       --test_on     annotator=Rene \
       --output "${OUTPUT_NAME}_item1_Mariska_Rene.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_2.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --cv_train_on annotator=Mariska \
       --test_on     annotator=Rene \
       --output "${OUTPUT_NAME}_item2_Mariska_Rene.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_3.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --cv_train_on annotator=Mariska \
       --test_on     annotator=Rene \
       --output "${OUTPUT_NAME}_item3_Mariska_Rene.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY


python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_1.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --cv_train_on annotator=Rene \
       --test_on     annotator=Mariska \
       --output "${OUTPUT_NAME}_item1_Rene_Mariska.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_2.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --cv_train_on annotator=Rene \
       --test_on     annotator=Mariska \
       --output "${OUTPUT_NAME}_item2_Rene_Mariska.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

python -m bin.Train --data data/full/CL_extraction/"${DATA_FILE}"_3.json \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --metrics AP \
       --RF_mode 'none' \
       --cv_column review \
       --cv_train_on annotator=Rene \
       --test_on     annotator=Mariska \
       --output "${OUTPUT_NAME}_item3_Rene_Mariska.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY
