from flask import Flask, request, jsonify
from configuration import Config 
from extensions import db, jwt, cors
from models import User, Product
from auth import auth_bp
from products import products_bp
import os
from datetime import datetime
from flask import request, jsonify
from sqlalchemy.exc import SQLAlchemyError

# Additional Models for Cart and Orders
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')

class OrderItems(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

# Cart Endpoints
from flask import Blueprint
cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/cart/<int:user_id>', methods=['GET'])
def get_cart(user_id):
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    result = []
    for item in cart_items:
        product = Product.query.get(item.product_id)
        result.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'quantity': item.quantity,
            'stock_quantity': product.stock_quantity
        })
    return jsonify(result)

@cart_bp.route('/cart/<int:user_id>', methods=['POST'])
def add_to_cart(user_id):
    data = request.json
    product_id = data['productId']
    quantity = data['quantity']

    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity = quantity
    else:
        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({'message': 'Cart updated successfully'})

@cart_bp.route('/cart/<int:user_id>/<int:product_id>', methods=['DELETE'])
def remove_cart_item(user_id, product_id):
    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
    return jsonify({'message': 'Item removed from cart'})

@cart_bp.route('/cart/<int:user_id>', methods=['DELETE'])
def clear_cart(user_id):
    Cart.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({'message': 'Cart cleared'})

# Order Endpoints
order_bp = Blueprint('order', __name__)

@order_bp.route('/orders/<int:user_id>', methods=['POST'])
def create_order(user_id):
    try:
        data = request.get_json()
        cart_items = data.get('cartItems', [])

        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        # Calculate total price
        total_price = sum(
    float(item['price']) * int(item['quantity']) 
    for item in cart_items
)

        # Create order
        order = Orders(user_id=user_id, total_price=total_price)
        db.session.add(order)
        db.session.flush()  # get order.id without committing yet

        # Add order items
        for item in cart_items:
            product = Product.query.get(item['id'])
            if not product:
                db.session.rollback()
                return jsonify({'error': f"Product with id {item['id']} not found"}), 404

            if product.stock_quantity < item['quantity']:
                db.session.rollback()
                return jsonify({'error': f"Not enough stock for product {product.name}"}), 400

            order_item = OrderItems(
                order_id=order.id,
                product_id=item['id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)

            # Reduce stock
            product.stock_quantity -= item['quantity']

        # Clear cart
        Cart.query.filter_by(user_id=user_id).delete()

        db.session.commit()
        return jsonify({'message': 'Order placed successfully', 'order_id': order.id}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@order_bp.route('/orders/<int:user_id>', methods=['GET'])
def get_orders(user_id):
    orders = Orders.query.filter_by(user_id=user_id).all()
    result = []
    for order in orders:
        items = OrderItems.query.filter_by(order_id=order.id).all()
        order_items = [{'product_id': i.product_id, 'quantity': i.quantity, 'price': i.price} for i in items]
        result.append({
            'order_id': order.id,
            'total_price': order.total_price,
            'order_date': order.order_date,
            'status': order.status,
            'items': order_items
        })
    return jsonify(result)

# Modified create_app to register new blueprints
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    cors.init_app(
    app,
    resources={r"/api/*": {"origins":["*","https://mini-e-commerce-website-five.vercel.app"],
                           "allow_headers": ["Content-Type", "Authorization"],
                           "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}},
    supports_credentials=True,
)



    with app.app_context():
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        db.create_all()

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(order_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
