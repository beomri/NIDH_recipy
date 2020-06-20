import spacy
import nltk
import numpy as np

import json
from collections import Counter
import re

tagger = spacy.load('en_core_web_sm')

with open('tfidf_w_ing.json', 'r') as f:
    tfidf = Counter(json.load(f))

cooking_devices = ['oven', 'refrigerator', 'freezer', 'bake',
                   'refrigerate', 'freeze', 'fridge', 'cool', 'cool down']
blacklisted_words = ['white', 'baking', 'large', 'round', 'beat', 'one']


def ingredient_prep(ingredients):
    """
    Extract the preparation needed for each of the ingredients, if there is one
    :param ingredients: the ingredients
    :return: a list <ingredients> and another list of lists of tuples
             [[(<ingredient0>, <verb0>), (<ingredient0>, <verb1>),...],[(<ingredient1>, <verb0>),...]]
             for each of the ingredients. If there is no related verb, an empty string is returned.
    """
    formatted_ingredients = []
    ing_verb_tups = []
    for ing in ingredients:
        tuples = []
        ing = ing.replace(',', '')
        tags = nltk.pos_tag(ing.split(), tagset='universal')
        verbs = [tag[0] for tag in tags if (tag[1] == 'VERB' or tag[1] == 'ADJ') and
                 tag[0][-2:] == 'ed']
        for v in verbs:
            ing = ing.replace(v, '')
        if ing[0] == ' ':
            ing = ing[1:]
        if ing[-1] == ' ':
            ing = ing[:-1]
        ing = ing.split()
        if tagger(ing[0])[0].is_stop:
            ing = ing[1:]
        if tagger(ing[-1])[0].is_stop:
            ing = ing[:-1]
        ing = ' '.join(ing)
        for v in verbs:
            tuples.append((ing, tagger(v)[0].lemma_))
        formatted_ingredients.append(ing)
        ing_verb_tups.append(tuples)

    return formatted_ingredients, ing_verb_tups


def cross_correlate(str1, str2):
    """
    Find longest cross correlation between str1 and str2, also return length
    as the substring
    :param str1: the first, preferably longer, string
    :param str2: the second, shorter, string
    :return: a tuple (<substring length>, <substring>)
    """

    def get_substr_match(s1, s2):
        """ returns the longest matching substring """
        cmp = [s1[k] != s2[k] for k in range(len(s1))]
        cmp = [True] + cmp + [True]
        nz_ind = np.nonzero(cmp)[0]
        match_lengths = np.diff(nz_ind) - 1
        best_ind = np.argmax(match_lengths)
        max_length = match_lengths[best_ind]
        substr = s1[nz_ind[best_ind]:nz_ind[best_ind]+max_length]
        return substr, max_length

    long_str, short_str = [str1, str2][::2*(len(str1) > len(str2))-1]
    long_len, short_len = len(long_str), len(short_str)

    lengths = []
    substrs = []

    for i in range(1-short_len, long_len):
        if i < 0:
            n = short_len + i
            s1 = short_str[-n:]
            s2 = long_str[:n]
        elif i > long_len-short_len:
            n = long_len - i
            s1 = short_str[:n]
            s2 = long_str[-n:]
        else:
            s1 = short_str
            s2 = long_str[i:i+short_len]

        substr, max_length = get_substr_match(s1, s2)
        lengths.append(max_length)
        substrs.append(substr)

    final_ind = np.argmax(lengths)
    ret_str = substrs[final_ind].strip()
    return lengths[final_ind], ret_str


def fix_matches(corr):
    """
    Fix the format of the found matches
    :param corr: the found correlation
    :return: the formatted match
    """
    match = corr[1].split()
    score = corr[0]
    for i, word in enumerate(match):
        if tfidf[word] == 0 or len(word) <= 2:
            match.pop(i)
        else:
            tag = tagger(word)
            tag = tag[0]
            if tag.pos_ != 'ADJ' and word not in blacklisted_words:
                score += tfidf[word]
            if tag.is_stop:
                score -= len(tag.text)
    match = '' if len(match) == 0 else ' '.join(match)
    return score, match


