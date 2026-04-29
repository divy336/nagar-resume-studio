from flask import Blueprint, request, render_template, redirect, url_for, session
import mysql.connector
import random
import smtplib
from email.message import EmailMessage
from auth import auth
from resume import detail
import os

db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT", 3306))
)

cursor = db.cursor(dictionary=True)
        #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

    
def send_email(to_email, otp):
    sender_email = "nagardivya73@gmail.com"
    sender_password = "gjgebkodbezyzoxr"

    msg = EmailMessage()
    msg["Subject"] = "🔐 Your OTP Verification Code"
    msg["From"] = f"Resume Builder <{sender_email}>"
    msg["To"] = to_email

 
    msg.set_content(f"""
Hello,

Your One-Time Password (OTP) is: {otp}

This OTP is valid for one-time verification only and will expire shortly.

If you did not request this OTP, please ignore this email.

Thanks,
Resume Builder Team
""")


    msg.add_alternative(f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Segoe UI, Arial, sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;">
<tr>
<td align="center">

<table width="520" cellpadding="0" cellspacing="0" style="
    background:#ffffff;
    border-radius:14px;
    box-shadow:0 15px 35px rgba(0,0,0,0.15);
    padding:35px;
">

<tr>
<td align="center" style="padding-bottom:20px;">
    <h2 style="margin:0;color:#4a6cf7;font-size:24px;">
        OTP Verification
    </h2>
</td>
</tr>

<tr>
<td style="color:#333;font-size:15px;line-height:1.6;">
    <p>Hello,</p>
    <p>Use the following One-Time Password (OTP) to verify your account:</p>
</td>
</tr>

<tr>
<td align="center" style="padding:30px 0;">
    <div style="
        font-size:32px;
        font-weight:700;
        letter-spacing:6px;
        background:#eef2ff;
        color:#2f3cff;
        padding:16px 30px;
        border-radius:12px;
        border:1px dashed #c7d2fe;
        display:inline-block;
    ">
        {otp}
    </div>
</td>
</tr>

<tr>
<td style="color:#555;font-size:14px;line-height:1.6;">
    <p>This OTP is valid for <strong>one-time use only</strong> and will expire shortly.</p>
    <p style="color:#888;font-size:13px;">
        If you did not request this verification, please ignore this email.
    </p>
</td>
</tr>

<tr>
<td align="center" style="
    padding-top:25px;
    border-top:1px solid #eee;
    color:#999;
    font-size:12px;
">
    © Resume Builder • Secure Account Verification
</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
""", subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)
      

        #signup code 
@auth.route("/signup", methods=["GET", "POST"])
def signup():
   

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")   
        password = request.form.get("password")
        confirm=request.form.get("confirm")
        cursor.execute("SELECT id FROM register WHERE email=%s", (email,))
        user = cursor.fetchone()

        if not all([username,email,password,confirm]):
                return render_template("signup.html", error="All fields are required")

        if password != confirm:
            return render_template("signup.html", error="Passwords do not match")

        cursor.execute("SELECT id from register where email=%s",(email,))
        if cursor.fetchone():
            return render_template("signup.html",error="email already registerd")
    
        otp= str(random.randint(100000,999999))
        cursor.execute("INSERT INTO otp_verify (email,otp,is_used) VALUES (%s,%s,0)",(email,otp))
        db.commit()
        send_email(email,otp)
        cursor.execute(
            "INSERT INTO register (username,email,password,is_verified) VALUES (%s,%s,%s,0)",
            (username,email,password)
        )
        db.commit()
        return redirect(url_for("auth.verify_otp",email=email))

    return render_template("signup.html")

#otp virification 
@auth.route("/verify-otp", methods=["GET","POST"])
def verify_otp():
    email = request.args.get("email")

    if request.method == "POST":
        otp = request.form.get("otp")

        if not otp:
            return render_template("otp.html", error="OTP required", email=email)

        cursor.execute(
            "SELECT id FROM otp_verify WHERE email=%s AND otp=%s AND is_used=0",
            (email,otp)
        ) 
        row = cursor.fetchone()

        if not row:
            return render_template("otp.html", error="Invalid or used OTP", email=email)

        cursor.execute("UPDATE otp_verify SET is_used=1 WHERE id=%s", (row[0],))
        cursor.execute("UPDATE register SET is_verified=1 WHERE email=%s", (email,))
        db.commit()

        return redirect(url_for("auth.login"))

    return render_template("otp.html", email=email)

#login code 



@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        if not email or not password:
            return render_template("login.html", error="All fields are required")

        cursor.execute(
            "SELECT id, username, is_verified FROM register WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cursor.fetchone()

        if user is None:
            return render_template("login.html", error="Invalid email or password")

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("resume.dashbord"))

    return render_template("login.html")
@auth.route("/logout", methods=["GET","POST"])


# logout code 
def logout():
    session.clear()
    return redirect(url_for("auth.login"))



@auth.route("/forgot-password",methods=["GET","POST"])        
def forgot_password():
    if request.method=="POST":
        email=request.form.get("email")
        
        if not email:
            return render_template("forgot_password.html",error="Email is required")
        
        cursor.execute("SELECT id FROM register WHERE email=%s",(email,))
        
        if not cursor.fetchone():
            return render_template("forgot_password.html",error="email is not regidtered")
        
        otp=str(random.randint(100000,999999))
        
        cursor.execute(
        "INSERT INTO otp_verify (email, otp, is_used) VALUES (%s, %s, 0)",
    (email, otp)
)

        send_email(email,otp)
        return redirect(url_for("auth.reset_otp",email=email))
    return render_template("forgot_password.html")

@auth.route("/reset-otp", methods=["GET", "POST"])
def reset_otp():
    email = request.args.get("email")

    if request.method == "POST":
        otp = request.form.get("otp")

        cursor.execute(
            "SELECT id FROM otp_verify WHERE email=%s AND otp=%s AND is_used=0",
            (email, otp)
        )
        row = cursor.fetchone()

        if not row:
            return render_template("reset_otp.html", error="Invalid OTP", email=email)

        cursor.execute(
            "UPDATE otp_verify SET is_used=1 WHERE id=%s",
            (row[0],)
        )
        db.commit()

        return redirect(url_for("auth.reset_password", email=email))

    return render_template("reset_otp.html", email=email)


@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email")                            

    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not password or not confirm:
            return render_template(
                "reset_password.html",
                error="All fields required",
                email=email
            )

        if password != confirm:
            return render_template(
                "reset_password.html",
                error="Passwords do not match",
                email=email
            )

        cursor.execute(
            "UPDATE register SET password=%s WHERE email=%s",
            (password, email)
        )
        db.commit()

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", email=email)
    
    
