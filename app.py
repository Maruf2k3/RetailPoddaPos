from app_init import create_app

# Initialize the app
app = create_app()

if __name__ == "__main__":
    # Run the app with specified host and port
    app.run(app , debug=True, host='0.0.0.0', port=5000)
