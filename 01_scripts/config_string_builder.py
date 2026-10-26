import json
import os
import xml.etree.ElementTree as ET
import uuid
from utils import  generate_table_aliases
from database_utils import setup_database_connection,get_mapping
from parse_twb_structure import resolve_column,build_meta_map

with open(os.path.join(os.path.dirname(__file__),'run_config.json')) as config_file:
    config = json.load(config_file)
mongoclient = setup_database_connection(config)
class ConfigStringBuilder:
    """
        The `ConfigStringBuilder` class is used to generate Power BI config strings
        for different groups of visuals (column, pie, tree, table, etc). Two visuals
        are considered in the same group if their config strings are mostly the same.
        
        Class variables:
        - **_table_alias_mapping** (dict): A dictionary mapping table names to generated 
        aliases used in select lists inside the config string. 
        - **_aggregation_mapping** (dict[tuple]): A dictionary mapping aggregation names in 
        `table_mapping` to a tuple (Power_BI_Aggregation_Name, Power_BI_Aggregation_Code).
    """
    # _aggregation_mapping: dict[tuple]
    _table_alias_mapping: dict
    
    def __init__(self,table_alias_mapping: dict,**kwargs):
        # self._aggregation_mapping = aggregation_mapping
        self._table_alias_mapping = table_alias_mapping
    
    def generate_column_chart_config(self, sheet_mapper: dict, zone: dict, visual_type: str) -> str:
        select_dict = {}
        unique_table = set()
        projection_category = []
        for column_info in sheet_mapper.get('cols'):
            table_name = column_info.get('table')
            column_name = column_info.get('column')
            unique_table.add(table_name)
            projection_category.append(
                {
                    "queryRef": f"{table_name}.{column_name}", "active": True
                } 
            )
            if column_name not in select_dict:
                if column_info.get('aggregation').lower() != 'none':
                    select_dict[column_name] = {
                        "Aggregation": {
                            "Expression": {
                                "Column": {
                                    "Expression": {
                                        "SourceRef": {
                                            "Source": self._table_alias_mapping.get(table_name)
                                        }
                                    },
                                    "Property": column_name
                                }
                            },
                            "Function": get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=column_info.get('aggregation'),default_value= ('CountNonNull', 5))[1]
                        },
                        "Name": f"{get_mapping(mongoclient[config['DATABASE']], mapping_type='AGGREGATION', key=column_info.get('aggregation'), default_value=('CountNonNull', 5))[0]}({table_name}.{column_name})",
                        "NativeReferenceName": column_name
                    }
                else:
                    select_dict[column_name] = {
                        "Column": {
                            "Expression": {
                                "SourceRef": {
                                    "Source": self._table_alias_mapping.get(table_name)
                                }
                            },
                            "Property": column_name
                        },
                        "Name": f"{table_name}.{column_name}",
                        "NativeReferenceName": column_name
                    }
        
        projection_y = []
        for row_info in sheet_mapper.get('rows'):
            table_name = row_info.get('table')
            unique_table.add(table_name)
            column_name = row_info.get('column')
            if column_name not in select_dict:
                if row_info.get('aggregation').lower() != 'none':
                    select_dict[column_name] = {
                        "Aggregation": {
                            "Expression": {
                                "Column": {
                                    "Expression": {
                                        "SourceRef": {
                                            "Source": self._table_alias_mapping.get(table_name)
                                        }
                                    },
                                    "Property": column_name
                                }
                            },
                            "Function": get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=row_info.get('aggregation'),default_value= ('CountNonNull', 5))[1]
                        },
                        "Name": f"{get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=row_info.get('aggregation'),default_value= ('CountNonNull', 5))[0]}({table_name}.{column_name})",
                        "NativeReferenceName": column_name
                    }
                else:
                    select_dict[column_name] = {
                        "Column": {
                            "Expression": {
                                "SourceRef": {
                                    "Source": self._table_alias_mapping.get(table_name)
                                }
                            },
                            "Property": column_name
                        },
                        "Name": f"{table_name}.{column_name}",
                        "NativeReferenceName": column_name
                    }
            projection_y.append(
                {
                    # TODO: Handle unknown aggregation mappings
                    "queryRef": f"{get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=row_info.get('aggregation'),default_value=('CountNonNull', 5))[0]}({table_name}.{column_name})"
                } 
            )
            
        color_info = sheet_mapper.get('encodings', {}).get('color', [])
        projection_series = []
        if len(color_info) >= 1:
            table_name = color_info[0].get('table')
            column_name = color_info[0].get('column')
            projection_series.append(
                {
                    "queryRef": f"{table_name}.{column_name}"
                }
            )
            if column_name not in select_dict:
                if color_info[0].get('aggregation').lower() != 'none':
                    select_dict[column_name] = {
                        "Aggregation": {
                            "Expression": {
                                "Column": {
                                    "Expression": {
                                        "SourceRef": {
                                            "Source": self._table_alias_mapping.get(table_name)
                                        }
                                    },
                                    "Property": column_name
                                }
                            },
                            "Function": get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=color_info[0].get('aggregation'),default_value= ('CountNonNull', 5))[1]
                        },
                        "Name": f"{get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=color_info[0].get('aggregation'),default_value= ('CountNonNull', 5))[0]}({table_name}.{column_name})",
                        "NativeReferenceName": column_name
                    }
                else:
                    select_dict[column_name] = {
                        "Column": {
                            "Expression": {
                                "SourceRef": {
                                    "Source": self._table_alias_mapping.get(table_name)
                                }
                            },
                            "Property": column_name
                        },
                        "Name": f"{table_name}.{column_name}",
                        "NativeReferenceName": column_name
                    }    
        
        order_by = []
        select = list(select_dict.values())
        added_exprs = set()
        for item in select:
            if "Aggregation" in item:
                expr_json = json.dumps(item["Aggregation"], sort_keys=True)
                if expr_json not in added_exprs:
                    order_by.append({"Direction": 2, "Expression":{"Aggregation": item["Aggregation"]}})
                    added_exprs.add(expr_json)
                    
        conf = {
            "name": uuid.uuid4().hex[:16],
            "layouts": [
                {
                    "id": 0,
                    "position": {
                        "x": zone.get('x'),
                        "y": zone.get('y'),
                        "z": 0,
                        "width": zone.get('w'),
                        "height": zone.get('h'),
                        "tabOrder": 0
                    }
                }
            ],
            "singleVisual": {
                "visualType": visual_type,
                "projections": {
                    "Category" : projection_category,
                    "Y": projection_y,
                    "Series": projection_series
                },
                "prototypeQuery": {
                "Version": 2,
                "From": [{"Name":str(self._table_alias_mapping.get(i)), "Entity": i, "Type": 0} for i in unique_table],
                "Select": select,
                "OrderBy": order_by
                },
                "drillFilterOtherVisuals": True,
                "hasDefaultSort": True,
                "objects": {
                    "labels": [
                        {
                            "properties": {
                                "show": {
                                    "expr": {
                                        "Literal": {
                                            "Value": "true"
                                        }
                                    }
                                }
                            }
                        }
                    ]
                },
                "vcObjects": {
                    "title": [
                        {
                            "properties": {
                                "text": {
                                    "expr": {
                                        "Literal": {
                                            "Value": f"'{sheet_mapper.get('chartTitle')}'"
                                        }
                                    }
                                },
                                "alignment": {
                                    "expr": {
                                        "Literal": {
                                            "Value": "'center'"
                                        }
                                    }
                                }
                            }
                        }
                    ],
                "border": [
                    {
                    "properties": {
                        "show": {
                        "expr": {
                            "Literal": {
                            "Value": "true"
                            }
                        }
                        }
                    }
                    }
                ]
                }
            }
        }
        return json.dumps(conf)
    def generate_pie_chart_config(self, sheet_mapper: dict, zone: dict,VISUAL_TYPE:str) -> str:
        select_dict={}
        unique_table=set()
        try:
            color=sheet_mapper['encodings']['color']
            if len(color) >=1:
                category=[{"queryRef": f"{color[0].get('table')}.{color[0].get('column')}", "active": True}]
                unique_table.add(color[0].get('table'))
                cat_name = category[0]['queryRef']
                if cat_name not in select_dict:
                    select_dict[cat_name] = {
                            "Column": {"Expression": {"SourceRef": {"Source": str(self._table_alias_mapping.get(color[0].get('table')))}}, "Property": color[0].get('column')},
                            "Name": cat_name,
                            "NativeReferenceName": color[0].get('column')
                        }
            else :
                return
        except Exception as e:
            return e
        try:
            texts=sheet_mapper['encodings']['text']
            if len(texts) >=1:
                Y=[{"queryRef": f"{get_mapping(mongoclient[config['DATABASE']],mapping_type='AGGREGATION',key=text.get('aggregation'),default_value=('CountNonNull',5))[0]}({text.get('table')}.{text.get('column')})"} for text in texts if text['aggregation'] != 'none']
                
                for text in texts:
                    unique_table.add(text.get('table'))
                    if text['aggregation'] != 'none':
                        Y_name = f"{get_mapping(mongoclient[config['DATABASE']], mapping_type='AGGREGATION', key=text.get('aggregation'), default_value=('CountNonNull', 5))[0]}({text.get('table')}.{text.get('column')})"
                        if Y_name not in select_dict:
                            select_dict[Y_name] = {
                                "Aggregation": {
                                    "Expression": {
                                        "Column": {
                                            "Expression": {"SourceRef": {"Source": str(self._table_alias_mapping.get(text.get('table')))}},
                                            "Property": text.get('column')
                                        }
                                    },
                                    "Function": get_mapping(mongoclient[config['DATABASE']], mapping_type='AGGREGATION', key=text.get('aggregation'), default_value=('CountNonNull', 5))[1]
                                },
                                "Name": Y_name,
                                "NativeReferenceName": text.get('column')
                            }

            else :
                return
        except Exception as e:
            print("error in Y",e)
            return e
        
        
        select = list(select_dict.values())

        order = []
        added_exprs = set()
        for item in select:
            if "'" in item:
                expr_json = json.dumps(item["Aggregation"], sort_keys=True)
                if expr_json not in added_exprs:
                    order.append({"Direction": 2, "Expression":{"Aggregation": item["Aggregation"]}})
                    added_exprs.add(expr_json)
        conf = {
                "name": uuid.uuid4().hex[:16],
                "layouts": [{
                    "id": 0,
                    "position": {
                        "x": zone['x'], "y": zone['y'],
                        "width": zone['w'], "height": zone['h'],
                        "z": 0, "tabOrder": 0
                    }
                }],
                "singleVisual": {
                    "visualType": VISUAL_TYPE,
                    "projections": {"Category": category, "Y": Y},
                    "prototypeQuery": {
                        "Version": 2,
                        "From": [{"Name":str(self._table_alias_mapping.get(i)), "Entity": i, "Type": 0} for i in set(unique_table)],
                        "Select": select,
                        "OrderBy": order
                    },
                    "drillFilterOtherVisuals": True,
                    "hasDefaultSort": True,
                    "objects": {
            "labels": [
                {
                "properties": {
                    "show": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
            "totals": [
                {
                "properties": {
                    "show": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
            "valueAxis": [
                {
                "properties": {
                    "gridlineShow": {
                    "expr": {
                        "Literal": {
                        "Value": "false"
                        }
                    }
                    }
                }
                }
            ]
            },
                    "vcObjects": {
            "title": [
                {
                "properties": {
                    "text": {
                    "expr": {
                        "Literal": {
                        "Value": f"'{sheet_mapper.get('chartTilte')}'"
                        }
                    }
                    },
                    "fontFamily": {
                    "expr": {
                        "Literal": {
                        "Value": "'''Segoe UI Semibold'', wf_segoe-ui_semibold, helvetica, arial, sans-serif'"
                        }
                    }
                    },
                    "alignment": {
                    "expr": {
                        "Literal": {
                        "Value": "'center'"
                        }
                    }
                    },
                    "underline": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ]
            }
                }
            }
        return json.dumps(conf)
    def generate_tree_chart_config(self, sheet_mapper: dict, zone: dict,VISUAL_TYPE:str) -> str:
        select_dict={}
        unique_table=set()
        try:
            color=sheet_mapper['encodings']['color']
            if len(color) >=1:
                Groups=[{"queryRef": f"{color[0].get('table')}.{color[0].get('column')}", "active": True}]
                unique_table.add(color[0].get('table'))
                Group_name = Groups[0]['queryRef']
                if Group_name not in select_dict:
                    select_dict[Group_name] = {
                            "Column": {"Expression": {"SourceRef": {"Source": str(self._table_alias_mapping.get(color[0].get('table')))}}, "Property": color[0].get('column')},
                            "Name": Group_name,
                            "NativeReferenceName": color[0].get('column')
                        }
            else :
                return
        except Exception as e:
            return "err",e
        try:
            texts=sheet_mapper['encodings']['text']
            if len(texts) >=1:
                values=[{"queryRef": f"{get_mapping(mongoclient[config['DATABASE']],mapping_type="AGGREGATION",key=text.get('aggregation'),default_value=('CountNonNull',5))[0]}({text.get('table')}.{text.get('column')})"} for text in texts if text['aggregation'] != 'none']
                
                for text in texts:
                    unique_table.add(text.get('table'))
                    if text['aggregation'] != 'none':
                        Values_name=f"{get_mapping(mongoclient[config['DATABASE']],mapping_type="AGGREGATION",key=text.get('aggregation'),default_value=('CountNonNull',5))[0]}({text.get('table')}.{text.get('column')})"
                        if Values_name not in select_dict:
                            select_dict[Values_name] = {
                                    "Aggregation": {
                                        "Expression": {
                                            "Column": {
                                                "Expression": {"SourceRef": {"Source": str(self._table_alias_mapping.get(text.get('table')))}},
                                                "Property": text.get('column')
                                            }
                                        },
                                        "Function": get_mapping(mongoclient[config['DATABASE']],mapping_type="AGGREGATION",key=text.get('aggregation'),default_value=('CountNonNull',5))[1]
                                    },
                                    
                                    "Name": Values_name,
                                    "NativeReferenceName": text.get('column')
                                }

            else :
                return
        except Exception as e:
            print("error in Y",e)
            return e
        
        
        select = list(select_dict.values())

        order = []
        added_exprs = set()
        for item in select:
            if "Aggregation" in item:
                expr_json = json.dumps(item["Aggregation"], sort_keys=True)
                if expr_json not in added_exprs:
                    order.append({"Direction": 2, "Expression":{"Aggregation": item["Aggregation"]}})
                    added_exprs.add(expr_json)
        conf = {
                "name": uuid.uuid4().hex[:16],
                "layouts": [{
                    "id": 0,
                    "position": {
                        "x": zone['x'], "y": zone['y'],
                        "width": zone['w'], "height": zone['h'],
                        "z": 0, "tabOrder": 0
                    }
                }],
                "singleVisual": {
                    "visualType": VISUAL_TYPE,
                    "projections": {"Group": Groups, "Values": values},
                    "prototypeQuery": {
                        "Version": 2,
                        "From": [{"Name":str(self._table_alias_mapping.get(i)), "Entity": i, "Type": 0} for i in set(unique_table)],
                        "Select": select,
                        "OrderBy": order
                    },
                    "drillFilterOtherVisuals": True,
                    "hasDefaultSort": True,
                    "objects": {
            "labels": [
                {
                "properties": {
                    "show": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
            "totals": [
                {
                "properties": {
                    "show": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
            "valueAxis": [
                {
                "properties": {
                    "gridlineShow": {
                    "expr": {
                        "Literal": {
                        "Value": "false"
                        }
                    }
                    }
                }
                }
            ]
            },
                    "vcObjects": {
            "title": [
                {
                "properties": {
                    "text": {
                    "expr": {
                        "Literal": {
                        "Value": f"'{sheet_mapper.get("chartTilte")}'"
                        }
                    }
                    },
                    "fontFamily": {
                    "expr": {
                        "Literal": {
                        "Value": "'''Segoe UI Semibold'', wf_segoe-ui_semibold, helvetica, arial, sans-serif'"
                        }
                    }
                    },
                    "alignment": {
                    "expr": {
                        "Literal": {
                        "Value": "'center'"
                        }
                    }
                    },
                    "underline": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ]
            }
                }
            }
        return json.dumps(conf) 
    def generate_table_chart_config(self, sheet_mapper: dict, zone: dict,VISUAL_TYPE:str) -> str:
        select_dict={}
        unique_table=set()
        try:
                rows=sheet_mapper['rows']
                if len(rows) >=1:
                    values=[{"queryRef": f"{row.get('table')}.{row.get('column')}"} for row in rows]
                    for row in rows:
                        unique_table.add(row.get('table'))
                        values_name=f"{row.get('table')}.{row.get('column')}"
                        if values_name not in select_dict:
                            select_dict[values_name] = {
                                    "Column": {"Expression": {"SourceRef": {"Source": str(self._table_alias_mapping.get(row.get('table')))}}, "Property": row.get('column')},
                                    "Name": values_name,
                                    "NativeReferenceName": row.get('column')
                                }
                else :
                    return
                
        except Exception as e:
            print("error in Y",e)
            return e
        select = list(select_dict.values())

        order = []
        added_exprs = set()
        for item in select:
            if "Aggregation" in item:
                expr_json = json.dumps(item["Aggregation"], sort_keys=True)
                if expr_json not in added_exprs:
                    order.append({"Direction": 2, "Expression":{"Aggregation": item["Aggregation"]}})
                    added_exprs.add(expr_json)
            else:
                expr_json = json.dumps(item["Column"], sort_keys=True)
                if expr_json not in added_exprs:
                    order=[{"Direction": 1, "Expression":{ "Column": item["Column"]}}]
                    added_exprs.add(expr_json)
        conf = {
                "name": uuid.uuid4().hex[:16],
                "layouts": [{
                    "id": 0,
                    "position": {
                        "x": zone['x'], "y": zone['y'],
                        "width": zone['w'], "height": zone['h'],
                        "z": 0, "tabOrder": 0
                    }
                }],
                "singleVisual": {
                    "visualType": VISUAL_TYPE,
                    "projections": {"Values": values},
                    "prototypeQuery": {
                        "Version": 2,
                        "From": [{"Name":str(self._table_alias_mapping.get(i)), "Entity": i, "Type": 0} for i in set(unique_table)],
                        "Select": select,
                        "OrderBy": order
                    },
                    "drillFilterOtherVisuals": True,
                    "hasDefaultSort": True,
                    "objects": {
            "labels": [
                {
                "properties": {
                    "show": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
            "totals": [
                {
                "properties": {
                    "show": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
            "valueAxis": [
                {
                "properties": {
                    "gridlineShow": {
                    "expr": {
                        "Literal": {
                        "Value": "false"
                        }
                    }
                    }
                }
                }
            ]
          },
                    "vcObjects": {
            "title": [
                {
                "properties": {
                    "text": {
                    "expr": {
                        "Literal": {
                        "Value": f"'{sheet_mapper.get("chartTilte")}'"
                        }
                    }
                    },
                    "fontFamily": {
                    "expr": {
                        "Literal": {
                        "Value": "'''Segoe UI Semibold'', wf_segoe-ui_semibold, helvetica, arial, sans-serif'"
                        }
                    }
                    },
                    "alignment": {
                    "expr": {
                        "Literal": {
                        "Value": "'center'"
                        }
                    }
                    },
                    "underline": {
                    "expr": {
                        "Literal": {
                        "Value": "true"
                        }
                    }
                    }
                }
                }
            ],
             "border": [
                        {
                        "properties": {
                            "show": {
                            "expr": {
                                "Literal": {
                                "Value": "true"
                                }
                            }
                            }
                        }
                        }
                    ]
           
           
            }
                }
            }
        return json.dumps(conf)
    def generate_slicer_config(self,Param:str,dbmap:dict,zone:dict,VISUAL_TYPE:str) -> str:
        parmas_cols=resolve_column(Param,dbmap)
        tbl=parmas_cols.get('table')
        col=parmas_cols.get('column')
        conf=json.dumps({
        "name": uuid.uuid4().hex[:16],
        "layouts": [{"id": 0, "position": {
            "x": round(float(zone['x']), 4),
            "y": round(float(zone['y']), 4),
            "width": round(float(zone['w']), 4),
            "height": round(float(zone['h']), 4),
            "z": 0,
            "tabOrder": 0
        }}],
        "singleVisual": {
            "visualType": VISUAL_TYPE,
            "projections": {
                "Values": [{"queryRef": f"{tbl}.{col}", "active": True}]
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name":str(self._table_alias_mapping.get(tbl)), "Entity": tbl, "Type": 0}],
                "Select": [{
                    "Column": {
                        "Expression": {"SourceRef": {"Source": str(self._table_alias_mapping.get(tbl))}},
                        "Property": col
                    },
                    "Name": f"{tbl}.{col}",
                    "NativeReferenceName": col
                }]
            },
            "drillFilterOtherVisuals": True,
            "hasDefaultSort": True
        }
    })
        return conf
        
     
        


class ConfigSectionBuilder:
    def build_sections(self,root:ET.Element,sheet_mapper: dict,database_mapper:dict) -> str:
        sections = []
        count=1
        for dash in root.findall('.//dashboard'):
            dashboardName=dash.get('name')
            print("="*50)
            print(dashboardName)
            zones=dash.find('zones')
            zones = zones.findall('.//zone')
            container_list = []
            for zone in zones:  
                # print(zone)
                worksheet_name = zone.get('name')
                if not worksheet_name :
                    continue	    
                zone_info = {
                    'x':  round(float(zone.get('x')) * 0.0128, 4), 'y': round(float(zone.get('y')) * 0.0072, 4),
                    'w':round(float(zone.get('w')) * 0.0128, 4), 'h': round(float(zone.get('h')) * 0.0072, 4)
                }   
                '''
                placeholder for params which filter in powerbi
                '''
                params=zone.get('param')
                alias_mapper=generate_table_aliases(database_mapper)
                builder=ConfigStringBuilder(alias_mapper)
                
                # print(type(params),worksheet_name,"====parmas:--",params)
                if params is not None:
                    # print(params)
                    databaseMapper=build_meta_map(root=root)
                    visual_json=builder.generate_slicer_config(params,databaseMapper,zone_info,'slicer')
                    
                else:
                
                    if worksheet_name not in sheet_mapper:
                        # log in database worksheet not able parse or something went wrong while parse
                        continue
                    
                    worksheet_information = sheet_mapper[worksheet_name]
                    powerBIChartType=get_mapping(mongoclient[config['DATABASE']], 'VISUAL', worksheet_information['visualType'])
                    # print(worksheet_information['visualType'],"powerBIChartType--",powerBIChartType)
                    # print("worksheet==",worksheet_information)
                    if powerBIChartType:
                       
                        if worksheet_information['visualType'] in  ['Bar', 'Area','Line']:
                            visual_json=builder.generate_column_chart_config(worksheet_information, zone_info,powerBIChartType)
                        elif worksheet_information['visualType'] in  ['Pie']:
                            visual_json=builder.generate_pie_chart_config(worksheet_information, zone_info,powerBIChartType)
                        else:
                            print("not support function -",worksheet_information['visualType'])
                            continue
                            # log need to create function
                    elif str(worksheet_information['visualType']).lower()=='automatic':
                        print("check_automatic")
                        # print("===",worksheet_information)
                        if (worksheet_information['cols'] and len(worksheet_information['cols']) >= 1) and \
                            (worksheet_information['rows'] and len(worksheet_information['rows']) >= 1):
                                print("automatic bar chart")
                                visualType=get_mapping(mongoclient[config['DATABASE']], 'VISUAL', 'Bar')
                                visual_json = builder.generate_column_chart_config(worksheet_information, zone_info, visualType)
                        elif (worksheet_information['encodings'].get('color') and len(worksheet_information['encodings'].get('color')) >= 1) and \
                            (worksheet_information['encodings'].get('text') and len(worksheet_information['encodings'].get('text')) >= 1):
                                print("automatic pie")
                                visualType=get_mapping(mongoclient[config['DATABASE']], 'VISUAL', 'Pie')
                                visual_json = builder.generate_pie_chart_config(worksheet_information, zone_info, visualType)
                        elif (worksheet_information['rows'] and len(worksheet_information['rows']) >= 1):
                            print("automatic tree")
                            print(type(worksheet_information),"==",worksheet_information)
                            print(type(zone_info),"==",zone_info)
                            visual_json = builder.generate_table_chart_config(worksheet_information, zone_info, "tableEx")
                        else:
                            print("not support -unable to figure out graph")
                            continue
                
                    else:
                        print("not support -",worksheet_information['visualType'])
                        continue
                    # log errror this visual type not supported by 
                container_list.append({
				"config": visual_json,
				"filters": "[]",
				"x": zone_info['x'], "y": zone_info['y'],
				"width": zone_info['w'], "height": zone_info['h'],
				"z": 0
			    })
            sections.append({
                              "config": "{}",
                                "displayName": dashboardName,
                                "displayOption": 1,
                                "filters": "[]",
                                "height": 720.00,
                                "name": "339aa1a7dca4c13189bc",
                                "ordinal": count,
                                'visualContainers':container_list,
                                "width": 1280.00
                             })
            count =count+1
        return sections    
                
if __name__ == "__main__":
    worksheet_information=dict({'visualType': 'Automatic', 'main_table': 'training_and_development_data', 'chartTilte': '', 'fontname': 
'', 'fontsize': '', 'rows': [{'column': 'LastName', 'table': 'employee_data', 'aggregation': 'none'}], 'cols': [], 'encodings': {'text': [{'column': 'Active emp', 'table': 'employee_data', 'aggregation': 'sum', 'formula': 'IF [StartDate]<=TODAY() and ISNULL([ExitDate])or [ExitDate]>=TODAY() THEN 1 ELSE 0 END'}]}})
    zone_info = dict({'x': 42.24, 'y': 29.7, 'w': 1045.76, 'h': 694.8})
    database_mapper=dict({'Employee ID': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Training Date': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Training Program Name': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Training Type': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Training Outcome': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Location': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Trainer': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Training Duration(Days)': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Training Cost': {'table': 'training_and_development_data', 'aggregation': 'Count', 'datatype': 'string'}, 'EmpID': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'FirstName': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'LastName': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'StartDate': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'ExitDate': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Title': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Supervisor': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'ADEmail': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'BusinessUnit': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'EmployeeStatus': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'EmployeeType': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'PayZone': {'table': 
'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'EmployeeClassificationType': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'TerminationType': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'TerminationDescription': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'DepartmentType': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Division': {'table': 'employee_data', 
'aggregation': 'Count', 'datatype': 'string'}, 'DOB': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'State': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'JobFunctionDescription': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'GenderCode': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'LocationCode': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'RaceDesc': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'MaritalDesc': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Performance Score': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Current Employee Rating': {'table': 'employee_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Applicant ID': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Application Date': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'First Name': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Last Name': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Gender': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Date of Birth': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Phone Number': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Email': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Address': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'City': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'State (recruitment_data)': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Zip Code': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Country': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Education Level': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Years of Experience': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Desired Salary': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 
'Job Title': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Status': {'table': 'recruitment_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Employee ID (employee_engagement_survey_data1)': {'table': 'employee_engagement_survey_data1', 'aggregation': 'Count', 'datatype': 'string'}, 'Survey Date (employee_engagement_survey_data1)': {'table': 'employee_engagement_survey_data1', 'aggregation': 'Count', 'datatype': 'string'}, 'Engagement Score (employee_engagement_survey_data1)': {'table': 'employee_engagement_survey_data1', 'aggregation': 'Count', 'datatype': 'string'}, 'Satisfaction Score (employee_engagement_survey_data1)': {'table': 'employee_engagement_survey_data1', 'aggregation': 'Count', 
'datatype': 'string'}, 'Work-Life Balance Score (employee_engagement_survey_data1)': {'table': 'employee_engagement_survey_data1', 'aggregation': 'Count', 'datatype': 'string'}, 'Employee ID (employee_engagement_survey_data)': {'table': 'employee_engagement_survey_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Survey Date': {'table': 'employee_engagement_survey_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Engagement Score': {'table': 'employee_engagement_survey_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Satisfaction Score': {'table': 'employee_engagement_survey_data', 'aggregation': 'Count', 'datatype': 'string'}, 'Work-Life Balance Score': {'table': 'employee_engagement_survey_data', 'aggregation': 'Count', 'datatype': 'string'}})
    alias_mapper=generate_table_aliases(database_mapper)
    builder=ConfigStringBuilder(alias_mapper)
    report=builder.generate_table_chart_config(worksheet_information, zone_info, "tableEx")
    print(report)
