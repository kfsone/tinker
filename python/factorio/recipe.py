"""
Factorio's recipe tree is written in Lua, we want it in Python.
"""

import glob
import json
import logging
import os

from slpp import slpp

# Subdirectory within Factorio where we expect to find recipe files.
RECIPE_LOCATION = os.path.join("data", "base", "prototypes", "recipe")

# What we expect scripts to begin with.
RECIPE_PREFIX   = "data:extend("
# What we expect scripts to end with.
RECIPE_SUFFIX   = ")"


class ParseError(RuntimeError):
    pass


def load_file_recipes(fh, enabled_only=False, expensive=False):
    """
    Load all the recipes from a given file handle.
    
    :param enabled_only: Set True to limit to only enabled recipes.
    :param expensive: Set True to use 'expensive' configurations.
    :return: dict(name -> {recipe})
    """

    logging.info("Loading recipes from %s", fh.name)
    
    lua_text = fh.read().strip()
    logging.debug("Loaded %d bytes", len(lua_text))

    # Strip the non-table wrapper.
    if not lua_text.startswith(RECIPE_PREFIX) or not lua_text.endswith(RECIPE_SUFFIX):
        logging.warn("%s does not appear to be a recipe definition file.", fh.name)
        return {}

    lua_table = lua_text[len(RECIPE_PREFIX):-len(RECIPE_SUFFIX)].strip()

    definitions = {}
    for table in slpp.decode(lua_table):

        # Only handle 'recipe's.
        if table.get('type') != "recipe":
            logging.debug("Ignoring: %s", table)
            continue
        del table['type']

        name = table.get('name')
        if not name:
            logging.warn("Malfored entry: %s", table)
            continue

        # Check if we're skipping disabled recipes.
        if enabled_only and table.get('enabled', True) is False:
            logging.debug("Skipping %s: disabled" % name)
            continue

        # Make sure it has a unique name.
        if name in definitions:
            raise ParseError("%s: Duplicated recipe: %s" % (fh.name, name))

        if 'ingredients' not in table:
            if expensive:
                ingredients = table.pop('expensive')
            else:
                ingredients = table.pop('normal')
            table['ingredients'] = ingredients

        logging.debug("\"%s\": %s", name, json.dumps(table, sort_keys=True))

        definitions[name] = table

    return definitions


def load_all_recipes(factorio_path):
    
    if not os.access(factorio_path, os.R_OK):
        raise ValueError("%s: No access or no such folder." % factorio_path)
    
    # Iterate across all the files we find in the RECIPE_LOCATION.
    recipes_path = os.path.join(factorio_path, RECIPE_LOCATION)
    logging.debug("recipes path: %s", recipes_path)
    if not os.access(recipes_path, os.R_OK):
        raise ValueError("%s: Missing recipe folder or no access: %s" % (factorio_path, recipes_path))

    lua_files = glob.glob(os.path.join(recipes_path, "*.lua"))
    if not lua_files:
        raise IOError("%s: no .lua files present" % (recipes_path))

    # Strip down to just the filename.
    lua_files = [os.path.basename(filename) for filename in lua_files]
    logging.debug("lua files: %s" % (", ".join(lua_files)))

    recipes = dict()
    for filename in lua_files:

        with open(os.path.join(recipes_path, filename), 'r') as fh:

            # Get a dictionary of the recipes from this file.
            new_recipes = load_file_recipes(fh)
            if not new_recipes:
                continue

            logging.debug("Loaded %d recipes: %s", len(new_recipes), ",".join(new_recipes.keys()))
            # Check for any duplicates.
            new_keys, old_keys = frozenset(new_recipes.keys()), frozenset(recipes.keys())
            for dupe in new_keys.intersection(old_keys):
                logging.warn("'%s' redefined in %s", dupe, filename)

            # Add the recipes to the main dictionary.
            recipes.update(new_recipes)

    logging.debug("Loaded %d recipes total" % len(recipes))

    return recipes

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print(json.dumps(load_all_recipes(r"C:\\Program Files (x86)\\steam\\steamapps\common\Factorio"), indent=4))