def find_correlations(ing, directions):
    """
    :param ing: the ingredient to find in the directions
    :param directions: the directions to use for correlation
    :return: all of the matches of the correlations
    """
    matches = []
    for d in directions:
        correlations = cross_correlate(d, ing)
        correlations = fix_matches(correlations)
        matches.append(correlations)
    return matches


def create_tuple(ind, name, step, tok_name):
    """
    Find the verb related to the ingredient in the step
    :param ind: the index of the step (this is just added to the tuple)
    :param name: the name of the ingredient
    :param step: the directions including the ingredient
    :param tok_name: the token the ingredient was changed into
    :return: a ingredient (name, verb, step index, direction) tuple
    """
    tags = [a for a in tagger(step)]
    verb = [t.text for t in tags if t.pos_ == 'VERB' and t.tag_ != 'VBN' and 'ingredient' not in t.text]
    if len(verb) == 0:
        if 'whisk' in step:
            tup = (name, 'whisk', ind, step)
        elif 'beat' in step:
            tup = (name, 'beat', ind, step)
        elif 'combine' in step:
            tup = (name, 'combine', ind, step)
        else:
            tup = (name, 'mix', ind, step)
    else:
        verb = [v for v in verb if v in step.split(tok_name)[0]]
        if len(verb) == 0:
            if 'whisk' in step:
                tup = (name, 'whisk', ind, step)
            elif 'beat' in step:
                tup = (name, 'beat', ind, step)
            elif 'combine' in step:
                tup = (name, 'combine', ind, step)
            else:
                tup = (name, 'mix', ind, step)
        else:
            tup = (name, verb[-1], ind, step)
    return tup[:2]


def replace_ing(directions, names, token, ind):
    """
    Replace all the ingredients in the directions by a token (that will hopefully never be tagged as
    a verb)
    :param directions: the directions containing the ingredients that should be replaced
    :param names: the names of the ingredients
    :param token: the token that the ingredients will be changed into
    :param ind: the index of the direction to be changed. If ind is none, all directions will be iterated over
    :return: the directions with the replaced ingredients
    """
    d = []
    all_steps = False
    if ind is None:
        all_steps = True
    rep = np.ones(len(names))  # the number of replaces that can be made for any ingredient
    for j, step in enumerate(directions):
        stripped_step = step
        if j == ind or all_steps:
            for i, n in enumerate(names):
                if len(n) > 0 and rep[i] == 1 and n in step:
                    rep[i] = 0
                    stripped_step = stripped_step.replace(n, token + ' ')
        d.append(stripped_step)
    return d


def find_cooking_devices(directions):
    """
    Find cooking devices in the directions
    :param directions: the directions for the recipe where there are, hopefully, some cooking
            devices
    :return: tuples of the (<direction index>, <device>, <action>) for each cooking device found
    """
    len_re = '(\d+)\s*(m|min|mins|minutes|hour|hours)(\.|\s|\,)'
    temp_re = '(at |to )(\d+) (degrees )?(C|F|c|f)'
    tups = []
    added_devices = set()
    for i, d in enumerate(directions[1:]):
        for cd in cooking_devices:
            if cd in d.lower():
                tups.append((cd, d.lower(), i+1))
    ret_tups = []
    for cd, d, ind in tups:
        length = re.findall(len_re, d)
        if len(length) > 0:
            length = length[0][:2]
        else:
            length = ''
        if cd == 'oven' or cd == 'bake':
            obj = 'oven'
            act = 'bake'
            deg = ' '
            for step in directions:
                step = step.lower()
                deg = re.findall(temp_re, step)
                if len(deg) > 0:
                    deg = list(deg[0])
                    if deg[3].lower() == 'f':
                        deg[3] = 'C'
                        deg[1] = int(np.round((float(deg[1]) - 32) * 5 / 9, -1))
                    deg = ' at ' + str(deg[1]) + ' ' + deg[3] + ' '
                    break
            if len(deg) == 0:
                deg = ' '
            act += deg
        elif cd == 'refrigerate' or cd == 'refrigerator' or cd == 'fridge':
            obj = 'refrigerator'
            act = 'refrigerate '
        elif cd == 'cool':
            obj = 'cool down'
            act = 'cool '
        else:
            obj = 'freezer'
            act = 'freeze '
        act += ('for ' if len(length) > 0 else '') + ' '.join(length)
        ret_tups.append((ind, obj, act))
        added_devices.add(obj)
    for cd in added_devices:
        occurences = [t for t in ret_tups if t[1] == cd]
        for occ in occurences[:-1]:
            ret_tups.remove(occ)
    return ret_tups


