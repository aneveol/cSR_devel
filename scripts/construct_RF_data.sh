#!bin/bash

declare -a sourcestest=("CD007394")
declare -a sources=("CD007394"
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

for s in "${sources[@]}"
do
   python -m bin.Train --data data/full/clef2017_ALL \
       --sparse \
       --pipeline data/param/pipeline/waterloo_orig.yaml \
       --classifier data/param/classifier/LogReg_default.yaml \
       --RF_mode 'Y|MN' \
       --train_on split=seed  source="$s" \
       --test_on  split!=seed source="$s" \
       --output_RF_data ../runs/CLEF/RF_data/20180610/RF_"$s" \
       --n_repetitions 20 \
       --verbosity 10
done
