# Recipy

Before running the program, the user should execute the "setup.sh" script.
This script will perform the following actions:

1. Download the recipes database to a local folder (from a public git server).
1. Set a virtual environment to install the required packages.
1. Install the required packages in the virtual environment.
1. Download files needed for the NLP packages.

After executing this script, if no virtual environment is needed (that is, all required packages are installed or can be installed), the user can just run the 'recipy.py' script with no parameters.
Otherwise, the user can call the 've_recipy.sh' script, which wraps the recipy script with activating the virtual environment.

The script will then ask for a recipe name (for example, 'chocolate').
The user then has a choice between choosing a single recipe, or a combination of all search results.
Choosing a single recipe will produce a list of the search results, from which the user will choose one.
The chosen recipe graph is then displayed.

Choosing the combination option will ask the user if a word cloud should also be presented.
The combination process might take a while, but then the recipe graph will be shown, and the word cloud after, if chosen.