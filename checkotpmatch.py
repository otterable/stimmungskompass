import pyotp
totp = pyotp.TOTP('MangoOttersLove')
print("Current OTP:", totp.now())
