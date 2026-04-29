
import os
from auth import routes
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, session,flash,jsonify
from resume import resume
import mysql.connector
import json



resume_type = "other"
db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT", 3306))
)

cur = db.cursor(dictionary=True)

@resume.route("/first_page", methods=["GET", "POST"])
def first_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.args.get("new") == "1":
        session.pop("resume", None)
        session.pop("edit_id", None)
        session.pop("edit_type", None)
        session.pop("group", None)

    if request.method == 'POST':

        linkedin_user = request.form.get("linkedin", "").strip()

        if linkedin_user:
            if "linkedin.com" in linkedin_user:
                full_linkedin = linkedin_user
            else:
                full_linkedin = f"https://www.linkedin.com/in/{linkedin_user}"
        else:
            full_linkedin = ""

        # ✅ KEEP OLD DATA
        resume_data = session.get("resume", {})

        # ✅ UPDATE ONLY THIS PAGE
        resume_data.update({
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "career": request.form.get("career"),
             "field_name": request.form.get("field_name"),
            "linkedin": full_linkedin,
            "address": request.form.get("address"),
            "objective": request.form.get("objective")
        })

        session["resume"] = resume_data
        session["group"] = request.form.get("career")
        session.modified = True

        # 🔥 ADD THIS (IMPORTANT)
        next_step = request.form.get("next_step")

        if next_step == "1":
            return redirect(url_for("resume.first_page"))
        elif next_step == "2":
            return redirect(url_for("resume.second_page"))
        elif next_step == "3":
            return redirect(url_for("resume.third_page"))
        elif next_step == "4":
            return redirect(url_for("resume.forth_page"))
        elif next_step == "5":
            return redirect(url_for("resume.fifth_page"))

        # ✅ default
        return redirect(url_for("resume.second_page"))

    return render_template(
        "all_resume/first_page.html",
        resume=session.get("resume", {}),
        current_step=1
    )
@resume.route("/second_page", methods=["GET", "POST"])
def second_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if "resume" not in session:
        return redirect(url_for("resume.first_page"))

    resume_data = session.get("resume", {})

    if request.method == "POST":

        # ✅ SAFE UPDATE (DON'T OVERWRITE WITH NONE)
        if request.form.get("skills"):
            resume_data["skills"] = request.form.get("skills")

        if request.form.get("projects"):
            resume_data["projects_summary"] = request.form.get("projects")

        if request.form.get("experience"):
            resume_data["experience"] = request.form.get("experience")

        group = session.get("group")

        if group == "Design":
            resume_data["design_type"] = request.form.get("design_type")
            resume_data["tools"] = request.form.get("tools")

        elif group == "Finance":
            resume_data["finance_type"] = request.form.get("finance_type")
            resume_data["tools"] = request.form.get("tools")

        elif group == "Business":
            resume_data["business_type"] = request.form.get("business_type")
            resume_data["tools"] = request.form.get("tools")

        elif group == "Other":
            resume_data["field_type"] = request.form.get("field_type")

        session["resume"] = resume_data
        session.modified = True

        # ✅ FIXED NAVIGATION
        next_step = request.form.get("next_step")

        routes = {
            "1": "resume.first_page",
            "2": "resume.second_page",
            "3": "resume.third_page",
            "4": "resume.forth_page",
            "5": "resume.fifth_page"
        }

        if next_step in routes:
            return redirect(url_for(routes[next_step]))

        return redirect(url_for("resume.third_page"))

    return render_template(
        "all_resume/second_page.html",
        resume=resume_data,
        current_step=2
    )
