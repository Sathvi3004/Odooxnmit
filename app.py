from flask import Flask, render_template, request, redirect, url_for, session, flash
import csv
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# CSV file paths
USERS_CSV = 'users.csv'
PRODUCTS_CSV = 'products.csv'
CART_CSV = 'cart.csv'
PURCHASES_CSV = 'purchases.csv'

# Initialize CSV files with headers if they don't exist
def init_csv_files():
    csv_files = {
        USERS_CSV: ['id', 'username', 'email', 'password', 'full_name', 'phone', 'address', 'created_at'],
        PRODUCTS_CSV: ['id', 'title', 'description', 'price', 'category', 'location', 'seller_id', 'seller_name', 'seller_contact', 'status', 'created_at'],
        CART_CSV: ['id', 'user_id', 'product_id', 'quantity', 'added_at'],
        PURCHASES_CSV: ['id', 'buyer_id', 'product_id', 'seller_id', 'quantity', 'total_price', 'purchase_date', 'status']
    }

    for file, headers in csv_files.items():
        if not os.path.exists(file):
            with open(file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

# CSV helper functions
def read_csv(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []

def write_csv(filename, data, fieldnames):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        print(f"Error writing {filename}: {e}")

def append_to_csv(filename, data, fieldnames):
    try:
        file_exists = os.path.exists(filename)
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
    except Exception as e:
        print(f"Error appending to {filename}: {e}")

def get_user_by_id(user_id):
    users = read_csv(USERS_CSV)
    for user in users:
        if user['id'] == str(user_id):
            return user
    return None

def get_product_by_id(product_id):
    products = read_csv(PRODUCTS_CSV)
    for product in products:
        if product['id'] == str(product_id):
            return product
    return None

# Initialize CSV files
init_csv_files()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        # Validate required fields
        if not all([username, email, password, full_name]):
            flash('Please fill in all required fields!', 'error')
            return render_template('register.html', 
                                 username=username, email=email, 
                                 full_name=full_name, phone=phone, address=address)

        # Check for duplicates
        users = read_csv(USERS_CSV)
        if any(u.get('username') == username or u.get('email') == email for u in users):
            flash('Username or email already exists!', 'error')
            return render_template('register.html', 
                                 username=username, email=email, 
                                 full_name=full_name, phone=phone, address=address)

        user_id = str(uuid.uuid4())
        new_user = {
            'id': user_id,
            'username': username,
            'email': email,
            'password': password,  # In production, hash this password!
            'full_name': full_name,
            'phone': phone,
            'address': address,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        fieldnames = ['id', 'username', 'email', 'password', 'full_name', 'phone', 'address', 'created_at']
        append_to_csv(USERS_CSV, new_user, fieldnames)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Email and password are required!', 'error')
            return render_template('login.html', email=email)

        users = read_csv(USERS_CSV)
        user = next((u for u in users if u.get('email') == email and u.get('password') == password), None)

        if user:
            session['user_id'] = user.get('id')
            session['username'] = user.get('username', 'Unknown')
            session['full_name'] = user.get('full_name', user.get('username', 'Unknown'))
            flash(f'Welcome back, {session["full_name"]}!', 'success')
            return redirect(url_for('product_list'))
        else:
            flash('Invalid email or password!', 'error')
            return render_template('login.html', email=email)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/products')
def product_list():
    search_term = request.args.get('search', '').strip()
    selected_category = request.args.get('category', 'All')
    
    all_products = read_csv(PRODUCTS_CSV)
    
    # Filter available products only
    products = [p for p in all_products if p.get('status', 'available') == 'available']
    
    # Apply search filter
    if search_term:
        products = [p for p in products if 
                   search_term.lower() in p.get('title', '').lower() or 
                   search_term.lower() in p.get('description', '').lower()]
    
    # Get categories for dropdown
    categories = ['All'] + sorted(set(p.get('category', '') for p in all_products if p.get('category')))
    
    # Apply category filter
    if selected_category != 'All':
        products = [p for p in products if p.get('category', '') == selected_category]

    return render_template('product_list.html', 
                         products=products, 
                         categories=categories, 
                         search_term=search_term, 
                         selected_category=selected_category)

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('product_list'))
    
    seller = get_user_by_id(product.get('seller_id'))
    return render_template('product_detail.html', product=product, seller=seller)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        flash('Please login to add products!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0').strip()
        category = request.form.get('category', 'Other').strip()
        location = request.form.get('location', '').strip()
        
        # Validate required fields
        if not all([title, description, price, category]):
            flash('Please fill in all required fields!', 'error')
            return render_template('add_product.html')
        
        # Validate price
        try:
            float(price)
        except ValueError:
            flash('Please enter a valid price!', 'error')
            return render_template('add_product.html')
        
        current_user = get_user_by_id(session['user_id'])
        product_id = str(uuid.uuid4())
        
        new_product = {
            'id': product_id,
            'title': title,
            'description': description,
            'price': price,
            'category': category,
            'location': location,
            'seller_id': session['user_id'],
            'seller_name': current_user.get('full_name', session.get('username', 'Unknown')) if current_user else session.get('username', 'Unknown'),
            'seller_contact': current_user.get('phone', '') if current_user else '',
            'status': 'available',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        fieldnames = ['id', 'title', 'description', 'price', 'category', 'location', 'seller_id', 'seller_name', 'seller_contact', 'status', 'created_at']
        append_to_csv(PRODUCTS_CSV, new_product, fieldnames)
        flash('Product added successfully!', 'success')
        return redirect(url_for('my_listings'))
    
    return render_template('add_product.html')

@app.route('/my_listings')
def my_listings():
    if 'user_id' not in session:
        flash('Please login to view your listings!', 'error')
        return redirect(url_for('login'))
    
    my_products = [p for p in read_csv(PRODUCTS_CSV) if p.get('seller_id') == session['user_id']]
    return render_template('my_listings.html', products=my_products)

@app.route('/edit_product/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    products = read_csv(PRODUCTS_CSV)
    product_index = next((i for i, p in enumerate(products) 
                         if p.get('id') == product_id and p.get('seller_id') == session['user_id']), None)
    
    if product_index is None:
        flash('Product not found or you do not have permission to edit it!', 'error')
        return redirect(url_for('my_listings'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0').strip()
        category = request.form.get('category', 'Other').strip()
        location = request.form.get('location', '').strip()
        status = request.form.get('status', 'available').strip()
        
        # Validate required fields
        if not all([title, description, price, category]):
            flash('Please fill in all required fields!', 'error')
            return render_template('edit_product.html', product=products[product_index])
        
        # Validate price
        try:
            float(price)
        except ValueError:
            flash('Please enter a valid price!', 'error')
            return render_template('edit_product.html', product=products[product_index])
        
        products[product_index].update({
            'title': title,
            'description': description,
            'price': price,
            'category': category,
            'location': location,
            'status': status
        })
        
        fieldnames = ['id', 'title', 'description', 'price', 'category', 'location', 'seller_id', 'seller_name', 'seller_contact', 'status', 'created_at']
        write_csv(PRODUCTS_CSV, products, fieldnames)
        flash('Product updated successfully!', 'success')
        return redirect(url_for('my_listings'))

    return render_template('edit_product.html', product=products[product_index])

@app.route('/delete_product/<product_id>')
def delete_product(product_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    products = read_csv(PRODUCTS_CSV)
    original_count = len(products)
    products = [p for p in products if not (p.get('id') == product_id and p.get('seller_id') == session['user_id'])]
    
    if len(products) < original_count:
        if products:
            fieldnames = ['id', 'title', 'description', 'price', 'category', 'location', 'seller_id', 'seller_name', 'seller_contact', 'status', 'created_at']
            write_csv(PRODUCTS_CSV, products, fieldnames)
        else:
            # If no products left, recreate file with headers only
            init_csv_files()
        flash('Product deleted successfully!', 'success')
    else:
        flash('Product not found or you do not have permission to delete it!', 'error')
    
    return redirect(url_for('my_listings'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view your cart!', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_items = [item for item in read_csv(CART_CSV) if item.get('user_id') == user_id]
    
    # Enhance cart items with product details
    enhanced_cart = []
    for item in cart_items:
        product = get_product_by_id(item.get('product_id'))
        if product:
            item['product'] = product
            enhanced_cart.append(item)

    return render_template('cart.html', cart_items=enhanced_cart)

@app.route('/add_to_cart/<product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login to add items to cart!', 'error')
        return redirect(url_for('login'))
    
    product = get_product_by_id(product_id)
    if not product:
        flash('Product does not exist!', 'error')
        return redirect(url_for('product_list'))

    # Normalize status: remove spaces, convert to lowercase
    status = product.get('status', '').strip().lower()
    if status != 'available':
        flash(f'Product is not available for purchase (status: "{status}").', 'error')
        return redirect(url_for('product_list'))
    
    # Check if item already in cart
    cart_items = read_csv(CART_CSV)
    existing_item = next((item for item in cart_items 
                         if item.get('user_id') == session['user_id'] and 
                         item.get('product_id') == product_id), None)
    
    if existing_item:
        flash('Item already in cart!', 'info')
    else:
        cart_item = {
            'id': str(uuid.uuid4()),
            'user_id': session['user_id'],
            'product_id': product_id,
            'quantity': '1',
            'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        fieldnames = ['id', 'user_id', 'product_id', 'quantity', 'added_at']
        append_to_csv(CART_CSV, cart_item, fieldnames)
        flash('Item added to cart!', 'success')
    
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/remove_from_cart/<cart_item_id>')
def remove_from_cart(cart_item_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))

    # Load current cart items
    cart_items = read_csv(CART_CSV)
    user_id = session['user_id']

    # Filter out the item to remove (match both cart_item_id and user_id)
    filtered_items = [
        item for item in cart_items
        if not (item.get('id') == cart_item_id and item.get('user_id') == user_id)
    ]

    # Check if an item was actually removed
    if len(filtered_items) < len(cart_items):
        # Item was removed — save updated cart
        fieldnames = ['id', 'user_id', 'product_id', 'quantity', 'added_at']
        write_csv(CART_CSV, filtered_items, fieldnames)
        flash('Item removed from cart!', 'success')
    else:
        # No matching item found
        flash('Item not found in your cart!', 'error')

    return redirect(url_for('cart'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile!', 'error')
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('home'))

    return render_template('profile.html', user=user)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    users = read_csv(USERS_CSV)
    user_index = next((i for i, u in enumerate(users) if u.get('id') == session['user_id']), None)
    
    if user_index is None:
        flash('User not found!', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        if not full_name:
            flash('Full name is required!', 'error')
            return render_template('edit_profile.html', user=users[user_index])
        
        users[user_index].update({
            'full_name': full_name,
            'phone': phone,
            'address': address
        })
        
        fieldnames = ['id', 'username', 'email', 'password', 'full_name', 'phone', 'address', 'created_at']
        write_csv(USERS_CSV, users, fieldnames)
        
        # Update session
        session['full_name'] = full_name
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=users[user_index])
@app.route('/purchase_history')
def purchase_history():
    if 'user_id' not in session:
        flash('Please login to view your purchase history!', 'error')
        return redirect(url_for('login'))

    # Read all purchases from CSV
    purchases = read_csv(PURCHASES_CSV)
    
    # Filter purchases for current logged-in user
    user_purchases = [p for p in purchases if p.get('buyer_id') == session['user_id']]

    # Enhance each purchase with product info (title, price, etc.)
    for purchase in user_purchases:
        product = get_product_by_id(purchase.get('product_id'))
        if product:
            purchase['product_title'] = product.get('title', 'Unknown Product')
            purchase['product_price'] = product.get('price', '0.00')
        else:
            purchase['product_title'] = 'Deleted Product'
            purchase['product_price'] = '0.00'

    return render_template('purchase_history.html', purchases=user_purchases)
@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    # You can show cart summary here
    flash('Proceeding to checkout...', 'info')
    return render_template('checkout.html')  # Create this template later

if __name__ == '__main__':
    app.run(debug=True)