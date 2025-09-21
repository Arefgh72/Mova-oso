import os
import json
import time
import random
from web3 import Web3

# --- توابع کمکی (اصلاح شده و به حالت اول بازگشته) ---
def get_wallet_addresses():
    """آدرس کیف پول دوم (مقصد) را از فایل JSON می‌خواند."""
    try:
        with open('wallet_address.json', 'r') as f:
            data = json.load(f)
            return data.get('address')
    except Exception as e:
        print(f"خطا در خواندن wallet_address.json: {e}")
        return None

def get_all_networks():
    """لیست تمام شبکه‌ها را از فایل networks.json می‌خواند."""
    try:
        with open('networks.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"خطا در خواندن networks.json: {e}")
        return []

# --- منطق اصلی اجرای تراکنش‌ها (بدون تغییر نسبت به نسخه قبل) ---
def run_operations_on_network(network_config):
    private_key_1 = os.getenv('PRIVATE_KEY')
    private_key_2 = os.getenv('PRIVATE_KEY_WALLET_2')
    rpc_url = network_config.get('rpc_url')
    chain_id = int(network_config.get('chain_id'))
    network_name = network_config.get('displayName', 'Unknown Network')

    print("-" * 50 + f"\nشروع عملیات برای شبکه: {network_name} (Chain ID: {chain_id})")

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
    # اینجا با تابع اصلاح شده، آدرس به درستی خوانده می‌شود
    address_2 = get_wallet_addresses()
    
    print(f"کیف پول ۱ (اصلی): {address_1}")
    print(f"کیف پول ۲ (مقصد): {address_2}")
    
    # اگر آدرس دوم خوانده نشود، اسکریپت متوقف می‌شود
    if not address_2:
        print("آدرس کیف پول دوم یافت نشد. عملیات متوقف شد.")
        return

    # --- مرحله ۱: ارسال ۱۰ تراکنش ---
    print("\n>> مرحله ۱: ارسال ۱۰ تراکنش به کیف پول دوم...")
    try:
        nonce = w3.eth.get_transaction_count(address_1)
        print(f"نانس اولیه دریافت شده: {nonce}")
    except Exception as e:
        print(f"خطا در دریافت نانس اولیه: {e}")
        return

    successful_txs = 0
    while successful_txs < 10:
        try:
            print(f"  ({successful_txs + 1}/10) تلاش برای ارسال با نانس: {nonce}")
            tx = {
                'to': address_2, 'value': w3.to_wei(0.001, 'ether'),
                'gas': 21000, 'gasPrice': w3.eth.gas_price,
                'nonce': nonce, 'chainId': chain_id
            }
            signed_tx = w3.eth.account.sign_transaction(tx, private_key_1)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"      تراکنش ارسال شد: {w3.to_hex(tx_hash)}")

            nonce += 1
            successful_txs += 1
            
            if successful_txs < 10:
                delay = random.uniform(5, 20)
                print(f"      ... انتظار برای {delay:.2f} ثانیه ...")
                time.sleep(delay)

        except Exception as e:
            error_message = str(e).lower()
            if any(err in error_message for err in ['nonce too low', 'invalid tx nonce', 'already exist', 'known transaction', 'replacement transaction underpriced']):
                print(f"      خطای نانس شناسایی شد. در حال هماهنگ‌سازی مجدد...")
                time.sleep(10)
                try:
                    nonce = w3.eth.get_transaction_count(address_1)
                    print(f"      نانس جدید دریافت شد: {nonce}")
                except Exception as sync_e:
                    print(f"      خطا در هماهنگ‌سازی مجدد نانس: {sync_e}")
                    return
            else:
                print(f"  خطای غیرمنتظره: {e}")
                print("عملیات روی این شبکه متوقف شد.")
                return

    print(">> مرحله ۱ با موفقیت و ارسال ۱۰ تراکنش انجام شد.")

    # --- مرحله ۲: بازگرداندن موجودی ---
    print("\n>> مرحله ۲: بازگرداندن کل موجودی به کیف پول اصلی...")
    # (این بخش بدون تغییر است)
    if not private_key_2:
        print("هشدار: کلید خصوصی کیف پول دوم تعریف نشده. از این مرحله صرف نظر می‌شود.")
        return
    try:
        wallet_2 = w3.eth.account.from_key(private_key_2)
        if wallet_2.address.lower() != address_2.lower():
            print("خطای امنیتی: کلید خصوصی دوم با آدرس مقصد مطابقت ندارد!")
            return
        balance = w3.eth.get_balance(address_2)
        print(f"موجودی کیف پول دوم: {w3.from_wei(balance, 'ether')} توکن")
        if balance > 0:
            gas_price = w3.eth.gas_price
            tx_fee = 21000 * gas_price
            if balance > tx_fee:
                amount_to_send = balance - tx_fee
                nonce_wallet_2 = w3.eth.get_transaction_count(address_2)
                sweep_tx = {
                    'to': address_1, 'value': amount_to_send, 'gas': 21000,
                    'gasPrice': gas_price, 'nonce': nonce_wallet_2, 'chainId': chain_id
                }
                signed_sweep_tx = w3.eth.account.sign_transaction(sweep_tx, private_key_2)
                sweep_tx_hash = w3.eth.send_raw_transaction(signed_sweep_tx.raw_transaction)
                print(f"تراکنش بازگشتی ارسال شد: {w3.to_hex(sweep_tx_hash)}")
            else:
                print("موجودی برای پوشش هزینه تراکنش کافی نیست.")
        else:
            print("موجودی صفر است.")
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
