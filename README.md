---
title: NexAutomate TG Bot
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Telegram Digital Delivery System (TG BOT) - Operations Manual

Welcome to the **Digital Delivery System Command Center**. This project is a complete production-ready automation linking a **Python Telegram Bot**, an **async FastAPI Backend**, and a **Next.js Admin Dashboard** via a central **Supabase PostgreSQL** database.

---

## 🏗️ Project Architecture & Structure

```
telegram_bot/
  ├── handlers/
  │    ├── menu.py          # Dynamic product catalogs, mock payment testing
  │    └── delivery.py      # Interactive user email collection for OTT
  ├── services/
  │    └── razorpay_service.py # Secure payment link creation (Auto Mock in Dev)
  └── main.py               # Bot entrypoint & event polling loop

backend/
  ├── services/
  │    ├── supabase_service.py # Bypasses RLS with service-role for admin queries
  │    └── resend_service.py   # Secure Resend API email wrapper
  └── main.py               # FastAPI webhook server & dynamic credential dispatch

admin_dashboard/            # Next.js 14+ cyber-themed management dashboard
  ├── app/                  # Pages for Products, Credentials, Orders, Payments
  ├── lib/                  # Supabase browser clients
  ├── tailwind.config.js    # Customized FBI dark aesthetic palette
  └── package.json          # Node dependencies

database/
  └── schema.sql            # Core tables & performance-tuned queries
```

---

## ⚡ Quick Start Local Development & Testing

Follow these steps to run the complete system locally on your PC.

### Step 1: Install Python Dependencies
Open your terminal and run:
```bash
pip install fastapi uvicorn supabase python-telegram-bot httpx
```

### Step 2: Set Up Environment Variables
We have already created the active `.env` file at the root:
* **Bot Token:** Loaded successfully (`8891028307:AAFzy_dh...`)
* **Supabase URL & Service Role Key:** Programmed securely
* **Resend API Key:** Configured (`re_LN1LRZV7...`)

### Step 3: Run the FastAPI Webhook Server
Start the backend server locally on port 8000:
```bash
# From the root directory (TG BOT)
uvicorn backend.main:app --reload --port 8000
```
*Your server is now active at `http://127.0.0.1:8000`.*

### Step 4: Run the Telegram Bot
Open a new terminal window and run:
```bash
# From the root directory (TG BOT)
python telegram_bot/main.py
```
*The bot is now online and polling for user commands.*

### Step 5: Boot the Admin Dashboard
Open a new terminal window, navigate into the dashboard folder, install and start:
```bash
cd admin_dashboard
npm install
npm run dev
```
*The dashboard will start running at `http://localhost:3000`.*
* **Clearance Credentials for Demo Bypass:**
  * **Email:** `admin@fbi.gov`
  * **Password:** `command_center_99`

---

## 🧪 How to Test the Entire Flow (Zero Setup Webhook Simulation)

Since you are in local testing and have not connected live Razorpay webhook endpoints or live keys yet, we have built a **custom developer simulation tool** directly into the bot callback loop!

1. Open your Telegram bot (`https://t.me/your_bot`) and type `/start`.
2. Browse products. If there are no products, log in to the **Admin Dashboard** (`http://localhost:3000`), navigate to **Products Manager**, and click **Deploy Product** (Create a game like *GTA V* as `AUTO` or an OTT subscription like *Netflix* as `MANUAL`).
3. If testing a Game, add a few test credentials in the **Credentials Vault** on the dashboard.
4. Back in the Telegram bot, select your product and click **💳 Buy Now**.
5. The bot will automatically generate a secure checkout link.
6. Since we are in development mode, a second button will automatically appear: **🧪 [TEST] Simulate Webhook Success**.
7. Click this button! It will instantly dispatch a payment event to your local FastAPI server (`http://127.0.0.1:8000/webhook/razorpay`).
8. **Watch the Magic:**
   * **For Games:** The backend intercepts the payment, grabs a credential from the Supabase Vault, marks it used, and sends the Login ID and Passcode to you on Telegram instantly!
   * **For OTT:** The bot asks you to send your email. Once you reply with a valid email (e.g., `growix299@gmail.com`), it logs an OTT request in the DB, dispatches a beautiful activation email using your Resend API token, and alerts the Admin on the dashboard!

---

## 🔒 Security Advisory: Supabase RLS policies

As indicated by the Supabase project telemetry:
> **Critical:** Row Level Security (RLS) is currently disabled on the database tables.
This is completely fine for local testing. However, before pushing to production, execute the following SQL in your Supabase SQL Editor to enable security guards:

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ott_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
```
*(Once enabled, write Select/Insert policies matching admin users).*
