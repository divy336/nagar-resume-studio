from flask import Flask,url_for,render_template,request,redirect,session
from resume import resume
import mysql.connector
import os
from werkzeug.utils import secure_filename
import pdfkit
from flask import Response

import json

db=mysql.connector.connect(
    host="localhost",
    user="root",
    password="nagar@73",
    database="flask"
)
cursor = db.cursor(dictionary=True)


UPLOAD_FOLDER = "static/uploads"
UPLOAD_EDU_DATA="static/edu"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

import json
@resume.route("/")
def main():
    pass
    return redirect(url_for("resume.dashbord"))
@resume.route("/dashbord")
def dashbord():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    cur = db.cursor(dictionary=True)
    resumes = []

    # IT RESUMES
    cur.execute("""
        SELECT id, resume_data, created_at
        FROM user_resume
        WHERE user_id=%s
    """, (user_id,))
    
    for row in cur.fetchall():

        r = json.loads(row["resume_data"]) if isinstance(row["resume_data"], str) else row["resume_data"]

        full_name = (
            (r.get("first_name", "") + " " + r.get("last_name", "")).strip()
            or r.get("name")
            or "No Name"
        )

        resumes.append({
            "id": row["id"],
            "name": full_name,
            "type": "it",
            "updated": row["created_at"]
        })

    # OTHER RESUMES
    cur.execute("""
        SELECT id, resume_data, created_at
        FROM other_resume
        WHERE user_id=%s
    """, (user_id,))
    
    for row in cur.fetchall():

        r = json.loads(row["resume_data"]) if isinstance(row["resume_data"], str) else row["resume_data"]

        full_name = (
            r.get("name")
            or (r.get("first_name", "") + " " + r.get("last_name", "")).strip()
            or "No Name"
        )

        resumes.append({
            "id": row["id"],
            "name": full_name,
            "type": "other",
            "updated": row["created_at"]
        })

    # 🔥 SORT FINAL MERGED LIST
    resumes.sort(key=lambda x: x["updated"], reverse=True)

    return render_template("dashbord.html", resumes=resumes)
