import json
import os
import re
from nltk.stem import PorterStemmer


reg1 = '^[0-9]*\.[0-9]+|^[0-9]+'
reg2 = '^[0-9]+/[0-9]+'

ps = PorterStemmer()
measureing_words = ['cup', 'spoon', 'tbsp', 'lbs', 'kg', 'gram', 'teaspoon', 'ounce', 'tablespoon',
                    'pinch', 'package', 'can', 'inch', 'pound', 'container', 'pieces', 'bag', 'dash', 'pint']
measureing_words = list(map(ps.stem, measureing_words))


def remove_brackets(ing_list):
    """
    Disregard of substrings that appear in brackets, e.g. '(about 8 ounces)'
    :param ing_list: current ingredient list
    :return: updated ingredients list, in lowercsae
    """
    return [re.sub(r'\(.*?\)', '', ing).lower() for ing in ing_list]


def ingredients_quantities_to_decimal(ing_list, num_dishes=1):
    """
    Changes the quantity of each ingredient to decimal value. Handles integer values and string
    representations of fractions (e.g. '1/4')
    :param ing_list: current ingredient list
    :param num_dishes: the number of dishes specified in the recipe
    :return: the updated ingredients list
    """
    new_ing_list = []
    for ing in ing_list:
        quant = 0
        counter = 0
        for n in ing.split():
            res = re.findall(reg2, n)  # find fracs
            for r in res:
                counter += 1
                slash = r.find('/')
                quant += int(r[:slash]) / int(r[slash+1:])
            if res:
                continue
            res = re.findall(reg1, n) # find ints and decimals
            for r in res:
                counter += 1
                quant += float(r)
        new_ing_list.append(str(round_nicely(quant/int(num_dishes))) + ' ' + ' '.join(ing.split()[counter:]))
    return new_ing_list


def round_nicely(num):
    """
    Returns the given number as integer if it is natural, rounds it to 2 decimal places if it is a float
    """
    return int(num) if int(num) == num else round(num, 1)


def split_instructions(inst_list):
    """
    Create an instruction list by the atomic sentences
    :param inst_list: current list of instruction
    :return: atomic list of instructions, in lowercase
    """
    new_inst_list = []
    for instruction in inst_list:
        new_inst_list += [x.strip() for x in instruction.lower().split('.') if x != '']
    return new_inst_list


def get_recipes(json_path, recipe_name):
    """
    Create a dictionary of all the available recipes with the given name
    :param json_path: the directory where the downloaded recipes are found
    :param recipe_name: the name of the recipe
    :return: a dictionary that contains only the recipes of the requested dish
    """
    recipes = {}
    files = [x for x in os.listdir(json_path) if x.endswith('.json')]
    # add recipes with the given name
    for filename in files:
        with open(json_path / filename, 'r') as f:
            recipe = json.load(f)
            if recipe_name.lower() in recipe["Title"].lower():
                recipes[recipe["Title"]] = recipe

    for name, recipe in recipes.items():
        # recipe['Ingredients'] = ingredients_quantities_to_decimal(remove_brackets(recipe['Ingredients']), recipe['NumServings'])
        recipe['Ingredients'] = ingredients_quantities_to_decimal(remove_brackets(recipe['Ingredients']), 1)  # un-normalized
        recipe['Directions'] = split_instructions(recipe['Directions'])
    return recipes


def split_ingredients(ingredients):
    """
    Splits the ingredient into 3 parts - its quantity, units of measurement of that quantity and the rest of the ingredient
    :param ingredients: list of the recipe's ingredients
    :return: a list of tuples in the following structure: (ing, quantity, unit of measurement)
    """
    wo_measuring = []
    for ing in ingredients:
        split_ing = ing.split()
        q = split_ing[0] if not split_ing[0].isalpha() else 1  # quantity
        # m = ' '.join([ps.stem(x) for x in split_ing if ps.stem(x) in measureing_words])  # metrics
        m = ' '.join([x for x in split_ing if stem_word(x) in measureing_words])  # metrics
        i = ' '.join([x for x in split_ing if x != str(q) and x not in m and x[0] != '(' and x[-1] != ')'])  # rest of ingredient
        q, m = measurement_converter(q, m)
        wo_measuring.append((i, str(round_nicely(q)), m))
    return wo_measuring


