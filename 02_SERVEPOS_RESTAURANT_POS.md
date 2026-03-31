# ServePOS — Restaurant POS System

## Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | ServePOS |
| **Code** | `servepos` |
| **Domain** | Restaurant Point-of-Sale & Kitchen Management |
| **Type** | Full-stack web application (offline-capable) |
| **Primary Language** | Python (FastAPI) + TypeScript (Next.js) |
| **License** | MIT |

---

## 1. Project Overview

ServePOS is a self-hosted, offline-capable restaurant POS system that handles:
- **Order taking** (dine-in, takeaway, delivery)
- **Table management** with floor plan visualization
- **Kitchen Display System (KDS)** for order preparation tracking
- **Menu management** with categories, modifiers, combos
- **Inventory & stock tracking** with low-stock alerts
- **Payment processing** (cash, card, **QR code e-wallets**, split bills)
- **E-wallet QR payments** — Alipay, Touch 'n Go, GrabPay, Boost, WeChat Pay, etc. via generated QR codes and payment status polling
- **Delivery platform integration** — Receive and manage orders from **FoodPanda, GrabFood, ShopeeFood** and other delivery services via webhook/polling
- **Delivery management interface** — Dedicated dashboard for delivery orders with status tracking, rider info, and auto-accept rules
- **Receipt printing** (ESC/POS thermal printers)
- **Staff management** with roles and shift tracking
- **Reporting & analytics** (daily sales, item performance, staff performance)
- **Multi-outlet support** for chain restaurants
- **3rd-party integration** via REST APIs and webhooks

---

## 2. Technology Stack (All Free / Open-Source)

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| Backend | FastAPI | MIT | REST API + WebSocket |
| Frontend | Next.js 14+ (PWA) | MIT | POS interface (works offline) |
| Database | PostgreSQL 16 | PostgreSQL License | Persistent storage |
| Offline DB | Dexie.js (IndexedDB) | Apache 2.0 | Offline-first frontend storage |
| Cache | Redis / Valkey | BSD | Session cache, real-time pub/sub |
| UI | shadcn/ui + Tailwind CSS | MIT | Component library |
| Receipt Printing | `python-escpos` | MIT | ESC/POS thermal printer driver |
| Barcode | `python-barcode` + `qrcode` | MIT | Barcode/QR generation |
| PDF Reports | `weasyprint` | BSD | PDF receipt/report generation |
| Real-time | WebSocket (native FastAPI) | — | KDS updates, order sync |
| PWA | next-pwa / Workbox | MIT | Offline capability |
| Charts | Recharts | MIT | Analytics charts |
| State Mgmt | Zustand + Dexie.js | MIT | Frontend state + offline sync |
| Images | Sharp (Next.js built-in) | Apache 2.0 | Menu item image optimization |
| QR Code | `qrcode` + `Pillow` (Python) | MIT/PIL | Generate payment QR codes |
| QR Scan | `html5-qrcode` (JS) | Apache 2.0 | Scan customer QR codes from camera |
| Webhooks In | FastAPI webhook receivers | — | Receive delivery platform order pushes |
| HTTP Polling | `httpx` (Python async) | BSD | Poll delivery platform APIs for order updates |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              ServePOS Frontend (Next.js PWA)                  │
│  ┌──────────┐ ┌───────────┐ ┌──────┐ ┌──────────────────┐  │
│  │ POS      │ │ Kitchen   │ │ Admin│ │ Customer Display  │  │
│  │ Terminal │ │ Display   │ │ Panel│ │ (Order Status)    │  │
│  └──────────┘ └───────────┘ └──────┘ └──────────────────┘  │
│              ↕ IndexedDB (Dexie.js) for offline mode         │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Order    │ │ Menu     │ │ Payment  │ │ Inventory     │  │
│  │ Service  │ │ Service  │ │ Service  │ │ Service       │  │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├───────────────┤  │
│  │ Table    │ │ Staff    │ │ Report   │ │ Print         │  │
│  │ Service  │ │ Service  │ │ Service  │ │ Service       │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├──────────────────────────────────────────────────────────────┤
│            Redis (Cache + Pub/Sub for KDS sync)              │
├──────────────────────────────────────────────────────────────┤
│                 PostgreSQL (Primary Database)                 │
└──────────────────────────────────────────────────────────────┘
        │                    │
   ┌────▼────────┐   ┌──────▼─────────┐
   │ ESC/POS     │   │ External APIs  │
   │ Printer(s)  │   │ (Webhooks,     │
   │             │   │  Delivery apps)│
   └─────────────┘   └────────────────┘
```

### Offline-First Architecture

```
ONLINE MODE:
  Frontend ←→ Backend API ←→ PostgreSQL

