import os
from datetime import datetime
import json
import glob
from pathlib import Path
from file_utils import scan_folder, extract_twbx, validate_twb_tags, create_pbip_folders, generate_pbip_files
from log_config import *

from parse_twb_structure import parse_twb_file
from generate_model_bim_content import *
from generate_report_json import *
from database_utils import *



# Logging setup
working_directory = Path(__file__).parent
logger = configure_logging(
    log_file_path = str(working_directory / "logs" / "run_log.log")
)

logger.info("Starting run, reading config...")
with open(working_directory / 'run_config.json') as config_file:
    config = json.load(config_file)
    
logger.info("Config loaded successfuly. Setting up database connection...")

# DATABASE CONFIG     
mongo_client = setup_database_connection(config)
DATABASE = config["DATABASE"]

try:
    server_info = mongo_client.server_info()
    logger.info(f"Database connection established successfully to database: {DATABASE}.")
    logger.debug(f"Server info - {server_info}")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")

UAT_TBI_DASHBOARD = mongo_client[DATABASE]
TABLEAU_FILES_FOLDER = working_directory.parent / '02_tableau_files'
OUTPUT_PBIP_FOLDER = working_directory.parent / '03_converted_pbips'
logger.info(f"Running folder scan for the folder {str(TABLEAU_FILES_FOLDER)}...")
TWBX_FILES, TWB_FILES, ALL_FILES = scan_folder(TABLEAU_FILES_FOLDER)
OTHER_FILES = [file for file in ALL_FILES if not (file.lower().endswith('.twb') or file.lower().endswith('.twbx'))]

logger.info(f"Scan complete! Scan found: {len(TWBX_FILES)} TWBX file(s), {len(TWB_FILES)} TWB file(s), and {len(OTHER_FILES)} other file(s) for a total of {len(ALL_FILES)} file(s).")
logger.debug(f"TWB_FILES -- {TWB_FILES}")
logger.debug(f"TWBX_FILES -- {TWBX_FILES}")
logger.debug(f"Other files -- {OTHER_FILES}")

try:
    RUN_LOGS = UAT_TBI_DASHBOARD["RUN_LOGS"]
except Exception as e:
    logger.error(f"Unkown error while accessing collection: {e}")

result = RUN_LOGS.insert_one(
    {
       "START_TIME": datetime.now(),
       "TOTAL_FILES": len(ALL_FILES),
       "NUM_TWB_FILES": len(TWB_FILES),
       "TWB_FILES": TWB_FILES,
       "NUM_TWBX_FILES": len(TWBX_FILES),
       "TWBX_FILES": TWBX_FILES,
       "NUM_OTHER_FILES": len(OTHER_FILES),
       "OTHER_FILES": OTHER_FILES
    }
)
RUN_ID = result.inserted_id
logger.info(f"Run with Run ID {RUN_ID} successfully created in RUN_LOGS.")

if TWBX_FILES:
    logger.info("Unpacking TWBX files to TWB files...")
    for i,twbx_path in enumerate(TWBX_FILES):
        message = f"Processing file {i+1} of {len(TWBX_FILES)} -- {twbx_path} ... "
        logger.info(message)
        try:
            extract_twbx(
                path_to_twbx_file = twbx_path,
                path_to_output_folder = str(TABLEAU_FILES_FOLDER)
            )
        except Exception as e:
            logger.error(f"Unknown error while extracting TWB from {twbx_path} - {e}")

# since TWBX files have been converted, TWB files need to be reglobbed
TWB_FILES = glob.glob(str(TABLEAU_FILES_FOLDER / '*.twb'))

