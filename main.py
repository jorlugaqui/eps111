import json
import logging
import sys
import urllib.request
import urllib.parse
import urllib.error

from flask import Flask

COCKTAIL_API_HOST = 'https://www.thecocktaildb.com/api/json/v1/1/search.php'
LOGGING_FORMAT = '%(asctime)s %(levelname)s %(name)s %(pathname)s %(message)s'

# Handler configuration
formatter = logging.Formatter(LOGGING_FORMAT)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


app = Flask(__name__)


def get_cocktail_data(cocktail: str) -> dict:
    query = urllib.parse.urlencode({'s': cocktail})
    response = urllib.request.urlopen(f'{COCKTAIL_API_HOST}?{query}')
    data = json.loads(response.read())
    return data


def get_ingredients(data: dict) -> list:
    index = 1
    ingredients = []
    ingredient = data.get('drinks')[0].get(f'strIngredient{index}')

    while ingredient is not None:
        ingredients.append(ingredient)
        index = index + 1
        ingredient = data.get('drinks')[0].get(f'strIngredient{index}')

    return ingredients


def get_instructions(data: dict) -> str:
    return data.get('drinks')[0].get('strInstructions')


@app.route('/cocktail/<string:cocktail>')
def get_cocktail(cocktail: str) -> str:
    error = None
    try:
        logger.info(f'Fetching cocktail {cocktail} information')
        data = get_cocktail_data(cocktail)
        return {
            'error': None,
            'instructions': get_instructions(data),
            'ingredients': get_ingredients(data)
        }, 200
    except urllib.error.HTTPError as e:
        logger.error(
            'There was an HTTP error while getting cocktail information'
        )
        logger.error(e, exc_info=True)
        error = e
    except urllib.error.URLError as e:
        logger.error('Looks like the ULR is malformed')
        logger.error(e, exc_info=True)
        error = e
    except Exception as e:
        logger.error('Internal server error')
        logger.error(e, exc_info=True)
        error = e
    finally:
        if error is not None:
            return {
                'error': error,
                'instructions': None,
                'ingredients': []
            }, 500


if __name__ == '__main__':
    app.run()
