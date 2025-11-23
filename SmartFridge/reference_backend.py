import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS
import pymysql
from dotenv import load_dotenv
import uuid
import datetime
import logging
import requests
import json
from gtts import gTTS
import io
import subprocess
import signal
import sys
import time

load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASS', 'Enjoylife@123')
DB_NAME = os.getenv('DB_NAME', 'smartfridge')
APP_PORT = int(os.getenv('PORT', '3001'))

# Google Gemini API Key (FREE - get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'xxxxxxxxx')

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'folder'

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path='')
CORS(app)  # allow all origins for development; tighten in production

# Basic logging to console for easier debugging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Which table to use for items. Set in init_db_if_needed()
TABLE_NAME = None

# Camera process management
camera_process = None


def get_conn():
    # Return a new pymysql connection using env settings
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=5,
    )


def init_db_if_needed():
    # Ensure the items and recipes tables exist. This will run at startup.
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Decide which table to use for items. If a legacy `item` table exists, prefer it
        cur.execute('SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema=%s AND table_name=%s', (DB_NAME, 'item'))
        r = cur.fetchone() or {}
        legacy_exists = r.get('cnt', 0) > 0

        global TABLE_NAME
        if legacy_exists:
            TABLE_NAME = 'item'
            app.logger.info('Using legacy table `item` for items storage')
        else:
            TABLE_NAME = 'items'
            # Create the new `items` table only when legacy does not exist
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id VARCHAR(36) PRIMARY KEY,
                    label VARCHAR(255),
                    quantity VARCHAR(100),
                    expiry_date VARCHAR(100),
                    location VARCHAR(255),
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

        # Ensure recipes table exists (safe to create)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id VARCHAR(36) PRIMARY KEY,
                title TEXT,
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        conn.commit()
    except Exception:
        # Do not crash startup if DB isn't available; routes will surface errors.
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/')
def serve_index():
    # Serve frontend index.html from folder
    return send_from_directory(str(STATIC_DIR), 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(str(STATIC_DIR), filename)


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/items', methods=['GET'])
def api_get_items():
    try:
        conn = get_conn()
        cur = conn.cursor()
        if TABLE_NAME == 'item':
            cur.execute('SELECT id, label, quantity, expiry_date, location FROM item')
        else:
            cur.execute('SELECT id, label, quantity, expiry_date, location FROM items')
        rows = cur.fetchall()
        conn.close()
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        app.logger.exception('Failed to GET /api/items')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/items', methods=['POST'])
def api_add_item():
    data = request.get_json(force=True)
    if not data.get('label'):
        return jsonify({'success': False, 'message': 'Missing label'}), 400
    item_id = str(uuid.uuid4())
    try:
        # Normalize payload: convert empty strings to None for DB
        label = data.get('label')
        quantity = data.get('quantity') or None
        expiry_date = data.get('expiry_date') or None
        location = data.get('location') or None
        source = data.get('source', 'manual')  # NEW: track source (manual or camera)
        confidence = data.get('confidence', None)  # NEW: camera detection confidence

        app.logger.info('Adding item: %s', {'label': label, 'quantity': quantity, 'expiry_date': expiry_date, 'location': location, 'source': source})

        conn = get_conn()
        cur = conn.cursor()
        if TABLE_NAME == 'item':
            # Insert into legacy `item` table (auto-increment id)
            if source == 'camera':
                # Camera-detected item
                cur.execute(
                    'INSERT INTO item (label, quantity, location, added_date, expiry_date, status, source, confidence, camera_last_seen) VALUES (%s,%s,%s,NOW(),%s,%s,%s,%s,NOW())',
                    (label, quantity, location, expiry_date, 'Fresh', source, confidence)
                )
            else:
                # Manual item
                cur.execute(
                    'INSERT INTO item (label, quantity, location, added_date, expiry_date, status, source) VALUES (%s,%s,%s,NOW(),%s,%s,%s)',
                    (label, quantity, location, expiry_date, 'Fresh', source)
                )
            conn.commit()
            inserted_id = cur.lastrowid
            conn.close()
            app.logger.info('Item added to `item` with id (autoinc): %s from %s', inserted_id, source)
            return jsonify({'success': True, 'id': inserted_id, 'source': source})
        else:
            # Insert into new `items` table (UUID id)
            cur.execute(
                'INSERT INTO items (id, label, quantity, expiry_date, location) VALUES (%s,%s,%s,%s,%s)',
                (item_id, label, quantity, expiry_date, location)
            )
            conn.commit()
            conn.close()
            app.logger.info('Item added to `items` with id: %s', item_id)
            return jsonify({'success': True, 'id': item_id})
    except Exception as e:
        app.logger.exception('Failed to POST /api/items')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/items/<item_id>', methods=['DELETE'])
def api_delete_item(item_id):
    try:
        conn = get_conn()
        cur = conn.cursor()
        if TABLE_NAME == 'item':
            cur.execute('DELETE FROM item WHERE id=%s', (item_id,))
        else:
            cur.execute('DELETE FROM items WHERE id=%s', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.exception('Failed to DELETE /api/items/%s', item_id)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/heartbeat', methods=['POST'])
def api_camera_heartbeat():
    """Update camera_last_seen timestamp for detected items"""
    try:
        data = request.get_json(force=True)
        labels = data.get('labels', [])  # List of currently detected item labels
        
        if not labels:
            return jsonify({'success': True, 'updated': 0})
        
        conn = get_conn()
        cur = conn.cursor()
        updated_count = 0
        
        # Update camera_last_seen for all currently detected items
        for label in labels:
            if TABLE_NAME == 'item':
                cur.execute(
                    "UPDATE item SET camera_last_seen=NOW() WHERE label=%s AND source='camera'",
                    (label,)
                )
                updated_count += cur.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'updated': updated_count})
    except Exception as e:
        app.logger.exception('Camera heartbeat failed')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/cleanup', methods=['POST'])
