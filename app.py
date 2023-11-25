from flask_caching import Cache
from flask_cors import CORS
from flask import Flask, Flask, render_template, request, jsonify, Response, session, redirect, url_for, send_from_directory, make_response, g, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from collections import Counter
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup, Comment
from werkzeug.utils import secure_filename
from datetime import datetime


import logging
import io
import json
import os
import re
import time
import sqlite3
import pyotp  # Importing pyotp for 2FA
import random
import string
from datetime import timedelta
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///s.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/imguploads'  # Set the upload folder here
app.secret_key = 'ZDlGoz5V4/CWj+OGx8h2vQ=='  # You should use a secure, random secret key.
CORS(app)  # This is to allow cross-origin requests, if needed.

db = SQLAlchemy(app)

class Shape(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shape_data = db.Column(db.JSON, nullable=False)
    shape_note = db.Column(db.String, nullable=True)
    shape_type = db.Column(db.String, nullable=False)
    shape_color = db.Column(db.String, nullable=True)
    shape_imagelink = db.Column(db.String, nullable=True)  # Column to store image link
    molen_id = db.Column(db.String, nullable=True, default="null")
    score = db.Column(db.String, nullable=True, default="null")
    highlight_id = db.Column(db.String, nullable=True, default="null")
    radius = db.Column(db.Float, nullable=True)

@app.before_request
def before_request():
    if not hasattr(g, 'db_initialized'):
        db.create_all()
        g.db_initialized = True

@app.route('/')
def index():
    total_objects, category_counts, color_counts = count_objects()  # Assuming count_objects is already defined as per your previous messages.
    return render_template('index.html', category_counts=category_counts, color_counts=color_counts, favicon=favicon)


@app.route('/categories')
def categories():
    return render_template('categories.html')
    

@app.route('/favicon.ico')
def favicon():
    app.logger.debug('Favicon loaded successfully')  # Add this debug message
    return url_for('static', filename='favicon.ico')



@app.route('/api/shapes', methods=['POST'])
def add_shape2():
    try:
        print("Request method:", request.method)
        print("Is JSON:", request.is_json)

        # Check if the request is JSON
        if request.is_json:
            data = request.json
            shape_data_json = json.dumps(data.get('shape_data', {}))
            shape_note = data.get('shape_note', '')  # For JSON requests
        else:
            # Handling Form data
            data = request.form
            shape_data_json = data.get('shape_data', '{}')
            shape_note = data.get('note', '')  # For form data, the key is 'note'

        print("Shape Note:", shape_note)
        print("Form Data:", data)

        new_shape = Shape(
            shape_data=shape_data_json,
            shape_note=shape_note,
            shape_type=data.get('shape_type', ''),
            shape_color=data.get('shape_color', '#212120'),
            molen_id=data.get('molen_id', 'null'),
            score=data.get('score', 'null'),
            highlight_id=data.get('highlight_id', 'null')
        )

        radius = data.get('radius')
        if new_shape.shape_type == 'circle' and radius and radius != 'null':
            new_shape.radius = float(radius)
        else:
            new_shape.radius = None

        if 'shape_image' in request.files:
            image = request.files['shape_image']
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                image.save(image_path)
                new_shape.shape_imagelink = image_path
                print(f"Image saved at {image_path}")
            else:
                print("No image uploaded")

        if hasattr(new_shape, 'shape_imagelink'):
            print("Image Link:", new_shape.shape_imagelink)

        db.session.add(new_shape)
        db.session.commit()
        print(f"New shape added with ID: {new_shape.id}")

        return jsonify(success=True, id=new_shape.id, image_link=getattr(new_shape, 'shape_imagelink', None))

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify(success=False, error=str(e)), 500
    
@app.route('/api/colorOrder')
def color_order():
    try:
        with open('templates/categories.html', 'r') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            colors = [button['style'].split(': ')[1] for button in soup.find_all('button', {'class': 'categorybutton'})]
            return jsonify({'colorOrder': colors})
    except Exception as e:
        print(f"Error retrieving color order: {e}")
        return jsonify({'error': 'Could not retrieve color order'}), 500

@app.route('/api/shapes', methods=['GET'])
def get_shapes():
    shapes = Shape.query.all()
    shapes_data = []

    for shape in shapes:
        # Construct the shape data
        shape_info = {
            'id': shape.id,
            'shape_data': json.loads(shape.shape_data),
            'shape_type': shape.shape_type,
            'shape_color': shape.shape_color,
            'radius': shape.radius,
            'shape_note': shape.shape_note,
            'shape_imagelink': shape.shape_imagelink
        }
        shapes_data.append(shape_info)

        # Print the name of the image file if it exists
        if shape.shape_imagelink:
            image_name = os.path.basename(shape.shape_imagelink)
            print(f"Image file fetched: {image_name}")

    print('Shapes fetched:', len(shapes_data))
    return jsonify(shapes=shapes_data)




@app.route('/api/add-shape', methods=['POST'])
def add_shape():
    shape_data = request.json.get('shape_data')
    shape_note = request.json.get('shape_note', '')
    shape_type = request.json.get('shape_type')
    shape_color = request.json.get('shape_color', '#FFFFFF')

    new_shape = Shape(shape_data=shape_data, shape_note=shape_note, shape_type=shape_type, shape_color=shape_color)
    db.session.add(new_shape)
    db.session.commit()

    return jsonify({'success': True, 'id': new_shape.id})
    
@app.route('/api/shapes/<int:shape_id>', methods=['DELETE'])
def delete_shape(shape_id):
    shape = Shape.query.get(shape_id)
    if shape:
        db.session.delete(shape)
        db.session.commit()
        print('Shape deleted with ID:', shape_id)

        # Call the get_shapes route to fetch the updated list of shapes
        updated_shapes_data = get_shapes().get_json()
        return jsonify(success=True, shapes=updated_shapes_data['shapes']), 200
    else:
        print('Shape not found with ID:', shape_id)
        return jsonify(success=False), 404


# Hardcoded user credentials and OTP secret
USER_CREDENTIALS = {
    'username': 'stimmungskarte',
    'password': 'techdemo',
}
OTP_SECRET = 'MangoOttersLove'

@app.route('/login', methods=['POST'])
def login():
    # Get form data
    username = request.form.get('username')
    password = request.form.get('password')
    otp_token = request.form.get('otp')
    
    # Validate username and password
    if username == USER_CREDENTIALS['username'] and password == USER_CREDENTIALS['password']:
        # Validate OTP token
        totp = pyotp.TOTP(OTP_SECRET)
        if totp.verify(otp_token):
            session['logged_in'] = True  # Set the session as logged in
            app.logger.info('User logged in successfully.')
            return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
        else:
            return jsonify({'status': 'failed', 'message': 'Incorrect OTP. Please contact your administrator.'}), 401
    else:
        return jsonify({'status': 'failed', 'message': 'Invalid credentials'}), 401


@app.route('/is-authenticated', methods=['GET'])
def is_authenticated():
    # Check if 'logged_in' key is in the session and if it's True
    if 'logged_in' in session and session['logged_in']:
        return jsonify({'isAuthenticated': True}), 200
    else:
        return jsonify({'isAuthenticated': False}), 401


@app.route('/admintools')
def admintools():
    if 'logged_in' in session and session['logged_in']:
        app.logger.info('Serving admin tools to an authenticated user.')
        return send_from_directory('.', 'admintools.html')
    else:
        app.logger.warning('Unauthorized attempt to access admin tools.')
        return jsonify({'status': 'failed', 'message': 'Unauthorized access'}), 401

 

@app.route('/filter-shapes', methods=['POST'])
def filter_shapes():
    data = request.json
    color_filter = data.get('color')
    type_filter = data.get('type')

    query = Shape.query
    if color_filter:
        query = query.filter(Shape.shape_color == color_filter)
    if type_filter:
        query = query.filter(Shape.shape_type == type_filter)

    shapes = query.all()
    shapes_data = [
        {
            'id': shape.id,
            'shape_data': json.loads(shape.shape_data),
            'shape_type': shape.shape_type,
            'shape_color': shape.shape_color,
            'radius': shape.radius,
            'shape_note': shape.shape_note
        } for shape in shapes
    ]
    return jsonify(shapes=shapes_data)



# OVERLAY IMAGE REPLACEMENT (TITELBILD) START
@app.route('/upload_overlay', methods=['GET'])
def upload_overlay():
    return render_template('upload.html')

@app.route('/upload_overlay_image', methods=['POST'])
def upload_overlay_image():
    file = request.files['file']
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.root_path, 'static', 'overlay.jpg'))
        return redirect(url_for('index'))  # Redirect to home page after successful upload
    return "File upload failed!", 400