@resume.route("/third_page", methods=["GET", "POST"])
def third_page():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if "resume" not in session:
        return redirect(url_for("resume.first_page"))

    if request.method == "POST":

        resume_data = session.get("resume", {})

        # ✅ EDUCATION
        degrees = request.form.getlist("degree")
        colleges = request.form.getlist("college")
        universities = request.form.getlist("university")
        cgpas = request.form.getlist("cgpa")
        starts = request.form.getlist("start")
        ends = request.form.getlist("end")

        education = []
        for i in range(len(degrees)):
            education.append({
                "degree": degrees[i],
                "college": colleges[i],
                "university": universities[i],
                "cgpa": cgpas[i],
                "start": starts[i],
                "end": ends[i]
            })

        resume_data["education"] = education

        # ✅ EXPERIENCE
        roles = request.form.getlist("role")
        companies = request.form.getlist("company")
        durations = request.form.getlist("duration")
        descs = request.form.getlist("exp_desc")

        experience = []
        for i in range(len(roles)):
            experience.append({
                "role": roles[i],
                "company": companies[i],
                "duration": durations[i],
                "desc": descs[i]
            })

        resume_data["experience_data"] = experience

        # ✅ PROJECTS
        titles = request.form.getlist("project_title")
        techs = request.form.getlist("project_tech")
        descs = request.form.getlist("project_desc")

        projects = []
        for i in range(len(titles)):
            projects.append({
                "title": titles[i],
                "tech": techs[i],
                "desc": descs[i]
            })

        resume_data["projects"] = projects

        # ✅ EXTRA
        resume_data["languages"] = request.form.get("languages")
        resume_data["hobbies"] = request.form.get("hobbies")

        # ✅ SAVE
        session["resume"] = resume_data
        session.modified = True

        # 🔥 ADD THIS (IMPORTANT)
        next_step = request.form.get("next_step")

        if next_step == "1":
            return redirect(url_for("resume.first_page"))
        elif next_step == "2":
            return redirect(url_for("resume.second_page"))
        elif next_step == "3":
            return redirect(url_for("resume.third_page"))
        elif next_step == "4":
            return redirect(url_for("resume.forth_page"))
        elif next_step == "5":
            return redirect(url_for("resume.fifth_page"))

        # default
        return redirect(url_for("resume.forth_page"))

    return render_template(
        "all_resume/third_page.html",
        resume=session.get("resume", {}),
        current_step=3,
        group=session.get("group")
    )

UPLOAD_FOLDER = 'static/uploads/image'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@resume.route("/forth_page" , methods=["GET", "POST"])
def forth_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
   
    if "resume" not in session or not isinstance(session["resume"], dict):
            return redirect(url_for("resume.first_page"))

    resume_data = session.get("resume", {})

    # Ensure the upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    next_step = None  
    if request.method == "POST":
        # ── 1. PROFILE PICTURE ──
        existing_pic = request.form.get("existing_profile_pic", "")
        pic_file = request.files.get("profile_pic")
        
        if pic_file and allowed_file(pic_file.filename):
            # Save new file
            filename = secure_filename(pic_file.filename)
            pic_file.save(os.path.join(UPLOAD_FOLDER, filename))
            resume_data["profile_pic"] = filename
        else:
            # Keep the old one if no new file is uploaded
            resume_data["profile_pic"] = existing_pic

        # ── 2. CERTIFICATIONS ──
        cert_files = request.files.getlist("cert_image")
        cert_descs = request.form.getlist("cert_desc")
        existing_certs = request.form.getlist("existing_cert_image")

        certifications = []
        # Loop through the descriptions to build the list
        for i in range(len(cert_descs)):
            desc = cert_descs[i].strip()
            existing_img = existing_certs[i] if i < len(existing_certs) else ""
            file_obj = cert_files[i] if i < len(cert_files) else None

            # If they uploaded a new image for this slot
            if file_obj and file_obj.filename and allowed_file(file_obj.filename):
                filename = secure_filename(file_obj.filename)
                file_obj.save(os.path.join(UPLOAD_FOLDER, filename))
                certifications.append({"image": filename, "desc": desc})
            
            # If they didn't upload a new one, but one already existed in session
            elif existing_img:
                certifications.append({"image": existing_img, "desc": desc})
                
            # If they just wrote a description but no image (optional fallback)
            elif desc:
                certifications.append({"image": "", "desc": desc})

        resume_data["certifications"] = certifications
        session["resume"] = resume_data
        
        next_step = request.form.get("next_step")

        if next_step:
            if next_step == "1":
                return redirect(url_for("resume.first_page"))
            elif next_step == "2":
                return redirect(url_for("resume.second_page"))
            elif next_step == "3":
                return redirect(url_for("resume.third_page"))
            elif next_step == "4":
                return redirect(url_for("resume.forth_page"))
            elif next_step == "5":
                return redirect(url_for("resume.fifth_page"))
        session.modified = True
        
        return redirect(url_for("resume.fifth_page"))    
    return render_template("all_resume/forth_page.html", resume=session.get("resume", {}), current_step=4)

