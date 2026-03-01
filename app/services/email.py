import resend
import structlog

from app.core.dependencies import settings
from app.models.purchase_request import PurchaseRequest
from app.schemas.stock_movement import StockLevelOut

resend.api_key = settings.RESEND_API


logger = structlog.get_logger()


def send_low_stock_alert(
    recipients: list[str],
    product_name: str,
    warehouse_name: str,
    current_stock: int,
    minimum_stock: int,
):

    params: resend.Emails.SendParams = {
        "from": "multitenant <onboarding@resend.dev>",
        "to": recipients,
        "subject": f"Low Stock Alert — {product_name}",
        "html": f"""
<h2>Low Stock Alert</h2>
<p>The following product has fallen below its minimum stock level:</p>
<table border="1" cellpadding="8" cellspacing="0">
    <tr><td><strong>Product</strong></td><td>{product_name}</td></tr>
    <tr><td><strong>Warehouse</strong></td><td>{warehouse_name}</td></tr>
    <tr><td><strong>Current Stock</strong></td><td>{current_stock} units</td></tr>
    <tr><td><strong>Minimum Level</strong></td><td>{minimum_stock} units</td></tr>
</table>
<p>Please review and restock as soon as possible.</p>
""",
    }
    try:
        logger.info("low stock alert sending")
        resend.Emails.send(params)
        logger.info(
            "Low stock alert sent", product=product_name, recipients=len(recipients)
        )
    except Exception as e:
        logger.error("Low stock alert failed", product=product_name, error=str(e))


def send_weekly_report(
    recipients: list[str],
    org_name: str,
    totals: dict[str, int],
    low_stock_products: list[StockLevelOut],
    pending_prs: list[PurchaseRequest],
):
    low_stock_rows = (
        "".join(
            f"<tr><td>{p.product_id}</td><td>{p.current_stock} units</td></tr>"
            for p in low_stock_products
        )
        or "<tr><td colspan='2'>No low stock products</td></tr>"
    )

    pending_rows = (
        "".join(
            f"<tr><td>{pr.request_number}</td><td>{pr.status}</td></tr>"
            for pr in pending_prs
        )
        or "<tr><td colspan='2'>No pending requests</td></tr>"
    )

    params: resend.Emails.SendParams = {
        "from": "multitenant <onboarding@resend.dev>",
        "to": recipients,
        "subject": f"Weekly Inventory Report — {org_name}",
        "html": f"""
<h2>Weekly Inventory Report — {org_name}</h2>

<h3>Stock Movements This Week</h3>
<table border="1" cellpadding="8" cellspacing="0">
    <tr><th>Type</th><th>Total Units</th></tr>
    <tr><td>IN</td><td>{totals.get("IN", 0)}</td></tr>
    <tr><td>OUT</td><td>{totals.get("OUT", 0)}</td></tr>
    <tr><td>TRANSFER IN</td><td>{totals.get("TRANSFER_IN", 0)}</td></tr>
    <tr><td>TRANSFER OUT</td><td>{totals.get("TRANSFER_OUT", 0)}</td></tr>
    <tr><td>ADJUSTMENT</td><td>{totals.get("ADJUSTMENT", 0)}</td></tr>
</table>

<h3>Products Below Minimum Stock</h3>
<table border="1" cellpadding="8" cellspacing="0">
    <tr><th>Product ID</th><th>Current Stock</th></tr>
    {low_stock_rows}
</table>

<h3>Pending Purchase Requests</h3>
<table border="1" cellpadding="8" cellspacing="0">
    <tr><th>Request Number</th><th>Status</th></tr>
    {pending_rows}
</table>
""",
    }
    try:
        logger.info("Weekly report sending", org=org_name)
        resend.Emails.send(params)
        logger.info("Weekly report sent", org=org_name, recipients=len(recipients))
    except Exception as e:
        logger.error("Weekly report failed", org=org_name, error=str(e))
