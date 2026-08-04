import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole, AuthProvider
from app.models.product import Category, Product, ProductVariant
from app.models.cart import Cart

logger = logging.getLogger(__name__)


async def seed_data(db: AsyncSession) -> None:
    """Auto-seed default categories, products, and admin/customer accounts if empty."""
    logger.info("Checking if database seeding is required...")

    # 1. Seed Users
    user_result = await db.execute(select(User))
    users = user_result.scalars().all()
    if not users:
        logger.info("No users found. Seeding default admin and customer accounts...")
        admin = User(
            email="admin@keecrochet.com",
            full_name="Kee Admin",
            hashed_password=hash_password("adminpassword123"),
            role=UserRole.admin,
            auth_provider=AuthProvider.email,
            is_active=True,
            is_verified=True,
        )
        customer = User(
            email="customer@keecrochet.com",
            full_name="Madhav Nair",
            hashed_password=hash_password("customerpassword123"),
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
        logger.info("Categories exist. Skipping category seeding.")
        # Fetch existing categories for products association
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
            stock=12,
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
        db.add(ProductVariant(product_id=p1.id, name="Stems", value="3 Tulips", price_delta=0.00, stock=10))
        db.add(ProductVariant(product_id=p1.id, name="Stems", value="5 Tulips (Large)", price_delta=200.00, stock=5))

        logger.info("Products and variants seeded successfully.")
    else:
        logger.info("Products exist. Skipping product seeding.")

    await db.commit()
    logger.info("Seeding process completed successfully.")