OFFLINE MODE:
  Frontend ←→ IndexedDB (Dexie.js)
  (Orders queued locally, synced when connection restored)

SYNC PROCESS:
  1. Frontend detects connection restored
  2. Queued offline orders sent to backend in order
  3. Backend processes and confirms each order
  4. Conflicts resolved by timestamp (last-write-wins for non-critical, manual for orders)
```

---

## 4. Database Schema

```sql
-- Outlet / Branch
CREATE TABLE outlets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    tax_id VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'USD',
    tax_rate DECIMAL(5, 2) DEFAULT 0,
    service_charge_rate DECIMAL(5, 2) DEFAULT 0,
    receipt_header TEXT, -- custom receipt header text
    receipt_footer TEXT, -- custom receipt footer text
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users / Staff
CREATE TABLE staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'owner', 'manager', 'cashier', 'waiter', 'kitchen', 'admin'
    pin_code VARCHAR(10), -- quick POS login PIN
    phone VARCHAR(50),
    hourly_rate DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT true,
    permissions JSONB DEFAULT '[]', -- granular permissions array
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shifts
CREATE TABLE shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES staff(id) ON DELETE CASCADE,
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    clock_in TIMESTAMPTZ NOT NULL,
    clock_out TIMESTAMPTZ,
    break_minutes INT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Floor Plan & Tables
CREATE TABLE floor_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- 'Main Hall', 'Patio', 'VIP Room'
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    floor_area_id UUID REFERENCES floor_areas(id) ON DELETE CASCADE,
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    table_number VARCHAR(20) NOT NULL,
    capacity INT DEFAULT 4,
    shape VARCHAR(20) DEFAULT 'rectangle', -- 'rectangle', 'circle', 'square'
    pos_x FLOAT DEFAULT 0, -- position on floor plan
    pos_y FLOAT DEFAULT 0,
    width FLOAT DEFAULT 100,
    height FLOAT DEFAULT 60,
    status VARCHAR(20) DEFAULT 'available', -- 'available', 'occupied', 'reserved', 'cleaning'
    current_order_id UUID, -- FK set after orders table created
    is_active BOOLEAN DEFAULT true,
    UNIQUE(outlet_id, table_number)
);

-- Menu Categories
CREATE TABLE menu_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    parent_id UUID REFERENCES menu_categories(id) ON DELETE SET NULL, -- subcategories
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Menu Items
CREATE TABLE menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    category_id UUID REFERENCES menu_categories(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    cost_price DECIMAL(10, 2), -- for profit calculation
    image_url VARCHAR(500),
    sku VARCHAR(50),
    barcode VARCHAR(100),
    tax_rate_override DECIMAL(5, 2), -- NULL = use outlet default
    is_taxable BOOLEAN DEFAULT true,
    preparation_time_minutes INT, -- estimated prep time
    calories INT,
    allergens JSONB DEFAULT '[]', -- ['nuts', 'dairy', 'gluten']
    tags JSONB DEFAULT '[]', -- ['spicy', 'vegetarian', 'bestseller']
    is_available BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Modifier Groups (e.g., "Size", "Spice Level", "Add-ons")
CREATE TABLE modifier_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- 'Size', 'Spice Level', 'Extra Toppings'
    selection_type VARCHAR(20) DEFAULT 'single', -- 'single', 'multiple'
    min_selections INT DEFAULT 0,
    max_selections INT DEFAULT 1,
    is_required BOOLEAN DEFAULT false,
    sort_order INT DEFAULT 0
);

-- Modifier Options
CREATE TABLE modifier_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID REFERENCES modifier_groups(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- 'Large', 'Extra Spicy', 'Add Cheese'
    price_adjustment DECIMAL(10, 2) DEFAULT 0, -- additional cost
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- Menu Item ↔ Modifier Group link
CREATE TABLE menu_item_modifier_groups (
    menu_item_id UUID REFERENCES menu_items(id) ON DELETE CASCADE,
    modifier_group_id UUID REFERENCES modifier_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (menu_item_id, modifier_group_id)
);

-- Combo Meals
CREATE TABLE combo_meals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL, -- combo price (usually discounted)
    image_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE combo_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    combo_id UUID REFERENCES combo_meals(id) ON DELETE CASCADE,
    menu_item_id UUID REFERENCES menu_items(id) ON DELETE CASCADE,
    quantity INT DEFAULT 1,
    is_substitutable BOOLEAN DEFAULT false -- can swap for another item in category
);

-- Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    order_number VARCHAR(20) NOT NULL, -- sequential per outlet per day (e.g., #001)
    order_type VARCHAR(20) NOT NULL, -- 'dine_in', 'takeaway', 'delivery'
    table_id UUID REFERENCES tables(id) ON DELETE SET NULL,
    staff_id UUID REFERENCES staff(id) ON DELETE SET NULL, -- who took the order
    customer_name VARCHAR(200),
    customer_phone VARCHAR(50),
    customer_notes TEXT,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    service_charge DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    discount_reason VARCHAR(200),
    total DECIMAL(10, 2) NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- 'pending', 'confirmed', 'preparing', 'ready', 'served', 'completed', 'cancelled'
    payment_status VARCHAR(20) DEFAULT 'unpaid', -- 'unpaid', 'partial', 'paid', 'refunded'
    guest_count INT DEFAULT 1,
    is_void BOOLEAN DEFAULT false,
    void_reason TEXT,
    voided_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(outlet_id, order_number, created_at::date) -- unique per day
);

-- Order Items
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id UUID REFERENCES menu_items(id) ON DELETE SET NULL,
    item_name VARCHAR(200) NOT NULL, -- denormalized for receipt history
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    modifiers JSONB DEFAULT '[]', -- selected modifier details
    -- [{"group": "Size", "option": "Large", "price_adjustment": 2.00}]
    subtotal DECIMAL(10, 2) NOT NULL,
    notes TEXT, -- special instructions
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'preparing', 'ready', 'served', 'cancelled'
    is_void BOOLEAN DEFAULT false,
    sent_to_kitchen BOOLEAN DEFAULT false,
    kitchen_sent_at TIMESTAMPTZ,
    prepared_at TIMESTAMPTZ,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payments (supports multiple payment methods per order, including QR e-wallets)
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    payment_method VARCHAR(30) NOT NULL,
    -- 'cash', 'card', 'alipay', 'touch_n_go', 'grabpay', 'boost', 'wechat_pay',
    -- 'shopeepay', 'qr_generic', 'bank_transfer', 'other'
    amount DECIMAL(10, 2) NOT NULL,
    tip_amount DECIMAL(10, 2) DEFAULT 0,
    reference_number VARCHAR(100), -- transaction ref from e-wallet/card
    change_amount DECIMAL(10, 2) DEFAULT 0, -- for cash payments
    qr_code_data TEXT, -- generated QR payload for e-wallet payments
    qr_code_url VARCHAR(500), -- URL to generated QR image
    ewallet_transaction_id VARCHAR(200), -- e-wallet platform transaction ID
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' (QR generated, awaiting scan), 'processing', 'completed', 'refunded', 'failed', 'expired'
    expires_at TIMESTAMPTZ, -- QR code expiry time (typically 5-15 min)
    completed_at TIMESTAMPTZ,
    processed_by UUID REFERENCES staff(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- E-Wallet Provider Configuration
CREATE TABLE ewallet_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    provider_name VARCHAR(50) NOT NULL,
    -- 'alipay', 'touch_n_go', 'grabpay', 'boost', 'wechat_pay', 'shopeepay', 'qr_generic'
    display_name VARCHAR(100) NOT NULL, -- 'Alipay', 'Touch \'n Go eWallet'
    merchant_id VARCHAR(200), -- merchant account ID on the platform
    credentials_encrypted JSONB NOT NULL, -- encrypted API keys/secrets
    -- Alipay: {"app_id": "...", "private_key": "...", "public_key": "..."}
    -- TnG: {"client_id": "...", "client_secret": "...", "merchant_id": "..."}
    -- GrabPay: {"partner_id": "...", "partner_secret": "...", "merchant_id": "..."}
    -- Generic QR: {"type": "static", "qr_content": "..."}  -- for static merchant QR
    qr_type VARCHAR(20) DEFAULT 'dynamic', -- 'dynamic' (per-order QR) or 'static' (fixed merchant QR)
    callback_url VARCHAR(500), -- webhook URL for payment notifications from provider
    is_active BOOLEAN DEFAULT true,
    logo_url VARCHAR(500),
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Delivery Platform Integration
CREATE TABLE delivery_platforms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    platform_name VARCHAR(50) NOT NULL, -- 'foodpanda', 'grabfood', 'shopeefood'
    display_name VARCHAR(100) NOT NULL, -- 'FoodPanda', 'GrabFood', 'ShopeeFood'
    store_id VARCHAR(200), -- restaurant ID on the platform
    credentials_encrypted JSONB NOT NULL, -- encrypted API token/keys
    -- FoodPanda: {"api_token": "...", "vendor_id": "...", "chain_id": "..."}
    -- GrabFood: {"client_id": "...", "client_secret": "...", "merchant_id": "..."}
    integration_type VARCHAR(20) DEFAULT 'webhook', -- 'webhook', 'polling', 'manual'
    webhook_secret VARCHAR(200), -- for verifying inbound webhook signatures
    polling_interval_seconds INT DEFAULT 30, -- if polling mode
    auto_accept BOOLEAN DEFAULT false, -- auto-accept incoming orders
    auto_accept_delay_seconds INT DEFAULT 0, -- delay before auto-accept
    menu_sync_enabled BOOLEAN DEFAULT false, -- sync menu to platform
    is_active BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Delivery Orders (orders received from delivery platforms)
CREATE TABLE delivery_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE, -- link to internal order
    platform_id UUID REFERENCES delivery_platforms(id) ON DELETE SET NULL,
    platform_order_id VARCHAR(200) NOT NULL, -- FoodPanda/Grab order ID
    platform_order_number VARCHAR(50), -- display number (e.g., 'FP-A1B2')
    platform_status VARCHAR(30), -- platform-specific status
    -- 'new', 'accepted', 'preparing', 'ready_for_pickup', 'picked_up', 'delivered', 'cancelled'
    customer_name VARCHAR(200),
    customer_phone VARCHAR(50),
    customer_address TEXT,
    delivery_notes TEXT,
    rider_name VARCHAR(200),
    rider_phone VARCHAR(50),
    rider_vehicle VARCHAR(50),
    estimated_pickup_time TIMESTAMPTZ,
    estimated_delivery_time TIMESTAMPTZ,
    actual_pickup_time TIMESTAMPTZ,
    platform_subtotal DECIMAL(10, 2), -- price on platform (may differ from internal)
    platform_commission DECIMAL(10, 2), -- platform commission fee
    platform_delivery_fee DECIMAL(10, 2),
    net_amount DECIMAL(10, 2), -- amount restaurant receives
    raw_payload JSONB, -- full original payload from platform for debugging
    is_accepted BOOLEAN DEFAULT false,
    accepted_at TIMESTAMPTZ,
    rejected_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform_id, platform_order_id)
);

