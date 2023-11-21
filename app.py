from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = ''

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

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'product_id', 'created_at', name='uq_customer_product_timestamp'),
    )


@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    required_attributes = []
    new_order = Order(**data)
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order created successfully'}), 201

# Get all orders
@app.route('/orders')
def get_all_orders():
    orders = Order.query.all()
    if orders is None or len(orders) == 0:
        return (error_response("orders not found"), 404)
    return jsonify({'orders': [{'order_id': order.order_id, 'customer_id': order.customer_id,
                                'product_id': order.product_id, 'quantity': order.quantity,
                                'created_at': order.created_at} for order in orders]}), 200

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
        if data is None or 'customer_email' not in data or 'product_name' not in data or 'quantity' not in data:
            return jsonify({"Error": "Missing required data (customer_email, product_name, quantity)"}), 400

        customer = Customer.query.filter_by(email=data.get('customer_email')).first()
        product = Product.query.filter_by(name=data.get('product_name')).first()

        if not customer or not product:
            return jsonify({'message': 'Customer or Product not found'}), 404

        order.customer_id = customer.customer_id
        order.product_id = product.product_id
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

    return jsonify({'customers': [{'customer_id': customer.customer_id,
                               'first_name': customer.first_name,
                               'last_name': customer.last_name,
                               'email': customer.email,
                               'total_products': customer.total_products} for customer, total_products in customers]})

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

@app.route("/product/<int:id>")
def getProductById(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"Product": product.name})

def success_response(message):
    return jsonify({'success': True, 'message': message}), 200

def error_response(message, status_code):
    return jsonify({'success': False, 'error': message}), status_code

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
