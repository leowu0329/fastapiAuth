# 企業實務上可對接 SendGrid 或 aiosmtplib，此處印出連結模擬寄信
class EmailService:
    @staticmethod
    async def send_verification_email(email: str, token: str):
        verify_link = f"http://localhost:8080/api/auth/verify?token={token}"
        print(f"\n[模擬寄信 - 信箱驗證] 發送至 {email} -> 請點擊以下連結驗證：\n{verify_link}\n")

    @staticmethod
    async def send_reset_password_email(email: str, token: str):
        reset_link = f"http://localhost:8080/reset-password?token={token}"
        print(f"\n[模擬寄信 - 忘記密碼] 發送至 {email} -> 請點擊以下連結重設密碼：\n{reset_link}\n")