-- Inventory
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(50),
    unit VARCHAR(30) NOT NULL, -- 'kg', 'liter', 'piece', 'pack', 'bottle'
    quantity DECIMAL(10, 3) NOT NULL DEFAULT 0,
    min_quantity DECIMAL(10, 3) DEFAULT 0, -- low stock threshold
    cost_per_unit DECIMAL(10, 2),
    supplier VARCHAR(200),
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_restocked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Menu Item → Inventory Recipe (ingredient mapping)
CREATE TABLE menu_item_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    menu_item_id UUID REFERENCES menu_items(id) ON DELETE CASCADE,
    inventory_item_id UUID REFERENCES inventory_items(id) ON DELETE CASCADE,
    quantity_used DECIMAL(10, 3) NOT NULL, -- how much used per serving
    unit VARCHAR(30) NOT NULL
);

-- Inventory Transactions (stock in/out log)
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inventory_item_id UUID REFERENCES inventory_items(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL, -- 'restock', 'consumption', 'waste', 'adjustment'
    quantity_change DECIMAL(10, 3) NOT NULL, -- positive=in, negative=out
    reference_id UUID, -- order_id or restock_id
    notes TEXT,
    performed_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Discounts / Promotions
CREATE TABLE promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(30) NOT NULL, -- 'percentage', 'fixed_amount', 'buy_x_get_y', 'happy_hour'
    value DECIMAL(10, 2) NOT NULL, -- percentage or fixed amount
    min_order_amount DECIMAL(10, 2),
    applicable_items JSONB DEFAULT '[]', -- specific menu item IDs, empty = all
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    valid_days JSONB DEFAULT '[0,1,2,3,4,5,6]', -- days of week
    valid_hours_start TIME,
    valid_hours_end TIME,
    promo_code VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    usage_limit INT,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cash Register Sessions (Shifts)
CREATE TABLE register_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    opened_by UUID REFERENCES staff(id),
    closed_by UUID REFERENCES staff(id),
    opening_cash DECIMAL(10, 2) NOT NULL,
    closing_cash DECIMAL(10, 2),
    expected_cash DECIMAL(10, 2), -- calculated from orders
    cash_difference DECIMAL(10, 2), -- over/short
    total_sales DECIMAL(10, 2),
    total_refunds DECIMAL(10, 2),
    total_discounts DECIMAL(10, 2),
    notes TEXT,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'open' -- 'open', 'closed'
);

-- Reservations
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlet_id UUID REFERENCES outlets(id) ON DELETE CASCADE,
    table_id UUID REFERENCES tables(id) ON DELETE SET NULL,
    customer_name VARCHAR(200) NOT NULL,
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    party_size INT NOT NULL,
    reservation_time TIMESTAMPTZ NOT NULL,
    duration_minutes INT DEFAULT 90,
    status VARCHAR(20) DEFAULT 'confirmed', -- 'confirmed', 'seated', 'completed', 'cancelled', 'no_show'
    notes TEXT,
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. API Endpoints