# OVERLAY IMAGE REPLACEMENT (TITELBILD) END


@app.route('/get-categories')
def get_categories():
    try:
        with open('templates/categories.html', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            categories = [{'color': button['style'].split(': ')[1].replace(';', '').strip(), 'text': button.h3.text}
                          for button in soup.find_all('button', {'class': 'categorybutton'})]
            categories.append({'color': 'null', 'text': ''})
        print("Categories fetched successfully:", categories)  # Debugging statement
        return jsonify(categories)
    except Exception as e:
        print(f"Error occurred in get_categories: {e}")  # Debugging statement
        return jsonify(error=str(e)), 500





@app.route('/update-category', methods=['POST'])
def update_category():
    logging.basicConfig(level=logging.DEBUG)

    try:
        color_to_update = request.json.get('oldColor')
        new_color = request.json.get('newColor')

        # Validating the input colors
        if not color_to_update or not new_color:
            logging.error(f"Invalid color data: oldColor={color_to_update}, newColor={new_color}")
            return jsonify(success=False, message="Invalid color data"), 400

        # Reading the HTML content with UTF-8 encoding
        with open('templates/categories.html', 'r', encoding='utf-8') as file:
            content = file.read()

        logging.debug(f"Original HTML content: {content}")

        soup = BeautifulSoup(content, 'html.parser')
        updated = False

        for button in soup.find_all('button', {'class': 'categorybutton'}):
            if color_to_update in button['style']:
                button['style'] = f"background-color: {new_color};"
                button['onclick'] = f"parent.setCategory('{new_color}')"
                updated = True

        # Writing the updated content back to the file with UTF-8 encoding, if necessary
        if updated:
            updated_html = str(soup)
            logging.debug(f"Updated HTML content: {updated_html}")
            with open('templates/categories.html', 'w', encoding='utf-8') as file:
                file.write(updated_html)
            return jsonify(success=True)
        else:
            return jsonify(success=False, message="Color not found"), 404

    except FileNotFoundError:
        logging.exception("File not found error")
        return jsonify(success=False, error="File not found"), 500
    except Exception as e:
        logging.exception("Unexpected error occurred")
        return jsonify(success=False, error=str(e)), 500

    
@app.route('/update-shape-colors', methods=['POST'])
def update_shape_colors():
    data = request.json
    old_color = data.get('oldColor')
    new_color = data.get('newColor')

    try:
        # Update the shapes with the old color to the new color
        Shape.query.filter_by(shape_color=old_color).update({'shape_color': new_color})
        db.session.commit()
        return jsonify(success=True), 200
    except Exception as e:
        print(f"Error updating shape colors: {e}")
        return jsonify(success=False, error=str(e)), 500
        
@app.route('/rename-category', methods=['POST'])
def rename_category():
    color = request.json.get('color')
    new_name = request.json.get('newName')
    
    try:
        with open('templates/categories.html', 'r+', encoding='utf-8') as file:  # Specify UTF-8 encoding
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            buttons = soup.find_all('button', {'class': 'categorybutton'})
            for button in buttons:
                if color in button['style']:
                    button.h3.string = new_name  # Update the text within the <h3> tag
            file.seek(0)
            file.write(str(soup))
            file.truncate()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while renaming category: {e}")
        return jsonify(success=False, error=str(e)), 500



@app.route('/create-category', methods=['POST'])
def create_category():
    name = request.json.get('name')
    color = request.json.get('color')
    
    try:
        with open('templates/categories.html', 'r+', encoding='utf-8') as file:  # Specify UTF-8 encoding
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Create a new button element for the category
            new_button = soup.new_tag('button', **{
                'class': 'categorybutton',
                'onclick': f"parent.setCategory('{color}')",
                'style': f"background-color: {color};"
            })
            new_button_h3 = soup.new_tag('h3')
            new_button_h3.string = name
            new_button.append(new_button_h3)
            
            # Insert the new button before the end comment
            end_comment = soup.find(string=lambda text: isinstance(text, Comment) and 'ENDING OF CATEGORY EDITING AREA' in text)
            end_comment.insert_before(new_button)

            # Write the updated HTML back to the file
            file.seek(0)
            file.write(str(soup))
            file.truncate()

        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while creating new category: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/delete-category', methods=['POST'])
def delete_category():
    color_to_delete = request.json.get('color')
    
    try:
        # Delete categories from the HTML file
        with open('templates/categories.html', 'r+') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            for button in soup.find_all('button', {'class': 'categorybutton'}):
                if color_to_delete in button['style']:
                    button.decompose()
            file.seek(0)
            file.write(str(soup))
            file.truncate()
        
        # Delete shapes with the corresponding color from the database
        shapes_to_delete = Shape.query.filter_by(shape_color=color_to_delete).all()
        for shape in shapes_to_delete:
            db.session.delete(shape)
        db.session.commit()
        
        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while deleting category: {e}")
        db.session.rollback()  # Roll back the session in case of an error
        return jsonify(success=False, error=str(e)), 500
 
@app.route('/export-geojson', methods=['GET'])
def export_geojson():
    # Query all shapes from the database
    shapes = Shape.query.all()
    
    # Construct GeoJSON features list
    features = []
    for shape in shapes:
        # Parse shape data and create GeoJSON feature
        feature = {
            "type": "Feature",
            "geometry": json.loads(shape.shape_data),
            "properties": {
                "id": shape.id,
                "note": shape.shape_note,
                "type": shape.shape_type,
                "color": shape.shape_color,
                "molen_id": shape.molen_id,
                "score": shape.score,
                "highlight_id": shape.highlight_id,
                "radius": shape.radius,
                "imagelink": shape.shape_imagelink
            }
        }
        features.append(feature)
    
    # Construct the full GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Convert the GeoJSON to a string and then to a BytesIO object for file download
    geojson_str = json.dumps(geojson, indent=2)
    geojson_bytes = io.BytesIO(geojson_str.encode('utf-8'))
    
    # Send the GeoJSON file to the client
    return send_file(geojson_bytes, mimetype='application/json',
    as_attachment=True, download_name='shapes_export.geojson')

@app.route('/import-geojson', methods=['POST'])
def import_geojson():
    try:
        uploaded_file = request.files['file']
        if uploaded_file:
            geojson_data = json.load(uploaded_file)
            for feature in geojson_data['features']:
                shape_data = json.dumps(feature['geometry'])
                shape_note = feature['properties']['note']
                shape_type = feature['properties']['type']
                shape_color = feature['properties']['color']
                molen_id = feature['properties']['molen_id']
                score = feature['properties']['score']
                highlight_id = feature['properties']['highlight_id']
                radius = feature['properties']['radius']
                shape = Shape(
                    shape_data=shape_data,
                    shape_note=shape_note,
                    shape_type=shape_type,
                    shape_color=shape_color,
                    molen_id=molen_id,
                    score=score,
                    highlight_id=highlight_id,
                    radius=radius
                )
                db.session.add(shape)
            db.session.commit()
            return '''
                <script>
                    alert('GeoJSON data imported successfully');
                    window.location.href = '/';
                </script>
            '''
        else:
            return '''
                <script>
                    alert('No file uploaded');
                    window.location.href = '/';
                </script>
            '''
    except Exception as e:
        return '''
            <script>
                alert('Error: {}');
                window.location.href = '/';
            </script>
        '''.format(str(e))

# Function to count all objects, category objects, and colors
def count_objects():
    total_objects = Shape.query.count()
    categories = Shape.query.with_entities(Shape.shape_type).distinct()
    category_counts = {}
    color_counts = {}

    for category in categories:
        category_counts[category[0]] = Shape.query.filter_by(shape_type=category[0]).count()

    # Count objects by color
    colors = Shape.query.with_entities(Shape.shape_color).distinct()
    for color in colors:
        color_counts[color[0]] = Shape.query.filter_by(shape_color=color[0]).count()

    return total_objects, category_counts, color_counts

# Route to display counts
# Change the return value to jsonify the counts
@app.route('/count-objects')
def display_counts():
    total_objects, category_counts, color_counts = count_objects()
    return jsonify({
        'total_objects': total_objects, 
        'category_counts': category_counts, 
        'color_counts': color_counts
    })  
 
@app.route('/update-allowed-object-types', methods=['POST'])
def update_allowed_object_types():
    data = request.json
    print("Received allowed object types:", data)
    # Save the data to a file or database as needed
    with open('allowed_object_types.json', 'w') as file:
        json.dump(data, file)
    return jsonify(success=True, message="Allowed object types updated successfully")

@app.route('/get-allowed-object-types')
def get_allowed_object_types():
    # Read the settings from the file where you saved them
    try:
        with open('allowed_object_types.json', 'r') as file:
            data = json.load(file)
            return jsonify(data)
    except FileNotFoundError:
        # If the file doesn't exist, return default values (all true, for example)
        return jsonify({'marker': True, 'rectangle': True, 'circle': True, 'polygon': True})

 

# Route to delete objects by category
@app.route('/delete-objects-by-category', methods=['POST'])
def delete_objects_by_category():
    data = request.json
    color_to_delete = data.get('color')

    try:
        # Delete objects with the corresponding category color from the database
        objects_to_delete = Shape.query.filter_by(shape_color=color_to_delete).all()
        for obj in objects_to_delete:
            db.session.delete(obj)
        db.session.commit()

        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while deleting objects by category: {e}")
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500

# Route to delete objects by object type
@app.route('/delete-objects-by-object-type', methods=['POST'])
def delete_objects_by_object_type():
    data = request.json
    object_type_to_delete = data.get('objectType')

    try:
        # Delete objects with the corresponding object type from the database
        objects_to_delete = Shape.query.filter_by(shape_type=object_type_to_delete).all()
        for obj in objects_to_delete:
            db.session.delete(obj)
        db.session.commit()

        return jsonify(success=True)
    except Exception as e:
        print(f"Error occurred while deleting objects by object type: {e}")
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/all-shapes', methods=['GET'])
def get_all_shapes():
    shapes = Shape.query.all()
    shapes_data = [
        {
            'id': shape.id,
            'shape_type': shape.shape_type,
            'shape_color': shape.shape_color,
            'shape_note': shape.shape_note
        } for shape in shapes
    ]
    return jsonify(shapes=shapes_data)

@app.route('/save_popup_content', methods=['POST'])
def save_popup_content():
    content = request.form['content']
    # Use BeautifulSoup or any other method to process the content
    # Save to popup_content.html
    with open('popup_content.html', 'w') as file:
        file.write(content)
    return 'Success'

@app.route('/api/delete-object/<int:object_id>', methods=['DELETE'])
def delete_object(object_id):
    try:
        # Find the object by its ID and delete it from the database
        object_to_delete = Shape.query.get(object_id)
        if object_to_delete:
            db.session.delete(object_to_delete)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Object deleted successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Object not found.'}), 404
    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        return jsonify({'success': False, 'message': str(e)}), 500
        
        
# Load or initialize pin size settings
def load_pin_settings():
    try:
        with open('pinsize.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {'pin_size': 32, 'outline_size': 16}

# Save pin size settings
def save_pin_settings(settings):
    with open('pinsize.json', 'w') as file:
        json.dump(settings, file)

# Update index.html with new pin sizes
def update_svg(pin_size, outline_size):
    file_path = 'templates/index.html'  # Ensure this is the correct path
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Regex pattern to find and capture the SVG string
    svg_pattern = r'var svgIcon = `(<svg[^>]*>.*?</svg>)`;'
    match = re.search(svg_pattern, content, re.DOTALL)

    if not match:
        print("Error: SVG pattern not found in index.html")
        return

    # Extract the current SVG string
    svg_string = match.group(1)
    
    # Use BeautifulSoup to modify the SVG
    soup = BeautifulSoup(svg_string, 'html.parser')
    circles = soup.find_all('circle')
    if len(circles) != 2:
        print(f"Error: Expected 2 <circle> elements, found {len(circles)}")
        return

    circle1, circle2 = circles
    circle1['r'] = str(pin_size // 2)
    circle2['r'] = str(pin_size // 2)
    circle2['stroke-width'] = str(outline_size)

    # Replace the old SVG string with the modified one
    modified_svg_string = str(soup)
    modified_content = re.sub(svg_pattern, f'var svgIcon = `{modified_svg_string}`;', content, flags=re.DOTALL)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

    print("SVG updated successfully")


@app.route('/update_sizes', methods=['POST'])
def update_sizes():
    data = request.json
    pin_size = data['pin_size']
    outline_size = data['outline_size']

    settings = load_pin_settings()
    settings['pin_size'] = pin_size
    settings['outline_size'] = outline_size
    save_pin_settings(settings)

    update_svg(pin_size, outline_size)
    return jsonify({'message': 'Sizes updated successfully'})

@app.route('/get-category-order')
def get_category_order():
    try:
        with open('templates/categories.html', 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            categories = [button['style'].split(':')[1].strip().replace(';', '') 
                          for button in soup.find_all('button', {'class': 'categorybutton'})]
        return jsonify(categories)
    except Exception as e:
        print(f"Error occurred while fetching category order: {e}")
        return jsonify(success=False, error=str(e)), 500
   
if __name__ == '__main__':
    app.run(debug=True)
