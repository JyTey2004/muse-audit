"""Read XLSX cells, independently evaluate one-column SUM, exact source mapping.

No Excel engine, cached result trust, currency conversion or semantic inference.
Repair changes selected integer cell XML only and clears formula caches.
"""
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree as ET
from openpyxl import load_workbook
from ..io import read_json

KINDS = {'xlsx.source_amount', 'xlsx.sum', 'xlsx.cap', 'xlsx.preserve_cell'}
VERSION = 'xlsx-budget-0.1'
CELL = re.compile(r'[A-Z]{1,3}[1-9][0-9]{0,5}\Z')
SUM = re.compile(r'=SUM\(([A-Z]{1,3})([1-9][0-9]{0,5}):\1([1-9][0-9]{0,5})\)\Z')
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def _integer(value):
    if type(value) is not int or abs(value) > 10**12:
        raise ValueError('Only integer cents up to 10^12 are supported; no booleans/floats')
    return value


def _cell(sheet, ref):
    if not isinstance(ref, str) or not CELL.fullmatch(ref):
        raise ValueError('Unsupported cell address')
    return sheet[ref].value


def _sum(sheet, ref):
    formula = _cell(sheet, ref)
    match = SUM.fullmatch(formula) if isinstance(formula, str) else None
    if not match:
        raise ValueError('Only exact =SUM(A1:A9)-style single-column formulas are evaluated')
    col, start, stop = match.groups()
    start, stop = int(start), int(stop)
    if stop < start or stop - start > 500:
        raise ValueError('SUM range must contain 1 through 501 rows')
    cells = [f'{col}{row}' for row in range(start, stop + 1)]
    return sum(_integer(_cell(sheet, cell)) for cell in cells), cells, formula


def _source(root, job, config):
    source = next((s for s in job['sources'] if s['id'] == config['source_id']), None)
    if source is None:
        raise ValueError('Selected source ID is absent')
    data = read_json(root / source['path'])
    if not isinstance(data, dict) or not isinstance(data.get('amounts'), dict):
        raise ValueError('Source must be an object containing an amounts object')
    currency = config.get('currency')
    if not isinstance(currency, str) or re.fullmatch(r'[A-Z]{3}', currency) is None:
        raise ValueError('Mapping requires an explicit three-letter uppercase currency')
    if data.get('currency') != currency:
        raise ValueError('Currency is missing or differs; no conversion is supported')
    return _integer(data['amounts'][config['source_key']]), source['path']


def _unsupported(workbook):
    reasons = []
    if workbook._external_links:
        reasons.append('external links')
    if len(workbook.worksheets) != 1:
        reasons.append('multiple worksheets')
    for sheet in workbook.worksheets:
        if sheet.sheet_state != 'visible' or any(d.hidden for d in sheet.row_dimensions.values()) or any(d.hidden for d in sheet.column_dimensions.values()):
            reasons.append('hidden regions')
        if sheet.max_row > 1000 or sheet.max_column > 50:
            reasons.append('sheet exceeds 1000 rows / 50 columns')
        if sheet.tables or sheet._charts or sheet._images:
            reasons.append('tables/charts/images')
    return reasons


