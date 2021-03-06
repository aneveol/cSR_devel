

for d in 1 2 3
do
    python -m scripts.construct_train_test_set_CV \
	   --data data/full/CL_extraction/annotated_"$d".json \
	   --col review \
	   --train_out data/full/CL_extraction/annotated_CV/annotated_"$d"_train.json \
	   --dev_out data/full/CL_extraction/annotated_CV/annotated_"$d"_dev.json
    python -m scripts.construct_train_test_set_CV \
	   --data data/full/CL_extraction/annotated_UMLS_"$d".json \
	   --col review \
	   --train_out data/full/CL_extraction/annotated_CV/annotated_UMLS_"$d"_train.json \
	   --dev_out data/full/CL_extraction/annotated_CV/annotated_UMLS_"$d"_dev.json
done

declare -a reviews=('CD007394'
		    'CD007427'
		    'CD008054'
		    'CD008081'
		    'CD008760'
		    'CD008782'
		    'CD008892'
		    'CD009372'
		    'CD009647'
		    'CD010339'
		    'CD010360'
		    'CD010653'
		    'CD010705'
		    'CD011420')
declare -a annotators=('Mariska'
		       'Rene')

for annotator in "${annotators[@]}"
do
    for d in 1 2 3
    do
	for review in "${reviews[@]}"
	do
	    python -m bin.Export \
 --input data/full/CL_extraction/annotated_CV/annotated_"$d"_train_"${annotator}"_"${review}".json \
              --output ../BERT/bert/data/CLEX/annotated_"$d"_train_"${annotator}"_"${review}".tsv \
              --type BERT
	    python -m bin.Export \
 --input data/full/CL_extraction/annotated_CV/annotated_"$d"_dev_"${annotator}"_"${review}".json \
              --output ../BERT/bert/data/CLEX/annotated_"$d"_dev_"${annotator}"_"${review}".tsv \
              --type BERT
	    python -m bin.Export \
 --input data/full/CL_extraction/annotated_CV/annotated_UMLS_"$d"_train_"${annotator}"_"${review}".json \
              --output ../BERT/bert/data/CLEX/annotated_UMLS_"$d"_train_"${annotator}"_"${review}".tsv \
              --type BERT
	    python -m bin.Export \
 --input data/full/CL_extraction/annotated_CV/annotated_UMLS_"$d"_dev_"${annotator}"_"${review}".json \
              --output ../BERT/bert/data/CLEX/annotated_UMLS_"$d"_dev_"${annotator}"_"${review}".tsv \
              --type BERT
	done
    done
done
