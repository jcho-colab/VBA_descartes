
import os
import glob
from lxml import etree

def debug_hs(target_hs):
    base_dir = r"d:\VS_project\VBA Descartes\input XML"
    files = glob.glob(os.path.join(base_dir, "*_DTR_*.xml"))
    
    print(f"Searching for HS {target_hs} in {len(files)} DTR files...")
    
    found = False
    for f in files:
        context = etree.iterparse(f, events=('end',), tag='duty_rate_entity')
        for event, elem in context:
            hs_id = elem.get('hs_id', '')
            # Cleanse logic: remove leading '00'
            if hs_id.startswith('00'):
                clean_hs = hs_id[2:]
            else:
                clean_hs = hs_id
                
            if clean_hs == target_hs:
                print(f"\nFOUND in {os.path.basename(f)}")
                print(f"HS ID raw: {hs_id}")
                print(f"Duty Rate Type: {elem.get('duty_rate_type')}")
                print(f"Valid From: {elem.get('valid_from')}")
                print(f"Valid To: {elem.get('valid_to')}")
                print(f"Version Date: {elem.get('date_of_physical_update')}")
                
                # Check rates and groups
                for cg in elem.findall('country_group'):
                    cg_id = cg.get('id')
                    print(f"  Group: {cg_id}")
                    for rate in cg.findall('rate'):
                        rt = rate.get('duty_rate_type_id')
                        print(f"    Rate Type ID: {rt}")
                        
                        # Print rate details
                        for child in rate:
                            print(f"      {child.tag}: {child.attrib}")
                            desc = child.find('description') # nested description?
                            # Check text attribute or nested description text
                            
                # Check preference note
                pn = elem.find('preference_note')
                if pn is not None:
                     note = pn.find('note')
                     if note is not None:
                         print(f"  Note: {note.text}")
                
                found = True
            
            elem.clear()
            
    if not found:
        print("HS not found.")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "2501000001L"
    debug_hs(target)
