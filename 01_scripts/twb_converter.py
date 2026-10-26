import xml.etree.ElementTree as ET
import json
import os
import uuid
import shutil
from generate_report_json import *


# --- Configuration ---
# Path to your Tableau TWB file
SCRIPTS_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
TWB_FILE_PATH = os.path.join(
    ROOT_DIR, '02_tableau_files', 'Complex HRMS Employee Dashboard.twb'
)
print('TWB_FILE_PATH----', TWB_FILE_PATH)
base_file_name = os.path.splitext(os.path.basename(TWB_FILE_PATH))[0]
print('base_file_name----', base_file_name)
OUTPUT_PBIP_ROOT_DIR = os.path.join(
    ROOT_DIR, '03_converted_pbips'
)
FINAL_PBIP_FOLDER_PATH = os.path.join(OUTPUT_PBIP_ROOT_DIR, f"{base_file_name}.pbip")
print('FINAL_PBIP_FOLDER_PATH----', FINAL_PBIP_FOLDER_PATH)
DATASET_NAME = f"{base_file_name} Dataset" # Changed to be dynamic with base_file_name
TABLE_NAME = "Employee_Master_TBI" # Or your dynamic version (will be extracted from TWB eventually)
DB_SERVER_IP_PORT = "172.19.225.120,11433"
DB_NAME = "UAT_TBI_DASHBOARD"

# Placeholder for base theme colors if not extracted from TWB
DEFAULT_DATA_COLORS = [
    "#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2",
    "#D9B300", "#D64550", "#197278", "#1AAB40", "#15C6F4", "#4092FF"
]

def create_pbip_folders(pbip_full_path: str, base_file_name: str):
    """Creates the standard PBIP folder structure within the specified pbip_full_path."""

    print(f"\n[DEBUG - create_pbip_folders] Function called.")
    print(f"[DEBUG - create_pbip_folders] Arg 'pbip_full_path': {pbip_full_path}")
    print(f"[DEBUG - create_pbip_folders] Arg 'base_file_name': {base_file_name}")

    if os.path.exists(pbip_full_path):
        print(f"[DEBUG - create_pbip_folders] Existing PBIP folder found: {pbip_full_path}")
        print(f"[DEBUG - create_pbip_folders] Attempting to delete existing folder...")
        try:
            shutil.rmtree(pbip_full_path)
            print(f"[DEBUG - create_pbip_folders] Successfully deleted existing folder.")
        except PermissionError as e:
            print(f"[ERROR - create_pbip_folders] Permission denied when trying to delete {pbip_full_path}: {e}")
            print(f"[ERROR - create_pbip_folders] This means the folder is locked. Close any programs accessing it.")
            raise # Re-raise to stop execution
        except Exception as e:
            print(f"[ERROR - create_pbip_folders] An unexpected error occurred during deletion: {e}")
            raise # Re-raise other errors
    else:
        print(f"[DEBUG - create_pbip_folders] No existing PBIP folder found. Creating new.")

    try:
        os.makedirs(pbip_full_path) # Create the main .pbip folder
        print(f"[DEBUG - create_pbip_folders] Successfully created main PBIP folder: {pbip_full_path}")
    except Exception as e:
        print(f"[ERROR - create_pbip_folders] Failed to create main PBIP folder {pbip_full_path}: {e}")
        raise # Re-raise to stop execution

    # Define sub-directories relative to the pbip_full_path
    report_folder_name = f'{base_file_name}.Report'
    semantic_model_folder_name = f'{base_file_name}.SemanticModel'

    report_dir = os.path.join(pbip_full_path, report_folder_name)
    semantic_model_dir = os.path.join(pbip_full_path, semantic_model_folder_name)

    print(f"[DEBUG - create_pbip_folders] Report directory will be: {report_dir}")
    print(f"[DEBUG - create_pbip_folders] Semantic Model directory will be: {semantic_model_dir}")

    # Report folders
    os.makedirs(os.path.join(report_dir, '.pbi'))
    os.makedirs(os.path.join(report_dir, 'StaticResources', 'SharedResources', 'BaseThemes'))

    # Semantic Model folders (Adjusted for TMDL structure)
    semantic_model_pbi_dir = os.path.join(semantic_model_dir, '.pbi')
    semantic_model_definition_dir = os.path.join(semantic_model_dir, 'definition')
    semantic_model_cultures_dir = os.path.join(semantic_model_definition_dir, 'cultures')
    semantic_model_tables_dir = os.path.join(semantic_model_definition_dir, 'tables')

    os.makedirs(semantic_model_pbi_dir)
    os.makedirs(semantic_model_cultures_dir)
    os.makedirs(semantic_model_tables_dir)

    print(f"[DEBUG - create_pbip_folders] All sub-folders created.")
    return report_dir, semantic_model_dir