def api_camera_cleanup():
    """Remove camera items that haven't been seen for 7+ seconds"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Delete camera items not seen in last 7 seconds
        if TABLE_NAME == 'item':
            cur.execute("""
                DELETE FROM item 
                WHERE source='camera' 
                AND camera_last_seen < DATE_SUB(NOW(), INTERVAL 7 SECOND)
            """)
            deleted_count = cur.rowcount
        else:
            deleted_count = 0
        
        conn.commit()
        conn.close()
        
        app.logger.info('Camera cleanup removed %d stale items', deleted_count)
        return jsonify({'success': True, 'removed': deleted_count})
    except Exception as e:
        app.logger.exception('Camera cleanup failed')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/items', methods=['GET'])
def api_get_camera_items():
    """Get all camera-detected items"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        if TABLE_NAME == 'item':
            cur.execute("SELECT id, label, quantity, confidence, camera_last_seen FROM item WHERE source='camera'")
        else:
            cur.execute("SELECT id, label FROM items WHERE 1=0")  # No camera support in new table yet
        rows = cur.fetchall()
        conn.close()
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        app.logger.exception('Failed to GET camera items')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/generate_recipe', methods=['POST'])
def api_generate_recipe():
    """Generate recipe suggestions using FREE Google Gemini API"""
    try:
        # Fetch current items from database
        conn = get_conn()
        cur = conn.cursor()
        if TABLE_NAME == 'item':
            cur.execute('SELECT label, quantity, expiry_date FROM item ORDER BY expiry_date ASC')
        else:
            cur.execute('SELECT label, quantity, expiry_date FROM items ORDER BY expiry_date ASC')
        items = cur.fetchall()
        conn.close()

        if not items or len(items) == 0:
            return jsonify({'success': False, 'message': 'No items in inventory to generate recipes'}), 400

        # Build ingredient list
        ingredients_list = [item['label'] for item in items[:10]]
        ingredients_text = ", ".join(ingredients_list)
        
        app.logger.info('Generating recipes for ingredients: %s', ingredients_text)

        # Try Google Gemini API (FREE - 60 requests/minute)
        if GEMINI_API_KEY:
            try:
                app.logger.info('Using Google Gemini API for recipe generation')
                
                # Use REST API with the correct current model
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                
                prompt = f"""Create 3-5 traditional Indian recipes (South Indian and North Indian cuisine) using these ingredients from my fridge: {ingredients_text}

IMPORTANT GUIDELINES:
1. Focus on authentic Indian dishes (e.g., dosa, biryani, curry, dal, sabzi, paratha, upma, sambar, rasam, paneer dishes)
2. Use ingredients from the fridge as the base
3. You may suggest adding common Indian pantry staples like: rice, flour, spices (turmeric, cumin, coriander), oil, salt, onions, tomatoes, ginger, garlic, green chilies
4. DO NOT mix sweet and savory items together (e.g., no milk with curry)
5. Keep recipes authentic and traditional - avoid fusion or unusual combinations
6. Each recipe should be practical and easy to cook

For each recipe, provide:
1. A traditional Indian recipe name
2. Main ingredients (from fridge) + suggested common staples if needed
3. Brief cooking instructions (2-3 sentences)

Return ONLY a JSON array in this exact format:
[
  {{
    "title": "Traditional Recipe Name",
    "ingredients": "fridge_item1, fridge_item2, + suggested: staple1, staple2",
    "instructions": "Brief traditional cooking steps..."
  }}
]

No extra text, just the JSON array with 3-5 authentic Indian recipes."""

                headers = {'Content-Type': 'application/json'}
                data = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    app.logger.info('Gemini API response received')
                    
                    # Extract text from response
                    ai_response = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    app.logger.info('Gemini text: %s', ai_response[:200])
                    # Extract text from response
                    ai_response = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    app.logger.info('Gemini text: %s', ai_response[:200])
                    
                    # Parse JSON response
                    try:
                        # Clean up response - remove markdown code blocks if present
                        if '```json' in ai_response:
                            ai_response = ai_response.split('```json')[1].split('```')[0]
                        elif '```' in ai_response:
                            ai_response = ai_response.split('```')[1].split('```')[0]
                        
                        ai_response = ai_response.strip()
                        
                        # Find JSON array
                        start_idx = ai_response.find('[')
                        end_idx = ai_response.rfind(']') + 1
                        if start_idx != -1 and end_idx > start_idx:
                            json_str = ai_response[start_idx:end_idx]
                            recipes = json.loads(json_str)
                        else:
                            raise ValueError("No JSON array found in response")
                            
                    except Exception as parse_error:
                        app.logger.warning('Could not parse Gemini JSON: %s', str(parse_error))
                        # Create a simple recipe from the response
                        recipes = [{
                            "title": f"Recipe with {ingredients_list[0]}",
                            "ingredients": ingredients_text[:100],
                            "instructions": ai_response[:300] if ai_response else "Mix ingredients and cook as desired."
                        }]
                    
                    # Save recipes to database
                    conn = get_conn()
                    cur = conn.cursor()
                    saved_count = 0
                    
                    for recipe in recipes[:3]:
                        rid = str(uuid.uuid4())
                        try:
                            cur.execute(
                                'INSERT INTO RecipeSuggestion (id, title, ingredients, instructions, created_at) VALUES (%s,%s,%s,%s,NOW())',
                                (rid, recipe.get('title', 'Untitled')[:255], recipe.get('ingredients', '')[:500], recipe.get('instructions', '')[:1000])
                            )
                            saved_count += 1
                        except:
                            try:
                                cur.execute('INSERT INTO recipes (id, title, created_at) VALUES (%s,%s,NOW())',
                                            (rid, recipe.get('title', 'Untitled')[:255]))
                                saved_count += 1
                            except:
                                pass
                    
                    conn.commit()
                    conn.close()
                    
                    app.logger.info('Saved %d Gemini recipes to database', saved_count)
                    return jsonify({'success': True, 'recipes': recipes[:3]})
                
                else:
                    app.logger.error('Gemini API error: %s - %s', response.status_code, response.text)
                    raise Exception(f"Gemini API returned {response.status_code}")
                    
            except Exception as gemini_error:
                app.logger.warning('Gemini API failed: %s, falling back to simple recipes', str(gemini_error))

        # Fallback: Generate smart rule-based recipes (NO API KEY NEEDED)
        app.logger.info('Using fallback recipe generation (no API key)')
        
        # Categorize ingredients intelligently
        proteins = [i['label'] for i in items if any(x in i['label'].lower() for x in ['chicken', 'beef', 'pork', 'fish', 'egg', 'tofu', 'bacon', 'turkey', 'shrimp'])]
        veggies = [i['label'] for i in items if any(x in i['label'].lower() for x in ['lettuce', 'tomato', 'carrot', 'pepper', 'onion', 'spinach', 'broccoli', 'cucumber', 'celery'])]
        carbs = [i['label'] for i in items if any(x in i['label'].lower() for x in ['bread', 'rice', 'pasta', 'potato', 'noodle', 'tortilla'])]
        dairy = [i['label'] for i in items if any(x in i['label'].lower() for x in ['milk', 'cheese', 'butter', 'yogurt', 'cream'])]
        
        recipes = []
        
        # Recipe 1: Main dish with protein
        if proteins:
            main = proteins[0]
            sides = (veggies[:2] if veggies else []) + (carbs[:1] if carbs else [])
            recipes.append({
                "title": f"Savory {main} Delight",
                "ingredients": ", ".join([main] + sides),
                "instructions": f"Season the {main.lower()} with salt and pepper. Cook until golden and done. Serve hot with {' and '.join([s.lower() for s in sides]) if sides else 'your favorite sides'}."
            })
        
        # Recipe 2: Fresh bowl/salad
        if veggies:
            base = veggies[0]
            additions = (proteins[:1] if proteins else []) + (dairy[:1] if dairy else []) + (veggies[1:2] if len(veggies) > 1 else [])
            recipes.append({
                "title": f"Fresh {base} Power Bowl",
                "ingredients": ", ".join([base] + additions),
                "instructions": f"Chop {base.lower()} into bite-sized pieces. Combine with {', '.join([a.lower() for a in additions]) if additions else 'toppings'}. Drizzle with olive oil and lemon juice, season to taste."
            })
        
        # Recipe 3: Quick comfort food
        if carbs:
            base = carbs[0]
            toppings = (proteins[:1] if proteins else []) + (veggies[:1] if veggies else []) + (dairy[:1] if dairy else [])
            recipes.append({
                "title": f"Comfort {base}",
                "ingredients": ", ".join([base] + toppings),
                "instructions": f"Prepare {base.lower()} according to package directions. Top generously with {', '.join([t.lower() for t in toppings]) if toppings else 'butter and seasoning'}. Mix well and serve warm!"
            })
        
        # Generic fallback if no categories matched
        if not recipes:
            recipes.append({
                "title": "Creative Kitchen Mix",
                "ingredients": ingredients_text,
                "instructions": "Combine your available ingredients creatively. Season with salt, pepper, herbs, and spices. Cook using your preferred method until everything is tender and delicious!"
            })
        
        # Save fallback recipes to database
        conn = get_conn()
        cur = conn.cursor()
        saved_count = 0
        
        for recipe in recipes[:3]:
            rid = str(uuid.uuid4())
            try:
                cur.execute(
                    'INSERT INTO RecipeSuggestion (id, title, ingredients, instructions, created_at) VALUES (%s,%s,%s,%s,NOW())',
                    (rid, recipe['title'][:255], recipe['ingredients'][:500], recipe['instructions'][:1000])
                )
                saved_count += 1
            except:
                try:
                    cur.execute('INSERT INTO recipes (id, title, created_at) VALUES (%s,%s,NOW())',
                                (rid, recipe['title'][:255]))
                    saved_count += 1
                except:
                    pass
        
        conn.commit()
        conn.close()
        
        app.logger.info('Saved %d fallback recipes to database', saved_count)
        return jsonify({'success': True, 'recipes': recipes[:3]})
            
    except Exception as e:
        app.logger.exception('Failed to generate recipe')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/recipes', methods=['POST'])
