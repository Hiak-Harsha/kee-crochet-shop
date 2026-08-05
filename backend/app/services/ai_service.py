import io
import json
import logging
from typing import Any

from PIL import Image

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    GEMINI_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the Gemini API client if the API key is configured
if GEMINI_AVAILABLE and settings.GEMINI_API_KEY and genai:
    genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore
else:
    logger.warning("Gemini API key not found. AI features will run in mock demonstration mode.")


def _get_model(model_name: str = "gemini-1.5-flash") -> Any:
    if GEMINI_AVAILABLE and settings.GEMINI_API_KEY and genai:
        return genai.GenerativeModel(model_name)  # type: ignore
    return None


async def semantic_search(query: str, products_list: list[dict]) -> list[str]:
    """
    Search over the catalog of products semantically.
    Returns a list of matching product IDs (str).
    """
    model = _get_model()
    if not model:
        # Fallback Mock Mode: search keywords in query
        query_lower = query.lower()
        matches = []
        for p in products_list:
            title = p.get("title", "").lower()
            desc = p.get("description", "").lower()
            tags = [t.lower() for t in p.get("tags", [])]
            if query_lower in title or query_lower in desc or any(t in query_lower for t in tags):
                matches.append(str(p.get("id")))
        # If no keywords match, return first 3 as recommendation fallback
        return matches if matches else [str(p.get("id")) for p in products_list[:3]]

    prompt = f"""
    You are an AI search engine for a boutique crochet shop called 'Kee Crochet'.
    Given the user's search query: "{query}"
    
    Here is our product catalog in JSON format:
    {json.dumps(products_list, default=str)}
    
    Determine which products match the user's intent. The user might search for concepts (e.g. "cute gift for girlfriend under 500", "keychain to match my backpack", "soft plushie").
    Understand budget constraint (if mentioned, e.g. "under 500" means check price <= 500).
    
    Output ONLY a JSON list of matching product IDs, ordered by relevance. Do not include markdown code block formatting or any other text.
    Example output format:
    ["uuid-1", "uuid-2"]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean potential markdown wrapping
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        matching_ids = json.loads(text)
        return [str(mid) for mid in matching_ids if isinstance(mid, (str, int))]
    except Exception as e:
        logger.error(f"Error in Gemini semantic_search: {e}")
        # Fallback keyword match
        return [str(p.get("id")) for p in products_list[:2]]


async def chat_shopper(messages: list[dict], products_list: list[dict], customer_context: str = "") -> tuple[str, list[str]]:
    """
    Personal shopper chat engine. 
    Accepts full message history, product context, and optional customer context (profile/cart/orders).
    Returns: (assistant_reply_text, list_of_recommended_product_ids)
    """
    model = _get_model()
    
    # Format message history for prompt
    chat_history = ""
    for msg in messages:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        chat_history += f"{role}: {msg['content']}\n"

    # Catalog brief
    catalog_summary = json.dumps([
        {"id": str(p["id"]), "title": p["title"], "price": float(p["price"]), "tags": p["tags"], "colors": p.get("colors", [])}
        for p in products_list
    ], default=str)

    if not model:
        # Smart Dynamic Mock Shopper
        last_message = messages[-1]["content"].lower()
        
        # 1. Parse colors
        colors = ["orange", "pink", "blue", "green", "red", "yellow", "purple", "lavender", "white", "black", "cream", "beige"]
        matched_colors = [c for c in colors if c in last_message]
        
        # 2. Parse product types
        wants_bouquet = "bouquet" in last_message or "flower" in last_message or "rose" in last_message or "tulip" in last_message or "sunflower" in last_message
        wants_plush = "plush" in last_message or "plushie" in last_message or "doll" in last_message or "toy" in last_message
        wants_keychain = "keychain" in last_message or "accessory" in last_message or "bag charm" in last_message
        
        # 3. Parse recipient
        recipient = None
        for r in ["friend", "mom", "mother", "girlfriend", "sister", "wife", "boyfriend", "dad", "teacher"]:
            if r in last_message:
                recipient = r
                break

        # Let's dynamically recommend products matching colors or types
        recs = []
        for p in products_list:
            p_title_lower = p["title"].lower()
            p_colors = [c.lower() for c in p.get("colors", [])]
            p_tags = [t.lower() for t in p.get("tags", [])]
            
            score = 0
            if any(c in p_title_lower or c in p_colors or c in p_tags for c in matched_colors):
                score += 3
            if wants_bouquet and "bouquet" in p_title_lower:
                score += 2
            if wants_plush and "plush" in p_title_lower:
                score += 2
            if wants_keychain and "keychain" in p_title_lower:
                score += 2
                
            if score > 0:
                recs.append((score, str(p["id"]), p["title"]))
                
        # Sort recommendations by match score
        recs.sort(key=lambda x: x[0], reverse=True)
        recommended_ids = [r[1] for r in recs]
        recommended_titles = [r[2] for r in recs]
        
        # Fallback if no specific matches found
        if not recommended_ids:
            recommended_ids = [str(p["id"]) for p in products_list[:3]]
            recommended_titles = [p["title"] for p in products_list[:3]]
            
        # Build a warm, customized mock reply based on parsed variables
        if matched_colors or wants_bouquet or wants_plush or wants_keychain or recipient:
            reply_parts = []
            if recipient:
                reply_parts.append(f"That is so sweet! A handmade crochet item makes a wonderful gift for your {recipient}.")
            
            if matched_colors:
                color_str = " and ".join(matched_colors)
                reply_parts.append(f"Since they love {color_str}, I highly recommend picking a handcrafted piece matching those colors.")
            
            if wants_bouquet:
                reply_parts.append("Our everlasting crochet flower bouquets (especially tulips and sunflowers) are perfect for bringing warmth and smiles.")
            elif wants_plush:
                reply_parts.append("Our soft yarn plushies are super squishy and make the cutest desk or bedside companions.")
            elif wants_keychain:
                reply_parts.append("Our mini keychains are great bag charms and daily reminders of your thoughtful gift.")
                
            if recommended_titles:
                titles_str = ", ".join(recommended_titles[:2])
                reply_parts.append(f"I've selected some lovely choices for you, such as the {titles_str}.")
            else:
                reply_parts.append("Feel free to browse our main catalog for more inspiration!")
                
            reply = " ".join(reply_parts)
        else:
            reply = "I'd love to help you find the perfect crochet gift! We offer high-quality, handmade crochet keychains, plushies, and custom bouquets. Can you tell me a bit about who this is for and their favorite colors?"
            
        return reply, recommended_ids[:3]

    prompt = f"""
    You are 'Kee', a warm, helpful, and charming AI Personal Shopper for 'Kee Crochet', a premium handmade crochet store.
    You assist customers in finding the right products, customizing orders, and suggesting gifts.
    
    {customer_context}
    
    Here is our current store catalog:
    {catalog_summary}
    
    Here is the conversation history:
    {chat_history}
    
    Respond to the user with a friendly, helpful reply. Address them by name if provided in their profile above, and reference their cart/purchase history if relevant (e.g. 'Since you liked the lavender bouquet from your past order...').
    Also, identify up to 3 product IDs from the catalog that fit their current search or request.
    
    Your response must be in JSON format with exactly two keys: "reply" (string) and "recommended_product_ids" (list of strings).
    Do NOT use markdown code blocks. Output raw JSON.
    Example:
    {{"reply": "Here are some bouquets you might like...", "recommended_product_ids": ["uuid-1"]}}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        data = json.loads(text)
        return data.get("reply", ""), data.get("recommended_product_ids", [])
    except Exception as e:
        logger.error(f"Error in Gemini chat_shopper: {e}")
        return "I'm having a little trouble fetching the live catalog, but our handmade flower bouquets and animal plushies are fantastic choices. Let me know what you'd like!", [str(p["id"]) for p in products_list[:2]]


