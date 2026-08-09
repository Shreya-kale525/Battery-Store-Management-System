from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    imports = db.relationship('Import', backref='supplier', lazy=True)

class Battery(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    model = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50))

    voltage = db.Column(db.Integer)
    capacity = db.Column(db.Integer)

    price = db.Column(db.Float, nullable=False)

    quantity = db.Column(db.Integer, default=0)

    barcode = db.Column(db.String(100), unique=True, nullable=False)

    qr_code = db.Column(db.String(200))

    import_date = db.Column(db.DateTime, default=datetime.utcnow)

    expiry_date = db.Column(db.DateTime)

    warranty_period = db.Column(db.Integer)

    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))

    purchase_price = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('SaleItem', backref='battery', lazy=True)
    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"BATTERY:{self.id}:{self.barcode}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"qr_{self.id}.png"
        filepath = os.path.join('static', 'uploads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        img.save(filepath)
        self.qr_code = filepath
        return filepath

class Import(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Integer)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    battery_id = db.Column(db.Integer, db.ForeignKey('battery.id'))
    total_cost = db.Column(db.Float)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sales = db.relationship('Sale', backref='customer', lazy=True)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    items = db.relationship('SaleItem', backref='sale', lazy=True)

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    battery_id = db.Column(db.Integer, db.ForeignKey('battery.id'))
    quantity = db.Column(db.Integer)
    price_at_sale = db.Column(db.Float)
    profit = db.Column(db.Float)