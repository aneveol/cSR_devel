#!bin/bash

#PIPELINE="data/param/pipeline/sparse_text_only.yaml"
PIPELINE="data/param/pipeline/sparse_text_only_5gram.yaml"
#CLASSIFIER="data/param/classifier/SGD_pairwise.yaml"
CLASSIFIER="data/param/classifier/SGD.yaml"
VERBOSITY="6"
OUTPUT_NAME="../runs/COMET/static_amended_comp"
INPUT_NAME="data/full/COMET/COMET_all_v3.json"


# ~~~~~~~~~~~~ Update 4 ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split!=update4 \
       --test_on  abstract!=_ split=update4 \
       --output "${OUTPUT_NAME}_update4.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

exit 1

# ~~~~~~~~~~~~ Update 2 ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split!=update2 split!=update3 split!=update4 \
       --test_on  abstract!=_ split=update2 \
       --output "${OUTPUT_NAME}_update2.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Original CV ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --test_on  abstract!=_ split=original \
       --cv_column cv_split \
       --output "${OUTPUT_NAME}_original_cv.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Update 1 ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split=original \
       --test_on  abstract!=_ split=update1 \
       --output "${OUTPUT_NAME}_update1.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Update 1 CV ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split=original \
       --test_on  abstract!=_ split=update1 \
       --cv_column cv_split \
       --output "${OUTPUT_NAME}_update1_cv.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Update 2 CV ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split!=update2 split!=update3 split!=update4 \
       --test_on  abstract!=_ split=update2 \
       --cv_column cv_split \
       --output "${OUTPUT_NAME}_update2_cv.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Update 3 ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split!=update3 split!=update4 \
       --test_on  abstract!=_ split=update3 \
       --output "${OUTPUT_NAME}_update3.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Update 3 CV ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split!=update3 split!=update4 \
       --test_on  abstract!=_ split=update3 \
       --cv_column cv_split \
       --output "${OUTPUT_NAME}_update3_cv.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY

# ~~~~~~~~~~~~ Update 4 CV ~~~~~~~~~~~~
python -m bin.Train --data $INPUT_NAME \
       --sparse \
       --pipeline $PIPELINE \
       --classifier $CLASSIFIER \
       --RF_mode 'none' \
       --train_on abstract!=_ split!=update4 \
       --test_on  abstract!=_ split=update4 \
       --cv_column cv_split \
       --output "${OUTPUT_NAME}_update4_cv.json" \
       --output_format 'DataStream' \
       --verbosity $VERBOSITY
