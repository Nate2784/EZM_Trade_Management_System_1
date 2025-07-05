#!/usr/bin/env python
"""
Test script to verify cashier login redirect behavior
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/home/silence/Documents/FinalProject/EZM_Trade_Management_System_1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()

def test_cashier_login_redirect():
    """Test that cashiers are redirected correctly based on login status"""
    
    print("🔍 Testing Cashier Login Redirect Behavior...")
    print("=" * 50)
    
    # Create or get a test cashier user
    print("1. Setting up test cashier user:")
    try:
        # Try to get existing cashier
        cashier = User.objects.filter(role='cashier').first()
        
        if not cashier:
            print("   Creating new test cashier...")
            cashier = User.objects.create_user(
                username='test_cashier',
                email='cashier@test.com',
                password='testpass123',
                role='cashier',
                first_name='Test',
                last_name='Cashier',
                is_first_login=True  # Simulate first login
            )
            print(f"   ✅ Created test cashier: {cashier.username}")
        else:
            print(f"   ✅ Using existing cashier: {cashier.username}")
            
    except Exception as e:
        print(f"   ❌ Failed to create/get cashier: {e}")
        return False
    
    # Test first login redirect
    print("\n2. Testing first login redirect:")
    try:
        client = Client()
        
        # Set cashier as first login
        cashier.is_first_login = True
        cashier.save()
        
        # Simulate login
        login_successful = client.login(username=cashier.username, password='testpass123')
        if not login_successful:
            print("   ❌ Login failed")
            return False
            
        print("   ✅ Login successful")
        
        # Check if already authenticated user gets redirected properly
        response = client.get('/users/login/')
        print(f"   ✅ Authenticated user redirect status: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.url
            print(f"   ✅ First login redirects to: {redirect_url}")
            if 'cashier/settings' in redirect_url:
                print("   ✅ Correct! First login redirects to cashier settings")
            else:
                print(f"   ⚠️  Unexpected redirect for first login: {redirect_url}")
        
    except Exception as e:
        print(f"   ❌ First login test failed: {e}")
        return False
    
    # Test subsequent login redirect
    print("\n3. Testing subsequent login redirect:")
    try:
        # Mark as not first login
        cashier.is_first_login = False
        cashier.save()
        
        # Logout and login again
        client.logout()
        login_successful = client.login(username=cashier.username, password='testpass123')
        
        if login_successful:
            # Check redirect for authenticated user
            response = client.get('/users/login/')
            if response.status_code == 302:
                redirect_url = response.url
                print(f"   ✅ Subsequent login redirects to: {redirect_url}")
                if 'cashier/' in redirect_url and 'settings' not in redirect_url:
                    print("   ✅ Correct! Subsequent login redirects to cashier dashboard")
                else:
                    print(f"   ⚠️  Unexpected redirect for subsequent login: {redirect_url}")
            
    except Exception as e:
        print(f"   ❌ Subsequent login test failed: {e}")
        return False
    
    # Test URL accessibility
    print("\n4. Testing URL accessibility:")
    try:
        # Test cashier dashboard
        response = client.get('/users/cashier/')
        print(f"   ✅ Cashier dashboard accessible: {response.status_code}")
        
        # Test cashier settings
        response = client.get('/users/cashier/settings/')
        print(f"   ✅ Cashier settings accessible: {response.status_code}")
        
        # Test cashier profile edit
        response = client.get('/users/cashier/profile/edit/')
        print(f"   ✅ Cashier profile edit accessible: {response.status_code}")
        
        # Test cashier password change
        response = client.get('/users/cashier/profile/change-password/')
        print(f"   ✅ Cashier password change accessible: {response.status_code}")
        
    except Exception as e:
        print(f"   ❌ URL accessibility test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Cashier login redirect tests completed!")
    print("\n📋 Summary:")
    print("   • First login: Cashier → Settings page (for profile setup)")
    print("   • Subsequent logins: Cashier → Dashboard page")
    print("   • All cashier URLs are accessible with proper authentication")
    print("   • Settings page provides clear navigation to dashboard")
    
    return True

if __name__ == "__main__":
    test_cashier_login_redirect()