def evaluate(root: Path, job: dict) -> list[dict]:
    results = []
    path = root / job['artifact']['path']
    workbook = load_workbook(path, data_only=False, read_only=False, keep_links=True)
    unsupported = _unsupported(workbook)
    with zipfile.ZipFile(path) as package:
        if any(name.lower().endswith('vbaproject.bin') for name in package.namelist()):
            unsupported.append('macros')
    for req in job['requirements']:
        if req['kind'] not in KINDS:
            continue
        result = dict(requirement_id=req['id'], status='UNKNOWN', reason='', observed=None, expected=None, locations=[])
        try:
            c = req['config']
            fields = {'xlsx.source_amount': {'sheet','cell','source_id','source_key','currency'}, 'xlsx.sum': {'sheet','cell','required_cells'}, 'xlsx.cap': {'sheet','cell','max_cents'}, 'xlsx.preserve_cell': {'sheet','cell','expected'}}
            if set(c) != fields[req['kind']]:
                raise ValueError('Unsupported or missing mapping configuration fields')
            sheet = workbook[c['sheet']]
            result['locations'] = [f"{job['artifact']['path']}#{c['sheet']}!{c['cell']}"]
            if req['kind'] == 'xlsx.source_amount':
                actual = _integer(_cell(sheet, c['cell']))
                expected, source_path = _source(root, job, c)
                result['locations'].append(f"{source_path}#/amounts/{c['source_key']}")
                result.update(observed=actual, expected=expected, status='PASS' if actual == expected else 'FAIL', reason='Mapped cell compared with selected source amount; integer cents.')
            elif req['kind'] == 'xlsx.sum':
                actual, cells, formula = _sum(sheet, c['cell'])
                required = c['required_cells']
                if not isinstance(required, list) or not required or any(not isinstance(x, str) or not CELL.fullmatch(x) for x in required):
                    raise ValueError('required_cells must declare the approved complete input range')
                result.update(observed={'formula':formula,'evaluated_cents':actual,'included_cells':cells}, expected={'required_cells':required}, status='PASS' if set(cells) == set(required) else 'FAIL', reason='Exact independent SUM evaluation and declared required-cell inclusion; cached display ignored.')
            elif req['kind'] == 'xlsx.cap':
                actual, _, formula = _sum(sheet, c['cell'])
                cap = _integer(c['max_cents'])
                result.update(observed=actual, expected={'maximum_cents':cap}, status='PASS' if actual <= cap else 'FAIL', reason='Independently evaluated total compared with approved cap; cap is never auto-repaired.')
            else:
                actual, expected = _cell(sheet, c['cell']), c['expected']
                if type(actual) not in (str, int, type(None)) or isinstance(actual, bool):
                    raise ValueError('Observed protected cell is outside exact string/integer support')
                if type(expected) not in (str, int) or isinstance(expected, bool):
                    raise ValueError('Preservation supports exact string or integer only')
                result.update(observed=actual, expected=expected, status='PASS' if type(actual) is type(expected) and actual == expected else 'FAIL', reason='Exact protected cell value/formula comparison.')
        except (KeyError, ValueError, TypeError, IndexError) as exc:
            result.update(status='UNKNOWN', reason=str(exc))
        results.append(result)
    if unsupported:
        results.append(dict(requirement_id='__xlsx_coverage__',status='UNKNOWN',reason='Unsupported workbook structure: '+', '.join(unsupported), observed=unsupported,expected=None,locations=[job['artifact']['path']]))
    workbook.close()
    return results


def plan(root: Path, job: dict) -> list[dict]:
    outcomes = {r['requirement_id']:r for r in evaluate(root, job)}
    if '__xlsx_coverage__' in outcomes:
        return []
    operations = []
    for req in job['requirements']:
        result = outcomes.get(req['id'])
        if req['kind'] == 'xlsx.source_amount' and req['mode'] == 'must_change' and result and result['status'] == 'FAIL':
            c = req['config']
            operations.append(dict(kind='xlsx.replace_integer', sheet=c['sheet'], cell=c['cell'], before=result['observed'], after=result['expected'], requirement_id=req['id']))
    return operations


def apply(input_path: Path, output_path: Path, operations: list[dict]) -> None:
    """Narrow native-file patch: preserve ZIP parts; never execute formulas/macros."""
    workbook = load_workbook(input_path, data_only=False)
    if _unsupported(workbook):
        raise ValueError('Repair refuses unsupported workbook structures')
    if len(workbook.worksheets) != 1:
        raise ValueError('Repair requires exactly one worksheet')
    sheet = workbook.worksheets[0]
    seen = set()
    for op in operations:
        if op['kind'] != 'xlsx.replace_integer' or op['sheet'] != sheet.title or op['cell'] in seen:
            raise ValueError('Unsupported or duplicate repair operation')
        if _integer(_cell(sheet, op['cell'])) != _integer(op['before']):
            raise ValueError('Cell changed after repair was proposed')
        _integer(op['after'])
        seen.add(op['cell'])
    workbook.close()
    with zipfile.ZipFile(input_path) as src:
        # This narrow adapter supports the standard single-sheet package only.
        member = 'xl/worksheets/sheet1.xml'
        xml = ET.fromstring(src.read(member))
        for op in operations:
            node = xml.find(f".//s:c[@r='{op['cell']}']", NS)
            if node is None or node.find('s:f', NS) is not None:
                raise ValueError('Repair target must be an existing literal integer cell')
            value = node.find('s:v', NS)
            if value is None:
                raise ValueError('Repair target has no numeric value')
            node.set('t', 'n')
            value.text = str(op['after'])
        # Formula text remains intact. Drop all formula caches rather than retaining stale numbers.
        for cell in xml.findall('.//s:c', NS):
            if cell.find('s:f', NS) is not None:
                for value in cell.findall('s:v', NS):
                    cell.remove(value)
        with zipfile.ZipFile(output_path, 'x', zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                dst.writestr(info, ET.tostring(xml, encoding='utf-8', xml_declaration=True) if info.filename == member else src.read(info.filename))
