from flask import render_template

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 errors."""
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 errors."""
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 errors."""
        return render_template('errors/400.html'), 400
