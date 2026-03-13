import re


def mask_cpf(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11:
        return "***.***.***-**"
    return f"***.{digits[3:6]}.***-**"


def mask_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 14:
        return "**.***.***/****-**"
    return f"**.{digits[2:5]}.{digits[5:8]}/***-**"


def mask_email(value: str) -> str:
    try:
        user, domain = value.split("@")
        visible = user[:2] if len(user) >= 2 else user[0]
        return f"{visible}***@{domain}"
    except Exception:
        return "***@***"


def mask_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11:
        return f"({digits[0:2]}) {digits[2]}****-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[0:2]}) ****-{digits[6:]}"
    return "(***) *****-****"


def mask_token(value: str) -> str:
    if not value:
        return "****"
    return f"{value[:6]}...****"


def mask_document(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11:
        return mask_cpf(digits)
    if len(digits) == 14:
        return mask_cnpj(digits)
    return "***"
