import os
from flask import Flask , render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
jwt = JWTManager()
migrate = Migrate()
csrf = CSRFProtect()  # Enable CSRF protection

def create_app():
    app = Flask(__name__, static_folder='static')

    # Set secret keys and database URI
    app.config['SECRET_KEY'] = 'Super-Strong-Key'

    database_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db', 'retail_cosmo.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'another-secret-key'
    app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF protection for forms

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate
    csrf.init_app(app)  # Enable CSRF protection

    # Load user
    from models import User  # Absolute import
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/", methods=['GET'])
    def root():
        return render_template('landingPage.html')

    # Register routes
    from auth import auth_bp  
    from usermanagment import usermanagment_bp
    from menumanagment import menu_bp
    from billing import billing_bp,fromjson_filter
    from crm import crm_bp
    from groups import groups_bp
    from employees import employees_bp
    from attendance import attendance_bp
    from inventory import inventory_bp
    from purchases import purchases_bp
    from ordermanagement import ordermanagement
     # Register the fromjson filter globally
    app.template_filter('fromjson')(fromjson_filter)

    app.register_blueprint(auth_bp)
    app.register_blueprint(usermanagment_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(ordermanagement)

    #No Use of the WTF CSRF for Form
    csrf.exempt(usermanagment_bp)
    csrf.exempt(menu_bp)
    csrf.exempt(billing_bp)
    csrf.exempt(crm_bp)
    csrf.exempt(groups_bp)
    csrf.exempt(employees_bp)
    csrf.exempt(attendance_bp)
    csrf.exempt(inventory_bp)
    csrf.exempt(purchases_bp)
    csrf.exempt(ordermanagement)

    return app
