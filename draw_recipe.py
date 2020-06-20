from graphviz import Digraph, Source
from directions2pairs import find_verb_tuples, ingredient_prep
from preprocess import split_ingredients, round_nicely, metric_scale
from merge_utils import merge_baseline

from os import mkdir
from os.path import exists


def prepare_single_graph(recipe, to_save=True):
    """
    Creates graphs of a single recipe
    :param recipe: a given recipe to be parsed
    :param to_save: True if the graphs should be saved
    :return: detailed and simple graph objects
    """
    directions = recipe['Directions']
    ingredients = recipe['Ingredients']
    recipe_name = recipe['Title']

    ings_table = split_ingredients(ingredients)
    true_ings, prepped_ings = ingredient_prep([x[0] for x in ings_table])
    extracted, ind = find_verb_tuples(directions, true_ings)

    recipe_graph = Digraph()
    detailed_graph = Digraph()
    set_graph_style(recipe_graph)
    set_graph_style(detailed_graph)

    # create pre-action subgraph
    with detailed_graph.subgraph(name='cluster pre-actions') as dg:
        for i, actions in enumerate(prepped_ings):
            if len(actions) > 0:
                verb = []
                for _, action in actions:
                    verb.append(action)
                node = node_name(actions[0][0], ings_table[i][1], ings_table[i][2])
                recipe_graph.edge(node, node, label=', '.join(verb))
                dg.edge(node, node, label=', '.join(verb))
        dg.attr(label='pre-actions', style='dashed')

    for i, (step_num, step_components) in enumerate(extracted):
        with detailed_graph.subgraph(name='cluster'+str(step_num)) as dg:
            connection = recipe_name + '\n' +str(recipe['NumServings']) + ' servings' if i == len(extracted) - 1 else str(i)

            for j, (stem_ing, verb) in enumerate(step_components):
                ing = stem_ing if ind[i][j] == -1 else true_ings[ind[i][j]]
                quantity = ings_table[ind[i][j]][1] if ind[i][j] != -1 else ''
                measure = ings_table[ind[i][j]][2] if ind[i][j] != -1 else ''
                node = node_name(ing, quantity, measure)
                recipe_graph.edge(node, connection, label=verb)
                dg.edge(node, connection, label=verb)

            dg.attr(label=break_step(directions[step_num]), style='rounded')
            if i > 0:  # add edges between a step and its preceding
                recipe_graph.edge(str(i-1), connection)
                dg.edge(str(i-1), connection)

    if to_save:
        if not exists('./graphs/'):  # Create target Directory if don't exist
            mkdir('./graphs/')
        recipe_graph.render(filename='./graphs/'+recipe_name+'_Simple Graph')
        detailed_graph.render(filename='./graphs/'+recipe_name+'_Detailed Graph')

    return recipe_graph, detailed_graph


def prepare_averaged_graph(recipes, recipe_name, to_save=True, vis=True):
    """
    Combines and creates a graph out of the given recipes
    :param recipes: all recipes with the chosen name
    :param recipe_name: name of the requested recipes
    :param to_save: True if the graphs should be saved
    :param vis: True if word cloud visualization should be created
    :return: detailed and simple graph objects
    """
    detailed_graph = Digraph()
    set_graph_style(detailed_graph)

    quantities, units, preactions, extracted, num_servings = merge_baseline(recipes, vis=vis)

    # create pre-action subgraph
    with detailed_graph.subgraph(name='cluster pre-actions') as dg:
        for actions in preactions:
            if len(actions) > 0:
                verb = []
                for _, action in actions:
                    verb.append(action)
                quantity, measure = find_quant_unit(actions[0][0], extracted, quantities, units, num_servings)
                node = node_name(actions[0][0], quantity, measure)
                dg.edge(node, node, label=', '.join(verb))
        dg.attr(label='pre-actions', style='dashed')

    for i, (step_num, step_components) in enumerate(extracted):
        with detailed_graph.subgraph(name='cluster' + str(step_num)) as dg:
            connection = recipe_name + '\n' +str(int(num_servings)) + ' servings' if i == len(extracted) - 1 else str(i)

            for j, (ing, verb) in enumerate(step_components):
                quantity, measure = metric_scale(round_nicely(quantities[i][j]*num_servings), units[i][j])
                node = node_name(ing, quantity, measure)
                dg.edge(node, connection, label=verb)
                dg.attr(style='rounded')

            if i > 0:  # add edges between a step and its preceding
                dg.edge(str(i - 1), connection)

    if to_save:
        if not exists('./graphs/'):  # Create target Directory if don't exist
            mkdir('./graphs/')
        detailed_graph.render(filename='./graphs/'+recipe_name+'_Combined')

    return detailed_graph


def set_graph_style(graph):
    graph.attr(fontsize='12', fontname='calibri')
    graph.attr('node', fontsize='11', fontname='calibri bold', fixedsize='false', margin='0.01')
    graph.attr('edge', fontsize='11', fontname='calibri')


def read_graph_file(path):
    return Source.from_file(path)


def node_name(ing, quantity, measure):
    quantity = str(quantity) if len(str(quantity)) == 0 or float(quantity) > 0 else ''
    if len(quantity) + len(measure) > 0:
        return ing + '\n' + str(quantity) + ' ' + measure
    return ing


def break_step(direction):
    steps = direction.split()
    new_direction = ''
    for i, word in enumerate(steps):
        new_direction += word + ' '
        if (i+1)%6 == 0 and len(steps) > i+2:
            new_direction += '\n'
    return new_direction


def find_ing_index(ing_name, extracted):
    for i, (_, step_components) in enumerate(extracted):
        for j, (ing, _) in enumerate(step_components):
            if ing == ing_name:
                return i, j
    print('could not find the ingredient ', ing_name)
    return -1, -1


def find_quant_unit(ing_name, extracted, quantities, units, num_servings):
    quantity = ''
    measure = ''
    for i, (_, step_components) in enumerate(extracted):
        for j, (ing, _) in enumerate(step_components):
            if ing == ing_name:
                quantity, measure = metric_scale(str(round_nicely(quantities[i][j] * num_servings)), units[i][j])
                break
    return quantity, measure
