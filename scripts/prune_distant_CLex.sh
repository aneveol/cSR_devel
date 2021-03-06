#!bin/bash

for i in {1..3};
do
    reviews=`python -m bin.Data --inspect --col review --input data/full/CL_extraction/annotated_$i.json | grep CD | sort | uniq`
    
    for review in $reviews;
    do
	if [[ $( python -m bin.Data --inspect --col review --get annotator!=Unk review=$review --input data/full/CL_extraction/data666_$i.json | grep CD ) ]];
	then # There's a train set
	    if [[ $( python -m bin.Data --inspect --col review --get label=Y annotator=Unk review=$review --input data/full/CL_extraction/data666_$i.json | grep CD ) ]];
	    then # There's a test set
		echo Processing item $i for review $review
		python -m bin.Train --data data/full/CL_extraction/data666_$i.json \
		       --sparse \
		       --pipeline data/param/pipeline/sparse_single_text_field.yaml \
		       --classifier data/param/classifier/SGD.yaml \
		       --metrics AP \
		       --RF_mode 'none' \
		       --train_on annotator!=Unk review=$review \
		       --test_on label=Y annotator=Unk review=$review \
		       --output "../runs/CL_distant_pruning/item{$i}_static_ngram_20181128_sorted.json" \
		       --output_format 'DataStream' \
		       --verbosity 1
	    fi
	fi
    done
done
