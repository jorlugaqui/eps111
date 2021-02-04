import json
import logging
import sys
import urllib.request
import urllib.parse
import urllib.error

from werkzeug.useragents import UserAgent

import logstash
from flask import Flask, request


COCKTAIL_API_HOST = 'https://www.thecocktaildb.com/api/json/v1/1/search.php'
LOGGING_FORMAT = '%(asctime)s %(levelname)s %(name)s %(pathname)s %(message)s'

formatter = logging.Formatter(LOGGING_FORMAT)

# Console handler configuration
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Logstash handlar configuration
logstash_handler = logstash.TCPLogstashHandler('localhost', 5044, version=1)
logstash_handler.setFormatter(formatter)

# Logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(logstash_handler)

app = Flask(__name__)


# Taken from
# https://docs.python.org/3/howto/logging-cookbook.html#implementing-structured-logging

class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Exception):
            return o.args[0]
        if isinstance(o, UserAgent):
            return o.string
        return super(Encoder, self).default(o)


class StructuredMessage:
    def __init__(self, /, **kwargs):
        self.kwargs = kwargs

    def __str__(self):
        s = Encoder().encode(self.kwargs)
        return '%s' % (json.dumps(s))


_ = StructuredMessage   # optional, to improve readability


@app.after_request
def after_request(response):
    logger.info(_(
        remote_addr=request.remote_addr,
        method=request.method,
        path=request.path,
        schema=request.scheme,
        status=response.status,
        content_length=response.content_length,
        referrer=request.referrer,
        user_agent=request.user_agent
    ))
    return response


def get_cocktail_data(cocktail: str) -> dict:
    query = urllib.parse.urlencode({'s': cocktail})
    response = urllib.request.urlopen(f'{COCKTAIL_API_HOST}?{query}')
    data = json.loads(response.read())
    return data


def get_ingredients(data: dict) -> list:
    index: int = 1
    ingredients = []
    ingredient: str = data.get('drinks')[0].get(f'strIngredient{index}')

    while ingredient is not None:
        ingredients.append(ingredient)
        index = index + 1
        ingredient = data.get('drinks')[0].get(f'strIngredient{index}')

    return ingredients


def get_instructions(data: dict) -> str:
    return data.get('drinks')[0].get('strInstructions')


@app.route('/cocktail/<string:cocktail>')
def get_cocktail(cocktail: str) -> tuple:
    error: str = ''
    try:
        logger.info(_(message=f'Fetching cocktail {cocktail} information'))
        data = get_cocktail_data(cocktail)
        return {
            'error': None,
            'instructions': get_instructions(data),
            'ingredients': get_ingredients(data)
        }, 200
    except (urllib.error.HTTPError, urllib.error.URLError):
        error = 'There was an error while fetching the cocktail information'
        logger.error(_(message=error), exc_info=True)
    except Exception:
        error = 'Internal Server Error'
        logger.error(_(message=error), exc_info=True)
    finally:
        if error:
            return {
                'error': error,
                'instructions': None,
                'ingredients': []
            }, 500


if __name__ == '__main__':
    app.run()
