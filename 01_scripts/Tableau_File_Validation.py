import xml.etree.ElementTree as ET
import json,os
import zipfile
import tempfile
from typing import Optional,List

def validate_file(path :str) -> Optional[str]:
    if not os.path.exists(path):
        print(f"[Error] File does not exist: {path}")
        return None
    ext=os.path.splitext(path)[1].lower()
    if ext=='.tbw':
        valid_path=path
    elif ext =='.twbx':
        try:
            with zipfile.ZipFile(path, 'r') as z:
                twb_files = [f for f in z.namelist() if f.endswith('.twb')]
                if not twb_files:
                    print("[Error] No .twb file found inside .twbx archive.")
                    return None
                twb_filename = twb_files[0]
                TWBX_file_name=os.path.splitext(os.path.basename(path))[0]
                current_dir=os.path.dirname(os.path.abspath(__file__))
                conversion_path=os.path.join(current_dir,'..','Converted_twbx',TWBX_file_name)
                os.makedirs(conversion_path,exist_ok=True)
                extracted_path = z.extract(twb_filename, path=conversion_path)
                valid_path= extracted_path
        except zipfile.BadZipFile:
            print("[Error] Invalid .twbx file (corrupt or not a zip).")
            return None
    else:
        print("[Error] File must be .twb or .twbx")
        return None
    
    return valid_path

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
if __name__=='__main__':
    twbx_file = r"D:\manish.yadav\project\Tableau to power bi\Tableau_Files\1 NetFlixDatasetnew - Bar Chart - Simple.twbx"
    file_path=validate_file(twbx_file)
    print(file_path)
    output=validate_twb_tags(file_path)
    print("====",output)