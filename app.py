from flask import Flask
from datetime import timedelta
from auth.routes import auth
from resume.detail import resume
from admin.routes import admin
import os

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "resume_studio_secret_key")

app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

app.register_blueprint(auth)
app.register_blueprint(resume)
app.register_blueprint(admin)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)