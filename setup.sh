#!/bin/bash

RECIPE_ENV="recipy_env"

echo "Getting database of recipes..."
git clone git@github.cs.huji.ac.il:omribd/recipy_data.git > /dev/null 2>&1
unzip recipy_data/new_jsons.zip -d. > /dev/null 2>&1

echo "Creating virtual environment..."
virtualenv $RECIPE_ENV > /dev/null 2>&1

echo "Getting required Python packages (might take a few minutes)..."
source $RECIPE_ENV/bin/activate
pip3 install -r requirements.txt > /dev/null 2>&1

echo "Getting language sets..."
source $RECIPE_ENV/bin/activate
python3 -m spacy download en > /dev/null 2>&1
python3 -c "import nltk; nltk.download('averaged_perceptron_tagger')" > /dev/null 2>&1
python3 -c "import nltk; nltk.download('universal_tagset')" > /dev/null 2>&1


echo "DONE! You can now execute recipy.py in the virtual environment recipy_env."
echo "Or, you can activate ve_recipy.sh directly"