### Authentication & Staff
```
POST   /api/v1/auth/login              - Staff login (email + password)
POST   /api/v1/auth/pin-login          - Quick PIN login (POS terminal)
POST   /api/v1/auth/refresh            - Refresh token
GET    /api/v1/staff                    - List staff members
POST   /api/v1/staff                   - Create staff member
PUT    /api/v1/staff/{id}              - Update staff
DELETE /api/v1/staff/{id}              - Deactivate staff
POST   /api/v1/staff/{id}/clock-in     - Clock in for shift
POST   /api/v1/staff/{id}/clock-out    - Clock out
GET    /api/v1/staff/{id}/shifts       - Shift history
```

### Outlets
```
GET    /api/v1/outlets                  - List outlets
POST   /api/v1/outlets                 - Create outlet
GET    /api/v1/outlets/{id}            - Outlet details
PUT    /api/v1/outlets/{id}            - Update outlet
GET    /api/v1/outlets/{id}/settings   - Outlet settings (tax, receipt, etc.)
PUT    /api/v1/outlets/{id}/settings   - Update settings
```

### Floor Plan & Tables
```
GET    /api/v1/tables                   - List all tables with status
GET    /api/v1/tables/floor-plan        - Get floor plan layout
PUT    /api/v1/tables/floor-plan        - Update floor plan positions
GET    /api/v1/tables/{id}              - Table detail with current order
PUT    /api/v1/tables/{id}/status       - Update table status
POST   /api/v1/tables/{id}/merge        - Merge tables for large party
POST   /api/v1/tables/{id}/transfer     - Transfer order to another table
GET    /api/v1/floor-areas              - List floor areas
POST   /api/v1/floor-areas             - Create floor area
```

### Menu Management
```
GET    /api/v1/menu/categories          - List categories
POST   /api/v1/menu/categories         - Create category
PUT    /api/v1/menu/categories/{id}    - Update category
DELETE /api/v1/menu/categories/{id}    - Delete category
GET    /api/v1/menu/items               - List all menu items
POST   /api/v1/menu/items              - Create menu item
GET    /api/v1/menu/items/{id}         - Menu item detail
PUT    /api/v1/menu/items/{id}         - Update menu item
DELETE /api/v1/menu/items/{id}         - Delete menu item
PUT    /api/v1/menu/items/{id}/availability - Toggle availability
GET    /api/v1/menu/modifiers           - List modifier groups
POST   /api/v1/menu/modifiers          - Create modifier group
PUT    /api/v1/menu/modifiers/{id}     - Update modifier group
GET    /api/v1/menu/combos              - List combos
POST   /api/v1/menu/combos             - Create combo
PUT    /api/v1/menu/combos/{id}        - Update combo
GET    /api/v1/menu/full                - Full menu tree (categories → items → modifiers)
```

### Orders
```
POST   /api/v1/orders                   - Create new order
GET    /api/v1/orders                   - List orders (filterable by date, status, type)
GET    /api/v1/orders/{id}              - Order detail
PUT    /api/v1/orders/{id}              - Update order (add/remove items)
POST   /api/v1/orders/{id}/items        - Add items to existing order
PUT    /api/v1/orders/{id}/items/{iid}  - Update order item (qty, modifiers)
DELETE /api/v1/orders/{id}/items/{iid}  - Remove item from order
POST   /api/v1/orders/{id}/send-to-kitchen - Send order to kitchen (KDS)
PUT    /api/v1/orders/{id}/status       - Update order status
POST   /api/v1/orders/{id}/void         - Void entire order
POST   /api/v1/orders/{id}/discount     - Apply discount to order
POST   /api/v1/orders/{id}/split        - Split bill (by item or equally)
POST   /api/v1/orders/{id}/print        - Print receipt
GET    /api/v1/orders/active            - Currently active orders (for KDS)
POST   /api/v1/orders/sync              - Sync offline orders (bulk create)
```

### Kitchen Display System (KDS)
```
GET    /api/v1/kitchen/orders           - Active kitchen orders
WS     /ws/kitchen                      - Real-time kitchen order stream
PUT    /api/v1/kitchen/items/{id}/status - Update item status (preparing/ready)
POST   /api/v1/kitchen/items/{id}/bump  - Bump item (mark as complete)
GET    /api/v1/kitchen/stats            - Avg prep time, pending count
```

