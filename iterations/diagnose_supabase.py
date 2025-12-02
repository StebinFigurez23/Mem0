# Save as test_connection.py
import socket
import os
from dotenv import load_dotenv

load_dotenv()

def test_supabase_connection():
    database_url = os.getenv('DATABASE_URL', '')
    print(f"DATABASE_URL loaded: {database_url[:50]}..." if database_url else "DATABASE_URL not found!")
    
    host = 'db.amuuoaojbxicmeslqeem.supabase.co'
    port = 5432
    
    print(f"\n=== Testing Supabase Connection ===")
    print(f"Host: {host}")
    print(f"Port: {port}\n")
    
    # Test 1: DNS Resolution
    try:
        ip = socket.gethostbyname(host)
        print(f"✓ DNS Resolution: SUCCESS → {ip}")
    except socket.gaierror as e:
        print(f"✗ DNS Resolution: FAILED → {e}")
        print("\nPossible causes:")
        print("  - No internet connection")
        print("  - DNS server issues")
        print("  - Firewall blocking DNS queries")
        print("  - VPN/Proxy interference")
        return False
    
    # Test 2: Port Connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ Port {port}: ACCESSIBLE")
            return True
        else:
            print(f"✗ Port {port}: NOT ACCESSIBLE (Error code: {result})")
            print("\nPossible causes:")
            print("  - Firewall blocking port 5432")
            print("  - Company network restrictions")
            print("  - Supabase project paused/deleted")
            return False
    except Exception as e:
        print(f"✗ Port test failed: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection()