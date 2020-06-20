from preprocess import *
import numpy as np
from directions2pairs import cooking_devices, ingredient_prep, find_verb_tuples
from wordcloud import WordCloud
from matplotlib import pyplot as plt


def edit_dist(s1, s2, thresh=None):
    """
    Calculate the edit distance between two strings. This is basically an implementation of the
    Wagner-Fischer algorithm I lifted from a stackoverflow thread:
            https://stackoverflow.com/questions/2460177/edit-distance-in-python
    (the first up-voted answer)
    :param s1: first string
    :param s2: second string
    :param thresh: threshold for checking actual edit distance. If the difference between the lengths of the
            strings is bigger than the threshold, then the edit distance won't be computed (to save computing
            time) and will return the value of the threshold
    :return: the editing distance between the two strings if it is lower than the threshold
    """
    if thresh is not None:
        if abs(len(s1) - len(s2)) > thresh:
            return thresh+1
    if len(s2) > len(s1):
        s1, s2 = s2, s1
    dists = range(len(s1) + 1)
    for i, c2 in enumerate(s2):
        dists_ = [i+1]
        for j, c1 in enumerate(s1):
            if c1 == c2:
                dists_.append(dists[j])
            else:
                dists_.append(1 + min(dists[j], dists[j+1], dists_[-1]))
        dists = dists_
    return dists[-1]


class MIngredient:
    """
    A class that holds all occurrences of an ingredient and provides support for merging operations
    """

    def __init__(self, name, quantity, unit, verb, preaction, step, score):
        self.name = name

        quantity, unit = quantity_to_vol(quantity, unit)
        self.quants = [quantity]
        self.meas = [unit]
        self.verbs = [verb]
        self.preacts = preaction
        self.steps = [step]
        self.scores = [score]

        self.oven = True if name == 'oven' else False

    def __lt__(self, other):
        if self.name < other.name:
            if edit_dist(self.name, other.name, 2) > 2:
                return True

    def __eq__(self, other):
        return True if edit_dist(self.name, other.name, 2) <= 2 else False

    def merge(self, other):
        n = other.name if self.name < other.name else self.name
        self.name = n
        self.quants += other.quants
        self.meas += other.meas
        self.verbs += other.verbs
        self.preacts += other.preacts
        self.steps += other.steps
        self.scores += other.scores

    def get_verb(self):
        if self.oven:
            return self.__oven_verb()
        unique, counts = np.unique(self.verbs, return_counts=True)
        return unique[np.argmax(counts)]

    def get_preaction(self):
        unique, counts = np.unique(self.preacts, return_counts=True)
        return unique[np.argmax(counts)]

    def get_amount(self):
        """
        :return: the weighted average quantity of the ingredient
        """
        m = self.get_unit()
        scores = np.array([self.scores[i] for i in range(len(self.meas)) if self.meas[i] == m])
        q = np.array([self.quants[i] for i in range(len(self.meas)) if self.meas[i] == m])
        amnt = np.sum(scores*q/np.sum(scores))
        return amnt

    def get_unit(self):
        unique, counts = np.unique(self.meas, return_counts=True)
        return unique[np.argmax(counts)]

    def get_step(self):
        scores = np.array(self.scores)
        return np.sum(np.array(self.steps) * scores / np.sum(scores))

    def __oven_verb(self):
        """
        :return: the "correct" verb for oven (including baking time and temperature)
        """
        scores = np.array(self.scores)
        cooking_time = []
        cooking_temp = []
        for v in self.verbs:
            numbers = [a for a in v.split() if a.isnumeric()]
            if len(numbers) < 2:
                cooking_time.append(0)
            else:
                cooking_time.append(int(numbers[1]) if v.split()[-1] == 'minutes' else 60*int(numbers[1]))
            if len(numbers) < 1:
                cooking_temp.append(180)
            else: cooking_temp.append(int(numbers[0]))
        temp = np.sum(np.array(cooking_temp) * scores / np.sum(scores))
        cooking_time = np.array(cooking_time)
        if len(cooking_time[cooking_time > 0]) == 0:
            time = 'until golden'
        else:
            time = cooking_time[cooking_time > 0] * scores[cooking_time > 0] / np.sum(scores[cooking_time > 0])
            time = np.sum(time)
            time = 'for ' + str(int(time)) + ' minutes'
        temp = np.round(temp/5)*5
        return 'bake at ' + str(int(temp)) + ' C ' + time

    @staticmethod
    def step_key(ing):
        return ing.get_step()

    @staticmethod
    def score_key(ing):
        s = np.sum(ing.scores)
        return s if not np.isnan(s) else 0

    @staticmethod
    def build_ings(ings_table, prep, ing_tuples, indxs, num_serve, score):
        # extract quantities and measurement units
        quants = [float(a[1])/num_serve for a in ings_table]
        meas = [a[2] for a in ings_table]

        # reorder by the verb tuples
        indxs = [ind for a in indxs for ind in a]
        quants = [quants[i] if i != -1 else -1 for i in indxs]
        meas = [meas[i] if i != -1 else '' for i in indxs]
        prep = [prep[i] if i != -1 else [] for i in indxs]

        # extract needed variables
        steps = [i for i, a in enumerate(ing_tuples) for _ in a[1]]
        ings = [tup[0] for step in ing_tuples for tup in step[1]]
        verbs = [tup[1] for step in ing_tuples for tup in step[1]]

        # make sure each ingredient has something in the prep and change format
        for i, p in enumerate(prep):
            if len(p) == 0:
                prep[i].append('')
            else:
                new = []
                for act in p:
                    new.append(act[1])
                prep[i] = new

        ing_objs = []
        for i, ing in enumerate(ings):
            tmp = MIngredient(ing, quants[i], meas[i], verbs[i], prep[i], steps[i], score)
            ing_objs.append(tmp)
        return ing_objs


