import logging
import os
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole, AuthProvider, StorePolicy
from app.models.product import Category, Product, ProductVariant
from app.models.cart import Cart
from app.models.order import Coupon, CouponType

logger = logging.getLogger(__name__)


async def seed_data(db: AsyncSession) -> None:
    """Auto-seed default categories, products, coupons, and policies if empty."""
    is_prod = settings.ENVIRONMENT == "production"
    if is_prod:
        logger.info("Production environment detected. Skipping automatic demo data seeding.")
        return

    logger.info("Checking if database seeding is required...")

    admin_email = os.getenv("ADMIN_EMAIL", "admin@keecrochet.com")
    admin_pass = os.getenv("ADMIN_PASSWORD", "adminpassword123")
    customer_email = os.getenv("CUSTOMER_EMAIL", "customer@keecrochet.com")
    customer_pass = os.getenv("CUSTOMER_PASSWORD", "customerpassword123")

    # 1. Seed Users (Development only)
    user_result = await db.execute(select(User))
    users = user_result.scalars().all()
    if not users:
        logger.info("No users found. Seeding default admin and customer accounts...")
        admin = User(
            email=admin_email,
            full_name="Kee Admin",
            hashed_password=hash_password(admin_pass),
            role=UserRole.admin,
            auth_provider=AuthProvider.email,
            is_active=True,
            is_verified=True,
        )
        customer = User(
            email=customer_email,
            full_name="Madhav Nair",
            hashed_password=hash_password(customer_pass),
            role=UserRole.customer,
            auth_provider=AuthProvider.email,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        db.add(customer)
        await db.flush()

        # Add carts for seeded users
        db.add(Cart(user_id=admin.id))
        db.add(Cart(user_id=customer.id))
        logger.info("Admin & Customer users seeded successfully.")
    else:
        logger.info("Users exist. Skipping user seeding.")

    # 2. Seed Categories
    category_result = await db.execute(select(Category))
    categories = category_result.scalars().all()
    
    cat_bouquets = None
    cat_plushies = None
    cat_keychains = None

    if not categories:
        logger.info("No categories found. Seeding default categories...")
        cat_bouquets = Category(
            name="Handmade Bouquets",
            slug="bouquets",
            description="Everlasting crochet flowers, tulips, and sunflowers wrapped with love."
        )
        cat_plushies = Category(
            name="Cozy Plushies",
            slug="plushies",
            description="Super soft, squishy animals and dolls hand-knitted for cozy companions."
        )
        cat_keychains = Category(
            name="Cute Keychains",
            slug="keychains",
            description="Miniature crochet accessories to carry warmth wherever you go."
        )
        db.add(cat_bouquets)
        db.add(cat_plushies)
        db.add(cat_keychains)
        await db.flush()
        logger.info("Categories seeded successfully.")
    else:
        for cat in categories:
            if cat.slug == "bouquets":
                cat_bouquets = cat
            elif cat.slug == "plushies":
                cat_plushies = cat
            elif cat.slug == "keychains":
                cat_keychains = cat

    # 3. Seed Products
    product_result = await db.execute(select(Product))
    products = product_result.scalars().all()
    if not products:
        logger.info("No products found. Seeding initial catalog...")
        
        p1 = Product(
            title="Everlasting Pink Tulip Bouquet",
            slug="pink-tulip-bouquet",
            description="A gorgeous handmade bouquet featuring three stems of crochet pink tulips. Handcrafted with precision using high-grade milk cotton yarn, wrapped in warm paper, and tied with a silk ribbon. A thoughtful gift that never withers.",
            price=599.00,
            compare_at_price=799.00,
            category_id=cat_bouquets.id if cat_bouquets else None,
            images=["/images/category_bouquets.jpg"],
            tags=["flower", "bouquet", "gift", "romantic"],
            colors=["Pink", "Cream White", "Dusty Rose"],
            stock=15,
            is_active=True,
            is_featured=True
        )
        
        p2 = Product(
            title="Chubby Crochet Octopus Plushie",
            slug="octopus-plushie",
            description="Brighten up your day with this super squishy, hand-knitted octopus companion. Made using hypoallergenic milk cotton yarn and filled with premium grade polyester fiberfill. Ideal for kids, desks, or as a pocket buddy.",
            price=349.00,
            compare_at_price=449.00,
            category_id=cat_plushies.id if cat_plushies else None,
            images=["/images/category_plushies.jpg"],
            tags=["plushie", "animal", "octopus", "cute"],
            colors=["Lilac", "Mint", "Peach"],
            stock=8,
            is_active=True,
            is_featured=True
        )
        
        p3 = Product(
            title="Artisanal Sunflower Crochet Stem",
            slug="sunflower-stem",
            description="A vibrant single stem crochet sunflower. Hand-stitched with love and perfect for adding a bright touch to your office desk, shelf, or study room.",
            price=249.00,
            compare_at_price=299.00,
            category_id=cat_bouquets.id if cat_bouquets else None,
            images=["/images/insta_2.jpg"],
            tags=["sunflower", "stem", "accessory"],
            colors=["Yellow", "Brown"],
            stock=15,
            is_active=True,
            is_featured=False
        )
        
        p4 = Product(
            title="Mini Avocado Heart Keychain",
            slug="avocado-keychain",
            description="Add some cuteness to your bags or keys with this handmade avocado couple keychain. Crochet with soft cotton yarn, complete with a tiny heart detail.",
            price=189.00,
            compare_at_price=249.00,
            category_id=cat_keychains.id if cat_keychains else None,
            images=["/images/category_keychains.jpg"],
            tags=["keychain", "accessory", "avocado", "couple"],
            colors=["Green"],
            stock=25,
            is_active=True,
            is_featured=False
        )
        
        db.add(p1)
        db.add(p2)
        db.add(p3)
        db.add(p4)
        await db.flush()

        # Seed Variants for tulip bouquet
        db.add(ProductVariant(product_id=p1.id, sku="TULIP-3STEM", name="Stems", value="3 Tulips", price=599.00, price_delta=0.00, stock=10))
        db.add(ProductVariant(product_id=p1.id, sku="TULIP-5STEM", name="Stems", value="5 Tulips (Large)", price=799.00, price_delta=200.00, stock=5))

        logger.info("Products and variants seeded successfully.")

    # 4. Seed Default Database-backed Coupons
    coupon_result = await db.execute(select(Coupon))
    coupons = coupon_result.scalars().all()
    if not coupons:
        logger.info("Seeding database coupons...")
        c1 = Coupon(
            code="WELCOME10",
            type=CouponType.percentage,
            value=Decimal("10.00"),
            minimum_order_value=Decimal("299.00"),
            maximum_discount=Decimal("200.00"),
            per_customer_limit=1,
            is_active=True,
        )
        c2 = Coupon(
            code="KEE15",
            type=CouponType.percentage,
            value=Decimal("15.00"),
            minimum_order_value=Decimal("499.00"),
            maximum_discount=Decimal("300.00"),
            per_customer_limit=1,
            is_active=True,
        )
        c3 = Coupon(
            code="FREESHIP",
            type=CouponType.free_shipping,
            value=Decimal("60.00"),
            minimum_order_value=Decimal("399.00"),
            per_customer_limit=2,
            is_active=True,
        )
        db.add(c1)
        db.add(c2)
        db.add(c3)
        logger.info("Coupons seeded successfully.")

    # 5. Seed Default Configurable Store Policies
    policy_result = await db.execute(select(StorePolicy))
    policies = policy_result.scalars().all()
    if not policies:
        logger.info("Seeding default store policies...")
        default_policies = [
            StorePolicy(key="shipping", title="Shipping & Delivery", content="Orders are shipped across all pin codes in India via premium courier partners. Standard shipping fee is ₹60 for orders under ₹999, and FREE for orders of ₹999 or more. Expected transit time is 3–5 business days."),
            StorePolicy(key="returns", title="Returns Policy", content="Due to the handcrafted nature of our crochet products, items can be exchanged or returned within 7 days of delivery only if received damaged or defective. Photos must be provided."),
            StorePolicy(key="refunds", title="Refund Policy", content="Approved refunds are processed to the original payment method within 5–7 business days via our payment gateway."),
            StorePolicy(key="custom_orders", title="Custom & Bespoke Orders", content="We accept custom requests for bouquets, personalized plushies, and custom color combinations. Processing time for custom orders is typically 4–7 business days before shipping."),
            StorePolicy(key="processing_times", title="Processing Times", content="In-stock handmade items ship within 24–48 hours. Custom designs take 4–7 working days."),
            StorePolicy(key="gift_wrapping", title="Gift Wrapping & Personalization", content="Premium craft gift wrapping with dried lavender and a personalized handwritten gift note is available for ₹50 per item."),
            StorePolicy(key="contact", title="Contact Information", content="Email: support@keecrochet.com | Instagram: @kee.crochet | Business hours: Mon–Sat 9:00 AM – 7:00 PM IST.")
        ]
        for pol in default_policies:
            db.add(pol)
        logger.info("Store policies seeded successfully.")

    # 6. Seed Default Store Settings
    from app.models.user import StoreSetting
    setting_result = await db.execute(select(StoreSetting))
    settings_records = setting_result.scalars().all()
    if not settings_records:
        logger.info("Seeding default store settings...")
        default_settings = [
            StoreSetting(
                key="shipping",
                value={
                    "standard_fee": 79.0,
                    "free_threshold": 999.0,
                    "gift_wrap_unit_fee": 50.0,
                    "processing_days": "1-2 business days",
                    "delivery_estimate": "3-5 business days",
                    "supported_countries": ["IN"],
                },
                description="General shipping fee rules and delivery timelines",
            ),
            StoreSetting(
                key="general",
                value={
                    "store_name": "Kee Crochet Shop",
                    "support_email": "support@keecrochet.com",
                    "instagram_handle": "@kee.crochet",
                    "currency": "INR",
                    "currency_symbol": "₹",
                },
                description="Core store branding and support channels",
            )
        ]
        for st in default_settings:
            db.add(st)
        logger.info("Store settings seeded successfully.")

    await db.commit()
    logger.info("Seeding process completed successfully.")
