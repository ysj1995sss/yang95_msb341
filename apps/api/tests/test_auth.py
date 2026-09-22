def test_register_and_login(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "secret123"})
    assert r.status_code == 201
    assert "access_token" in r.json()

    r2 = client.post("/auth/register", json={"email": "a@example.com", "password": "secret123"})
    assert r2.status_code == 409

    r3 = client.post("/auth/login", json={"email": "a@example.com", "password": "secret123"})
    assert r3.status_code == 200

    r4 = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong"})
    assert r4.status_code == 401
