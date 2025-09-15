import json
import os
import random
import time
from web3 import Web3
from solcx import compile_files, install_solc, set_solc_version

# --- توابع کمکی ---

def compile_contract(file_path, contract_name):
    """
    یک فایل Solidity فلت شده را کامپایل کرده و ABI و Bytecode آن را برمی‌گرداند.
    """
    solc_version = '0.8.20'
    print(f"در حال کامپایل کردن {file_path} با solc نسخه {solc_version}...")
    
    # نصب و تنظیم نسخه دقیق کامپایلر
    install_solc(solc_version)
    set_solc_version(solc_version)
    
    # کامپایل فایل بدون نیاز به remapping چون تمام کدها در یک فایل هستند
    compiled_sol = compile_files(
        [file_path],
        output_values=['abi', 'bin']
    )
    
    contract_id = f"{file_path}:{contract_name}"
    abi = compiled_sol[contract_id]['abi']
    bytecode = compiled_sol[contract_id]['bin']
    print(f"کامپایل '{contract_name}' با موفقیت انجام شد.")
    return abi, bytecode

def generate_random_name():
    """یک نام تصادفی برای قراردادها ایجاد می‌کند."""
    adjectives = ["Cool", "Fast", "Magic", "Shiny", "Brave", "Wise"]
    nouns = ["Dragon", "Tiger", "Eagle", "Star", "River", "Moon"]
    return f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(1, 999)}"

def deploy_contract(w3, account, chain_id, abi, bytecode, contract_name, contract_symbol):
    """یک قرارداد هوشمند را دیپلوی کرده و آدرس آن را برمی‌گرداند."""
    private_key = os.environ.get('PRIVATE_KEY')
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    transaction = contract.constructor(contract_name, contract_symbol).build_transaction({
        'chainId': chain_id,
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"در حال دیپلوی قرارداد '{contract_name}'. هش تراکنش: {tx_hash.hex()}")
    
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt['contractAddress']
    print(f"قرارداد '{contract_name}' با موفقیت در آدرس {contract_address} دیپلوی شد.")
    return contract_address

# --- ۱. خواندن تنظیمات و اتصال ---

print("--- شروع اسکریپت ---")
with open('networks.json', 'r') as f:
    network_info = json.load(f)[0]
    rpc_url = network_info['rpc_url']
    chain_id = int(network_info['chain_id'])

w3 = Web3(Web3.HTTPProvider(rpc_url))
if not w3.is_connected():
    raise ConnectionError(f"خطا: اتصال به RPC URL '{rpc_url}' برقرار نشد.")
print(f"با موفقیت به شبکه با Chain ID: {chain_id} متصل شد.")

private_key = os.environ.get('PRIVATE_KEY')
if not private_key:
    raise ValueError("کلید خصوصی (PRIVATE_KEY) در GitHub Secrets تنظیم نشده است!")

account = w3.eth.account.from_key(private_key)
print(f"تراکنش‌ها از آدرس {account.address} ارسال خواهد شد.")
print(f"موجودی اولیه: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} اتر")

# --- شروع چرخه اصلی تراکنش‌ها ---
try:
    # --- ۲. آماده‌سازی قرارداد InteractFeeProxy ---
    with open('contract_addresses.json', 'r') as f:
        proxy_address = json.load(f)['InteractFeeProxy']
    with open('abis/InteractFeeProxy-ABI.json', 'r') as f:
        proxy_abi = json.load(f)
    
    proxy_contract = w3.eth.contract(address=proxy_address, abi=proxy_abi)

    # --- ۳. تراکنش اول (interactWithFee) ---
    print("\n--- مرحله ۱: اجرای تراکنش 'interactWithFee' ---")
    amount_to_send_wei = w3.to_wei(0.001, 'ether')
    tx1 = proxy_contract.functions.interactWithFee().build_transaction({
        'chainId': chain_id,
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'value': amount_to_send_wei,
        'gas': 200000, 
        'gasPrice': w3.eth.gas_price
    })
    signed_tx1 = w3.eth.account.sign_transaction(tx1, private_key=private_key)
    tx1_hash = w3.eth.send_raw_transaction(signed_tx1.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx1_hash)
    print(f"تراکنش 'interactWithFee' با موفقیت انجام شد. هش: {tx1_hash.hex()}")

    # --- ۴. تاخیر اول و تراکنش دوم (دیپلوی) ---
    delay1 = random.uniform(5, 20)
    print(f"\nتاخیر تصادفی برای {delay1:.2f} ثانیه...")
    time.sleep(delay1)

    random_number = random.randint(1, 100)
    random_name = generate_random_name()
    print(f"--- مرحله ۲: عدد تصادفی: {random_number}. نام تصادفی: '{random_name}' ---")

    if random_number % 2 == 0:
        print("تصمیم: دیپلوی قرارداد توکن (ERC20)...")
        token_abi, token_bytecode = compile_contract('contracts/MyToken.sol', 'MyToken')
        deploy_contract(w3, account, chain_id, token_abi, token_bytecode, random_name, random_name[:4].upper())
    else:
        print("تصمیم: دیپلوی قرارداد NFT (ERC721)...")
        nft_abi, nft_bytecode = compile_contract('contracts/MyNFT.sol', 'MyNFT')
        deploy_contract(w3, account, chain_id, nft_abi, nft_bytecode, random_name, random_name[:4].upper())
        
    # --- ۵. تاخیر دوم و تراکنش سوم (Withdraw) ---
    delay2 = random.uniform(5, 20)
    print(f"\nتاخیر تصادفی برای {delay2:.2f} ثانیه...")
    time.sleep(delay2)
    
    print("\n--- مرحله ۳: اجرای تراکنش 'withdrawEther' ---")
    tx3 = proxy_contract.functions.withdrawEther().build_transaction({
        'chainId': chain_id,
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 100000,
        'gasPrice': w3.eth.gas_price
    })
    signed_tx3 = w3.eth.account.sign_transaction(tx3, private_key=private_key)
    tx3_hash = w3.eth.send_raw_transaction(signed_tx3.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx3_hash)
    print(f"تراکنش 'withdrawEther' با موفقیت انجام شد. هش: {tx3_hash.hex()}")

except Exception as e:
    print(f"\n!!! یک خطای کلی رخ داد: {e}")
    exit(1)

print("\n\nچرخه کامل اسکریپت با موفقیت اجرا شد.")
print(f"موجودی نهایی: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} اتر")
