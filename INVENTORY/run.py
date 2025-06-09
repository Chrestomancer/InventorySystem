from app import create_app
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app()

if __name__ == '__main__':
    # Disable auto-reload to prevent issues with OCR libraries
    app.run(debug=True, use_reloader=False)
