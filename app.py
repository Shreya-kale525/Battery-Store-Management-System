from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Battery, Supplier, Import, Customer, Sale, SaleItem
from datetime import datetime, timedelta
import qrcode
import os
import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
LOW_STOCK_LIMIT = 5

import sqlite3

def create_table():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT,
        address TEXT
    )
    """)

    conn.commit()
    conn.close()

create_table()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

os.makedirs(app.instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'battery_store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if username == "admin" and password == "1234":
            login_user(user)
            return redirect(url_for('dashboard'))
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_stock = db.session.query(db.func.sum(Battery.quantity)).scalar() or 0
    total_sales = db.session.query(db.func.sum(Sale.total_amount)).scalar() or 0
    low_stock = Battery.query.filter(Battery.quantity <= LOW_STOCK_LIMIT).all() 
    top_selling = db.session.query(Battery, db.func.sum(SaleItem.quantity).label('total_sold')).join(SaleItem).group_by(Battery.id).order_by(db.func.sum(SaleItem.quantity).desc()).limit(5).all()
    
    sales_data = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
            db.func.date(Sale.date) == date
        ).scalar() or 0
        sales_data.append({'date': date, 'sales': daily_sales})

    return render_template('dashboard.html', 
                           total_stock=total_stock, 
                           total_sales=total_sales, 
                           low_stock=low_stock,
                           top_selling=top_selling,
                           sales_data=sales_data)

@app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    if request.method == 'POST':

        barcode = request.form['barcode']

        # Duplicate barcode check
        existing = Battery.query.filter_by(barcode=barcode).first()
        if existing:
            flash("Battery with this barcode already exists", "danger")
            return redirect(url_for('inventory'))

        # Create new battery
        battery = Battery(
            model=request.form['model'],
            brand=request.form['brand'],
            voltage=request.form['voltage'],
            capacity=request.form['capacity'],
            price=request.form['price'],
            quantity=request.form['quantity'],
            barcode=barcode,
            warranty_period=request.form.get('warranty_period', 0),
            expiry_date=request.form.get('expiry_date'),
            supplier_id=request.form.get('supplier_id'),
            purchase_price=request.form.get('purchase_price')
        )

        db.session.add(battery)
        db.session.commit()

        # Generate QR code
        battery.generate_qr_code()

        flash('Battery added successfully', 'success')
        return redirect(url_for('inventory'))

    # Search batteries
    search = request.args.get('search', '')
    if search:
        batteries = Battery.query.filter(
            (Battery.model.contains(search)) |
            (Battery.barcode.contains(search)) |
            (Battery.brand.contains(search))
        ).all()
    else:
        batteries = Battery.query.all()

    suppliers = Supplier.query.all()

    return render_template(
        'inventory.html',
        batteries=batteries,
        suppliers=suppliers
    )
       
@app.route('/delete_battery/<int:id>')
@login_required
def delete_battery(id):
    battery = Battery.query.get_or_404(id)
    db.session.delete(battery)
    db.session.commit()
    flash('Battery deleted', 'success')
    return redirect(url_for('inventory'))

@app.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    if request.method == 'POST':

        barcode = request.form.get('barcode')
        battery = Battery.query.filter_by(barcode=barcode).first()

        if not battery:
            return jsonify({'success': False, 'message': 'Battery not found'})

        if battery.quantity <= 0:
            return jsonify({'success': False, 'message': 'Battery out of stock'})

        cart = session.get('cart', [])

        # 🔹 Duplicate scan check
        for item in cart:
            if item['id'] == battery.id:
                item['qty'] += 1
                session['cart'] = cart
                return jsonify({'success': True, 'message': 'Quantity updated'})

        # 🔹 Add new item
        cart.append({
            'id': battery.id,
            'model': battery.model,
            'price': battery.price,
            'qty': 1
        })

        session['cart'] = cart

        return jsonify({'success': True, 'message': 'Added to cart', 'item': battery.model})

    cart = session.get('cart', [])
    customers = Customer.query.all()

    return render_template('sales.html', cart=cart, customers=customers)
@app.route('/process_sale', methods=['POST'])
@login_required
def process_sale():

    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('sales'))

    customer_id = request.form.get('customer_id')

    # Invoice number
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 1️⃣ Create Sale
    sale = Sale(
        invoice_number=invoice_number,
        total_amount=0,
        customer_id=customer_id
    )

    db.session.add(sale)
    db.session.flush()   # 🔥 important (NOT commit)

    total = 0

    # 2️⃣ Process items
    for item in cart:
        battery = Battery.query.get(item['id'])

        if battery.quantity < item['qty']:
            flash(f"Insufficient stock for {battery.model}", "danger")
            return redirect(url_for('sales'))

        # Reduce stock
        battery.quantity -= item['qty']

        item_total = battery.price * item['qty']
        total += item_total

        sale_item = SaleItem(
            sale_id=sale.id,
            battery_id=battery.id,
            quantity=item['qty'],
            price_at_sale=battery.price,
            profit=battery.price - (battery.purchase_price or 0)
        )

        db.session.add(sale_item)

    # 3️⃣ Update total
    sale.total_amount = total

    # 4️⃣ Save everything
    db.session.commit()

    # 5️⃣ Clear cart
    session['cart'] = []

    # 6️⃣ Redirect to invoice
    return redirect(url_for('invoice', invoice_number=invoice_number))


@app.route('/invoice/<invoice_number>')
@login_required
def invoice(invoice_number):
    sale = Sale.query.filter_by(invoice_number=invoice_number).first()
    if not sale:
        flash('Invoice not found', 'danger')
        return redirect(url_for('sales'))
    
    return render_template('invoice.html', sale=sale)

@app.route('/export_invoice/<invoice_number>')
@login_required
def export_invoice(invoice_number):
    sale = Sale.query.filter_by(invoice_number=invoice_number).first()
    if not sale:
        return redirect(url_for('sales'))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("BATTERY STORE", styles['Title']))
    elements.append(Paragraph(f"Invoice: {sale.invoice_number}", styles['Heading2']))
    elements.append(Paragraph(f"Date: {sale.date.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Paragraph(f"Customer: {sale.customer.name if sale.customer else 'Walk-in'}", styles['Normal']))
    elements.append(Paragraph(f"Total: ${sale.total_amount:.2f}", styles['Heading3']))
    
    elements.append(Paragraph("Items:", styles['Heading3']))
    table_data = [["Model", "Qty", "Price", "Total"]]
    for item in sale.items:
        battery = Battery.query.get(item.battery_id)
        table_data.append([battery.model, item.quantity, f"${item.price_at_sale}", f"${item.price_at_sale * item.quantity}"])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"invoice_{invoice_number}.pdf", mimetype='application/pdf')

@app.route('/imports', methods=['GET', 'POST'])
@login_required
def imports():
    if request.method == 'POST':
        battery_id = request.form['battery_id']
        supplier_id = request.form['supplier_id']
        quantity = int(request.form['quantity'])
        purchase_price = float(request.form['purchase_price'])
        
        battery = Battery.query.get(battery_id)
        battery.quantity += quantity
        battery.purchase_price = purchase_price
        
        import_record = Import(
            battery_id=battery_id,
            supplier_id=supplier_id,
            quantity=quantity,
            total_cost=purchase_price * quantity
        )
        db.session.add(import_record)
        db.session.commit()
        flash('Import recorded successfully', 'success')
        return redirect(url_for('imports'))
    
    batteries = Battery.query.all()
    suppliers = Supplier.query.all()
    imports = Import.query.order_by(Import.date.desc()).all()
    return render_template('imports.html', batteries=batteries, suppliers=suppliers, imports=imports)

@app.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            phone=request.form['phone'],
            email=request.form['email'],
            address=request.form['address']
        )
        db.session.add(customer)
        db.session.commit()
        flash('Customer added successfully', 'success')
        return redirect(url_for('customers'))
    
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
def suppliers():
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form['name'],
            phone=request.form['phone'],
            email=request.form['email'],
            address=request.form['address']
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added successfully', 'success')
        return redirect(url_for('suppliers'))
    
    suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=suppliers)
@app.route("/find_battery_by_barcode/<barcode>")
def find_battery_by_barcode(barcode):

    battery = Battery.query.filter_by(barcode=barcode).first()

    if battery:
        return jsonify({
            "success": True,
            "battery_id": battery.id,
            "model": battery.model
        })

    return jsonify({"success": False})
@app.route('/export_excel')
def export_excel():
    return "Excel export working"
@app.route('/reports')
@login_required
def reports():

    sales = Sale.query.order_by(Sale.date.desc()).all()

    total_profit = db.session.query(db.func.sum(SaleItem.profit)).scalar() or 0

    total_products = db.session.query(db.func.sum(SaleItem.quantity)).scalar() or 0

    return render_template(
        'reports.html',
        sales=sales,
        total_profit=total_profit,
        total_products=total_products
    )

@app.route("/delete_supplier/<int:id>")
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash("Supplier deleted successfully", "success")
    return redirect(url_for("suppliers"))
@app.route('/import_stock')
def import_stock():
    return render_template('import_stock.html')  # Your template with above HTML

@app.route('/test_scanner')
def test_scanner():
    return render_template('test_scanner.html')
@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)

    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone = request.form['phone']
        customer.email = request.form['email']
        customer.address = request.form['address']

        db.session.commit()
        flash('Customer updated successfully', 'success')
        return redirect(url_for('customers'))

    return render_template('edit_customer.html', customer=customer)


@app.route('/delete_customer/<int:id>')
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully', 'success')
    return redirect(url_for('customers'))
@app.route('/analysis')
@login_required
def analysis():

    total_sales = db.session.query(db.func.sum(Sale.total_amount)).scalar() or 0

    total_profit = db.session.query(db.func.sum(SaleItem.profit)).scalar() or 0

    total_products = db.session.query(db.func.sum(SaleItem.quantity)).scalar() or 0

    top_products = db.session.query(
        Battery.model,
        db.func.sum(SaleItem.quantity).label('qty_sold')
    ).join(SaleItem, Battery.id == SaleItem.battery_id)\
     .group_by(Battery.model)\
     .order_by(db.func.sum(SaleItem.quantity).desc())\
     .all()

    return render_template(
        'analysis.html',
        total_sales=total_sales,
        total_profit=total_profit,
        total_products=total_products,
        top_products=top_products
    )
if __name__ == "__main__":
    app.run(debug=True, port=5001)