from flask import Flask, redirect, url_for, session, render_template
from auth.routes import auth
from resume.detail import resume
from admin.routes import admin
import os

app = Flask(__name__)
app.secret_key = "register_form"

app.register_blueprint(auth)
app.register_blueprint(resume)
app.register_blueprint(admin)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)