"""
Factorio's recipe tree is written in Lua, we want it in Python.
"""

import collections
import glob
import json
import logging
import os

from slpp import slpp

# Subdirectory within Factorio where we expect to find recipe files.
RECIPE_LOCATION = os.path.join("data", "base", "prototypes", "recipe")

DEFAULT_PATH="C:\\Program Files (x86)\\steam\\steamapps\\common\\Factorio"

# What we expect scripts to begin with.
RECIPE_PREFIX   = "data:extend("
# What we expect scripts to end with.
RECIPE_SUFFIX   = ")"

logger = logging.getLogger("recipe")
logger.setLevel(logging.DEBUG)


class ParseError(RuntimeError):
    pass


def load_file_recipes(fh, enabled_only=False, expensive=False, logger=logger):
    """
    Load all the recipes from a given file handle.
    
    :param enabled_only: Set True to limit to only enabled recipes.
    :param expensive: Set True to use 'expensive' configurations.
    :return: dict(name -> {recipe})
    """

    logger.info("Loading recipes from %s", fh.name)
    
    lua_text = fh.read().strip()
    logger.debug("Loaded %d bytes", len(lua_text))

    # Strip the non-table wrapper.
    if not lua_text.startswith(RECIPE_PREFIX) or not lua_text.endswith(RECIPE_SUFFIX):
        logger.warn("%s does not appear to be a recipe definition file.", fh.name)
        return {}

    lua_table = lua_text[len(RECIPE_PREFIX):-len(RECIPE_SUFFIX)].strip()

    definitions = {}
    for table in slpp.decode(lua_table):

        own_version = {}

        # Only handle 'recipe's.
        if table.get('type') != "recipe":
            logger.debug("Ignoring: %s", table)
            continue

        name = table.get('name').lower()
        if not name:
            logger.warn("Malformed entry: %s", table)
            continue
        own_version['name'] = name

        # Check if we're skipping disabled recipes.
        if enabled_only:
            if table.get('enabled', True) is False:
                logger.debug("Skipping %s: disabled" % name)
                continue
            own_version['enabled'] = table['enabled']

        # Make sure it has a unique name.
        if name in definitions:
            raise ParseError("%s: Duplicated recipe: %s" % (fh.name, name))

        inset = table.get('normal')
        if expensive:
            inset = table.get('expensive', inset)
        if inset:
            if enabled_only and inset.get('enabled', True) is False:
                logger.debug("Skipping %s: inset dsabled" % name)
                continue
            if 'ingredients' in inset:
                table = inset

        ingredients = table.get('ingredients')
        if not ingredients:
            logger.warn("Entry with no ingredients: %s", table)
            continue
        ingredients = tuple(tuple(e) for e in ingredients)
        own_version['ingredients'] = ingredients

        if 'energy_required' in table:
            own_version['energy_required'] = table['energy_required']

        logger.debug("\"%s\": %s", name, json.dumps(own_version, sort_keys=True))

        definitions[name] = own_version

    return definitions


def load_all_recipes(factorio_path, logger=logger):
    
    if not os.access(factorio_path, os.R_OK):
        raise ValueError("%s: No access or no such folder." % factorio_path)
    
    # Iterate across all the files we find in the RECIPE_LOCATION.
    recipes_path = os.path.join(factorio_path, RECIPE_LOCATION)
    logger.debug("recipes path: %s", recipes_path)
    if not os.access(recipes_path, os.R_OK):
        raise ValueError("%s: Missing recipe folder or no access: %s" % (factorio_path, recipes_path))

    lua_files = glob.glob(os.path.join(recipes_path, "*.lua"))
    if not lua_files:
        raise IOError("%s: no .lua files present" % (recipes_path))

    # Strip down to just the filename.
    lua_files = [os.path.basename(filename) for filename in lua_files]
    logger.debug("lua files: %s" % (", ".join(lua_files)))

    recipes = dict()
    for filename in lua_files:

        with open(os.path.join(recipes_path, filename), 'r') as fh:

            # Get a dictionary of the recipes from this file.
            new_recipes = load_file_recipes(fh)
            if not new_recipes:
                continue

            logger.debug("Loaded %d recipes: %s", len(new_recipes), ",".join(new_recipes.keys()))
            # Check for any duplicates.
            new_keys, old_keys = frozenset(new_recipes.keys()), frozenset(recipes.keys())
            for dupe in new_keys.intersection(old_keys):
                logger.warn("'%s' redefined in %s", dupe, filename)

            # Add the recipes to the main dictionary.
            recipes.update(new_recipes)

    logger.debug("Loaded %d recipes total" % len(recipes))

    return recipes


def dump_requirements(recipes, requests):

    requests = set(requests)
    requirements = collections.defaultdict(int)
    for request in requests:
        recipe = recipes.get(request.lower())
        if not recipe:
            raise ValueError("Unknown recipe: " + request)
        ingredients = list(recipe['ingredients'])
        while ingredients:
            ingredient, quantity = ingredients.pop(0)
            ingredient_recipe = recipes.get(ingredient)
            if ingredient_recipe:
                for sub_ingredient, sub_quantity in ingredient_recipe['ingredients']:
                    ingredients.append((sub_ingredient, sub_quantity * quantity))
            requirements[ingredient] += quantity

    for item, quantity in requirements.items():
        print("%5d %s" % (quantity, item))


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser("Recipe translator")
    parser.add_argument("--verbose", "-v", help="Increase verbosity.", default=0, action="count")
    parser.add_argument("--json", help="Write json dump", required=False, type=argparse.FileType('w'))
    parser.add_argument("--path", help="Path to the Factorio folder", default=DEFAULT_PATH, type=str)
    parser.add_argument("--make", help="Add an item to the request list", action="append")

    args = parser.parse_args(sys.argv[1:])

    if not os.path.exists(args.path):
        logger.error("No such path: %s", args.path)
        sys.exit(-1)

    if args.verbose == 0:
        logger.setLevel(logging.WARN)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose >= 2:
        logger.setLevel(logging.DEBUG)

    recipes = load_all_recipes(args.path)

    if args.json:
        args.json.write(json.dumps(recipes, indent=4))

    if args.make:
        dump_requirements(recipes, args.make)
