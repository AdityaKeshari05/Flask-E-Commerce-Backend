from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "username": self.username, "role": self.role}

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    brand = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    release_date = db.Column(db.Date)
    product_available = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, default=0)
    image_filename = db.Column(db.String(255))
    image_mimetype = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "description": self.description,
            "price": float(self.price) if self.price is not None else None,
            "category": self.category,
            "releaseDate": self.release_date.isoformat() if self.release_date else None,
            "productAvailable": self.product_available,
            "stockQuantity": self.stock_quantity,
            "imageName": self.image_filename
        }