@resume.route("/home", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if request.args.get("type"):
        session["resume_type"] = request.args.get("type") 

    if request.args.get("new") == "1":
        session.pop("resume", None)

    if "resume" not in session:
        session["resume"] = {}

    if request.method == "POST":
        session["resume"]["first_name"] = request.form.get("first_name")
        session["resume"]["last_name"] = request.form.get("last_name")
        session["resume"]["email"] = request.form.get("email")
        session["resume"]["mobile"] = request.form.get("mobile")
        session["resume"]["major"] = request.form.get("major")
        session["resume"]["github"] = request.form.get("github")
        session["resume"]["linkedin"] = request.form.get("linkedin")
        session["resume"]["summary"] = request.form.get("summary")
        
        

        session.modified = True
        next_step = request.form.get("next_step")

        if next_step == "dashboard":
            return redirect(url_for("resume.dashbord"))

        elif next_step == "2":   # Home
            return redirect(url_for("resume.home"))

        elif next_step == "3":   # Language
            return redirect(url_for("resume.languages_images"))

        elif next_step == "4":   # Education
            return redirect(url_for("resume.education"))

        elif next_step == "5":   # Projects
            return redirect(url_for("resume.projects"))

        # default (Next button)
        return redirect(url_for("resume.languages_images"))


        

    return render_template("home.html", resume=session.get("resume", {}), current_step=2 )



@resume.route("/languages_images", methods=["GET", "POST"])
def languages_images():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if "resume" not in session:
        session["resume"] = {}

    if request.method == "POST":

        languages = request.form.get("languages")
        languages_list = languages.split(",") if languages else []
        session["resume"]["languages"] = languages_list

        file = request.files.get("photo")
        if file and allowed_file(file.filename):
            user_id = session["user_id"]
            filename = secure_filename(f"{user_id}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            session["resume"]["photo"] = filename

        session.modified = True
        next_step = request.form.get("next_step")

        if next_step == "dashboard":
            return redirect(url_for("resume.dashbord"))

        elif next_step == "2":   # Home
            return redirect(url_for("resume.home"))

        elif next_step == "3":   # Language
            return redirect(url_for("resume.languages_images"))

        elif next_step == "4":   # Education
            return redirect(url_for("resume.education"))

        elif next_step == "5":   # Projects
            return redirect(url_for("resume.projects"))

        # default (Next button)
        return redirect(url_for("resume.education"))

   
    return render_template("languages_images.html", resume=session.get("resume", {}), current_step=3)


@resume.route("/education", methods=["GET", "POST"])
def education():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    
    if "resume" not in session:
        session["resume"] = {}


    if request.method == "POST":

       

        user_id = session["user_id"]

        education_data = request.form.get("education_data")
        education_list = json.loads(education_data) if education_data else []

        for i, edu in enumerate(education_list):
            file = request.files.get(f"marksheet_{i}")
            filename = None

            if file and allowed_file(file.filename):
                filename = secure_filename(f"{user_id}_{file.filename}")
                file.save(os.path.join(UPLOAD_EDU_DATA, filename))

            edu["marksheet"] = filename

        session["resume"]["education"] = education_list

        session["resume"]["skills"] = request.form.get("skills").split(",")

        session["resume"]["master_languages"] = request.form.get("master_languages").split(",")
        session.modified = True
        next_step = request.form.get("next_step")

        if next_step == "dashboard":
            return redirect(url_for("resume.dashbord"))

        elif next_step == "2":   # Home
            return redirect(url_for("resume.home"))

        elif next_step == "3":   # Language
            return redirect(url_for("resume.languages_images"))

        elif next_step == "4":   # Education
            return redirect(url_for("resume.education"))

        elif next_step == "5":   # Projects
            return redirect(url_for("resume.projects"))

        # default (Next button)
        return redirect(url_for("resume.projects"))

        

    return render_template("education.html",resume=session.get("resume", {}), current_step=4)

@resume.route("/projects", methods=["GET", "POST"])
def projects():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    if "resume" not in session:
        session["resume"] = {}

    resume = session.get("resume", {})
    error = None

    if request.method == "POST":

        # ✅ VALIDATION
        if not resume.get("first_name"):
            error = "⚠ Please complete your resume details before generating Resume."
            return render_template("projects.html", error=error, resume=resume)

        r = session.get("resume", {})

        # ✅ PROJECTS
        projects = []
        names = request.form.getlist("project_name[]")
        descs = request.form.getlist("project_desc[]")
        techs = request.form.getlist("project_tech[]")

        for i in range(len(names)):
            projects.append({
                "name": names[i],
                "description": descs[i],
                "technologies": techs[i]
            })

        # ✅ EXPERIENCE
        experience = []
        roles = request.form.getlist("role[]")
        companies = request.form.getlist("company[]")
        locations = request.form.getlist("location[]")
        durations = request.form.getlist("duration[]")
        work_descs = request.form.getlist("work_desc[]")

        for i in range(len(roles)):
            experience.append({
                "role": roles[i],
                "company": companies[i],
                "location": locations[i],
                "duration": durations[i],
                "description": work_descs[i]
            })

        # ✅ LANGUAGES
        lang_levels = []
        languages = request.form.getlist("language[]")
        levels = request.form.getlist("language_level[]")

        for i in range(len(languages)):
            lang_levels.append({
                "language": languages[i],
                "level": levels[i]
            })

        # ✅ SAVE IN SESSION
        r["projects"] = projects
        r["experience"] = experience
        r["language_levels"] = lang_levels

        session["resume"] = r
        session.modified = True

        # ✅ NAVIGATION (FIXED POSITION)
        next_step = request.form.get("next_step")

        if next_step == "dashboard":
            return redirect(url_for("resume.dashbord"))

        elif next_step == "2":
            return redirect(url_for("resume.home"))

        elif next_step == "3":
            return redirect(url_for("resume.languages_images"))

        elif next_step == "4":
            return redirect(url_for("resume.education"))

        elif next_step == "5":
            return redirect(url_for("resume.projects"))

        # ✅ FINAL SAVE (ONLY WHEN NO NAVIGATION)
        if "edit_id" in session:
            cursor.execute("""
                UPDATE user_resume 
                SET resume_data=%s 
                WHERE id=%s AND user_id=%s
            """, (json.dumps(r), session["edit_id"], user_id))

            session.pop("edit_id", None)

        else:
            cursor.execute("""
                INSERT INTO user_resume (user_id, resume_data)
                VALUES (%s, %s)
            """, (user_id, json.dumps(r)))

        resume_json = json.dumps(r)
        original_id = cursor.lastrowid
        resume_type = "it"   # ✅ FIXED VALUE

        cursor.execute("""
        INSERT INTO all_resume
        (user_id, resume_data, resume_type, original_id, action_type)
        VALUES (%s, %s, %s, %s, %s)
        """, (user_id, resume_json, resume_type, original_id, "created"))

        db.commit()


        return redirect(url_for("resume.resume_type"))

    return render_template(
        "projects.html",
        error=error,
        resume=resume,
        current_step=5   
    )


@resume.route("/resume_type", methods=["GET", "POST"])
def resume_type():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    error = None

    if request.method == "POST":
        resume = session.get("resume")

        if not resume or "first_name" not in resume:
            error = "⚠ Please complete your resume details before generating Resume."
            
        else:
            choice=request.form.get("resume_type")
            
            if choice=="ai":
                return redirect(url_for("resume.ai_resume"))
            
            elif choice=="fancy":
                return redirect(url_for("resume.fancy_resume"))
            elif choice=="professional":
                return redirect(url_for("resume.professional_resume"))
                

    return render_template("resume_type.html", error=error,)


@resume.route("/ai_resume")
def ai_resume():
    if "user_id" not in session: 
        return redirect(url_for("auth.login"))
    
    resume_data = session["resume"]

    

    return render_template("fancy1.html",resume=resume_data)

@resume.route("/fancy_resume")
def fancy_resume():
    if "resume" not in session:
        return redirect(url_for("resume.resume_type"))
    return render_template("fancy_resume.html", resume=session["resume"])


@resume.route("/professional_resume")
def professional_resume():
    if "resume" not in session:
        return redirect(url_for("resume.resume_type"))
    return render_template("professional_resume.html", resume=session["resume"])

    


@resume.route("/api/preview/<int:id>")
def preview_api(id):
    if "user_id" not in session:
        return {"error": "login required"}

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_resume WHERE id=%s", (id,))
    data = cursor.fetchone()

    if not data:
        return {"error": "not found"}

    resume = json.loads(data["resume_data"]) if isinstance(data["resume_data"], str) else data["resume_data"]

    return {"ok": True, "resume": resume}

@resume.route("/edit/<int:id>")
def edit_resume(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_resume WHERE id=%s", (id,))
    row = cursor.fetchone()

    if not row:
        return "Resume not found"

    # convert JSON → dict
    data = row["resume_data"]
    if isinstance(data, str):
        data = json.loads(data)

    # store in session
    session["resume"] = data
    session["edit_id"] = id   
    session.modified = True

    return redirect(url_for("resume.home"))