import os
from preprocess import get_recipes
from draw_recipe import prepare_single_graph, prepare_averaged_graph, read_graph_file
from pathlib import Path
import matplotlib.pyplot as plt


def draw_single_recipe(recipes_dict):
    rec_names = list(recipes_dict.keys())
    print('found recipes:')
    for i, rname in enumerate(rec_names):
        print(str(i+1) + ') ' + rname)
    chosen_ind = int(input("Enter a recipe number: "))
    while chosen_ind < 1 or chosen_ind > len(rec_names):
        chosen_ind = int(input("Enter a recipe number: "))

    chosen_rec = recipes_dict[rec_names[chosen_ind-1]]
    simple, detailed = prepare_single_graph(chosen_rec)
    detailed.view()


def recipe_union(recipes_dict, recipe_name, to_wordcloud):
    print('Combining (might take a while)... ')
    graph = prepare_averaged_graph(recipes_dict, recipe_name, vis=to_wordcloud)
    graph.view()


def input_recipe():
    recipe_name = input("Hi there. What cake would you like to make today?   ")
    json_path = Path(os.path.dirname(os.path.realpath(__file__)) +  '/jsons/')
    recipes = get_recipes(json_path, recipe_name)
    return recipes, recipe_name


def main():
    recipes, recipe_name = input_recipe()
    while not recipes:
        print("No matches were found. Please try another type of cake.")
        recipes, recipe_name = input_recipe()

    print('Found ' + str(len(recipes)) + ' recipes.')
    to_combine = None
    while to_combine is None:
        user_choice = input('Would you like a Specific recipe or a Combination [S/C]?   ').lower()
        if user_choice in ['s', 'specific']:
            to_combine = False
        elif user_choice in ['c', 'combined']:
            to_combine = True

    if not to_combine:
        draw_single_recipe(recipes)
        return

    to_wordcloud = None
    while to_wordcloud is None:
        user_choice = input('Would you like to see a word cloud [Yes/No]?   ').lower()
        if user_choice in ['n', 'no']:
            to_wordcloud = False
        elif user_choice in ['y', 'yes']:
            to_wordcloud = True

    recipe_union(recipes, recipe_name, to_wordcloud)
    if to_wordcloud:
        plt.show()


if __name__ == "__main__":
    main()