try:
    FILE_COLLECTION = UAT_TBI_DASHBOARD['FILE_COLLECTION']
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    
for twb_file_path in TWB_FILES:
    file_result = FILE_COLLECTION.insert_one(
        {
            "RUN ID": RUN_ID,
            "FILE_PATH": twb_file_path,
            "ERRORS": [],
            "REPROCESS_COUNT": 0
        }
    )
    FILE_ID = file_result.inserted_id
    print("fileID------------", FILE_ID)


        # --- THIS IS THE FULL, CORRECTED LOGIC ---
    exported_csv_path = None
    hyper_file_path = None
    
    # We first parse the TWB file to find the connection name
    # We call it here so we have the connection info
    try:
        parsed_data = parse_twb_file(twb_file_path)
    except Exception as e:
        logger.error(f"Unknown error while trying to parse file {twb_file_path}: {e}")
        # ... (rest of error handling) ...
        continue

    # Find the hyper file based on parsed data or by glob search
    base_dir = os.path.dirname(twb_file_path)
    if 'connections' in parsed_data and parsed_data['connections']:
        for conn in parsed_data['connections']:
            if 'filename' in conn and conn['filename'].lower().endswith('.hyper'):
                conn_file_name = os.path.basename(conn['filename'])
                potential_path = os.path.join(base_dir, conn_file_name)
                if os.path.exists(potential_path):
                    hyper_file_path = potential_path
                    logger.info(f"Found Hyper file from TWB connection: {hyper_file_path}")
                    break
    
    if not hyper_file_path:
        all_hyper_files_in_dir = glob.glob(os.path.join(base_dir, "*.hyper"))
        if all_hyper_files_in_dir:
            hyper_file_path = all_hyper_files_in_dir[0]
            logger.info(f"Found Hyper file by glob search: {hyper_file_path}")

    # Now, try to export the data if a hyper file was found
    base_file_name = os.path.splitext(os.path.basename(twb_file_path))[0]
    if hyper_file_path:
        output_dir = os.path.join(
            OUTPUT_PBIP_FOLDER,
            f"{base_file_name}.pbip",
            f"{base_file_name}.SemanticModel"
        )
        os.makedirs(output_dir, exist_ok=True)
        exported_csv_path = os.path.join(output_dir, "data.csv")

        logger.info(f"Attempting to export {hyper_file_path} to CSV at {exported_csv_path}...")
        
        from generate_model_bim_content import export_hyper_to_csv # We should be explicit here
        success = export_hyper_to_csv(hyper_file_path, exported_csv_path)
        
        if success:
            logger.info("CSV export completed successfully.")
        else:
            logger.error("CSV export failed.")

    try:
        valid_tags = validate_twb_tags(twb_file_path)
    except Exception as e:
        print("logging all issue---============")
        logger.error(f"Unknown error while trying to validate file {twb_file_path}: {e}")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Unknown error while trying to validate: {e}"
                }
            }
        )
        continue
    
    FILE_COLLECTION.update_one(
        filter = {
            "_id": FILE_ID
        },
        update = {
            "$set": {
                "VALID_TAGS": valid_tags
            }
        }
    )
    
    if not valid_tags:
        logger.error(f"Error - invalid tags for file {twb_file_path}.")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Invalid tags"
                }
            }
        )
        continue
    
    # CORRECTED LOGIC: Call the main parsing function once
    # and pass its output to the next steps.
    try:
        parsed_data = parse_twb_file(twb_file_path)
        
        # print("+++====",parsed_data['calculated_columns'])
        # print("="*40)
    except Exception as e:
        logger.error(f"Unknown error while trying to parse file {twb_file_path}: {e}")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Unknown error while trying to parse: {e}"
                }
            }
        )
        continue
    
    try:
        # CORRECTED: Passing the parsed_data dictionary and file path
        semantic_model_logical_id = str(uuid.uuid4())
        model_bim_content = generate_model_bim_content(parsed_data, twb_file_path, semantic_model_logical_id)
    except Exception as e:
        logger.error(f"Unknown error while trying to generate model bim content for file {twb_file_path}: {e}")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Unknown error while trying to generate model bim content: {e}"
                }
            }
        )
        continue
    
    # Note: I am assuming convert_twb still only needs the file path, but you may need to update this function call if it also needs 'parsed_data'
    try:
        report_json_content = generate_report_json(twb_file_path)
    except Exception as e:
        logger.error(f"Unkown error while trying to generate report json content for file {twb_file_path}: {e}")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Unkown error while trying to generate report json content: {e}"
                }
            }
        )
        continue
    
    base_file_name = os.path.splitext(os.path.basename(twb_file_path))[0]
    output_pbip_root_dir = OUTPUT_PBIP_FOLDER / f'{base_file_name}.pbip'
    try:
        report_dir, semantic_model_dir = create_pbip_folders(output_pbip_root_dir, base_file_name)
    except Exception as e:
        logger.error(f"Unknown error while trying to create PBIP folders for file {twb_file_path}: {e}")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Unknown error while trying to create PBIP folders: {e}"
                }
            }
        )
        continue
    try:
        generate_pbip_files(
            output_pbip_root_dir = output_pbip_root_dir,
            report_dir = report_dir,
            semantic_model_dir = semantic_model_dir,
            base_file_name = base_file_name,
            report_json_content = report_json_content,
            model_bim_content = model_bim_content,
            semantic_model_logical_id = semantic_model_logical_id
        )
    except Exception as e:
        logger.error(f"Unknown error while trying to generate PBIP files for file {twb_file_path}: {e}")
        FILE_COLLECTION.update_one(
            filter = {
                "_id": FILE_ID
            },
            update = {
                "$push": {
                    "ERRORS": f"Unknown error while trying to PBIP files: {e}"
                }
            }
        )
        continue