def measurement_converter(quantity, metric):
    """
    Standardize the quantities to non-American units of measurement
    :param quantity: string representation of the quantity
    :param metric: unit of measurement given in the recipe
    :return: a tuple that contains the transformed quantity (as float) and the standardized unit of measurement
    """
    quantity = float(quantity)
    s_metric = stem_word(metric)
    if s_metric in measureing_words:
        if s_metric == 'spoon' or s_metric == 'tbsp':
            return quantity, 'tablespoon'
        elif s_metric == 'kg':
            return 1000*quantity, 'gram'
        elif s_metric == 'lbs' or s_metric == 'pound':
            return 453.5*quantity, 'gram'
        elif s_metric == 'ounce':
            return 28.35*quantity, 'gram'
        elif s_metric == 'pinch' or s_metric == 'dash':
            return 3*quantity, 'gram'
        elif s_metric == 'container' or s_metric == 'bag':
            return quantity, 'package'
        elif s_metric == 'piece':
            return quantity, ''
        elif s_metric == 'pint':
            return 2.36*quantity, 'cup'
    return quantity, metric  # didn't find a match


def quantity_to_vol(quantity, metric):
    """
    Converts units to volume measures. Input is assumed to have passed through measurement_converter
    :param quantity: string representation of the quantity
    :param metric: unit of measurement given in the recipe
    :return: a tuple that contains the transformed quantity (as float) and the standardized unit of measurement
    """
    quantity = float(quantity)
    s_metric = stem_word(metric)
    if stem_word(s_metric) in measureing_words:
        if s_metric == 'tablespoon':
            return 16*quantity, 'ml'
        elif s_metric == 'cup':
            return 200*quantity, 'ml'
        elif s_metric == 'teaspoon':
            return 5*quantity, 'ml'
    return quantity, metric


def vol_to_quantity(quantity, metric):
    """
    Converts from volume to more comfortable units of measurements
    :param quantity: string representation of the quantity
    :param metric: unit of measurement given in the recipe
    :return: a tuple that contains the transformed quantity (as float) and the standardized unit of measurement
    """
    quantity = float(quantity)
    if metric == 'ml':
        if quantity < 16:
            return quantity/5, 'teaspoon'
        elif quantity < 50:
            return quantity/16, 'tablespoon'
        else:
            return quantity/200, 'cup'
    return quantity, metric


def metric_scale(quantity, metric):
    """
    Convert measurement units if needed
    :param quantity: string representation of the quantity
    :param metric: unit of measurement given in the recipe
    :return: a tuple that contains the transformed quantity (as float) and the standardized unit of measurement
    """
    quantity, metric = vol_to_quantity(quantity, metric)
    if metric == 'teaspoon' and quantity > 3:
        quantity /= 3
        metric = 'tablespoon'
    if metric == 'tablespoon' and quantity > 3.125:
        quantity /= 3.125
        metric = 'cup'
    return round_nicely(quantity), metric


def stem_word(word):
    """
    Stem the given word using a Porter stemmer
    """
    return ps.stem(word)


# ############ functions used in earlier versions ############
# def remove_outliers(directions, ingredients):
#     outliers = ['baking', 'sifted']
#     for outlier in outliers:
#         directions = [d.replace(outlier,'') for d in directions]
#         ingredients = [ing.replace(outlier,'') for ing in ingredients]
#     return directions, ingredients
#
#
# def remove_measuring_words(ingredients):
#     wo_measuring = []
#     for ing in ingredients:
#         wo_measuring.append(' '.join([x for x in ing.split() if ps.stem(x) not in measureing_words]))
#     return wo_measuring
