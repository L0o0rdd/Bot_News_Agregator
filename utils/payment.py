import uuid
import aiohttp
from aiogram import Bot
from utils.logger import logger

# Замените на ваш реальный shopId из ЮKassa
YOOKASSA_SHOP_ID = "1062538"  # Пример тестового shopId, замените на ваш
YOOKASSA_SECRET_KEY = "test_PHmgyB5z-RvgKcf1jiX0s5uj8Cho1noprxl7SIGdDf0"


async def create_payment(user_id: int, amount: int, description: str, action_type: str, quantity: int) -> dict:
    idempotence_key = str(uuid.uuid4())
    url = "https://api.yookassa.ru/v3/payments"
    headers = {
        "Idempotence-Key": idempotence_key,
        "Content-Type": "application/json",
    }
    auth = aiohttp.BasicAuth(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    payment_data = {
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot_username"  # Замените на ссылку на ваш бот
        },
        "capture": True,
        "description": description,
        "metadata": {
            "user_id": str(user_id),
            "action_type": action_type,
            "quantity": str(quantity)
        }
    }

    logger.info(f"Creating payment for user {user_id}: {payment_data}")
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.post(url, json=payment_data, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Payment creation failed: {error_text}")
                return None
            result = await response.json()
            logger.info(f"Payment created: {result['id']}")
            return result


async def check_payment(payment_id: str) -> dict:
    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
    headers = {
        "Content-Type": "application/json",
    }
    auth = aiohttp.BasicAuth(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)

    logger.info(f"Checking payment {payment_id}")
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Payment check failed: {error_text}")
                return None
            result = await response.json()
            logger.info(f"Payment status: {result['status']}")
            return result