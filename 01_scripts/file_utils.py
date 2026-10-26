from pathlib import Path
import glob
from typing import List
import xml.etree.ElementTree as ET
import zipfile
import os
import uuid
import shutil
import json 

def extract_twbx(path_to_twbx_file: str, path_to_output_folder: str) -> None:
    with zipfile.ZipFile(path_to_twbx_file, 'r') as zip_ref:
        zip_ref.extractall(path_to_output_folder)
    print(f"Extracted {path_to_twbx_file} to {path_to_output_folder}")
    
def scan_folder(TABLEAU_FILES_FOLDER: Path) -> tuple[list[str],list[str],list[str]]:
    TWBX_FILES = glob.glob(str(TABLEAU_FILES_FOLDER / '*.twbx'))
    TWB_FILES = glob.glob(str(TABLEAU_FILES_FOLDER / '*.twb'))
    ALL_FILES = glob.glob(str(TABLEAU_FILES_FOLDER / '*'))
    return TWBX_FILES, TWB_FILES, ALL_FILES

def validate_twb_tags(twb_path: str ,required_tags:List[str] =None) -> bool:
    if required_tags is None:
        required_tags = ['datasource', 'worksheet', 'dashboard', 'zone']
    try:
        tree = ET.parse(twb_path)
        root = tree.getroot()
        namespace = ''
        if '}' in root.tag:
            namespace = root.tag.split('}')[0] + '}'
        found_tags = {tag: False for tag in required_tags}
        for tag in required_tags:
            elements = root.findall(f".//{namespace}{tag}")
            if elements:
                found_tags[tag] = True
        missing_tags = [tag for tag, present in found_tags.items() if not present]
        if missing_tags:
            print(f"[Validation Failed] Missing tag(s): {', '.join(missing_tags)}")
            return False
        print("[Validation Passed] All required tags are present.")
        return True
    except ET.ParseError as e:
        print(f"[Parse Error] Invalid XML in TWB file: {e}")
        return False
    except FileNotFoundError:
        print(f"[Error] File not found: {twb_path}")
        return False
    except Exception as e:
        print(f"[Error] Unexpected error: {e}")
        return False
    
def create_pbip_folders(pbip_full_path: str, base_file_name: str):
    """Creates the standard PBIP folder structure within the specified pbip_full_path."""

    if os.path.exists(pbip_full_path):
        try:
            shutil.rmtree(pbip_full_path)
        except PermissionError as e:
            raise 
        except Exception as e:
            raise 

    try:
        os.makedirs(pbip_full_path)
    except Exception as e:
        raise 

    # Define sub-directories relative to the pbip_full_path
    report_folder_name = f'{base_file_name}.Report'
    semantic_model_folder_name = f'{base_file_name}.SemanticModel'

    report_dir = os.path.join(pbip_full_path, report_folder_name)
    semantic_model_dir = os.path.join(pbip_full_path, semantic_model_folder_name)

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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Created/Updated JSON file: {path}")
    
def generate_pbip_files(
    output_pbip_root_dir: str,
    report_dir : str, 
    semantic_model_dir : str, 
    base_file_name : str, 
    report_json_content : dict, 
    model_bim_content : dict, 
    semantic_model_logical_id : str):

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



    main_pbip_path = os.path.join(output_pbip_root_dir, f'{base_file_name}.pbip')
    write_json_file(main_pbip_path, main_pbip_content)

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
    write_json_file(model_bim_path, model_bim_content)
    print(f"[DEBUG] Created model.bim: {model_bim_path}")

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
        "dataColors": ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF"],
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
    write_json_file(os.path.join(report_dir, 'report.json'), report_json_content)
    print(f"[DEBUG] Created report.json: {os.path.join(report_dir, 'report.json')}")