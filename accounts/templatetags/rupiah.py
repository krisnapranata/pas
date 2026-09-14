from django import template

register = template.Library()


def format_rupiah(value):
    """Format angka menjadi Rupiah dengan pemisah ribuan titik (contoh: 1.500.000)."""
    if value is None:
        return "0"
    try:
        amount = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:,}".replace(",", ".")


@register.filter
def rupiah(value):
    return format_rupiah(value)
