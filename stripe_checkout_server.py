#!/usr/bin/env python3
"""Ceremli production server with hardened Stripe checkout handling."""
import json
import os
import urllib.parse
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import server as core
import ceremli_launch_server as launch


def _clean_secret(value: str) -> str:
    value = (value or '').strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    return value


def stripe_checkout(plan, user_id):
    secret = _clean_secret(os.getenv('STRIPE_SECRET_KEY', ''))
    premium = _clean_secret(os.getenv('STRIPE_PREMIUM_PRICE_ID', ''))
    ultimate = _clean_secret(os.getenv('STRIPE_ULTIMATE_PRICE_ID', ''))
    price = {'premium': premium, 'ultimate': ultimate}.get(plan, '')

    if not secret or not price:
        return None

    # Never log the credential itself. This only reports safe shape information.
    prefix = secret.split('_', 2)[:2]
    safe_prefix = '_'.join(prefix) + '_' if len(prefix) >= 2 else 'unknown'
    print(f'[stripe] checkout credential prefix={safe_prefix} length={len(secret)} plan={plan} price_prefix={price[:6]}')

    data = urllib.parse.urlencode({
        'mode': 'payment',
        'success_url': f'{core.BASE_URL}/pricing.html?checkout=success',
        'cancel_url': f'{core.BASE_URL}/pricing.html?checkout=cancelled',
        'line_items[0][price]': price,
        'line_items[0][quantity]': '1',
        'metadata[user_id]': str(user_id),
        'metadata[plan]': plan,
    }).encode()

    req = urllib.request.Request(
        'https://api.stripe.com/v1/checkout/sessions',
        data=data,
        method='POST',
        headers={
            'Authorization': f'Bearer {secret}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Ceremli/1.0',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            payload = json.loads(body)
            stripe_error = payload.get('error') or {}
            message = stripe_error.get('message') or body
            err_type = stripe_error.get('type') or 'stripe_error'
            code = stripe_error.get('code') or ''
            print(f'[stripe] HTTP {e.code} type={err_type} code={code} message={message}')
            raise RuntimeError(f'Stripe {e.code}: {message}')
        except json.JSONDecodeError:
            print(f'[stripe] HTTP {e.code}: {body[:500]}')
            raise RuntimeError(f'Stripe {e.code}: {body[:200]}')


core.stripe_checkout = stripe_checkout

if __name__ == '__main__':
    launch.migrate_launch()
    core.os.chdir(core.ROOT)
    print(f'Ceremli Stripe-hardened server on {core.PORT} | DB={core.DB}')
    ThreadingHTTPServer(('0.0.0.0', core.PORT), launch.CeremliLaunchApp).serve_forever()
