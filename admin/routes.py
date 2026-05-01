

from flask import session, url_for, render_template, request, redirect, jsonify
from admin import admin
import mysql.connector
import random
import json
import os
import requests

def get_db():
    db = mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306)),
        connection_timeout=30,
        autocommit=True
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor

SUPER_ADMIN_EMAIL = "nagardivya73@gmail.com"
SENDER_EMAIL      = "nagardivya73@gmail.com"
SENDER_PASSWORD   = "gjgebkodbezyzoxr"


# ══════════════════════════════════════
#  EMAIL HELPERS
# ══════════════════════════════════════

import requests

def get_email_template(otp, title="OTP Verification"):
    return f"""
    <html>
    <body style="font-family:Arial;background:#f4f4f4;padding:30px;">
      <div style="max-width:500px;margin:auto;background:#fff;padding:30px;border-radius:12px;">
        <h2 style="text-align:center;color:#4f46e5;">Resume Builder Admin</h2>
        <h3 style="text-align:center;">{title}</h3>
        <div style="
            font-size:34px;
            font-weight:bold;
            text-align:center;
            background:#4f46e5;
            color:white;
            padding:15px;
            border-radius:10px;
            letter-spacing:8px;
            margin:25px 0;
        ">
            {otp}
        </div>
        <p style="text-align:center;">OTP valid for one time use.</p>
      </div>
    </body>
    </html>
    """

