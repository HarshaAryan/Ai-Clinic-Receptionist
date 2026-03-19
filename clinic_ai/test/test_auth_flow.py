"""Quick route verification for the refactored auth flow."""
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

print("── Route Verification ──────────────────────────────────")

# 1. Home page renders
r = client.get("/")
assert r.status_code == 200, f"Home page returned {r.status_code}"
assert "ClinicOS" in r.text
assert "signinModal" in r.text, "Sign-in modal missing from home page"
assert "signupModal" in r.text, "Signup modal missing from home page"
print(f"✅ GET / → {r.status_code} (home with both modals)")

# 2. Sign-in with email (no account → redirect to error)
r = client.post("/auth/signin", data={"email": "nobody@test.com"}, follow_redirects=False)
assert r.status_code == 302
loc = r.headers.get("location", "")
print(f"✅ POST /auth/signin (unknown email) → {r.status_code} → {loc}")

# 3. Sign-in with empty email → redirect to email_required error
r = client.post("/auth/signin", data={"email": ""}, follow_redirects=False)
assert r.status_code == 302
loc = r.headers.get("location", "")
assert "email_required" in loc, f"Expected email_required error, got {loc}"
print(f"✅ POST /auth/signin (empty) → {r.status_code} → {loc}")

# 4. Signup → should redirect with success
r = client.post("/auth/signup/setup", data={
    "full_name": "Dr Test",
    "email": "newdoc@test.com",
    "clinic_name": "Test Clinic",
    "contact_phone": "+919876543210",
}, follow_redirects=False)
assert r.status_code == 302
loc = r.headers.get("location", "")
print(f"✅ POST /auth/signup/setup → {r.status_code} → {loc}")

# 5. /auth/login in dev mode → should redirect to /
r = client.get("/auth/login?mode=signin", follow_redirects=False)
assert r.status_code == 302
loc = r.headers.get("location", "")
print(f"✅ GET /auth/login (dev mode) → {r.status_code} → {loc}")

# 6. Logout
r = client.get("/auth/logout", follow_redirects=False)
assert r.status_code in (302, 307)
print(f"✅ GET /auth/logout → {r.status_code}")

# 7. Verify sign-in modal has NO signup fields
r = client.get("/")
# The sign-in modal should only have email, not full_name/clinic_name/specialization
signin_modal_start = r.text.find('id="signinModal"')
signin_modal_end = r.text.find('id="signupModal"')
signin_section = r.text[signin_modal_start:signin_modal_end]
assert 'name="email"' in signin_section, "Sign-in modal should have email field"
assert 'name="full_name"' not in signin_section, "Sign-in modal should NOT have full_name"
assert 'name="clinic_name"' not in signin_section, "Sign-in modal should NOT have clinic_name"
assert 'name="specialization"' not in signin_section, "Sign-in modal should NOT have specialization"
print("✅ Sign-in modal contains ONLY email (no signup fields)")

print()
print("All route verifications passed! ✓")