def recipe_score(rating, num_rated, num_made):
    """
    Calculate the score of the recipe according to our scoring scheme
    :param rating: the user's rating of the recipe
    :param num_rated: number of users that rated the recipe
    :param num_made: number of users who have stated that they used the recipe
    :return: the score of the recipe
    """
    return np.log(rating*num_rated*num_made + 1)  # TODO choose a better scoring scheme


def parse_recipe(recipe):
    """
    Parse a single recipe
    :param recipe: a dictionary containing all of the necessary details about the recipe in question
    :return: a tuple containing
                - the number of servings in the recipe
                - the recipe's score
                - a list of MIngredients used in the recipe
    """
    directions = recipe['Directions']
    ingredients = recipe['Ingredients']
    num_rated = float(recipe['NumReviews'])
    num_made = float(recipe['NumMadeIt'])
    rating = float(recipe['Rating'])
    num_serv = float(recipe['NumServings'])
    score = recipe_score(rating, num_rated, num_made)

    # strip ingredient names from quantities and measurement units
    ings_table = split_ingredients(ingredients)
    true_ings, prep = ingredient_prep([x[0] for x in ings_table])
    ingredient_tups, ind = find_verb_tuples(directions, true_ings)
    return num_serv, score, MIngredient.build_ings(ings_table, prep, ingredient_tups, ind, num_serv, score)


def parse_relevant_recipes(recipes, ing_restriction=lambda _: True):
    """
    Parse all of the relevant recipes for data needed
    :param recipes: a list of dictionaries containing all necessary parts of the recipe
    :param ing_restriction: a restriction on the number of ingredients
    :return: a tuple containing
             - the average number of servings
             - the score of each recipe
             - the average number of ingredients used
             - a list of the ingredients from all the recipes
    """
    ings = []
    num_ings = []
    scores = []
    num_serves = []
    for recipe in recipes:

        # add only if the recipe abides by the restrictions
        if ing_restriction(len(recipes[recipe]['Ingredients'])):

            # parse the recipe
            ns, score, rec_ings = parse_recipe(recipes[recipe])
            num_serves.append(ns)
            scores.append(score)
            num_ings.append(len(rec_ings))

            # merge copies of the same ingredient
            for i, ing in enumerate(ings):
                for j, r in enumerate(rec_ings):
                    to_pop = []
                    if ing == r:
                        ings[i].merge(r)
                        to_pop.append(j)
                    for tmp in to_pop:
                        rec_ings.pop(tmp)
            ings += rec_ings

    # normalize scores to 1
    scores = np.array(scores)
    scores /= np.sum(scores)
    return np.sum(np.array(num_serves)*scores), scores, np.sum(np.array(num_ings)*scores), ings