async def suggest_colors(image_bytes: bytes, products_list: list[dict]) -> dict:
    """
    Takes an uploaded image of a room/setting, extracts dominant color themes,
    and suggests matching crochet products/yarn colors.
    """
    model = _get_model()
    
    # Prepare image
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Failed to parse image bytes: {e}")
        return {
            "recommended_colors": ["Pastel Pink", "Mint Green", "Cream"],
            "reasoning": "Could not parse the uploaded image, but these warm pastel colors are our signature cozy crochet shades.",
            "matching_product_ids": [str(p["id"]) for p in products_list[:2]]
        }

    if not model:
        # Mock mode
        return {
            "recommended_colors": ["Warm Beige", "Forest Green", "Soft Yellow"],
            "reasoning": "Based on the warm tones and lighting of your setting, we suggest grounding earthy tones. A forest green bouquet or warm beige plushie would fit perfectly on your desk or shelf.",
            "matching_product_ids": [str(p["id"]) for p in products_list[:2]]
        }

    catalog_summary = json.dumps([
        {"id": str(p["id"]), "title": p["title"], "colors": p.get("colors", [])}
        for p in products_list
    ], default=str)

    prompt = f"""
    Analyze the uploaded photo of the user's room or desktop space.
    1. Identify the dominant color palette and design style (e.g. cozy, minimalist, dark academia, pastel aesthetic).
    2. Suggest 3-4 yarn/crochet colors that would complement or accent this space beautifully.
    3. Look through our product list and match any items that fit this theme: {catalog_summary}
    
    Format your response in JSON with these keys: "recommended_colors" (list of strings), "reasoning" (string explaining color choices based on the image), and "matching_product_ids" (list of matching product UUIDs).
    Do NOT use markdown code blocks. Output raw JSON.
    """
    try:
        # Multimodal call
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error in Gemini suggest_colors: {e}")
        return {
            "recommended_colors": ["Pastel Pink", "Cream White"],
            "reasoning": "We recommend cozy neutral tones to blend with your current room setup.",
            "matching_product_ids": [str(p["id"]) for p in products_list[:1]]
        }


