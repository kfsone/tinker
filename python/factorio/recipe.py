"""
Factorio's recipe tree is written in Lua, we want it in Python.
"""

import argparse
import collections
import glob
import json
import logging
import os
import sys

try:
    from .slpp import slpp
except (ValueError, ImportError):
    from slpp import slpp

# Subdirectory within Factorio where we expect to find recipe files.
RECIPE_LOCATION = os.path.join("data", "base", "prototypes", "recipe")

if sys.platform == 'darwin':
    DEFAULT_PATH = os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Factorio/factorio.app/Contents")
else:  ###TODO: Linux, kthxbai
    DEFAULT_PATH="C:\\Program Files (x86)\\steam\\steamapps\\common\\Factorio"

# What we expect scripts to begin with.
RECIPE_PREFIX   = "data:extend("
# What we expect scripts to end with.
RECIPE_SUFFIX   = ")"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("recipe")


class ParseError(RuntimeError):
    pass


class Resource(object):
    """ Raw or manufactured item that can be constructed or used to construct. """

    def __init__(self, name, recipe):
        self.name = name
        self.recipe = recipe
        self.inputs = {}
        self.outputs = {}

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.name)

    def __hash__(self):
        return hash(self.name)


class RawResource(Resource):
    def __init__(self, name):
        super().__init__(name, None)


class Manufactured(Resource):
    def __init__(self, name, recipe):
        super().__init__(name, recipe)


class Production(object):

    def __init__(self, resource_in, quantity, manufactured):
        assert isinstance(resource_in,  Resource)
        assert isinstance(manufactured, Manufactured)

        self.resource_in = resource_in
        self.quantity = quantity
        self.manufactured = manufactured

        assert manufactured.name not in resource_in.inputs
        assert manufactured.name not in resource_in.outputs
        assert resource_in.name not in manufactured.inputs
        assert resource_in.name not in manufactured.outputs

        resource_in.outputs[manufactured.name] = self
        manufactured.inputs[resource_in.name] = self

    def __repr__(self):
        return "Production('%s', %d, '%s')" % (self.resource_in.name, self.quantity, self.manufactured.name)


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
        logger.warning("%s does not appear to be a recipe definition file.", fh.name)
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
            logger.warning("Malformed entry: %s", table)
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
            logger.warning("Entry with no ingredients: %s", table)
            continue
        own_version['ingredients'] = {}
        for entry in ingredients:
            if isinstance(entry, (tuple, list)):
                assert len(entry) == 2
                assert isinstance(entry[1], int)
                own_version['ingredients'][entry[0]] = entry[1]
            else:
                assert isinstance(entry, dict)
                assert len(entry) == 3
                own_version['ingredients'][entry['name']] = int(entry['amount'])

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
                logger.warning("'%s' redefined in %s", dupe, filename)

            # Add the recipes to the main dictionary.
            recipes.update(new_recipes)

    logger.debug("Loaded %d recipes total" % len(recipes))

    return recipes


def dump_requirements(recipes, requests):

    requests = set(r.lower() for r in requests)
    requirements = collections.defaultdict(int)
    uses = collections.defaultdict(set)

    for request in requests:
        recipe = recipes.get(request)
        if not recipe:
            raise ValueError("Unknown recipe: " + request)

        ingredients = list(((ing, qty), request) for (ing, qty) in recipe['ingredients'].items())

        while ingredients:
            (ingredient, quantity), use = ingredients.pop(0)
            uses[ingredient].add(use)
            ingredient_recipe = recipes.get(ingredient)
            if ingredient_recipe:
                for (sub_ingredient, sub_quantity) in ingredient_recipe['ingredients'].items():
                    ingredients.append(((sub_ingredient, sub_quantity * quantity), ingredient))
            requirements[ingredient] += quantity

    keys = list(requirements.keys())
    keys.sort(key=lambda k: k)
    keys.sort(key=lambda k: requirements[k], reverse=True)
    keys.sort(key=lambda k: len(uses[k]), reverse=True)

    print("%-5s %-5s %-40s %s" % ("Qty", "#Use", "Item", "Uses"))
    for item in keys:
        print("%5d %5d %-40s %s" % (requirements[item], len(uses[item]), item, ', '.join(uses[item])))


def build_graph(recipes, goals):
    """ Builds a graph of productions to produce a set of goals. """

    resources = {}
    productions = dict()
    produces = set()
    consumes = set()

    demands = [(goal, 1) for goal in goals]
    while demands:

        product_name, quantity = demands.pop()

        produces.add(product_name)
        product_recipe = recipes[product_name]
        product_resource = resources.get(product_name, Manufactured(product_name, product_recipe))

        for ing_name, ing_quantity in product_recipe['ingredients'].items():

            consumes.add(ing_name)

            ing_resource = resources.get(ing_name)
            if not ing_resource:
                ing_recipe = recipes.get(ing_name)
                if ing_recipe:
                    ing_resource = Manufactured(ing_name, ing_recipe)
                else:
                    ing_resource = RawResource(ing_name)
                resources[ing_name] = ing_resource

            if (ing_resource, product_resource) not in productions:
                productions[ing_resource, product_resource] = Production(ing_resource, ing_quantity, product_resource)

            if not isinstance(ing_resource, RawResource):
                demands.append((ing_name, quantity * ing_quantity))

    outputs = frozenset((produces - consumes) | set(goals))
    assert outputs == set(goals)
    inputs = frozenset(consumes - produces)

    ready = set(resources[k] for k in inputs)
    rounds = []

    while True:
        outputs = collections.defaultdict(set)
        for pin, pout in productions:
            if pin not in ready:
                continue
            if pout in ready:
                continue
            if not all(ing.resource_in in ready for ing in pout.inputs.values()):
                continue
            outputs[pout].add(pin)
        if not outputs:
            break
        rounds.append(dict(outputs))
        ready.update(outputs.keys())

    return {
        'inputs': inputs,
        'outputs': outputs,
        'rounds': rounds,
        'resources': resources,
        'productions': productions,
    }


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Recipe translator")
    parser.add_argument("--verbose", "-v", help="Increase verbosity.", default=0, action="count")
    parser.add_argument("--json", help="Write json dump", required=False, type=str)
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

    if args.path.endswith('.json'):
        if args.json:
            raise RuntimeError("--json is not compatbile with specifying a .json input source")
        with open(args.path, 'r') as fh:
            recipes = json.loads(fh.read())
    else:
        recipes = load_all_recipes(args.path)

    if args.json:
        with open(args.json, 'w') as fh:
            fh.write(json.dumps(recipes, indent=4))

    if args.make:
        project = dump_requirements(recipes, args.make)