def merge_baseline(recipes, special_ings=None, restrictions='', rest_func=lambda _: True, vis=True):
    """
    Baseline model for merging recipes, by taking their average
    :param recipes: a list of dictionaries of the relevant recipes
    :param special_ings: an option to add special ingredients
    :param restrictions: an option to add restrictions on the number of ingredients
    :param rest_func: the restrictions function on the number of ingredients
    :return: a tuple containing:
             - the quantities of each ingredient
             - an ingredient tuple list as returned by directions2pairs.find_verb_tups
    """
    num_ings = [len(recipes[recipe]['Ingredients']) for recipe in recipes]

    if restrictions.lower() == 'fast':
        rest_func = lambda _: True if np.random.random() <= 0.5 else False
    elif restrictions.lower() == 'veryfast':
        rest_func = lambda _: True if np.random.random() <= 0.25 else False
    elif restrictions.lower() == 'simple':
        ni = np.quantile(num_ings, 0.2)
        rest_func = lambda x: True if x <= ni else False
    elif restrictions.lower() == 'complex':
        ni = np.quantile(num_ings, 0.66)
        rest_func = lambda x: True if x >= ni else False

    ns, scores, avg_ings, ings = parse_relevant_recipes(recipes, rest_func)  # TODO add restrictions
    if vis:
        create_vis(ings)

    # sort ingredients by their total score
    ings.sort(key=MIngredient.score_key, reverse=True)

    # choose only the top ingredients
    ings = ings[:int(np.round(avg_ings))]
    ings.sort(key=MIngredient.step_key)

    # create the returned arrays in the correct format
    steps = np.floor([ing.get_step() for ing in ings])
    step_num = 0
    tups = [[0, []]]
    prep = [[]]
    quants = [[]]
    meas = [[]]
    for i, ing in enumerate(ings):
        if i > 0 and steps[i] != steps[i-1]:
            step_num += 1
            tups.append([step_num, []])
            quants.append([])
            meas.append([])
        tups[-1][1].append((ing.name, ing.get_verb()))
        quants[-1].append(ing.get_amount() if ing.name not in cooking_devices else -1)
        meas[-1].append(ing.get_unit())
        if ing.get_preaction() != '':
            prep[-1].append((ing.name, ing.get_preaction()))
        elif ing.name not in cooking_devices:
            prep.append([])
    return quants, meas, prep, tups, ns


def create_vis(ings):
    """
    Create word clouds of the ingredients and (ing, action) tuples during merging
    :param ings: a list of MIngredient objects
    """
    # create a dictionary between ingredient names and their scores
    ingredients = {ing.name: np.ceil(MIngredient.score_key(ing) + 1) for ing in ings if ing.name not in cooking_devices}

    # create a dictionary between (ing, action) tuples and their scores
    tups = {v + ' ' + ing.name: np.ceil(MIngredient.score_key(ing) + 1) for ing in ings for v in ing.verbs
            if ing.name not in cooking_devices}

    # create the WordClouds
    wc = WordCloud(width=1400, height=800, background_color='white') \
        .generate_from_frequencies(ingredients)
    wc_tup = WordCloud(width=1400, height=800, background_color='white') \
             .generate_from_frequencies(tups)
    plt.figure()

    plt.subplot(211)
    plt.imshow(wc)
    plt.axis('off')

    plt.subplot(212)
    plt.imshow(wc_tup)
    plt.axis('off')

    plt.tight_layout()