### Payments (Multi-Method + QR E-Wallet)
```
POST   /api/v1/payments                 - Process payment for order
       Body: { order_id, payment_method, amount, ... }
       Supports: cash, card, alipay, touch_n_go, grabpay, boost, wechat_pay, shopeepay
GET    /api/v1/payments/{id}            - Payment detail
POST   /api/v1/payments/{id}/refund     - Refund payment
GET    /api/v1/orders/{id}/payments     - All payments for an order (supports split across methods)
POST   /api/v1/payments/qr/generate     - Generate QR code for e-wallet payment
       Body: { order_id, provider: "alipay", amount: 31.32 }
       Returns: { qr_code_base64, qr_url, payment_id, expires_at }
GET    /api/v1/payments/qr/{payment_id}/status  - Poll payment status (pending → completed)
       Returns: { status: "completed", transaction_id: "..." }
POST   /api/v1/payments/qr/callback      - Webhook callback from e-wallet provider
       (Verifies signature, updates payment status automatically)
POST   /api/v1/payments/qr/scan          - Process customer-presented QR code
       Body: { order_id, qr_data: "...scanned from customer phone..." }
```

### E-Wallet Providers
```
GET    /api/v1/ewallet/providers          - List configured e-wallet providers
POST   /api/v1/ewallet/providers         - Add provider config
PUT    /api/v1/ewallet/providers/{id}    - Update provider credentials
DELETE /api/v1/ewallet/providers/{id}    - Remove provider
POST   /api/v1/ewallet/providers/{id}/test - Test provider connection
GET    /api/v1/ewallet/providers/available - List all supported providers with setup status
```

### Delivery Platform Integration
```
GET    /api/v1/delivery/platforms          - List configured delivery platforms
POST   /api/v1/delivery/platforms         - Add delivery platform
PUT    /api/v1/delivery/platforms/{id}    - Update platform config
DELETE /api/v1/delivery/platforms/{id}    - Remove platform
POST   /api/v1/delivery/platforms/{id}/test - Test platform connection
POST   /api/v1/delivery/platforms/{id}/sync-menu - Push menu to platform

GET    /api/v1/delivery/orders             - List all delivery orders (filter by platform, status, date)
GET    /api/v1/delivery/orders/{id}        - Delivery order detail (with rider info, timeline)
POST   /api/v1/delivery/orders/{id}/accept - Accept incoming delivery order
POST   /api/v1/delivery/orders/{id}/reject - Reject order with reason
PUT    /api/v1/delivery/orders/{id}/status  - Update delivery order status (preparing → ready)
POST   /api/v1/delivery/orders/{id}/ready  - Mark order ready for rider pickup
GET    /api/v1/delivery/orders/pending      - Orders awaiting acceptance
GET    /api/v1/delivery/orders/active       - Currently active delivery orders

POST   /api/v1/delivery/webhook/foodpanda  - FoodPanda order webhook receiver
POST   /api/v1/delivery/webhook/grabfood   - GrabFood order webhook receiver
POST   /api/v1/delivery/webhook/shopeefood - ShopeeFood order webhook receiver
POST   /api/v1/delivery/webhook/generic    - Generic delivery platform webhook
```

### Inventory
```
GET    /api/v1/inventory                - List inventory items
POST   /api/v1/inventory               - Add inventory item
PUT    /api/v1/inventory/{id}          - Update inventory item
POST   /api/v1/inventory/{id}/restock  - Record restocking
GET    /api/v1/inventory/low-stock     - Items below min quantity
GET    /api/v1/inventory/{id}/transactions - Stock movement history
POST   /api/v1/inventory/waste         - Record waste/spoilage
```

### Promotions & Discounts
```
GET    /api/v1/promotions               - List promotions
POST   /api/v1/promotions              - Create promotion
PUT    /api/v1/promotions/{id}         - Update promotion
DELETE /api/v1/promotions/{id}         - Delete promotion
POST   /api/v1/promotions/validate     - Validate promo code for order
```

### Reservations
```
GET    /api/v1/reservations             - List reservations
POST   /api/v1/reservations            - Create reservation
PUT    /api/v1/reservations/{id}       - Update reservation
PUT    /api/v1/reservations/{id}/status - Update status (seated, cancel, no-show)
GET    /api/v1/reservations/availability - Check available slots
```

### Register Sessions
```
POST   /api/v1/register/open            - Open cash register
POST   /api/v1/register/close           - Close register (end of day)
GET    /api/v1/register/current         - Current register session
GET    /api/v1/register/history         - Past register sessions
```