async def describe_product(image_bytes: bytes) -> dict:
    """
    Owner uploads a photo of a new crochet item.
    Gemini generates the Title, Description, Tags, and an Instagram Caption.
    """
    model = _get_model()
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Failed to parse product image: {e}")
        return {
            "title": "Handmade Crochet Mascot",
            "description": "A beautifully hand-stitched crochet creation made with super soft premium yarn. Perfect as a gift or desk companion.",
            "tags": ["crochet", "handmade", "plushie", "gift"],
            "instagram_caption": "Handmade with love! 🧶✨ Add this cute companion to your desk today. DM for custom colors!"
        }

    if not model:
        # Mock mode
        return {
            "title": "Cute Crochet Sunflower Bouquet",
            "description": "Brighten up someone's day with this hand-knitted sunflower bouquet. Crafted using premium, non-allergenic milk cotton yarn, it features detailed stitching and vibrant colors that never fade.",
            "tags": ["sunflower", "crochet bouquet", "flower gift", "handmade gift", "kee crochet"],
            "instagram_caption": "No watering needed! 🌻💛 Our handmade crochet sunflowers are here to keep your room bright forever. Crafted with high-quality soft yarn. Shop yours now! ✨ #crochetflower #sunflower #handmadebouquet #giftideas"
        }

    prompt = """
    Analyze the uploaded photo of a handmade crochet product.
    Generate a professional e-commerce product detail schema:
    1. "title": A catchy, search-friendly title (e.g. "Cute Crochet Pink Tulip Bouquet")
    2. "description": A warm, descriptive description highlighting craftsmanship, materials (like premium milk cotton yarn), and gift suitability.
    3. "tags": 4-6 search tags/keywords.
    4. "instagram_caption": An engaging Instagram caption complete with emojis, calls to action (e.g., "link in bio to shop"), and popular crochet hashtags.
    
    Format your response in JSON with these keys: "title", "description", "tags" (list of strings), and "instagram_caption".
    Do NOT use markdown code blocks. Output raw JSON.
    """
    try:
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error in Gemini describe_product: {e}")
        return {
            "title": "Handmade Crochet Tulip",
            "description": "Lovely hand-stitched crochet flower tulip. Crafted with premium milk cotton yarn.",
            "tags": ["tulip", "crochet", "handmade"],
            "instagram_caption": "Spring is always in bloom! 🌷✨ Click the link in bio to shop these cute handmade tulips! #crochettulip #handmadegifts"
        }


