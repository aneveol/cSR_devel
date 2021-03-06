#!bin/bash

declare -a sourcestest=("CD008122")
declare -a sources2017=("CD007394"
                    "CD007427"
		    "CD007431"
		    "CD008054"
		    "CD008081"
		    "CD008643"
		    "CD008686"
		    "CD008691"
		    "CD008760"
		    "CD008782"
		    "CD008803"
		    "CD009020"
		    "CD009135"
		    "CD009185"
		    "CD009323"
		    "CD009372"
		    "CD009519"
		    "CD009551"
		    "CD009579"
		    "CD009591"
		    "CD009593"
		    "CD009647"
		    "CD009786"
		    "CD009925"
		    "CD009944"
		    "CD010023"
		    "CD010173"
		    "CD010276"
		    "CD010339"
		    "CD010386"
		    "CD010409"
		    "CD010438"
		    "CD010542"
		    "CD010632"
		    "CD010633"
		    "CD010653"
		    "CD010705"
		    "CD010771"
		    "CD010772"
		    "CD010775"
		    "CD010783"
		    "CD010860"
		    "CD010896"
		    "CD011134"
		    "CD011145"
		    "CD011548"
		    "CD011549"
		    "CD011975"
		    "CD011984"
		    "CD012019")
declare -a sources2018=("CD008122"
			"CD008587"
			"CD008759"
			"CD008892"
			"CD009175"
			"CD009263"
			"CD009694"
			"CD010213"
			"CD010296"
			"CD010502"
			"CD010657"
			"CD010680"
			"CD010864"
			"CD011053"
			"CD011126"
			"CD011420"
			"CD011431"
			"CD011515"
			"CD011602"
			"CD011686"
			"CD011912"
			"CD011926"
			"CD012009"
			"CD012010"
			"CD012083"
			"CD012165"
			"CD012179"
			"CD012216"
			"CD012281"
			"CD012599")

for s in "${sourcestest[@]}"
do
   python -m bin.Train --data data/full/clef2018_ALL \
       --sparse \
       --pipeline data/param/pipeline/waterloo_pipeline.yaml \
       --classifier data/param/classifier/LogReg_default.yaml \
       --static_models ../models/CLEF2017/clef2017_sparse_SGD_train_split_noUS\[1\] \
       --RF_mode 'Y|MN' \
       --train_on split=seed  source="$s" \
       --test_on  split!=seed source="$s" \
       --output_format 'TREC' \
       --output ../runs/CLEF/20180508/waterloo_pipeline_B_"$s" \
       --n_repetitions 20 \
       --verbosity 10
done
