from generate_report_json import convert_twb
import os

tableau_files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '02_tableau_files')
input_tableau_file = os.path.join(tableau_files_dir, 'Complex HRMS Employee Dashboard.twb')
AGG_MAP_combo = {
    'count': ('CountNonNull',5), 
    'cnt': ('CountNonNull',5),
	'sum': ('Sum',0), 
    'avg': ('Average',1), 
    'min': ('Min',2),
	'max': ('Max',3), 
    'median': ('Median',4)
}

convert_twb(input_tableau_file)