from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv(".env")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
db = SQLAlchemy(app)

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
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())


@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    new_order = Order(**data)
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order created successfully'}), 201

# Get all orders
@app.route('/orders')
def get_all_orders():
    orders = Order.query.all()
    return jsonify({'orders': [{'order_id': order.order_id, 'customer_id': order.customer_id,
                                'product_id': order.product_id, 'quantity': order.quantity,
                                'created_at': order.created_at} for order in orders]})

# Get order by ID
@app.route('/orders/<int:order_id>')
def get_order_by_id(order_id):
    order = Order.query.get(order_id)
    if order:
        return jsonify({'order_id': order.order_id, 'customer_id': order.customer_id,
                        'product_id': order.product_id, 'quantity': order.quantity,
                        'created_at': order.created_at})
    else:
        return jsonify({'message': 'Order not found'}), 404

# Update order by ID
@app.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    order = Order.query.get(order_id)
    if order:
        data = request.get_json()
        order.customer_id = data.get('customer_id', order.customer_id)
        order.product_id = data.get('product_id', order.product_id)
        order.quantity = data.get('quantity', order.quantity)
        db.session.commit()
        return jsonify({'message': 'Order updated successfully'})
    else:
        return jsonify({'message': 'Order not found'}), 404

# Delete order by ID
@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order = Order.query.get(order_id)
    if order:
        db.session.delete(order)
        db.session.commit()
        return jsonify({'message': 'Order deleted successfully'})
    else:
        return jsonify({'message': 'Order not found'}), 404

# Get customers by the number of products they've bought
@app.route('/customers/number-of-products')
def get_customers_by_products():
    customers = db.session.query(Customer, db.func.count(Order.customer_id).label('total_products')) \
        .join(Order, Customer.customer_id == Order.customer_id) \
        .group_by(Customer.customer_id) \
        .all()

    return jsonify({'customers': [{'customer_id': customer.Customer.customer_id,
                                   'first_name': customer.Customer.first_name,
                                   'last_name': customer.Customer.last_name,
                                   'email': customer.Customer.email,
                                   'total_products': customer.total_products} for customer in customers]})

# Get purchase history for a customer
@app.route('/customers/<int:customer_id>/purchase-history')
def get_purchase_history(customer_id):
    customer = Customer.query.get(customer_id)
    if customer:
        orders = Order.query.filter_by(customer_id=customer_id).all()
        return jsonify({'purchase_history': [{'order_id': order.order_id,
                                              'product_id': order.product_id,
                                              'quantity': order.quantity,
                                              'created_at': order.created_at} for order in orders]})
    else:
        return jsonify({'message': 'Customer not found'}), 404

# Get all customers
@app.route("/customers")
def getAllCustomers():
    customers = Customer.query.all()
    return jsonify({"customers": [customer.email for customer in customers]})

# Get all products
@app.route("/products")
def getAllProducts():
    products = Product.query.all()
    return jsonify({"products": [product.name for product in products]})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
