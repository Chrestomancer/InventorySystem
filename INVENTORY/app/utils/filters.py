from datetime import datetime
from markupsafe import Markup

def register_filters(app):
    """Register custom template filters for the application."""
    
    @app.template_filter('min')
    def min_filter(value, other):
        """Return the minimum of value and other."""
        return min(value, other)
    
    @app.template_filter('max')
    def max_filter(value, other):
        """Return the maximum of value and other."""
        return max(value, other)
    
    @app.template_filter('currency')
    def currency_filter(value):
        """Format a value as currency."""
        if value is None:
            return '$0.00'
        return '${:,.2f}'.format(value)
    
    @app.template_filter('datetime')
    def datetime_filter(value, format='%Y-%m-%d %H:%M'):
        """Format a datetime object."""
        if value is None:
            return ''
        return value.strftime(format)
    
    @app.template_filter('date')
    def date_filter(value, format='%Y-%m-%d'):
        """Format a date object."""
        if value is None:
            return ''
        return value.strftime(format)
    
    @app.template_filter('time_ago')
    def time_ago_filter(value):
        """Format a datetime as time ago."""
        if value is None:
            return ''
        
        now = datetime.utcnow()
        diff = now - value
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    @app.template_filter('nl2br')
    def nl2br_filter(value):
        """Convert newlines to <br> tags."""
        if value is None:
            return ''
        # Escape HTML first to prevent XSS, then replace newlines
        escaped = Markup.escape(value)
        return Markup(escaped.replace('\n', '<br>'))
    
    @app.template_filter('truncate_words')
    def truncate_words_filter(value, length=30):
        """Truncate text to a certain number of words."""
        if value is None:
            return ''
        
        words = value.split()
        if len(words) <= length:
            return value
        
        return ' '.join(words[:length]) + '...'
