# Auth API

A secure authentication API built with FastAPI and Supabase Auth. Handles sign up, log in, log out, and protects specific routes using JWT bearer tokens.

## What this is

This project implements a real authentication flow using Supabase as the Identity Provider (IdP). Clients sign up and log in through Supabase, receive a JWT access token, and present that token to access protected routes. The server verifies every token against Supabase before granting access.

## How to run it

1. Clone the repo and enter the folder:
   ```
   git clone https://github.com/subanaash/auth-api.git
   cd auth-api
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   venv\Scripts\activate   # on Mac/Linux: source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install fastapi uvicorn supabase python-dotenv
   ```

4. Create your own Supabase project at [supabase.com](https://supabase.com), then create a `.env` file in the project root:
   ```
   SUPABASE_URL=your_project_url
   SUPABASE_KEY=your_publishable_key
   PORT=8000
   ```
   (Find these under Project Settings → API in your Supabase dashboard. `.env` is gitignored — never commit real keys.)

5. In Supabase, go to Authentication settings and turn off "Confirm email" for local testing, so new signups can log in immediately.

6. Run the server:
   ```
   uvicorn main:app --reload
   ```

7. Open your browser to `http://127.0.0.1:8000/docs`

## API reference

| Method | Endpoint | Auth required | Description | Success Code | Error Codes |
|--------|----------|:---:|--------------|:---:|:---:|
| POST | `/auth/signup` | No | Create a new user account | 201 | 400 |
| POST | `/auth/login` | No | Authenticate and receive a JWT | 200 | 400, 401 |
| POST | `/auth/logout` | Yes | End the current session | 204 | 401 |
| GET | `/public/info` | No | Public, unprotected message | 200 | — |
| GET | `/protected/profile` | Yes | Read the authenticated user's own profile | 200 | 401 |
| GET | `/protected/dashboard` | Yes | Second protected route, proves middleware reuse | 200 | 401 |

## How authentication works

1. A client signs up or logs in via `/auth/signup` or `/auth/login`, sending credentials directly to this API.
2. This API forwards those credentials to Supabase Auth. On success, Supabase returns a JWT access token.
3. The client sends that token on future requests in the `Authorization: Bearer <token>` header.
4. Protected routes use a shared FastAPI dependency (`get_current_user`) that extracts the token, verifies it against Supabase, and rejects the request with `401` if the token is missing, invalid, or expired.
5. Both `/protected/profile` and `/protected/dashboard` reuse the same dependency, proving the auth check is written once and applied everywhere it's needed.

## Swagger UI

Interactive docs are available at `http://127.0.0.1:8000/docs`. Protected routes show a padlock icon; click "Authorize" at the top of the page and paste a valid access token (obtained from `/auth/login`) to test them directly from the browser.

<img width="1167" height="896" alt="protected-profile-screenshot" src="https://github.com/user-attachments/assets/156a5ca4-4a3a-40a5-8656-096fdcaff6ed" />

<img width="1176" height="887" alt="protected-dashboard-screenshot" src="https://github.com/user-attachments/assets/e585bc53-82b2-4af8-bdd7-3249c33875e1" />

<img width="1180" height="651" alt="logout-screenshot" src="https://github.com/user-attachments/assets/604e3f2e-e9c7-4bbc-a962-88006d4b0de9" />

