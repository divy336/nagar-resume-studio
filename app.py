from flask import Flask
from auth.routes import auth
from resume.detail import resume
from admin.routes import admin
import os

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "register_form")

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(resume)
app.register_blueprint(admin)

if __name__ == "__main__":
   
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)