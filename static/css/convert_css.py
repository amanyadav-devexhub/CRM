import os

def convert_css():
    path = r'c:\Users\Simran\Downloads\CRM\static\css\original_dashboard.css'
    output_path = r'c:\Users\Simran\Downloads\CRM\static\css\dashboard_recovered.css'
    
    try:
        with open(path, 'rb') as f:
            content = f.read()
        
        # Try to decode from UTF-16LE
        decoded = content.decode('utf-16le')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(decoded)
        print(f"Successfully converted to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    convert_css()