### Reports & Analytics
```
GET    /api/v1/reports/daily-sales      - Daily sales summary
GET    /api/v1/reports/sales-by-item    - Sales breakdown by menu item
GET    /api/v1/reports/sales-by-category - Sales by category
GET    /api/v1/reports/sales-by-staff   - Sales per staff member
GET    /api/v1/reports/hourly-sales     - Sales by hour of day
GET    /api/v1/reports/payment-methods  - Payment method breakdown
GET    /api/v1/reports/inventory        - Inventory usage report
GET    /api/v1/reports/waste            - Waste/spoilage report
GET    /api/v1/reports/profit-margin    - Profit margins by item
GET    /api/v1/reports/peak-hours       - Busiest hours analysis
GET    /api/v1/reports/export           - Export any report as CSV/PDF
       ?type=daily_sales&from=2026-01-01&to=2026-03-31&format=csv
```

### System & Integration
```
GET    /api/v1/health                    - Health check
POST   /api/v1/webhooks/config          - Configure outbound webhooks
POST   /api/v1/webhooks/test            - Test webhook delivery
GET    /api/v1/system/printers          - List connected printers
POST   /api/v1/system/printers/test     - Test print
```

### WebSocket Endpoints
```
WS     /ws/kitchen                       - Kitchen display real-time updates
WS     /ws/orders                        - Order status changes
WS     /ws/tables                        - Table status changes (floor plan)
WS     /ws/notifications                 - Staff notifications (low stock, etc.)
WS     /ws/delivery                      - Delivery order real-time updates (new orders, rider status)
WS     /ws/payments                      - QR payment status updates (pending → completed)
```

---

## 6. Frontend Pages

| Route | Page | Role Access |
|-------|------|-------------|
| `/login` | Staff Login (Email/PIN) | All |
| `/` | POS Terminal (Main Order Screen) | Cashier, Waiter, Manager |
| `/tables` | Floor Plan & Table Map | Waiter, Manager |
| `/kitchen` | Kitchen Display System | Kitchen Staff |
| `/orders` | Order List & History | Cashier, Manager |
| `/orders/{id}` | Order Detail / Edit | Cashier, Manager |
| `/menu` | Menu Management | Manager, Admin |
| `/menu/items/new` | Add Menu Item | Manager, Admin |
| `/menu/items/{id}` | Edit Menu Item | Manager, Admin |
| `/inventory` | Inventory Dashboard | Manager, Admin |
| `/inventory/{id}` | Inventory Item Detail | Manager, Admin |
| `/staff` | Staff Management | Manager, Admin |
| `/reservations` | Reservation Calendar | All |
| `/register` | Cash Register (Open/Close) | Cashier, Manager |
| `/reports` | Reports & Analytics Dashboard | Manager, Owner, Admin |
| `/reports/{type}` | Specific Report View | Manager, Owner, Admin |
| `/settings` | Outlet Settings | Owner, Admin |
| `/customer-display` | Customer-Facing Order Display | Public (kiosk mode) |
| `/delivery` | Delivery Orders Dashboard | Cashier, Manager |
| `/delivery/orders/{id}` | Delivery Order Detail (rider, timeline) | Cashier, Manager |
| `/delivery/settings` | Delivery Platform Configuration | Manager, Admin |
| `/payments/qr` | QR Payment Screen (show QR, await scan) | Cashier |
| `/settings/ewallet` | E-Wallet Provider Configuration | Manager, Admin |

### POS Terminal Layout (Main Screen)

```
┌────────────────────────────────────────────────────────────────┐
│  [ServePOS]  Table: #5 (4 guests)  │  Staff: John  │  [Logout]│
├──────────────────────────┬─────────────────────────────────────┤
│                          │                                     │
│  ┌─────────────────────┐ │  ┌─────────────────────────────┐   │
│  │ CATEGORIES          │ │  │ CURRENT ORDER               │   │
│  │ ┌──────┐ ┌──────┐   │ │  │                             │   │
│  │ │Drinks│ │Foods │   │ │  │  1x Chicken Rice    $8.50   │   │
│  │ │      │ │      │   │ │  │     + Extra Spicy   $0.50   │   │
│  │ └──────┘ └──────┘   │ │  │  2x Iced Tea        $6.00   │   │
│  │ ┌──────┐ ┌──────┐   │ │  │  1x Combo A        $12.00   │   │
│  │ │Desser│ │Sides │   │ │  │                             │   │
│  │ └──────┘ └──────┘   │ │  │ ─────────────────────────── │   │
│  ├─────────────────────┤ │  │  Subtotal:         $27.00   │   │
│  │ MENU ITEMS          │ │  │  Tax (6%):          $1.62   │   │
│  │ ┌──────┐ ┌──────┐   │ │  │  Service (10%):    $2.70   │   │
│  │ │Chicke│ │Noodle│   │ │  │ ─────────────────────────── │   │
│  │ │n Rice│ │Soup  │   │ │  │  TOTAL:           $31.32   │   │
│  │ │$8.50 │ │$7.00 │   │ │  │                             │   │
│  │ └──────┘ └──────┘   │ │  │ [Send to Kitchen] [Hold]    │   │
│  │ ┌──────┐ ┌──────┐   │ │  │ [Discount] [Split Bill]     │   │
│  │ │Iced  │ │Coffee│   │ │  │ [PAY - $31.32]              │   │
│  │ │Tea   │ │      │   │ │  │                             │   │
│  │ │$3.00 │ │$4.50 │   │ │  └─────────────────────────────┘   │
│  │ └──────┘ └──────┘   │ │                                     │
│  └─────────────────────┘ │                                     │
└──────────────────────────┴─────────────────────────────────────┘
```

