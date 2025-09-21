import os
import json
import time
import random
from web3 import Web3

# --- توابع کمکی (بدون تغییر) ---

def get_wallet_addresses():
    try:
        with open('wallet_address.json', 'r') as f:
            data = json.load(f)
            return data.get('address')
    except Exception as e:
        print(f"خطا در خواندن wallet_address.json: {e}")
        return None

def get_all_networks():
    try:
        with open('networks.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"خطا در خواندن networks.json: {e}")
        return []

def wait_for_receipt(w3, tx_hash, timeout=180):
    from web3.exceptions import TransactionNotFound
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        return receipt
    except Exception as e:
        print(f"خطایی در گرفتن رسید تراکنش رخ داد: {e}")
        return None

# --- منطق اصلی اجرای تراکنش‌ها (نسخه مقاوم) ---

def run_operations_on_network(network_config):
    private_key_1 = os.getenv('PRIVATE_KEY')
    private_key_2 = os.getenv('PRIVATE_KEY_WALLET_2')
    rpc_url = network_config.get('rpc_url')
    chain_id = int(network_config.get('chain_id'))
    network_name = network_config.get('displayName', 'Unknown')

    print("-" * 50)
    print(f"شروع عملیات برای شبکه: {network_name} (Chain ID: {chain_id})")

    if not private_key_1 or not rpc_url:
        print("خطا: کلید خصوصی اصلی یا RPC URL یافت نشد.")
        return

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            print("خطا در اتصال به RPC.")
            return
    except Exception as e:
        print(f"خطای اتصال: {e}")
        return
        
    wallet_1 = w3.eth.account.from_key(private_key_1)
    address_1 = wallet_1.address
    address_2 = get_wallet_addresses()
    if not address_2: return

    print(f"کیف پول ۱ (اصلی): {address_1}")
    print(f"کیف پول ۲ (مقصد): {address_2}")

    print("\n>> مرحله ۱: ارسال ۱۰ تراکنش به کیف پول دوم...")
    
    successful_txs = 0
    # استفاده از حلقه while برای ارسال دقیقاً ۱۰ تراکنش موفق
    while successful_txs < 10:
        try:
            # همیشه آخرین nonce را از شبکه دریافت می‌کنیم تا مقاوم باشیم
            current_nonce = w3.eth.get_transaction_count(address_1)
            print(f"  ({successful_txs + 1}/10) تلاش برای ارسال با نانس: {current_nonce}")

            tx = {
                'to': address_2,
                'value': w3.to_wei(0.001, 'ether'),
                'gas': 21000,
                'gasPrice': w3.eth.gas_price,
                'nonce': current_nonce,
                'chainId': chain_id
            }
            
            signed_tx = w3.eth.account.sign_transaction(tx, private_key_1)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"      تراکنش ارسال شد: {w3.to_hex(tx_hash)}")
            
            # پس از ارسال موفق، شمارنده را افزایش می‌دهیم
            successful_txs += 1
            
            # اگر آخرین تراکنش نیست، تاخیر ایجاد کن
            if successful_txs < 10:
                delay = random.uniform(5, 20)
                print(f"      ... انتظار برای {delay:.2f} ثانیه ...")
                time.sleep(delay)

        except Exception as e:
            error_message = str(e).lower()
            # اگر خطا مربوط به nonce بود، فقط صبر کرده و دوباره تلاش می‌کنیم
            if 'nonce too low' in error_message or 'invalid tx nonce' in error_message or 'replacement transaction underpriced' in error_message:
                print(f"      خطای نانس شناسایی شد. در حال تلاش مجدد...")
                time.sleep(10) # کمی صبر می‌کنیم تا شبکه به‌روز شود
            else:
                # برای خطاهای دیگر، عملیات را متوقف می‌کنیم
                print(f"  خطای پیش‌بینی‌نشده: {e}")
                print("عملیات روی این شبکه متوقف شد.")
                return

    print(">> مرحله ۱ با موفقیت و ارسال ۱۰ تراکنش انجام شد.")

    # --- مرحله ۲: بازگرداندن موجودی (بدون تغییر) ---
    print("\n>> مرحله ۲: بازگرداندن کل موجودی به کیف پول اصلی...")
    if not private_key_2:
        print("هشدار: کلید خصوصی کیف پول دوم (PRIVATE_KEY_WALLET_2) تعریف نشده. از این مرحله صرف نظر می‌شود.")
        return

    try:
        wallet_2 = w3.eth.account.from_key(private_key_2)
        if wallet_2.address.lower() != address_2.lower():
            print(f"خطای امنیتی: کلید خصوصی دوم با آدرس {address_2} مطابقت ندارد!")
            return

        balance = w3.eth.get_balance(address_2)
        print(f"موجودی کیف پول دوم: {w3.from_wei(balance, 'ether')} توکن")
        
        if balance > 0:
            gas_price = w3.eth.gas_price
            gas_limit = 21000
            tx_fee = gas_limit * gas_price
            
            if balance > tx_fee:
                amount_to_send = balance - tx_fee
                nonce_wallet_2 = w3.eth.get_transaction_count(address_2)
                sweep_tx = {
                    'to': address_1,
                    'value': amount_to_send,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'nonce': nonce_wallet_2,
                    'chainId': chain_id
                }
                
                signed_sweep_tx = w3.eth.account.sign_transaction(sweep_tx, private_key_2)
                sweep_tx_hash = w3.eth.send_raw_transaction(signed_sweep_tx.raw_transaction)
                print(f"تراکنش بازگشتی ارسال شد: {w3.to_hex(sweep_tx_hash)}")
                receipt = wait_for_receipt(w3, sweep_tx_hash)
                if receipt and receipt.status == 1:
                    print(">> مرحله ۲ با موفقیت انجام شد.")
                else:
                    print("خطا: تراکنش بازگشتی ناموفق بود.")
            else:
                print("موجودی برای پوشش هزینه تراکنش کافی نیست.")
        else:
            print("موجودی صفر است. تراکنش بازگشتی انجام نمی‌شود.")

    except Exception as e:
        print(f"خطا در مرحله بازگرداندن موجودی: {e}")

# --- نقطه شروع برنامه ---
if __name__ == "__main__":
    networks_to_process = get_all_networks()
    if not networks_to_process:
        print("هیچ شبکه‌ای برای پردازش در networks.json یافت نشد.")
    else:
        for network in networks_to_process:
            run_operations_on_network(network)
    
    print("\nتمام عملیات به پایان رسید.")
