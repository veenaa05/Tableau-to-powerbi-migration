import xml.etree.ElementTree as ET
from config_string_builder import ConfigStringBuilder,ConfigSectionBuilder
from parse_twb_structure import parseWorksheet,build_meta_map
import os


def generate_report_json(TWB_file_path):
	tree = ET.parse(TWB_file_path)
	root = tree.getroot()
	ds_map = build_meta_map(root)
	print(type(ds_map),'==',ds_map)
	ws_map = parseWorksheet(root,ds_map)
	section = ConfigSectionBuilder().build_sections(root,ws_map,ds_map)
	# print(type(section))
	report_content= {
		"config": "{\"version\":\"5.59\",\"themeCollection\":{\"baseTheme\":{\"name\":\"CY24SU10\",\"version\":\"5.65\",\"type\":2}},\"activeSectionIndex\":1,\"defaultDrillFilterOtherVisuals\":true,\"linguisticSchemaSyncVersion\":2,\"settings\":{\"useNewFilterPaneExperience\":true,\"allowChangeFilterTypes\":true,\"useStylableVisualContainerHeader\":true,\"queryLimitOption\":6,\"exportreport_contentMode\":1,\"useDefaultAggregateDisplayName\":true,\"useEnhancedTooltips\":true},\"objects\":{\"section\":[{\"properties\":{\"verticalAlignment\":{\"expr\":{\"Literal\":{\"Value\":\"'Top'\"}}}}}]}}",
		"layoutOptimization": 0,
		"resourcePackages": [
			{
				"resourcePackage": {
					"disabled": False,
					"items": [
						{
							"name": "CY24SU10",
							"path": "BaseThemes/CY24SU10.json",
							"type": 202
						}
					],
					"name": "SharedResources",
					"type": 2
				}
			}
		],
		"sections": section
	}
	return report_content
if __name__=='__main__':
	tableau_files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '02_tableau_files')
	report_data=generate_report_json(os.path.join(tableau_files_dir, 'Complex HRMS Employee Dashboard.twb'))
	output_file_path = os.path.join(tableau_files_dir, 'report.json')
	import json
	# Write the report data to a JSON file
	with open(output_file_path, 'w') as json_file:
		json_file.write(str(report_data))
     
		# json.dump(report_data, json_file, indent=4)  # Using indent for pretty printing

	print(f'Report saved to {output_file_path}')