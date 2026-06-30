import asyncio
import os

os.environ["RESEND_API_KEY"] = "re_VQGBbg26_MjTek5dTDfDxRCxD18u88eN3"
from backend.services.resend_service import send_delivery_email

async def main():
    res = await send_delivery_email("growix299@gmail.com", "Test", "123")
    print("Result:", res)

asyncio.run(main())