def merge_cooking_devices(cd_tup, ret_list, ret_inds):
    """
    Merge cooking devices to the return list of ingredients
    :param cd_tup: the cooking device tuples list
    :param ret_list: the list of ingredient tuples that are normally returned
    :param ret_inds: the original indices of the ingredients, ordered by their new placements
    :return: the update return list with all of the cooking devices that were found
    """
    inds = np.array([a[0] for a in ret_list])
    for tup in cd_tup:
        if tup[0] not in inds and tup[0] > inds[-1]:
            ret_list.append([tup[0], [(tup[1], tup[2])]])
            ret_inds.append([-1])
            inds = np.array([a[0] for a in ret_list])
        elif tup[0] not in inds:
            add_ind = np.where(inds >= tup[0])[0][0]
            ret_list = ret_list[:add_ind] + [[tup[0], [(tup[1], tup[2])]]] + ret_list[add_ind:]
            ret_inds = ret_inds[:add_ind] + [[-1]] + ret_inds[add_ind:]
            inds = np.array([a[0] for a in ret_list])
        else:
            add_ind = np.where(inds >= tup[0])[0][0]
            ret_list[add_ind][1].append((tup[1], tup[2]))
            ret_inds[add_ind].append(-1)
    return ret_list, ret_inds


def find_verb_tuples(directions, ingredients):
    """
    Find the tuples of ingredients and actions used in the directions
    :param directions: the recipe's directions
    :param ingredients: the ingredients that are used in the recipe
    :return: a list of lists for each step with and ingredient in of tuples of
             (<ingredient name, verb, direction index, full direction>)
    """
    tok = 'ingredient'
    matches = []
    names = []
    nums = []
    inds = []
    d = directions
    d = replace_ing(d, ['grease and flour'], 'grease', None)
    # Find best matches for ingredients in the directions
    for i, ingredient in enumerate(ingredients):
        # ing = nltk.word_tokenize(ingredient)
        ing_match = find_correlations(ingredient, d)
        matches.append(ing_match)
        hits = [a[0] for a in ing_match]
        ind = np.argmax(hits)
        inds.append(ind)
        names.append(ing_match[ind][1])
        nums.append(i)
        d = replace_ing(d, [ing_match[ind][1]], tok + str(i), ind)

    # Sort the names of the ingredients by the step that they appear in
    sorted_indices = np.argsort(inds)
    names = [names[i] for i in sorted_indices]
    nums = [nums[i] for i in sorted_indices]
    inds = [inds[i] for i in sorted_indices]

    unique_inds = np.unique(inds)
    ret_list = [[i, []] for i in unique_inds]
    ret_inds = [[] for _ in unique_inds]
    # Replace the ingredients in the direction by a token
    # d = replace_ing(directions, names, tok)

    # Find the tuples corresponding to each ingredient in the directions
    indices = [a[0] for a in ret_list]
    for i, ind in enumerate(inds):
        list_ind = indices.index(ind)
        name = names[i]
        step = d[ind]
        tok_name = tok + str(nums[i])
        tup = create_tuple(ind, name, step, tok_name)
        ret_list[list_ind][1].append(tup)
        ret_inds[list_ind].append(sorted_indices[i])

    for i, val in enumerate(ret_list):
        if len(val[1]) == 0:
            ret_list.pop(i)
    cd = find_cooking_devices(directions)
    ret_list, ret_inds = merge_cooking_devices(cd, ret_list, ret_inds)
    return ret_list, ret_inds


