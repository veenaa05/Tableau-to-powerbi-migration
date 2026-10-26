# parse_twb_structure.py
import os
import re
import glob
import uuid
import shutil
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, Any, List, Tuple
from tableauhyperapi import HyperProcess, Telemetry, Connection, TableDefinition, TableName

# -----------------------
# Helpers
# -----------------------
def generate_guid() -> str:
    return str(uuid.uuid4())

def sanitize_name(name: str) -> str:
    if not name:
        return ""
    n = re.sub(r'^\[|\]$', '', name.strip())
    n = re.sub(r'["\']', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def clean_column_display_name(name: str) -> str:
    return sanitize_name(name)

def map_tableau_type_to_pb_type(tableau_type: str) -> str:
    t = (tableau_type or "").lower()
    if t in ("integer", "int", "int16", "int32", "int64"):
        return "Int64"
    if t in ("real", "double", "float", "number", "numeric"):
        return "Double"
    if t in ("boolean", "bool"):
        return "Boolean"
    if t in ("date", "datetime", "timestamp"):
        return "DateTime"
    return "String"

def default_summarize_by(pb_type: str) -> str:
    return "sum" if pb_type in ("Int64", "Double") else "none"

def build_m_expression(server: str, database: str, schema: str, item: str) -> str:
    schema = schema or "dbo"
    safe_item = sanitize_name(item)
    return (
        f'let '
        f'Source = Sql.Database("{server}", "{database}"), '
        f'#{schema}_{safe_item} = Source{{[Schema="{schema}",Item="{item}"]}}[Data] '
        f'in #{schema}_{safe_item}'
    )

# -----------------------
# Hyper file parsing logic
# -----------------------
def get_columns_from_hyper_file(hyper_file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(hyper_file_path):
        print(f"Warning: .hyper file not found at {hyper_file_path}")
        return {}
    table_schemas = defaultdict(list)
    try:
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_AND_MACHINE_ID) as hyper:
            with Connection(hyper.endpoint, hyper_file_path) as connection:
                for db_name in connection.catalog.get_databases():
                    for schema_name in connection.catalog.get_schemas(db_name):
                        for table_name_obj in connection.catalog.get_table_names(TableName(db_name, schema_name)):
                            table_def: TableDefinition = connection.catalog.get_table_definition(table_name_obj)
                            table_name = f"{table_name_obj.schema_name}.{table_name_obj.name}"
                            for col in table_def.columns:
                                table_schemas[table_name].append({
                                    "name": col.name,
                                    "remote_name": col.name,
                                    "data_type": map_tableau_type_to_pb_type(str(col.type))
                                })
    except Exception as e:
        print(f"Error reading Hyper file {hyper_file_path}: {e}")
        return {}
    return dict(table_schemas)

def export_hyper_to_csv(hyper_file_path: str, output_csv_path: str) -> bool:
    if not os.path.exists(hyper_file_path):
        print(f"Hyper file not found at {hyper_file_path}. Skipping export.")
        return False
    try:
        with HyperProcess(telemetry=Telemetry.NONE) as hyper:
            with Connection(endpoint=hyper.endpoint, database=hyper_file_path) as connection:
                for db_name in connection.catalog.get_databases():
                    for schema_name in connection.catalog.get_schemas(db_name):
                        for table_name_obj in connection.catalog.get_table_names(TableName(db_name, schema_name)):
                            print(f"Exporting data from table '{table_name_obj}' to CSV at {output_csv_path}...")
                            connection.catalog.export_csv(table_name_obj, output_csv_path)
                            print("Export successful.")
                            return True
    except Exception as e:
        print(f"Error exporting Hyper file '{hyper_file_path}' to CSV: {e}")
        return False
    return False

# -----------------------
# Remaining parsing functions (as provided by you)
# -----------------------
def build_meta_map(root: ET.Element) -> Dict[str, Dict[str, str]]:
    meta: Dict[str, Dict[str, str]] = {}
    for m in root.findall(".//metadata-record[@class='column']"):
        local = (m.findtext("local-name") or "").strip("[]")
        parent = (m.findtext("parent-name") or "").strip("[]")
        agg = m.findtext("aggregation") or "None"
        datatype = m.findtext('local-type') or ""
        if local:
            meta[local] = {"table": parent, "aggregation": agg, "datatype": datatype}
    return meta

def unpack_ref(ref: str) -> Tuple[str, str]:
    if not ref:
        return ("", "")
    tokens = re.findall(r'\[([^\]]+)\]', ref)
    if len(tokens) >= 2:
        return tokens[0], tokens[1]
    if len(tokens) == 1:
        return tokens[0], tokens[0]
    if "." in ref:
        parts = [p.strip(" []'\"") for p in ref.split(".") if p.strip()]
        if len(parts) >= 2:
            return parts[0], parts[-1]
        return parts[0], parts[0]
    return (ref.strip("[]'\" "), ref.strip("[]'\" "))

def resolve_column(ref: str, meta_map: dict) -> Dict[str, Any]:
    agg, key = unpack_ref(ref)
    table_name = meta_map.get(key, {}).get("table") if meta_map else None
    return {"column": key, "table": table_name, "aggregation": agg}

def buildMetaMap(root: ET.Element) -> Dict[str, Dict[str, str]]:
    return build_meta_map(root)

def resolveColumn(ref: str, meta_map: dict) -> Dict[str, Any]:
    return resolve_column(ref, meta_map)

def extract_column_names(formula: str) -> List[str]:
    if not formula:
        return []
    return re.findall(r'\[([A-Za-z0-9_\s\-\.:]+)\]', formula)

def parse_calculated_column(root: ET.Element, db_map: dict) -> List[Dict[str, Any]]:
    calculated_columns = set()
    for ws in root.findall('.//worksheet'):
        for dependency in ws.findall('./table/view/datasource-dependencies'):
            for column in dependency.findall('column'):
                calculation = column.find('calculation')
                if calculation is not None:
                    column_name = column.get('caption') or column.get('name')
                    formula = calculation.get('formula')
                    datatype = column.get('datatype')
                    table_assigned = None
                    col_refs = extract_column_names(formula)
                    if col_refs and db_map:
                        table_assigned = db_map.get(col_refs[0], {}).get("table")
                    calculated_columns.add((column_name, formula, datatype, table_assigned))
    unique_calculated_columns = [
        {'column_name': t[0], 'formula': t[1], 'datatype': t[2], 'table': t[3]}
        for t in calculated_columns
    ]
    return unique_calculated_columns

def parseWorksheet(root: ET.Element, db_map: dict) -> Dict[str, Any]:
    sheetMapper = {}
    for ws in root.findall('.//worksheet'):
        sheetName = ws.get('name')
        sheetMapper[sheetName] = {}
        mark = ws.find('./table//panes//pane/mark')
        sheetMapper[sheetName]['visualType'] = mark.get('class') if mark is not None else ""
        main_table = ws.find('./table//view/datasources/datasource')
        sheetMapper[sheetName]['main_table'] = str(main_table.get('caption', '')).split('+')[0] if main_table is not None else ''
        Title = ws.find('.//run')
        if Title is not None:
            sheetMapper[sheetName]['chartTilte'] = Title.text
            sheetMapper[sheetName]['fontname'] = Title.get('fontname', 'Segoe UI Semibold')
            sheetMapper[sheetName]['fontsize'] = Title.get('fontsize', 11)
        else:
            sheetMapper[sheetName]['chartTilte'] = ""
            sheetMapper[sheetName]['fontname'] = ""
            sheetMapper[sheetName]['fontsize'] = ""

        y_axis = ws.find('.//rows')
        x_axis = ws.find('.//cols')
        if y_axis is not None and y_axis.text:
            list_y_column = []
            for column in y_axis.text.split('/'):
                y_columns = resolve_column(column, db_map)
                list_y_column.append(y_columns)
            sheetMapper[sheetName]['rows'] = list_y_column
        else:
            sheetMapper[sheetName]['rows'] = []
        if x_axis is not None and x_axis.text:
            list_x_column = []
            for row in x_axis.text.split('/'):
                x_columns = resolve_column(row, db_map)
                list_x_column.append(x_columns)
            sheetMapper[sheetName]['cols'] = list_x_column
        else:
            sheetMapper[sheetName]['cols'] = []
        unique_tags = {}
        for pane in ws.findall('.//pane'):
            encodings = pane.find('encodings')
            if encodings is not None:
                for element in encodings:
                    tag_name = element.tag
                    if tag_name not in unique_tags:
                        unique_tags[tag_name] = []
                    parsed = resolve_column(ET.tostring(element, encoding='unicode'), db_map)
                    unique_tags[tag_name].append(parsed)
        sheetMapper[sheetName]['encodings'] = unique_tags
    return sheetMapper

def parse_tables_and_connections(root: ET.Element, hyper_file_path: str):
    parsed_tables_info_dict = {}
    unique_data_source_connections = {}
    hyper_schema = {}
    if hyper_file_path and os.path.exists(hyper_file_path):
        hyper_schema = get_columns_from_hyper_file(hyper_file_path)
    for ds_elem in root.findall(".//datasource"):
        ds_name = ds_elem.get('name') or ds_elem.get('caption') or None
        if ds_elem.get('source-type') == 'hyper' and hyper_schema:
            print(f"Detected Hyper extract for datasource: {ds_name}. Using Hyper file schema.")
            for full_table_name, columns in hyper_schema.items():
                table_logical_name = ds_elem.get('caption') or full_table_name
                if table_logical_name not in parsed_tables_info_dict:
                    conn_key = ('hyper', hyper_file_path)
                    unique_data_source_connections[conn_key] = {
                        "type": "hyper",
                        "path": hyper_file_path,
                        "bim_name": f"HyperSource_{sanitize_name(os.path.basename(hyper_file_path))}"
                    }
                    parsed_tables_info_dict[table_logical_name] = {
                        'table_name': table_logical_name,
                        'db_table_path': full_table_name,
                        'db_schema': full_table_name.split('.')[0] if '.' in full_table_name else '',
                        'db_item_name': full_table_name.split('.')[-1],
                        'columns': columns,
                        'connection_key': conn_key
                    }
        else:
            conn_elem = ds_elem.find(".//connection")
            if conn_elem is None:
                continue
            server_address = conn_elem.get('server') or conn_elem.get('host') or ""
            database_name = conn_elem.get('dbname') or conn_elem.get('odbc-dbname') or ds_name or ""
            conn_key_from_twb = (server_address, database_name)

            if conn_key_from_twb not in unique_data_source_connections:
                unique_data_source_connections[conn_key_from_twb] = {
                    "type": "database",
                    "server": server_address,
                    "database": database_name,
                    "username": conn_elem.get('username') or "UAT_TBI_DASHBOARD_LOGIN",
                    "password": conn_elem.get('password') or "UAT_TBI_DASHBOARD_LOGIN_$25#",
                    "bim_name": f"DataSource_{sanitize_name(database_name)}_{generate_guid().replace('-', '')[:8]}"
                }
            for relation_elem in ds_elem.findall(".//relation[@type='table']"):
                db_table_path_full = relation_elem.get('table')
                table_name_logical = relation_elem.get('name') or db_table_path_full or ds_name
                if not table_name_logical or not db_table_path_full:
                    continue
                table_path = db_table_path_full.strip("[]")
                db_path_parts = table_path.split('].[') if '].[' in db_table_path_full else table_path.split('.')
                if len(db_path_parts) > 1:
                    db_schema = db_path_parts[-2].strip("[]")
                    db_item_name = db_path_parts[-1].strip("[]")
                else:
                    db_schema = "dbo"
                    db_item_name = db_path_parts[0].strip("[]")
                table_columns = []
                for col_metadata in ds_elem.findall(".//metadata-record[@class='column']"):
                    parent_name_from_meta = (col_metadata.findtext("parent-name") or "").strip("[]")
                    if parent_name_from_meta == table_name_logical or parent_name_from_meta == db_table_path_full.strip("[]"):
                        local_name = (col_metadata.findtext("local-name") or "").strip("[]")
                        remote_name = (col_metadata.findtext("remote-name") or "").strip("[]")
                        data_type_attr = col_metadata.findtext("local-type") or "string"
                        pb_data_type = map_tableau_type_to_pb_type(data_type_attr)
                        if not any(col['name'] == local_name for col in table_columns):
                            table_columns.append({
                                'name': local_name,
                                'remote_name': remote_name or local_name,
                                'data_type': pb_data_type
                            })
                if table_columns:
                    table_unique_id = (conn_key_from_twb, db_table_path_full)
                    if table_unique_id not in parsed_tables_info_dict:
                        parsed_tables_info_dict[table_unique_id] = {
                            'table_name': table_name_logical,
                            'db_table_path': db_table_path_full,
                            'db_schema': db_schema,
                            'db_item_name': db_item_name,
                            'columns': table_columns,
                            'connection_key': conn_key_from_twb
                        }
    parsed_tables_info = list(parsed_tables_info_dict.values())
    return parsed_tables_info, unique_data_source_connections

def parse_relationship(root: ET.Element, table_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    relationships_list = []
    for join_elem in root.findall(".//join") + root.findall(".//group/join"):
        left_rel = join_elem.find('repository-connection/relation[@role="left"]')
        right_rel = join_elem.find('repository-connection/relation[@role="right"]')
        left_table_name = left_rel.get("name") if left_rel is not None else None
        right_table_name = right_rel.get("name") if right_rel is not None else None
        if not left_table_name or not right_table_name:
            continue
        left_table = table_map.get(left_table_name)
        right_table = table_map.get(right_table_name)
        if not left_table or not right_table:
            continue
        for join_field in join_elem.findall('join-field'):
            left_col_elem = join_field.find('field[@role="left"]')
            right_col_elem = join_field.find('field[@role="right"]')
            left_col = left_col_elem.text if left_col_elem is not None else None
            right_col = right_col_elem.text if right_col_elem is not None else None
            if left_col and right_col:
                relationship = {
                    "operand_1": {
                        "column": clean_column_display_name(left_col),
                        "table": left_table['table_name']
                    },
                    "operand_2": {
                        "column": clean_column_display_name(right_col),
                        "table": right_table['table_name']
                    }
                }
                relationships_list.append(relationship)
    return relationships_list

def parse_twb_file(file_path: str, hyper_file_path: str = None) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"TWB file not found: {file_path}")
    if hyper_file_path is None:
        twb_dir = os.path.dirname(file_path)
        twb_name = os.path.splitext(os.path.basename(file_path))[0]
        possible_hyper_paths = [
            os.path.join(twb_dir, f"{twb_name}.hyper"),
            os.path.join(twb_dir, f"{twb_name} Extract.hyper")
        ]
        for p in possible_hyper_paths:
            if os.path.exists(p):
                hyper_file_path = p
                print(f"Found associated Hyper file: {hyper_file_path}")
                break
    final_hyper_file_path = hyper_file_path if hyper_file_path is not None else ''
    tree = ET.parse(file_path)
    root = tree.getroot()
    meta_map = build_meta_map(root)
    parsed_tables_info, unique_data_source_connections = parse_tables_and_connections(root, final_hyper_file_path)
    table_logical_name_map = {t['table_name']: t for t in parsed_tables_info}
    columns_by_table = defaultdict(list)
    measures_by_table = defaultdict(list)
    for t in parsed_tables_info:
        tbl_name = t['table_name']
        for col in t.get('columns', []):
            col_name = clean_column_display_name(col['name'])
            columns_by_table[tbl_name].append({
                'name': col_name,
                'remote_name': col.get('remote_name') or col_name,
                'data_type': col.get('data_type')
            })
            if col.get('data_type') in ("Int64", "Double"):
                measures_by_table[tbl_name].append({
                    'name': col_name,
                    'expression': f"SUM ( '{tbl_name}'[{col_name}] )",
                    'displayFolder': 'Measures'
                })
            if col_name.lower() == "number of records":
                measures_by_table[tbl_name].append({
                    'name': "Number of Records",
                    'expression': f"SUM ( '{tbl_name}'[Number of Records] )",
                    'displayFolder': 'Measures'
                })
    relationships = parse_relationship(root, table_logical_name_map)
    calculated_columns = parse_calculated_column(root, table_logical_name_map)
    worksheets = parseWorksheet(root, table_logical_name_map)

    return {
        "tables_info": table_logical_name_map,
        "columns_by_table": columns_by_table,
        "measures_by_table": measures_by_table,
        "connections": unique_data_source_connections,
        "relationships": relationships,
        "calculated_columns": calculated_columns,
        "worksheets": worksheets,
        "meta_map": meta_map
    }

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tableau_files_dir = os.path.join(current_dir, "..", "02_tableau_files")
    twb_files = glob.glob(os.path.join(tableau_files_dir, "*.twb")) + \
                glob.glob(os.path.join(tableau_files_dir, "*.twbx"))

    for path in twb_files:
        temp_dir = None
        twb_path_to_parse = None
        hyper_file_path = None
        try:
            file_extension = os.path.splitext(path)[1].lower()
            file_name_without_ext = os.path.splitext(os.path.basename(path))[0]
            if file_extension == '.twbx':
                temp_dir = os.path.join(tableau_files_dir, f"temp_{file_name_without_ext}")
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                twb_files_in_zip = glob.glob(os.path.join(temp_dir, "*.twb"))
                if not twb_files_in_zip:
                    continue
                twb_path_to_parse = twb_files_in_zip[0]
                hyper_files_in_zip = glob.glob(os.path.join(temp_dir, "*.hyper"))
                if hyper_files_in_zip:
                    hyper_file_path = hyper_files_in_zip[0]
            elif file_extension == '.twb':
                twb_path_to_parse = path
                possible_hyper_paths = [
                    os.path.join(tableau_files_dir, f"{file_name_without_ext}.hyper"),
                    os.path.join(tableau_files_dir, f"{file_name_without_ext} Extract.hyper")
                ]
                for p in possible_hyper_paths:
                    if os.path.exists(p):
                        hyper_file_path = p
                        break
            if twb_path_to_parse:
                parsed = parse_twb_file(twb_path_to_parse, hyper_file_path)
                print(f"Parsed {os.path.basename(twb_path_to_parse)}")
        except Exception as e:
            print(f"Error parsing {path}: {e}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)