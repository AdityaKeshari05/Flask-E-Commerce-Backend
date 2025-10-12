from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models import User
from flask_jwt_extended import create_access_token, get_jwt, verify_jwt_in_request
from datetime import timedelta
from functools import wraps

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "user").strip().lower()

    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400
    if role not in ["user", "admin"]:
        return jsonify({"msg": "Invalid role"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409

    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "Registered successfully", "user": user.to_dict()}), 201

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid username or password"}), 401

    claims = {"role": user.role, "username": user.username}
    token = create_access_token(identity=user.id, additional_claims=claims, expires_delta=timedelta(hours=8))
    return jsonify({"access_token": token, "user": user.to_dict()})

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_app.config.get("ADMIN_OPEN_ACCESS"):
            return fn(*args, **kwargs)
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") != "admin":
                return jsonify({"msg": "Admins only"}), 403
        except Exception as e :
            print(str(e))
            return jsonify({"msg": "Missing or invalid token"}), 401

        return fn(*args, **kwargs)
    return wrapper
