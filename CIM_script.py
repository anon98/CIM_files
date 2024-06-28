from PyCIM import cimread
import pandas as pd
import xml.etree.ElementTree as ET


def convert_single_cim_to_ppc(cim_file):
    # Initialize the PPC dictionary
    ppc = {
        'version': '2',
        'baseMVA': 1.0,
        'bus': [],
        'gen': [],
        'branch': [],
        'gencost': []
    }
    
    # Define the namespaces
    ns = {
        'cim': 'http://iec.ch/TC57/2016/CIM-schema-cim17#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    }
    
    # Parse the CIM XML file
    tree = ET.parse(cim_file)
    root = tree.getroot()
    
    # Debug: Print root tag and its attributes
    print(f"Processing file: {cim_file}")
    print(f"Root tag: {root.tag}, Attributes: {root.attrib}")

    # Create a dictionary to store BaseVoltage values by ID
    base_voltage_dict = {}
    for bv in root.findall('cim:BaseVoltage', ns):
        bv_id = bv.get(f'{{{ns["rdf"]}}}ID')
        nominal_voltage = bv.find('cim:BaseVoltage.nominalVoltage', ns).text
        base_voltage_dict[bv_id] = float(nominal_voltage)
    
    # Create a mapping for unique IDs to numbers
    id_mapping = {}
    id_counter = 1
    
    def get_mapped_id(original_id):
        nonlocal id_counter
        if original_id not in id_mapping:
            id_mapping[original_id] = id_counter
            id_counter += 1
        return id_mapping[original_id]

    # Process ConnectivityNodes as buses
    for node in root.findall('cim:ConnectivityNode', ns):
        bus_id = get_mapped_id(node.get(f'{{{ns["rdf"]}}}ID'))
        name = node.find('cim:IdentifiedObject.name', ns).text
        print(f"ConnectivityNode ID: {bus_id}, Name: {name}")
        ppc['bus'].append([
            bus_id,
            1,  # type
            0.0,  # Pd (default to 0 for now)
            0.0,  # Qd (default to 0 for now)
            0.0,  # Gs
            0.0,  # Bs
            1,  # area
            1.0,  # Vm (default to 1.0 for now)
            0.0,  # Va (default to 0 for now)
            1.0,  # base_kv (default to 1.0 for now)
            1,  # zone
            1.1,  # Vmax
            0.9   # Vmin
        ])
    
    # Process EnergyConsumers as loads on buses
    for consumer in root.findall('cim:EnergyConsumer', ns):
        consumer_id = consumer.get(f'{{{ns["rdf"]}}}ID')
        name = consumer.find('cim:IdentifiedObject.name', ns).text
        p_fixed = float(consumer.find('cim:EnergyConsumer.pfixed', ns).text)
        q_fixed = float(consumer.find('cim:EnergyConsumer.qfixed', ns).text)
        bus_id = get_mapped_id(consumer.find('cim:Equipment.EquipmentContainer', ns).get(f'{{{ns["rdf"]}}}resource').split("#")[-1])
        print(f"EnergyConsumer ID: {consumer_id}, Name: {name}, P_fixed: {p_fixed}, Q_fixed: {q_fixed}, Bus ID: {bus_id}")
        
        for bus in ppc['bus']:
            if bus[0] == bus_id:
                bus[2] = p_fixed  # Pd
                bus[3] = q_fixed  # Qd
    
    # Process Disconnectors as branches
    for disconnector in root.findall('cim:Disconnector', ns):
        disconnector_id = get_mapped_id(disconnector.get(f'{{{ns["rdf"]}}}ID'))
        name = disconnector.find('cim:IdentifiedObject.name', ns).text
        base_voltage_id = disconnector.find('cim:ConductingEquipment.BaseVoltage', ns).get(f'{{{ns["rdf"]}}}resource').split("#")[-1]
        base_voltage = base_voltage_dict.get(base_voltage_id, 1.0)
        equipment_container = get_mapped_id(disconnector.find('cim:Equipment.EquipmentContainer', ns).get(f'{{{ns["rdf"]}}}resource').split("#")[-1])
        print(f"Disconnector ID: {disconnector_id}, Name: {name}, Base Voltage: {base_voltage}, Equipment Container: {equipment_container}")
        
        ppc['branch'].append([
            base_voltage,
            equipment_container,
            0.0,  # r (default to 0 for now)
            0.0,  # x (default to 0 for now)
            0.0,  # bch (default to 0 for now)
            9999.0,  # rateA (default to a high value for now)
            9999.0,  # rateB (default to a high value for now)
            9999.0,  # rateC (default to a high value for now)
            0.0,  # ratio (default to 0 for now)
            0.0,  # angle (default to 0 for now)
            1,  # status (assuming all disconnectors are closed)
            -360,  # angmin
            360   # angmax
        ])
    
    # Process TopologicalNodes as buses
    for node in root.findall('cim:TopologicalNode', ns):
        topo_node_id = get_mapped_id(node.get(f'{{{ns["rdf"]}}}ID'))
        name = node.find('cim:IdentifiedObject.name', ns).text
        base_voltage_id = node.find('cim:TopologicalNode.BaseVoltage', ns).get(f'{{{ns["rdf"]}}}resource').split("#")[-1]
        base_voltage = base_voltage_dict.get(base_voltage_id, 1.0)
        print(f"TopologicalNode ID: {topo_node_id}, Name: {name}, Base Voltage: {base_voltage}")
        
        ppc['bus'].append([
            topo_node_id,
            1,  # type
            0.0,  # Pd (default to 0 for now)
            0.0,  # Qd (default to 0 for now)
            0.0,  # Gs
            0.0,  # Bs
            1,  # area
            1.0,  # Vm (default to 1.0 for now)
            0.0,  # Va (default to 0 for now)
            base_voltage,  # base_kv
            1,  # zone
            1.1,  # Vmax
            0.9   # Vmin
        ])
    
    return ppc

# List of CIM files to parse
cim_files = [
    'data/1.xml',
    'data/2.xml',
    'data/3.xml'
]

# Convert CIM to PPC and save each one separately
for i, cim_file in enumerate(cim_files):
    ppc = convert_single_cim_to_ppc(cim_file)
    output_file = f'ppc_{i+1}.py'
    with open(output_file, 'w') as f:
        f.write(f'ppc = {ppc}')
    print(f"Conversion to PYPOWER PPC format completed successfully for {cim_file}, saved as {output_file}")