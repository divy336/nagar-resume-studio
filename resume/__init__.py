from flask import Blueprint

resume = Blueprint("resume", __name__)

from resume import detail
from resume import all_resume
