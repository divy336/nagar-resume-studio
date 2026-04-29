from flask import Flask
from auth.routes import auth
from resume.detail import resume
from admin.routes import admin
import os

app = Flask(__name__)
app.secret_key = "register_form"

app.register_blueprint(auth)
app.register_blueprint(resume)
app.register_blueprint(admin)