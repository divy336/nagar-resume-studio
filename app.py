from flask import Flask,redirect,url_for,session,render_template
from auth.routes import auth
from resume.detail import resume
from admin.routes import admin
app=Flask(__name__)
app.secret_key="register_form"

app.register_blueprint(auth)
app.register_blueprint(resume)
app.register_blueprint(admin)
if __name__=='__main__':
    app.run(host="0.0.0.0",debug=True,port=5000)