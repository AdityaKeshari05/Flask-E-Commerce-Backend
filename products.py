from flask import Blueprint, request, jsonify, current_app, send_from_directory, abort
from extensions import db
from models import Product
from auth import admin_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from datetime import datetime
from decimal import Decimal
import os, json

products_bp = Blueprint("products", __name__)

# -------- Helpers --------
def _parse_product_from_multipart():
    """
    Read the 'product' JSON (sent as a Blob) + optional 'imageFile' from multipart/form-data.
    Maps keys from frontend (camelCase) to DB fields (snake_case).
    """
    image = request.files.get("imageFile")
    product_json = request.form.get("product")
    if not product_json:
        return None, image, "Missing product JSON"

    try:
        data = json.loads(product_json)
    except Exception:
        return None, image, "Invalid product JSON"

    mapped = {
        "name": data.get("name"),
        "brand": data.get("brand"),
        "description": data.get("description"),
        "category": data.get("category"),
        "stock_quantity": data.get("stockQuantity"),
        "product_available": data.get("productAvailable", True),
    }

    # Price -> Decimal
    if data.get("price") is not None:
        try:
            mapped["price"] = Decimal(str(data.get("price")))
        except Exception:
            return None, image, "Invalid price format"

    # releaseDate -> datetime.date
    release_date = data.get("releaseDate")
    if release_date:
        try:
            mapped["release_date"] = datetime.fromisoformat(release_date).date()
        except Exception:
            mapped["release_date"] = None

    return mapped, image, None


def _save_image_file(image):
    if not image or image.filename == "":
        return None, None
    filename = secure_filename(image.filename)
    base, ext = os.path.splitext(filename)
    unique_name = f"{base}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    image.save(os.path.join(folder, unique_name))
    return unique_name, image.mimetype

# -------- Routes --------

@products_bp.get("/products")
def list_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify([p.to_dict() for p in products])

@products_bp.get("/product/<int:pid>")
def get_product(pid):
    p = Product.query.get_or_404(pid)
    return jsonify(p.to_dict())

@products_bp.get("/product/<int:pid>/image")
def get_product_image(pid):
    p = Product.query.get_or_404(pid)
    if not p.image_filename:
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        p.image_filename,
        mimetype=p.image_mimetype,
        as_attachment=False
    )

@products_bp.get("/products/search")
def search_products():
    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return jsonify([])
    like = f"%{keyword}%"
    results = Product.query.filter(
        or_(
            Product.name.ilike(like),
            Product.brand.ilike(like),
            Product.category.ilike(like),
        )
    ).all()
    return jsonify([p.to_dict() for p in results])

@products_bp.post("/product")
@admin_required
def create_product():
    data, image, err = _parse_product_from_multipart()
    if err:
        return jsonify({"msg": err}), 400

    required = ["name", "brand", "price", "category", "stock_quantity"]
    missing = [k for k in required if data.get(k) in (None, "", [])]
    if missing:
        return jsonify({"msg": f"Missing fields: {', '.join(missing)}"}), 400

    p = Product(**data)
    if image:
        filename, mimetype = _save_image_file(image)
        p.image_filename = filename
        p.image_mimetype = mimetype

    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201

@products_bp.put("/product/<int:pid>")
@admin_required
def update_product(pid):
    p = Product.query.get_or_404(pid)
    data, image, err = _parse_product_from_multipart()
    if err:
        return jsonify({"msg": err}), 400

    for key, value in data.items():
        if value is not None:
            setattr(p, key, value)

    if image:
        # Remove old image if present
        if p.image_filename:
            try:
                os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], p.image_filename))
            except Exception:
                pass
        filename, mimetype = _save_image_file(image)
        p.image_filename = filename
        p.image_mimetype = mimetype

    db.session.commit()
    return jsonify(p.to_dict())

@products_bp.delete("/product/<int:pid>")
@admin_required
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    if p.image_filename:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], p.image_filename))
        except Exception:
            pass
    db.session.delete(p)
    db.session.commit()
    return jsonify({"msg": "deleted"})
