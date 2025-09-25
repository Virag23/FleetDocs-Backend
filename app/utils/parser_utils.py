import re
from datetime import datetime, date

def find_truck_number(text: str) -> str | None:
    """Finds a vehicle registration number (e.g., MH20EE1234) in a block of text."""
    match = re.search(r'\b([A-Z]{2}[- ]?\d{2}[- ]?[A-Z]{1,2}[- ]?\d{4})\b', text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "").replace("-", "").upper()
    return None

def parse_date(text: str) -> date | None:
    """Finds and parses various date formats (dd/mm/yyyy, dd-mm-yyyy, dd-Mon-yyyy)."""
    match = re.search(r'\b(\d{2})[-/](\d{2})[-/](\d{4})\b', text)
    if match:
        try:
            return datetime.strptime(match.group(0), '%d-%m-%Y').date()
        except ValueError:
            try:
                return datetime.strptime(match.group(0), '%d/%m/%Y').date()
            except ValueError:
                return None
    match = re.search(r'\b(\d{2})-([A-Za-z]{3})-(\d{4})\b', text)
    if match:
        try:
            return datetime.strptime(match.group(0), '%d-%b-%Y').date()
        except ValueError:
            return None
            
    return None

def parse_period(text: str) -> tuple[date | None, date | None]:
    """Parses a 'From X to Y' or 'X to Y' date range."""
    matches = re.findall(r'\b(\d{2}[-/][A-Za-z]{3}[-/]\d{4}|\d{2}[-/]\d{2}[-/]\d{4})\b', text, re.IGNORECASE)
    if len(matches) >= 2:
        start_date = parse_date(matches[0])
        end_date = parse_date(matches[1])
        return start_date, end_date
    return None, None

def parse_license_details(text: str):
    """
    Parses Indian Driving License text to extract key details.
    """
    data = {}
    lines = text.splitlines()
    dl_number_match = re.search(r'\b([A-Z]{2}\d{13,14})\b', text)
    if dl_number_match:
        data['license_number'] = dl_number_match.group(1)

    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        if 'name' in line_lower and 'father' not in line_lower:
            name_str = line.split(':')[-1].strip() if ':' in line else (lines[i+1].strip() if i+1 < len(lines) else None)
            if name_str:
                if ',' in name_str:
                    parts = [p.strip() for p in name_str.split(',')]
                    data['name_on_license'] = f"{parts[1]} {parts[0]}" if len(parts) > 1 else name_str
                else:
                    data['name_on_license'] = name_str

        if 'issue date' in line_lower or 'doi' in line_lower:
            dt = parse_date(line)
            if dt: data['issue_date'] = dt

        if 'validity' in line_lower and 'nt' in line_lower:
            dt = parse_date(line)
            if dt: data['validity_nt'] = dt
        
        if 'validity' in line_lower and 'tr' in line_lower:
            dt = parse_date(line)
            if dt: data['validity_tr'] = dt
            
    return data

def parse_rc_details(text: str):
    """Parses Registration Certificate text."""
    data = {'truck_number': find_truck_number(text)}
    for line in text.splitlines():
        if re.search(r'Date of Regn', line, re.IGNORECASE):
            data['issue_date'] = parse_date(line)
    return data

def parse_puc_details(text: str):
    """Parses PUC text."""
    data = {'truck_number': find_truck_number(text)}
    for line in text.splitlines():
        if re.search(r'Certificate SL\. No', line, re.IGNORECASE):
            data['number'] = line.split(':')[-1].strip()
        if 'issue_date' not in data and parse_date(line):
             data['issue_date'] = parse_date(line)
        if re.search(r'Validity Upto', line, re.IGNORECASE):
            data['expiry_date'] = parse_date(line)
    return data

def parse_tax_details(text: str):
    """Parses Tax Receipt text."""
    data = {'truck_number': find_truck_number(text)}
    for line in text.splitlines():
        if re.search(r'Application Number|Receipt No', line, re.IGNORECASE):
            data['number'] = line.split(':')[-1].strip()
        if re.search(r'Period', line, re.IGNORECASE):
            issue_date, expiry_date = parse_period(line)
            if issue_date and expiry_date:
                data['issue_date'] = issue_date
                data['expiry_date'] = expiry_date
    return data

def parse_insurance_details(text: str):
    """Parses Insurance document text."""
    data = {'truck_number': find_truck_number(text)}
    for line in text.splitlines():
        if re.search(r'Policy Number', line, re.IGNORECASE):
            data['number'] = line.split(':')[-1].strip()
        if re.search(r'Policy Start Date', line, re.IGNORECASE):
            data['issue_date'] = parse_date(line)
        if re.search(r'Policy End Date', line, re.IGNORECASE):
            data['expiry_date'] = parse_date(line)
    return data

def parse_permit_details(text: str):
    """Parses National or State Permit text."""
    data = {'truck_number': find_truck_number(text)}
    for line in text.splitlines():
        if re.search(r'Permit No', line, re.IGNORECASE):
            data['number'] = line.split(':')[-1].strip()
        if re.search(r'Validity of Permit', line, re.IGNORECASE):
            issue_date, expiry_date = parse_period(line)
            if issue_date and expiry_date:
                data['issue_date'] = issue_date
                data['expiry_date'] = expiry_date
    return data

def parse_fitness_details(text: str):
    """Parses Fitness Certificate text."""
    data = {'truck_number': find_truck_number(text)}
    for line in text.splitlines():
        if re.search(r'Inspection/Issuance Fee Receipt No', line, re.IGNORECASE):
            data['number'] = line.split(':')[-1].strip()
        if re.search(r'Application No', line, re.IGNORECASE):
            data['application_no'] = line.split(':')[-1].strip()
        if re.search(r'Inspected/Issued Date', line, re.IGNORECASE):
            data['issue_date'] = parse_date(line)
        if re.search(r'Certificate will expire on', line, re.IGNORECASE):
            data['main_expiry_date'] = parse_date(line)
        if re.search(r'Next Inspection due date', line, re.IGNORECASE):
            data['next_inspection_due_date'] = parse_date(line)
    return data

def get_parser_for_doc_type(doc_type: str):
    """Returns the correct parsing function for a given document type."""
    parsers = {
        "rc": parse_rc_details,
        "puc": parse_puc_details,
        "tax": parse_tax_details,
        "insurance": parse_insurance_details,
        "national_permit": parse_permit_details,
        "state_permit": parse_permit_details,
        "fitness": parse_fitness_details,
        "license": parse_license_details,
    }
    return parsers.get(doc_type)

