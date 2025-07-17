from .odoo_client import OdooClient
from logging import getLogger

logger = getLogger(__name__)

EMPLOYEE_FIELDS = [
    "id", "display_name", "mobile_phone", "work_email",
    "identification_id", "contract_id"
]

CONTRACT_FIELDS = [
    "date_start", "date_end", "state","wage"
]

def get_field_workers():
    cli = OdooClient()
    data = cli.get_model_records(
        model="hr.employee",
        fields=EMPLOYEE_FIELDS,
        field_worker=True
    )
    output = []
    for employee in data.get("content", []):
        output.append({
            "odoo_employee_id": employee["id"],
            "odoo_contract_id": employee["contract_id"][0] if employee["contract_id"] else None,
            "name": employee["display_name"],
            "mobile_phone": employee["mobile_phone"],
            "email": employee["work_email"],
            "identification_number": employee["identification_id"],
        })
    return output

def get_employee_contract(cid):
    if not cid:
        return {}

    cli = OdooClient()
    logger.info(f"Getting contract with id: {cid}(type: {type(cid)})")
    res = cli.get_model_records(
        model="hr.contract",
        fields=CONTRACT_FIELDS,
        id=cid
    )
    contract = res.get("content", [{}])[0]
    logger.info(f"Got contract: {contract}")

    # Handle fields safely
    start_date = contract.get("date_start", None)
    end_date = contract.get("date_end", None)

    if start_date is False:
        start_date = None
    if end_date is False:
        end_date = None

    # Debug the date values
    logger.info(f"Start date: {start_date}, End date: {end_date}")
    logger.info(f"Start date type: {type(start_date)}, End date type: {type(end_date)}")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "contract_status": contract["state"],
        "wage": contract["wage"],
    }