def clean_text(text):
    if not text:
        return ""
    return text.strip().split("File")[0]           



@resume.route("/fifth_page", methods=["GET", "POST"])
def fifth_page():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if "resume" not in session or not isinstance(session["resume"], dict):
        return redirect(url_for("resume.first_page"))

    resume_data = session.get("resume", {})
    next_step = None

    if request.method == "POST":

        # =========================
        # STANDARDIZE DATA
        # =========================

        # NAME SPLIT
        full_name = resume_data.get("name", "")
        parts = full_name.split()

        resume_data["first_name"] = parts[0] if parts else ""
        resume_data["last_name"] = " ".join(parts[1:]) if len(parts) > 1 else ""

        # BASIC FIELDS
        resume_data["mobile"] = resume_data.get("phone", "")
        resume_data["summary"] = resume_data.get("objective", "")

        # =========================
        # SKILLS FIX
        # =========================
        skills = resume_data.get("skills", "")

        if isinstance(skills, str):
            resume_data["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
        elif isinstance(skills, list):
            resume_data["skills"] = skills
        else:
            resume_data["skills"] = []

        # =========================
        # LANGUAGES FIX
        # =========================
        langs = resume_data.get("languages", "")

        if isinstance(langs, str):
            lang_list = [l.strip() for l in langs.split(",") if l.strip()]
        elif isinstance(langs, list):
            lang_list = langs
        else:
            lang_list = []

        resume_data["language_levels"] = [
            {"language": l, "level": "Basic"} for l in lang_list
        ]

        # =========================
        # PROJECTS FIX
        # =========================
        fixed_projects = []

        for p in resume_data.get("projects", []):
            fixed_projects.append({
                "name": p.get("title") or p.get("name", ""),
                "description": p.get("desc") or p.get("description", ""),
                "technologies": p.get("tech") or p.get("technologies", "")
            })

        resume_data["projects"] = fixed_projects

        # =========================
        # EXPERIENCE FIX
        # =========================
        fixed_exp = []

        for e in resume_data.get("experience_data", []):
            fixed_exp.append({
                "role": e.get("role", ""),
                "company": e.get("company", ""),
                "duration": e.get("duration", ""),
                "description": e.get("desc") or e.get("description", ""),
                "location": ""
            })

        resume_data["experience"] = fixed_exp

        # =========================
        # STEP NAVIGATION
        # =========================
        next_step = request.form.get("next_step")

        if next_step:
            if next_step == "1":
                return redirect(url_for("resume.first_page"))
            elif next_step == "2":
                return redirect(url_for("resume.second_page"))
            elif next_step == "3":
                return redirect(url_for("resume.third_page"))
            elif next_step == "4":
                return redirect(url_for("resume.forth_page"))
            elif next_step == "5":
                return redirect(url_for("resume.fifth_page"))

        # =========================
        # SAVE / UPDATE DATABASE
        # =========================

        resume_json = json.dumps(resume_data)
        user_id = session["user_id"]

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="nagar@73",
            database="flask"
        )

        cursor = conn.cursor()

        resume_type = "other"

        # ==================================
        # UPDATE IF resume_id EXISTS
        # ==================================
        if "resume_id" in session:

            cursor.execute("""
                UPDATE other_resume
                SET resume_data=%s
                WHERE id=%s AND user_id=%s
            """, (
                resume_json,
                session["resume_id"],
                user_id
            ))

            original_id = session["resume_id"]
            action_type = "updated"

        # ==================================
        # INSERT FIRST TIME
        # ==================================
        else:

            cursor.execute("""
                INSERT INTO other_resume (user_id, resume_data, created_at)
                VALUES (%s, %s, NOW())
            """, (
                user_id,
                resume_json
            ))

            original_id = cursor.lastrowid
            session["resume_id"] = original_id
            action_type = "created"

        # ==================================
        # HISTORY TABLE
        # ==================================
        cursor.execute("""
            INSERT INTO all_resume
            (user_id, resume_data, resume_type, original_id, action_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id,
            resume_json,
            resume_type,
            original_id,
            action_type
        ))

        conn.commit()
        conn.close()

        flash("✅ Resume saved successfully!", "success")

        return redirect(url_for("resume.professional_page"))

    return render_template(
        "all_resume/fifth_page.html",
        resume=resume_data,
        current_step=5,
        group=session.get("group")
    )



@resume.route("/fancy_page")
def fancy_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("all_resume/fancy_page.html", resume=session.get("resume", {}))




def normalize_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                if item:
                    out.append(item)
            elif item:
                out.append(item)
        return out
    return []

def normalize_resume_data(data):
    data = data or {}

    full_name = data.get("name") or ""
    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""
    display_name = full_name.strip() or (first_name + " " + last_name).strip() or "Your Name"

    job_title = (
        data.get("career")
        or data.get("field_name")
        or data.get("business_type")
        or data.get("finance_type")
        or data.get("design_type")
        or data.get("field_type")
        or "Professional"
    )

    experience_list = data.get("experience") or data.get("experience_data") or []
    projects_list = data.get("projects") or []
    education_list = data.get("education") or []
    certifications_list = data.get("certifications") or []
    achievements_list = data.get("achievements") or data.get("highlights") or []

    return {
        **data,
        "display_name": display_name,
        "job_title": job_title,
        "summary_text": data.get("summary") or data.get("objective") or "",
        "skills_list": normalize_list(data.get("skills")),
        "tools_list": normalize_list(data.get("tools")),
        "languages_list": normalize_list(data.get("languages")),
        "hobbies_list": normalize_list(data.get("hobbies")),
        "achievements_list": normalize_list(achievements_list),
        "experience_list": experience_list if isinstance(experience_list, list) else [],
        "projects_list": projects_list if isinstance(projects_list, list) else [],
        "education_list": education_list if isinstance(education_list, list) else [],
        "certifications_list": certifications_list if isinstance(certifications_list, list) else [],
        "mobile": data.get("mobile") or data.get("phone") or "",
        "linkedin": data.get("linkedin") or "",
        "address": data.get("address") or "",
        "email": data.get("email") or "",
        "profile_pic": data.get("profile_pic") or "",
        "design_type": data.get("design_type") or "",
        "field_name": data.get("field_name") or "",
        "projects_summary": data.get("projects_summary") or "",
    }

@resume.route("/professional_page")
def professional_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    layout = request.args.get("layout", session.get("resume_layout", "1"))
    if layout not in ["1", "2", "3", "4"]:
        layout = "1"

    session["resume_layout"] = layout

    resume_data = normalize_resume_data(session.get("resume", {}))
    group = (session.get("group") or resume_data.get("career") or "").strip()
    show_projects = group not in ["Finance", "Business"]

    return render_template(
        "all_resume/professional_page.html",
        resume=resume_data,
        layout=layout,
        group=group,
        show_projects=show_projects
    )
@resume.route("/edit-other/<int:id>")
def edit_other_resume(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur.execute("SELECT * FROM other_resume WHERE id=%s", (id,))
    row = cur.fetchone()

    if not row:
        return "Resume not found"

    data = row["resume_data"]
    if isinstance(data, str):
        data = json.loads(data)

    keys = ["resume", "edit_id", "edit_type", "group"]
    for k in keys:
        session.pop(k, None)#IMPORTANT (removes old IT data)

    session["user_id"] = data.get("user_id") or session.get("user_id")
    session["resume"] = data
    session["edit_id"] = id
    session["edit_type"] = "other"
    session["group"] = "Other"   

    session.modified = True

    return redirect(url_for("resume.second_page"))

@resume.route("/api/get-other-resumes")
def get_other_resumes():
    user_id = session.get("user_id")

    cur.execute("""
        SELECT id, resume_data, created_at 
        FROM other_resume 
        WHERE user_id=%s
    """, (user_id,))

    rows = cur.fetchall()

    result = []
    for row in rows:
        data = json.loads(row["resume_data"]) if isinstance(row["resume_data"], str) else row["resume_data"]

        result.append({
            "id": row["id"],
            "name": data.get("first_name") or data.get("name") or "No Name",
            "updated": row["created_at"],
            "type": "other"   #  VERY IMPORTANT
        })

    return jsonify(result)
@resume.route("/api/get-it-resumes")
def get_it_resumes():
    user_id = session.get("user_id")
   

    cur.execute("""
        SELECT id, resume_data, created_at 
        FROM user_resume 
        WHERE user_id=%s
    """, (user_id,))

    rows = cur.fetchall()

    result = []
    for row in rows:
        data = json.loads(row["resume_data"])

        result.append({
            "id": row["id"],
            "name": data.get("first_name"),
            "updated": row["created_at"],
            "type": "it"   #  IMPORTANT
        })

    return jsonify(result)

@resume.route("/api/get-all-resumes")
def get_all_resumes():
    user_id = session.get("user_id")

    result = []

    # IT
    cur.execute("SELECT id, resume_data, created_at FROM user_resume WHERE user_id=%s", (user_id,))
    for row in cur.fetchall():
        data = json.loads(row["resume_data"])
        result.append({
            "id": row["id"],
            "name": data.get("first_name"),
            "updated": row["created_at"],
            "type": "it"
        })

    # OTHER
    cur.execute("SELECT id, resume_data, created_at FROM other_resume WHERE user_id=%s", (user_id,))
    for row in cur.fetchall():
        data = json.loads(row["resume_data"])
        result.append({
            "id": row["id"],
            "name": data.get("first_name"),
            "updated": row["created_at"],
            "type": "other"
        })

    return jsonify(result)

@resume.route("/api/preview/<rtype>/<int:id>")
def preview(rtype, id):

    if "user_id" not in session:
        return jsonify({"ok": False})

    

    if rtype == "it":
        cur.execute("""
            SELECT resume_data
            FROM user_resume
            WHERE id=%s AND user_id=%s
        """, (id, session["user_id"]))

    else:
        cur.execute("""
            SELECT resume_data
            FROM other_resume
            WHERE id=%s AND user_id=%s
        """, (id, session["user_id"]))

    row = cur.fetchone()

    if not row:
        return jsonify({"ok": False})

    data = row["resume_data"]

    if isinstance(data, str):
        data = json.loads(data)

    return jsonify({
        "ok": True,
        "resume": data
    })
    
    
    
@resume.route("/api/delete-resume/<rtype>/<int:id>", methods=['DELETE'])
def delete_resume(rtype, id):
    """Delete a resume from the database"""
    
    if "user_id" not in session:
        return jsonify({"ok": False, "message": "Not authenticated"})
 
    try:
        if rtype == "it":
            cur.execute("""
                DELETE FROM user_resume 
                WHERE id=%s AND user_id=%s
            """, (id, session["user_id"]))
        else:
            cur.execute("""
                DELETE FROM other_resume 
                WHERE id=%s AND user_id=%s
            """, (id, session["user_id"]))
        
       
            db.commit() 
        
        return jsonify({"ok": True, "message": "Resume deleted successfully"})
    
    except Exception as e:
        print(f"Error deleting resume: {e}")
        return jsonify({"ok": False, "message": str(e)})    