def api_save_recipe():
    data = request.get_json(force=True)
    title = data.get('title')
    if not title:
        return jsonify({'success': False, 'message': 'Missing title'}), 400
    rid = str(uuid.uuid4())
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO recipes (id, title, created_at) VALUES (%s,%s,%s)',
                    (rid, title, datetime.datetime.utcnow()))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': rid})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/voice/query', methods=['POST'])
def api_voice_query():
    """Process voice query about inventory using AI"""
    try:
        data = request.get_json() or {}
        query_text = data.get('query', '').strip()
        language = data.get('language', 'en').strip()  # Get selected language
        
        if not query_text:
            return jsonify({'success': False, 'message': 'No query provided'}), 400
        
        app.logger.info('Voice query received: %s (language: %s)', query_text, language)
        
        # Language mapping
        language_names = {
            'en': 'English',
            'hi': 'Hindi (हिन्दी)',
            'te': 'Telugu (తెలుగు)',
            'ta': 'Tamil (தமிழ்)',
            'kn': 'Kannada (ಕನ್ನಡ)',
            'ml': 'Malayalam (മലയാളം)',
            'mr': 'Marathi (मराठी)',
            'bn': 'Bengali (বাংলা)',
            'gu': 'Gujarati (ગુજરાતી)',
            'pa': 'Punjabi (ਪੰਜਾਬੀ)'
        }
        
        # Fetch current inventory
        conn = get_conn()
        cur = conn.cursor()
        if TABLE_NAME == 'item':
            cur.execute('SELECT label, quantity, expiry_date, location, status FROM item ORDER BY expiry_date ASC')
        else:
            cur.execute('SELECT label, quantity, expiry_date, location FROM items ORDER BY expiry_date ASC')
        items = cur.fetchall()
        conn.close()
        
        # Build inventory summary
        inventory_text = "\n".join([
            f"- {item['label']} ({item.get('quantity', 'N/A')}) in {item.get('location', 'unknown location')}, expires: {item.get('expiry_date', 'unknown')}"
            for item in items
        ])
        
        # FIRST: Check if user wants to ADD, REMOVE, or UPDATE an item via voice
        if GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                
                # Check if this is an "add", "remove", or "update" command
                detection_prompt = f"""Analyze this user command: "{query_text}"

Is the user trying to ADD, REMOVE, or UPDATE an item in the fridge/freezer?

**ADD** - Adding a completely new item:
Return JSON: {{"action": "add", "label": "item name", "quantity": "amount", "location": "location name"}}

**REMOVE** - Removing entire item:
Return JSON: {{"action": "remove", "label": "item name"}}

**UPDATE** - Modifying existing item (quantity, expiry, location):
Return JSON: {{"action": "update", "label": "item name", "field": "quantity|expiry_date|location", "value": "new value"}}

If NONE of these (just a question/query):
Return JSON: {{"action": "none"}}

Examples:
- "add fish to the freezer one quantity" => {{"action": "add", "label": "fish", "quantity": "1 unit", "location": "Freezer"}}
- "remove fish from inventory" => {{"action": "remove", "label": "fish"}}
- "reduce apple quantity by 1" => {{"action": "update", "label": "apple", "field": "quantity", "value": "reduce:1"}}
- "remove one quantity from apple" => {{"action": "update", "label": "apple", "field": "quantity", "value": "reduce:1"}}
- "set expiry date for milk to 2025-11-15" => {{"action": "update", "label": "milk", "field": "expiry_date", "value": "2025-11-15"}}
- "change milk expiry to 15th November" => {{"action": "update", "label": "milk", "field": "expiry_date", "value": "2025-11-15"}}
- "move chicken to freezer" => {{"action": "update", "label": "chicken", "field": "location", "value": "Freezer"}}
- "what's in my fridge?" => {{"action": "none"}}

IMPORTANT: For quantity reduction, use "reduce:X" format. For setting exact quantity, use just the number."""

                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": detection_prompt
                        }]
                    }]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    # Parse JSON response
                    try:
                        # Clean markdown if present
                        if '```json' in ai_response:
                            ai_response = ai_response.split('```json')[1].split('```')[0]
                        elif '```' in ai_response:
                            ai_response = ai_response.split('```')[1].split('```')[0]
                        
                        ai_response = ai_response.strip()
                        detection_result = json.loads(ai_response)
                        
                        action = detection_result.get('action', 'none')
                        
                        # HANDLE ADD COMMAND
                        if action == 'add':
                            label = detection_result.get('label', '').strip()
                            quantity = detection_result.get('quantity', '1 unit').strip()
                            location = detection_result.get('location', 'Fridge').strip()
                            
                            if label:
                                app.logger.info(f'Voice ADD detected: {label} ({quantity}) to {location}')
                                
                                # Add item to database
                                conn = get_conn()
                                cur = conn.cursor()
                                
                                if TABLE_NAME == 'item':
                                    cur.execute(
                                        'INSERT INTO item (label, quantity, location, added_date, expiry_date, status, source) VALUES (%s,%s,%s,NOW(),%s,%s,%s)',
                                        (label, quantity, location, None, 'Fresh', 'voice')
                                    )
                                    conn.commit()
                                    item_id = cur.lastrowid
                                else:
                                    item_id = str(uuid.uuid4())
                                    cur.execute(
                                        'INSERT INTO items (id, label, quantity, expiry_date, location) VALUES (%s,%s,%s,%s,%s)',
                                        (item_id, label, quantity, None, location)
                                    )
                                    conn.commit()
                                
                                conn.close()
                                
                                app.logger.info(f'Item added via voice: ID {item_id}')
                                
                                # Create English response first
                                response_text = f"✓ Added {label} ({quantity}) to {location}"
                                
                                # Translate to selected language if not English
                                if language != 'en':
                                    try:
                                        lang_name = language_names.get(language, language)
                                        translate_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                                        translate_prompt = f"Translate this message to {lang_name}: '{response_text}'. Return ONLY the translation, nothing else."
                                        
                                        translate_response = requests.post(
                                            translate_url, 
                                            headers={'Content-Type': 'application/json'}, 
                                            json={{"contents": [{{"parts": [{{"text": translate_prompt}}]}}]}},
                                            timeout=10
                                        )
                                        
                                        if translate_response.status_code == 200:
                                            translate_result = translate_response.json()
                                            translated = translate_result['candidates'][0]['content']['parts'][0]['text'].strip()
                                            translated = translated.strip('"').strip("'").strip()
                                            response_text = translated
                                            app.logger.info(f'Translated response: {response_text}')
                                    except Exception as e:
                                        app.logger.warning(f'Translation failed: {e}')
                                
                                # Return success response
                                return jsonify({
                                    'success': True,
                                    'action': 'item_added',
                                    'query': query_text,
                                    'response': response_text,
                                    'item_id': item_id,
                                    'item_data': {
                                        'label': label,
                                        'quantity': quantity,
                                        'location': location
                                    },
                                    'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                                })
                        
                        # HANDLE REMOVE COMMAND
                        elif action == 'remove':
                            label = detection_result.get('label', '').strip()
                            
                            if label:
                                app.logger.info(f'Voice REMOVE detected: {label}')
                                
                                # Find and remove item from database
                                conn = get_conn()
                                cur = conn.cursor()
                                
                                # Find item by label (case-insensitive)
                                if TABLE_NAME == 'item':
                                    cur.execute('SELECT id FROM item WHERE LOWER(label) = LOWER(%s) LIMIT 1', (label,))
                                else:
                                    cur.execute('SELECT id FROM items WHERE LOWER(label) = LOWER(%s) LIMIT 1', (label,))
                                
                                item = cur.fetchone()
                                
                                if item:
                                    item_id = item['id']
                                    
                                    # Delete the item
                                    if TABLE_NAME == 'item':
                                        cur.execute('DELETE FROM item WHERE id = %s', (item_id,))
                                    else:
                                        cur.execute('DELETE FROM items WHERE id = %s', (item_id,))
                                    
                                    conn.commit()
                                    conn.close()
                                    
                                    app.logger.info(f'Item removed via voice: {label} (ID {item_id})')
                                    
                                    # Create English response first
                                    response_text = f"✓ Removed {label} from inventory"
                                    
                                    # Translate to selected language if not English
                                    if language != 'en':
                                        try:
                                            lang_name = language_names.get(language, language)
                                            translate_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                                            translate_prompt = f"Translate this message to {lang_name}: '{response_text}'. Return ONLY the translation, nothing else."
                                            
                                            translate_response = requests.post(
                                                translate_url, 
                                                headers={'Content-Type': 'application/json'}, 
                                                json={{"contents": [{{"parts": [{{"text": translate_prompt}}]}}]}},
                                                timeout=10
                                            )
                                            
                                            if translate_response.status_code == 200:
                                                translate_result = translate_response.json()
                                                translated = translate_result['candidates'][0]['content']['parts'][0]['text'].strip()
                                                translated = translated.strip('"').strip("'").strip()
                                                response_text = translated
                                                app.logger.info(f'Translated response: {response_text}')
                                        except Exception as e:
                                            app.logger.warning(f'Translation failed: {e}')
                                    
                                    # Return success response
                                    return jsonify({
                                        'success': True,
                                        'action': 'item_removed',
                                        'query': query_text,
                                        'response': response_text,
                                        'item_id': item_id,
                                        'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                                    })
                                else:
                                    # Item not found
                                    conn.close()
                                    
                                    # Create English error message
                                    response_text = f"❌ {label} not found in inventory"
                                    
                                    # Translate to selected language if not English
                                    if language != 'en':
                                        try:
                                            lang_name = language_names.get(language, language)
                                            translate_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                                            translate_prompt = f"Translate this message to {lang_name}: '{response_text}'. Return ONLY the translation, nothing else."
                                            
                                            translate_response = requests.post(
                                                translate_url, 
                                                headers={'Content-Type': 'application/json'}, 
                                                json={{"contents": [{{"parts": [{{"text": translate_prompt}}]}}]}},
                                                timeout=10
                                            )
                                            
                                            if translate_response.status_code == 200:
                                                translate_result = translate_response.json()
                                                translated = translate_result['candidates'][0]['content']['parts'][0]['text'].strip()
                                                translated = translated.strip('"').strip("'").strip()
                                                response_text = translated
                                        except Exception as e:
                                            app.logger.warning(f'Translation failed: {e}')
                                    
                                    return jsonify({
                                        'success': False,
                                        'action': 'item_not_found',
                                        'query': query_text,
                                        'response': response_text,
                                        'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                                    })
                        
                        # HANDLE UPDATE COMMAND
                        elif action == 'update':
                            label = detection_result.get('label', '').strip()
                            field = detection_result.get('field', '').strip()
                            value = detection_result.get('value', '').strip()
                            
                            if label and field and value:
                                app.logger.info(f'Voice UPDATE detected: {label} - {field} = {value}')
                                
                                # Find item in database
                                conn = get_conn()
                                cur = conn.cursor()
                                
                                if TABLE_NAME == 'item':
                                    cur.execute('SELECT id, label, quantity, expiry_date, location FROM item WHERE LOWER(label) = LOWER(%s) LIMIT 1', (label,))
                                else:
                                    cur.execute('SELECT id, label, quantity, expiry_date, location FROM items WHERE LOWER(label) = LOWER(%s) LIMIT 1', (label,))
                                
                                item = cur.fetchone()
                                
                                if item:
                                    item_id = item['id']
                                    
                                    # Process the update based on field
                                    if field == 'quantity':
                                        # Handle quantity reduction (e.g., "reduce:1")
                                        if value.startswith('reduce:'):
                                            try:
                                                reduce_amount = int(value.split(':')[1])
                                                current_qty = item.get('quantity', '1 unit')
                                                
                                                # Extract current number from quantity string
                                                import re
                                                current_match = re.search(r'(\d+)', current_qty)
                                                if current_match:
                                                    current_num = int(current_match.group(1))
                                                    new_num = max(0, current_num - reduce_amount)
                                                    
                                                    # Keep the unit part
                                                    unit_part = re.sub(r'\d+', '', current_qty).strip()
                                                    new_quantity = f"{new_num} {unit_part}".strip() if unit_part else str(new_num)
                                                else:
                                                    new_quantity = f"{max(0, 1 - reduce_amount)} unit"
                                                
                                                value = new_quantity
                                            except:
                                                value = "0 unit"
                                        
                                        # Update quantity
                                        if TABLE_NAME == 'item':
                                            cur.execute('UPDATE item SET quantity = %s WHERE id = %s', (value, item_id))
                                        else:
                                            cur.execute('UPDATE items SET quantity = %s WHERE id = %s', (value, item_id))
                                        
                                        response_msg = f"✓ Updated {label} quantity to {value}"
                                    
                                    elif field == 'expiry_date':
                                        # Update expiry date
                                        if TABLE_NAME == 'item':
                                            cur.execute('UPDATE item SET expiry_date = %s WHERE id = %s', (value, item_id))
                                        else:
                                            cur.execute('UPDATE items SET expiry_date = %s WHERE id = %s', (value, item_id))
                                        
                                        response_msg = f"✓ Set {label} expiry date to {value}"
                                    
                                    elif field == 'location':
                                        # Update location
                                        if TABLE_NAME == 'item':
                                            cur.execute('UPDATE item SET location = %s WHERE id = %s', (value, item_id))
                                        else:
                                            cur.execute('UPDATE items SET location = %s WHERE id = %s', (value, item_id))
                                        
                                        response_msg = f"✓ Moved {label} to {value}"
                                    
                                    else:
                                        conn.close()
                                        return jsonify({
                                            'success': False,
                                            'action': 'invalid_field',
                                            'query': query_text,
                                            'response': f"❌ Cannot update field: {field}",
                                            'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                                        })
                                    
                                    conn.commit()
                                    conn.close()
                                    
                                    app.logger.info(f'Item updated via voice: {label} (ID {item_id})')
                                    
                                    # Translate response to selected language
                                    if language != 'en':
                                        try:
                                            lang_name = language_names.get(language, language)
                                            translate_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                                            translate_prompt = f"Translate this message to {lang_name}: '{response_msg}'. Return ONLY the translation, nothing else."
                                            
                                            translate_response = requests.post(
                                                translate_url, 
                                                headers={'Content-Type': 'application/json'}, 
                                                json={{"contents": [{{"parts": [{{"text": translate_prompt}}]}}]}},
                                                timeout=10
                                            )
                                            
                                            if translate_response.status_code == 200:
                                                translate_result = translate_response.json()
                                                translated = translate_result['candidates'][0]['content']['parts'][0]['text'].strip()
                                                translated = translated.strip('"').strip("'").strip()
                                                response_msg = translated
                                                app.logger.info(f'Translated response: {response_msg}')
                                        except Exception as e:
                                            app.logger.warning(f'Translation failed: {e}')
                                    
                                    # Return success response
                                    return jsonify({
                                        'success': True,
                                        'action': 'item_updated',
                                        'query': query_text,
                                        'response': response_msg,
                                        'item_id': item_id,
                                        'update_field': field,
                                        'update_value': value,
                                        'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                                    })
                                else:
                                    # Item not found for UPDATE
                                    conn.close()
                                    
                                    # Create English error message
                                    response_text = f"❌ {label} not found in inventory"
                                    
                                    # Translate to selected language if not English
                                    if language != 'en':
                                        try:
                                            lang_name = language_names.get(language, language)
                                            translate_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                                            translate_prompt = f"Translate this message to {lang_name}: '{response_text}'. Return ONLY the translation, nothing else."
                                            
                                            translate_response = requests.post(
                                                translate_url, 
                                                headers={'Content-Type': 'application/json'}, 
                                                json={{"contents": [{{"parts": [{{"text": translate_prompt}}]}}]}},
                                                timeout=10
                                            )
                                            
                                            if translate_response.status_code == 200:
                                                translate_result = translate_response.json()
                                                translated = translate_result['candidates'][0]['content']['parts'][0]['text'].strip()
                                                translated = translated.strip('"').strip("'").strip()
                                                response_text = translated
                                        except Exception as e:
                                            app.logger.warning(f'Translation failed: {e}')
                                    
                                    return jsonify({
                                        'success': False,
                                        'action': 'item_not_found',
                                        'query': query_text,
                                        'response': response_text,
                                        'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                                    })
                    except Exception as parse_error:
                        app.logger.warning(f'Could not parse command detection: {parse_error}')
            except Exception as detection_error:
                app.logger.warning(f'Command detection failed: {detection_error}')
        
        # SECOND: Process as regular query if not an add/remove/update command
        if GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                
                # Build prompt with language instruction
                lang_instruction = ""
                if language != 'en':
                    lang_name = language_names.get(language, language)
                    lang_instruction = f"\n\nCRITICAL INSTRUCTION: The user may ask in English or any language, but you MUST respond ONLY in {lang_name}. Translate your ENTIRE response to {lang_name}. Always give response the in selected {lang_name} ."
                
                prompt = f"""You are a smart fridge voice assistant. Answer ONLY what the user explicitly asks - nothing more, nothing less.

Current inventory:
{inventory_text}

User question: {query_text}

STRICT RULES:
1. Answer ONLY the specific question asked - be precise and direct
2. If they ask about quantity (e.g., "how many mutton"), check the inventory and respond with the EXACT quantity from the data
3. If they ask what is present in the fridge, list ONLY the items along with Quantity and Location
4. If they ask for a recipe, give ONLY recipe suggestions
5. If they ask what's expiring, mention ONLY expiring items(elaborate with some suggestions)
6. If they ask what you have, list ONLY the items
7. Do NOT add extra information, dates, or recommendations unless specifically asked
8. Keep response to 5-8 sentences maximum
9. Be direct and to the point{lang_instruction}
10. Always tell where are the items located in the fridge if explicitly asked
11. Suggest good traditional South Indian dishes with the items present in the fridge if the user asks
12. Answer any questions about the inventory based on the inventory data only
13. If asked about a specific item (like "how many mutton"), search the inventory list above and respond with the exact quantity
14. If an item is NOT in the inventory, say "No [item] found in the fridge" or similar
15. DO NOT give generic responses like "Would you like to know what's expiring" - answer the specific question asked
16. User can ask about specific items, quantities, locations - answer accurately from the inventory data
17. If the question is unrelated to fridge inventory, respond naturally as a helpful assistant
18. LANGUAGE HANDLING: If language is {language} (not English), respond ENTIRELY in {language} script. When user mixes English words in their {language} query (e.g., "Add tomatoes to fridge" in Telugu), transliterate those English words phonetically into {language} script in your response. Example: "tomatoes" becomes "టొమాటోలు", "fridge" becomes "ఫ్రిజ్". Never use English words in your {language} response."""

                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    app.logger.info('AI response generated: %s', response_text[:100])
                    
                    # Save to voice query log
                    try:
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute(
                            'INSERT INTO VoiceQuery (query_text, response_text, created_at) VALUES (%s,%s,NOW())',
                            (query_text, response_text)
                        )
                        conn.commit()
                        conn.close()
                    except:
                        pass  # Don't fail if logging doesn't work
                    
                    return jsonify({
                        'success': True,
                        'query': query_text,
                        'response': response_text,
                        'timestamp': datetime.datetime.now().strftime('%I:%M %p')
                    })
                else:
                    raise Exception(f"Gemini API error: {response.status_code}")
                    
            except Exception as ai_error:
                app.logger.warning('AI query failed: %s', str(ai_error))
        
        # Fallback: rule-based responses
        query_lower = query_text.lower()
        
        if 'expir' in query_lower or 'soon' in query_lower:
            # Find items expiring soon
            today = datetime.datetime.now().date()
            expiring = []
            for item in items:
                if item.get('expiry_date'):
                    try:
                        exp_date = datetime.datetime.strptime(str(item['expiry_date']), '%Y-%m-%d').date()
                        days_left = (exp_date - today).days
                        if 0 <= days_left <= 3:
                            expiring.append(f"{item['label']} (expires in {days_left} days)")
                    except:
                        pass
            
            if expiring:
                response_text = f"You have {len(expiring)} items expiring soon: {', '.join(expiring)}. I recommend using them in your next meal!"
            else:
                response_text = "Good news! No items are expiring in the next 3 days."
        
        elif 'what' in query_lower and ('have' in query_lower or 'inventory' in query_lower):
            item_names = [item['label'] for item in items[:5]]
            response_text = f"You currently have {len(items)} items: {', '.join(item_names)}{', and more' if len(items) > 5 else ''}."
        
        elif 'recipe' in query_lower or 'cook' in query_lower or 'make' in query_lower:
            response_text = "I can suggest recipes! Click the 'Generate Custom Recipe' button to get AI-powered recipe suggestions based on your current inventory."
        
        else:
            response_text = f"You have {len(items)} items in your fridge. Would you like to know what's expiring soon, or get recipe suggestions?"
        
        return jsonify({
            'success': True,
            'query': query_text,
            'response': response_text,
            'timestamp': datetime.datetime.now().strftime('%I:%M %p')
        })
        
    except Exception as e:
        app.logger.exception('Voice query failed')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/voice/tts', methods=['POST'])
def api_text_to_speech():
    """Convert text to speech using gTTS (Google Text-to-Speech)"""
    try:
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        language = data.get('language', 'en').strip()
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400
        
        app.logger.info('TTS request: %s chars in %s', len(text), language)
        
        # Language code mapping for gTTS
        gtts_lang_map = {
            'en': 'en',
            'hi': 'hi',
            'te': 'te',
            'ta': 'ta',
            'kn': 'kn',
            'ml': 'ml',
            'mr': 'mr',
            'bn': 'bn',
            'gu': 'gu',
            'pa': 'pa'
        }
        
        gtts_lang = gtts_lang_map.get(language, 'hi')
        
        # Generate speech using gTTS
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        
        # Save to memory buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        app.logger.info('TTS generated successfully for %s', language)
        
        # Return audio file
        return send_file(
            audio_buffer,
            mimetype='audio/mp3',
            as_attachment=False,
            download_name=f'speech_{language}.mp3'
        )
        
    except Exception as e:
        app.logger.exception('TTS generation failed')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/start', methods=['POST'])
def api_start_camera():
    """Start camera detection script"""
    global camera_process
    
    try:
        # Check if already running
        if camera_process and camera_process.poll() is None:
            return jsonify({
                'success': True,
                'message': 'Camera already running',
                'status': 'running'
            })
        
        # Get Python executable path from virtual environment
        python_exe = sys.executable
        script_path = BASE_DIR / 'camera_stream_server.py'
        
        app.logger.info(f'Starting camera stream server: {python_exe} {script_path}')
        
        # Start camera detection as subprocess
        import logging
        log_file = BASE_DIR / 'camera_stream.log'
        
        with open(log_file, 'w') as f:
            camera_process = subprocess.Popen(
                [python_exe, str(script_path)],
                stdout=f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
        
        app.logger.info(f'Camera process started with PID: {camera_process.pid}')
        app.logger.info(f'Camera logs: {log_file}')
        
        # Wait a moment and check if process is still running
        time.sleep(1)
        if camera_process.poll() is not None:
            # Process crashed immediately
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    error_log = f.read()
            except Exception as e:
                error_log = f"Could not read log: {str(e)}"
            app.logger.error(f'Camera process crashed: {error_log}')
            return jsonify({
                'success': False,
                'message': 'Camera failed to start. Check camera_stream.log for details.',
                'error': error_log
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Camera detection started',
            'status': 'running',
            'pid': camera_process.pid
        })
        
    except Exception as e:
        app.logger.exception('Failed to start camera')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/stop', methods=['POST'])
def api_stop_camera():
    """Stop camera detection script"""
    global camera_process
    
    try:
        if not camera_process or camera_process.poll() is not None:
            camera_process = None
            return jsonify({
                'success': True,
                'message': 'Camera not running',
                'status': 'stopped'
            })
        
        app.logger.info(f'Stopping camera process PID: {camera_process.pid}')
        
        # Terminate the process
        if sys.platform == 'win32':
            # Windows: use CTRL_BREAK_EVENT
            camera_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            # Unix: use SIGTERM
            camera_process.terminate()
        
        # Wait for process to end (with timeout)
        try:
            camera_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't stop gracefully
            camera_process.kill()
            camera_process.wait()
        
        camera_process = None
        app.logger.info('Camera process stopped')
        
        return jsonify({
            'success': True,
            'message': 'Camera detection stopped',
            'status': 'stopped'
        })
        
    except Exception as e:
        app.logger.exception('Failed to stop camera')
        camera_process = None
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/status', methods=['GET'])
def api_camera_status():
    """Check if camera is running"""
    global camera_process
    
    is_running = camera_process and camera_process.poll() is None
    
    return jsonify({
        'success': True,
        'status': 'running' if is_running else 'stopped',
        'pid': camera_process.pid if is_running else None
    })


if __name__ == '__main__':
    # attempt to create tables (best-effort)
    init_db_if_needed()
    print(f"Starting backend on http://0.0.0.0:{APP_PORT}")
    
    # Cleanup camera process on exit
    def cleanup():
        global camera_process
        if camera_process and camera_process.poll() is None:
            print("\nStopping camera process...")
            camera_process.terminate()
            camera_process.wait()
    
    import atexit
    atexit.register(cleanup)
    
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)

