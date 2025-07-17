from .odoo_client import OdooClient

EMPLOYEE_FIELDS = [
    "id", "display_name", "mobile_phone", "work_email",
    "identification_id", "contract_id"
]

CONTRACT_FIELDS = [
    "start_date", "end_date", "state","wage"
]

def get_field_workers():
    cli = OdooClient()
    data = cli.get_model_records(
        model="hr.employee",
        fields=EMPLOYEE_FIELDS,
        domain=[["field_worker", "=", True]],
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
    res = cli.get_model_records(
        model="hr.contract",
        fields=CONTRACT_FIELDS,
        domain=[["id", "=", cid]],
    )
    contract = res.get("content", [{}])[0]
    return {
        "start_date": contract["start_date"],
        "end_date": contract["end_date"],
        "contract_status": contract["state"],
        "wage": contract["wage"],
    }