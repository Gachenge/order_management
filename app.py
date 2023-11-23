from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv('.env')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")

db = SQLAlchemy(app)

# Initialize CORS
CORS(app, supports_credentials=True)

# Define Models
class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    product = db.relationship('Product', backref='orders')

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'product_id', 'created_at', name='uq_customer_product_timestamp'),
    )


@app.route('/orders', methods=['GET', 'POST'])
def create_order():
    if request.method == 'POST':
        data = request.get_json()
        allowed_attributes = ['customer_id', 'product_id', 'quantity']

        if not data or not all(key in data for key in allowed_attributes):
            return jsonify({"Error": "Missing or invalid data"}), 400

        time_threshold = datetime.utcnow() - timedelta(seconds=60)
        existing_order = Order.query.filter(
            Order.customer_id == data['customer_id'],
            Order.product_id == data['product_id'],
            Order.created_at > time_threshold
        ).first()

        if existing_order:
            return jsonify({'message': 'Order already placed for the same customer and product within a short time frame'}), 400

        new_order = Order(**data)
        db.session.add(new_order)
        db.session.commit()

        return jsonify({'message': 'Order created successfully'}), 201

    if request.method == 'GET':
        orders = Order.query.all()
        
        if not orders:
            return error_response("Orders not found"), 404

        orders_data = [
            {
                'order_id': order.order_id,
                'customer_id': order.customer_id,
                'product_id': order.product_id,
                'quantity': order.quantity,
                'created_at': order.created_at
            }
            for order in orders
        ]

        return jsonify({'orders': orders_data}), 200

    else:
        return jsonify({"Error": "method not allowed"}), 405

# Get order by ID
@app.route('/orders/<int:order_id>', methods = ['GET', 'PUT', 'DELETE'])
def get_order_by_id(order_id):
    order = Order.query.get_or_404(order_id)

    if request.method == 'GET':
        order_data = {
            'order_id': order.order_id,
            'customer_id': order.customer_id,
            'product_id': order.product_id,
            'quantity': order.quantity,
            'created_at': order.created_at
        }

        return jsonify({'order': order_data})

    if request.method == 'PUT':
        data = request.get_json()
        allowed_attributes = ['customer_name', 'product_name', 'quantity']

        if data is None or not set(data.keys()).issubset(allowed_attributes):
            return jsonify({"Error": "Invalid or missing data"}), 400

        for key, value in data.items():
            if key == 'customer_name':
                customer = Customer.query.filter_by(name=value).first()
                if not customer:
                    return jsonify({'message': 'Customer not found'}), 404
                if customer.customer_id != order.customer_id:
                    order.customer_id = customer.customer_id

            elif key == 'product_name':
                product = Product.query.filter_by(name=value).first()
                if not product:
                    return jsonify({'message': 'Product not found'}), 404
                if product.product_id != order.product_id:
                    order.product_id = product.product_id

            elif key == 'quantity':
                order.quantity = value

            else:
                return jsonify({"Error": f"You cannot change the {key} attribute"}), 403

        db.session.commit()

        return jsonify({'message': 'Order updated successfully'})

    if request.method == 'DELETE':
        try:
            db.session.delete(order)
            db.session.commit()
            return jsonify({'message': 'Order deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': 'Error deleting order', 'error': str(e)}), 500

    else:
        return jsonify({"Error": "method not allowed"}), 405

# Get customers by the number of products they've bought
@app.route('/customers/number-of-products')
def get_customers_by_products():
    try:
        customers_query = db.session.query(Customer, db.func.count(Order.customer_id).label('total_products')) \
            .join(Order, Customer.customer_id == Order.customer_id) \
            .group_by(Customer.customer_id) \
            .all()

        customers_data = [
            {
                'customer_id': customer.customer_id,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'total_products': total_products
            }
            for customer, total_products in customers_query
        ]

        return jsonify({'customers': customers_data})

    except Exception as e:
        return jsonify({'message': 'Error fetching customers', 'error': str(e)}), 500

# Get purchase history for a customer
@app.route('/customers/<int:customer_id>/purchase-history')
def get_purchase_history(customer_id):
    try:
        customer = Customer.query.get(customer_id)

        if not customer:
            return jsonify({'message': 'Customer not found'}), 404

        orders = Order.query.filter_by(customer_id=customer_id).all()

        purchase_history = [
            {
                'order_id': order.order_id,
                'product_id': order.product_id,
                'quantity': order.quantity,
                'created_at': order.created_at,
                'product_name': order.product.name
            }
            for order in orders
        ]

        return jsonify({'purchase_history': purchase_history})

    except Exception as e:
        return jsonify({'message': 'Error fetching purchase history', 'error': str(e)}), 500

# Get all customers
@app.route("/customers")
def get_all_customers():
    customers = Customer.query.all()

    if not customers:
        return jsonify({"error": "No customers data"}), 404

    customer_data = [
        {
            "customer_id": customer.customer_id,
            "email": customer.email,
            "first_name": customer.first_name,
            "last_name": customer.last_name
        }
        for customer in customers
    ]

    return jsonify({"data": customer_data})

# Get all products
@app.route("/products")
def get_all_products():
    products = Product.query.all()

    if not products:
        return jsonify({"error": "No products data"}), 404

    product_data = [
        {
            "product_id": product.product_id,
            "name": product.name,
            "price": product.price
        }
        for product in products
    ]

    return jsonify({"data": product_data})

# Get product by ID
@app.route("/product/<int:id>")
def get_product_by_id(id):
    product = Product.query.get(id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    product_data = {
        "product_id": product.product_id,
        "name": product.name,
        "price": product.price
    }

    return jsonify({"data": product_data})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
