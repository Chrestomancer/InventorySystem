# Import route blueprints to make them available when importing from the package
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.inventory import inventory_bp
from app.routes.sales import sales_bp
from app.routes.reports import reports_bp
