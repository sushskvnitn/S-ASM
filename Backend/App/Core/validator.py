# app/core/validator.py
def is_reflected(response, payload):
    return payload in response.text

def validate_response(payload, response):
    if response.status_code == 200 and is_reflected(response, payload):
        return True
    return False