---

## 7. Implementation Phases

### Phase 1: Core Setup (Week 1-2)
- [ ] Project scaffolding (FastAPI + Next.js + Docker)
- [ ] Database schema and migrations
- [ ] Auth system (JWT + PIN login)
- [ ] Outlet and staff CRUD
- [ ] Basic role-based access control

### Phase 2: Menu & Orders (Week 3-5)
- [ ] Menu management (categories, items, modifiers, combos)
- [ ] POS terminal UI (touch-friendly)
- [ ] Order creation and management
- [ ] Order item modifiers and notes
- [ ] Price calculation (tax, service charge)

### Phase 3: Table Management & KDS (Week 6-7)
- [ ] Floor plan editor (drag-and-drop tables)
- [ ] Table status tracking
- [ ] Kitchen Display System (WebSocket real-time)
- [ ] Order → Kitchen → Ready → Served flow
- [ ] Table merge and transfer

### Phase 4: Payments & Receipt (Week 8-10)
- [ ] Basic payment processing (cash, card entry)
- [ ] Split bill functionality (across multiple payment methods)
- [ ] Receipt printing (ESC/POS)
- [ ] Cash register open/close
- [ ] Refund handling
- [ ] E-wallet provider configuration system
- [ ] QR code generation for e-wallet payments (Alipay, Touch 'n Go, GrabPay, Boost, WeChat Pay, ShopeePay)
- [ ] Dynamic QR (per-order amount) and static QR (fixed merchant code) support
- [ ] QR payment status polling + webhook callback handling
- [ ] QR payment screen UI (display QR, show countdown, auto-detect completion)
- [ ] Customer-presented QR scan (cashier scans customer's phone)
- [ ] Multi-method payment per order (e.g., $20 cash + $11.32 Touch 'n Go)
- [ ] Payment method breakdown in receipts and reports

### Phase 5: Inventory (Week 10)
- [ ] Inventory items and tracking
- [ ] Menu item → ingredient mapping
- [ ] Auto-deduction on order completion
- [ ] Low stock alerts
- [ ] Restock and waste logging

### Phase 6: Reporting & Analytics (Week 11-12)
- [ ] Daily sales report
- [ ] Item-level and category-level sales
- [ ] Staff performance
- [ ] Inventory reports
- [ ] PDF/CSV export
- [ ] Charts and dashboards

### Phase 7: Offline & PWA (Week 13)
- [ ] PWA setup (service worker, manifest)
- [ ] IndexedDB offline order storage (Dexie.js)
- [ ] Offline order taking
- [ ] Sync mechanism on reconnect

### Phase 8: Delivery Platform Integration (Week 14-16)
- [ ] Delivery platform configuration system (FoodPanda, GrabFood, ShopeeFood)
- [ ] Webhook receivers for each platform (receive new orders automatically)
- [ ] Polling fallback for platforms without webhook support
- [ ] Auto-mapping of delivery platform menu items to internal menu
- [ ] Delivery orders dashboard (dedicated UI with incoming order alerts)
- [ ] Order accept/reject flow with configurable auto-accept rules
- [ ] Order status sync (preparing → ready for pickup → picked up)
- [ ] Rider info display (name, phone, vehicle, ETA)
- [ ] Delivery order notification sounds (new order bell)
- [ ] Kitchen routing (delivery orders auto-sent to KDS with "DELIVERY" tag)
- [ ] Platform commission tracking and net revenue calculation
- [ ] Menu push/sync to delivery platforms (availability, price, out-of-stock)
- [ ] Delivery analytics (orders per platform, avg prep-to-pickup time, commission costs)

### Phase 9: Advanced Features (Week 17-19)
- [ ] Reservations system
- [ ] Promotions and promo codes
- [ ] Customer-facing display
- [ ] Multi-outlet support
- [ ] Webhook outbound notifications
- [ ] API documentation (Swagger auto-generated)