def send_otp_email(to_email, otp, subject="OTP Verification"):
    api_key = os.getenv("BREVO_API_KEY")

    payload = {
        "sender": {
            "name": "Resume Builder",
            "email": "nagardivya73@gmail.com"
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": get_email_template(otp, subject)
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=20
        )

        print("Email Status:", response.status_code)
        print("Response:", response.text)

    except Exception as e:
        print("Email Error:", e)        
        
@admin.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not all([username, email, password, confirm]):
            return render_template("admin_signup.html", error="All fields are required")

        if password != confirm:
            return render_template("admin_signup.html", error="Passwords do not match")

        db, cursor = get_db()

        try:
            db.ping(reconnect=True, attempts=3, delay=2)

            # check email exists
            cursor.execute(
                "SELECT id FROM admin_signup WHERE email=%s",
                (email,)
            )

            if cursor.fetchone():
                return render_template(
                    "admin_signup.html",
                    error="Email already registered"
                )

            # insert admin
            cursor.execute(
                """
                INSERT INTO admin_signup
                (username, email, password, is_verified)
                VALUES (%s,%s,%s,0)
                """,
                (username, email, password)
            )

            # otp
            otp = str(random.randint(100000, 999999))

            cursor.execute(
                """
                INSERT INTO admin_otp
                (email, otp, is_used)
                VALUES (%s,%s,0)
                """,
                (email, otp)
            )

            db.commit()

            send_otp_email(
                SUPER_ADMIN_EMAIL,
                otp,
                f"New Admin Signup Approval for {email}"
            )

            session["otp_email"] = email

            return redirect(url_for("admin.admin_otp"))

        except Exception as e:
            db.rollback()
            return render_template(
                "admin_signup.html",
                error=str(e)
            )

        finally:
            cursor.close()
            db.close()

    return render_template("admin_signup.html")

@admin.route("/admin_otp", methods=["GET", "POST"])
def admin_otp():

    email = session.get("otp_email")

    if request.method == "POST":

        otp = request.form.get("otp", "").strip()

        if not otp:
            return render_template(
                "admin_otp.html",
                error="Please enter OTP"
            )

        db, cursor = get_db()

        try:
            db.ping(reconnect=True, attempts=3, delay=2)

            cursor.execute("""
                SELECT id FROM admin_otp
                WHERE email=%s AND otp=%s AND is_used=0
                ORDER BY id DESC LIMIT 1
            """, (email, otp))

            row = cursor.fetchone()

            if not row:
                return render_template(
                    "admin_otp.html",
                    error="Invalid or expired OTP"
                )

            cursor.execute(
                "UPDATE admin_otp SET is_used=1 WHERE id=%s",
                (row["id"],)
            )

            cursor.execute(
                "UPDATE admin_signup SET is_verified=1 WHERE email=%s",
                (email,)
            )

            db.commit()

            return redirect(url_for("admin.admin_login"))

        except Exception as e:
            db.rollback()
            return render_template(
                "admin_otp.html",
                error=str(e)
            )

        finally:
            cursor.close()
            db.close()

    return render_template("admin_otp.html")


@admin.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        ip = request.remote_addr or "Unknown"

        if not email or not password:
            return render_template(
                "admin_login.html",
                error="All fields are required"
            )

        db, cursor = get_db()

        try:
            db.ping(reconnect=True, attempts=3, delay=2)

            cursor.execute("""
                SELECT id, username, email
                FROM admin_signup
                WHERE email=%s AND password=%s AND is_verified=1
            """, (email, password))

            row = cursor.fetchone()

            if not row:
                log_login("UNKNOWN", email, ip, "FAILED")

                return render_template(
                    "admin_login.html",
                    error="Invalid credentials or account not verified"
                )

            session["admin_id"] = row["id"]
            session["admin_name"] = row["username"]
            session["admin_email"] = row["email"]

            log_login(row["username"], row["email"], ip, "SUCCESS")

            return redirect(url_for("admin.admin_dashboard"))

        except Exception as e:
            return render_template(
                "admin_login.html",
                error=str(e)
            )

        finally:
            cursor.close()
            db.close()

    return render_template("admin_login.html")

@admin.route("/forgot_admin", methods=["GET", "POST"])
def forgot_admin():

    if request.method == "POST":

        email = request.form.get("email", "").strip()

        if not email:
            return render_template(
                "forgot_admin.html",
                error="Email required"
            )

        db, cursor = get_db()

        try:
            db.ping(reconnect=True, attempts=3, delay=2)

            cursor.execute(
                "SELECT id FROM admin_signup WHERE email=%s",
                (email,)
            )

            if not cursor.fetchone():
                return render_template(
                    "forgot_admin.html",
                    error="Email not registered"
                )

            otp = str(random.randint(100000, 999999))

            cursor.execute(
                """
                INSERT INTO admin_otp
                (email, otp, is_used)
                VALUES (%s,%s,0)
                """,
                (email, otp)
            )

            db.commit()

            send_otp_email(email, otp, "Password Reset OTP")

            session["reset_email"] = email

            return redirect(url_for("admin.forgot_admin_otp"))

        except Exception as e:
            db.rollback()
            return render_template(
                "forgot_admin.html",
                error=str(e)
            )

        finally:
            cursor.close()
            db.close()

    return render_template("forgot_admin.html")


@admin.route("/forgot_admin_otp", methods=["GET", "POST"])
def forgot_admin_otp():

    email = session.get("reset_email")

    if request.method == "POST":

        otp = request.form.get("otp", "").strip()

        if not otp:
            return render_template(
                "forgot_admin_otp.html",
                error="OTP required"
            )

        db, cursor = get_db()

        try:
            db.ping(reconnect=True, attempts=3, delay=2)

            cursor.execute("""
                SELECT id FROM admin_otp
                WHERE email=%s AND otp=%s AND is_used=0
                ORDER BY id DESC LIMIT 1
            """, (email, otp))

            row = cursor.fetchone()

            if not row:
                return render_template(
                    "forgot_admin_otp.html",
                    error="Invalid OTP"
                )

            cursor.execute(
                "UPDATE admin_otp SET is_used=1 WHERE id=%s",
                (row["id"],)
            )

            db.commit()

            return redirect(url_for("admin.admin_login"))

        except Exception as e:
            db.rollback()
            return render_template(
                "forgot_admin_otp.html",
                error=str(e)
            )

        finally:
            cursor.close()
            db.close()

    return render_template("forgot_admin_otp.html")


@admin.route("/delete_admin/<int:admin_id>", methods=["POST"])
def delete_admin(admin_id):

    if "admin_id" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    db, cursor = get_db()

    try:
        db.ping(reconnect=True, attempts=3, delay=2)

        # Get admin details
        cursor.execute(
            "SELECT id, username, email FROM admin_signup WHERE id=%s",
            (admin_id,)
        )

        row = cursor.fetchone()

        if not row:
            return jsonify({
                "success": False,
                "message": "Admin not found"
            }), 404

        deleted_id = row["id"]
        deleted_name = row["username"]
        deleted_email = row["email"]

        # Super Admin protect
        if deleted_email == SUPER_ADMIN_EMAIL:
            return jsonify({
                "success": False,
                "message": "Super Admin cannot be deleted"
            }), 403

        # Self delete block
        if deleted_id == session["admin_id"]:
            return jsonify({
                "success": False,
                "message": "You cannot delete your own account"
            }), 400

        # Delete records
        cursor.execute(
            "DELETE FROM admin_signup WHERE id=%s",
            (admin_id,)
        )

        cursor.execute(
            "DELETE FROM admin_otp WHERE email=%s",
            (deleted_email,)
        )

        db.commit()

        return jsonify({
            "success": True,
            "message": f"Admin '{deleted_name}' deleted successfully"
        })

    except Exception as e:
        db.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

@admin.route("/admin_dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    db, cursor = get_db()

    try:
        db.ping(reconnect=True, attempts=3, delay=2)

        # =====================================
        # IT RESUMES
        # =====================================
        cursor.execute("SELECT user_id, resume_data FROM user_resume")
        resume_rows = cursor.fetchall()

        users = []
        resumes = []

        for row in resume_rows:

            user_id = row["user_id"]

            try:
                r = json.loads(row["resume_data"]) if isinstance(
                    row["resume_data"], str
                ) else row["resume_data"]

            except:
                continue

            name = (
                (r.get("first_name", "") + " " + r.get("last_name", "")).strip()
            ) or "No Name"

            users.append({
                "user_id": user_id,
                "name": name,
                "email": r.get("email", "Not Provided"),
                "mobile": r.get("mobile", "Not Provided"),
                "major": r.get("major", "Not Provided"),
                "status": 1
            })

            resumes.append({
                "user_id": user_id,
                "name": name,
                "email": r.get("email", "Not Provided"),
                "skills": ", ".join(r.get("skills", [])),
                "experience": len(r.get("experience", [])),
                "projects": len(r.get("projects", [])),
                "raw": r
            })

        # =====================================
        # OTHER RESUMES
        # =====================================
        cursor.execute("SELECT user_id, resume_data FROM other_resume")
        other_rows = cursor.fetchall()

        other_resumes = []

        for row in other_rows:

            try:
                r = json.loads(row["resume_data"]) if isinstance(
                    row["resume_data"], str
                ) else row["resume_data"]

            except:
                continue

            other_resumes.append({
                "user_id": row["user_id"],
                "name": r.get("name", "No Name"),
                "email": r.get("email", "Not Provided"),
                "career": r.get("career", ""),
                "skills": ", ".join(r.get("skills", [])),
                "experience": len(r.get("experience", [])),
                "projects": len(r.get("projects", [])),
                "raw": r
            })

        # =====================================
        # ADMINS
        # =====================================
        cursor.execute("""
            SELECT id, username, email, is_verified, created_at
            FROM admin_signup
            ORDER BY id DESC
        """)

        admin_rows = cursor.fetchall()

        admins = []

        for row in admin_rows:
            admins.append({
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "is_verified": bool(row["is_verified"]),
                "created_at": str(row["created_at"]),
                "is_self": row["id"] == session["admin_id"]
            })

        # =====================================
        # LOGIN ACTIVITY
        # =====================================
        cursor.execute("""
            SELECT id, username, email, created_at
            FROM admin_login
            ORDER BY created_at DESC
            LIMIT 50
        """)

        login_rows = cursor.fetchall()

        login_activity = []

        for row in login_rows:
            login_activity.append({
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "login_time": str(row["created_at"])
            })

        # =====================================
        # SUCCESS LOGIN COUNT
        # =====================================
        cursor.execute("""
            SELECT COUNT(DISTINCT email) AS total
            FROM admin_login
            WHERE username LIKE 'SUCCESS:%'
        """)

        result = cursor.fetchone()
        successful_logins = result["total"] if result else 0

        # =====================================
        # RENDER PAGE
        # =====================================
        return render_template(
            "admin/dashbord_admin.html",

            users=users,
            resumes=resumes,

            other_resumes=other_resumes,

            admins=admins,
            login_activity=login_activity,

            total_users=len(users),
            total_resumes=len(resumes),
            total_other_resumes=len(other_resumes),

            verified_admins=sum(
                1 for a in admins if a["is_verified"]
            ),

            successful_logins=successful_logins,

            admin_name=session.get("admin_name", "Admin"),
            admin_email=session.get("admin_email", ""),
            current_admin_id=session.get("admin_id")
        )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        db.close()

@admin.route("/admin_logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)

    return redirect(url_for("admin.admin_login"))