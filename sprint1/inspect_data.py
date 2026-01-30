import pickle
import pandas as pd
import json
import numpy as np
from datetime import date, datetime

def convert_to_serializable(obj):
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)

try:
    with open('mckinsey_our_code_we_respect_data.pkl', 'rb') as f:
        dict_df = pickle.load(f)
    
    output_data = {}
    
    print("Keys in dict_df:", dict_df.keys())
    
    for key, value in dict_df.items():
        if isinstance(value, dict):
            output_data[key] = {}
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, pd.DataFrame):
                    print(f"Processing DataFrame: {key} -> {sub_key}")
                    df_info = {
                        'type': 'DataFrame',
                        'shape': sub_value.shape,
                        'columns': sub_value.columns.tolist(),
                        'dtypes': sub_value.dtypes.astype(str).to_dict(),
                        'sample_data': sub_value.head(5).to_dict(orient='records')
                    }
                    output_data[key][sub_key] = df_info
                else:
                    output_data[key][sub_key] = {
                        'type': str(type(sub_value)),
                        'value': str(sub_value)
                    }
        elif isinstance(value, pd.DataFrame):
            print(f"Processing DataFrame: {key}")
            df_info = {
                'type': 'DataFrame',
                'shape': value.shape,
                'columns': value.columns.tolist(),
                'dtypes': value.dtypes.astype(str).to_dict(),
                'sample_data': value.head(5).to_dict(orient='records')
            }
            output_data[key] = df_info
        else:
             output_data[key] = {
                'type': str(type(value)),
                'value': str(value)
            }

    # Custom JSON encoder to handle non-serializable types
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            return convert_to_serializable(obj)

    with open('data_inspection.json', 'w') as f:
        json.dump(output_data, f, indent=2, cls=CustomEncoder)
        
    print("Data structure exported to data_inspection.json")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
