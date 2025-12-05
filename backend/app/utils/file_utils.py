
import re

def sanitize_filename(filename):
    
    filename = filename.strip()
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'[^\w\.\-]', '', filename)
    filename = filename.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ç", "c")
    filename = filename.replace("É", "E").replace("È", "E").replace("Ê", "E").replace("À", "A").replace("Ç", "C")
    filename = filename.replace("ô", "o").replace("î", "i").replace("ù", "u").replace("Â", "A").replace("Î", "I")
    filename = filename.replace("Ô", "O").replace("Û", "U").replace("ë", "e").replace("ü", "u").replace("Ë", "E")
    filename = filename.replace("Ü", "U").replace("Â", "A").replace("Î", "I").replace("Ô", "O").replace("Û", "U")
    filename = filename.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")

    filename_parts = filename.rsplit('.', 1)
    
    if len(filename_parts) > 1:
        if len(filename) > 60:
           filename_parts[0] = filename_parts[0][:50] + '___'
        filename = filename_parts[0].replace('.', '_') + '.' + filename_parts[1]

    return filename
   