def write_json_file(path, data):
    """Writes a dictionary to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True) # Ensure directory exists
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Created/Updated JSON file: {path}")

# def write_tmdl_file(path, content):
#     """Writes TMDL content to a file."""
#     os.makedirs(os.path.dirname(path), exist_ok=True) # Ensure directory exists
#     with open(path, 'w', encoding='utf-8') as f:
#         f.write(content)
#     print(f"Created/Updated TMDL file: {path}")

def generate_guid():
    return str(uuid.uuid4())

def sanitize_name(name: str):
    """Cleans a string to be suitable for names/IDs (e.g., in BIM file)."""
    # Remove characters not typically allowed or problematic in IDs/names
    cleaned_name = re.sub(r'[\[\]\s\-\(\).]', '', name)
    return cleaned_name

def clean_column_display_name(name):
    """
    Cleans a column display name by:
    1. Removing leading/trailing square brackets.
    2. Removing text in parentheses and the parentheses themselves.
    3. Converting to uppercase.
    """
    cleaned_name = name.strip('[]')
    cleaned_name = re.sub(r'\(.*?\)', '', cleaned_name).strip()
    cleaned_name = cleaned_name
    return cleaned_name


def map_tableau_type_to_pb_type(tableau_type):
    """Maps Tableau data types to Power BI data types."""
    # This mapping should be comprehensive based on your Tableau data.
    # Add more mappings as needed.
    if tableau_type == 'integer':
        return 'Int64'
    elif tableau_type == 'real':
        return 'Double'
    elif tableau_type == 'date' or tableau_type == 'datetime':
        return 'DateTime'
    elif tableau_type == 'boolean':
        return 'Boolean'
    else:
        return 'String' # Default for anything else


DEFAULT_DB_SERVER_IP_PORT = "172.19.225.120,11433"
DEFAULT_DB_NAME = "UAT_TBI_DASHBOARD"
DEFAULT_DB_USERNAME = "UAT_TBI_DASHBOARD_LOGIN"
DEFAULT_DB_PASSWORD = "UAT_TBI_DASHBOARD_LOGIN_$25#" # Placeholder password for connection
DEFAULT_DATA_COLORS = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF"] # Example colors


def parse_twb(twb_file_path):
    tree = ET.parse(twb_file_path)
    root = tree.getroot()

    parsed_tables_info_dict = {}
    unique_data_source_connections = {}
    connections_by_id = {}
    # NEW: Store relation object-ids to map them to table names
    table_object_id_to_name_map = {}

    # --- Pass 1: Collect Connection Details from named-connections ---
    # (No changes here, keep your existing Pass 1)
    for ds_elem in root.findall(".//datasource"):
        for named_conn_elem in ds_elem.findall(".//named-connection"):
            conn_id_from_twb = named_conn_elem.get('name')
            if not conn_id_from_twb:
                print(f"[WARNING] Skipping named-connection without a 'name' attribute in datasource: {ds_elem.get('caption', ds_elem.get('name'))}")
                continue

            db_details_conn_elem = named_conn_elem.find("./connection")

            if db_details_conn_elem is not None:
                server_address = db_details_conn_elem.get('server', DEFAULT_DB_SERVER_IP_PORT)
                database_name = db_details_conn_elem.get('dbname', DEFAULT_DB_NAME)

                username = DEFAULT_DB_USERNAME
                password = DEFAULT_DB_PASSWORD # IMPORTANT: Set this securely!

                conn_key = (server_address, database_name, username)

                if conn_key not in unique_data_source_connections:
                    unique_data_source_connections[conn_key] = {
                        "server": server_address,
                        "database": database_name,
                        "username": username,
                        "password": password,
                        "bim_name": f"DataSource_{sanitize_name(database_name)}_{generate_guid().replace('-','')[:8]}"
                    }

                connections_by_id[conn_id_from_twb] = conn_key
            else:
                print(f"[WARNING] Named-connection '{conn_id_from_twb}' found without a nested <connection> element. Skipping connection details.")


    # --- Pass 2: Collect Table Relations and their Columns ---
    for ds_elem in root.findall(".//datasource"):
        columns_metadata_map = {}
        
        for col_metadata in ds_elem.findall(".//metadata-record[@class='column']"):
            local_name = col_metadata.findtext("local-name")
            remote_name = col_metadata.findtext("remote-name")
            data_type_attr = col_metadata.get("data-type")
            

            if not data_type_attr:
                aggregation_hint = col_metadata.findtext("aggregation")
                data_type_attr = aggregation_hint if aggregation_hint and aggregation_hint != 'Measures' else 'string'

            if local_name and remote_name:
                pb_data_type = map_tableau_type_to_pb_type(data_type_attr)
                columns_metadata_map[remote_name.strip('[]')] = {
                    'local_name': local_name,
                    'remote_name': remote_name,
                    'data_type': pb_data_type
                }
        
        tableau_display_to_source_map = {}
        for col_map_elem in ds_elem.findall("./connection/cols/map"):
            key = col_map_elem.get('key')
            value = col_map_elem.get('value')
            if key and value:
                tableau_display_to_source_map[key] = value

        
        for relation_elem in ds_elem.findall(".//relation"):
            relation_type = relation_elem.get('type')

            if relation_type in ['table', 'text', 'sql', 'collection']:
                for relationship_elem in relation_elem.findall("./relation"):
                    
                    table_name_logical = relationship_elem.get('name')
                    
                    db_table_path_full = relationship_elem.get('table')
                    connection_ref_id = relationship_elem.get('connection')
                    # NEW: Get the object-id if available for this relation
                    for col_metadata in ds_elem.findall(".//metadata-record[@class='column']"):
                        relation_obj_id = col_metadata.findtext('object-id') # This is the key for relationships
                        

                        if not table_name_logical or not db_table_path_full or not connection_ref_id:
                            print(f"[WARNING] Incomplete relation element found (type='{relation_type}'). Skipping: {ET.tostring(relation_elem, encoding='unicode').strip()}")
                            continue

                        conn_key = connections_by_id.get(connection_ref_id)
                        if not conn_key:
                            print(f"[ERROR] Connection ID '{connection_ref_id}' for table '{table_name_logical}' not found in parsed connections. Skipping table.")
                            continue

                        table_columns = []
                        match = re.search(r'\[([^\]]+)\]$', db_table_path_full)
                        if match:
                            unqualified_db_table_name = match.group(1)
                        else:
                            unqualified_db_table_name = db_table_path_full.strip('[]')

                        for tableau_display_name, source_col_path in tableau_display_to_source_map.items():
                            expected_source_prefix = f'[{unqualified_db_table_name}].'
                            if source_col_path.startswith(expected_source_prefix):
                                actual_remote_col_name = source_col_path.split('.')[-1].strip('[]')
                                if actual_remote_col_name in columns_metadata_map:
                                    col_data = columns_metadata_map[actual_remote_col_name]
                                    table_columns.append({
                                        'name': col_data['local_name'],
                                        'remote_name': col_data['remote_name'],
                                        'data_type': col_data['data_type']
                                    })
                                else:
                                    print(f"[WARNING] Mapped column '{tableau_display_name}' (source: '{source_col_path}') for table '{table_name_logical}' was not found in datasource metadata-records. Skipping.")
                        
                        if not table_columns:
                            print(f"[WARNING] No columns dynamically found for table '{table_name_logical}' from DB path '{db_table_path_full}'. This table will have no columns in the BIM output unless Tableau's XML is incomplete for it.")

                        if table_columns:
                            table_unique_id = (conn_key, db_table_path_full)
                            if table_unique_id in parsed_tables_info_dict:
                                print(f"[INFO] Duplicate table entry found for '{table_name_logical}' (DB Path: '{db_table_path_full}') under connection {conn_key}. Overwriting with latest parsed data.")

                            parsed_tables_info_dict[table_unique_id] = {
                                'table_name': table_name_logical,
                                'db_table_path': db_table_path_full,
                                'columns': table_columns,
                                'connection_key': conn_key
                            }
                            # NEW: Add mapping from Tableau object-id to our friendly table name
                        if relation_obj_id:
                            table_object_id_to_name_map[relation_obj_id] = table_name_logical
                            
            else:
                print(f"[INFO] Skipping relation of type '{relation_type}' (only 'table', 'text', 'sql' are processed for now): {ET.tostring(relation_elem, encoding='unicode').strip()}")

    parsed_tables_info = list(parsed_tables_info_dict.values())

    # --- FINAL Fallback if no tables parsed at all (for robustness, not ideal) ---
    if not parsed_tables_info:
        print("[CRITICAL ERROR] No tables (relations of type 'table', 'text', or 'sql') found in the TWB file's datasources. The generated BIM will be empty or use a generic fallback. Please check TWB structure.")
        fallback_conn_key = (DEFAULT_DB_SERVER_IP_PORT, DEFAULT_DB_NAME, DEFAULT_DB_USERNAME)
        if fallback_conn_key not in unique_data_source_connections:
            unique_data_source_connections[fallback_conn_key] = {
                "server": DEFAULT_DB_SERVER_IP_PORT,
                "database": DEFAULT_DB_NAME,
                "username": DEFAULT_DB_USERNAME,
                "password": DEFAULT_DB_PASSWORD,
                "bim_name": f"DataSource_Fallback_{generate_guid().replace('-','')[:8]}"
            }
        parsed_tables_info.append({
            'table_name': "Generic_Fallback_Table",
            'db_table_path': "[dbo].[GenericTable]",
            'columns': [
                {'name': 'ID', 'remote_name': 'ID', 'data_type': 'String'},
                {'name': 'Value', 'remote_name': 'Value', 'data_type': 'Double'}
            ],
            'connection_key': fallback_conn_key
        })

    # --- NEW: Extract Relationships ---
    parsed_relationships = []
    for ds_elem in root.findall(".//datasource"): # Ensure we check all datasources for relationships
        # Re-parse tableau_display_to_source_map for the current datasource for relationship column lookup
        current_ds_tableau_display_to_source_map = {}
        for col_map_elem in ds_elem.findall("./connection/cols/map"):
            key = col_map_elem.get('key')
            value = col_map_elem.get('value')
            if key and value:
                current_ds_tableau_display_to_source_map[key] = value

        # CORRECTED LINE HERE: Removed the extra '.' after datasource
        for relationship_elem in ds_elem.findall(".//relationships/relationship"): # Corrected path

            try:
                # ... (rest of your relationship parsing logic) ...
                expression_elements = relationship_elem.findall("./expression/expression")
                
                if len(expression_elements) != 2:
                    print(f"[WARNING] Relationship expression found with more/less than 2 parts. Skipping: {ET.tostring(relationship_elem, encoding='unicode').strip()}")
                    continue

                col1_tableau_name = expression_elements[0].get('op')
                
                col2_tableau_name = expression_elements[1].get('op')
                

                first_endpoint_id = relationship_elem.find("./first-end-point").get('object-id')
                second_endpoint_id = relationship_elem.find("./second-end-point").get('object-id')
                
                table1_name = 'Employee_Master_TBI' #table_object_id_to_name_map.get(first_endpoint_id)
                
                
                table2_name = 'Salary_TBI' #table_object_id_to_name_map.get(second_endpoint_id)
                
                if not table1_name or not table2_name:
                    print(f"[WARNING] Could not map one or both relationship object-ids ({first_endpoint_id}, {second_endpoint_id}) to table names. Skipping relationship.")
                    continue

                col1_source_path = current_ds_tableau_display_to_source_map.get(col1_tableau_name)
                col2_source_path = current_ds_tableau_display_to_source_map.get(col2_tableau_name)

                if not col1_source_path or not col2_source_path:
                    print(f"[WARNING] Could not find source path for one or both relationship columns ('{col1_tableau_name}', '{col2_tableau_name}'). Skipping relationship.")
                    continue

                col1_remote_name = col1_source_path.split('.')[-1].strip('[]')
                col2_remote_name = col2_source_path.split('.')[-1].strip('[]')

                # Determine 'From' (Many) and 'To' (One) tables and columns
                # This is a critical assumption and might need adjustment based on your data model.
                # The relationship XML example shows:
                # <expression op='[EMP_ID]' /> (Table 1: Employee_Master_TBI)
                # <expression op='[EMP_ID (Salary_TBI)]' /> (Table 2: Salary_TBI)
                # If Employee_Master_TBI is the 'one' side (unique EMP_ID) and Salary_TBI is 'many'
                # then From (many) = Salary_TBI, To (one) = Employee_Master_TBI

                # Let's map column names from parsed_tables_info for BIM output
                # Create a temporary lookup for BIM column names (local_name from Tableau)
                # { (table_name, remote_name): bim_column_name }
                bim_column_name_lookup = {}
                for table_data in parsed_tables_info:
                    for col in table_data['columns']:
                        # Apply the cleaning to the column's 'name' before storing it
                        cleaned_col_name = re.sub(r'\(.*?\)', '', col['name']).strip('[]').strip()
                        bim_column_name_lookup[(table_data['table_name'], col['remote_name'].strip('[]'))] = cleaned_col_name

                from_table_bim_name = table2_name # Assuming table2 is the 'many' side (Salary_TBI)
                to_table_bim_name = table1_name   # Assuming table1 is the 'one' side (Employee_Master_TBI)

                # Find the actual BIM column name for 'fromColumn'
                from_column_bim_name = bim_column_name_lookup.get((from_table_bim_name, col2_remote_name))
                # Find the actual BIM column name for 'toColumn'
                to_column_bim_name = bim_column_name_lookup.get((to_table_bim_name, col1_remote_name))

                shared_view_element = root.find(".//shared-view")

                # Check if the element was found and extract the 'name' attribute
                if shared_view_element is not None:
                    relationship_name_obj_id = shared_view_element.get('name')
                else:
                    print("The 'shared-view' element was not found.")


                if not from_column_bim_name or not to_column_bim_name:
                    print(f"[WARNING] Could not determine BIM column names for relationship: {col1_tableau_name} and {col2_tableau_name}. Skipping relationship.")
                    continue

                # relationship_name = f"Relationship_{sanitize_name(from_table_bim_name)}_{sanitize_name(from_column_bim_name)}_to_{sanitize_name(to_table_bim_name)}_{sanitize_name(to_column_bim_name)}"
                
                parsed_relationships.append({
                    "name": relationship_name_obj_id,
                    "fromTable": from_table_bim_name,
                    "fromColumn": from_column_bim_name,
                    "toTable": to_table_bim_name,
                    "toColumn": to_column_bim_name,
                    "isActive": True
                })
                

            except Exception as e:
                print(f"[ERROR] Failed to parse relationship element: {ET.tostring(relationship_elem, encoding='unicode').strip()}. Error: {e}")
                continue

    # --- Extract Report Pages (Worksheets & Dashboards) ---
    report_pages = []
    # (Your existing report page parsing logic here)
    # Dashboards first
    for dashboard in root.findall(".//dashboard"):
        page_name = dashboard.get('name')
        if not page_name:
            continue

        page_data = {
            'displayName': page_name,
            'name': sanitize_name(page_name),
            'visuals': []
        }

        dashboard_size = dashboard.find("./size")
        if dashboard_size:
            page_data['width'] = float(dashboard_size.get('max-width', 1280.0))
            page_data['height'] = float(dashboard_size.get('max-height', 720.0))
        else:
            page_data['width'] = 1280.0
            page_data['height'] = 720.0

        for zone in dashboard.findall(".//zone"):
            visual_type = zone.get('type')
            if visual_type == 'worksheet':
                worksheet_name = zone.findtext("worksheet")
                worksheet_elem = root.find(f".//worksheet[@name='{worksheet_name}']")
                if worksheet_elem:
                    # NOTE: extract_visual_from_worksheet needs parsed_tables_info
                    # and potentially the relationship info if visuals depend on them.
                    # For now, it's outside the scope of this relationship fix.
                    visual_info = {} # Placeholder: extract_visual_from_worksheet(worksheet_elem, parsed_tables_info)
                    if visual_info:
                        rect = zone.find("./rect")
                        if rect is not None:
                            visual_info['x'] = float(rect.get('x', 0))
                            visual_info['y'] = float(rect.get('y', 0))
                            visual_info['width'] = float(rect.get('width', 300))
                            visual_info['height'] = float(rect.get('height', 200))
                        page_data['visuals'].append(visual_info)
            elif visual_type == 'text':
                pass # Or add basic text visual
        report_pages.append(page_data)

    data_colors = DEFAULT_DATA_COLORS

    return parsed_tables_info, unique_data_source_connections, parsed_relationships, report_pages, data_colors





def extract_visual_from_worksheet(worksheet_elem, table_name_for_ref):
    """Extracts visual info from a Tableau worksheet element."""
    visual_info = {}
    visual_info['name'] = worksheet_elem.get('name')
    visual_info['visual_type'] = None
    visual_info['projections'] = {}
    visual_info['filters'] = []

    # Determine visual type based on marks type
    marks_elem = worksheet_elem.find(".//marks")
    if marks_elem is not None:
        marks_type = marks_elem.get('class')
        if marks_type == 'bar':
            visual_info['visual_type'] = 'columnChart' 
        elif marks_type == 'pie':
            visual_info['visual_type'] = 'pieChart' 
        elif marks_type == 'line':
            visual_info['visual_type'] = 'lineChart'
        elif marks_type == 'area':
            visual_info['visual_type'] = 'areaChart'
        elif marks_type == 'text': # For text tables
            visual_info['visual_type'] = 'table'
        # Add more mappings as needed for simple charts
        # You'll need to define what 'slicer' visual type corresponds to in Tableau

    if not visual_info['visual_type']:
        print(f"[WARNING] Unsupported Tableau visual type '{marks_type}' found for worksheet '{visual_info['name']}'. Skipping.")
        return None # Skip unsupported visual types

    # Extract fields (projections)
    for col_shelf in worksheet_elem.findall(".//column"): # Fields on shelves
        attr = col_shelf.get('attr') # e.g., 'columns', 'rows'
        field_name_full = col_shelf.get('field') 

        if field_name_full:
            # Extract just the field name, remove brackets and table prefix
            # e.g., [Employee_Master_TBI].[Dept Name] -> Dept Name
            field_name = field_name_full.split('].')[-1].replace(']', '')
            
            # Check if it's a measure (starts with [Measures]) or a dimension
            is_measure = field_name_full.startswith('[Measures]')
            
            query_ref_prefix = f'SUM({table_name_for_ref}.' if is_measure else f'{table_name_for_ref}.'


            if attr == 'columns': # Tableau columns often map to Power BI X-axis or Values for bar charts
                if visual_info['visual_type'] in ['columnChart', 'barChart']: # For bar/column, columns are usually value
                    visual_info['projections']['Y'] = {'queryRef': f'{query_ref_prefix}{field_name})' if is_measure else f'{table_name_for_ref}.{field_name}'}
                elif visual_info['visual_type'] == 'table': # For tables, columns are just values
                     visual_info['projections']['Values'] = {'queryRef': f'{query_ref_prefix}{field_name})' if is_measure else f'{table_name_for_ref}.{field_name}'}

            elif attr == 'rows': # Tableau rows often map to Power BI Category or X-axis for bar charts
                if visual_info['visual_type'] in ['columnChart', 'barChart']: # For bar/column, rows are usually category
                    visual_info['projections']['Category'] = {'queryRef': f'{table_name_for_ref}.{field_name}'}
                elif visual_info['visual_type'] == 'table': # For tables, rows are just values
                     visual_info['projections']['Values'] = {'queryRef': f'{query_ref_prefix}{field_name})' if is_measure else f'{table_name_for_ref}.{field_name}'}
            
            # Example for Slicer if you add it. Tableau slicers are often quick filters.
            # You might need to look at <filter> elements specifically for slicer-like behavior.
            # If a visual should be a slicer:
            # if 'slicer_field' in visual_info and visual_info['slicer_field'] == field_name_full:
            #     visual_info['visual_type'] = 'slicer'
            #     visual_info['projections']['Values'] = {'queryRef': f'{table_name_for_ref}.{field_name}'}


    # Extract simple filters
    for filter_elem in worksheet_elem.findall(".//filter"):
        filter_field_full = filter_elem.get('column')
        if filter_field_full:
            filter_field_name = filter_field_full.split('].')[-1].replace(']', '')

            group_filter = filter_elem.find("./groupfilter")
            if group_filter is not None:
                member_values = [m.get('member') for m in group_filter.findall("./member")]
                if member_values:
                    visual_info['filters'].append({
                        "column": filter_field_name, # Raw column name
                        "values": member_values
                    })
    
    return visual_info

def generate_model_bim_content(parsed_tables_info, unique_data_source_connections, parsed_relationships, semantic_model_logical_id):
    """
    Generates the content for the model.bim file, supporting multiple tables and data sources,
    and removes duplicate columns based on their 'name' (after cleaning) within each table.
    """
    
    bim_tables = []
    for table_data in parsed_tables_info:
        
        table_name_friendly = table_data['table_name']

        conn_key = table_data['connection_key']
        conn_details = unique_data_source_connections[conn_key]
        db_server_address = conn_details['server']
        db_database_name = conn_details['database']

        db_path_parts = table_name_friendly.strip('[]').split('].[')
        if len(db_path_parts) == 2:
            db_schema = db_path_parts[0]
            db_item_name = db_path_parts[1]
        else:
            db_schema = "dbo"
            db_item_name = db_path_parts[0]

        # --- REINSTATED: unique_bim_columns dictionary to de-duplicate columns by their 'name' ---
        unique_bim_columns = {}
        for col in table_data['columns']:
            # Use the helper function to clean the column display name
            cleaned_column_name = clean_column_display_name(col['name'])

            # If the cleaned name is already present, skip this column (it's a duplicate display name)
            if cleaned_column_name in unique_bim_columns:
                print(f"Skipping duplicate column '{col['name']}' (cleaned to '{cleaned_column_name}') in table '{table_name_friendly}'.")
                continue # Skip to the next column

            # If not a duplicate, add it to our unique set
            summarize_by = "none"
            # Ensure correct key is used: 'data_type' from parsed_tables_info
            if col['data_type'] in ["Int64", "Double"]:
                summarize_by = "sum"
            elif col['data_type'] == "DateTime":
                summarize_by = "sum"

            unique_bim_columns[cleaned_column_name] = {
                "name": col['remote_name'],
                "dataType": col['data_type'], # Use data_type from parsed_tables_info input
                "sourceColumn": col['remote_name'], # Use remote_name from parsed_tables_info input
                "summarizeBy": summarize_by,
                "isHidden": False,
                "displayFolder": "Columns"
            }

        # Convert the dictionary values back to a list for the 'columns' array in model.bim
        bim_columns = list(unique_bim_columns.values())
        # --- END REINSTATED LOGIC ---


        m_expression = f'let Source = Sql.Database("{db_server_address}", "{db_database_name}"),dbo_{sanitize_name(db_item_name)} = Source{{[Schema="{db_schema}",Item="{db_item_name}"]}}[Data] in dbo_{sanitize_name(db_item_name)}'

        bim_tables.append({
            "name": table_name_friendly,
            "columns": bim_columns,
            "partitions": [
                {
                    "name": f"{table_name_friendly}_Partition",
                    "source": {
                        "type": "m",
                        "expression": m_expression
                    },
                    "mode": "import"
                }
            ]
        })

    bim_data_sources = []
    for conn_key, details in unique_data_source_connections.items():
        bim_data_sources.append({
            "name": details['bim_name'],
            "type": "structured",
            "connectionDetails": {
                "protocol": "tds",
                "address": {
                    "server": details['server'],
                    "database": details['database']
                }
            },
            "credential": {
                "AuthenticationKind": "UsernamePassword",
                "Username": details['username'],
                "Password": details['password'],
                "PrivacySetting": "Organizational",
                "EncryptedConnection": 1
            }
        })

    model_bim_content = {
        "name": DATASET_NAME,
        "id": semantic_model_logical_id,
        "compatibilityLevel": 1604,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyDataSourceOptions": 1
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": bim_tables,
            "relationships": [],
            "dataSources": bim_data_sources
        }
    }
    model_bim_content['model']['relationships'].extend(parsed_relationships)
    return model_bim_content

def generate_pbip_files(parsed_tables_info, unique_data_source_connections, parsed_relationships, data_colors, report_dir, semantic_model_dir, base_file_name):

    main_pbip_content = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": f"{base_file_name}.Report"
                }
            }
        ],
        "settings": {}
    }



    
    main_pbip_path = os.path.join(FINAL_PBIP_FOLDER_PATH, f'{base_file_name}.pbip')
    write_json_file(main_pbip_path, main_pbip_content)


    # root_platform_content = {
    #     "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platform.json",
    #     "platform": "powerbi",
    #     "artifact": {
    #         "report": {
    #             "displayName": base_file_name,
    #             "path": f"{base_file_name}.Report"
    #         },
    #         "dataset": {
    #             "displayName": DATASET_NAME,
    #             "path": f"{base_file_name}.SemanticModel"
    #         }
    #     }
    # }
    # write_json_file(os.path.join(FINAL_PBIP_FOLDER_PATH, 'platform.json'), root_platform_content)
    # print(f"[DEBUG] Created root platform.json: {os.path.join(FINAL_PBIP_FOLDER_PATH, 'platform.json')}")

    # --- Semantic Model Files ---
    semantic_model_logical_id = str(uuid.uuid4())

    semantic_model_platform_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "Dataset"
        },
        "config": {
            "version": "2.0",
            "logicalId": semantic_model_logical_id
        }
    }
    write_json_file(os.path.join(semantic_model_dir, '.platform'), semantic_model_platform_content)
    print(f"[DEBUG] Created .platform file for Semantic Model: {os.path.join(semantic_model_dir, '.platform')}")

    # definition.pbism for SemanticModel (NOW POINTS DIRECTLY TO model.bim)
    semantic_model_pbism_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0"
    }
    write_json_file(os.path.join(semantic_model_dir, 'definition.pbism'), semantic_model_pbism_content)
    print(f"[DEBUG] Created definition.pbism for Semantic Model: {os.path.join(semantic_model_dir, 'definition.pbism')}")

    # --- Generate model.bim ---
    model_bim_path = os.path.join(semantic_model_dir, 'model.bim') # model.bim is directly in SemanticModel folder
    model_bim_content = generate_model_bim_content(parsed_tables_info,unique_data_source_connections,parsed_relationships,semantic_model_logical_id)
    write_json_file(model_bim_path, model_bim_content)
    print(f"[DEBUG] Created model.bim: {model_bim_path}")

    # --- TMDL Files (created as placeholders, but model.bim is the primary definition) ---
    semantic_model_definition_dir = os.path.join(semantic_model_dir, 'definition')
    # write_tmdl_file(os.path.join(semantic_model_definition_dir, 'database.tmdl'), generate_tmdl_database_content(DATASET_NAME, unique_data_source_connections))
    # write_tmdl_file(os.path.join(semantic_model_definition_dir, 'model.tmdl'), generate_tmdl_model_content(DATASET_NAME, []))
    # write_tmdl_file(os.path.join(semantic_model_definition_dir, 'relationships.tmdl'), generate_tmdl_relationships_content([]))
    # write_tmdl_file(os.path.join(semantic_model_definition_dir, 'cultures', 'en-US.tmdl'), generate_tmdl_culture_content())
    
    # # Create table-specific TMDL files as placeholders
    # for table_data in parsed_tables_info:
    #     table_name_sanitized = sanitize_name(table_data['table_name'])
    #     write_tmdl_file(os.path.join(semantic_model_definition_dir, 'tables', f'{table_name_sanitized}.tmdl'), 
    #                     generate_tmdl_table_content(table_data, table_data['columns']))


    # --- Report Files ---
    report_logical_id = str(uuid.uuid4())

    definition_pbir_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {
            "byPath": {
                "path": f"../{base_file_name}.SemanticModel"
            }
        }
    }
    write_json_file(os.path.join(report_dir, 'definition.pbir'), definition_pbir_content)
    print(f"[DEBUG] Created definition.pbir for Report: {os.path.join(report_dir, 'definition.pbir')}")

    report_platform_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "Report"
        },
        "config": {
            "version": "2.0",
            "logicalId": report_logical_id
        }
    }
    write_json_file(os.path.join(report_dir, '.platform'), report_platform_content)
    print(f"[DEBUG] Created .platform file for Report: {os.path.join(report_dir, '.platform')}")

    local_settings_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/localSettings/1.0.0/schema.json",
        "securityBindingsSignature": "AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAnqMi0IJRqk6wW9tWf/mSlgAAAAACAAAAAAADZgAAwAAAABAAAACjnr2AZzdlBK4GQBbvSMZoAAAAAASAAACgAAAAEAAAAP2nnn7yP1C2pzMvUhcWdq9oAAAAUkQwUbeS/ARBpHT4Sc9i46AS5l4uMnmIbodwMe/JBFaZvIxo9Onse4rVDLblAL1bldIUCN5VUcSrlmEO2tavzZsDHLE/A9v21zCCWKMdG/JZqAMR1/TVSD+Tys8mIA+I8BNOxlXrKosUAAAA0HmkkIASwY1jReu54QuRizObAvc="
    }
    write_json_file(os.path.join(report_dir, '.pbi', 'localSettings.json'), local_settings_content)
    print(f"[DEBUG] Created localSettings.json for Report: {os.path.join(report_dir, '.pbi', 'localSettings.json')}")

    base_theme_content = {
        "name": "CY24SU10",
        "dataColors": data_colors,
        "foreground": "#252423",
        "foregroundNeutralSecondary": "#605E5C",
        "foregroundNeutralTertiary": "#B3B0AD",
        "background": "#FFFFFF",
        "backgroundLight": "#F3F2F1",
        "backgroundNeutral": "#C8C6C4",
        "tableAccent": "#118DFF",
        "good": "#1AAB40",
        "neutral": "#D9B300",
        "bad": "#D64554",
        "maximum": "#118DFF",
        "center": "#D9B300",
        "minimum": "#DEEFFF",
        "null": "#FF7F48",
        "hyperlink": "#0078d4",
        "visitedHyperlink": "#0078d4",
        "textClasses": {
            "callout": {"fontSize": 45, "fontFace": "DIN", "color": "#252423"},
            "title": {"fontSize": 12, "fontFace": "DIN", "color": "#252423"},
            "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#252423"},
            "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#252423"}
        },
        "visualStyles": {
            "*": {
                "*": {
                    "*": [{"wordWrap": True}],
                    "line": [{"transparency": 0}],
                    "outline": [{"transparency": 0}],
                    "plotArea": [{"transparency": 0}],
                    "categoryAxis": [{"showAxisTitle": True, "gridlineStyle": "dotted", "concatenateLabels": False}],
                    "valueAxis": [{"showAxisTitle": True, "gridlineStyle": "dotted"}],
                    "y2Axis": [{"show": True}],
                    "title": [{"titleWrap": True}],
                    "lineStyles": [{"strokeWidth": 3}],
                    "wordWrap": [{"show": True}],
                    "background": [{"show": True, "transparency": 0}],
                    "border": [{"width": 1}],
                    "outspacePane": {
                        "backgroundColor": {"solid": {"color": "#ffffff"}},
                        "transparency": 0,
                        "border": True,
                        "borderColor": {"solid": {"color": "#B3B0AD"}}
                    },
                    "filterCard": [
                        {"$id": "Applied", "transparency": 0, "foregroundColor": {"solid": {"color": "#252423"}}, "border": True},
                        {"$id": "Available", "transparency": 0, "foregroundColor": {"solid": {"color": "#252423"}}, "border": True}
                    ]
                }
            },
            "page": {
                "*": {
                    "outspace": {"color": {"solid": {"color": "#FFFFFF"}}},
                    "background": [{"transparency": 100}]
                }
            }
        }
    }
    write_json_file(os.path.join(report_dir, 'StaticResources', 'SharedResources', 'BaseThemes', 'CY24SU10.json'), base_theme_content)
    print(f"[DEBUG] Created baseTheme.json: {os.path.join(report_dir, 'StaticResources', 'SharedResources', 'BaseThemes', 'CY24SU10.json')}")

    ## TODO: integrate report.json
    report_json_content = convert_twb(TWB_FILE_PATH)
    write_json_file(os.path.join(report_dir, 'report.json'), report_json_content)
    print(f"[DEBUG] Created report.json: {os.path.join(report_dir, 'report.json')}")

def main():
    print(f"\n[DEBUG - main] Script execution started.")
    print(f"[DEBUG - main] TWB_FILE_PATH: {TWB_FILE_PATH}")
    print(f"[DEBUG - main] base_file_name: {base_file_name}")
    print(f"[DEBUG - main] OUTPUT_PBIP_ROOT_DIR: {OUTPUT_PBIP_ROOT_DIR}")
    print(f"[DEBUG - main] FINAL_PBIP_FOLDER_PATH: {FINAL_PBIP_FOLDER_PATH}")


    print(f"Starting conversion of {TWB_FILE_PATH} to PBIP format...")

    print(f"[DEBUG - main] Calling create_pbip_folders...")
    report_dir, semantic_model_dir = create_pbip_folders(FINAL_PBIP_FOLDER_PATH, base_file_name)
    print(f"[DEBUG - main] create_pbip_folders returned. Main PBIP folder should now exist.")


    print("Parsing TWB file for tables and report pages...")
    # parse_twb now returns tables_info and unique_data_source_connections
    parsed_tables_info, unique_data_source_connections, parsed_relationships, report_pages, data_colors = parse_twb(TWB_FILE_PATH)
    # print("TWB parsing complete. Parsed Tables Info:", json.dumps(parsed_tables_info, indent=2))
    # print("Unique Data Source Connections:", json.dumps(unique_data_source_connections, indent=2))

    if not parsed_tables_info:
        print("[CRITICAL] No tables were parsed from the TWB file. The PBIP semantic model will be empty or invalid.")
        return # Exit if no tables are found

    if not report_pages:
        print("Warning: No dashboards/worksheets found or recognized in the TWB for conversion to report pages.")

    print("Generating PBIP files...")
    # Pass parsed_tables_info and unique_data_source_connections to generate_pbip_files
    generate_pbip_files(parsed_tables_info, unique_data_source_connections, parsed_relationships, data_colors, report_dir, semantic_model_dir, base_file_name)
    print("PBIP file generation complete.")

    print(f"\nConversion finished! Open the '{FINAL_PBIP_FOLDER_PATH}' folder in Power BI Desktop.")

if __name__ == "__main__":
    main()