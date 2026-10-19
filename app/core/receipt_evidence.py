import re


def is_receipt_instruction(text: str) -> bool:
    compact = re.sub(r"\s+", "", text).lower()
    return bool(re.search(
        r"(?:구매|구입)(?:점포|매장|처).*?(?:\d+일|이내|가능|교환|환불)"
        r"|(?:교환|환불).*?(?:이내|불가|가능)"
        r"|(?:미개봉|미사용).*?한함", compact,
    )) or any(phrase in compact for phrase in (
        "교환/환불은", "결제카드필요", "결제시", "결제할때", "발행불가",
        "시행령", "세법", "받으세요", "지참", "바랍니다", "고객센터", "광고",
    ))