async def generate_instagram_caption(product_title: str, product_desc: str, style: str) -> dict:
    """
    Generate tailored Instagram captions based on product and style.
    Styles: romantic, festive, trendy, funny.
    """
    model = _get_model()
    if not model:
        # Mock mode
        hashtags = ["#keecrochet", "#handmade", "#crochetplushie", "#giftideas"]
        if style == "romantic":
            return {
                "caption": f"Gift your special someone something as unique as your love. 💖 This handmade '{product_title}' is stitched with care, warmth, and detail. DM us or visit our link in bio to order custom color combinations! ✨",
                "hashtags": hashtags + ["#romanticgift", "#crochetlove"]
            }
        elif style == "festive":
            return {
                "caption": f"Festivals are all about spreading joy! 🌸 Celebrate with our artisanal '{product_title}' - the perfect traditional gift with a cozy handmade twist. Get yours before the holiday rush! 🌟",
                "hashtags": hashtags + ["#festivevibes", "#handmadegifting"]
            }
        else:
            return {
                "caption": f"Meet your new cozy companion: the handmade '{product_title}'! 🧶✨ Super soft, extremely cute, and ready to brighten your workspace. Order yours today! 🛍️",
                "hashtags": hashtags + ["#crochetersofinstagram", "#aesthetic"]
            }

    prompt = f"""
    Create a highly engaging, custom Instagram caption for a crochet product.
    Product Title: {product_title}
    Product Description: {product_desc}
    Tone/Style: {style} (can be 'romantic', 'festive', 'trendy', or 'funny')
    
    Include:
    - Catchy opening line.
    - Call to action (e.g. check the website, click link in bio).
    - Aesthetic emojis.
    - A list of 6-8 relevant hashtags.
    
    Format your response in JSON with these keys: "caption" (string) and "hashtags" (list of strings).
    Do NOT use markdown code blocks. Output raw JSON.
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error in Gemini generate_instagram_caption: {e}")
        return {
            "caption": f"Cozy and handcrafted! Get our '{product_title}' today! ✨🧶",
            "hashtags": ["#crochet", "#kee_crochet", "#handmadegifts"]
        }


async def summarize_reviews(reviews: list[str]) -> dict:
    """
    Summarize product reviews. Returns pros, cons, overall summary, and sentiment.
    """
    model = _get_model()
    if not model or not reviews:
        return {
            "summary": "Customers overall express high satisfaction, frequently highlighting the soft texture, careful packaging, and high-quality craftsmanship of the crochet work.",
            "pros": ["Extremely soft and squishy yarn", "Aesthetic and careful gift wrapping", "Looks exactly like the product photos"],
            "cons": ["Custom orders take 4-7 days to ship", "Limited stock on popular variants"],
            "sentiment": "Very Positive"
        }

    prompt = f"""
    Analyze these customer reviews for a crochet product:
    {json.dumps(reviews)}
    
    Summarize the general feedback:
    1. Write a 2-sentence general summary of the feedback.
    2. Extract a list of "pros" (strengths liked by customers).
    3. Extract a list of "cons" or complaints.
    4. Determine the overall sentiment (Positive, Neutral, or Negative).
    
    Format your response in JSON with these keys: "summary" (string), "pros" (list of strings), "cons" (list of strings), and "sentiment" (string).
    Do NOT use markdown code blocks. Output raw JSON.
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error in Gemini summarize_reviews: {e}")
        return {
            "summary": "Highly positive reviews stressing the soft quality of materials.",
            "pros": ["Soft texture", "Cute design"],
            "cons": ["Slight shipping delays during festivals"],
            "sentiment": "Positive"
        }


async def faq_bot(question: str) -> str:
    """
    Answers user questions dynamically based on Kee Crochet's business policies.
    """
    model = _get_model()
    
    knowledge_base = """
    Kee Crochet Store Policies:
    - Products: All items are 100% handmade using premium cotton/acrylic blend yarns. They are hypoallergenic, washable (handwash recommended, lay flat to dry).
    - Delivery time: Ready-to-ship products are dispatched in 1-2 days. Custom orders (e.g. customized color bouquets, personalized plushies) take 4-7 days to handcraft before shipping.
    - Shipping charges: Flat rate of ₹60. Free shipping on orders above ₹999.
    - Shipping locations: We ship all across India.
    - Urgent Delivery: For urgent orders, customers can contact us to coordinate express delivery (extra charges apply depending on location).
    - Return/Refund: Since all products are handmade, we do not accept returns. However, if a product is damaged during transit, we offer refunds or replacements upon showing an unboxing video.
    - Custom Requests: Customers can specify custom colors, sizes, or notes in the checkout notes or submit requests through their dashboard.
    """

    if not model:
        q_lower = question.lower()
        if "deliver" in q_lower or "ship" in q_lower or "days" in q_lower:
            return "Standard ready-made items ship in 1-2 days. Custom orders take 4-7 days to handcraft before they ship out. Shipping is ₹60 or free above ₹999!"
        elif "custom" in q_lower or "color" in q_lower:
            return "Yes, we love custom orders! You can add customization notes when adding items to your cart, or upload room aesthetics for color recommendations."
        elif "wash" in q_lower or "clean" in q_lower:
            return "We recommend gently hand washing your crochet products with mild detergent, and laying them flat on a towel to dry so they keep their shape."
        else:
            return "Thanks for asking! All our items are 100% handmade with premium soft yarn. We ship India-wide. Let me know if you need help choosing a gift!"

    prompt = f"""
    You are 'Kee', the friendly AI FAQ chatbot for 'Kee Crochet'. Answer the customer's question politely and accurately based on our shop policies.
    
    Shop Policies:
    {knowledge_base}
    
    Customer Question: "{question}"
    
    Reply in a warm, helpful, and concise manner.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error in Gemini faq_bot: {e}")
        return "All our products are 100% handmade using high quality yarn. Shipping is ₹60 (free over ₹999). Ready items ship in 2 days; custom requests take 4-7 days!"
