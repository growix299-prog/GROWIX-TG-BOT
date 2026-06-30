-- Database Schema for Telegram Digital Delivery System

-- 1. Create Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    wallet_balance NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Create Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('OTT', 'Games')),
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    delivery_type VARCHAR(50) NOT NULL CHECK (delivery_type IN ('AUTO', 'MANUAL')),
    active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create Credentials table
CREATE TABLE IF NOT EXISTS credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    email_or_username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'UNUSED' NOT NULL CHECK (status IN ('UNUSED', 'USED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Create Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    telegram_id BIGINT NOT NULL,
    product_id UUID REFERENCES products(id) NOT NULL,
    payment_id VARCHAR(255) UNIQUE,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(50) DEFAULT 'PENDING' NOT NULL CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED')),
    delivery_status VARCHAR(50) DEFAULT 'PENDING' NOT NULL CHECK (delivery_status IN ('PENDING', 'DELIVERED', 'MANUAL_PROCESSING')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Create OTT Requests table
CREATE TABLE IF NOT EXISTS ott_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE UNIQUE NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' NOT NULL CHECK (status IN ('PENDING', 'COMPLETED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. Create Payments table
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    razorpay_order_id VARCHAR(255),
    razorpay_payment_id VARCHAR(255) UNIQUE,
    amount NUMERIC(10, 2),
    verified BOOLEAN DEFAULT false NOT NULL,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- CREATE OPTIMIZED INDEXES FOR HIGH-PERFORMANCE QUERIES

-- Speed up user lookup by Telegram ID
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Speed up fetching of available (UNUSED) credentials for a specific game/product
CREATE INDEX IF NOT EXISTS idx_credentials_product_unused ON credentials(product_id) WHERE status = 'UNUSED';

-- Speed up order history lookup for bot users
CREATE INDEX IF NOT EXISTS idx_orders_telegram_id ON orders(telegram_id);

-- Speed up webhook lookup of orders using payment reference
CREATE INDEX IF NOT EXISTS idx_orders_payment_id ON orders(payment_id);

-- 7. Create Wallet Transactions table
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('DEPOSIT', 'PURCHASE', 'REFUND')),
    reference_id VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
