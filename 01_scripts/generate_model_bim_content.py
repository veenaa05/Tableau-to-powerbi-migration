import json
import os
import uuid
import glob
from parse_twb_structure import (
    parse_twb_file,
    export_hyper_to_csv,
    sanitize_name,
    clean_column_display_name,
    map_tableau_type_to_pb_type
)

def generate_model_bim_content(
    parsed_data: dict,
    twb_file_path: str,
    exported_csv_path: str = None,
    semantic_model_logical_id: str = None
) -> dict:
    tables_info = parsed_data['tables_info']
    columns_by_table = parsed_data['columns_by_table']
    measures_by_table = parsed_data['measures_by_table']
    connections = parsed_data['connections']
    relationships = parsed_data['relationships']
    calculated_columns = parsed_data['calculated_columns']
    
    base_file_name = os.path.splitext(os.path.basename(twb_file_path))[0]
    DATASET_NAME = f"{base_file_name} Dataset"

    if semantic_model_logical_id is None:
        semantic_model_logical_id = str(uuid.uuid4())

    bim_tables = []
    bim_data_sources = []
    
    # Process connections to determine data sources
    for conn_key, details in connections.items():
        if details.get("type") == "database":
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

    # Consolidate tables to avoid duplicates (e.g., "Extract" and "data.csv")
    unique_tables = {}
    for tbl_name, tbl_info in tables_info.items():
        # Use the connection key as a unique identifier for the underlying data source
        conn_key = tbl_info['connection_key']
        # If we haven't seen this connection before, add the table
        if conn_key not in unique_tables:
            unique_tables[conn_key] = tbl_name
        # If we have, prefer a more descriptive name if available (e.g., the CSV file name)
        else:
            current_name = unique_tables[conn_key]
            if current_name == "Extract" and tbl_name != "Extract":
                unique_tables[conn_key] = tbl_name

    for conn_key, tbl_name in unique_tables.items():
        tbl_info = tables_info[tbl_name]
        bim_columns = []
        bim_measures = []
        bim_calculated_columns = []
        
        # --- Truly Dynamic M-Code Generation ---
        # The M-code is now generated purely based on the connection type.
        # It does not contain any hard-coded data transformations.
        conn_details = connections[conn_key]
        
        if conn_details.get("type") == "hyper" or conn_details.get("database", "").startswith("federated."):
            # FIX: Use the hard-coded data.csv name to ensure the file path is correct
            m_expression = (
                f'let\n'
                f'    Source = Csv.Document(File.Contents("data.csv"),[Delimiter=",", Columns=null, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
                f'    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n'
                f'in\n'
                f'    #"Promoted Headers"'
            )
        else: # Standard database connection
            db_server_address = conn_details.get('server', '')
            db_database_name = conn_details.get('database', '')
            db_schema = tbl_info.get('db_schema', 'dbo')
            db_item_name = tbl_info.get('db_item_name', tbl_name)
            m_expression = (
                f'let Source = Sql.Database("{db_server_address}", "{db_database_name}"), '
                f'dbo_{sanitize_name(db_item_name)} = Source{{[Schema="{db_schema}",Item="{db_item_name}"]}}[Data] '
                f'in dbo_{sanitize_name(db_item_name)}'
            )
        
        # Columns (dynamically built from parsed data)
        seen_cols = set()
        for col in columns_by_table.get(tbl_name, []):
            col_name = clean_column_display_name(col['name'])
            if col_name in seen_cols:
                continue
            seen_cols.add(col_name)
            
            bim_columns.append({
                "name": col_name,
                "dataType": col['data_type'],
                "sourceColumn": col['remote_name'],
                "summarizeBy": "sum" if col['data_type'] in ("Int64", "Double") else "none",
                "isHidden": False,
                "annotations": [
                    {"name": "PBI_NavigationStepName", "value": "Navigation"},
                    {"name": "PBI_DisplayFolder", "value": "Data"}
                ],
                "lineageTag": str(uuid.uuid4())
            })
            
        # Measures (dynamically built from parsed data)
        for m in measures_by_table.get(tbl_name, []):
            bim_measures.append({
                "name": clean_column_display_name(m['name']),
                "expression": m['expression'],
                "dataType": "Double",
                "displayFolder": "Measures"
            })
            
        # Calculated columns (dynamically built from parsed data)
        for calc in calculated_columns:
            if calc['table'] == tbl_name:
                bim_calculated_columns.append({
                    "name": clean_column_display_name(calc['column_name']),
                    "expression": calc['formula'],
                    "dataType": map_tableau_type_to_pb_type(calc['datatype']),
                    "isHidden": False
                })

        bim_table = {
            "name": tbl_name,
            "lineageTag": str(uuid.uuid4()),
            "annotations": [
                {
                    "name": "PBI_QueryMetadata",
                    "value": f'{{"QueryId":"{str(uuid.uuid4())}"}}'
                }
            ],
            "columns": bim_columns,
            "partitions": [
                {
                    "name": f"{tbl_name}_Partition",
                    "source": {"type": "m", "expression": m_expression},
                    "mode": "import"
                }
            ],
        }
        
        if bim_measures:
            bim_table["measures"] = bim_measures
        if bim_calculated_columns:
            bim_table["calculatedColumns"] = bim_calculated_columns

        bim_tables.append(bim_table)

    # Build relationships (dynamically built from parsed data)
    bim_relationships = []
    seen_rels = set()
    for rel in relationships:
        from_table = rel.get('operand_2', {}).get('table')
        from_column = rel.get('operand_2', {}).get('column')
        to_table = rel.get('operand_1', {}).get('table')
        to_column = rel.get('operand_1', {}).get('column')
        rel_name = f"Rel_{sanitize_name(from_table)}_{sanitize_name(from_column)}_to_{sanitize_name(to_table)}_{sanitize_name(to_column)}"
        if rel_name not in seen_rels:
            seen_rels.add(rel_name)
            bim_relationships.append({
                "name": rel_name,
                "fromTable": from_table,
                "fromColumn": from_column,
                "toTable": to_table,
                "toColumn": to_column,
                "isActive": True
            })

    model_bim_content = {
        "name": DATASET_NAME,
        "id": semantic_model_logical_id,
        "compatibilityLevel": 1604,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {"legacyDataSourceOptions": 1},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": bim_tables,
            "relationships": bim_relationships,
            "dataSources": bim_data_sources,
        }
    }
    return model_bim_content

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tableau_files_dir = os.path.join(current_dir, "..", "02_tableau_files")
    OUTPUT_PBIP_ROOT_DIR = os.path.join(current_dir, "..", "03_converted_pbips")

    os.makedirs(OUTPUT_PBIP_ROOT_DIR, exist_ok=True)

    twb_files = glob.glob(os.path.join(tableau_files_dir, "*.twb"))

    if not twb_files:
        print(f"No .twb files found in {tableau_files_dir}")
    else:
        for twb_file_path in twb_files:
            try:
                twb_dir = os.path.dirname(twb_file_path)
                twb_name = os.path.splitext(os.path.basename(twb_file_path))[0]
                
                hyper_file_path = os.path.join(twb_dir, f"{twb_name}.hyper")
                
                pbip_project_path = os.path.join(OUTPUT_PBIP_ROOT_DIR, f"{twb_name}.pbip")
                semantic_model_path = os.path.join(pbip_project_path, f"{twb_name}.SemanticModel")
                os.makedirs(semantic_model_path, exist_ok=True)
                
                exported_csv_path = None
                if os.path.exists(hyper_file_path):
                    exported_csv_path = os.path.join(semantic_model_path, "data.csv")
                    print('export_csv_path---------', export_hyper_to_csv)
                    success = export_hyper_to_csv(hyper_file_path, exported_csv_path)
                    if not success:
                        exported_csv_path = None

                parsed_data = parse_twb_file(twb_file_path, hyper_file_path)
                
                logical_id = str(uuid.uuid4())
                model_bim_content = generate_model_bim_content(
                    parsed_data=parsed_data,
                    twb_file_path=twb_file_path,
                    exported_csv_path=exported_csv_path,
                    semantic_model_logical_id=logical_id
                )
                
                output_bim_file_path = os.path.join(semantic_model_path, "model.bim")
                with open(output_bim_file_path, "w", encoding="utf-8") as f:
                    json.dump(model_bim_content, f, indent=4)
                
                print(f"✅ Generated {output_bim_file_path}")
            except Exception as e:
                print(f"❌ Error processing {os.path.basename(twb_file_path)}: {e}")