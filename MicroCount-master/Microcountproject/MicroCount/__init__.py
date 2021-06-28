import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
#from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class


app = Flask(__name__, template_folder='microcounttemplates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///microsite.db'
app.config['SECRET_KEY'] = '6811628bb0b13ce0c676dfde280ba245'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
mail = Mail(app)
''''basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOADED_SAMPLES_DEST'] = os.path.join(basedir, 'static/sampleplates')

samples = UploadSet('samples', IMAGES)
configure_uploads(app, samples)
patch_request_class(app)'''

from MicroCount import routes

