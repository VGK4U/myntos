import sys
import json
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar

def test_flow():
    # 1. Login to get token
    login_url = "http://127.0.0.1:8000/api/v1/vgk/auth/login"
    login_data = json.dumps({
        "identifier": "VGK07102207",
        "password": "8875551666"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        login_url,
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            resp_body = json.loads(res.read().decode("utf-8"))
            print("Login response status:", res.status)
            access_token = resp_body.get("access_token")
            if not access_token:
                print("Error: No access_token in login response!")
                sys.exit(1)
            print("Successfully obtained access_token:", access_token[:15] + "...")
    except Exception as e:
        print("Login failed:", e)
        sys.exit(1)
        
    # 2. Setup cookie handler to inspect cookies
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # 3. Request embedded dashboard with token
    dashboard_url = f"http://127.0.0.1:5001/vgk/dashboard?embed=true&token={urllib.parse.quote(access_token)}"
    print(f"Requesting dashboard URL: {dashboard_url[:80]}...")
    
    try:
        # Prevent automatic redirect handling so we can inspect redirect responses if any
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                print(f"Intercepted redirect to: {newurl} (Code: {code})")
                return None
        
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirectHandler)
        
        req_dash = urllib.request.Request(dashboard_url)
        with opener.open(req_dash) as res_dash:
            print("Dashboard response status:", res_dash.status)
            body = res_dash.read().decode("utf-8")
            
            # Check for cookie
            cookies = list(cj)
            print("Cookies returned:")
            for cookie in cookies:
                print(f"  {cookie.name} = {cookie.value[:10]}... (Domain: {cookie.domain}, Path: {cookie.path})")
            
            print("Dashboard Body Preview:")
            print(body[:1000])
                
            # Check for script injection
            if "// 1. Resolve token from URL or localStorage" in body:
                print("✅ Found VGK_TOKEN_PROPAGATION_SCRIPT (via comment) in dashboard HTML!")
            else:
                print("❌ VGK_TOKEN_PROPAGATION_SCRIPT NOT found in dashboard HTML!")
                
            if "vgk_dashboard.html" in body or "MyntReal" in body or "dashboard" in body.lower():
                print("✅ Dashboard page returned successfully!")
            else:
                print("❌ Unexpected response body shape.")
    except Exception as e:
        print("Dashboard request failed:", e)
        
    # 4. Request vendor directory with token
    vd_url = f"http://127.0.0.1:5001/vgk/vendor-directory?token={urllib.parse.quote(access_token)}"
    print(f"Requesting vendor directory URL: {vd_url[:80]}...")
    
    try:
        req_vd = urllib.request.Request(vd_url)
        with opener.open(req_vd) as res_vd:
            print("Vendor Directory response status:", res_vd.status)
            body = res_vd.read().decode("utf-8")
            
            if "// 1. Resolve token from URL or localStorage" in body:
                print("✅ Found VGK_TOKEN_PROPAGATION_SCRIPT (via comment) in vendor directory HTML!")
            else:
                print("❌ VGK_TOKEN_PROPAGATION_SCRIPT NOT found in vendor directory HTML!")
                
            if "vgk_vendor_directory.html" in body or "Vendor Directory" in body:
                print("✅ Vendor Directory page returned successfully!")
            else:
                print("❌ Unexpected response body shape for vendor directory.")
    except Exception as e:
        print("Vendor Directory request failed:", e)
        
    # 5. Request a slug sub-page (e.g. birthdays)
    bd_url = f"http://127.0.0.1:5001/vgk/birthdays?token={urllib.parse.quote(access_token)}"
    print(f"Requesting birthdays URL: {bd_url[:80]}...")
    
    try:
        req_bd = urllib.request.Request(bd_url)
        with opener.open(req_bd) as res_bd:
            print("Birthdays response status:", res_bd.status)
            body = res_bd.read().decode("utf-8")
            
            if "// 1. Resolve token from URL or localStorage" in body:
                print("✅ Found VGK_TOKEN_PROPAGATION_SCRIPT (via comment) in birthdays HTML!")
            else:
                print("❌ VGK_TOKEN_PROPAGATION_SCRIPT NOT found in birthdays HTML!")
    except Exception as e:
        print("Birthdays request failed:", e)

if __name__ == "__main__":
    test_flow()
