from pymongo import MongoClient, database

def setup_database_connection(config: dict[str, str]) -> MongoClient:
    DATABASE = config["DATABASE"]
    USER_NAME = config["USER_NAME"]
    PASSWORD = config["PASSWORD"]
    SERVER_IP = config["SERVER_IP"]
    SERVER_PORT = config["SERVER_PORT"]
    mongo_uri = f"mongodb://{SERVER_IP}:{SERVER_PORT}/{DATABASE}"
    print("==",mongo_uri)
    mongo_client = MongoClient(
        mongo_uri,
        username = USER_NAME,
        password = PASSWORD
    )
    return mongo_client

def get_mapping(mongo_database: database.Database, mapping_type: str, key: str, default_value : str | None = None) -> str | None:
    """
    Retrieve a mapping from the specified MongoDB database based on the provided mapping type and key.

    This function queries the "MAPPING_TABLE" collection in the given MongoDB database to find a document 
    that matches the specified mapping type and key. It returns the corresponding Power BI name and 
    function ID, or a default value if no matching document is found. If the mapping type is "AGGREGATION", 
    it returns both the Power BI name and function ID as a tuple. For other mapping types, it returns only 
    the Power BI name.

    Args:
        mongo_database (database.Database): The MongoDB database object containing the mapping table.
        mapping_type (str): The type of mapping to look for (e.g., "AGGREGATION").
        key (str): The identifier for the specific mapping entry to retrieve.
        default_value (str | None, optional): The value to return if no matching mapping is found. 
                                              Defaults to None.

    Returns:
        str | None: The Power BI name corresponding to the mapping or the default_value if no mapping 
                    is found. If the mapping_type is "AGGREGATION", returns a tuple of (Power BI name, 
                    Power BI function ID).
    """
    mapping_table = mongo_database["MAPPING_TABLE"]
    result = mapping_table.find_one(
        {
            "MAPPING_TYPE": mapping_type,
            "TABLEAU_NAME": key 
        }
    )
    if not result:
        # mapping not found
        return default_value
    if mapping_type.upper() == "AGGREGATION":
        return (result.get("POWERBI_NAME"), result.get("POWERBI_FUNCTION_ID"))
    return result.get("POWERBI_NAME")

def add_mapping(mongo_database: database.Database, mapping_type: str, tableau_name: str, powerbi_name: str, powerbi_function_id: str | None = None):
    """
    Add a new mapping entry to the specified MongoDB database's mapping table.

    This function inserts a new document into the "MAPPING_TABLE" collection of the given MongoDB database. 
    The document will contain the provided mapping type, Tableau name, Power BI name, and optionally the 
    Power BI function ID if the mapping type is "AGGREGATION".

    Args:
        mongo_database (database.Database): The MongoDB database object where the mapping table is stored.
        mapping_type (str): The type of mapping being added (e.g., "AGGREGATION").
        tableau_name (str): The name from Tableau to be mapped.
        powerbi_name (str): The name in Power BI that corresponds to the Tableau name.
        powerbi_function_id (str | None, optional): The Power BI function ID associated with the mapping. 
                                                    This is required only if the mapping type is "AGGREGATION".

    Returns:
        tuple: A tuple containing two elements:
            - bool: Acknowledgment status of the insert operation (True if successful, False otherwise).
            - ObjectId | None: The ID of the newly inserted document if the operation was successful; 
                               otherwise, None if an error occurred.
    """
    mapping_table = mongo_database["MAPPING_TABLE"]
    try:
        result = mapping_table.insert_one(
            {
                "MAPPING_TYPE": mapping_type,
                "TABLEAU_NAME": tableau_name,
                "POWERBI_NAME": powerbi_name,
                "POWERBI_FUNCTION_ID": powerbi_function_id if powerbi_function_id and mapping_type.upper() == "AGGREGATION" else None
            }
        )
        return result.acknowledged, result.inserted_id
    except Exception as e:
        return None, None
    
def delete_mapping(mongo_database: database.Database, mapping_type: str, tableau_name: str):
    """
    Delete a mapping entry from the specified MongoDB database's mapping table.

    This function attempts to remove a document from the "MAPPING_TABLE" collection in the provided 
    MongoDB database that matches the specified mapping type and Tableau name. 

    Args:
        mongo_database (database.Database): The MongoDB database object containing the mapping table.
        mapping_type (str): The type of mapping to be deleted (e.g., "AGGREGATION").
        tableau_name (str): The name from Tableau that corresponds to the mapping entry to delete.

    Returns:
        bool | None: 
            - True if the deletion was acknowledged and successful.
            - False if no documents matched the deletion criteria.
            - None if an error occurred during the deletion process.
    """
    mapping_table = mongo_database["MAPPING_TABLE"]
    try:
        result = mapping_table.delete_one(
            {
                "MAPPING_TYPE": mapping_type,
                "TABLEAU_NAME": tableau_name
            }
        )
        return result.acknowledged
    except Exception as e:
        return None
    
def update_mapping(mongo_database: database.Database, tableau_name: str, field_to_update: str, update_value: str):
    """
    Update a specific field of a mapping entry in the specified MongoDB database's mapping table.

    This function modifies an existing document in the "MAPPING_TABLE" collection of the provided 
    MongoDB database. It updates the specified field with the new value for the document that matches 
    the given Tableau name. 

    Args:
        mongo_database (database.Database): The MongoDB database object containing the mapping table.
        tableau_name (str): The name from Tableau whose mapping entry should be updated.
        field_to_update (str): The name of the field that needs to be updated (e.g., "POWERBI_NAME", "POWERBI_FUNCTION_ID").
        update_value (str): The new value to set for the specified field.

    Returns:
        bool | None: 
            - True if the update was acknowledged and successful.
            - False if no documents matched the update criteria or if the update did not modify any documents.
            - None if an error occurred during the update process.
    """
    mapping_table = mongo_database["MAPPING_TABLE"]
    try:
        result = mapping_table.update_one(
            {"TABLEAU_NAME": tableau_name},
            {"$set": {field_to_update: update_value}}
        )
        return result.acknowledged and result.modified_count > 0
    except Exception as e:
        return None

def log_to_error_collection(error_message: str, error_collection: database.Collection):
    ...

if __name__ == "__main__":
    import json
    import os
    
    with open(os.path.join(os.path.dirname(__file__), "run_config.json")) as config_file:
        config = json.load(config_file)
    mongoclient = setup_database_connection(config)
    print(get_mapping(mongoclient[config['DATABASE']], 'AGGREGATION', 'cnt12'))
