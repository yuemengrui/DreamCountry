from flask import Blueprint

index_blu = Blueprint('index', __name__
                      # static_folder='static/news',
                      # static_url_path='/static/news',
                      # template_folder='templates'
                      )

from . import views